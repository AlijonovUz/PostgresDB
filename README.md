# 🐘 PostgresDB3 ORM

`postgresdb3` - Python tilida yozilgan, PostgreSQL ma'lumotlar bazasi bilan ishlashga mo'ljallangan, o'ta tezkor va yengil ORM (Object-Relational Mapping) kutubxonasi. U **sinxron** (`psycopg2` orqali) va **asinxron** (`asyncpg` orqali) ishlash rejimlarini to'liq qo'llab-quvvatlaydi hamda Django-ga o'xshash qulay sintaksis va mukammal migratsiya dvigatelini taqdim etadi.

---

## 📌 Mundarija
1. [O'rnatish (Installation)](#1-ornatish-installation)
2. [Ma'lumotlar Bazasiga Ulanish, Auto-Reconnect & Profiling](#2-malumotlar-bazasiga-ulanish-auto-reconnect--profiling)
3. [Modellarni Yaratish (Models & Composite PK)](#3-modellarni-yaratish-models--composite-pk)
4. [Maydonlar (Fields) va Konstantalar](#4-maydonlar-fields-va-konstantalar)
5. [Model Signallari (Signals Tizimi)](#5-model-signallari-signals-tizimi)
6. [Validatorlar (Validation)](#6-validatorlar-validation)
7. [CRUD Operatsiyalari va FastAPI Pydantic Sxemalar](#7-crud-operatsiyalari)
8. [QuerySet API (FTS, PostGIS, JSONB, only, defer, cache)](#8-queryset-api-qidiruv-jsonb-only-defer-cache)
9. [Aloqalar bilan ishlash (Relationships)](#9-aloqalar-bilan-ishlash-relationships)
10. [Migratsiya va Fixtures Tizimi (Data Migrations, Fixtures, CLI)](#10-migratsiya-va-fixtures-tizimi-data-migrations-fixtures-cli)
11. [Xatoliklar va Exceptionlar (Error Handling)](#11-xatoliklar-va-exceptionlar-error-handling)

---

## 1. O'rnatish (Installation)

Loyihangizga kutubxonani o'rnatish uchun:

```bash
pip install postgresdb3
```

---

## 2. Ma'lumotlar Bazasiga Ulanish, Auto-Reconnect & Profiling

`postgresdb3` ulanishlar pulida avtomatik tiklanish (Fault-tolerant Auto-Reconnect retry) hamda so'rovlar bajarilish vaqtini o'lchash mexanizmiga ega.

```python
from postgresdb3 import PostgresDB
from postgresdb3.orm import Model

db_sync = PostgresDB(
    database="my_db",
    user="postgres",
    password="my_password",
    host="localhost",
    port=5432,
    echo=True,                   # Har bir so'rov vaqtini ko'rsatadi [SQL - 1.25ms]
    slow_query_threshold=200.0,  # 200ms dan oshsa [SLOW QUERY WARNING] chiqaradi
)

Model.db = db_sync
```

---

## 3. Modellarni Yaratish (Models & Composite PK)

```python
from postgresdb3.orm import Model, fields

# 1. Birlamchi Kalitli Model
class Category(Model):
    name = fields.String(length=50, unique=True)

# 2. Murakkab (Composite) Birlamchi Kalitli Model
class OrderItem(Model):
    order_id = fields.Integer(primary_key=True)
    product_id = fields.Integer(primary_key=True)
    quantity = fields.Integer(default=1)
```

---

## 4. Maydonlar (Fields) va Konstantalar

- **Turlar:** `Integer`, `String`, `Text`, `Boolean`, `Date`, `Time`, `Timestamp`, `UUID`, `JSON`, `JSONB`, `Array`, `ForeignKey`, `OneToOne`, `ManyToMany`
- **Konstantalar:** `fields.CASCADE`, `fields.SET_NULL`, `fields.RESTRICT`, `fields.SET_DEFAULT`, `fields.DO_NOTHING`

---

## 5. Model Signallari (Signals Tizimi)

Django-ga o'xshash event-driven signallar tizimi: `pre_save`, `post_save`, `pre_delete`, `post_delete`.

```python
from postgresdb3.orm import Model, fields, post_save, receiver

class User(Model):
    username = fields.String(length=50)

@receiver(post_save, sender=User)
def notify_user_created(sender, instance, created, **kwargs):
    if created:
        print(f"Yangi foydalanuvchi yaratildi: {instance.username}")
```

---

## 6. Validatorlar (Validation)

```python
from postgresdb3.orm import Model, fields
from postgresdb3.orm.validators import MinValueValidator, EmailValidator

class User(Model):
    age = fields.Integer(validators=[MinValueValidator(18)])
    email = fields.String(length=100, validators=[EmailValidator()])
```

---

## 7. CRUD Operatsiyalari

```python
user = User.create(username="ali", age=25)
user = User.first(username="ali")
user.age = 26
user.save()
user.delete()
```

---

## 7.1. FastAPI & Pydantic Sxemalari Generatori (`to_pydantic`)

ORM modellardan FastAPI request va response ob'ektlari uchun avtomatik `pydantic.BaseModel` yaratish:

```python
class User(Model):
    id = fields.Serial(primary_key=True)
    username = fields.String(length=50)
    password = fields.String(length=128)
    email = fields.String(length=100)

# 1. To'liq Pydantic Sxema (Response Model uchun):
UserResponseSchema = User.to_pydantic(name="UserResponse")

# 2. Primary Key ("id") chiqarib tashlangan sxema (POST body so'rovlari uchun):
UserCreateSchema = User.to_pydantic(exclude=["id"])

# 3. Maxsus ustunlarni chiqarib tashlash (Masalan password va id):
UserPublicSchema = User.to_pydantic(exclude=["password", "id"])

# 4. Faqat belgilangan ustunlarni kiritish:
UserSimpleSchema = User.to_pydantic(include=["username", "email"])

# 5. Belgilangan maydonlarni ixtiyoriy (Optional/None) qilish:
UserUpdateSchema = User.to_pydantic(exclude=["id"], optional=["email", "username"])

# 6. PATCH so'rovi uchun barcha maydonlarni ixtiyoriy qilish (optional=True):
UserPatchSchema = User.to_pydantic(name="UserPatch", exclude=["id"], optional=True)
```

---

## 8. QuerySet API (Qidiruv, JSONB, only, defer, cache)

### A) Full-Text Search (FTS - To'liq Matnli Qidiruv):
PostgreSQL-ning `to_tsvector` va `plainto_tsquery` imkoniyati orqali matnlar ichidan lug'at boyligi bo'yicha tezkor qidiruv:

```python
# 'content' matni ichidan "python ORM" so'z birikmalarini professional qidirish:
articles = Article.filter(content__search="python ORM").all()
```

### B) PostGIS GeoSpatial (Geolokatsiya va Geometrik Qidiruv):
`fields.Point` maydoni va `distance_lte` / `dwithin` filtrlari orqali ma'lum koordinatadan belgilangan masofa (radius/metr) ichidagi obyektlarni qidirish:

```python
class Store(Model):
    name = fields.String(length=100)
    location = fields.Point(srid=4326)

# Berilgan lat/lon (masalan Toshkent: 41.311, 69.240) dan 5000 metr (5km) radiusdagi do'konlar:
nearby_stores = Store.filter(location__distance_lte=(41.311, 69.240, 5000)).all()
```

### C) JSONB Ustunlari Bo'yicha Chuqur Qidiruv:
```python
# 1. Ichki JSON kalitlari bo'yicha filtrlash (metadata->'user'->>'role' = 'admin')
User.filter(metadata__user__role="admin").all()

# 2. JSON kaliti mavjudligini tekshirish (metadata ? 'discount')
Product.filter(metadata__has_key="discount").all()

# 3. JSON mosligini tekshirish (metadata @> '{"role": "admin"}'::jsonb)
User.filter(metadata__json_contains={"role": "admin"}).all()
```

### D) QuerySet Caching (`.cache(ttl=60)`):
```python
# PostgreSQL-ga takroriy so'rov yubormasdan so'rov natijasini 60 soniya xotirada keshlaydi:
categories = Category.filter(is_active=True).cache(ttl=60).all()
```

### E) `.only()` va `.defer()` (RAM xotirani tejash):
```python
# Faqat kerakli ustunlarni yuklash:
articles = Article.query().only("title", "views").all()

# Og'ir ustunlarni yuklashni kechiktirish:
articles = Article.query().defer("body", "payload").all()
```

---

## 9. Aloqalar bilan ishlash (Relationships & String References)

`postgresdb3` ORM munosabatlar (`ForeignKey`, `OneToOne`, `ManyToMany`) uchun string shaklida model nomini berishni (`to="ModelName"`) to'liq qo'llab-quvvatlaydi. Bu orqali alohida fayllarda joylashgan modellar o'rtasidagi **Circular Import** muammolarining oldi olinadi.

Jadvallar nomlanishi avtomatik tarzda `CamelCase` -> `snake_case` ko'rinishida belgilanadi (masalan, `UserProfile` -> `user_profile`, `Category` -> `category`).

```python
# models/author.py
from postgresdb3.orm import Model, fields

class Author(Model):
    name = fields.String(length=100)
    # Author modelida profile va posts munosabatlari avtomatik dynamic resolve bo'ladi

# models/post.py (Author yoki Tag modelini bevosita import qilish SHART EMAS)
from postgresdb3.orm import Model, fields

class Post(Model):
    title = fields.String(length=200)
    # String reference - Circular import bo'lmaydi:
    author = fields.ForeignKey("Author", related_name="posts", on_delete=fields.CASCADE)
    tags = fields.ManyToMany("Tag", related_name="posts")

# models/profile.py
class Profile(Model):
    bio = fields.Text()
    author = fields.OneToOne("Author", related_name="profile", on_delete=fields.CASCADE)
```

**Munosabatlardan foydalanish:**
```python
# Forward va Reverse munosabatlarni chaqirish:
post = Post.first(id=1)
author = post.author              # Post muallifini olish

author_posts = author.posts.all()  # Muallifning barcha postlarini olish
author_profile = author.profile   # OneToOne profile obyektini olish

# ManyToMany bilan ishlash:
post.tags.add(tag1, tag2)         # Tag qo'shish
post_tags = post.tags.all()       # Post taglarini olish
post.tags.remove(tag1)            # Tag o'chirish
```

---

## 10. Migratsiya va Fixtures Tizimi (Data Migrations, Fixtures, CLI)

### Fixtures & Seed Data (CLI Buyruqlari):
```bash
# 1. Bazadagi ma'lumotlarni JSON faylga saqlash (Fixture export)
python manage.py dumpdata initial_data.json

# 2. JSON fixture faylidan ma'lumotlarni bazaga yuklash (Seed data import)
python manage.py loaddata initial_data.json

# 3. Migratsiya yaratish va qo'llash
python manage.py makemigrations
python manage.py migrate
```

---

## 11. Xatoliklar va Exceptionlar (Error Handling)

```python
from postgresdb3.exceptions import (
    PostgresDBError,
    DatabaseError,
    IntegrityError,
    UniqueViolationError,
    ForeignKeyViolationError,
    DoesNotExist,
)
```

---

## 📄 Litsenziya
Ushbu loyiha MIT litsenziyasi ostida tarqatiladi.
