from .base import Field
from postgresdb3.orm.validators import ValidationError


class String(Field):

    def __init__(self, verbose_name=None, length=255, **kwargs):
        # Agar birinchi argument butun son bo'lsa, demak uzunlik (length) berilgan
        if isinstance(verbose_name, int):
            length = verbose_name
            verbose_name = None
        super().__init__(verbose_name=verbose_name, **kwargs)
        self.length = length

    @property
    def sql_type(self):
        return f"VARCHAR({self.length})"

    def validate(self, value):
        value = super().validate(value)
        if value is not None:
            field_desc = self.verbose_name or f"'{self.name}'"
            if not isinstance(value, str):
                raise ValidationError(
                    f"{field_desc} ustuni satr (string) bo'lishi kerak."
                )
            if len(value) > self.length:
                raise ValidationError(
                    f"{field_desc} ustuniga maksimal {self.length} ta belgi kiritish mumkin (hozir: {len(value)})."
                )
        return value


class Text(Field):
    sql_type = "TEXT"
