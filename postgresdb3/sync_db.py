from typing import Any, Optional
import psycopg2


class PostgresDB:

    def __init__(self, database: str, user: str, password: str, host: str = "localhost", port: int = 5432) -> None:
        """
        PostgreSQL bazasiga ulanish.

        Parametrlar:
            database (str): Bazaning nomi
            user (str): Foydalanuvchi
            password (str): Parol
            host (str): Server manzili (standart = localhost)
            port (int): Port (standart = 5432)
        """
        self.connection = psycopg2.connect(
            database=database, user=user, password=password, host=host, port=port
        )

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
        """
        SQL so'rovlarini xavfsiz bajaruvchi yagona, ichki metod.

        Bu metod **protected** bo‘lib, tashqaridan ishlatish tavsiya etilmaydi.
        Public uchun `raw()` metodini ishlatish yaxshiroq.

        Parametrlar
        ----------
        sql : str
            Bajariladigan SQL so'rov. Majburiy.
        params : tuple, list yoki None, ixtiyoriy
            SQL so‘rovga parametrlarni bog‘lash uchun ishlatiladi. Default: None.
            Agar `many=True` bo‘lsa, bu **tuple lar ro‘yxati** bo‘lishi kerak.
        commit : bool, ixtiyoriy
            Agar True bo‘lsa, tranzaksiya bajarilgandan keyin commit qilinadi.
            Default: False. INSERT, UPDATE, DELETE kabi so‘rovlar uchun kerak.
        many : bool, ixtiyoriy
            Agar True bo‘lsa, so‘rovni bir nechta parametrlar bilan qayta bajaradi
            (`cursor.executemany()` ishlatiladi). Default: False.
            `fetchone`, `fetchall` yoki `fetchmany` bilan birga ishlatilmaydi.
        fetchone : bool, ixtiyoriy
            Agar True bo‘lsa, so‘rov natijasidan faqat bitta qator qaytariladi.
            Default: False. `fetchall`, `fetchmany` yoki `many=True` bilan ishlamaydi.
        fetchall : bool, ixtiyoriy
            Agar True bo‘lsa, so‘rov natijasidagi barcha qatorlar qaytariladi.
            Default: False. `fetchone`, `fetchmany` yoki `many=True` bilan ishlamaydi.
        fetchmany : int yoki None, ixtiyoriy
            Agar butun son N berilsa, so‘rov natijasidan N ta qator qaytariladi.
            Default: None. `fetchone`, `fetchall` yoki `many=True` bilan ishlamaydi.

        Returns
        -------
        result : any
            So‘rov natijasi fetch parametriga bog‘liq:
            - `fetchone=True` → bitta qator (tuple)
            - `fetchall=True` → barcha qatorlar ro‘yxati
            - `fetchmany=N` → N ta qator ro‘yxati
            - `many=True` → None
            - Fetch parametri ishlatilmasa → None

        Raises
        ------
        ValueError
            - Agar `sql` bo‘sh yoki None bo‘lsa.
            - Agar bir vaqtda `fetchone` va `fetchall` True bo‘lsa.
            - Agar `many=True` fetch parametrlar bilan birga ishlatilsa.

        Izohlar
        --------
        - Bu metod connection va cursor ni context manager orqali avtomatik boshqaradi.
        - Exceptionlar va tranzaksiya nazorati psycopg2 tomonidan amalga oshiriladi.
        - Tashqarida ishlatishda `raw()` yoki yuqori darajadagi metodlar (`insert()`, `select()`, `insert_many()`) ishlatilishi tavsiya etiladi.
        - Tashqaridan bevosita chaqirish tavsiya etilmaydi.
        """

        if not sql or not sql.strip():
            raise ValueError("SQL query cannot be empty")
        if fetchone and fetchall:
            raise ValueError("fetchone and fetchall cannot be True at the same time")
        if many and (fetchone or fetchall or fetchmany):
            raise ValueError("cannot use fetchone/fetchall/fetchmany with many=True")

        with self.connection.cursor() as cursor:
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

            if commit:
                self.connection.commit()

        return result

    def close(self) -> None:
        """
           Faol bazaga ulanishni yopadi.

           Bu metod chaqirilgandan so‘ng, connection obyekti ishlatilmaydi.
           Ulanishni yopishdan oldin, har qanday kutilayotgan tranzaksiyalarni commit qilganingizga ishonch hosil qiling.
        """
        self.connection.close()

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
        """
        SQL so'rovini bevosita bajarish (raw execution).

        Faqat ilg'or foydalanish uchun. Bu metod ichki `_manager` metodini chaqiradi.
        Tashqaridan oddiy foydalanuvchilar uchun `select()`, `insert()`, `update()`,
        `delete()` yoki `insert_many()` metodlarini ishlatish tavsiya etiladi.

        Parametrlar
        ----------
        sql : str
            Bajariladigan SQL so'rov. Majburiy.
        params : tuple, list yoki None, ixtiyoriy
            SQL so‘rovga parametrlarni bog‘lash uchun ishlatiladi. Default: None.
        commit : bool, ixtiyoriy
            Agar True bo‘lsa, tranzaksiya bajarilgandan keyin commit qilinadi.
            Default: False.
        fetchone : bool, ixtiyoriy
            Agar True bo‘lsa, so‘rov natijasidan faqat bitta qator qaytariladi.
            Default: False. `fetchall` bilan birga ishlatilmaydi.
        fetchall : bool, ixtiyoriy
            Agar True bo‘lsa, so‘rov natijasidagi barcha qatorlar qaytariladi.
            Default: False. `fetchone` bilan birga ishlatilmaydi.

        Returns
        -------
        result : any
            So‘rov natijasi fetch parametriga bog‘liq:
            - `fetchone=True` → bitta qator (tuple)
            - `fetchall=True` → barcha qatorlar ro‘yxati
            - Hech qaysi fetch parametr ishlatilmasa → None

        Raises
        ------
        ValueError
            - Agar bir vaqtda `fetchone` va `fetchall` True bo‘lsa.

        Misol
        ------
        >>> db.raw("SELECT * FROM users WHERE age > %s", (18,), fetchall=True)
        """

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
        """
        table: str - jadval nomi
        columns: str - ustunlar va turlari, misol: "id SERIAL PRIMARY KEY, name VARCHAR(100)"
        """
        sql = f"CREATE TABLE IF NOT EXISTS {table} ({columns})"
        self._manager(sql, commit=True)

    def drop(self, table: str, cascade: bool = False) -> None:
        """
        Jadvalni o'chiradi.

        Parametrlar:
            table (str): O'chiriladigan jadval nomi
            cascade (bool): Agar True bo'lsa, jadval bilan bog'liq barcha obyektlar ham o'chiriladi. Default: True
        """
        sql = f"DROP TABLE IF EXISTS {table}"
        if cascade:
            sql += " CASCADE"
        self._manager(sql, commit=True)

    def select(
            self,
            table: str,
            columns: str = "*",
            where: tuple | None = None,
            join: list[tuple] | None = None,
            group_by: str | None = None,
            order_by: str | None = None,
            limit: int | None = None,
            offset: int | None = None,
            fetchone: bool = False,
            fetchmany: int | None = None
    ) -> Any:
        """
        table: str — asosiy jadval
        columns: str — tanlanadigan ustunlar ("id, name")
        where: tuple | None — ("age > %s", [18])
        join: list | None — [("INNER JOIN", "orders", "users.id = orders.user_id")]
        group_by: str | None — "age"
        order_by: str | None — "age DESC"
        limit: int | None
        offset: int | None
        fetchone: bool
        fetchmany: int | None
        """

        sql = f"SELECT {columns} FROM {table}"
        params = []

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
            sql += f" LIMIT %s"
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

    def insert(self, table: str, columns: str, values: tuple | list) -> None:
        """
        table: str - jadval nomi
        columns: str - ustunlar, misol: "name, email, age"
        values: tuple yoki list - ustun qiymatlari, misol: ("Ali", "ali@mail.com", 25)
        """
        placeholders = ", ".join(["%s"] * len(values))
        sql = f"INSERT INTO {table} ({columns}) VALUES ({placeholders})"
        self._manager(sql, values, commit=True)

    def insert_many(self, table: str, columns: str, values_list: list[tuple]) -> None:
        """
        Jadvalga bir nechta qatorni qo'shish (bulk insert).

        Parametrlar
        ----------
        table : str
            Jadval nomi.
        columns : str
            Ustunlar, misol: "name, email, age".
        values_list : list of tuples
            Har tuple bitta qator qiymatlari, misol:
            [("Ali", "ali@mail.com", 25), ("Vali", "vali@mail.com", 30)]

        Misol
        ------
        >>> db.insert_many(
        ...     "users",
        ...     "name, email, age",
        ...     [("Ali", "ali@mail.com", 25), ("Vali", "vali@mail.com", 30)]
        ... )
        """
        if not values_list:
            raise ValueError("values_list bo'sh bo'lishi mumkin emas")

        placeholders = ", ".join(["%s"] * len(values_list[0]))
        sql = f"INSERT INTO {table} ({columns}) VALUES ({placeholders})"

        self._manager(sql, values_list, commit=True, many=True)

    def update(self, table: str, set_column: str, set_value: Any, where_column: str, where_value: Any) -> None:
        """
        Jadvaldagi ma'lumotni yangilash.

        Parametrlar:
            table (str): Jadval nomi.
            set_column (str): O'zgartiriladigan ustun.
            set_value (Any): Yangi qiymat.
            where_column (str): Filtrlash ustuni.
            where_value (Any): Qaysi qatorda o'zgarish bo'lishi.

        Izoh:
            Faqat WHERE shartiga mos kelgan qatorlar yangilanadi.
        """
        sql = f"UPDATE {table} SET {set_column} = %s WHERE {where_column} = %s"
        self._manager(sql, (set_value, where_value), commit=True)

    def delete(self, table: str, where_column: str, where_value: Any) -> None:
        """
        Jadvaldan qator o'chirish.
        """
        sql = f"DELETE FROM {table} WHERE {where_column} = %s"
        self._manager(sql, (where_value,), commit=True)

    def list_tables(self, schema="public") -> list[tuple]:
        """
        Bazadagi mavjud jadvallar ro'yxatini qaytaradi.

        schema: str — schema nomi (standart: public)
        """
        sql = """
              SELECT table_name
              FROM information_schema.tables
              WHERE table_schema = %s
              ORDER BY table_name; 
              """
        return self._manager(sql, (schema,), fetchall=True)

    def describe_table(self, table: str, schema: str = "public") -> list[tuple]:
        """
        Jadval ustunlari haqida ma'lumot beradi.
        """
        sql = """
              SELECT column_name,
                     data_type,
                     is_nullable,
                     column_default
              FROM information_schema.columns
              WHERE table_schema = %s
                AND table_name = %s
              ORDER BY ordinal_position; 
              """
        return self._manager(sql, (schema, table), fetchall=True)

    def alter(self, table: str, action: str) -> Any:
        """
        Universal ALTER TABLE metodi.

        table: str — jadval nomi
        action: str — ALTER TABLE dan keyingi qism
        """
        sql = f"ALTER TABLE {table} {action}"
        return self._manager(sql, commit=True)
