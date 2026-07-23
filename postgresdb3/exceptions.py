"""
PostgresDB3 ORM uchun xatoliklar (Exceptions) moduli.
Barcha ma'lumotlar bazasi va ORM xatoliklari uchun alohida exception sinflarini taqdim etadi.
"""


class PostgresDBError(Exception):
    """PostgresDB ORM uchun asosiy xatolik sinfi."""

    pass


class DatabaseError(PostgresDBError):
    """Ma'lumotlar bazasi so'rovlari bilan bog'liq xatoliklar."""

    pass


class IntegrityError(DatabaseError):
    """Ma'lumotlar bazasi cheklovlari (constraint) buzilganda yuzaga keladigan xatolik."""

    pass


class UniqueViolationError(IntegrityError):
    """Takrorlanmaslik (UNIQUE) sharti buzilganda yuzaga keladigan xatolik."""

    pass


class ForeignKeyViolationError(IntegrityError):
    """Tashqi kalit (FOREIGN KEY) sharti buzilganda yuzaga keladigan xatolik."""

    pass


class NotNullViolationError(IntegrityError):
    """BO'SH BO'LMASLIGI SHART (NOT NULL) bo'lgan maydon bo'sh qolganda yuzaga keladigan xatolik."""

    pass


class CheckViolationError(IntegrityError):
    """CHECK cheklovi buzilganda yuzaga keladigan xatolik."""

    pass


class OperationalError(DatabaseError):
    """Ulanish uzilishi, server javob bermasligi yoki timeout xatoliklari."""

    pass


class DataError(DatabaseError):
    """Ma'lumot turi yoki o'lchami mos kelmaganda yuzaga keladigan xatolik."""

    pass


class ProgrammingError(DatabaseError):
    """SQL sintaksis xatoligi yoki jadval/ustun topilmaganda yuzaga keladigan xatolik."""

    pass


class UndefinedTableError(ProgrammingError):
    """Ma'lumotlar bazasida jadval topilmaganda yuzaga keladigan xatolik (relation does not exist)."""

    pass


class UndefinedColumnError(ProgrammingError):
    """Ma'lumotlar bazasida ustun topilmaganda yuzaga keladigan xatolik (column does not exist)."""

    pass


class UndefinedObjectError(ProgrammingError):
    """PostgreSQL obyekti yoki turi (masalan geometry) topilmaganda yuzaga keladigan xatolik."""

    pass


class UndefinedFunctionError(ProgrammingError):
    """PostgreSQL funksiyasi (masalan ST_DWithin) topilmaganda yuzaga keladigan xatolik."""

    pass


class TransactionError(DatabaseError):
    """Tranzaksiya muvaffaqiyatsiz tugaganda yuzaga keladigan xatolik."""

    pass


class ObjectDoesNotExist(PostgresDBError, ValueError):
    """Qidirilayotgan obyekt topilmaganda yuzaga keladigan xatolik."""

    pass


DoesNotExist = ObjectDoesNotExist


class MultipleObjectsReturned(PostgresDBError, ValueError):
    """Bir nechta obyekt qaytganda (faqat 1 ta kutilganda) yuzaga keladigan xatolik."""

    pass


class ModelSetupError(PostgresDBError, ValueError):
    """Model yoki baza sozlamalari noto'g'ri o'rnatilganda yuzaga keladigan xatolik."""

    pass


def translate_db_error(exc: Exception) -> Exception:
    """
    psycopg2 va asyncpg xatoliklarini bir xil PostgresDB ORM xatoliklariga aylantiradi.
    """
    if isinstance(exc, PostgresDBError):
        return exc

    try:
        import asyncpg.exceptions as a_exc

        if isinstance(exc, a_exc.UndefinedTableError):
            return UndefinedTableError(str(exc))
        if isinstance(exc, a_exc.UndefinedColumnError):
            return UndefinedColumnError(str(exc))
        if isinstance(exc, a_exc.UniqueViolationError):
            return UniqueViolationError(str(exc))
        if isinstance(exc, a_exc.ForeignKeyViolationError):
            return ForeignKeyViolationError(str(exc))
        if isinstance(exc, a_exc.NotNullViolationError):
            return NotNullViolationError(str(exc))
        if isinstance(exc, a_exc.CheckViolationError):
            return CheckViolationError(str(exc))
        if isinstance(exc, a_exc.IntegrityConstraintViolationError):
            return IntegrityError(str(exc))
        if isinstance(exc, a_exc.DataError):
            return DataError(str(exc))
        if isinstance(
            exc,
            (
                a_exc.PostgresConnectionError,
                a_exc.InterfaceError,
                a_exc.CannotConnectNowError,
            ),
        ):
            return OperationalError(str(exc))
        if isinstance(exc, a_exc.PostgresSyntaxError):
            return ProgrammingError(str(exc))
    except ImportError:
        pass

    try:
        import psycopg2
        import psycopg2.errors as p_exc

        if isinstance(exc, p_exc.UndefinedTable):
            return UndefinedTableError(str(exc))
        if isinstance(exc, p_exc.UndefinedColumn):
            return UndefinedColumnError(str(exc))
        if isinstance(exc, p_exc.UniqueViolation):
            return UniqueViolationError(str(exc))
        if isinstance(exc, p_exc.ForeignKeyViolation):
            return ForeignKeyViolationError(str(exc))
        if isinstance(exc, p_exc.NotNullViolation):
            return NotNullViolationError(str(exc))
        if isinstance(exc, p_exc.CheckViolation):
            return CheckViolationError(str(exc))
        if isinstance(exc, psycopg2.IntegrityError):
            return IntegrityError(str(exc))
        if isinstance(exc, psycopg2.DataError):
            return DataError(str(exc))
        if isinstance(exc, psycopg2.OperationalError):
            return OperationalError(str(exc))
        if isinstance(exc, psycopg2.ProgrammingError):
            exc_str = str(exc)
            if "UndefinedTable" in exc.__class__.__name__ or 'relation "' in exc_str and "does not exist" in exc_str:
                return UndefinedTableError(exc_str)
            if "UndefinedColumn" in exc.__class__.__name__ or 'column "' in exc_str and "does not exist" in exc_str:
                return UndefinedColumnError(exc_str)
            return ProgrammingError(exc_str)
    except (ImportError, AttributeError):
        pass

    sqlstate = getattr(exc, "pgcode", None) or getattr(exc, "sqlstate", None)
    exc_name = exc.__class__.__name__
    exc_msg = str(exc)

    if sqlstate == "42P01" or "UndefinedTable" in exc_name or ('relation "' in exc_msg and "does not exist" in exc_msg):
        return UndefinedTableError(exc_msg)
    elif sqlstate == "42703" or "UndefinedColumn" in exc_name or ('column "' in exc_msg and "does not exist" in exc_msg):
        return UndefinedColumnError(exc_msg)
    elif sqlstate == "23505" or "UniqueViolation" in exc_name:
        return UniqueViolationError(exc_msg)
    elif sqlstate == "23503" or "ForeignKeyViolation" in exc_name:
        return ForeignKeyViolationError(exc_msg)
    elif sqlstate == "23502" or "NotNullViolation" in exc_name:
        return NotNullViolationError(exc_msg)
    elif sqlstate == "23514" or "CheckViolation" in exc_name:
        return CheckViolationError(exc_msg)
    elif (sqlstate and str(sqlstate).startswith("23")) or "Integrity" in exc_name:
        return IntegrityError(exc_msg)
    elif (sqlstate and str(sqlstate).startswith("22")) or "DataError" in exc_name:
        return DataError(exc_msg)
    elif "UndefinedObject" in exc_name or 'type "geometry"' in exc_msg:
        return UndefinedObjectError(exc_msg)
    elif "UndefinedFunction" in exc_name or "st_dwithin" in exc_msg.lower():
        return UndefinedFunctionError(exc_msg)
    elif (
        (sqlstate and str(sqlstate).startswith("42"))
        or "ProgrammingError" in exc_name
        or "SyntaxError" in exc_name
    ):
        return ProgrammingError(exc_msg)
    elif (
        (sqlstate and str(sqlstate).startswith("08"))
        or "OperationalError" in exc_name
        or "Connection" in exc_name
        or "InterfaceError" in exc_name
    ):
        return OperationalError(exc_msg)
    elif (
        (sqlstate and str(sqlstate).startswith("40"))
        or "Transaction" in exc_name
        or "Deadlock" in exc_name
    ):
        return TransactionError(exc_msg)

    return DatabaseError(exc_msg)
