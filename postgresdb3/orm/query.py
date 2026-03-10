class QuerySet:
    def __init__(self, model):
        self.model = model
        self._where = None
        self._order_by = None
        self._limit = None
        self._offset = None
        self._columns = "*"

    def filter(self, **kwargs):
        self._where = kwargs if kwargs else None
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

    def all(self):
        records = self.model.db.select(
            self.model.table,
            columns=self._columns,
            where=self._where,
            order_by=self._order_by,
            limit=self._limit,
            offset=self._offset,
        )
        return self.model._from_records(records)

    def first(self):
        record = self.model.db.select(
            self.model.table,
            columns=self._columns,
            where=self._where,
            order_by=self._order_by,
            limit=1 if self._limit is None else self._limit,
            offset=self._offset,
            fetchone=True,
        )
        return self.model._from_record(record)


class AsyncQuerySet:
    def __init__(self, model):
        self.model = model
        self._where = None
        self._order_by = None
        self._limit = None
        self._offset = None
        self._columns = "*"
        self._join = None
        self._group_by = None

    def filter(self, **kwargs):
        self._where = kwargs if kwargs else None
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
        records = await self.model.db.select(
            self.model.table,
            columns=self._columns,
            where=self._where,
            join=self._join,
            group_by=self._group_by,
            order_by=self._order_by,
            limit=self._limit,
            offset=self._offset,
            fetchone=False
        )
        return self.model._from_records(records)

    async def first(self):
        record = await self.model.db.select(
            self.model.table,
            columns=self._columns,
            where=self._where,
            join=self._join,
            group_by=self._group_by,
            order_by=self._order_by,
            limit=1 if self._limit is None else self._limit,
            offset=self._offset,
            fetchone=True
        )
        return self.model._from_record(record)
