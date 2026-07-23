import unittest
import datetime
import time
import asyncio
from contextlib import nullcontext, asynccontextmanager

from postgresdb3 import (
    Model,
    AsyncModel,
    Date,
    Time,
    Timestamp,
    Timestamptz,
    Serial,
    String,
)


class DummyDB:
    def __init__(self):
        self.inserted_records = []
        self.updated_records = []
        self.raw_sqls = []
        self.next_id = 1

    def insert(self, table, columns, values, returning="*"):
        cols = [c.strip() for c in columns.split(",")]
        rec = dict(zip(cols, values))
        if "id" not in rec or rec["id"] is None:
            rec["id"] = self.next_id
            self.next_id += 1
        self.inserted_records.append((table, rec))
        return rec

    def update_fields(self, table, data, where_column, where_value):
        self.updated_records.append((table, data, where_column, where_value))
        return 1

    def update_where(self, table, data, where):
        self.updated_records.append((table, data, where))
        return 1

    def delete(self, table, where_column, where_value):
        return None

    def delete_where(self, table, where):
        return 1

    def select(self, table, *args, **kwargs):
        return []

    def insert_many(self, table, columns, values_list):
        cols = [c.strip() for c in columns.split(",")]
        for val_tuple in values_list:
            rec = dict(zip(cols, val_tuple))
            if "id" not in rec or rec["id"] is None:
                rec["id"] = self.next_id
                self.next_id += 1
            self.inserted_records.append((table, rec))

    def raw(self, sql, params=None, fetchall=True):
        self.raw_sqls.append((sql, params))
        return []

    def _manager(self, sql, params=None, **kwargs):
        self.raw_sqls.append((sql, params))
        return "UPDATE 1"

    def transaction(self):
        return nullcontext()


class DummyAsyncDB:
    def __init__(self):
        self.inserted_records = []
        self.updated_records = []
        self.raw_sqls = []
        self.next_id = 1

    async def insert(self, table, columns, values, returning="*"):
        cols = [c.strip() for c in columns.split(",")]
        rec = dict(zip(cols, values))
        if "id" not in rec or rec["id"] is None:
            rec["id"] = self.next_id
            self.next_id += 1
        self.inserted_records.append((table, rec))
        return rec

    async def update_fields(self, table, data, where_column, where_value):
        self.updated_records.append((table, data, where_column, where_value))
        return 1

    async def update_where(self, table, data, where):
        self.updated_records.append((table, data, where))
        return 1

    async def delete(self, table, where_column, where_value):
        return None

    async def delete_where(self, table, where):
        return 1

    async def select(self, table, *args, **kwargs):
        return []

    async def insert_many(self, table, columns, values_list):
        cols = [c.strip() for c in columns.split(",")]
        for val_tuple in values_list:
            rec = dict(zip(cols, val_tuple))
            if "id" not in rec or rec["id"] is None:
                rec["id"] = self.next_id
                self.next_id += 1
            self.inserted_records.append((table, rec))

    async def _manager(self, sql, *params, **kwargs):
        self.raw_sqls.append((sql, params))
        return "UPDATE 1"

    def transaction(self):
        @asynccontextmanager
        async def dummy_tx():
            yield

        return dummy_tx()


class SyncPostgresEvent(Model):
    class Meta:
        table_name = "test_sync_datetime_events"

    id = Serial(primary_key=True)
    title = String(length=100)
    event_date = Date(auto_now_add=True)
    event_time = Time(auto_now_add=True)
    created_at = Timestamp(auto_now_add=True)
    created_at_tz = Timestamptz(auto_now_add=True)
    updated_at = Timestamp(auto_now=True)


class AsyncPostgresEvent(AsyncModel):
    class Meta:
        table_name = "test_async_datetime_events"

    id = Serial(primary_key=True)
    title = String(length=100)
    event_date = Date(auto_now_add=True)
    event_time = Time(auto_now_add=True)
    created_at = Timestamp(auto_now_add=True)
    created_at_tz = Timestamptz(auto_now_add=True)
    updated_at = Timestamp(auto_now=True)


class DateTimeIntegrationTestCase(unittest.TestCase):
    def setUp(self):
        self.db = DummyDB()
        Model.db = self.db

    def test_sync_auto_now_add_and_auto_now_create(self):
        event = SyncPostgresEvent.create(title="Meeting")
        self.assertIsInstance(event.event_date, datetime.date)
        self.assertIsInstance(event.event_time, datetime.time)
        self.assertIsInstance(event.created_at, datetime.datetime)
        self.assertIsInstance(event.created_at_tz, datetime.datetime)
        self.assertIsInstance(event.updated_at, datetime.datetime)

        last_inserted = self.db.inserted_records[-1][1]
        self.assertNotEqual(last_inserted["created_at"], "CURRENT_TIMESTAMP")
        self.assertIsInstance(last_inserted["created_at"], datetime.datetime)

        initial_updated_at = event.updated_at
        time.sleep(0.01)

        event.update(title="Updated Meeting")
        self.assertGreaterEqual(event.updated_at, initial_updated_at)

        last_updated = self.db.updated_records[-1][1]
        self.assertIn("updated_at", last_updated)
        self.assertIsInstance(last_updated["updated_at"], datetime.datetime)
        self.assertNotEqual(last_updated["updated_at"], "CURRENT_TIMESTAMP")

    def test_sync_save_update(self):
        event = SyncPostgresEvent(title="Conference")
        event.save()
        self.assertIsNotNone(event.id)
        self.assertIsInstance(event.created_at, datetime.datetime)

        first_updated_at = event.updated_at
        time.sleep(0.01)

        event.title = "Conference 2026"
        event.save()
        self.assertGreaterEqual(event.updated_at, first_updated_at)

        last_updated = self.db.updated_records[-1][1]
        self.assertIsInstance(last_updated["updated_at"], datetime.datetime)

    def test_sync_bulk_create_and_bulk_update(self):
        e1 = SyncPostgresEvent(title="Event 1")
        e2 = SyncPostgresEvent(title="Event 2")
        SyncPostgresEvent.bulk_create([e1, e2])

        self.assertEqual(len(self.db.inserted_records), 2)
        for _, rec in self.db.inserted_records:
            self.assertIsInstance(rec["created_at"], datetime.datetime)
            self.assertNotEqual(rec["created_at"], "CURRENT_TIMESTAMP")

        old_updated_at = e1.updated_at
        time.sleep(0.01)

        e1.title = "Event 1 Modified"
        SyncPostgresEvent.bulk_update([e1], fields=["title"])

        self.assertGreaterEqual(e1.updated_at, old_updated_at)


class AsyncDateTimeIntegrationTestCase(unittest.TestCase):
    def setUp(self):
        self.async_db = DummyAsyncDB()
        AsyncModel.db = self.async_db

    def test_async_auto_now_add_and_auto_now(self):
        async def run_test():
            event = await AsyncPostgresEvent.create(title="Async Event")
            self.assertIsInstance(event.event_date, datetime.date)
            self.assertIsInstance(event.event_time, datetime.time)
            self.assertIsInstance(event.created_at, datetime.datetime)
            self.assertIsInstance(event.created_at_tz, datetime.datetime)
            self.assertIsInstance(event.updated_at, datetime.datetime)

            last_inserted = self.async_db.inserted_records[-1][1]
            self.assertIsInstance(last_inserted["created_at"], datetime.datetime)
            self.assertNotEqual(last_inserted["created_at"], "CURRENT_TIMESTAMP")

            first_updated_at = event.updated_at
            await asyncio.sleep(0.01)

            await event.update(title="Updated Async Event")
            self.assertGreaterEqual(event.updated_at, first_updated_at)

            last_updated = self.async_db.updated_records[-1][1]
            self.assertIsInstance(last_updated["updated_at"], datetime.datetime)
            self.assertNotEqual(last_updated["updated_at"], "CURRENT_TIMESTAMP")

        asyncio.run(run_test())


if __name__ == "__main__":
    unittest.main()
