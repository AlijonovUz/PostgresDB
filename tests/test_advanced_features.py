import unittest
from postgresdb3 import PostgresDB
from postgresdb3.orm import Model, fields
from postgresdb3.migrations.engine import MigrationEngine
from postgresdb3.orm.meta import model_registry


class TestAdvancedFeatures(unittest.TestCase):
    def setUp(self):
        import shutil

        model_registry.clear()
        shutil.rmtree("tmp_migrations_test", ignore_errors=True)

    def tearDown(self):
        import shutil

        shutil.rmtree("tmp_migrations_test", ignore_errors=True)

    def test_slow_query_threshold_init(self):
        from unittest.mock import MagicMock, patch

        with patch("psycopg2.pool.ThreadedConnectionPool"):
            db = PostgresDB("mydb", "user", "pass", slow_query_threshold=200.0)
            self.assertEqual(db.slow_query_threshold, 200.0)

    def test_queryset_only_and_defer(self):
        from unittest.mock import MagicMock

        Model.db = MagicMock()

        class Article(Model):
            id = fields.Serial(primary_key=True)
            title = fields.String(length=100)
            body = fields.Text()
            views = fields.Integer(default=0)

        qs_only = Article.query().only("title", "views")
        self.assertIn("id", qs_only._columns)
        self.assertIn("title", qs_only._columns)
        self.assertIn("views", qs_only._columns)
        self.assertNotIn("body", qs_only._columns)

        qs_defer = Article.query().defer("body")
        self.assertIn("id", qs_defer._columns)
        self.assertIn("title", qs_defer._columns)
        self.assertNotIn("body", qs_defer._columns)

        with self.assertRaises(ValueError):
            Article.query().only("non_existing_field")

    def test_data_migration_creation(self):
        import os
        import json

        engine = MigrationEngine(migrations_dir="tmp_migrations_test")
        engine.create_data_migration(
            message="update_roles",
            operations=["UPDATE users SET role = 'user' WHERE role IS NULL;"],
            reverse_operations=["UPDATE users SET role = NULL;"],
        )

        files = [f for f in os.listdir("tmp_migrations_test") if f.endswith(".json")]
        self.assertEqual(len(files), 1)
        with open(os.path.join("tmp_migrations_test", files[0]), "r") as f:
            data = json.load(f)
            self.assertEqual(
                data["operations"],
                ["UPDATE users SET role = 'user' WHERE role IS NULL;"],
            )

    def test_composite_primary_key(self):
        class OrderItem(Model):
            order_id = fields.Integer(primary_key=True)
            product_id = fields.Integer(primary_key=True)
            quantity = fields.Integer(default=1)

        self.assertEqual(OrderItem.get_pk_name(), ("order_id", "product_id"))
        item = OrderItem(order_id=10, product_id=20, quantity=2)
        self.assertEqual(item.get_pk_value(), (10, 20))


if __name__ == "__main__":
    unittest.main()
