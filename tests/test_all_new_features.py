import unittest
import os
import json
from unittest.mock import MagicMock
from postgresdb3.orm import Model, fields, pre_save, post_save, receiver
from postgresdb3.migrations.engine import MigrationEngine
from postgresdb3.orm.meta import model_registry
from postgresdb3.core.sync_db import PostgresDB


class TestAllNewFeatures(unittest.TestCase):
    def setUp(self):
        model_registry.clear()
        Model.db = MagicMock()

    def test_model_signals(self):
        events = []

        class Profile(Model):
            id = fields.Serial(primary_key=True)
            name = fields.String(length=50)

        @receiver(post_save, sender=Profile)
        def on_post_save(sender, instance, created, **kwargs):
            events.append(("post_save", instance.name, created))

        p = Profile(id=1, name="Ali")
        post_save.send(sender=Profile, instance=p, created=True)
        self.assertEqual(events, [("post_save", "Ali", True)])

    def test_jsonb_where_building(self):
        from unittest.mock import patch

        with patch("psycopg2.pool.ThreadedConnectionPool"):
            db = PostgresDB("mydb", "user", "pass")

        # Test nested JSON key lookup: metadata__user__role = 'admin'
        sql, params = db._build_where({"metadata__user__role": "admin"})
        self.assertEqual(sql, "metadata->'user'->>'role' = %s")
        self.assertEqual(params, ["admin"])

        # Test has_key lookup
        sql, params = db._build_where({"metadata__has_key": "discount"})
        self.assertEqual(sql, "metadata ? %s")
        self.assertEqual(params, ["discount"])

        # Test json_contains lookup
        sql, params = db._build_where({"metadata__json_contains": {"role": "admin"}})
        self.assertEqual(sql, "metadata @> %s::jsonb")
        self.assertEqual(params, ['{"role": "admin"}'])

    def test_queryset_caching(self):
        class Product(Model):
            id = fields.Serial(primary_key=True)
            name = fields.String(length=50)

        Model.db.select.return_value = [{"id": 1, "name": "Phone"}]

        qs = Product.query().cache(ttl=60.0)
        res1 = qs.all()
        res2 = qs.all()

        self.assertEqual(len(res1), 1)
        self.assertEqual(len(res2), 1)
        # Select should only be called once because the second call hits cache
        self.assertEqual(Model.db.select.call_count, 1)

    def test_dumpdata_and_loaddata(self):
        class UserSetting(Model):
            id = fields.Serial(primary_key=True)
            key = fields.String(length=50)

        Model.db.select.return_value = [{"id": 1, "key": "theme"}]
        engine = MigrationEngine()

        engine.dumpdata(Model.db, filename="tmp_fixture.json")
        self.assertTrue(os.path.exists("tmp_fixture.json"))

        with open("tmp_fixture.json", "r") as f:
            data = json.load(f)
            self.assertEqual(len(data), 1)
            self.assertEqual(data[0]["model"], "UserSetting")

        os.remove("tmp_fixture.json")


if __name__ == "__main__":
    unittest.main()
