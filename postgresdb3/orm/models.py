from .base import BaseModel
from .meta import ModelMeta


class Model(BaseModel, metaclass=ModelMeta):
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
    def filter(cls, **kwargs):
        return cls.query().filter(**kwargs)

    @classmethod
    def first(cls, **kwargs):
        qs = cls.query()
        if kwargs:
            qs = qs.filter(**kwargs)
        return qs.first()

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
            raise ValueError("Ma'lumot qo'shish uchun kamida bitta ustun kerak")

        for key in kwargs:
            if key not in cls._fields:
                raise ValueError(f"{cls.__name__} modelida '{key}' degan ustun yo'q")

        columns = []
        values = []

        for key, value in kwargs.items():
            columns.append(key)
            values.append(value)

        cls.db.insert(cls.table, ", ".join(columns), tuple(values))

        pk_name = cls.get_pk_name()

        if pk_name in kwargs and kwargs[pk_name] is not None:
            return cls.find(kwargs[pk_name])

        return cls.first(**kwargs)

    @classmethod
    def create_table(cls):
        cls._check_setup()

        columns_sql = []
        has_primary_key = False

        for field_name, field in cls._fields.items():
            if getattr(field, "primary_key", False):
                has_primary_key = True
            columns_sql.append(field.to_sql())

        if not has_primary_key:
            columns_sql.insert(0, f"{cls.get_pk_name()} SERIAL PRIMARY KEY")

        cls.db.create(cls.table, ", ".join(columns_sql))

    @classmethod
    def drop_table(cls, cascade=False):
        cls._check_setup()
        cls.db.drop(cls.table, cascade=cascade)

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

        for field_name in self.__class__._fields:
            if field_name == pk_name:
                continue

            value = getattr(self, field_name, None)
            self.__class__.db.update(self.__class__.table, field_name, value, pk_name, pk_value)

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
    def filter(cls, **kwargs):
        return cls.query().filter(**kwargs)

    @classmethod
    async def first(cls, **kwargs):
        qs = cls.query()
        if kwargs:
            qs = qs.filter(**kwargs)
        return await qs.first()

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
    def exclude(cls, **kwargs):
        return cls.query().exclude(**kwargs)

    @classmethod
    def count(cls):
        return cls.query().count()

    @classmethod
    def exists(cls):
        return cls.query().exists()

    @classmethod
    async def create(cls, **kwargs):
        cls._check_setup()

        if not kwargs:
            raise ValueError("Ma'lumot qo'shish uchun kamida bitta ustun kerak")

        for key in kwargs:
            if key not in cls._fields:
                raise ValueError(f"{cls.__name__} modelida '{key}' degan ustun yo'q")

        columns = []
        values = []

        for key, value in kwargs.items():
            columns.append(key)
            values.append(value)

        await cls.db.insert(cls.table, ", ".join(columns), values)

        pk_name = cls.get_pk_name()

        if pk_name in kwargs and kwargs[pk_name] is not None:
            return await cls.find(kwargs[pk_name])

        return await cls.first(**kwargs)

    @classmethod
    async def create_table(cls):
        cls._check_setup()

        columns_sql = []
        has_primary_key = False

        for field_name, field in cls._fields.items():
            if getattr(field, "primary_key", False):
                has_primary_key = True
            columns_sql.append(field.to_sql())

        if not has_primary_key:
            columns_sql.insert(0, f"{cls.get_pk_name()} SERIAL PRIMARY KEY")

        await cls.db.create(cls.table, ", ".join(columns_sql))

    @classmethod
    async def drop_table(cls, cascade=False):
        cls._check_setup()
        await cls.db.drop(cls.table, cascade=cascade)

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

        for field_name in self.__class__._fields:
            if field_name == pk_name:
                continue

            value = getattr(self, field_name, None)
            await self.__class__.db.update(self.__class__.table, field_name, value, pk_name, pk_value)

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
