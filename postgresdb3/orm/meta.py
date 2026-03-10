from .fields import Field


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

        return super().__new__(mcls, name, bases, attrs)