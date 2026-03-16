class ForeignKeyRelation:
    def __init__(self, field_name, related_model):
        self.field_name = field_name
        self.related_model = related_model

    def __get__(self, instance, owner):
        if instance is None:
            return self

        fk_value = getattr(instance, self.field_name, None)
        if fk_value is None:
            return None

        return self.related_model.find(fk_value)


class ReverseRelation:
    def __init__(self, related_model, fk_name):
        self.related_model = related_model
        self.fk_name = fk_name

    def __get__(self, instance, owner):
        if instance is None:
            return self

        pk_name = instance.__class__.get_pk_name()
        pk_value = getattr(instance, pk_name, None)

        return self.related_model.filter(**{self.fk_name: pk_value})

class AsyncForeignKeyRelation:
    def __init__(self, field_name, related_model):
        self.field_name = field_name
        self.related_model = related_model

    def __get__(self, instance, owner):
        if instance is None:
            return self

        fk_value = getattr(instance, self.field_name, None)
        if fk_value is None:
            return None

        return self.related_model.find(fk_value)