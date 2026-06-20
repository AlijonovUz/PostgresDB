class BaseModel:
    db = None
    table = None
    pk = "id"
    _fields = {}

    def __init__(self, **kwargs):
        for field_name, field in self._fields.items():
            if field_name in kwargs:
                val = kwargs[field_name]
            else:
                val = getattr(field, "default", None)
                
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

    def __repr__(self):
        pk_name = self.get_pk_name()
        pk_val = getattr(self, pk_name, None)
        return f"<{self.__class__.__name__}: {pk_name}={pk_val}>"

    def __str__(self):
        return repr(self)

    def __iter__(self):
        for field in self._fields:
            yield field, getattr(self, field, None)

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
        for name, field in cls._fields.items():
            if getattr(field, "primary_key", False):
                return name
        return cls.pk

    def to_dict(self):
        return {
            field_name: getattr(self, field_name, None)
            for field_name in self._fields
        }

    def __repr__(self):
        fields = ", ".join(
            f"{name}={getattr(self, name, None)!r}"
            for name in self._fields
        )
        return f"<{self.__class__.__name__} {fields}>"