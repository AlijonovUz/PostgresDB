from .fields import Field, ForeignKey, OneToOne, ManyToMany
from .indexes import Index
from .relations import (
    ForeignKeyRelation,
    ReverseRelation,
    AsyncForeignKeyRelation,
    AsyncReverseRelation,
    ManyToManyRelation,
)

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
                if isinstance(value, ForeignKey) and not isinstance(value, ManyToMany):
                    if not key.endswith("_id"):
                        new_key = f"{key}_id"
                        value.name = new_key
                        fields[new_key] = value
                        field_names_to_remove.append(key)
                        continue

                value.name = key
                fields[key] = value
                field_names_to_remove.append(key)

        for key in field_names_to_remove:
            attrs.pop(key)

        attrs["_fields"] = fields

        meta_class = attrs.pop("Meta", None)
        meta_options = {}

        for base in bases:
            base_meta = getattr(base, "_meta_options", None)
            if base_meta:
                for key, val in base_meta.items():
                    if key not in ("abstract", "verbose_name", "verbose_name_plural"):
                        meta_options[key] = val

        if meta_class:
            table_name = getattr(meta_class, "table_name", None) or getattr(
                meta_class, "db_table", None
            )
            if table_name:
                attrs["table"] = table_name

            if hasattr(meta_class, "unique_together"):
                meta_options["unique_together"] = meta_class.unique_together
            if hasattr(meta_class, "index_together"):
                meta_options["index_together"] = meta_class.index_together
            if hasattr(meta_class, "indexes"):
                raw_indexes = meta_class.indexes
                parsed_indexes = []
                for idx in raw_indexes:
                    if isinstance(idx, Index):
                        parsed_indexes.append(idx)
                    elif isinstance(idx, (list, tuple)):
                        parsed_indexes.append(Index(fields=idx))
                    elif isinstance(idx, dict):
                        parsed_indexes.append(Index.from_dict(idx))
                meta_options["indexes"] = parsed_indexes
            if hasattr(meta_class, "ordering"):
                meta_options["ordering"] = meta_class.ordering
            if hasattr(meta_class, "abstract"):
                meta_options["abstract"] = meta_class.abstract
            if hasattr(meta_class, "verbose_name"):
                meta_options["verbose_name"] = meta_class.verbose_name
            if hasattr(meta_class, "verbose_name_plural"):
                meta_options["verbose_name_plural"] = meta_class.verbose_name_plural

        meta_options.setdefault("unique_together", ())
        meta_options.setdefault("index_together", ())
        meta_options.setdefault("indexes", [])
        meta_options.setdefault("ordering", ())

        meta_options.setdefault("abstract", False)
        meta_options.setdefault("verbose_name", name.lower())
        meta_options.setdefault(
            "verbose_name_plural", meta_options["verbose_name"] + "s"
        )

        attrs["_meta_options"] = meta_options

        if not attrs.get("table"):
            attrs["table"] = name.lower() + "s"

        pk_names = [
            fname for fname, f in fields.items() if getattr(f, "primary_key", False)
        ]
        meta_pk = meta_options.get("primary_key") or (
            getattr(meta_class, "primary_key", None) if meta_class else None
        )
        if meta_pk:
            if isinstance(meta_pk, (list, tuple)):
                pk_names = list(meta_pk)
            elif isinstance(meta_pk, str):
                pk_names = [meta_pk]

        if len(pk_names) == 1:
            attrs["pk"] = pk_names[0]
        elif len(pk_names) > 1:
            attrs["pk"] = tuple(pk_names)
            for fname in pk_names:
                if fname in fields:
                    fields[fname].primary_key = True

        cls = super().__new__(mcls, name, bases, attrs)

        is_async_model = any(base.__name__ == "AsyncModel" for base in bases)

        for field_name, field in fields.items():
            if isinstance(field, ForeignKey) and not isinstance(field, ManyToMany):
                relation_name = (
                    field_name[:-3] if field_name.endswith("_id") else field_name
                )

                if not hasattr(cls, relation_name):
                    if is_async_model:
                        setattr(
                            cls,
                            relation_name,
                            AsyncForeignKeyRelation(
                                field_name, field.to, field.to_field
                            ),
                        )
                    else:
                        setattr(
                            cls,
                            relation_name,
                            ForeignKeyRelation(field_name, field.to, field.to_field),
                        )

                is_o2o = isinstance(field, OneToOne)
                related_name = field.related_name or (
                    name.lower() if is_o2o else f"{name.lower()}_set"
                )

                if hasattr(field.to, related_name):
                    raise ValueError(
                        f"'{field.to.__name__}.{related_name}' nomida ziddiyat bor. "
                        f"'{name}.{field_name}' maydoniga boshqa 'related_name' bering."
                    )

                if is_async_model:
                    setattr(
                        field.to,
                        related_name,
                        AsyncReverseRelation(cls, field_name, is_o2o),
                    )
                else:
                    setattr(
                        field.to, related_name, ReverseRelation(cls, field_name, is_o2o)
                    )

            elif isinstance(field, ManyToMany):
                through_table = f"{cls.table}_{field.to.table}"
                source_col = f"{name.lower()}_id"
                target_col = f"{field.to.__name__.lower()}_id"

                setattr(
                    cls,
                    field_name,
                    ManyToManyRelation(
                        field.to, through_table, source_col, target_col, is_async_model
                    ),
                )

                related_name = field.related_name or f"{name.lower()}_set"

                if hasattr(field.to, related_name):
                    raise ValueError(
                        f"'{field.to.__name__}.{related_name}' nomida ziddiyat bor. "
                        f"'{name}.{field_name}' maydoniga boshqa 'related_name' bering."
                    )

                setattr(
                    field.to,
                    related_name,
                    ManyToManyRelation(
                        cls, through_table, target_col, source_col, is_async_model
                    ),
                )

                source_fk = ForeignKey(cls)
                source_fk.name = source_col
                target_fk = ForeignKey(field.to)
                target_fk.name = target_col
                attrs_dict = {
                    "table": through_table,
                    source_col: source_fk,
                    target_col: target_fk,
                    "is_through_table": True,
                }

                if not hasattr(cls, "_m2m_throughs"):
                    cls._m2m_throughs = []

                M2MThrough = type(
                    f"{cls.__name__}{field.to.__name__}Through",
                    (bases[0] if bases else object,),
                    attrs_dict,
                )
                M2MThrough.get_pk_name = classmethod(lambda cls: "id")
                cls._m2m_throughs.append(M2MThrough)

        is_abstract = attrs.get("_meta_options", {}).get("abstract", False)
        if (
            name not in ("Model", "AsyncModel")
            and not attrs.get("is_through_table")
            and not is_abstract
        ):
            model_registry.append(cls)
            if hasattr(cls, "_m2m_throughs"):
                for m2m in cls._m2m_throughs:
                    if m2m not in model_registry:
                        model_registry.append(m2m)

        return cls
