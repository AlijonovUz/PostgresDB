import unittest
from postgresdb3.orm import Model, Index
from postgresdb3.orm.fields import String, Integer
from postgresdb3.migrations.engine import MigrationEngine
from postgresdb3.orm.meta import model_registry


class IndexTestCase(unittest.TestCase):
    def setUp(self):
        model_registry.clear()

    def test_index_sql_generation(self):
        idx1 = Index(fields=["category", "price"], name="idx_prod_cat_price")
        self.assertEqual(
            idx1.to_sql("products"),
            "CREATE INDEX IF NOT EXISTS idx_prod_cat_price ON products (category, price);",
        )

        idx2 = Index(fields=["-created_at"], name="idx_created_desc")
        self.assertEqual(
            idx2.to_sql("orders"),
            "CREATE INDEX IF NOT EXISTS idx_created_desc ON orders (created_at DESC);",
        )

        idx3 = Index(fields=["email"], unique=True)
        self.assertEqual(
            idx3.to_sql("users"),
            "CREATE UNIQUE INDEX IF NOT EXISTS uniq_idx_users_email ON users (email);",
        )

        idx4 = Index(fields=["status"], condition="status = 'active'")
        self.assertEqual(
            idx4.to_sql("users"),
            "CREATE INDEX IF NOT EXISTS idx_users_status ON users (status) WHERE status = 'active';",
        )

        idx5 = Index(fields=["data"], using="gin")
        self.assertEqual(
            idx5.to_sql("logs"),
            "CREATE INDEX IF NOT EXISTS idx_logs_data ON logs USING gin (data);",
        )

        idx6 = Index(fields=["title"], include=["author_id"])
        self.assertEqual(
            idx6.to_sql("posts"),
            "CREATE INDEX IF NOT EXISTS idx_posts_title ON posts (title) INCLUDE (author_id);",
        )

    def test_meta_indexes_parsing(self):
        class Product(Model):
            category = String(length=50)
            price = Integer()

            class Meta:
                indexes = [
                    Index(fields=["category", "price"], name="custom_idx"),
                    Index(fields=["-price"]),
                    ("category",),
                ]

        meta_options = getattr(Product, "_meta_options")
        indexes = meta_options.get("indexes")
        self.assertEqual(len(indexes), 3)
        self.assertTrue(isinstance(indexes[0], Index))
        self.assertEqual(indexes[0].name, "custom_idx")
        self.assertEqual(indexes[1].fields, ["-price"])
        self.assertEqual(indexes[2].fields, ["category"])

    def test_migration_engine_state_and_sql(self):
        class Article(Model):
            title = String(length=100)
            status = String(length=20)

            class Meta:
                indexes = [
                    Index(fields=["title"], unique=True),
                    Index(fields=["status"], condition="status = 'published'"),
                ]

        engine = MigrationEngine(migrations_dir="tmp_migrations")
        state = engine._get_current_state()
        self.assertIn("articles", state)
        self.assertIn("indexes", state["articles"]["meta_options"])

        indexes_state = state["articles"]["meta_options"]["indexes"]
        self.assertEqual(len(indexes_state), 2)
        self.assertEqual(indexes_state[0]["unique"], True)
        self.assertEqual(indexes_state[1]["condition"], "status = 'published'")


if __name__ == "__main__":
    unittest.main()
