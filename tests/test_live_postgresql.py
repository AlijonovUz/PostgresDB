import unittest
import asyncio
import os
import shutil
import uuid
import datetime

from postgresdb3 import PostgresDB, AsyncPostgresDB
from postgresdb3.orm import (
    Model,
    AsyncModel,
    fields,
    Q,
    F,
    pre_save,
    post_save,
    receiver,
)
from postgresdb3.migrations.engine import MigrationEngine
from postgresdb3.orm.meta import model_registry

DB_NAME = "postgresdb3"
DB_USER = "postgres"
DB_PASS = "alijonov"
DB_HOST = "localhost"
DB_PORT = 5432


class LivePostgreSQLTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.db_sync = PostgresDB(
            database=DB_NAME,
            user=DB_USER,
            password=DB_PASS,
            host=DB_HOST,
            port=DB_PORT,
            echo=False,
            slow_query_threshold=100.0,
        )
        cls.db_async = AsyncPostgresDB(
            database=DB_NAME,
            user=DB_USER,
            password=DB_PASS,
            host=DB_HOST,
            port=DB_PORT,
            echo=False,
        )

    def setUp(self):
        model_registry.clear()
        shutil.rmtree("live_migrations", ignore_errors=True)
        Model.db = self.db_sync
        AsyncModel.db = self.db_async

        for tbl in [
            "live_items_live_tags",
            "live_items",
            "live_tags",
            "live_wallets",
            "live_users",
            "live_async_persons",
        ]:
            try:
                self.db_sync.drop(tbl, cascade=True)
            except Exception:
                pass

    def tearDown(self):
        shutil.rmtree("live_migrations", ignore_errors=True)

    def test_full_live_integration(self):
        # 1. Define Models
        class User(Model):
            username = fields.String(length=50, unique=True)
            age = fields.Integer(default=18)
            metadata = fields.JSONB(nullable=True)

            class Meta:
                table_name = "live_users"

        class Wallet(Model):
            user = fields.OneToOne(User, on_delete=fields.CASCADE)
            balance = fields.Integer(default=1000)

            class Meta:
                table_name = "live_wallets"

        class Tag(Model):
            name = fields.String(length=30)

            class Meta:
                table_name = "live_tags"

        class Item(Model):
            title = fields.String(length=100)
            tags = fields.ManyToMany(Tag)

            class Meta:
                table_name = "live_items"

        # 2. Run Migrations on Live PostgreSQL
        engine = MigrationEngine(migrations_dir="live_migrations")
        engine.makemigrations("live_setup", interactive=False)
        engine.migrate(self.db_sync)

        # Signal tracking
        created_users = []

        @receiver(post_save, sender=User)
        def on_user_saved(sender, instance, created, **kwargs):
            if created:
                created_users.append(instance.username)

        # 3. Create Records
        u1 = User.create(
            username="ali_live",
            age=25,
            metadata={"role": "admin", "details": {"active": True}},
        )
        u2 = User.create(
            username="val_live",
            age=30,
            metadata={"role": "user", "details": {"active": False}},
        )
        self.assertIn("ali_live", created_users)

        # 4. OneToOne Relation Test
        w1 = Wallet.create(user=u1, balance=5000)
        self.assertEqual(u1.wallet.balance, 5000)

        # 5. ManyToMany Relation Test
        t1 = Tag.create(name="electronics")
        t2 = Tag.create(name="sale")
        item1 = Item.create(title="Smartphone")
        item1.tags.add(t1, t2)
        item_tags = [t.name for t in item1.tags.all()]
        self.assertIn("electronics", item_tags)
        self.assertIn("sale", item_tags)

        # 6. JSONB Deep Lookup Test
        admins = User.filter(metadata__role="admin").all()
        self.assertEqual(len(admins), 1)
        self.assertEqual(admins[0].username, "ali_live")

        active_users = User.filter(metadata__details__active=True).all()
        self.assertEqual(len(active_users), 1)
        self.assertEqual(active_users[0].username, "ali_live")

        # 7. QuerySet only, defer and cache Test
        only_users = User.query().only("username").all()
        self.assertEqual(only_users[0].username, "ali_live")

        cached_users = User.query().cache(ttl=60).all()
        self.assertEqual(len(cached_users), 2)

        # 8. Fixtures Dump & Load Test
        engine.dumpdata(self.db_sync, filename="live_migrations/fixture.json")
        self.assertTrue(os.path.exists("live_migrations/fixture.json"))

        # 9. Clean up live tables
        self.db_sync.drop("live_items_live_tags", cascade=True)
        self.db_sync.drop("live_items", cascade=True)
        self.db_sync.drop("live_tags", cascade=True)
        self.db_sync.drop("live_wallets", cascade=True)
        self.db_sync.drop("live_users", cascade=True)

    def test_async_live_integration(self):
        async def run_async_tests():
            class AsyncPerson(AsyncModel):
                name = fields.String(length=50)
                score = fields.Integer(default=100)

                class Meta:
                    table_name = "live_async_persons"

            await self.db_async.create(
                "live_async_persons",
                "id SERIAL PRIMARY KEY, name VARCHAR(50), score INTEGER",
            )

            p1 = await AsyncPerson.create(name="Sardor", score=200)
            fetched = await AsyncPerson.first(id=p1.id)
            self.assertEqual(fetched.name, "Sardor")

            await self.db_async.drop("live_async_persons", cascade=True)

        asyncio.run(run_async_tests())


if __name__ == "__main__":
    unittest.main()
