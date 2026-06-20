from .fields import Field, ForeignKey, OneToOneField, ManyToManyField
from .relations import ForeignKeyRelation, ReverseRelation, AsyncForeignKeyRelation, AsyncReverseRelation, ManyToManyRelation


model_registry = []

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
        
        meta_class = attrs.pop("Meta", None)
        meta_options = {}
        if meta_class:
            meta_options["unique_together"] = getattr(meta_class, "unique_together", ())
            meta_options["index_together"] = getattr(meta_class, "index_together", ())
            meta_options["abstract"] = getattr(meta_class, "abstract", False)
        attrs["_meta_options"] = meta_options

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
            if isinstance(field, ForeignKey) and not isinstance(field, ManyToManyField):
                relation_name = field_name[:-3] if field_name.endswith("_id") else field_name

                if not hasattr(cls, relation_name):
                    if is_async_model:
                        setattr(cls, relation_name, AsyncForeignKeyRelation(field_name, field.to))
                    else:
                        setattr(cls, relation_name, ForeignKeyRelation(field_name, field.to))

                related_name = field.related_name or f"{name.lower()}_set"
                is_o2o = isinstance(field, OneToOneField)

                if hasattr(field.to, related_name):
                    raise ValueError(f"'{field.to.__name__}.{related_name}' nomida ziddiyat bor. "
                                     f"'{name}.{field_name}' maydoniga boshqa 'related_name' bering.")
                                     
                if is_async_model:
                    setattr(field.to, related_name, AsyncReverseRelation(cls, field_name, is_o2o))
                else:
                    setattr(field.to, related_name, ReverseRelation(cls, field_name, is_o2o))
            
            elif isinstance(field, ManyToManyField):
                through_table = f"{cls.table}_{field.to.table}"
                source_col = f"{name.lower()}_id"
                target_col = f"{field.to.__name__.lower()}_id"
                
                                  
                setattr(cls, field_name, ManyToManyRelation(
                    field.to, through_table, source_col, target_col, is_async_model
                ))
                
                                  
                related_name = field.related_name or f"{name.lower()}_set"
                
                if hasattr(field.to, related_name):
                    raise ValueError(f"'{field.to.__name__}.{related_name}' nomida ziddiyat bor. "
                                     f"'{name}.{field_name}' maydoniga boshqa 'related_name' bering.")
                                     
                setattr(field.to, related_name, ManyToManyRelation(
                    cls, through_table, target_col, source_col, is_async_model
                ))
                
                                                             
                source_fk = ForeignKey(cls)
                source_fk.name = source_col
                target_fk = ForeignKey(field.to)
                target_fk.name = target_col
                attrs_dict = {
                    "table": through_table,
                    source_col: source_fk,
                    target_col: target_fk,
                    "is_through_table": True
                }
                
                                                                                                     
                if not hasattr(cls, "_m2m_throughs"):
                    cls._m2m_throughs = []
                
                M2MThrough = type(f"{cls.__name__}{field.to.__name__}Through", (bases[0] if bases else object,), attrs_dict)
                M2MThrough.get_pk_name = classmethod(lambda cls: "id")
                cls._m2m_throughs.append(M2MThrough)

        is_abstract = attrs.get("_meta_options", {}).get("abstract", False)
        if name not in ("Model", "AsyncModel") and not attrs.get("is_through_table") and not is_abstract:
            model_registry.append(cls)
            if hasattr(cls, "_m2m_throughs"):
                for m2m in cls._m2m_throughs:
                    if m2m not in model_registry:
                        model_registry.append(m2m)

        return cls
