from .base import Field


class Date(Field):
    sql_type = "DATE"


class Time(Field):
    sql_type = "TIME"


class Timestamp(Field):
    sql_type = "TIMESTAMP"


class Timestamptz(Field):
    sql_type = "TIMESTAMPTZ"
