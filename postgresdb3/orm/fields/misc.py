from .base import Field


class Boolean(Field):
    sql_type = "BOOLEAN"


class JSON(Field):
    sql_type = "JSON"


class JSONB(Field):
    sql_type = "JSONB"


class UUID(Field):
    sql_type = "UUID"


class Array(Field):

    def __init__(self, base_type, **kwargs):
        super().__init__(**kwargs)
        self.base_type = base_type

    @property
    def sql_type(self):
        return f"{self.base_type}[]"