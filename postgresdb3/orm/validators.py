from __future__ import annotations
import re
from typing import Any, Callable


class ValidationError(Exception):
    """Validation xatoligi yuz berganda chaqiriladigan xatolik klassi."""

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class MinValueValidator:
    """Qiymatning minimal miqdorini tekshirish uchun validator."""

    def __init__(self, limit_value: Any, message: str = None) -> None:
        self.limit_value = limit_value
        self.message = (
            message or f"Qiymat {limit_value} dan kichik bo'lishi mumkin emas."
        )

    def __call__(self, value: Any) -> None:
        if value is not None and value < self.limit_value:
            raise ValidationError(self.message)


class MaxValueValidator:
    """Qiymatning maksimal miqdorini tekshirish uchun validator."""

    def __init__(self, limit_value: Any, message: str = None) -> None:
        self.limit_value = limit_value
        self.message = (
            message or f"Qiymat {limit_value} dan katta bo'lishi mumkin emas."
        )

    def __call__(self, value: Any) -> None:
        if value is not None and value > self.limit_value:
            raise ValidationError(self.message)


class MinLengthValidator:
    """Satr yoki massivning minimal uzunligini tekshirish uchun validator."""

    def __init__(self, limit_value: int, message: str = None) -> None:
        self.limit_value = limit_value
        self.message = (
            message or f"Uzunlik {limit_value} tadan kam bo'lishi mumkin emas."
        )

    def __call__(self, value: Any) -> None:
        if value is not None and len(value) < self.limit_value:
            raise ValidationError(self.message)


class MaxLengthValidator:
    """Satr yoki massivning maksimal uzunligini tekshirish uchun validator."""

    def __init__(self, limit_value: int, message: str = None) -> None:
        self.limit_value = limit_value
        self.message = (
            message or f"Uzunlik {limit_value} tadan ko'p bo'lishi mumkin emas."
        )

    def __call__(self, value: Any) -> None:
        if value is not None and len(value) > self.limit_value:
            raise ValidationError(self.message)


class RegexValidator:
    """Berilgan muntazam ifoda (regex) shabloniga mosligini tekshirish uchun validator."""

    def __init__(self, regex: str | re.Pattern, message: str = None) -> None:
        self.regex = re.compile(regex) if isinstance(regex, str) else regex
        self.message = message or "Qiymat berilgan shablonga mos kelmadi."

    def __call__(self, value: Any) -> None:
        if value is not None and not self.regex.search(str(value)):
            raise ValidationError(self.message)


class EmailValidator(RegexValidator):
    """Elektron pochta manzilini tekshirish uchun validator."""

    def __init__(self, message: str = None) -> None:
        email_regex = re.compile(
            r"(^[-!#$%&\'*+/=?^_`{}|~0-9A-Z]+(\.[-!#$%&\'*+/=?^_`{}|~0-9A-Z]+)*"
            r'|^"([\001-\010\013\014\016-\037!#-\[\]-\177]|\\[\001-\011\013\014\016-\077!#-\[\]-\177])*"'
            r")@(?:[A-Z0-9-]+\.)+[A-Z]{2,6}$",
            re.IGNORECASE,
        )
        super().__init__(email_regex, message or "Noto'g'ri elektron pochta manzili.")
