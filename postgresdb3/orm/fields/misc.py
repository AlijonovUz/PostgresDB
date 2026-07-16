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

    def __init__(self, verbose_name=None, base_type=None, **kwargs):
        if verbose_name is not None and not isinstance(verbose_name, str):
            base_type = verbose_name
            verbose_name = None
        super().__init__(verbose_name=verbose_name, **kwargs)
        self.base_type = base_type

    @property
    def sql_type(self):
        return f"{self.base_type}[]"
