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
    def find(cls, pk):
        return cls.query().filter(**{cls.get_pk_name(): pk}).first()

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
        results = cls.filter(**kwargs).limit(2).all()

        if not results:
            raise ValueError("Obyekt topilmadi")

        if len(results) > 1:
            raise ValueError("Bir nechta obyekt topildi")

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
    def columns(cls, value):
        return cls.query().columns(value)

    @classmethod
    def join(cls, value):
        return cls.query().join(value)

    @classmethod
    def group_by(cls, value):
        return cls.query().group_by(value)

    @classmethod
    def exclude(cls, **kwargs):
        return cls.query().exclude(**kwargs)

    @classmethod
    def count(cls):
        return cls.query().count()

    @classmethod
    def exists(cls):
        return cls.query().exists()

    @classmethod
    def create(cls, **kwargs):
        cls._check_setup()

        if not kwargs:
            for key, field in cls._fields.items():
                if key not in kwargs and field.default is not None:
                    kwargs[key] = field.default

        if not kwargs:
            raise ValueError("Create requires at least one field to insert")

        columns = ", ".join(kwargs.keys())
        values = tuple(kwargs.values())
        
        record = cls.db.insert(cls.table, columns, values, returning="*")
        return cls._from_record(record)
        
    @classmethod
    def bulk_create(cls, instances: list["Model"]) -> None:
        if not instances:
            return
            
        columns = [k for k, f in cls._fields.items() if not (f.primary_key and f.sql_type in ("SERIAL", "BIGSERIAL"))]
        
        values_list = []
        for inst in instances:
            for col in columns:
                if getattr(inst, col, None) is None and cls._fields[col].default is not None:
                    setattr(inst, col, cls._fields[col].default)
                    
            val_tuple = tuple(getattr(inst, col, None) for col in columns)
            values_list.append(val_tuple)
            
        columns_str = ", ".join(columns)
        cls.db.insert_many(cls.table, columns_str, values_list)

    @classmethod
    def bulk_update(cls, instances: list["Model"], fields: list[str]) -> None:
        if not instances or not fields:
            return
            
        pk_name = cls.get_pk_name()
        set_clause = ", ".join([f"{f} = %s" for f in fields])
        sql = f"UPDATE {cls.table} SET {set_clause} WHERE {pk_name} = %s"
        
        values_list = []
        for inst in instances:
            val_tuple = tuple(getattr(inst, f, None) for f in fields) + (getattr(inst, pk_name),)
            values_list.append(val_tuple)
            
        cls.db._manager(sql, values_list, commit=True, many=True)

    def save(self):
        self.__class__._check_setup()

        pk_name = self.__class__.get_pk_name()
        pk_value = getattr(self, pk_name, None)

        if pk_value is None:
            data = self.to_dict()
            if data.get(pk_name) is None:
                data.pop(pk_name, None)

            created = self.__class__.create(**data)
            for field_name in self.__class__._fields:
                setattr(self, field_name, getattr(created, field_name, None))
            return self

        data = {}
        for field_name in self.__class__._fields:
            if field_name == pk_name:
                continue
            data[field_name] = getattr(self, field_name, None)

        self.__class__.db.update_fields(
            self.__class__.table,
            data,
            pk_name,
            pk_value
        )

        return self

    def update(self, **kwargs):
        self.__class__._check_setup()

        if not kwargs:
            raise ValueError("Yangilash uchun kamida bitta ustun kerak")

        pk_name = self.__class__.get_pk_name()
        pk_value = getattr(self, pk_name, None)

        if pk_value is None:
            raise ValueError(f"{pk_name} qiymati yo'q, yangilab bo'lmaydi")

        for key, value in kwargs.items():
            if key not in self.__class__._fields:
                raise ValueError(f"{self.__class__.__name__} modelida '{key}' degan ustun yo'q")

            if key == pk_name:
                raise ValueError(f"{pk_name} ustunini yangilab bo'lmaydi")

            setattr(self, key, value)
            self.__class__.db.update(self.__class__.table, key, value, pk_name, pk_value)

        return self

    def delete(self):
        self.__class__._check_setup()

        pk_name = self.__class__.get_pk_name()
        pk_value = getattr(self, pk_name, None)

        if pk_value is None:
            raise ValueError(f"{pk_name} qiymati yo'q, o'chirib bo'lmaydi")

        self.__class__.db.delete(self.__class__.table, pk_name, pk_value)
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
    async def find(cls, pk):
        return await cls.query().filter(**{cls.get_pk_name(): pk}).first()

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
        results = await cls.filter(**kwargs).limit(2).all()

        if not results:
            raise ValueError("Obyekt topilmadi")

        if len(results) > 1:
            raise ValueError("Bir nechta obyekt topildi")

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
    def columns(cls, value):
        return cls.query().columns(value)

    @classmethod
    def join(cls, value):
        return cls.query().join(value)

    @classmethod
    def group_by(cls, value):
        return cls.query().group_by(value)

    @classmethod
    def exclude(cls, *args, **kwargs):
        return cls.query().exclude(*args, **kwargs)

    @classmethod
    def count(cls):
        return cls.query().count()

    @classmethod
    def exists(cls):
        return cls.query().exists()

    @classmethod
    async def create(cls, **kwargs):
        cls._check_setup()

        for key, field in cls._fields.items():
            if key not in kwargs and field.default is not None:
                kwargs[key] = field.default

        if not kwargs:
            raise ValueError("Create requires at least one field to insert")

        columns = ", ".join(kwargs.keys())
        values = tuple(kwargs.values())
        record = await cls.db.insert(cls.table, columns, values, returning="*")
        
        return cls._from_record(record)
        
    @classmethod
    async def bulk_create(cls, instances: list["AsyncModel"]) -> None:
        if not instances:
            return
            
        columns = [k for k, f in cls._fields.items() if not (f.primary_key and f.sql_type in ("SERIAL", "BIGSERIAL"))]
        
        values_list = []
        for inst in instances:
            for col in columns:
                if getattr(inst, col, None) is None and cls._fields[col].default is not None:
                    setattr(inst, col, cls._fields[col].default)
                    
            val_tuple = tuple(getattr(inst, col, None) for col in columns)
            values_list.append(val_tuple)
            
        columns_str = ", ".join(columns)
        await cls.db.insert_many(cls.table, columns_str, values_list)

    @classmethod
    async def bulk_update(cls, instances: list["AsyncModel"], fields: list[str]) -> None:
        if not instances or not fields:
            return
            
        pk_name = cls.get_pk_name()
        set_clause = ", ".join([f"{f} = ${i+1}" for i, f in enumerate(fields)])
        sql = f"UPDATE {cls.table} SET {set_clause} WHERE {pk_name} = ${len(fields)+1}"
        
        values_list = []
        for inst in instances:
            val_tuple = tuple(getattr(inst, f, None) for f in fields) + (getattr(inst, pk_name),)
            values_list.append(val_tuple)
            
        await cls.db._manager(sql, values_list, commit=True, many=True)

    async def save(self):
        self.__class__._check_setup()

        pk_name = self.__class__.get_pk_name()
        pk_value = getattr(self, pk_name, None)

        if pk_value is None:
            data = self.to_dict()
            if data.get(pk_name) is None:
                data.pop(pk_name, None)

            created = await self.__class__.create(**data)
            for field_name in self.__class__._fields:
                setattr(self, field_name, getattr(created, field_name, None))
            return self

        data = {}
        for field_name in self.__class__._fields:
            if field_name == pk_name:
                continue
            data[field_name] = getattr(self, field_name, None)

        await self.__class__.db.update_fields(
            self.__class__.table,
            data,
            pk_name,
            pk_value
        )

        return self

    async def update(self, **kwargs):
        self.__class__._check_setup()

        if not kwargs:
            raise ValueError("Yangilash uchun kamida bitta ustun kerak")

        pk_name = self.__class__.get_pk_name()
        pk_value = getattr(self, pk_name, None)

        if pk_value is None:
            raise ValueError(f"{pk_name} qiymati yo'q, yangilab bo'lmaydi")

        for key, value in kwargs.items():
            if key not in self.__class__._fields:
                raise ValueError(f"{self.__class__.__name__} modelida '{key}' degan ustun yo'q")

            if key == pk_name:
                raise ValueError(f"{pk_name} ustunini yangilab bo'lmaydi")

            setattr(self, key, value)
            await self.__class__.db.update(self.__class__.table, key, value, pk_name, pk_value)

        return self

    async def delete(self):
        self.__class__._check_setup()

        pk_name = self.__class__.get_pk_name()
        pk_value = getattr(self, pk_name, None)

        if pk_value is None:
            raise ValueError(f"{pk_name} qiymati yo'q, o'chirib bo'lmaydi")

        await self.__class__.db.delete(self.__class__.table, pk_name, pk_value)
        return True
