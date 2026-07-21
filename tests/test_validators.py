import unittest
from postgresdb3 import (
    ValidationError,
    MinValueValidator,
    MaxValueValidator,
    MinLengthValidator,
    MaxLengthValidator,
    RegexValidator,
    EmailValidator,
)


class ValidatorsTestCase(unittest.TestCase):
    def test_min_max_value_validators(self):
        min_v = MinValueValidator(18)
        min_v(20)
        with self.assertRaises(ValidationError):
            min_v(15)

        max_v = MaxValueValidator(100)
        max_v(50)
        with self.assertRaises(ValidationError):
            max_v(150)

    def test_min_max_length_validators(self):
        min_len = MinLengthValidator(3)
        min_len("hello")
        with self.assertRaises(ValidationError):
            min_len("hi")

        max_len = MaxLengthValidator(5)
        max_len("hello")
        with self.assertRaises(ValidationError):
            max_len("hello world")

    def test_email_and_regex_validators(self):
        email_v = EmailValidator()
        email_v("user@example.com")
        with self.assertRaises(ValidationError):
            email_v("invalid-email")

        regex_v = RegexValidator(r"^\d{4}$", message="4 xonali son kiritilsin")
        regex_v("1234")
        with self.assertRaises(ValidationError):
            regex_v("12345")


if __name__ == "__main__":
    unittest.main()
