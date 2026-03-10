# PostgresDB3

![PyPI Version](https://img.shields.io/pypi/v/postgresdb3)
![Python Version](https://img.shields.io/pypi/pyversions/postgresdb3)
![License](https://img.shields.io/badge/license-MIT-green)

**PostgresDB3** — PostgreSQL bilan ishlash uchun oddiy, qulay va yengil Python wrapper.
Kutubxona sync va async ishlashni qo‘llab-quvvatlaydi hamda sodda ORM imkoniyatlarini ham taqdim etadi.

---

# O‘rnatish

```bash
pip install postgresdb3
```

---

# Asosiy imkoniyatlar

* PostgreSQL bilan **sync va async** ishlash
* CRUD amallari
* `where`, `join`, `group_by`, `order_by`, `limit`, `offset`
* `like`, `ilike`, `in`, `isnull`, `gt`, `lt` kabi filterlar
* Raw SQL bajarish imkoniyati
* Sodda ORM tizimi
* Async ORM qo‘llab-quvvatlash

---

# Sync foydalanish

```python
from postgresdb3 import PostgresDB

db = PostgresDB(
    database="mydb",
    user="postgres",
    password="mypassword",
    host="localhost",
    port=5432
)

# Jadval yaratish
db.create("users", "id SERIAL PRIMARY KEY, name VARCHAR(100), age INT")

# Bitta qator qo‘shish
db.insert("users", "name, age", ("Ali", 25))

# Bir nechta qator qo‘shish
db.insert_many(
    "users",
    "name, age",
    [("Vali", 30), ("Gulnoza", 22), ("Hasan", 28)]
)

# Barcha ma'lumotlarni olish
users = db.select("users")
print(users)

# Faqat kerakli ustunlarni olish
users = db.select("users", columns=["id", "name"])
print(users)

# Bitta qatorni olish
user = db.select("users", where={"name": "Ali"}, fetchone=True)
print(user)

# Shart bilan qidirish
adults = db.select("users", where={"age__gt": 18})
print(adults)

# LIKE qidiruv
users_like = db.select("users", where={"name__like": "%Ali%"})
print(users_like)

# ILIKE qidiruv
users_ilike = db.select("users", where={"name__ilike": "%ali%"})
print(users_ilike)

# IN operatori
selected_users = db.select("users", where={"id__in": [1, 2, 3]})
print(selected_users)

# NULL tekshirish
users_with_name = db.select("users", where={"name__isnull": False})
print(users_with_name)

# Tartiblash va limit
ordered_users = db.select(
    "users",
    where={"age__gt": 18},
    order_by="age DESC",
    limit=2
)
print(ordered_users)

# Pagination
paged_users = db.select(
    "users",
    order_by="id ASC",
    limit=2,
    offset=2
)
print(paged_users)

# Ma'lumotni yangilash
db.update("users", "age", 26, "name", "Ali")

# Ma'lumotni o‘chirish
db.delete("users", "name", "Ali")

# Jadvalni o‘chirish
db.drop("users", cascade=False)

# Raw SQL bajarish
result = db.raw("SELECT name, age FROM users WHERE age > %s", [25], fetchall=True)
print(result)

# Connectionni yopish
db.close()
```

---

# Async foydalanish

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

    await db.create("users", "id SERIAL PRIMARY KEY, name VARCHAR(100), age INT")

    await db.insert("users", "name, age", ["Ali", 25])

    await db.insert_many(
        "users",
        "name, age",
        [["Vali", 30], ["Gulnoza", 22], ["Hasan", 28]]
    )

    users = await db.select("users")
    print(users)

    user = await db.select("users", where={"name": "Ali"}, fetchone=True)
    print(user)

    adults = await db.select("users", where={"age__gt": 18})
    print(adults)

    users_ilike = await db.select("users", where={"name__ilike": "%ali%"})
    print(users_ilike)

    await db.update("users", "age", 26, "name", "Ali")

    await db.delete("users", "name", "Ali")

    await db.drop("users", cascade=False)

    result = await db.raw(
        "SELECT name, age FROM users WHERE age > $1",
        [25],
        fetchall=True
    )

    print(result)

    await db.close_pool()

asyncio.run(main())
```

---

# ORM foydalanish

## Sync ORM

```python
from postgresdb3 import PostgresDB
from postgresdb3.orm import Model
from postgresdb3.orm.fields import Serial, String, Integer, Text

db = PostgresDB(
    database="mydb",
    user="postgres",
    password="mypassword"
)

class User(Model):
    db = db
    table = "users"

    id = Serial(primary_key=True)
    name = String()
    age = Integer()
    about = Text(nullable=True)

User.create_table()

user = User.create(name="Ali", age=20)

print(User.all())

user = User.find(1)

user.update(name="Valijon")

user.delete()
```

---

# Qo‘shimcha

`%s` va `$1` bilan parametrizatsiya qilish xavfsiz va SQL injection'dan himoya qiladi.

`where` va `join` yordamida murakkab so‘rovlar yozish mumkin.

`limit`, `offset` va `order_by` parametrlaridan foydalanib ma'lumotlarni tartiblash va sahifalash oson.

`raw()` metodi orqali kerak bo‘lganda to‘g‘ridan-to‘g‘ri SQL so‘rov yozish mumkin.

