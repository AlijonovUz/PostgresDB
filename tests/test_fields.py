import unittest
from postgresdb3 import (
    String,
    Text,
    Integer,
    SmallInteger,
    BigInteger,
    Float,
    Double,
    Decimal,
    Boolean,
    Date,
    Time,
    Timestamp,
    Timestamptz,
    UUID,
    JSON,
    JSONB,
    Array,
    Serial,
    BigSerial,
    MinValueValidator,
    ValidationError,
)


class FieldsTestCase(unittest.TestCase):
    def test_numeric_fields(self):
        f_int = Integer(primary_key=True)
        f_int.name = "id"
        self.assertIn("id INTEGER PRIMARY KEY", f_int.to_sql())

        f_smallint = SmallInteger(nullable=True)
        f_smallint.name = "count"
        self.assertEqual(f_smallint.to_sql().strip(), "count SMALLINT")

        f_bigint = BigInteger(default=0)
        f_bigint.name = "amount"
        self.assertIn("amount BIGINT NOT NULL DEFAULT 0", f_bigint.to_sql())

        f_float = Float()
        f_float.name = "rate"
        self.assertEqual(f_float.to_sql().strip(), "rate REAL NOT NULL")

        f_double = Double()
        f_double.name = "score"
        self.assertEqual(f_double.to_sql().strip(), "score DOUBLE PRECISION NOT NULL")

        f_dec = Decimal(precision=10, scale=2)
        f_dec.name = "price"
        self.assertEqual(f_dec.to_sql().strip(), "price NUMERIC(10,2) NOT NULL")

    def test_text_fields(self):
        f_str = String(length=100, unique=True)
        f_str.name = "title"
        self.assertIn("title VARCHAR(100)", f_str.to_sql())
        self.assertIn("UNIQUE", f_str.to_sql())
        self.assertIn("NOT NULL", f_str.to_sql())

        f_text = Text(nullable=True)
        f_text.name = "body"
        self.assertEqual(f_text.to_sql().strip(), "body TEXT")

    def test_datetime_and_misc_fields(self):
        f_date = Date()
        f_date.name = "dob"
        self.assertIn("dob DATE", f_date.to_sql())

        f_time = Time()
        f_time.name = "t"
        self.assertIn("t TIME", f_time.to_sql())

        f_timestamp = Timestamp()
        f_timestamp.name = "ts"
        self.assertIn("ts TIMESTAMP", f_timestamp.to_sql())

        f_timestamptz = Timestamptz()
        f_timestamptz.name = "tsz"
        self.assertIn("tsz TIMESTAMPTZ", f_timestamptz.to_sql())

        f_bool = Boolean(default=False)
        f_bool.name = "is_active"
        self.assertIn("is_active BOOLEAN NOT NULL DEFAULT False", f_bool.to_sql())

        f_uuid = UUID()
        f_uuid.name = "uid"
        self.assertIn("uid UUID", f_uuid.to_sql())

        f_json = JSON()
        f_json.name = "meta"
        self.assertIn("meta JSON", f_json.to_sql())

        f_jsonb = JSONB()
        f_jsonb.name = "data"
        self.assertIn("data JSONB", f_jsonb.to_sql())

        f_array = Array(base_type="INTEGER")
        f_array.name = "tags"
        self.assertIn("tags INTEGER[]", f_array.to_sql())

    def test_serials(self):
        f_serial = Serial(primary_key=True)
        f_serial.name = "id"
        self.assertIn("id SERIAL PRIMARY KEY", f_serial.to_sql())

        f_bigserial = BigSerial(primary_key=True)
        f_bigserial.name = "id"
        self.assertIn("id BIGSERIAL PRIMARY KEY", f_bigserial.to_sql())

    def test_field_validation(self):
        f = Integer(validators=[MinValueValidator(10)])
        f.name = "age"
        f.validate(15)
        with self.assertRaises(ValidationError):
            f.validate(5)

    def test_datetime_auto_now_and_auto_now_add(self):
        import datetime

        f_date_add = Date(auto_now_add=True)
        f_date_add.name = "d"
        self.assertTrue(f_date_add.auto_now_add)
        self.assertFalse(f_date_add.auto_now)
        self.assertIn("DEFAULT CURRENT_DATE", f_date_add.to_sql())
        self.assertIsInstance(f_date_add.get_default_value(), datetime.date)

        f_time_now = Time(auto_now=True)
        f_time_now.name = "t"
        self.assertTrue(f_time_now.auto_now)
        self.assertFalse(f_time_now.auto_now_add)
        self.assertIn("DEFAULT CURRENT_TIME", f_time_now.to_sql())
        self.assertIsInstance(f_time_now.get_default_value(), datetime.time)

        f_ts_add = Timestamp(auto_now_add=True)
        f_ts_add.name = "ts"
        self.assertTrue(f_ts_add.auto_now_add)
        self.assertIn("DEFAULT CURRENT_TIMESTAMP", f_ts_add.to_sql())
        self.assertIsInstance(f_ts_add.get_default_value(), datetime.datetime)

        f_tsz_now = Timestamptz(auto_now=True)
        f_tsz_now.name = "tsz"
        self.assertTrue(f_tsz_now.auto_now)
        self.assertIn("DEFAULT CURRENT_TIMESTAMP", f_tsz_now.to_sql())
        val = f_tsz_now.get_default_value()
        self.assertIsInstance(val, datetime.datetime)
        self.assertIsNotNone(val.tzinfo)

        # Positional boolean test (legacy compatibility)
        f_legacy = Date(True)
        self.assertTrue(f_legacy.auto_now_add)


if __name__ == "__main__":
    unittest.main()
