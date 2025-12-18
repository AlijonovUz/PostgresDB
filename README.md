# PostgresDB

![PyPI Version](https://img.shields.io/pypi/v/nameuz)
![Python Version](https://img.shields.io/pypi/pyversions/nameuz)
![License](https://img.shields.io/badge/license-MIT-green)

Oddiy va qulay Python wrapper PostgreSQL bazasi bilan ishlash uchun.

## O'rnatish

``` bash
pip install postgresdb3
```

## Foydalanish (Sync)

```python
from postgresdb3 import PostgresDB

# Bazaga ulanish
db = PostgresDB(
    database="mydb",
    user="postgres",
    password="mypassword",
    host="localhost",  # ixtiyoriy
    port=5432          # ixtiyoriy
)

# Jadval yaratish
db.create("users", "id SERIAL PRIMARY KEY, name VARCHAR(100), age INT")

# Bitta qator qo'shish
db.insert("users", "name, age", ("Ali", 25))

# Bir nechta qator qo'shish
db.insert_many(
    "users",
    "name, age",
    [("Vali", 30), ("Gulnoza", 22), ("Hasan", 28)]
)

# Ma'lumotlarni olish
users = db.select("users")
print(users)

# Bitta qatorni olish
user = db.select("users", where=("name=%s", ["Ali"]), fetchone=True)
print(user)

# Shart bilan ma'lumot olish
adults = db.select("users", where=("age > %s", [18]))
print(adults)

# Bir nechta shart bilan
specific_users = db.select("users", where=("age > %s AND name = %s", [18, "Ali"]))
print(specific_users)

# Faqat 2 ta qatorni olish
users = db.select("users", fetchmany=2)
print(users)

# Jadvaldagi ma'lumotni yangilash
db.update("users", "age", 26, "name", "Ali")

# Ma'lumotni o'chirish
db.delete("users", "name", "Ali")

# Jadvalni o'chirish
db.drop("users", cascade=False)

# To‘g‘ridan-to‘g‘ri SQL bajarish (raw)
result = db.raw("SELECT name, age FROM users WHERE age > %s", [25], fetchall=True)
print(result)

# Connectionni yopish
db.close()
```

## Foydalanish (Async)

```python
import asyncio
from postgresdb3 import AsyncPostgresDB

async def main():
    db = AsyncPostgresDB(
        database="mydb",
        user="postgres",
        password="mypassword",
        host="localhost",
        port=5432
    )

    # Jadval yaratish
    await db.create("users", "id SERIAL PRIMARY KEY, name VARCHAR(100), age INT")

    # Bitta qator qo'shish
    await db.insert("users", "name, age", ["Ali", 25])

    # Bir nechta qator qo'shish
    await db.insert_many(
        "users",
        "name, age",
        [["Vali", 30], ["Gulnoza", 22], ["Hasan", 28]]
    )

    # Barcha ma'lumotlarni olish
    users = await db.select("users")
    print("Barcha foydalanuvchilar:", users)

    # Bitta qatorni olish
    user = await db.select("users", where=("name=$1", ["Ali"]), fetchone=True)
    print("Foydalanuvchi Ali:", user)

    # Shart bilan ma'lumot olish
    adults = await db.select("users", where=("age > $1", [18]))
    print("Kattalar:", adults)

    # Bir nechta shart bilan
    specific_users = await db.select("users", where=("age > $1 AND name = $2", [18, "Ali"]))
    print("Maxsus foydalanuvchi:", specific_users)
    
    # Faqat 2 ta qatorni olish
    users = await db.select("users", fetchmany=2)
    print(users)
    
    # Jadvaldagi ma'lumotni yangilash
    await db.update("users", "age", 26, "name", "Ali")

    # Ma'lumotni o'chirish
    await db.delete("users", "name", "Ali")

    # Jadvalni o'chirish
    await db.drop("users", cascade=False)

    # To‘g‘ridan-to‘g‘ri SQL bajarish (raw)
    result = await db.raw("SELECT name, age FROM users WHERE age > $1", [25], fetchall=True)
    print("Raw query result:", result)

    # Connection poolni yopish
    await db.close_pool()

asyncio.run(main())
```

## Parametrlar va metodlar

**PostgresDB(database, user, password, host="localhost", port=5432)**
--- bazaga ulanish.

**create(table, columns)** --- jadval yaratish, `columns` SQL
sintaksisida.

**drop(table, cascade=False)** --- jadvalni o'chirish.

**insert(table, columns, values)** --- ma'lumot qo'shish.

**insert_many(table, columns, values_list)** --- bir nechta qator qo‘shish

**select(table, columns="\*", where=None, join=None, group_by=None,
order_by=None, limit=None, fetchone=False)** --- ma'lumotlarni olish.

### where misollar:

``` python
db.select("users", where=("age > %s", [18]))
db.select("users", where=("age > %s AND name = %s", [18, "Ali"]))
```

### join misol:

``` python
db.select("orders", join=[("INNER JOIN", "users", "users.id = orders.user_id")])
```

**update(table, set_column, set_value, where_column, where_value)** ---
ma'lumotni yangilash.

**delete(table, where_column, where_value)** --- ma'lumotni o'chirish.

## Qo‘shimcha

`%s` va `$1` bilan parametrizatsiya qilish xavfsiz va SQL injection'dan himoya qiladi.

`where` va `join` yordamida murakkab so‘rovlar yozish mumkin.

`limit`, `offset` va `order_by` parametrlaridan foydalanib ma'lumotlarni tartiblash va cheklash oson.

`commit=True` bo‘lgan amallar darhol bazaga yoziladi, select() esa hech qachon o‘zgartirish kiritmaydi.

`raw()` — barcha SQL buyruqlarini bajaruvchi yagona metod bo‘lib, kerak bo‘lganda to‘g‘ridan‑to‘g‘ri SQL yozish imkonini beradi.