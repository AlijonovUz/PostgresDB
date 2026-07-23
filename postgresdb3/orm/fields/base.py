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

    def get_default_value(self):
        if hasattr(self, "get_current_value") and (
            getattr(self, "auto_now", False) or getattr(self, "auto_now_add", False)
        ):
            return self.get_current_value()
        if callable(self.default):
            return self.default()
        if self.default in (
            "CURRENT_DATE",
            "CURRENT_TIME",
            "CURRENT_TIMESTAMP",
            "NOW()",
        ):
            if hasattr(self, "get_current_value"):
                return self.get_current_value()
        return self.default

    def get_sql_default(self):
        if self.default is None:
            return None

        if callable(self.default):
            import uuid
            import datetime

            if self.default == uuid.uuid4:
                return "gen_random_uuid()"
            elif self.default in (datetime.datetime.now, datetime.datetime.utcnow):
                return "CURRENT_TIMESTAMP"
            elif self.default == datetime.date.today:
                return "CURRENT_DATE"
            return None

        if isinstance(self.default, bool):
            return str(self.default)
        elif isinstance(self.default, (int, float)):
            return str(self.default)
        elif isinstance(self.default, str):
            val_upper = self.default.upper()
            if val_upper in (
                "CURRENT_TIMESTAMP",
                "CURRENT_DATE",
                "CURRENT_TIME",
                "NOW()",
                "LOCALTIME",
                "GEN_RANDOM_UUID()",
            ):
                return val_upper
            if self.default.startswith("'") and self.default.endswith("'"):
                return self.default
            return f"'{self.default}'"

        return str(self.default)

    def validate(self, value):
        if value is None:
            if (
                not self.nullable
                and not self.primary_key
                and self.default is None
                and not getattr(self, "auto_now", False)
                and not getattr(self, "auto_now_add", False)
            ):
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

        sql_default = self.get_sql_default()
        if sql_default is not None:
            parts.append(f"DEFAULT {sql_default}")

        return " ".join(parts)
