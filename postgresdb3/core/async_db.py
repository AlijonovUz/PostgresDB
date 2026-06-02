import asyncpg
import asyncio
from typing import Any, List, Optional
from postgresdb3.orm.expressions import Q, FExpression
from contextlib import asynccontextmanager
import contextvars

_async_conn = contextvars.ContextVar("async_conn", default=None)


class AsyncPostgresDB:
    """
    PostgreSQL bazasi bilan asinxron (async/await) ishlash uchun asosiy sinf.
    Ichkarida `asyncpg.pool.Pool` orqali ulanishlar hovuzini (connection pool) boshqaradi.
    """
    def __init__(self, database: str, user: str, password: str, host: str = "localhost", port: int = 5432, min_size: int = 1, max_size: int = 20, echo: bool = False) -> None:
        self.database = database
        self.user = user
        self.password = password
        self.host = host
        self.port = port
        self.min_size = min_size
        self.max_size = max_size
        self.echo = echo
        self.pool: Optional[asyncpg.pool.Pool] = None
        self._pool_lock = None
        self._async_conn = contextvars.ContextVar(f"async_conn_{id(self)}", default=None)

    async def _manager(self, sql: str, *params, fetchone=False, fetchall=False, commit=False, many=False) -> Any:
        if "%s" in sql:
            parts = sql.split("%s")
            sql = "".join([part + f"${i+1}" for i, part in enumerate(parts[:-1])]) + parts[-1]
            
        if self.echo:
            print(f"\033[94m[SQL]: {sql} \n[PARAMS]: {params}\033[0m")
        if not self.pool:
            if self._pool_lock is None:
                self._pool_lock = asyncio.Lock()
            async with self._pool_lock:
                if not self.pool:
                    self.pool = await asyncpg.create_pool(
                        database=self.database,
                        user=self.user,
                        password=self.password,
                        host=self.host,
                        port=self.port,
                        min_size=self.min_size,
                        max_size=self.max_size
                    )

        conn = self._async_conn.get()
        is_transaction = conn is not None
        
        if not is_transaction:
            conn = await self.pool.acquire()

        try:
            if commit:
                if many:
                    return await conn.executemany(sql, params[0])
                return await conn.execute(sql, *params)
            if fetchone:
                return await conn.fetchrow(sql, *params)
            if fetchall:
                return await conn.fetch(sql, *params)
        finally:
            if not is_transaction:
                await self.pool.release(conn)

    async def close_pool(self) -> None:
        if self.pool:
            await self.pool.close()
            self.pool = None

    async def create(self, table: str, columns: str) -> None:
        await self._manager(f"CREATE TABLE IF NOT EXISTS {table} ({columns})", commit=True)

    async def drop(self, table: str, cascade: bool = False) -> None:
        sql = f"DROP TABLE IF EXISTS {table}"
        if cascade:
            sql += " CASCADE"

        await self._manager(sql, commit=True)

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

    def _build_where(self, where: Any, start_index: int = 1) -> tuple[str, list]:
        if where is None:
            return "", []

        if isinstance(where, tuple) and len(where) == 2:
            condition, values = where
            return condition, list(values)

        if isinstance(where, dict):
            clauses = []
            params = []
            index = start_index

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

                self._validate_identifier(field, "where field")

                if op in operator_map:
                    clauses.append(f"{field} {operator_map[op]} ${index}")
                    params.append(value)
                    index += 1

                elif op == "in":
                    if not isinstance(value, (list, tuple)) or not value:
                        raise ValueError(f"{field}__in uchun bo'sh bo'lmagan list/tuple kerak")

                    placeholders = ", ".join(f"${i}" for i in range(index, index + len(value)))
                    clauses.append(f"{field} IN ({placeholders})")
                    params.extend(value)
                    index += len(value)

                elif op == "not_in":
                    if not isinstance(value, (list, tuple)) or not value:
                        raise ValueError(f"{field}__not_in uchun bo'sh bo'lmagan list/tuple kerak")

                    placeholders = ", ".join(f"${i}" for i in range(index, index + len(value)))
                    clauses.append(f"{field} NOT IN ({placeholders})")
                    params.extend(value)
                    index += len(value)

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
            index = start_index

            if where.conditions:
                condition_sql, condition_params = self._build_where(where.conditions, index)
                if condition_sql:
                    clauses.append(f"({condition_sql})")
                    params.extend(condition_params)
                    index += len(condition_params)

            for child in where.children:
                child_sql, child_params = self._build_where(child, index)
                if child_sql:
                    clauses.append(f"({child_sql})")
                    params.extend(child_params)
                    index += len(child_params)

            if where.connector == "NOT":
                return f"NOT ({clauses[0]})", params
            
            return f" {where.connector} ".join(clauses), params

        if isinstance(where, list):
            clauses = []
            params = []
            index = start_index

            for item in where:
                if len(item) != 3:
                    raise ValueError("List formatidagi where elementlari (field, operator, value) bo'lishi kerak")

                field, operator, value = item
                self._validate_identifier(field, "where field")
                op = operator.upper()

                if op in {"=", "!=", ">", ">=", "<", "<=", "LIKE", "ILIKE"}:
                    clauses.append(f"{field} {op} ${index}")
                    params.append(value)
                    index += 1

                elif op in {"IN", "NOT IN"}:
                    if not isinstance(value, (list, tuple)) or not value:
                        raise ValueError(f"{field} {op} uchun bo'sh bo'lmagan list/tuple kerak")

                    placeholders = ", ".join(f"${i}" for i in range(index, index + len(value)))
                    clauses.append(f"{field} {op} ({placeholders})")
                    params.extend(value)
                    index += len(value)

                elif op == "IS NULL":
                    clauses.append(f"{field} IS NULL")

                elif op == "IS NOT NULL":
                    clauses.append(f"{field} IS NOT NULL")

                else:
                    raise ValueError(f"Noma'lum operator: {operator}")

            return " AND ".join(clauses), params

        raise TypeError("where tuple, dict yoki list bo'lishi kerak")

    async def select(
            self,
            table: str,
            columns: str | list[str] = "*",
            where: tuple | dict | list | None = None,
            join: Optional[List[tuple]] = None,
            group_by: Optional[str] = None,
            order_by: Optional[str] = None,
            limit: Optional[int] = None,
            offset: Optional[int] = None,
            fetchone: bool = False
    ) -> Any:
        table = self._validate_identifier(table, "table")
        columns = self._normalize_columns(columns)

        sql = f"SELECT {columns} FROM {table}"
        params: List[Any] = []

        if join:
            for join_type, join_table, on_condition in join:
                join_table = self._validate_identifier(join_table, "join table")
                sql += f" {join_type} {join_table} ON {on_condition}"

        if where:
            condition, values = self._build_where(where, start_index=1)
            if condition:
                sql += f" WHERE {condition}"
                params.extend(values)

        if group_by:
            sql += f" GROUP BY {group_by}"

        if order_by:
            sql += f" ORDER BY {order_by}"

        if limit is not None:
            sql += f" LIMIT ${len(params) + 1}"
            params.append(limit)

        if offset is not None:
            sql += f" OFFSET ${len(params) + 1}"
            params.append(offset)

        return await self._manager(sql, *params, fetchone=fetchone, fetchall=not fetchone)

    async def insert(self, table: str, columns: str, values: list, returning: str | None = None):
        placeholders = ", ".join(f"${i + 1}" for i in range(len(values)))
        sql = f"INSERT INTO {table} ({columns}) VALUES ({placeholders})"

        if returning:
            sql += f" RETURNING {returning}"
            return await self._manager(sql, *values, fetchone=True)

        await self._manager(sql, *values, commit=True)

    async def insert_many(self, table: str, columns: str, values_list: List[List[Any]]) -> None:
        if not values_list:
            raise ValueError("values_list bo'sh bo'lishi mumkin emas")

        placeholders_list = []
        flat_values = []
        counter = 1

        for values in values_list:
            placeholders = ", ".join(f"${i}" for i in range(counter, counter + len(values)))
            placeholders_list.append(f"({placeholders})")
            flat_values.extend(values)
            counter += len(values)

        sql = f"INSERT INTO {table} ({columns}) VALUES {', '.join(placeholders_list)}"
        await self._manager(sql, *flat_values, commit=True)

    async def update(self, table: str, set_column: str, set_value: Any, where_column: str, where_value: Any) -> None:
        sql = f"UPDATE {table} SET {set_column} = $1 WHERE {where_column} = $2"
        await self._manager(sql, set_value, where_value, commit=True)

    async def update_fields(self, table: str, data: dict, where_column: str, where_value: Any) -> int:
        table = self._validate_identifier(table, "table")
        where_column = self._validate_identifier(where_column, "where column")

        if not data:
            raise ValueError("Yangilash uchun data bo'sh bo'lmasligi kerak")

        set_parts = []
        params = []
        index = 1

        for key, value in data.items():
            key = self._validate_identifier(key, "column")
            if isinstance(value, FExpression):
                set_parts.append(f"{key} = {value.name} {value.operator} ${index}")
                params.append(value.value)
            else:
                set_parts.append(f"{key} = ${index}")
                params.append(value)
            index += 1

        sql = f"UPDATE {table} SET {', '.join(set_parts)} WHERE {where_column} = ${index}"
        params.append(where_value)

        result = await self._manager(sql, *params, commit=True)
        return int(result.split()[-1])

    async def update_where(self, table: str, data: dict, where: tuple | dict | list) -> int:
        table = self._validate_identifier(table, "table")

        if not data:
            raise ValueError("Yangilash uchun data bo'sh bo'lmasligi kerak")

        if not where:
            raise ValueError("update_where uchun where bo'sh bo'lmasligi kerak")

        set_parts = []
        params = []
        index = 1

        for key, value in data.items():
            key = self._validate_identifier(key, "column")
            if isinstance(value, FExpression):
                set_parts.append(f"{key} = {value.name} {value.operator} ${index}")
                params.append(value.value)
            else:
                set_parts.append(f"{key} = ${index}")
                params.append(value)
            index += 1

        where_sql, where_params = self._build_where(where, start_index=index)

        if not where_sql:
            raise ValueError("WHERE sharti noto'g'ri")

        sql = f"UPDATE {table} SET {', '.join(set_parts)} WHERE {where_sql}"

        result = await self._manager(
            sql,
            *(params + where_params),
            commit=True
        )

        return int(result.split()[-1])

    async def delete(self, table: str, where_column: str, where_value: Any) -> None:
        sql = f"DELETE FROM {table} WHERE {where_column} = $1"
        await self._manager(sql, where_value, commit=True)

    async def delete_where(self, table: str, where: tuple | dict | list) -> int:
        table = self._validate_identifier(table, "table")

        if not where:
            raise ValueError("delete_where uchun where bo'sh bo'lmasligi kerak")

        where_sql, where_params = self._build_where(where, start_index=1)

        if not where_sql:
            raise ValueError("WHERE sharti noto'g'ri")

        sql = f"DELETE FROM {table} WHERE {where_sql}"

        result = await self._manager(
            sql,
            *where_params,
            commit=True
        )

        return int(result.split()[-1])

    async def exists_where(
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
            condition, values = self._build_where(where, start_index=1)
            if condition:
                sql += f" WHERE {condition}"
                params.extend(values)

        if group_by:
            sql += f" GROUP BY {group_by}"

        sql += f" LIMIT ${len(params) + 1}"
        params.append(1)

        record = await self._manager(sql, *params, fetchone=True)
        return record is not None

    async def list_tables(self, schema: str = "public") -> List[str]:
        sql = """
              SELECT table_name
              FROM information_schema.tables
              WHERE table_schema = $1
              ORDER BY table_name;
              """
        result = await self._manager(sql, schema, fetchall=True)
        return [r["table_name"] for r in result]

    async def describe_table(self, table: str, schema: str = "public") -> List[str]:
        sql = """
              SELECT column_name, data_type, is_nullable, column_default
              FROM information_schema.columns
              WHERE table_schema = $1
                AND table_name = $2
              ORDER BY ordinal_position; \
              """
        return await self._manager(sql, schema, table, fetchall=True)

    async def alter(self, table: str, action: str) -> None:
        sql = f"ALTER TABLE {table} {action}"
        await self._manager(sql, commit=True)
        
    @asynccontextmanager
    async def transaction(self):
        if not self.pool:
            if self._pool_lock is None:
                self._pool_lock = asyncio.Lock()
            async with self._pool_lock:
                if not self.pool:
                    self.pool = await asyncpg.create_pool(
                        database=self.database,
                        user=self.user,
                        password=self.password,
                        host=self.host,
                        port=self.port,
                        min_size=self.min_size,
                        max_size=self.max_size
                    )
        
        conn = await self.pool.acquire()
        token = self._async_conn.set(conn)
        try:
            async with conn.transaction():
                yield conn
        finally:
            self._async_conn.reset(token)
            await self.pool.release(conn)
