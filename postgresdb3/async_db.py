import asyncpg
from typing import Any, List, Optional


class AsyncPostgresDB:
    """
    Async PostgreSQL helper class for CRUD operations and schema management.

    Ushbu class `asyncpg` kutubxonasidan foydalanib,
    PostgreSQL bilan asynchronous CRUD va schema operatsiyalarini bajaradi.
    Aiogram kabi async frameworklar bilan to‘g‘ridan-to‘g‘ri ishlash uchun mos.
    """

    def __init__(self, database: str, user: str, password: str, host: str = "localhost", port: int = 5432) -> None:
        """
        PostgreSQL bazasiga ulanishni tayyorlaydi.

        Args:
            database (str): Bazaning nomi.
            user (str): Foydalanuvchi nomi.
            password (str): Parol.
            host (str): Server manzili (default: "localhost").
            port (int): Port (default: 5432).
        """
        self.database = database
        self.user = user
        self.password = password
        self.host = host
        self.port = port
        self.pool: Optional[asyncpg.pool.Pool] = None

    async def _manager(self, sql: str, *params, fetchone=False, fetchall=False, commit=False) -> Any:
        """
        Markaziy metod: barcha SQL so‘rovlarni bajaradi.

        Args:
            sql (str): Bajariladigan SQL so‘rov.
            *params: SQL parametrlarini berish.
            fetchone (bool): True bo‘lsa, faqat bitta qator qaytaradi.
            fetchall (bool): True bo‘lsa, barcha natijalarni qaytaradi.
            commit (bool): True bo‘lsa, tranzaksiya commit qilinadi.

        Returns:
            fetchone=True bo‘lsa: asyncpg.Record
            fetchall=True bo‘lsa: list[asyncpg.Record]
            commit=True bo‘lsa: None
        """
        if not self.pool:
            self.pool = await asyncpg.create_pool(
                database=self.database,
                user=self.user,
                password=self.password,
                host=self.host,
                port=self.port
            )

        async with self.pool.acquire() as conn:
            if commit:
                await conn.execute(sql, *params)
                return
            if fetchone:
                return await conn.fetchrow(sql, *params)
            if fetchall:
                return await conn.fetch(sql, *params)

    async def close_pool(self) -> None:
        """
        Connection poolni yopadi.
        """
        if self.pool:
            await self.pool.close()
            self.pool = None

    async def create(self, table: str, columns: str) -> None:
        """
        Jadval yaratadi (agar mavjud bo‘lsa o‘tkazib yuboradi).

        Args:
            table (str): Jadval nomi.
            columns (str): Ustunlar va turlari, misol: "id SERIAL PRIMARY KEY, name TEXT".
        """
        await self._manager(f"CREATE TABLE IF NOT EXISTS {table} ({columns})", commit=True)

    async def drop(self, table: str) -> None:
        """
        Jadvalni o‘chiradi (agar mavjud bo‘lsa).

        Args:
            table (str): Jadval nomi.
        """
        await self._manager(f"DROP TABLE IF EXISTS {table} CASCADE", commit=True)

    async def select(
            self, table: str, columns: str = "*",
            where: Optional[List[Any]] = None,
            join: Optional[List[tuple]] = None,
            group_by: Optional[str] = None,
            order_by: Optional[str] = None,
            limit: Optional[int] = None,
            fetchone: bool = False
    ) -> Any:
        """
        Jadvaldan ma'lumotlarni tanlash.

        Args:
            table (str): Asosiy jadval nomi.
            columns (str): Tanlanadigan ustunlar (default: "*").
            where (Optional[List[Any]]): ("shart", [qiymatlar])
            join (Optional[List[tuple]]): [("INNER JOIN", "orders", "users.id = orders.user_id")]
            group_by (Optional[str]): GROUP BY ustuni.
            order_by (Optional[str]): ORDER BY qoidasi.
            limit (Optional[int]): LIMIT qiymati.
            fetchone (bool): True bo‘lsa faqat bitta qator qaytaradi.

        Returns:
            asyncpg.Record yoki list[asyncpg.Record]
        """
        sql = f"SELECT {columns} FROM {table}"
        params: List[Any] = []

        if join:
            for join_type, join_table, on_condition in join:
                sql += f" {join_type} {join_table} ON {on_condition}"

        if where:
            condition, values = where
            sql += f" WHERE {condition}"
            params.extend(values)

        if group_by:
            sql += f" GROUP BY {group_by}"

        if order_by:
            sql += f" ORDER BY {order_by}"

        if limit is not None:
            sql += f" LIMIT $%d" % (len(params) + 1)
            params.append(limit)

        return await self._manager(sql, *params, fetchone=fetchone, fetchall=not fetchone)

    async def insert(self, table: str, columns: str, values: List[Any]) -> None:
        """
        Jadvalga yangi qator qo‘shadi.

        Args:
            table (str): Jadval nomi.
            columns (str): Ustunlar nomi, misol: "name, age".
            values (List[Any]): Qiymatlar, misol: ["Ali", 25].
        """
        placeholders = ", ".join(f"${i + 1}" for i in range(len(values)))
        sql = f"INSERT INTO {table} ({columns}) VALUES ({placeholders})"
        await self._manager(sql, *values, commit=True)

    async def insert_many(self, table: str, columns: str, values_list: List[List[Any]]) -> None:
        """
        Jadvalga bir nechta qator qo‘shish (bulk insert).

        Args:
            table (str): Jadval nomi.
            columns (str): Ustunlar nomi, misol: "name, age".
            values_list (List[List[Any]]): Qiymatlar ro‘yxati, misol: [["Ali", 25], ["Vali", 30]].

        Raises:
            ValueError: Agar `values_list` bo‘sh bo‘lsa.

        Notes:
            - `asyncpg` kutubxonasida har bir parametr uchun unikal `$n` indekslari kerak,
              shuning uchun har bir qator uchun ketma-ket `$1, $2, ...` ishlatiladi.
            - Metod barcha qatorlarni bir so‘rovda qo‘shadi.
            - `fetchmany` kerak emas, chunki bu insert operatsiyasi natija qaytarmaydi.

        Example:
            await db.insert_many(
                "users",
                "name, age",
                [["Ali", 25], ["Vali", 30], ["Guli", 22]]
            )
        """
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
        """
        Jadvaldagi qatorni yangilaydi.

        Args:
            table (str): Jadval nomi.
            set_column (str): O‘zgartiriladigan ustun.
            set_value (Any): Yangi qiymat.
            where_column (str): Filtrlash ustuni.
            where_value (Any): Filtrlash qiymati.
        """
        sql = f"UPDATE {table} SET {set_column} = $1 WHERE {where_column} = $2"
        await self._manager(sql, set_value, where_value, commit=True)

    async def delete(self, table: str, where_column: str, where_value: Any) -> None:
        """
        Jadvaldan qator o‘chiradi.

        Args:
            table (str): Jadval nomi.
            where_column (str): Filtrlash ustuni.
            where_value (Any): Filtrlash qiymati.
        """
        sql = f"DELETE FROM {table} WHERE {where_column} = $1"
        await self._manager(sql, where_value, commit=True)

    async def list_tables(self, schema: str = "public") -> List[str]:
        """
        Bazadagi barcha jadvallarni ro‘yxat sifatida qaytaradi.

        Args:
            schema (str): Schema nomi, default "public".

        Returns:
            List[str]: Jadval nomlari
        """
        sql = """
              SELECT table_name
              FROM information_schema.tables
              WHERE table_schema = $1
              ORDER BY table_name \
              """
        result = await self._manager(sql, schema, fetchall=True)
        return [r["table_name"] for r in result]

    async def describe_table(self, table: str, schema: str = "public") -> List[str]:
        """
        Jadval ustunlari haqida ma'lumot beradi.

        Args:
            table (str): Jadval nomi.
            schema (str): Schema nomi, default "public".

        Returns:
            list[asyncpg.Record]: Har bir ustun bo‘yicha ma’lumot
        """
        sql = """
              SELECT column_name, data_type, is_nullable, column_default
              FROM information_schema.columns
              WHERE table_schema = $1
                AND table_name = $2
              ORDER BY ordinal_position \
              """
        return await self._manager(sql, schema, table, fetchall=True)

    async def alter(self, table: str, action: str) -> None:
        """
        Jadval strukturasi o‘zgartirish (ALTER TABLE).

        Args:
            table (str): Jadval nomi.
            action (str): ALTER TABLE dan keyingi SQL qismi, misol: "ADD COLUMN age INT".
        """
        sql = f"ALTER TABLE {table} {action}"
        await self._manager(sql, commit=True)
