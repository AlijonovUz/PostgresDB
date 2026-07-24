from .base import Field

CASCADE = "CASCADE"
SET_NULL = "SET NULL"
RESTRICT = "RESTRICT"
SET_DEFAULT = "SET DEFAULT"
DO_NOTHING = "NO ACTION"


class ForeignKey(Field):
    def __init__(
        self, to, to_field=None, related_name=None, on_delete=CASCADE, **kwargs
    ):
        super().__init__(**kwargs)

        if isinstance(to, str):
            self._to_ref = to
            self._resolved_to = None
        else:
            self._to_ref = None
            self._resolved_to = to

        self.to_field = to_field
        self.related_name = related_name
        self.on_delete = on_delete

    @property
    def to(self):
        """
        Bog'langan model klassini qaytaradi.
        Agar hali string holatida bo'lsa, registry'dan topishga urinadi.
        """
        if self._resolved_to is not None:
            return self._resolved_to

        if self._to_ref is not None:
            from . import registry
            resolved = registry.resolve(self._to_ref)
            if resolved is not None:
                self._resolved_to = resolved
                return resolved
            raise LookupError(
                f"ForeignKey('{self._to_ref}') — bu nomdagi model hali "
                f"ro'yxatga olinmagan yoki import qilinmagan.\n"
                f"Maslahat: shu model faylini import qilib qo'ying, "
                f"yoki resolve_all() ni chaqiring."
            )
        return None

    @to.setter
    def to(self, value):
        """Bevosita o'rnatish imkonini beradi (orqaga moslik uchun)."""
        if isinstance(value, str):
            self._to_ref = value
            self._resolved_to = None
        else:
            self._to_ref = None
            self._resolved_to = value

    def is_resolved(self) -> bool:
        """True bo'lsa — model allaqachon resolve bo'lgan."""
        return self._resolved_to is not None

    @property
    def sql_type(self):
        return "INTEGER"

    def get_to_field(self):
        if self.to_field:
            return self.to_field
        return self.to.get_pk_name()

    def to_sql(self):
        base = super().to_sql()
        table = self.to.table
        to_field = self.get_to_field()

        sql = f"{base} REFERENCES {table}({to_field})"

        if self.on_delete:
            sql += f" ON DELETE {self.on_delete}"

        return sql


class OneToOne(ForeignKey):
    """
    Yakkama-yakka (One-to-One) bog'lanish.
    ForeignKey bilan bir xil, faqat UNIQUE qoida qo'shiladi.
    """

    def __init__(
        self, to, to_field=None, related_name=None, on_delete="CASCADE", **kwargs
    ):
        kwargs["unique"] = True
        super().__init__(to, to_field, related_name, on_delete, **kwargs)


class ManyToMany(Field):
    """
    Ko'pga-ko'p (Many-to-Many) bog'lanish.
    O'rtada avtomatik bog'lovchi jadval yaratiladi.
    """

    def __init__(self, to, related_name=None, verbose_name=None):
        super().__init__(verbose_name=verbose_name)
        # 'to' string yoki klass bo'lishi mumkin
        if isinstance(to, str):
            self._to_ref = to
            self._resolved_to = None
        else:
            self._to_ref = None
            self._resolved_to = to

        self.related_name = related_name
        self.through = None

    @property
    def to(self):
        """
        Bog'langan model klassini qaytaradi.
        Agar hali string holatida bo'lsa, registry'dan topishga urinadi.
        """
        if self._resolved_to is not None:
            return self._resolved_to

        if self._to_ref is not None:
            from . import registry
            resolved = registry.resolve(self._to_ref)
            if resolved is not None:
                self._resolved_to = resolved
                return resolved
            raise LookupError(
                f"ManyToMany('{self._to_ref}') — bu nomdagi model hali "
                f"ro'yxatga olinmagan yoki import qilinmagan.\n"
                f"Maslahat: shu model faylini import qilib qo'ying."
            )
        return None

    @to.setter
    def to(self, value):
        """Bevosita o'rnatish imkonini beradi (orqaga moslik uchun)."""
        if isinstance(value, str):
            self._to_ref = value
            self._resolved_to = None
        else:
            self._to_ref = None
            self._resolved_to = value

    def is_resolved(self) -> bool:
        """True bo'lsa — model allaqachon resolve bo'lgan."""
        return self._resolved_to is not None

    @property
    def sql_type(self):
        return ""

    def to_sql(self):
        return ""
