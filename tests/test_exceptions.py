import unittest
from postgresdb3.exceptions import (
    PostgresDBError,
    DatabaseError,
    IntegrityError,
    UniqueViolationError,
    ForeignKeyViolationError,
    NotNullViolationError,
    CheckViolationError,
    OperationalError,
    DataError,
    ProgrammingError,
    TransactionError,
    ObjectDoesNotExist,
    DoesNotExist,
    MultipleObjectsReturned,
    ModelSetupError,
    translate_db_error,
)
from postgresdb3.orm.validators import ValidationError


class ExceptionsTestCase(unittest.TestCase):
    def test_exception_hierarchy(self):
        # IntegrityError inheritance
        self.assertTrue(issubclass(UniqueViolationError, IntegrityError))
        self.assertTrue(issubclass(ForeignKeyViolationError, IntegrityError))
        self.assertTrue(issubclass(NotNullViolationError, IntegrityError))
        self.assertTrue(issubclass(CheckViolationError, IntegrityError))
        self.assertTrue(issubclass(IntegrityError, DatabaseError))
        self.assertTrue(issubclass(DatabaseError, PostgresDBError))

        # Other database errors
        self.assertTrue(issubclass(OperationalError, DatabaseError))
        self.assertTrue(issubclass(DataError, DatabaseError))
        self.assertTrue(issubclass(ProgrammingError, DatabaseError))
        self.assertTrue(issubclass(TransactionError, DatabaseError))

        # DoesNotExist and MultipleObjectsReturned compatibility
        self.assertTrue(issubclass(ObjectDoesNotExist, ValueError))
        self.assertTrue(issubclass(ObjectDoesNotExist, PostgresDBError))
        self.assertEqual(DoesNotExist, ObjectDoesNotExist)
        self.assertTrue(issubclass(MultipleObjectsReturned, ValueError))
        self.assertTrue(issubclass(ValidationError, ValueError))
        self.assertTrue(issubclass(ModelSetupError, ValueError))

    def test_translate_db_error_unique_violation(self):
        class DummyPsycopg2UniqueError(Exception):
            pgcode = "23505"

        err = translate_db_error(
            DummyPsycopg2UniqueError("duplicate key value violates unique constraint")
        )
        self.assertIsInstance(err, UniqueViolationError)
        self.assertIsInstance(err, IntegrityError)
        self.assertIsInstance(err, DatabaseError)

    def test_translate_db_error_foreign_key_violation(self):
        class DummyAsyncpgFKError(Exception):
            sqlstate = "23503"

        err = translate_db_error(
            DummyAsyncpgFKError(
                "insert or update on table violates foreign key constraint"
            )
        )
        self.assertIsInstance(err, ForeignKeyViolationError)

    def test_translate_db_error_not_null_violation(self):
        class DummyNotNullError(Exception):
            pgcode = "23502"

        err = translate_db_error(
            DummyNotNullError("null value in column violates not-null constraint")
        )
        self.assertIsInstance(err, NotNullViolationError)

    def test_translate_db_error_check_violation(self):
        class DummyCheckError(Exception):
            pgcode = "23514"

        err = translate_db_error(DummyCheckError("new row violates check constraint"))
        self.assertIsInstance(err, CheckViolationError)

    def test_translate_db_error_by_class_name(self):
        class UniqueViolation(Exception):
            pass

        err = translate_db_error(UniqueViolation("duplicate key"))
        self.assertIsInstance(err, UniqueViolationError)

    def test_sync_db_manager_raises_orm_exception(self):
        from unittest.mock import MagicMock
        from postgresdb3 import PostgresDB

        db = PostgresDB.__new__(PostgresDB)
        db._local = MagicMock()
        db.echo = False
        mock_pool = MagicMock()
        mock_conn = MagicMock()

        class FakePsycopg2UniqueError(Exception):
            pgcode = "23505"

        mock_conn.cursor.return_value.__enter__.return_value.execute.side_effect = (
            FakePsycopg2UniqueError("duplicate key")
        )
        mock_pool.getconn.return_value = mock_conn
        db.pool = mock_pool
        db.ping_connections = False
        db._local.conn = None

        with self.assertRaises(UniqueViolationError):
            db._manager("INSERT INTO users VALUES (1)")

    def test_async_db_manager_raises_orm_exception(self):
        from unittest.mock import MagicMock, AsyncMock
        import asyncio
        from postgresdb3 import AsyncPostgresDB

        db = AsyncPostgresDB.__new__(AsyncPostgresDB)
        db._async_conn = MagicMock()
        db._async_conn.get.return_value = None
        db.echo = False

        class FakeAsyncpgUniqueError(Exception):
            sqlstate = "23505"

        mock_conn = MagicMock()
        mock_conn.execute = AsyncMock(
            side_effect=FakeAsyncpgUniqueError("duplicate key")
        )

        mock_pool = MagicMock()
        mock_pool.acquire = AsyncMock(return_value=mock_conn)
        mock_pool.release = AsyncMock()
        db.pool = mock_pool

        async def run_test():
            with self.assertRaises(UniqueViolationError):
                await db._manager("INSERT INTO users VALUES (1)", commit=True)

        asyncio.run(run_test())

    def test_async_db_transaction_raises_orm_exception(self):
        from unittest.mock import MagicMock, AsyncMock
        import asyncio
        from postgresdb3 import AsyncPostgresDB

        db = AsyncPostgresDB.__new__(AsyncPostgresDB)
        db._async_conn = MagicMock()
        db._async_conn.get.return_value = None

        class FakeAsyncpgFKError(Exception):
            sqlstate = "23503"

        mock_tx = MagicMock()
        mock_tx.__aenter__ = AsyncMock(return_value=None)
        mock_tx.__aexit__ = AsyncMock(
            side_effect=FakeAsyncpgFKError("foreign key error")
        )

        mock_conn = MagicMock()
        mock_conn.transaction.return_value = mock_tx

        mock_pool = MagicMock()
        mock_pool.acquire = AsyncMock(return_value=mock_conn)
        mock_pool.release = AsyncMock()
        db.pool = mock_pool

        async def run_test():
            with self.assertRaises(ForeignKeyViolationError):
                async with db.transaction():
                    pass

        asyncio.run(run_test())


if __name__ == "__main__":
    unittest.main()
