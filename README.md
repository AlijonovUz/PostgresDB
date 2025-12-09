# PostgresDB

Oddiy va qulay Python wrapper PostgreSQL bazasi bilan ishlash uchun.

## O'rnatish

``` bash
    pip install postgresdb3
```

## Foydalanish

``` python
from postgresdb3 import PostgresDB

# Bazaga ulanish
db = PostgresDB(
    database="mydb",
    user="postgres",
    password="mypassword",
    host="localhost",
    port=5432
)

# Jadval yaratish
db.create("users", "id SERIAL PRIMARY KEY, name VARCHAR(100), age INT")

# Ma'lumot qo'shish
db.insert("users", "name, age", ("Ali", 25))

# Ma'lumotlarni olish
users = db.select("users")
print(users)

# Bitta qatorni olish
user = db.select("users", where=("name=%s", ["Ali"]), fetchone=True)
print(user)

# Shart bilan ma'lumot olish
adults = db.select("users", where=("age > %s", [18]))
print(adults)

# Bir nechta shart
specific_users = db.select("users", where=("age > %s AND name = %s", [18, "Ali"]))
print(specific_users)

# Jadvaldagi ma'lumotni yangilash
db.update("users", "age", 26, "name", "Ali")

# Ma'lumotni o'chirish
db.delete("users", "name", "Ali")

# Jadvalni o'chirish
db.drop("users")
```

## Parametrlar va metodlar

**PostgresDB(database, user, password, host="localhost", port=5432)**
--- bazaga ulanish.

**create(table, columns)** --- jadval yaratish, `columns` SQL
sintaksisida.

**drop(table)** --- jadvalni o'chirish.

**insert(table, columns, values)** --- ma'lumot qo'shish.

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

**manager(sql, params=None, commit=False, fetchall=False,
fetchone=False)** --- barcha SQL amallarni bajaruvchi yagona metod.

## Qo‘shimcha

`%s` bilan parametrizatsiya qilish xavfsiz va SQL injection'dan himoya qiladi.

`where` va `join` `list` yoki `tuple` yordamida murakkab so‘rovlar yozish mumkin.

`limit` va `order_by` parametrlaridan foydalanib ma'lumotlarni tartiblash va cheklash oson.

`commit=True` bo‘lgan amallar darhol bazaga yoziladi, select() esa hech qachon o‘zgartirish kiritmaydi.

`manager()` — barcha SQL buyruqlarini bajaruvchi yagona metod bo‘lib, kerak bo‘lganda to‘g‘ridan‑to‘g‘ri SQL yozish imkonini beradi.

PostgreSQL bilan ishlash uchun `psycopg2` kutubxonasi talab qilinadi.