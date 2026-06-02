class Q:
    """
    Q obyekti ma'lumotlar bazasida murakkab AND va OR shartlarini yozish uchun ishlatiladi.
    Misol uchun: Q(age__gt=18) | Q(name="Ali")
    """
    def __init__(self, **kwargs):
        self.conditions = kwargs
        self.children = []
        self.connector = "AND"

    def _combine(self, other, connector):
        if not isinstance(other, Q):
            raise TypeError("Q obyektini faqat boshqa Q obyekti bilan birlashtirish mumkin")
        obj = Q()
        obj.connector = connector
        obj.children = [self, other]
        return obj

    def __or__(self, other):
        return self._combine(other, "OR")

    def __and__(self, other):
        return self._combine(other, "AND")

    def __invert__(self):
        obj = Q()
        obj.connector = "NOT"
        obj.children = [self]
        return obj


class F:
    """
    F obyekti ma'lumotlar bazasining o'zidagi ustun qiymatlariga murojaat qilish uchun ishlatiladi.
    Masalan: Model.update(views=F("views") + 1)
    """
    def __init__(self, name):
        self.name = name

    def __add__(self, other):
        return FExpression(self.name, "+", other)

    def __sub__(self, other):
        return FExpression(self.name, "-", other)

    def __mul__(self, other):
        return FExpression(self.name, "*", other)

    def __truediv__(self, other):
        return FExpression(self.name, "/", other)


class FExpression:
    def __init__(self, name, operator, value):
        self.name = name
        self.operator = operator
        self.value = value

class Aggregate:
    function = ""
    def __init__(self, field):
        self.field = field

    def to_sql(self):
        return f"{self.function}({self.field})"

class Sum(Aggregate):
    function = "SUM"

class Avg(Aggregate):
    function = "AVG"

class Min(Aggregate):
    function = "MIN"

class Max(Aggregate):
    function = "MAX"

class Count(Aggregate):
    function = "COUNT"
