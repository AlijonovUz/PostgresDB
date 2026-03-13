# PostgresDB3

![PyPI Version](https://img.shields.io/pypi/v/postgresdb3)
![Python Version](https://img.shields.io/pypi/pyversions/postgresdb3)
![License](https://img.shields.io/badge/license-MIT-green)

**PostgresDB3** — PostgreSQL bilan ishlash uchun oddiy, qulay va yengil Python wrapper.

Kutubxona quyidagilarni qo‘llab-quvvatlaydi:

- Sync va Async ishlash
- CRUD operatsiyalari
- Query builder (`where`, `join`, `group_by`, `order_by`, `limit`, `offset`)
- Kengaytirilgan filterlar (`gt`, `lt`, `like`, `ilike`, `in`, `isnull`)
- Raw SQL bajarish
- Sodda ORM tizimi

---

# O‘rnatish

```bash
pip install postgresdb3
````

---

# Sync foydalanish

```python
from postgresdb3 import PostgresDB

db = PostgresDB(
    database="mydb",
    user="postgres",
    password="mypassword"
)

# Jadval yaratish
db.create("users", "id SERIAL PRIMARY KEY, name VARCHAR(100), age INT")

# Qator qo‘shish
db.insert("users", "name, age", ("Ali", 25))

# Barcha ma'lumotlar
users = db.select("users")

# Shart bilan qidirish
adults = db.select("users", where={"age__gt": 18})

# Tartiblash
users = db.select("users", order_by="age DESC")

# Yangilash
db.update("users", "age", 26, "name", "Ali")

# O‘chirish
db.delete("users", "name", "Ali")

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
        password="mypassword"
    )

    await db.create("users", "id SERIAL PRIMARY KEY, name VARCHAR(100), age INT")

    await db.insert("users", "name, age", ["Ali", 25])

    users = await db.select("users")

    adults = await db.select("users", where={"age__gt": 18})

    await db.update("users", "age", 26, "name", "Ali")

    await db.delete("users", "name", "Ali")

    await db.close_pool()

asyncio.run(main())
```

---

# ORM foydalanish

PostgresDB3 oddiy ORM tizimini ham taqdim etadi.

## Sync ORM

```python
from postgresdb3 import PostgresDB
from postgresdb3.orm import Model
from postgresdb3.orm.fields import Serial, String, Integer

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

User.create_table()

# create
user = User.create(name="Ali", age=20)

# all
users = User.all()

# find
user = User.find(1)

# filter
users = User.filter(age__gt=18).all()

# get
user = User.get(id=1)

# exclude
users = User.exclude(name="Ali").all()

# update
user.update(name="Valijon")

# delete
user.delete()
```

---

## Async ORM

```python
from postgresdb3 import AsyncPostgresDB
from postgresdb3.orm import AsyncModel
from postgresdb3.orm.fields import Serial, String, Integer

db = AsyncPostgresDB(
    database="mydb",
    user="postgres",
    password="mypassword"
)

class User(AsyncModel):
    db = db
    table = "users"

    id = Serial(primary_key=True)
    name = String()
    age = Integer()

await User.create_table()

user = await User.create(name="Ali", age=20)

users = await User.all()

user = await User.find(1)

users = await User.filter(age__gt=18).all()

user = await User.get(id=1)

users = await User.exclude(name="Ali").all()

await user.update(name="Valijon")

await user.delete()
```

---

# Filter operatorlari

| Operator | Tavsif           |
| -------- | ---------------- |
| eq       | teng             |
| ne       | teng emas        |
| gt       | katta            |
| gte      | katta yoki teng  |
| lt       | kichik           |
| lte      | kichik yoki teng |
| like     | LIKE             |
| ilike    | ILIKE            |
| in       | IN               |
| not_in   | NOT IN           |
| isnull   | NULL tekshirish  |

Misol:

```python
User.filter(age__gt=18)
User.filter(name__ilike="%ali%")
User.filter(id__in=[1,2,3])
User.filter(name__ne="Ali")
```

---

# Raw SQL

```python
result = db.raw(
    "SELECT name FROM users WHERE age > %s",
    [18],
    fetchall=True
)
```
