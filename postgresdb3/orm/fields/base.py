from postgresdb3.orm.validators import ValidationError


class Field:

    sql_type = ""

    def __init__(
        self,
        verbose_name=None,
        *,
        nullable=False,
        primary_key=False,
        unique=False,
        default=None,
        index=False,
        validators=None,
    ):
        self.verbose_name = verbose_name
        self.nullable = nullable
        self.primary_key = primary_key
        self.unique = unique
        self.default = default
        self.index = index
        self.validators = validators or []
        self.name = None

    def validate(self, value):
        if value is None:
            if not self.nullable and not self.primary_key and self.default is None:
                field_desc = self.verbose_name or f"'{self.name}'"
                raise ValidationError(
                    f"{field_desc} ustuni bo'sh (NULL) bo'lishi mumkin emas."
                )
            return value

        for validator in self.validators:
            validator(value)

        return value

    def to_sql(self):

        parts = [self.name, self.sql_type]

        if self.primary_key:
            parts.append("PRIMARY KEY")

        if self.unique:
            parts.append("UNIQUE")

        if not self.nullable and not self.primary_key:
            parts.append("NOT NULL")

        if self.default is not None:
            parts.append(f"DEFAULT {self.default}")

        return " ".join(parts)
