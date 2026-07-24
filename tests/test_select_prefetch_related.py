import unittest
from unittest.mock import MagicMock
from postgresdb3.orm import Model, AsyncModel, fields
from postgresdb3.orm.meta import model_registry


class TestSelectAndPrefetchRelated(unittest.TestCase):
    def setUp(self):
        model_registry.clear()
        Model.db = MagicMock()

    def test_select_and_prefetch_related_both_names(self):
        class Category(Model):
            id = fields.Serial(primary_key=True)
            name = fields.String(length=50)

        class Product(Model):
            id = fields.Serial(primary_key=True)
            category = fields.ForeignKey(Category, on_delete=fields.CASCADE)
            title = fields.String(length=100)

        # Product._fields must have 'category_id'
        self.assertIn("category_id", Product._fields)
        self.assertNotIn("category", Product._fields)

        # Test select_related with 'category' (relation descriptor name)
        qs1 = Product.filter().select_related("category")
        self.assertTrue(any("LEFT JOIN category" in j[0] + " " + j[1] for j in qs1._join))
        self.assertTrue(any("product.category_id = category.id" in j[2] for j in qs1._join))

        # Test select_related with 'category_id' (db column name)
        qs2 = Product.filter().select_related("category_id")
        self.assertTrue(any("LEFT JOIN category" in j[0] + " " + j[1] for j in qs2._join))
        self.assertTrue(any("product.category_id = category.id" in j[2] for j in qs2._join))

        # Test prefetch_related with both names
        qs3 = Product.filter().prefetch_related("category")
        self.assertIn("category", qs3._prefetch)

        qs4 = Product.filter().prefetch_related("category_id")
        self.assertIn("category", qs4._prefetch)

    def test_async_select_related_both_names(self):
        class AsyncCategory(AsyncModel):
            id = fields.Serial(primary_key=True)
            name = fields.String(length=50)

        class AsyncProduct(AsyncModel):
            id = fields.Serial(primary_key=True)
            category = fields.ForeignKey(AsyncCategory, on_delete=fields.CASCADE)
            title = fields.String(length=100)

        # Test select_related with 'category' on AsyncModel / AsyncQuerySet
        qs1 = AsyncProduct.query().select_related("category")
        self.assertTrue(any("LEFT JOIN async_category" in j[0] + " " + j[1] for j in qs1._join))
        self.assertTrue(any("async_product.category_id = async_category.id" in j[2] for j in qs1._join))

        # Test select_related with 'category_id' on AsyncModel / AsyncQuerySet
        qs2 = AsyncProduct.query().select_related("category_id")
        self.assertTrue(any("LEFT JOIN async_category" in j[0] + " " + j[1] for j in qs2._join))
        self.assertTrue(any("async_product.category_id = async_category.id" in j[2] for j in qs2._join))

    def test_ordering_prefix(self):
        class OrderItem(Model):
            id = fields.Serial(primary_key=True)
            created_at = fields.String()

            class Meta:
                ordering = ["-created_at"]

        class AsyncOrderItem(AsyncModel):
            id = fields.Serial(primary_key=True)
            created_at = fields.String()

            class Meta:
                ordering = ["-created_at"]

        qs_sync = OrderItem.query()
        self.assertEqual(qs_sync._get_order_by_sql(), "order_item.created_at DESC")

        qs_async = AsyncOrderItem.query()
        self.assertEqual(qs_async._get_order_by_sql(), "async_order_item.created_at DESC")

    def test_select_related_columns_prefix(self):
        class Category(Model):
            id = fields.Serial(primary_key=True)
            name = fields.String(length=50)

        class Product(Model):
            id = fields.Serial(primary_key=True)
            name = fields.String(length=100)
            category = fields.ForeignKey(Category, on_delete=fields.CASCADE)

        # Mock db.select to verify columns argument
        Product.db = MagicMock()
        Product.db.select.return_value = []

        Product.query().select_related("category").all()
        call_args = Product.db.select.call_args
        columns = call_args.kwargs.get("columns")
        self.assertIn("product.id AS id", columns)
        self.assertIn("category.id AS __rel__category__id", columns)

    def test_select_related_first_and_last(self):
        class Category(Model):
            id = fields.Serial(primary_key=True)
            name = fields.String(length=50)

        class Product(Model):
            id = fields.Serial(primary_key=True)
            name = fields.String(length=100)
            category = fields.ForeignKey(Category, on_delete=fields.CASCADE)

        Product.db = MagicMock()
        Product.db.select.return_value = [{
            "id": 1,
            "name": "Laptop",
            "category_id": 10,
            "__rel__category__id": 10,
            "__rel__category__name": "Electronics"
        }]

        p = Product.query().select_related("category").first()
        self.assertIsNotNone(p)
        self.assertEqual(p.name, "Laptop")
        self.assertEqual(p.category.name, "Electronics")


if __name__ == "__main__":
    unittest.main()




