from .base import Field

class String(Field):

    def __init__(self, length=255, **kwargs):
        super().__init__(**kwargs)
        self.length = length

    @property
    def sql_type(self):
        return f"VARCHAR({self.length})"


class Text(Field):
    sql_type = "TEXT"