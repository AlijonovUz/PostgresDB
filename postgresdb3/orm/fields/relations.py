from .base import Field

class ForeignKey(Field):

    def __init__(self, model, **kwargs):
        super().__init__(**kwargs)
        self.model = model

    @property
    def sql_type(self):
        return "INTEGER"

    def to_sql(self):
        base = super().to_sql()
        table = self.model.table
        return f"{base} REFERENCES {table}(id)"