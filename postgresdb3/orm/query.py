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

    def filter(self, **kwargs):
        if not kwargs:
            return self

        if self._where is None:
            self._where = {}

        self._where.update(kwargs)
        return self

    def exclude(self, **kwargs):
        if not kwargs:
            return self

        if self._exclude is None:
            self._exclude = {}

        self._exclude.update(kwargs)
        return self

    def order_by(self, value):
        self._order_by = value
        return self

    def limit(self, value):
        self._limit = value
        return self

    def offset(self, value):
        self._offset = value
        return self

    def columns(self, value):
        self._columns = value
        return self

    def join(self, value):
        self._join = value
        return self

    def group_by(self, value):
        self._group_by = value
        return self

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
        return self.count() > 0

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

    def filter(self, **kwargs):
        if not kwargs:
            return self

        if self._where is None:
            self._where = {}

        self._where.update(kwargs)
        return self

    def exclude(self, **kwargs):
        if not kwargs:
            return self

        if self._exclude is None:
            self._exclude = {}

        self._exclude.update(kwargs)
        return self

    def order_by(self, value):
        self._order_by = value
        return self

    def limit(self, value):
        self._limit = value
        return self

    def offset(self, value):
        self._offset = value
        return self

    def columns(self, value):
        self._columns = value
        return self

    def join(self, value):
        self._join = value
        return self

    def group_by(self, value):
        self._group_by = value
        return self

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
            fetchone=False
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
            fetchone=True
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
            fetchone=True
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
        return await self.count() > 0

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
