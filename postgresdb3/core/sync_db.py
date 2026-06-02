from typing import Any, Optional
import psycopg2
from psycopg2 import pool
from psycopg2.extras import RealDictCursor
from contextlib import contextmanager
import threading
from postgresdb3.orm.expressions import Q, FExpression


class PostgresDB:
    """
    PostgreSQL bazasi bilan sinxron ishlash uchun asosiy sinf.
    Ichkarida `psycopg2.pool.ThreadedConnectionPool` orqali ulanishlar hovuzini (connection pool) boshqaradi.
    Katta yuklamalarda ham qotib qolmaslik uchun mo'ljallangan.
    """

    def __init__(
            self, database: str, user: str, password: str, host: str = "localhost", port: int = 5432,
            minconn: int = 1, maxconn: int = 20, echo: bool = False
    ) -> None:
        self.echo = echo
        self.pool = pool.ThreadedConnectionPool(
            minconn, maxconn,
            database=database, user=user, password=password, host=host, port=port
        )
        self._local = threading.local()

    def _manager(
            self,
            sql: str,
            params: Optional[list | tuple] = None,
            *,
            commit: bool = False,
            many: bool = False,
            fetchone: bool = False,
            fetchall: bool = False,
            fetchmany: int | None = None
    ) -> Any:

        if self.echo:
            print(f"\033[94m[SQL]: {sql} \n[PARAMS]: {params}\033[0m")

        if not sql or not sql.strip():
            raise ValueError("SQL query cannot be empty")
        if fetchone and fetchall:
            raise ValueError("fetchone and fetchall cannot be True at the same time")
        if many and (fetchone or fetchall or fetchmany):
            raise ValueError("cannot use fetchone/fetchall/fetchmany with many=True")

        in_transaction = getattr(self._local, "conn", None) is not None
        conn = self._local.conn if in_transaction else self.pool.getconn()
        
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                if many:
                    cursor.executemany(sql, params)
                    result = None
                else:
                    cursor.execute(sql, params)
                    if fetchone:
                        result = cursor.fetchone()
                    elif fetchall:
                        result = cursor.fetchall()
                    elif fetchmany is not None:
                        result = cursor.fetchmany(fetchmany)
                    else:
                        result = None

                if commit and not in_transaction:
                    conn.commit()

            return result
        finally:
            if not in_transaction:
                self.pool.putconn(conn)

    def close(self) -> None:
        if self.pool:
            self.pool.closeall()
            self.pool = None

    def raw(
            self,
            sql: str,
            params: list | tuple | None = None,
            *,
            commit: bool = False,
            many: bool = False,
            fetchone: bool = False,
            fetchall: bool = False,
            fetchmany: int | None = None
    ) -> Any:

        return self._manager(
            sql,
            params,
            commit=commit,
            many=many,
            fetchone=fetchone,
            fetchall=fetchall,
            fetchmany=fetchmany,
        )

    def create(self, table: str, columns: str) -> None:
        sql = f"CREATE TABLE IF NOT EXISTS {table} ({columns})"
        self._manager(sql, commit=True)

    def drop(self, table: str, cascade: bool = False) -> None:
        sql = f"DROP TABLE IF EXISTS {table}"
        if cascade:
            sql += " CASCADE"
        self._manager(sql, commit=True)

    def _build_where(self, where: Any) -> tuple[str, list]:
        if where is None:
            return "", []

        if isinstance(where, tuple) and len(where) == 2:
            condition, values = where
            return condition, list(values)

        if isinstance(where, dict):
            clauses = []
            params = []

            operator_map = {
                "eq": "=",
                "ne": "!=",
                "not": "!=",
                "gt": ">",
                "gte": ">=",
                "lt": "<",
                "lte": "<=",
                "like": "LIKE",
                "ilike": "ILIKE",
            }

            for key, value in where.items():
                if "__" in key:
                    field, op = key.rsplit("__", 1)
                else:
                    field, op = key, "eq"

                if op in operator_map:
                    clauses.append(f"{field} {operator_map[op]} %s")
                    params.append(value)

                elif op == "in":
                    if not isinstance(value, (list, tuple)) or not value:
                        raise ValueError(f"{field}__in uchun bo'sh bo'lmagan list/tuple kerak")
                    placeholders = ", ".join(["%s"] * len(value))
                    clauses.append(f"{field} IN ({placeholders})")
                    params.extend(value)

                elif op == "not_in":
                    if not isinstance(value, (list, tuple)) or not value:
                        raise ValueError(f"{field}__not_in uchun bo'sh bo'lmagan list/tuple kerak")
                    placeholders = ", ".join(["%s"] * len(value))
                    clauses.append(f"{field} NOT IN ({placeholders})")
                    params.extend(value)

                elif op == "isnull":
                    if value:
                        clauses.append(f"{field} IS NULL")
                    else:
                        clauses.append(f"{field} IS NOT NULL")

                else:
                    raise ValueError(f"Noma'lum operator: {op}")

            return " AND ".join(clauses), params

        if isinstance(where, Q):
            if not where.children and not where.conditions:
                return "", []

            clauses = []
            params = []

            if where.conditions:
                condition_sql, condition_params = self._build_where(where.conditions)
                if condition_sql:
                    clauses.append(f"({condition_sql})")
                    params.extend(condition_params)

            for child in where.children:
                child_sql, child_params = self._build_where(child)
                if child_sql:
                    clauses.append(f"({child_sql})")
                    params.extend(child_params)

            if where.connector == "NOT":
                return f"NOT ({clauses[0]})", params
            
            return f" {where.connector} ".join(clauses), params

        if isinstance(where, list):
            clauses = []
            params = []

            for item in where:
                if len(item) != 3:
                    raise ValueError("List formatidagi where elementlari (field, operator, value) bo'lishi kerak")

                field, operator, value = item
                op = operator.upper()

                if op in {"=", "!=", ">", ">=", "<", "<=", "LIKE", "ILIKE"}:
                    clauses.append(f"{field} {op} %s")
                    params.append(value)

                elif op in {"IN", "NOT IN"}:
                    if not isinstance(value, (list, tuple)) or not value:
                        raise ValueError(f"{field} {op} uchun bo'sh bo'lmagan list/tuple kerak")
                    placeholders = ", ".join(["%s"] * len(value))
                    clauses.append(f"{field} {op} ({placeholders})")
                    params.extend(value)

                elif op == "IS NULL":
                    clauses.append(f"{field} IS NULL")

                elif op == "IS NOT NULL":
                    clauses.append(f"{field} IS NOT NULL")

                else:
                    raise ValueError(f"Noma'lum operator: {operator}")

            return " AND ".join(clauses), params

        raise TypeError("where tuple, dict yoki list bo'lishi kerak")

    def _validate_identifier(self, value: str, name: str = "identifier") -> str:
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"{name} bo'sh bo'lmasligi kerak")

        cleaned = value.replace("_", "").replace(".", "")
        if not cleaned.isalnum():
            raise ValueError(f"Invalid {name}: {value}")

        return value

    def _normalize_columns(self, columns: str | list[str]) -> str:
        if isinstance(columns, list):
            if not columns:
                raise ValueError("columns bo'sh list bo'lmasligi kerak")

            validated_columns = [self._validate_identifier(col, "column") for col in columns]
            return ", ".join(validated_columns)

        if not isinstance(columns, str) or not columns.strip():
            raise ValueError("columns noto'g'ri bo'lishi mumkin emas")

        return columns

    def select(
            self,
            table: str,
            columns: str | list[str] = "*",
            where: tuple | dict | list | None = None,
            join: list[tuple] | None = None,
            group_by: str | None = None,
            order_by: str | None = None,
            limit: int | None = None,
            offset: int | None = None,
            fetchone: bool = False,
            fetchmany: int | None = None
    ) -> Any:
        table = self._validate_identifier(table, "table")
        columns = self._normalize_columns(columns)

        sql = f"SELECT {columns} FROM {table}"
        params = []

        if join:
            for join_type, join_table, on_condition in join:
                join_table = self._validate_identifier(join_table, "join table")
                sql += f" {join_type} {join_table} ON {on_condition}"

        if where:
            condition, values = self._build_where(where)
            if condition:
                sql += f" WHERE {condition}"
                params.extend(values)

        if group_by:
            sql += f" GROUP BY {group_by}"

        if order_by:
            sql += f" ORDER BY {order_by}"

        if limit is not None:
            sql += " LIMIT %s"
            params.append(limit)

        if offset is not None:
            sql += " OFFSET %s"
            params.append(offset)

        if fetchone:
            return self._manager(sql, params, fetchone=True)
        elif fetchmany is not None:
            return self._manager(sql, params, fetchmany=fetchmany)
        else:
            return self._manager(sql, params, fetchall=True)

    def insert(self, table: str, columns: str, values: tuple | list, returning: str | None = None):
        placeholders = ", ".join(["%s"] * len(values))
        sql = f"INSERT INTO {table} ({columns}) VALUES ({placeholders})"

        if returning:
            sql += f" RETURNING {returning}"
            return self._manager(sql, values, fetchone=True, commit=True)

        self._manager(sql, values, commit=True)

    def insert_many(self, table: str, columns: str, values_list: list[tuple]) -> None:
        if not values_list:
            raise ValueError("values_list bo'sh bo'lishi mumkin emas")

        placeholders = ", ".join(["%s"] * len(values_list[0]))
        sql = f"INSERT INTO {table} ({columns}) VALUES ({placeholders})"

        self._manager(sql, values_list, commit=True, many=True)

    def update(self, table: str, set_column: str, set_value: Any, where_column: str, where_value: Any) -> None:
        sql = f"UPDATE {table} SET {set_column} = %s WHERE {where_column} = %s"
        self._manager(sql, (set_value, where_value), commit=True)

    def update_fields(self, table: str, data: dict, where_column: str, where_value: Any) -> int:
        table = self._validate_identifier(table, "table")
        where_column = self._validate_identifier(where_column, "where column")

        if not data:
            raise ValueError("Yangilash uchun data bo'sh bo'lmasligi kerak")

        set_parts = []
        params = []

        for key, value in data.items():
            key = self._validate_identifier(key, "column")
            if isinstance(value, FExpression):
                set_parts.append(f"{key} = {value.name} {value.operator} %s")
                params.append(value.value)
            else:
                set_parts.append(f"{key} = %s")
                params.append(value)

        params.append(where_value)

        sql = f"UPDATE {table} SET {', '.join(set_parts)} WHERE {where_column} = %s"

        conn = self.pool.getconn()
        try:
            with conn.cursor() as cursor:
                cursor.execute(sql, tuple(params))
                affected_rows = cursor.rowcount
                conn.commit()
        finally:
            self.pool.putconn(conn)

        return affected_rows

    def update_where(self, table: str, data: dict, where: tuple | dict | list) -> int:
        table = self._validate_identifier(table, "table")

        if not data:
            raise ValueError("Yangilash uchun data bo'sh bo'lmasligi kerak")

        if not where:
            raise ValueError("update_where uchun where bo'sh bo'lmasligi kerak")

        set_parts = []
        params = []

        for key, value in data.items():
            key = self._validate_identifier(key, "column")
            if isinstance(value, FExpression):
                set_parts.append(f"{key} = {value.name} {value.operator} %s")
                params.append(value.value)
            else:
                set_parts.append(f"{key} = %s")
                params.append(value)

        where_sql, where_params = self._build_where(where)
        if not where_sql:
            raise ValueError("WHERE sharti noto'g'ri")

        sql = f"UPDATE {table} SET {', '.join(set_parts)} WHERE {where_sql}"
        params.extend(where_params)

        conn = self.pool.getconn()
        try:
            with conn.cursor() as cursor:
                cursor.execute(sql, tuple(params))
                affected_rows = cursor.rowcount
                conn.commit()
        finally:
            self.pool.putconn(conn)

        return affected_rows

    def delete(self, table: str, where_column: str, where_value: Any) -> None:
        sql = f"DELETE FROM {table} WHERE {where_column} = %s"
        self._manager(sql, (where_value,), commit=True)


    def delete_where(self, table: str, where: tuple | dict | list) -> int:
        table = self._validate_identifier(table, "table")

        if not where:
            raise ValueError("delete_where uchun where bo'sh bo'lmasligi kerak")

        where_sql, where_params = self._build_where(where)
        if not where_sql:
            raise ValueError("WHERE sharti noto'g'ri")

        sql = f"DELETE FROM {table} WHERE {where_sql}"

        conn = self.pool.getconn()
        try:
            with conn.cursor() as cursor:
                cursor.execute(sql, tuple(where_params))
                affected_rows = cursor.rowcount
                conn.commit()
        finally:
            self.pool.putconn(conn)

        return affected_rows

    def exists_where(
            self,
            table: str,
            where: tuple | dict | list | None = None,
            join: list[tuple] | None = None,
            group_by: str | None = None,
    ) -> bool:
        table = self._validate_identifier(table, "table")

        sql = f"SELECT 1 FROM {table}"
        params = []

        if join:
            for join_type, join_table, on_condition in join:
                join_table = self._validate_identifier(join_table, "join table")
                sql += f" {join_type} {join_table} ON {on_condition}"

        if where:
            condition, values = self._build_where(where)
            if condition:
                sql += f" WHERE {condition}"
                params.extend(values)

        if group_by:
            sql += f" GROUP BY {group_by}"

        sql += " LIMIT 1"

        record = self._manager(sql, params, fetchone=True)
        return record is not None

    def list_tables(self, schema="public") -> list[tuple]:
        sql = """
              SELECT table_name
              FROM information_schema.tables
              WHERE table_schema = %s
              ORDER BY table_name; \
              """
        return self._manager(sql, (schema,), fetchall=True)

    def describe_table(self, table: str, schema: str = "public") -> list[tuple]:
        sql = """
              SELECT column_name,
                     data_type,
                     is_nullable,
                     column_default
              FROM information_schema.columns
              WHERE table_schema = %s
                AND table_name = %s
              ORDER BY ordinal_position; \
              """
        return self._manager(sql, (schema, table), fetchall=True)

    def alter(self, table: str, action: str) -> Any:
        sql = f"ALTER TABLE {table} {action}"
        return self._manager(sql, commit=True)
        
    @contextmanager
    def transaction(self):
        conn = self.pool.getconn()
        self._local.conn = conn
        try:
            with conn:                                                                 
                yield conn
        finally:
            self._local.conn = None
            self.pool.putconn(conn)
        
    def close_pool(self):
        if self.pool:
            self.pool.closeall()
