from .base import Field


class Date(Field):
    sql_type = "DATE"

    def __init__(self, verbose_name=None, auto_now=False, auto_now_add=False, **kwargs):
        if isinstance(verbose_name, bool):
            auto_now_add = verbose_name
            verbose_name = None
        self.auto_now = auto_now
        self.auto_now_add = auto_now_add
        if (auto_now or auto_now_add) and "default" not in kwargs:
            kwargs["default"] = "CURRENT_DATE"
        super().__init__(verbose_name=verbose_name, **kwargs)

    def get_current_value(self):
        import datetime

        return datetime.date.today()


class Time(Field):
    sql_type = "TIME"

    def __init__(self, verbose_name=None, auto_now=False, auto_now_add=False, **kwargs):
        if isinstance(verbose_name, bool):
            auto_now_add = verbose_name
            verbose_name = None
        self.auto_now = auto_now
        self.auto_now_add = auto_now_add
        if (auto_now or auto_now_add) and "default" not in kwargs:
            kwargs["default"] = "CURRENT_TIME"
        super().__init__(verbose_name=verbose_name, **kwargs)

    def get_current_value(self):
        import datetime

        return datetime.datetime.now().time()


class Timestamp(Field):
    sql_type = "TIMESTAMP"

    def __init__(self, verbose_name=None, auto_now=False, auto_now_add=False, **kwargs):
        if isinstance(verbose_name, bool):
            auto_now_add = verbose_name
            verbose_name = None
        self.auto_now = auto_now
        self.auto_now_add = auto_now_add
        if (auto_now or auto_now_add) and "default" not in kwargs:
            kwargs["default"] = "CURRENT_TIMESTAMP"
        super().__init__(verbose_name=verbose_name, **kwargs)

    def get_current_value(self):
        import datetime

        return datetime.datetime.now()


class Timestamptz(Field):
    sql_type = "TIMESTAMPTZ"

    def __init__(self, verbose_name=None, auto_now=False, auto_now_add=False, **kwargs):
        if isinstance(verbose_name, bool):
            auto_now_add = verbose_name
            verbose_name = None
        self.auto_now = auto_now
        self.auto_now_add = auto_now_add
        if (auto_now or auto_now_add) and "default" not in kwargs:
            kwargs["default"] = "CURRENT_TIMESTAMP"
        super().__init__(verbose_name=verbose_name, **kwargs)

    def get_current_value(self):
        import datetime

        return datetime.datetime.now(datetime.timezone.utc)
