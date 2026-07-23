from __future__ import annotations
from .base import BaseModel
from .meta import ModelMeta


class Model(BaseModel, metaclass=ModelMeta):
    """
    Sinxron muhit uchun ORM Model klassi.
    Jadval tuzilishi, ma'lumotlarni o'qish, yozish, yangilash va o'chirish metodlarini taqdim etadi.
    """

    @classmethod
    def query(cls):
        cls._check_setup()
        from .query import QuerySet

        return QuerySet(cls)

    @classmethod
    def all(cls):
        return cls.query().all()

    @classmethod
    def find(cls, pk=None, id=None):
        search_id = pk if pk is not None else id
        from .query import FindQuerySet

        return FindQuerySet(cls, search_id)

    @classmethod
    def raw_sql(cls, sql: str, *params):
        """Sof SQL orqali model obyektlarini olish."""
        cls._check_setup()
        records = cls.db.raw(sql, params, fetchall=True)
        if not records:
            return []
        return [cls._from_record(r) for r in records]

    @classmethod
    def filter(cls, *args, **kwargs):
        return cls.query().filter(*args, **kwargs)

    @classmethod
    def first(cls, **kwargs):
        qs = cls.query()
        if kwargs:
            qs = qs.filter(**kwargs)
        return qs.first()

    @classmethod
    def last(cls, **kwargs):
        qs = cls.query()
        if kwargs:
            qs = qs.filter(**kwargs)
        return qs.last()

    @classmethod
    def get(cls, **kwargs):
        from postgresdb3.exceptions import ObjectDoesNotExist, MultipleObjectsReturned

        results = cls.filter(**kwargs).limit(2).all()

        if not results:
            raise ObjectDoesNotExist(f"{cls.__name__} obyekti topilmadi")

        if len(results) > 1:
            raise MultipleObjectsReturned(f"Bir nechta {cls.__name__} obyekti topildi")

        return results[0]

    @classmethod
    def order_by(cls, value):
        return cls.query().order_by(value)

    @classmethod
    def limit(cls, value):
        return cls.query().limit(value)

    @classmethod
    def offset(cls, value):
        return cls.query().offset(value)

    @classmethod
    def paginate(cls, page: int = 1, per_page: int = 10):
        return cls.query().paginate(page, per_page)

    @classmethod
    def columns(cls, value):
        return cls.query().columns(value)

    @classmethod
    def join(cls, value):
        return cls.query().join(value)

    @classmethod
    def group_by(cls, value):
        return cls.query().group_by(value)

    @classmethod
    def annotate(cls, **kwargs):
        return cls.query().annotate(**kwargs)

    @classmethod
    def exclude(cls, **kwargs):
        return cls.query().exclude(**kwargs)

    @classmethod
    def count(cls):
        return cls.query().count()

    @classmethod
    def values(cls, *fields):
        return cls.query().values(*fields)

    @classmethod
    def values_list(cls, *fields, flat=False):
        return cls.query().values_list(*fields, flat=flat)

    @classmethod
    def exists(cls):
        return cls.query().exists()

    @classmethod
    def create(cls, **kwargs):
        cls._check_setup()

        kwargs = cls._normalize_kwargs(kwargs)
        kwargs = {
            k: v
            for k, v in kwargs.items()
            if not (cls._fields.get(k) and not cls._fields[k].to_sql())
        }

        for key, field in cls._fields.items():
            if not field.to_sql():
                continue
            if getattr(field, "auto_now", False):
                kwargs[key] = field.get_current_value()
            elif (
                key not in kwargs
                or kwargs[key] is None
                or kwargs[key]
                in ("CURRENT_DATE", "CURRENT_TIME", "CURRENT_TIMESTAMP", "NOW()")
            ):
                if getattr(field, "auto_now_add", False):
                    kwargs[key] = field.get_current_value()
                elif field.default is not None:
                    kwargs[key] = field.get_default_value()

        from postgresdb3.orm.signals import pre_save, post_save

        instance = cls(**kwargs)
        instance.clean()
        instance.before_save()
        pre_save.send(sender=cls, instance=instance, created=True)

        columns = ", ".join(kwargs.keys())
        values = tuple(kwargs.values())

        record = cls.db.insert(cls.table, columns, values, returning="*")
        obj = cls._from_record(record)
        obj.after_save(created=True)
        post_save.send(sender=cls, instance=obj, created=True)
        return obj

    @classmethod
    def get_or_create(cls, defaults=None, **kwargs):
        return cls.query().get_or_create(defaults=defaults, **kwargs)

    @classmethod
    def update_or_create(cls, defaults=None, **kwargs):
        return cls.query().update_or_create(defaults=defaults, **kwargs)

    @classmethod
    def bulk_create(cls, instances: list["Model"]) -> None:
        if not instances:
            return

        columns = [
            k
            for k, f in cls._fields.items()
            if not (f.primary_key and f.sql_type in ("SERIAL", "BIGSERIAL"))
            and f.to_sql()
        ]

        values_list = []
        for inst in instances:
            for col in columns:
                field = cls._fields[col]
                if getattr(field, "auto_now", False):
                    setattr(inst, col, field.get_current_value())
                elif getattr(field, "auto_now_add", False):
                    if getattr(inst, col, None) is None:
                        setattr(inst, col, field.get_current_value())
                elif getattr(inst, col, None) is None and field.default is not None:
                    setattr(inst, col, field.get_default_value())

            val_tuple = tuple(getattr(inst, col, None) for col in columns)
            values_list.append(val_tuple)

        columns_str = ", ".join(columns)
        with cls.db.transaction():
            cls.db.insert_many(cls.table, columns_str, values_list)

    @classmethod
    def bulk_update(cls, instances: list["Model"], fields: list[str]) -> None:
        if not instances or not fields:
            return

        pk_name = cls.get_pk_name()
        auto_now_fields = [
            k for k, f in cls._fields.items() if getattr(f, "auto_now", False)
        ]
        fields_to_update = list(fields)
        for col in auto_now_fields:
            if col not in fields_to_update and col != pk_name:
                fields_to_update.append(col)

        set_clause = ", ".join([f"{f} = %s" for f in fields_to_update])
        sql = f"UPDATE {cls.table} SET {set_clause} WHERE {pk_name} = %s"

        values_list = []
        for inst in instances:
            for col in auto_now_fields:
                val = cls._fields[col].get_current_value()
                setattr(inst, col, val)
            val_tuple = tuple(getattr(inst, f, None) for f in fields_to_update) + (
                getattr(inst, pk_name),
            )
            values_list.append(val_tuple)

        with cls.db.transaction():
            cls.db._manager(sql, values_list, commit=True, many=True)

    def clean(self):
        for field_name, field in self.__class__._fields.items():
            if not field.to_sql():
                continue
            value = getattr(self, field_name, None)
            if hasattr(field, "validate"):
                setattr(self, field_name, field.validate(value))

    def before_save(self):
        pass

    def after_save(self, created: bool):
        pass

    def before_delete(self):
        pass

    def after_delete(self):
        pass

    def save(self):
        from postgresdb3.orm.signals import pre_save, post_save

        self.__class__._check_setup()

        pk_name = self.__class__.get_pk_name()
        pk_value = getattr(self, pk_name, None)
        is_created = pk_value is None

        if is_created:
            for field_name, field in self.__class__._fields.items():
                if getattr(field, "auto_now", False):
                    setattr(self, field_name, field.get_current_value())
                elif getattr(field, "auto_now_add", False):
                    if getattr(self, field_name, None) is None:
                        setattr(self, field_name, field.get_current_value())

            self.clean()
            self.before_save()
            pre_save.send(sender=self.__class__, instance=self, created=True)

            data = self.to_dict()
            if data.get(pk_name) is None:
                data.pop(pk_name, None)

            created = self.__class__.create(**data)
            for field_name, field in self.__class__._fields.items():
                if field.to_sql():
                    setattr(self, field_name, getattr(created, field_name, None))
            self.after_save(created=True)
            post_save.send(sender=self.__class__, instance=self, created=True)
            return self

        for field_name, field in self.__class__._fields.items():
            if getattr(field, "auto_now", False):
                setattr(self, field_name, field.get_current_value())

        self.clean()
        self.before_save()
        pre_save.send(sender=self.__class__, instance=self, created=False)

        data = {}
        for field_name, field in self.__class__._fields.items():
            if field_name == pk_name or not field.to_sql():
                continue
            data[field_name] = getattr(self, field_name, None)

        data = self.__class__._normalize_kwargs(data)
        self.__class__.db.update_fields(self.__class__.table, data, pk_name, pk_value)

        self.after_save(created=False)
        post_save.send(sender=self.__class__, instance=self, created=False)
        return self

    def update(self, **kwargs):
        self.__class__._check_setup()

        if not kwargs:
            raise ValueError("Yangilash uchun kamida bitta ustun kerak")

        kwargs = self.__class__._normalize_kwargs(kwargs)

        pk_name = self.__class__.get_pk_name()
        pk_value = getattr(self, pk_name, None)

        if pk_value is None:
            raise ValueError(f"{pk_name} qiymati yo'q, yangilab bo'lmaydi")

        for key, value in kwargs.items():
            if key not in self.__class__._fields:
                raise ValueError(
                    f"{self.__class__.__name__} modelida '{key}' degan ustun yo'q"
                )

            if key == pk_name:
                raise ValueError(f"{pk_name} ustunini yangilab bo'lmaydi")

            if not isinstance(
                value,
                __import__(
                    "postgresdb3.orm.expressions", fromlist=["FExpression"]
                ).FExpression,
            ):
                setattr(self, key, value)

        for key, field in self.__class__._fields.items():
            if getattr(field, "auto_now", False) and key not in kwargs:
                val = field.get_current_value()
                kwargs[key] = val
                setattr(self, key, val)

        self.__class__.db.update_fields(self.__class__.table, kwargs, pk_name, pk_value)

        return self

    def delete(self):
        from postgresdb3.orm.signals import pre_delete, post_delete

        self.__class__._check_setup()
        self.before_delete()
        pre_delete.send(sender=self.__class__, instance=self)

        pk_name = self.__class__.get_pk_name()
        pk_value = getattr(self, pk_name, None)

        if pk_value is None:
            raise ValueError(f"{pk_name} qiymati yo'q, o'chirib bo'lmaydi")

        self.__class__.db.delete(self.__class__.table, pk_name, pk_value)
        self.after_delete()
        post_delete.send(sender=self.__class__, instance=self)
        return True


class AsyncModel(BaseModel, metaclass=ModelMeta):
    """
    Asinxron muhit uchun ORM Model klassi.
    Sinxron Model bilan bir xil ishlaydi, faqat barcha metodlari (create, update, delete va hk) `await` bilan chaqirilishi kerak.
    """

    @classmethod
    def query(cls):
        cls._check_setup()
        from .query import AsyncQuerySet

        return AsyncQuerySet(cls)

    @classmethod
    async def all(cls):
        return await cls.query().all()

    @classmethod
    def find(cls, pk=None, id=None):
        search_id = pk if pk is not None else id
        from .query import AsyncFindQuerySet

        return AsyncFindQuerySet(cls, search_id)

    @classmethod
    async def raw_sql(cls, sql: str, *params):
        """Sof SQL orqali asinxron model obyektlarini olish."""
        cls._check_setup()
        records = await cls.db._manager(sql, *params, fetchall=True)
        if not records:
            return []
        return [cls._from_record(r) for r in records]

    @classmethod
    def filter(cls, *args, **kwargs):
        return cls.query().filter(*args, **kwargs)

    @classmethod
    async def first(cls, **kwargs):
        qs = cls.query()
        if kwargs:
            qs = qs.filter(**kwargs)
        return await qs.first()

    @classmethod
    async def last(cls, **kwargs):
        qs = cls.query()
        if kwargs:
            qs = qs.filter(**kwargs)
        return await qs.last()

    @classmethod
    async def get(cls, **kwargs):
        from postgresdb3.exceptions import ObjectDoesNotExist, MultipleObjectsReturned

        results = await cls.filter(**kwargs).limit(2).all()

        if not results:
            raise ObjectDoesNotExist(f"{cls.__name__} obyekti topilmadi")

        if len(results) > 1:
            raise MultipleObjectsReturned(f"Bir nechta {cls.__name__} obyekti topildi")

        return results[0]

    @classmethod
    def order_by(cls, value):
        return cls.query().order_by(value)

    @classmethod
    def limit(cls, value):
        return cls.query().limit(value)

    @classmethod
    def offset(cls, value):
        return cls.query().offset(value)

    @classmethod
    async def paginate(cls, page: int = 1, per_page: int = 10):
        return await cls.query().paginate(page, per_page)

    @classmethod
    def columns(cls, value):
        return cls.query().columns(value)

    @classmethod
    def join(cls, value):
        return cls.query().join(value)

    @classmethod
    def group_by(cls, value):
        return cls.query().group_by(value)

    @classmethod
    def annotate(cls, **kwargs):
        return cls.query().annotate(**kwargs)

    @classmethod
    def exclude(cls, *args, **kwargs):
        return cls.query().exclude(*args, **kwargs)

    @classmethod
    def count(cls):
        return cls.query().count()

    @classmethod
    def values(cls, *fields):
        return cls.query().values(*fields)

    @classmethod
    def values_list(cls, *fields, flat=False):
        return cls.query().values_list(*fields, flat=flat)

    @classmethod
    def exists(cls):
        return cls.query().exists()

    @classmethod
    async def create(cls, **kwargs):
        cls._check_setup()

        kwargs = cls._normalize_kwargs(kwargs)
        kwargs = {
            k: v
            for k, v in kwargs.items()
            if not (cls._fields.get(k) and not cls._fields[k].to_sql())
        }

        for key, field in cls._fields.items():
            if not field.to_sql():
                continue
            if getattr(field, "auto_now", False):
                kwargs[key] = field.get_current_value()
            elif (
                key not in kwargs
                or kwargs[key] is None
                or kwargs[key]
                in ("CURRENT_DATE", "CURRENT_TIME", "CURRENT_TIMESTAMP", "NOW()")
            ):
                if getattr(field, "auto_now_add", False):
                    kwargs[key] = field.get_current_value()
                elif field.default is not None:
                    kwargs[key] = field.get_default_value()

        from postgresdb3.orm.signals import pre_save, post_save

        import inspect

        instance = cls(**kwargs)
        if inspect.iscoroutinefunction(instance.clean):
            await instance.clean()
        else:
            instance.clean()

        if inspect.iscoroutinefunction(instance.before_save):
            await instance.before_save()
        else:
            instance.before_save()

        await pre_save.send_async(sender=cls, instance=instance, created=True)

        columns = ", ".join(kwargs.keys())
        values = tuple(kwargs.values())
        record = await cls.db.insert(cls.table, columns, values, returning="*")

        obj = cls._from_record(record)

        if inspect.iscoroutinefunction(obj.after_save):
            await obj.after_save(created=True)
        else:
            obj.after_save(created=True)

        await post_save.send_async(sender=cls, instance=obj, created=True)
        return obj

    @classmethod
    async def get_or_create(cls, defaults=None, **kwargs):
        return await cls.query().get_or_create(defaults=defaults, **kwargs)

    @classmethod
    async def update_or_create(cls, defaults=None, **kwargs):
        return await cls.query().update_or_create(defaults=defaults, **kwargs)

    @classmethod
    async def bulk_create(cls, instances: list["AsyncModel"]) -> None:
        if not instances:
            return

        columns = [
            k
            for k, f in cls._fields.items()
            if not (f.primary_key and f.sql_type in ("SERIAL", "BIGSERIAL"))
            and f.to_sql()
        ]

        values_list = []
        for inst in instances:
            for col in columns:
                field = cls._fields[col]
                if getattr(field, "auto_now", False):
                    setattr(inst, col, field.get_current_value())
                elif getattr(field, "auto_now_add", False):
                    if getattr(inst, col, None) is None:
                        setattr(inst, col, field.get_current_value())
                elif getattr(inst, col, None) is None and field.default is not None:
                    setattr(inst, col, field.get_default_value())

            val_tuple = tuple(getattr(inst, col, None) for col in columns)
            values_list.append(val_tuple)

        columns_str = ", ".join(columns)
        async with cls.db.transaction():
            await cls.db.insert_many(cls.table, columns_str, values_list)

    @classmethod
    async def bulk_update(
        cls, instances: list["AsyncModel"], fields: list[str]
    ) -> None:
        if not instances or not fields:
            return

        pk_name = cls.get_pk_name()
        auto_now_fields = [
            k for k, f in cls._fields.items() if getattr(f, "auto_now", False)
        ]
        fields_to_update = list(fields)
        for col in auto_now_fields:
            if col not in fields_to_update and col != pk_name:
                fields_to_update.append(col)

        set_clause = ", ".join(
            [f"{f} = ${i+1}" for i, f in enumerate(fields_to_update)]
        )
        sql = f"UPDATE {cls.table} SET {set_clause} WHERE {pk_name} = ${len(fields_to_update)+1}"

        values_list = []
        for inst in instances:
            for col in auto_now_fields:
                val = cls._fields[col].get_current_value()
                setattr(inst, col, val)
            val_tuple = tuple(getattr(inst, f, None) for f in fields_to_update) + (
                getattr(inst, pk_name),
            )
            values_list.append(val_tuple)

        async with cls.db.transaction():
            await cls.db._manager(sql, values_list, commit=True, many=True)

    async def clean(self):
        for field_name, field in self.__class__._fields.items():
            if not field.to_sql():
                continue
            value = getattr(self, field_name, None)
            if hasattr(field, "validate"):
                setattr(self, field_name, field.validate(value))

    async def before_save(self):
        pass

    async def after_save(self, created: bool):
        pass

    async def before_delete(self):
        pass

    async def after_delete(self):
        pass

    async def save(self):
        self.__class__._check_setup()

        pk_name = self.__class__.get_pk_name()
        pk_value = getattr(self, pk_name, None)

        if pk_value is None:
            for field_name, field in self.__class__._fields.items():
                if getattr(field, "auto_now", False):
                    setattr(self, field_name, field.get_current_value())
                elif getattr(field, "auto_now_add", False):
                    if getattr(self, field_name, None) is None:
                        setattr(self, field_name, field.get_current_value())

            await self.clean()
            await self.before_save()

            data = self.to_dict()
            if data.get(pk_name) is None:
                data.pop(pk_name, None)

            created = await self.__class__.create(**data)
            for field_name, field in self.__class__._fields.items():
                if field.to_sql():
                    setattr(self, field_name, getattr(created, field_name, None))
            await self.after_save(created=True)
            return self

        for field_name, field in self.__class__._fields.items():
            if getattr(field, "auto_now", False):
                setattr(self, field_name, field.get_current_value())

        await self.clean()
        await self.before_save()

        data = {}
        for field_name, field in self.__class__._fields.items():
            if field_name == pk_name or not field.to_sql():
                continue
            data[field_name] = getattr(self, field_name, None)

        data = self.__class__._normalize_kwargs(data)
        await self.__class__.db.update_fields(
            self.__class__.table, data, pk_name, pk_value
        )

        await self.after_save(created=False)
        return self

    async def update(self, **kwargs):
        self.__class__._check_setup()

        if not kwargs:
            raise ValueError("Yangilash uchun kamida bitta ustun kerak")

        kwargs = self.__class__._normalize_kwargs(kwargs)

        pk_name = self.__class__.get_pk_name()
        pk_value = getattr(self, pk_name, None)

        if pk_value is None:
            raise ValueError(f"{pk_name} qiymati yo'q, yangilab bo'lmaydi")

        for key, value in kwargs.items():
            if key not in self.__class__._fields:
                raise ValueError(
                    f"{self.__class__.__name__} modelida '{key}' degan ustun yo'q"
                )

            if key == pk_name:
                raise ValueError(f"{pk_name} ustunini yangilab bo'lmaydi")

            if not isinstance(
                value,
                __import__(
                    "postgresdb3.orm.expressions", fromlist=["FExpression"]
                ).FExpression,
            ):
                setattr(self, key, value)

        for key, field in self.__class__._fields.items():
            if getattr(field, "auto_now", False) and key not in kwargs:
                val = field.get_current_value()
                kwargs[key] = val
                setattr(self, key, val)

        await self.__class__.db.update_fields(
            self.__class__.table, kwargs, pk_name, pk_value
        )

        return self

    async def delete(self):
        self.__class__._check_setup()
        await self.before_delete()

        pk_name = self.__class__.get_pk_name()
        pk_value = getattr(self, pk_name, None)

        if pk_value is None:
            raise ValueError(f"{pk_name} qiymati yo'q, o'chirib bo'lmaydi")

        await self.__class__.db.delete(self.__class__.table, pk_name, pk_value)
        await self.after_delete()
        return True
