from __future__ import annotations

import sys
from typing import TYPE_CHECKING, Dict, List, Type

if TYPE_CHECKING:
    pass

_registry: Dict[str, "type"] = {}

_pending: List[tuple] = []

# ManyToMany through jadval yaratish paytida rekursiyani oldini olish
_in_m2m_setup: bool = False


def register(model_cls: "type") -> None:
    """
    Model klassini registry'ga ro'yxatdan o'tkazadi.
    ModelMeta.__new__ tomonidan avtomatik chaqiriladi.
    """
    simple_name = model_cls.__name__
    _registry[simple_name] = model_cls

    module = getattr(model_cls, "__module__", None)
    if module:
        full_name = f"{module}.{simple_name}"
        _registry[full_name] = model_cls


def resolve(ref: "str | type") -> "type | None":
    """
    String yoki to'g'ridan-to'g'ri klass qabul qiladi:
    - str bo'lsa: registry'dan qidiradi
    - klass bo'lsa: o'zini qaytaradi
    - topilmasa None qaytaradi (hali ro'yxatga olinmagan bo'lishi mumkin)
    """
    if not isinstance(ref, str):
        return ref

    if ref in _registry:
        return _registry[ref]

    short = ref.rsplit(".", 1)[-1]
    if short in _registry:
        return _registry[short]

    if "." in ref:
        module_path, class_name = ref.rsplit(".", 1)
        module = sys.modules.get(module_path)
        if module and hasattr(module, class_name):
            cls = getattr(module, class_name)
            register(cls)
            return cls

    return None


def add_pending(field_obj, owner_cls, setup_callback) -> None:
    """
    String reference hali resolve bo'lmagan maydonni navbatga qo'yadi.
    setup_callback(resolved_model) — model resolve bo'lganda chaqiriladi.
    """
    _pending.append((field_obj, owner_cls, setup_callback))


def resolve_pending() -> None:
    """
    Navbatdagi hamma string reference'larni resolve qilishga urinadi.
    Har yangi model ro'yxatga olinganda chaqiriladi.
    """
    global _in_m2m_setup
    if _in_m2m_setup:
        return  # Through jadval yaratish paytida rekursiyadan saqlanish
    still_pending = []
    for field_obj, owner_cls, callback in _pending:
        ref = field_obj._to_ref
        resolved = resolve(ref)
        if resolved is not None:
            field_obj._resolved_to = resolved
            try:
                callback(resolved)
            except Exception as e:
                import warnings
                warnings.warn(
                    f"'{owner_cls.__name__}' modelidagi '{field_obj.name}' maydoni "
                    f"resolve bo'ldi, lekin callback xato berdi: {e}",
                    stacklevel=2,
                )
        else:
            still_pending.append((field_obj, owner_cls, callback))
    _pending.clear()
    _pending.extend(still_pending)


def resolve_all() -> List[str]:
    """
    Barcha modellar import qilingandan keyin bir marta chaqiriladigan funksiya.
    Hali resolve bo'lmagan string reference'larni resolve qiladi.

    Qaytaradi: resolve bo'lmagan qolganlar ro'yxati (bo'sh bo'lsa — hammasi yaxshi).

    Misol::

        # main.py
        from myapp.models import user, post, comment   # barcha modellarni import
        from postgresdb3.orm import resolve_all

        unresolved = resolve_all()
        if unresolved:
            raise RuntimeError(f"Topilmagan modellar: {unresolved}")
    """
    resolve_pending()
    return get_unresolved()


def get_unresolved() -> List[str]:
    """
    Hali resolve bo'lmagan string reference'lar ro'yxatini qaytaradi.
    Debug/diagnostika uchun.
    """
    return [
        f"{owner.__name__}.{field.name} → '{field._to_ref}'"
        for field, owner, _ in _pending
    ]

