from .fields import Field, ForeignKey
from .relations import ForeignKeyRelation, ReverseRelation, AsyncForeignKeyRelation


class ModelMeta(type):
    def __new__(mcls, name, bases, attrs):
        if name in ("Model", "AsyncModel"):
            return super().__new__(mcls, name, bases, attrs)

        fields = {}

        for base in bases:
            base_fields = getattr(base, "_fields", {})
            if base_fields:
                fields.update(base_fields)

        field_names_to_remove = []

        for key, value in attrs.items():
            if isinstance(value, Field):
                value.name = key
                fields[key] = value
                field_names_to_remove.append(key)

        for key in field_names_to_remove:
            attrs.pop(key)

        attrs["_fields"] = fields

        if not attrs.get("table"):
            attrs["table"] = name.lower() + "s"

        pk_name = None
        for field_name, field in fields.items():
            if getattr(field, "primary_key", False):
                pk_name = field_name
                break

        if pk_name:
            attrs["pk"] = pk_name

        cls = super().__new__(mcls, name, bases, attrs)

        is_async_model = any(base.__name__ == "AsyncModel" for base in bases)

        for field_name, field in fields.items():
            if isinstance(field, ForeignKey):
                relation_name = field_name[:-3] if field_name.endswith("_id") else field_name

                if not hasattr(cls, relation_name):
                    if is_async_model:
                        setattr(cls, relation_name, AsyncForeignKeyRelation(field_name, field.to))
                    else:
                        setattr(cls, relation_name, ForeignKeyRelation(field_name, field.to))

                related_name = field.related_name or f"{name.lower()}_set"

                if not hasattr(field.to, related_name):
                    setattr(field.to, related_name, ReverseRelation(cls, field_name))

        return cls
