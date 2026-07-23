from __future__ import annotations


class BaseModel:
    db = None
    table = None
    pk = "id"
    _fields = {}

    def __init__(self, **kwargs):
        for field_name, field in self._fields.items():
            if not field.to_sql():
                continue
            if field_name in kwargs:
                val = kwargs[field_name]
            else:
                val = field.get_default_value()

            try:
                setattr(self, field_name, val)
            except AttributeError:
                pass

        for key, value in kwargs.items():
            if key not in self._fields:
                try:
                    setattr(self, key, value)
                except AttributeError:
                    pass


    def __iter__(self):
        for field_name, field in self._fields.items():
            if field.to_sql():
                yield field_name, getattr(self, field_name, None)

    def __getitem__(self, item):
        return getattr(self, item)

    @classmethod
    def _check_setup(cls):
        if cls.db is None:
            raise ValueError(f"{cls.__name__}.db belgilanmagan")

        if cls.table is None:
            raise ValueError(f"{cls.__name__}.table belgilanmagan")

        if not isinstance(cls._fields, dict):
            raise ValueError(f"{cls.__name__}._fields noto‘g‘ri")

    @classmethod
    def _from_record(cls, record):
        if record is None:
            return None

        if isinstance(record, dict):
            return cls(**record)

        if hasattr(record, "_asdict"):
            return cls(**record._asdict())

        if hasattr(record, "items"):
            return cls(**dict(record))

        if isinstance(record, (tuple, list)):
            data = dict(zip(cls._fields.keys(), record))
            return cls(**data)

        data = {}
        for field_name in cls._fields:
            try:
                if hasattr(record, field_name):
                    data[field_name] = getattr(record, field_name)
                else:
                    data[field_name] = record[field_name]
            except Exception:
                pass

        return cls(**data)

    @classmethod
    def _from_records(cls, records):
        if not records:
            return []
        return [cls._from_record(record) for record in records]

    @classmethod
    def get_fields(cls):
        return cls._fields

    @classmethod
    def get_pk_name(cls):
        if hasattr(cls, "pk"):
            return cls.pk
        pks = [
            name
            for name, field in cls._fields.items()
            if getattr(field, "primary_key", False)
        ]
        if len(pks) == 1:
            return pks[0]
        elif len(pks) > 1:
            return tuple(pks)
        return "id"

    def get_pk_value(self):
        pk_name = self.get_pk_name()
        if isinstance(pk_name, (list, tuple)):
            return tuple(getattr(self, k, None) for k in pk_name)
        return getattr(self, pk_name, None)

    @classmethod
    def _normalize_kwargs(cls, kwargs):
        normalized = {}
        for k, v in kwargs.items():
            if hasattr(cls, k):
                desc = getattr(cls, k)
                if hasattr(desc, "field_name"):
                    k = desc.field_name
            if hasattr(v, "get_pk_name"):
                v = getattr(v, v.get_pk_name(), v)
            normalized[k] = v
        return normalized

    def to_dict(self):
        return {
            field_name: getattr(self, field_name, None)
            for field_name, field in self._fields.items()
            if field.to_sql()
        }

    def __repr__(self):
        fields = ", ".join(
            f"{name}={getattr(self, name, None)!r}"
            for name, field in self._fields.items()
            if field.to_sql()
        )
        return f"<{self.__class__.__name__} {fields}>"

    @classmethod
    def to_pydantic(cls, name=None, exclude=None, include=None, optional=None):
        """
        Model ma'lumotlari, tiplari va cheklovlaridan kelib chiqib dynamic Pydantic BaseModel yaratadi.
        FastAPI bilan ishlashda response_model va request body uchun xizmat qiladi.

        :param name: Yaratiladigan Pydantic modelining nomi.
        :param exclude: Sxemadan chiqarib tashlanadigan maydonlar ro'yxati.
        :param include: Sxemaga kiritiladigan maydonlar ro'yxati.
        :param optional: Ixtiyoriy (Optional/None) qilinadigan maydonlar ro'yxati (list/tuple),
                         yoki True bo'lsa barcha maydonlar ixtiyoriy qilinadi (PATCH so'rovlari uchun).
        """
        try:
            import pydantic
            from pydantic import create_model, Field as PydanticField
        except ImportError:
            raise ImportError(
                "Pydantic o'rnatilmagan. Iltimos 'pip install pydantic' buyrug'i orqali o'rnating."
            )

        import typing

        model_name = name or f"{cls.__name__}Pydantic"
        fields_dict = {}
        exclude_set = set(exclude or [])

        include_set = set(include) if include is not None else None
        optional_set = set(optional) if isinstance(optional, (list, tuple, set)) else None
        make_all_optional = optional is True or optional == "__all__"

        for field_name, field in cls._fields.items():
            if not field.to_sql():
                continue
            if include_set is not None and field_name not in include_set:
                continue
            if field_name in exclude_set:
                continue

            py_type = cls._get_field_python_type(field)

            field_kwargs = {}
            if getattr(field, "length", None):
                field_kwargs["max_length"] = field.length

            is_optional = (
                field.nullable
                or make_all_optional
                or (optional_set is not None and field_name in optional_set)
            )

            default_val = ...
            if is_optional:
                py_type = typing.Optional[py_type]
                default_val = None

            if not make_all_optional and getattr(field, "default", None) is not None:
                if callable(field.default):
                    field_kwargs["default_factory"] = field.default
                    default_val = None
                elif field.default not in (
                    "CURRENT_DATE",
                    "CURRENT_TIME",
                    "CURRENT_TIMESTAMP",
                    "NOW()",
                ):
                    default_val = field.default

            if getattr(field, "validators", None):
                try:
                    from pydantic import AfterValidator

                    for v_func in field.validators:

                        def _make_validator(fn):
                            def _validate(val):
                                if val is not None:
                                    try:
                                        fn(val)
                                    except Exception as err:
                                        raise ValueError(
                                            getattr(err, "message", str(err))
                                        )
                                return val

                            return _validate

                        py_type = typing.Annotated[
                            py_type, AfterValidator(_make_validator(v_func))
                        ]
                except Exception:
                    pass

            if "default_factory" in field_kwargs:
                pydantic_field_obj = PydanticField(**field_kwargs)
            else:
                pydantic_field_obj = PydanticField(default=default_val, **field_kwargs)

            fields_dict[field_name] = (
                py_type,
                pydantic_field_obj,
            )

        pk_name = cls.get_pk_name()
        if (
            isinstance(pk_name, str)
            and pk_name not in cls._fields
            and pk_name not in exclude_set
            and (include_set is None or pk_name in include_set)
        ):
            pk_type = typing.Optional[int]
            if make_all_optional or (optional_set and pk_name in optional_set):
                pk_default = None
            else:
                pk_default = None
            pk_field_obj = PydanticField(default=pk_default)
            fields_dict = {pk_name: (pk_type, pk_field_obj), **fields_dict}

        return create_model(model_name, **fields_dict)

    @classmethod
    def _get_field_python_type(cls, field):
        import datetime
        import uuid
        import typing

        field_cls_name = field.__class__.__name__

        if field_cls_name in (
            "Integer",
            "BigInteger",
            "SmallInteger",
            "Serial",
            "BigSerial",
            "ForeignKey",
            "OneToOne",
        ):
            return int
        elif field_cls_name in ("Float", "Double"):
            return float
        elif field_cls_name in ("Decimal",):
            import decimal

            return decimal.Decimal
        elif field_cls_name in ("String", "Text"):
            return str
        elif field_cls_name in ("Boolean",):
            return bool
        elif field_cls_name in ("Timestamp", "Timestamptz"):
            return datetime.datetime
        elif field_cls_name in ("Date",):
            return datetime.date
        elif field_cls_name in ("Time",):
            return datetime.time
        elif field_cls_name in ("UUID",):
            return uuid.UUID
        elif field_cls_name in ("Point",):
            return typing.Tuple[float, float]
        elif field_cls_name in ("JSON", "JSONB"):
            return typing.Dict[str, typing.Any]
        elif field_cls_name in ("Array",):
            return typing.List[typing.Any]

        return typing.Any
