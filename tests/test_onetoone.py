import unittest
from unittest.mock import MagicMock
from postgresdb3.orm import Model, fields
from postgresdb3.orm.meta import model_registry


class TestOneToOneField(unittest.TestCase):
    def setUp(self):
        model_registry.clear()
        Model.db = MagicMock()

    def test_one_to_one_field_definition_and_relation(self):
        class User(Model):
            id = fields.Serial(primary_key=True)
            username = fields.String(length=50)

        class Wallet(Model):
            id = fields.Serial(primary_key=True)
            user = fields.OneToOne(User, on_delete=fields.CASCADE)
            balance = fields.Integer(default=0)

        # 1. Verify SQL definition contains UNIQUE
        wallet_user_field = Wallet._fields["user_id"]
        self.assertTrue(wallet_user_field.unique)
        self.assertIn("UNIQUE", wallet_user_field.to_sql())

        # 2. Mock DB select for reverse relation: user.wallet -> returns Wallet instance
        Model.db.select.return_value = {"id": 5, "user_id": 1, "balance": 1000}

        u = User(id=1, username="ali")
        # Reverse relation user.wallet (singular name, not wallet_set)
        w = u.wallet
        self.assertIsNotNone(w)
        self.assertEqual(w.balance, 1000)


if __name__ == "__main__":
    unittest.main()
