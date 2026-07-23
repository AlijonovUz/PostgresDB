import unittest
from postgresdb3.migrations.engine import MigrationEngine


class TestMigrationPromptValidation(unittest.TestCase):
    def setUp(self):
        self.engine = MigrationEngine(migrations_dir="tmp_migrations_test")

    def test_validate_integer(self):
        self.assertEqual(
            self.engine.validate_and_format_default("123", "INTEGER"), "123"
        )
        self.assertEqual(self.engine.validate_and_format_default("-42", "INT"), "-42")
        with self.assertRaises(ValueError):
            self.engine.validate_and_format_default("abc", "INTEGER")

    def test_validate_float(self):
        self.assertEqual(
            self.engine.validate_and_format_default("3.14", "REAL"), "3.14"
        )
        with self.assertRaises(ValueError):
            self.engine.validate_and_format_default("invalid", "FLOAT")

    def test_validate_boolean(self):
        self.assertEqual(
            self.engine.validate_and_format_default("true", "BOOLEAN"), "TRUE"
        )
        self.assertEqual(
            self.engine.validate_and_format_default("1", "BOOLEAN"), "TRUE"
        )
        self.assertEqual(
            self.engine.validate_and_format_default("false", "BOOLEAN"), "FALSE"
        )
        self.assertEqual(
            self.engine.validate_and_format_default("0", "BOOLEAN"), "FALSE"
        )
        with self.assertRaises(ValueError):
            self.engine.validate_and_format_default("hello", "BOOLEAN")

    def test_validate_time(self):
        self.assertEqual(
            self.engine.validate_and_format_default("14:30:00", "TIME"), "'14:30:00'"
        )
        self.assertEqual(
            self.engine.validate_and_format_default("CURRENT_TIME", "TIME"),
            "CURRENT_TIME",
        )
        with self.assertRaises(ValueError):
            self.engine.validate_and_format_default("99:99:99", "TIME")

    def test_validate_date(self):
        self.assertEqual(
            self.engine.validate_and_format_default("2025-05-20", "DATE"),
            "'2025-05-20'",
        )
        self.assertEqual(
            self.engine.validate_and_format_default("CURRENT_DATE", "DATE"),
            "CURRENT_DATE",
        )
        with self.assertRaises(ValueError):
            self.engine.validate_and_format_default("2025-13-45", "DATE")

    def test_validate_json(self):
        self.assertEqual(
            self.engine.validate_and_format_default('{"a": 1}', "JSONB"), "'{\"a\": 1}'"
        )
        with self.assertRaises(ValueError):
            self.engine.validate_and_format_default("{invalid json}", "JSONB")

    def test_validate_uuid(self):
        valid_uuid = "123e4567-e89b-12d3-a456-426614174000"
        self.assertEqual(
            self.engine.validate_and_format_default(valid_uuid, "UUID"),
            f"'{valid_uuid}'",
        )
        with self.assertRaises(ValueError):
            self.engine.validate_and_format_default("not-a-uuid", "UUID")

    def test_on_delete_constants(self):
        from postgresdb3.orm.fields import (
            CASCADE,
            SET_NULL,
            RESTRICT,
            SET_DEFAULT,
            DO_NOTHING,
            ForeignKey,
        )

        class DummyModel:
            table = "dummy"

            @classmethod
            def get_pk_name(cls):
                return "id"

        fk_cascade = ForeignKey(DummyModel, on_delete=CASCADE)
        self.assertEqual(fk_cascade.on_delete, "CASCADE")

    def test_callable_default_mapping(self):
        import uuid
        import datetime
        from postgresdb3.orm.fields import UUID, Timestamp, Date

        u_field = UUID(default=uuid.uuid4)
        u_field.name = "id"
        self.assertIn("DEFAULT gen_random_uuid()", u_field.to_sql())

        t_field = Timestamp(default=datetime.datetime.now)
        t_field.name = "created_at"
        self.assertIn("DEFAULT CURRENT_TIMESTAMP", t_field.to_sql())

        d_field = Date(default=datetime.date.today)
        d_field.name = "birth_date"
        self.assertIn("DEFAULT CURRENT_DATE", d_field.to_sql())

    def test_uuid1_and_custom_callable_defaults(self):
        import uuid
        from postgresdb3.orm.fields import UUID

        # uuid1 test (zero-argument callable)
        u1_field = UUID(default=uuid.uuid1)
        u1_field.name = "uid1"
        # SQL generator does not crash, generates simple column definition:
        self.assertEqual(u1_field.to_sql(), "uid1 UUID NOT NULL")
        # Python ORM layer generates valid UUID1 instance:
        val1 = u1_field.get_default_value()
        self.assertIsInstance(val1, uuid.UUID)

        # uuid3 test with lambda
        u3_field = UUID(default=lambda: uuid.uuid3(uuid.NAMESPACE_DNS, "example.com"))
        u3_field.name = "uid3"
        self.assertEqual(u3_field.to_sql(), "uid3 UUID NOT NULL")
        val3 = u3_field.get_default_value()
        self.assertIsInstance(val3, uuid.UUID)
        self.assertEqual(val3, uuid.uuid3(uuid.NAMESPACE_DNS, "example.com"))


if __name__ == "__main__":
    unittest.main()
