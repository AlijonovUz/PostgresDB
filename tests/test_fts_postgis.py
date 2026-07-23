import unittest
from unittest.mock import MagicMock, patch
from postgresdb3.orm import Model, fields
from postgresdb3.orm.meta import model_registry
from postgresdb3 import PostgresDB


class TestFTSAndPostGIS(unittest.TestCase):
    def setUp(self):
        model_registry.clear()

    def test_full_text_search_where_building(self):
        with patch("psycopg2.pool.ThreadedConnectionPool"):
            db = PostgresDB("mydb", "user", "pass")

        sql, params = db._build_where({"content__search": "python ORM"})
        self.assertEqual(
            sql, "to_tsvector('english', content) @@ plainto_tsquery('english', %s)"
        )
        self.assertEqual(params, ["python ORM"])

    def test_postgis_distance_where_building(self):
        with patch("psycopg2.pool.ThreadedConnectionPool"):
            db = PostgresDB("mydb", "user", "pass")

        # lat=41.311, lon=69.240, distance=5000m (5km radius)
        sql, params = db._build_where(
            {"location__distance_lte": (41.311, 69.240, 5000)}
        )
        self.assertEqual(
            sql,
            "ST_DWithin(location::geography, ST_SetSRID(ST_MakePoint(%s, %s), 4326)::geography, %s)",
        )
        self.assertEqual(params, [69.240, 41.311, 5000])

    def test_point_field_sql_type(self):
        class Store(Model):
            name = fields.String(length=100)
            location = fields.Point(srid=4326)

        point_field = Store._fields["location"]
        self.assertEqual(point_field.sql_type, "geometry(Point, 4326)")


if __name__ == "__main__":
    unittest.main()
