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

    def __init__(self, precision=10, scale=2, **kwargs):
        super().__init__(**kwargs)
        self.precision = precision
        self.scale = scale

    @property
    def sql_type(self):
        return f"NUMERIC({self.precision},{self.scale})"