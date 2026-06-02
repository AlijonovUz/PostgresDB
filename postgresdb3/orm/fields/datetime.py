from .base import Field


class Date(Field):
    sql_type = "DATE"
    
    def __init__(self, auto_now_add=False, **kwargs):
        if auto_now_add:
            kwargs["default"] = "CURRENT_DATE"
        super().__init__(**kwargs)


class Time(Field):
    sql_type = "TIME"


class Timestamp(Field):
    sql_type = "TIMESTAMP"
    
    def __init__(self, auto_now_add=False, **kwargs):
        if auto_now_add:
            kwargs["default"] = "CURRENT_TIMESTAMP"
        super().__init__(**kwargs)


class Timestamptz(Field):
    sql_type = "TIMESTAMPTZ"

    def __init__(self, auto_now_add=False, **kwargs):
        if auto_now_add:
            kwargs["default"] = "CURRENT_TIMESTAMP"
        super().__init__(**kwargs)
