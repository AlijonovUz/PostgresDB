from .base import Field


class Integer(Field):
    sql_type = "INTEGER"


class BigInteger(Field):
    sql_type = "BIGINT"


class SmallInteger(Field):
    sql_type = "SMALLINT"


class Float(Field):
    sql_type = "REAL"


class Double(Field):
    sql_type = "DOUBLE PRECISION"


class Serial(Field):
    sql_type = "SERIAL"


class BigSerial(Field):
    sql_type = "BIGSERIAL"


class Decimal(Field):

    def __init__(self, verbose_name=None, precision=10, scale=2, max_digits=None, decimal_places=None, **kwargs):
        if max_digits is not None:
            precision = max_digits
        if decimal_places is not None:
            scale = decimal_places
        if isinstance(verbose_name, int):
            scale = precision
            precision = verbose_name
            verbose_name = None
        super().__init__(verbose_name=verbose_name, **kwargs)
        self.precision = precision
        self.scale = scale

    @property
    def sql_type(self):
        return f"NUMERIC({self.precision},{self.scale})"
