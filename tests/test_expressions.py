import unittest
from postgresdb3 import Q, F, Sum, Avg, Min, Max, Count
from postgresdb3.orm.expressions import FExpression


class ExpressionsTestCase(unittest.TestCase):
    def test_q_expressions(self):
        q1 = Q(name="Ali")
        q2 = Q(age__gt=20)

        q_and = q1 & q2
        self.assertEqual(q_and.connector, "AND")
        self.assertEqual(len(q_and.children), 2)

        q_or = q1 | q2
        self.assertEqual(q_or.connector, "OR")

        q_not = ~q1
        self.assertEqual(q_not.connector, "NOT")
        self.assertEqual(len(q_not.children), 1)

    def test_f_expressions(self):
        f = F("age")
        self.assertEqual(f.name, "age")

        f_add = f + 1
        self.assertTrue(isinstance(f_add, FExpression))
        self.assertEqual(f_add.name, "age")
        self.assertEqual(f_add.operator, "+")
        self.assertEqual(f_add.value, 1)

        f_sub = f - 5
        self.assertEqual(f_sub.operator, "-")

        f_mul = f * 2
        self.assertEqual(f_mul.operator, "*")

        f_div = f / 2
        self.assertEqual(f_div.operator, "/")

    def test_aggregate_expressions(self):
        self.assertEqual(Sum("price").to_sql(), "SUM(price)")
        self.assertEqual(Avg("score").to_sql(), "AVG(score)")
        self.assertEqual(Min("created_at").to_sql(), "MIN(created_at)")
        self.assertEqual(Max("updated_at").to_sql(), "MAX(updated_at)")
        self.assertEqual(Count("id").to_sql(), "COUNT(id)")
        self.assertEqual(Count("*").to_sql(), "COUNT(*)")


if __name__ == "__main__":
    unittest.main()
