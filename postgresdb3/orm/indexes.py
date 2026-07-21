class Index:
    """
    Django-style database Index representation for PostgresDB3.
    
    Usage:
        Index(fields=['first_name', 'last_name'], name='idx_user_name')
        Index(fields=['-created_at'], name='idx_created_desc')
        Index(fields=['email'], unique=True)
        Index(fields=['data'], using='gin')
        Index(fields=['status'], condition="status = 'active'")
        Index(fields=['title'], include=['author_id'])
    """
    def __init__(
        self,
        *expressions,
        fields=(),
        name=None,
        unique=False,
        using=None,
        condition=None,
        include=(),
    ):
        if expressions and not fields:
            fields = expressions
        elif isinstance(fields, str):
            fields = [fields]

        self.fields = [str(f) for f in fields]
        self.name = name
        self.unique = bool(unique)
        self.using = using
        self.condition = str(condition) if condition else None

        if isinstance(include, str):
            self.include = [include]
        else:
            self.include = [str(i) for i in include] if include else []

    def get_name(self, table_name: str) -> str:
        if self.name:
            return self.name
        clean_fields = [f.lstrip("-") for f in self.fields]
        prefix = "uniq_idx" if self.unique else "idx"
        return f"{prefix}_{table_name}_{'_'.join(clean_fields)}"

    def to_sql(self, table_name: str) -> str:
        idx_name = self.get_name(table_name)
        unique_str = "UNIQUE " if self.unique else ""
        using_str = f" USING {self.using}" if self.using else ""

        formatted_fields = []
        for field in self.fields:
            if field.startswith("-"):
                formatted_fields.append(f"{field[1:]} DESC")
            else:
                formatted_fields.append(field)

        cols_str = ", ".join(formatted_fields)
        include_str = f" INCLUDE ({', '.join(self.include)})" if self.include else ""
        where_str = f" WHERE {self.condition}" if self.condition else ""

        return f"CREATE {unique_str}INDEX IF NOT EXISTS {idx_name} ON {table_name}{using_str} ({cols_str}){include_str}{where_str};"

    def to_drop_sql(self, table_name: str) -> str:
        idx_name = self.get_name(table_name)
        return f"DROP INDEX IF EXISTS {idx_name};"

    def to_dict(self) -> dict:
        return {
            "fields": self.fields,
            "name": self.name,
            "unique": self.unique,
            "using": self.using,
            "condition": self.condition,
            "include": self.include,
        }

    @classmethod
    def from_dict(cls, data: dict):
        if not isinstance(data, dict):
            return data
        return cls(
            fields=data.get("fields", ()),
            name=data.get("name"),
            unique=data.get("unique", False),
            using=data.get("using"),
            condition=data.get("condition"),
            include=data.get("include", ()),
        )

    def __eq__(self, other):
        if isinstance(other, Index):
            return (
                self.fields == other.fields
                and self.name == other.name
                and self.unique == other.unique
                and self.using == other.using
                and self.condition == other.condition
                and self.include == other.include
            )
        elif isinstance(other, dict):
            return self.to_dict() == other
        return False

    def __repr__(self):
        return f"Index(fields={self.fields}, name={self.name!r}, unique={self.unique})"
