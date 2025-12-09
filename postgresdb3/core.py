import psycopg2


class PostgresDB:

    def __init__(self, database, user, password, host="localhost", port=5432):
        """
        PostgreSQL bazasiga ulanish.

        Parametrlar:
            database (str): Bazaning nomi
            user (str): Foydalanuvchi
            password (str): Parol
            host (str): Server manzili (standart = localhost)
            port (int): Port (standart = 5432)
        """
        self.connect = psycopg2.connect(
            database=database, user=user, password=password, host=host, port=port
        )

    def manager(
            self,
            sql=None,
            params=None,
            *,
            commit=False,
            fetchall=False,
            fetchone=False,
    ):
        """
        Barcha SQL amallarni boshqaruvchi yagona metod.

        Parametrlar:
            sql (str | None): Bajariladigan SQL so'rov.
            params (tuple | list | None): Parametrlar.
            commit (bool): Tranzaksiyani tasdiqlash.
            fetchall (bool): Barcha natijalarni olish.
            fetchone (bool): Bitta natija olish.
        """

        with self.connect as connect:
            result = None
            with connect.cursor() as cursor:
                cursor.execute(sql, params)

                if commit:
                    connect.commit()
                elif fetchall:
                    result = cursor.fetchall()
                elif fetchone:
                    result = cursor.fetchone()

            return result

    def create(self, table, columns):
        """
        table: str - jadval nomi
        columns: str - ustunlar va turlari, misol: "id SERIAL PRIMARY KEY, name VARCHAR(100)"
        """
        sql = f"CREATE TABLE IF NOT EXISTS {table} ({columns})"
        self.manager(sql, commit=True)

    def drop(self, table):
        """
        table: str - o'chiriladigan jadval nomi
        """
        sql = f"DROP TABLE IF EXISTS {table} CASCADE"
        self.manager(sql, commit=True)

    def select(
            self,
            table,
            columns="*",
            where=None,
            join=None,
            group_by=None,
            order_by=None,
            limit=None,
            fetchone=False,
    ):
        """
        table: str — asosiy jadval
        columns: str — tanlanadigan ustunlar ("id, name")
        where: tuple | None — ("age > %s", [18])
        join: list | None — [("INNER JOIN", "orders", "users.id = orders.user_id")]
        group_by: str | None — "age"
        order_by: str | None — "age DESC"
        limit: int | None
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

        if limit:
            sql += f" LIMIT %s"
            params.append(limit)

        if fetchone:
            return self.manager(sql, params, fetchone=True)
        return self.manager(sql, params, fetchall=True)

    def insert(self, table, columns, values):
        """
        table: str - jadval nomi
        columns: str - ustunlar, misol: "name, email, age"
        values: tuple yoki list - ustun qiymatlari, misol: ("Ali", "ali@mail.com", 25)
        """
        placeholders = ", ".join(["%s"] * len(values))
        sql = f"INSERT INTO {table} ({columns}) VALUES ({placeholders})"
        self.manager(sql, values, commit=True)

    def update(self, table, set_column, set_value, where_column, where_value):
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
        return self.manager(sql, (set_value, where_value), commit=True)

    def delete(self, table, where_column, where_value):
        """
        Jadvaldan qator o'chirish.
        """
        sql = f"DELETE FROM {table} WHERE {where_column} = %s"
        return self.manager(sql, (where_value,), commit=True)
