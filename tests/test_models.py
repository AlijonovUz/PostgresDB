import unittest
from postgresdb3.orm.models import Model, AsyncModel
from postgresdb3 import String, Integer, ValidationError
from postgresdb3.orm.meta import model_registry


class ModelsTestCase(unittest.TestCase):
    def setUp(self):
        model_registry.clear()

    def test_model_meta_options(self):
        class ParentUser(Model):
            name = String(length=50)

            class Meta:
                abstract = True
                ordering = ["-id"]

        class ChildUser(ParentUser):
            age = Integer()

            class Meta:
                table_name = "custom_users"

        self.assertEqual(ChildUser.table, "custom_users")
        meta_options = getattr(ChildUser, "_meta_options")
        self.assertEqual(meta_options["ordering"], ["-id"])

    def test_model_hooks(self):
        saved_events = []

        class User(Model):
            username = String(length=50)
            status = String(length=20, default="pending")

            def clean(self):
                super().clean()
                if self.username == "invalid":
                    raise ValidationError("Invalid username!")

            def before_save(self):
                if not self.status:
                    self.status = "pending"

            def after_save(self, created: bool):
                saved_events.append(("saved", created))

        u = User(username="invalid")
        with self.assertRaises(ValidationError):
            u.clean()

        u2 = User(username="valid_user")
        u2.before_save()
        self.assertEqual(u2.status, "pending")
        u2.after_save(created=True)
        self.assertEqual(saved_events, [("saved", True)])

    def test_auto_now_and_auto_now_add_defaults(self):
        import datetime
        from postgresdb3 import Date, Time, Timestamp, Timestamptz

        class Article(Model):
            created_date = Date(auto_now_add=True)
            created_time = Time(auto_now_add=True)
            created_at = Timestamp(auto_now_add=True)
            created_at_tz = Timestamptz(auto_now_add=True)
            updated_at = Timestamp(auto_now=True)

        article = Article()
        self.assertIsInstance(article.created_date, datetime.date)
        self.assertIsInstance(article.created_time, datetime.time)
        self.assertIsInstance(article.created_at, datetime.datetime)
        self.assertIsInstance(article.created_at_tz, datetime.datetime)
        self.assertIsInstance(article.updated_at, datetime.datetime)


if __name__ == "__main__":
    unittest.main()
