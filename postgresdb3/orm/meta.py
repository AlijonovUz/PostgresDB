import re
from .fields import Field, ForeignKey, OneToOne, ManyToMany
from .indexes import Index
from .relations import (
    ForeignKeyRelation,
    ReverseRelation,
    AsyncForeignKeyRelation,
    AsyncReverseRelation,
    ManyToManyRelation,
)
from . import registry as _registry_module

model_registry = []


# Invariant (birlik va ko'plik bir xil) yoki allaqachon birlik bo'lgan jadval nomlari
_SINGULARIZE_EXCEPTIONS = frozenset({
    "series", "species", "news", "means", "offspring",
    "information", "data", "media", "agenda", "criteria",
})


def _singularize(table_name: str) -> str:
    """
    Ko'plik jadval nomini birlik shaklga o'tkazadi — M2M ustun nomi uchun.

    Misollar:
        test_posts   → test_post
        categories   → category
        statuses     → status      (ko'plik)
        status       → status      (allaqachon birlik — us qo'shimchasi)
        analysis     → analysis    (allaqachon birlik — is qo'shimchasi)
        news         → news        (invariant)
        series       → series      (invariant)
        boxes        → box
        matches      → match
    """
    # 1. To'liq istisno so'zlar
    if table_name in _SINGULARIZE_EXCEPTIONS:
        return table_name

    # 2. Compound jadval nomining oxirgi qismini tekshirish (test_series → series)
    last_part = table_name.rsplit("_", 1)[-1]
    if last_part in _SINGULARIZE_EXCEPTIONS:
        return table_name

    # 3. Ko'plik qoidalari
    if table_name.endswith("ies"):
        # categories → category, countries → country
        # LEKIN: series → "sery" noto'g'ri — yuqorida ushlanadi
        return table_name[:-3] + "y"
    elif table_name.endswith(("ses", "xes", "zes", "ches", "shes")):
        # statuses → status, boxes → box, matches → match
        return table_name[:-2]
    elif (
        table_name.endswith("s")
        and not table_name.endswith(("ss", "us", "is", "ews", "ous", "ias"))
    ):
        # posts → post, authors → author
        # LEKIN: status(us), analysis(is), news(ews), bonus(us) — saqlanadi
        return table_name[:-1]

    # 4. O'zgarmaydi
    return table_name



def _to_table_name(class_name: str) -> str:
    """
    Model sinf nomini jadval nomiga o'tkazadi (CamelCase → snake_case).
    Ko'plik qo'shimchasi qo'shilmaydi — har qanday tilda ishlaydi.

    Misollar:
        Post        → post
        UserProfile → user_profile
        Category    → category
        Mahsulot    → mahsulot        (o'zbekcha)
        Kategoriya  → kategoriya      (o'zbekcha)
    """
    # CamelCase → snake_case: UserProfile → user_profile
    s = re.sub(r'(?<=[a-z0-9])(?=[A-Z])', '_', class_name)
    return s.lower()


def _setup_fk_relation(cls, field_name, field, is_async_model, name):
    """
    ForeignKey / OneToOne uchun forward + reverse relation descriptor'larini
    modelga bog'laydi. 'field.to' tayyor klass bo'lishi shart.
    """
    to_model = field.to  # LookupError ko'tarishi mumkin — qo'yib beramiz

    relation_name = (
        field_name[:-3] if field_name.endswith("_id") else field_name
    )

    if not hasattr(cls, relation_name):
        if is_async_model:
            setattr(
                cls,
                relation_name,
                AsyncForeignKeyRelation(field_name, to_model, field.to_field),
            )
        else:
            setattr(
                cls,
                relation_name,
                ForeignKeyRelation(field_name, to_model, field.to_field),
            )

    is_o2o = isinstance(field, OneToOne)
    related_name = field.related_name or (
        name.lower() if is_o2o else f"{name.lower()}_set"
    )

    # Lazy resolve holatida descriptor allaqachon o'rnatilgan bo'lishi mumkin
    existing_attr = getattr(to_model, related_name, None)
    is_already_reverse = isinstance(
        existing_attr, (ReverseRelation, AsyncReverseRelation)
    )
    if existing_attr is not None and not is_already_reverse:
        raise ValueError(
            f"'{to_model.__name__}.{related_name}' nomida ziddiyat bor. "
            f"'{name}.{field_name}' maydoniga boshqa 'related_name' bering."
        )

    if not is_already_reverse:
        if is_async_model:
            setattr(
                to_model,
                related_name,
                AsyncReverseRelation(cls, field_name, is_o2o),
            )
        else:
            setattr(
                to_model, related_name, ReverseRelation(cls, field_name, is_o2o)
            )


def _setup_m2m_relation(cls, field_name, field, is_async_model, name, bases):
    """
    ManyToMany uchun through jadval + relation descriptor'larini ulaydi.
    'field.to' tayyor klass bo'lishi shart.
    """
    to_model = field.to  # LookupError ko'tarishi mumkin

    through_table = f"{cls.table}_{to_model.table}"
    # Ustun nomlari jadval nomidan olinadi (sinf nomidan emas) — izchillik uchun.
    # test_posts → test_post_id, categories → category_id, authors → author_id
    source_col = f"{_singularize(cls.table)}_id"
    target_col = f"{_singularize(to_model.table)}_id"

    setattr(
        cls,
        field_name,
        ManyToManyRelation(
            to_model, through_table, source_col, target_col, is_async_model
        ),
    )

    related_name = field.related_name or f"{name.lower()}_set"

    # Agar bu lazy resolve bo'lsa (string) — descriptor allaqachon o'rnatilgan bo'lishi mumkin
    existing = getattr(to_model, related_name, None)
    if existing is not None and not isinstance(existing, ManyToManyRelation):
        raise ValueError(
            f"'{to_model.__name__}.{related_name}' nomida ziddiyat bor. "
            f"'{name}.{field_name}' maydoniga boshqa 'related_name' bering."
        )

    if not isinstance(existing, ManyToManyRelation):
        setattr(
            to_model,
            related_name,
            ManyToManyRelation(
                cls, through_table, target_col, source_col, is_async_model
            ),
        )

    source_fk = ForeignKey(cls)
    source_fk.name = source_col
    target_fk = ForeignKey(to_model)
    target_fk.name = target_col
    attrs_dict = {
        "table": through_table,
        source_col: source_fk,
        target_col: target_fk,
        "is_through_table": True,
    }

    if not hasattr(cls, "_m2m_throughs"):
        cls._m2m_throughs = []

    # Rekursiyani oldini olish: Through jadval yaratish paytida
    # ModelMeta.__new__ -> resolve_pending -> bu callback qayta chaqirilmasligi uchun
    _registry_module._in_m2m_setup = True
    try:
        M2MThrough = type(
            f"{cls.__name__}{to_model.__name__}Through",
            (bases[0] if bases else object,),
            attrs_dict,
        )
    finally:
        _registry_module._in_m2m_setup = False

    M2MThrough.get_pk_name = classmethod(lambda c: "id")
    cls._m2m_throughs.append(M2MThrough)

    # Through jadvalini ham global registry'ga qo'shish
    if M2MThrough not in model_registry:
        model_registry.append(M2MThrough)


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
            "verbose_name_plural", meta_options["verbose_name"]
        )

        attrs["_meta_options"] = meta_options

        if not attrs.get("table"):
            attrs["table"] = _to_table_name(name)

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

        # --- Model registry'ga qo'shish ---
        _registry_module.register(cls)

        is_async_model = any(base.__name__ == "AsyncModel" for base in bases)

        for field_name, field in fields.items():
            if isinstance(field, ForeignKey) and not isinstance(field, ManyToMany):
                # String reference bo'lsa — lazy yechish
                if not field.is_resolved():
                    _original_ref = field._to_ref

                    def _make_fk_callback(_field_name, _field, _cls, _is_async, _name, _bases):
                        def _callback(resolved_model):
                            _setup_fk_relation(_cls, _field_name, _field, _is_async, _name)
                        return _callback

                    _registry_module.add_pending(
                        field,
                        cls,
                        _make_fk_callback(field_name, field, cls, is_async_model, name, bases),
                    )
                else:
                    # Klass bevosita berilgan — darhol sozlash
                    _setup_fk_relation(cls, field_name, field, is_async_model, name)

            elif isinstance(field, ManyToMany):
                # String reference bo'lsa — lazy yechish
                if not field.is_resolved():
                    def _make_m2m_callback(_field_name, _field, _cls, _is_async, _name, _bases):
                        def _callback(resolved_model):
                            _setup_m2m_relation(_cls, _field_name, _field, _is_async, _name, _bases)
                        return _callback

                    _registry_module.add_pending(
                        field,
                        cls,
                        _make_m2m_callback(field_name, field, cls, is_async_model, name, bases),
                    )
                else:
                    # Klass bevosita berilgan — darhol sozlash
                    _setup_m2m_relation(cls, field_name, field, is_async_model, name, bases)

        # Har yangi model qo'shilganda pending'larni resolve qilishga urinish
        _registry_module.resolve_pending()

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
