import unittest
from unittest.mock import MagicMock
from postgresdb3.orm import Model, fields
from postgresdb3.orm.meta import model_registry


class TestAuditFeatures(unittest.TestCase):
    def setUp(self):
        model_registry.clear()
        Model.db = MagicMock()

    def test_nested_select_related(self):
        class ParentCategory(Model):
            id = fields.Serial(primary_key=True)
            name = fields.String(length=50)

        class Category(Model):
            id = fields.Serial(primary_key=True)
            name = fields.String(length=50)
            parent = fields.ForeignKey(ParentCategory, on_delete=fields.CASCADE, nullable=True)

        class Product(Model):
            id = fields.Serial(primary_key=True)
            name = fields.String(length=100)
            category = fields.ForeignKey(Category, on_delete=fields.CASCADE)

        Product.db = MagicMock()
        Product.db.select.return_value = [{
            "id": 101,
            "name": "MacBook Pro",
            "category_id": 5,
            "__rel__category__id": 5,
            "__rel__category__name": "Laptops",
            "__rel__category__parent_id": 1,
            "__rel__category__parent__id": 1,
            "__rel__category__parent__name": "Computers"
        }]

        p = Product.query().select_related("category__parent").first()
        self.assertIsNotNone(p)
        self.assertEqual(p.name, "MacBook Pro")
        self.assertIsNotNone(p.category)
        self.assertEqual(p.category.name, "Laptops")
        self.assertIsNotNone(p.category.parent)
        self.assertEqual(p.category.parent.name, "Computers")

    def test_values_with_relation_columns(self):
        class Category(Model):
            id = fields.Serial(primary_key=True)
            name = fields.String(length=50)

        class Product(Model):
            id = fields.Serial(primary_key=True)
            name = fields.String(length=100)
            category = fields.ForeignKey(Category, on_delete=fields.CASCADE)

        Product.db = MagicMock()
        Product.db.select.return_value = [{"name": "Olma", "category__name": "Mevalar"}]

        res = Product.query().values("name", "category__name").all()
        self.assertEqual(res, [{"name": "Olma", "category__name": "Mevalar"}])

        call_args = Product.db.select.call_args
        columns = call_args.kwargs.get("columns")
        self.assertIn('category.name AS "category__name"', columns)

    def test_force_bulk_update_and_delete(self):
        class User(Model):
            id = fields.Serial(primary_key=True)
            status = fields.String(default="inactive")

        User.db = MagicMock()
        User.db.update_where.return_value = 10
        User.db.delete_where.return_value = 10

        # Without filter or force -> raises ValueError
        with self.assertRaises(ValueError):
            User.query().update(status="active")

        with self.assertRaises(ValueError):
            User.query().delete()

        # With force=True -> succeeds
        res_up = User.query().update(force=True, status="active")
        self.assertEqual(res_up, 10)

        res_del = User.query().delete(force=True)
        self.assertEqual(res_del, 10)

        # With .force() chain -> succeeds
        res_up2 = User.query().force().update(status="active")
        self.assertEqual(res_up2, 10)

        res_del2 = User.query().force().delete()
        self.assertEqual(res_del2, 10)


if __name__ == "__main__":
    unittest.main()
