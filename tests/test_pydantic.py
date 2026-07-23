import unittest
from postgresdb3.orm import Model, fields
from postgresdb3.orm.meta import model_registry


class TestPydanticSchemaGeneration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        try:
            import pydantic
        except ImportError:
            raise unittest.SkipTest("pydantic is not installed")

    def setUp(self):
        model_registry.clear()

    def test_to_pydantic_schema_generation(self):
        class User(Model):
            id = fields.Serial(primary_key=True)
            username = fields.String(length=50)
            email = fields.String(length=100)
            password = fields.String(length=128)
            age = fields.Integer(default=18, nullable=True)

        # 1. Full Response Schema
        UserSchema = User.to_pydantic(name="UserSchema")
        self.assertIn("id", UserSchema.model_fields)
        self.assertIn("username", UserSchema.model_fields)
        self.assertIn("password", UserSchema.model_fields)

        # Validate Pydantic data
        u_data = UserSchema(
            id=1, username="ali", email="ali@example.com", password="secret_hash"
        )
        self.assertEqual(u_data.username, "ali")

        # 2. Schema with exclude=["id"] (Create/POST schema)
        UserCreateSchema = User.to_pydantic(name="UserCreateSchema", exclude=["id"])
        self.assertNotIn("id", UserCreateSchema.model_fields)
        self.assertIn("username", UserCreateSchema.model_fields)

        # 3. Custom Exclude Schema (e.g. exclude password and id)
        UserPublicSchema = User.to_pydantic(
            name="UserPublicSchema", exclude=["password", "id"]
        )
        self.assertNotIn("password", UserPublicSchema.model_fields)
        self.assertNotIn("id", UserPublicSchema.model_fields)
        self.assertIn("username", UserPublicSchema.model_fields)
        self.assertIn("email", UserPublicSchema.model_fields)

        # 4. Custom Include Schema (e.g. only username and age)
        UserSimpleSchema = User.to_pydantic(
            name="UserSimpleSchema", include=["username", "age"]
        )
        self.assertIn("username", UserSimpleSchema.model_fields)
        self.assertIn("age", UserSimpleSchema.model_fields)
        self.assertNotIn("email", UserSimpleSchema.model_fields)

        # 5. Optional Parameter Schema (Specific fields)
        UserPartialSchema = User.to_pydantic(
            name="UserPartialSchema", exclude=["id"], optional=["email", "username"]
        )
        # Email and username are now optional (can instantiate without them)
        patch_obj = UserPartialSchema(password="secret")
        self.assertIsNone(patch_obj.username)
        self.assertIsNone(patch_obj.email)

        # 6. Optional=True (All fields optional - ideal for PATCH)
        UserPatchSchema = User.to_pydantic(
            name="UserPatchSchema", exclude=["id"], optional=True
        )
        patch_empty = UserPatchSchema()
        self.assertIsNone(patch_empty.username)
        self.assertIsNone(patch_empty.password)

        # 7. Default value handling test
        user_with_default = UserSchema(
            id=2, username="bob", email="bob@test.com", password="pass"
        )
        self.assertEqual(user_with_default.age, 18)

    def test_pydantic_validators_integration(self):
        from postgresdb3.orm.validators import MinValueValidator, EmailValidator
        import pydantic

        class Account(Model):
            age = fields.Integer(validators=[MinValueValidator(18)])
            email = fields.String(length=100, validators=[EmailValidator()])

        AccountSchema = Account.to_pydantic()

        # Valid input -> Should pass
        valid_acc = AccountSchema(age=25, email="user@domain.com")
        self.assertEqual(valid_acc.age, 25)

        # Invalid age (< 18) -> Pydantic should raise ValidationError
        with self.assertRaises(pydantic.ValidationError):
            AccountSchema(age=15, email="user@domain.com")

        # Invalid email -> Pydantic should raise ValidationError
        with self.assertRaises(pydantic.ValidationError):
            AccountSchema(age=20, email="invalid-email")


if __name__ == "__main__":
    unittest.main()
