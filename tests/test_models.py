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

    def test_find_with_pk_and_id(self):
        from unittest.mock import MagicMock, AsyncMock
        import asyncio

        class DummyModel(Model):
            id = Integer(primary_key=True)
            name = String()

        DummyModel.db = MagicMock()
        DummyModel.db._check_setup = MagicMock()

        # Check pk / id assignment
        qs1 = DummyModel.find(10)
        self.assertEqual(qs1.pk_value, 10)

        qs2 = DummyModel.find(pk=20)
        self.assertEqual(qs2.pk_value, 20)

        qs3 = DummyModel.find(id=30)
        self.assertEqual(qs3.pk_value, 30)

        # Check update and delete on find()
        DummyModel.find(10).update(name="New Name")
        self.assertTrue(DummyModel.db.update_where.called)

        DummyModel.find(10).delete()
        self.assertTrue(DummyModel.db.delete_where.called)

        # Async tests
        class AsyncDummyModel(AsyncModel):
            id = Integer(primary_key=True)
            name = String()

        mock_db = MagicMock()
        mock_db.update_where = AsyncMock(return_value=1)
        mock_db.delete_where = AsyncMock(return_value=1)
        mock_db.select = AsyncMock(return_value=None)
        AsyncDummyModel.db = mock_db

        async def run_async_tests():
            qs_a = AsyncDummyModel.find(40)
            self.assertEqual(qs_a.pk_value, 40)

            await AsyncDummyModel.find(40).update(name="Async Name")
            mock_db.update_where.assert_called()

            await AsyncDummyModel.find(40).delete()
            mock_db.delete_where.assert_called()

        asyncio.run(run_async_tests())




if __name__ == "__main__":
    unittest.main()

