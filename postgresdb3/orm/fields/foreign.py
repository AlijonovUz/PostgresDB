from .base import Field


class ForeignKey(Field):
    def __init__(self, to, to_field=None, related_name=None, on_delete="CASCADE", **kwargs):
        super().__init__(**kwargs)
        self.to = to
        self.to_field = to_field
        self.related_name = related_name
        self.on_delete = on_delete

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


class OneToOneField(ForeignKey):
    """
    Yakkama-yakka (One-to-One) bog'lanish.
    ForeignKey bilan bir xil, faqat UNIQUE qoida qo'shiladi.
    """
    def __init__(self, to, to_field=None, related_name=None, on_delete="CASCADE", **kwargs):
        kwargs["unique"] = True
        super().__init__(to, to_field, related_name, on_delete, **kwargs)


class ManyToManyField(Field):
    """
    Ko'pga-ko'p (Many-to-Many) bog'lanish.
    O'rtada avtomatik bog'lovchi jadval yaratiladi.
    """
    def __init__(self, to, related_name=None):
        super().__init__()
        self.to = to
        self.related_name = related_name
        self.through = None                                  

    @property
    def sql_type(self):
                                               
        return ""
    
    def to_sql(self):
        return ""
