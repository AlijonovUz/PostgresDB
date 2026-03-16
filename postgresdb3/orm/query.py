class QuerySet:
    def __init__(self, model):
        self.model = model
        self._where = None
        self._exclude = None
        self._order_by = None
        self._limit = None
        self._offset = None
        self._columns = "*"
        self._join = None
        self._group_by = None

    def _clone(self):
        qs = self.__class__(self.model)
        qs._where = dict(self._where) if self._where else None
        qs._exclude = dict(self._exclude) if self._exclude else None
        qs._order_by = self._order_by
        qs._limit = self._limit
        qs._offset = self._offset
        qs._columns = self._columns
        qs._join = self._join
        qs._group_by = self._group_by
        return qs

    def update(self, **kwargs):
        self.model._check_setup()

        if not kwargs:
            raise ValueError("Yangilash uchun kamida bitta ustun kerak")

        pk_name = self.model.get_pk_name()

        for key in kwargs:
            if key not in self.model._fields:
                raise ValueError(f"{self.model.__name__} modelida '{key}' degan ustun yo'q")

            if key == pk_name:
                raise ValueError(f"{pk_name} ustunini yangilab bo'lmaydi")

        where = self._build_where()

        if not where:
            raise ValueError("Yangilash uchun shart berilishi kerak")

        return self.model.db.update_where(
            self.model.table,
            kwargs,
            where
        )

    def delete(self):
        self.model._check_setup()

        where = self._build_where()

        if not where:
            raise ValueError("O'chirish uchun shart berilishi kerak")

        return self.model.db.delete_where(
            self.model.table,
            where
        )

    def filter(self, **kwargs):
        qs = self._clone()

        if not kwargs:
            return qs

        if qs._where is None:
            qs._where = {}

        qs._where.update(kwargs)
        return qs

    def exclude(self, **kwargs):
        qs = self._clone()

        if not kwargs:
            return qs

        if qs._exclude is None:
            qs._exclude = {}

        qs._exclude.update(kwargs)
        return qs

    def order_by(self, value):
        qs = self._clone()
        qs._order_by = value
        return qs

    def limit(self, value):
        qs = self._clone()
        qs._limit = value
        return qs

    def offset(self, value):
        qs = self._clone()
        qs._offset = value
        return qs

    def columns(self, value):
        qs = self._clone()
        qs._columns = value
        return qs

    def join(self, value):
        qs = self._clone()
        qs._join = value
        return qs

    def group_by(self, value):
        qs = self._clone()
        qs._group_by = value
        return qs

    def all(self):
        where = self._build_where()
        records = self.model.db.select(
            self.model.table,
            columns=self._columns,
            where=where,
            join=self._join,
            group_by=self._group_by,
            order_by=self._order_by,
            limit=self._limit,
            offset=self._offset,
        )
        return self.model._from_records(records)

    def first(self):
        where = self._build_where()
        record = self.model.db.select(
            self.model.table,
            columns=self._columns,
            where=where,
            join=self._join,
            group_by=self._group_by,
            order_by=self._order_by,
            limit=1 if self._limit is None else self._limit,
            offset=self._offset,
            fetchone=True,
        )
        return self.model._from_record(record)

    def last(self):
        pk_name = self.model.get_pk_name()

        order = self._order_by
        if not order:
            order = f"-{pk_name}"
        elif isinstance(order, str):
            if order.startswith("-"):
                order = order[1:]
            else:
                order = f"-{order}"

        where = self._build_where()

        record = self.model.db.select(
            self.model.table,
            columns=self._columns,
            where=where,
            join=self._join,
            group_by=self._group_by,
            order_by=order,
            limit=1,
            offset=self._offset,
            fetchone=True,
        )

        return self.model._from_record(record)

    def count(self):
        where = self._build_where()
        record = self.model.db.select(
            self.model.table,
            columns="COUNT(*) AS count",
            where=where,
            join=self._join,
            group_by=self._group_by,
            order_by=None,
            limit=None,
            offset=None,
            fetchone=True,
        )

        if record is None:
            return 0

        if isinstance(record, dict):
            return record.get("count", 0)

        if hasattr(record, "_asdict"):
            return record._asdict().get("count", 0)

        if hasattr(record, "items"):
            return dict(record).get("count", 0)

        if isinstance(record, (tuple, list)):
            return record[0] if record else 0

        value = getattr(record, "count", 0)
        if callable(value):
            return 0

        return value

    def exists(self):
        where = self._build_where()
        return self.model.db.exists_where(
            self.model.table,
            where=where,
            join=self._join,
            group_by=self._group_by,
        )

    def _build_where(self):
        if self._where and self._exclude:
            where = dict(self._where)
            for key, value in self._exclude.items():
                where[f"{key}__not"] = value
            return where

        if self._where:
            return dict(self._where)

        if self._exclude:
            where = {}
            for key, value in self._exclude.items():
                where[f"{key}__not"] = value
            return where

        return None


class AsyncQuerySet:
    def __init__(self, model):
        self.model = model
        self._where = None
        self._exclude = None
        self._order_by = None
        self._limit = None
        self._offset = None
        self._columns = "*"
        self._join = None
        self._group_by = None

    def _clone(self):
        qs = self.__class__(self.model)
        qs._where = dict(self._where) if self._where else None
        qs._exclude = dict(self._exclude) if self._exclude else None
        qs._order_by = self._order_by
        qs._limit = self._limit
        qs._offset = self._offset
        qs._columns = self._columns
        qs._join = self._join
        qs._group_by = self._group_by
        return qs

    async def update(self, **kwargs):
        self.model._check_setup()

        if not kwargs:
            raise ValueError("Yangilash uchun kamida bitta ustun kerak")

        pk_name = self.model.get_pk_name()

        for key in kwargs:
            if key not in self.model._fields:
                raise ValueError(f"{self.model.__name__} modelida '{key}' degan ustun yo'q")

            if key == pk_name:
                raise ValueError(f"{pk_name} ustunini yangilab bo'lmaydi")

        where = self._build_where()

        if not where:
            raise ValueError("Yangilash uchun shart berilishi kerak")

        return await self.model.db.update_where(
            self.model.table,
            kwargs,
            where
        )

    async def delete(self):
        self.model._check_setup()

        where = self._build_where()

        if not where:
            raise ValueError("O'chirish uchun shart berilishi kerak")

        return await self.model.db.delete_where(
            self.model.table,
            where
        )

    def filter(self, **kwargs):
        qs = self._clone()

        if not kwargs:
            return qs

        if qs._where is None:
            qs._where = {}

        qs._where.update(kwargs)
        return qs

    def exclude(self, **kwargs):
        qs = self._clone()

        if not kwargs:
            return qs

        if qs._exclude is None:
            qs._exclude = {}

        qs._exclude.update(kwargs)
        return qs

    def order_by(self, value):
        qs = self._clone()
        qs._order_by = value
        return qs

    def limit(self, value):
        qs = self._clone()
        qs._limit = value
        return qs

    def offset(self, value):
        qs = self._clone()
        qs._offset = value
        return qs

    def columns(self, value):
        qs = self._clone()
        qs._columns = value
        return qs

    def join(self, value):
        qs = self._clone()
        qs._join = value
        return qs

    def group_by(self, value):
        qs = self._clone()
        qs._group_by = value
        return qs

    async def all(self):
        where = self._build_where()
        records = await self.model.db.select(
            self.model.table,
            columns=self._columns,
            where=where,
            join=self._join,
            group_by=self._group_by,
            order_by=self._order_by,
            limit=self._limit,
            offset=self._offset,
            fetchone=False,
        )
        return self.model._from_records(records)

    async def first(self):
        where = self._build_where()
        record = await self.model.db.select(
            self.model.table,
            columns=self._columns,
            where=where,
            join=self._join,
            group_by=self._group_by,
            order_by=self._order_by,
            limit=1 if self._limit is None else self._limit,
            offset=self._offset,
            fetchone=True,
        )
        return self.model._from_record(record)

    async def last(self):
        pk_name = self.model.get_pk_name()

        order = self._order_by
        if not order:
            order = f"-{pk_name}"
        elif isinstance(order, str):
            if order.startswith("-"):
                order = order[1:]
            else:
                order = f"-{order}"

        where = self._build_where()

        record = await self.model.db.select(
            self.model.table,
            columns=self._columns,
            where=where,
            join=self._join,
            group_by=self._group_by,
            order_by=order,
            limit=1,
            offset=self._offset,
            fetchone=True,
        )

        return self.model._from_record(record)

    async def count(self):
        where = self._build_where()
        record = await self.model.db.select(
            self.model.table,
            columns="COUNT(*) AS count",
            where=where,
            join=self._join,
            group_by=self._group_by,
            order_by=None,
            limit=None,
            offset=None,
            fetchone=True,
        )

        if record is None:
            return 0

        if isinstance(record, dict):
            return record.get("count", 0)

        if hasattr(record, "_asdict"):
            return record._asdict().get("count", 0)

        if hasattr(record, "items"):
            return dict(record).get("count", 0)

        if isinstance(record, (tuple, list)):
            return record[0] if record else 0

        value = getattr(record, "count", 0)
        if callable(value):
            return 0

        return value

    async def exists(self):
        where = self._build_where()
        return await self.model.db.exists_where(
            self.model.table,
            where=where,
            join=self._join,
            group_by=self._group_by,
        )

    def _build_where(self):
        if self._where and self._exclude:
            where = dict(self._where)
            for key, value in self._exclude.items():
                where[f"{key}__not"] = value
            return where

        if self._where:
            return dict(self._where)

        if self._exclude:
            where = {}
            for key, value in self._exclude.items():
                where[f"{key}__not"] = value
            return where

        return None
