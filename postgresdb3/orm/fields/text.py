from .base import Field

class String(Field):

    def __init__(self, length=255, **kwargs):
        super().__init__(**kwargs)
        self.length = length

    @property
    def sql_type(self):
        return f"VARCHAR({self.length})"

    def validate(self, value):
        value = super().validate(value)
        if value is not None:
            if not isinstance(value, str):
                raise ValueError(f"'{self.name}' ustuni satr (string) bo'lishi kerak.")
            if len(value) > self.length:
                raise ValueError(f"'{self.name}' ustuniga maksimal {self.length} ta belgi kiritish mumkin (hozir: {len(value)}).")
        return value

class Text(Field):
    sql_type = "TEXT"