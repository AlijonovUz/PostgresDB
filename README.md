# 🐘 PostgresDB3 ORM

`postgresdb3` - Python tilida yozilgan, PostgreSQL ma'lumotlar bazasi bilan ishlashga mo'ljallangan, o'ta tezkor va yengil ORM (Object-Relational Mapping) kutubxonasi. U **sinxron** (`psycopg2` orqali) va **asinxron** (`asyncpg` orqali) ishlash rejimlarini to'liq qo'llab-quvvatlaydi hamda Django-ga o'xshash qulay sintaksisni taqdim etadi.

---

## 📌 Mundarija
1. [O'rnatish (Installation)](#1-ornatish-installation)
2. [Ma'lumotlar Bazasiga Ulanish](#2-malumotlar-bazasiga-ulanish)
3. [Modellarni Yaratish (Models)](#3-modellarni-yaratish-models)
4. [Maydonlar (Fields)](#4-maydonlar-fields)
5. [Validatorlar (Validation)](#5-validatorlar-validation)
6. [Model Metodlari va Hooklar (Hooks)](#6-model-metodlari-va-hooklar-hooks)
7. [CRUD Operatsiyalari](#7-crud-operatsiyalari)
8. [QuerySet API (Qidiruv va Filtrlash)](#8-queryset-api-qidiruv-va-filtrlash)
9. [Aloqalar bilan ishlash (Relationships)](#9-aloqalar-bilan-ishlash-relationships)
10. [Migratsiya Tizimi (CLI va Kod orqali)](#10-migratsiya-tizimi-cli-va-kod-orqali)

---

## 1. O'rnatish (Installation)

Loyihangizga kutubxonani o'rnatish uchun:

```bash
pip install postgresdb3
```

> **Eslatma:** Agar siz sinxron dvigatelda ishlamoqchi bo'lsangiz, tizimingizda `libpq-dev` (Linux) o'rnatilgan bo'lishi kerak. Aks holda `psycopg2-binary` kutubxonasini alohida o'rnatib olishingiz mumkin.

---

## 2. Ma'lumotlar Bazasiga Ulanish

PostgresDB3 sinxron va asinxron ulanishlarni alohida dvigatellar yordamida amalga oshiradi. Ulanishlar hovuzi (Connection Pool) avtomatik tarzda boshqariladi.

### Sinxron ulanish (`PostgresDB`)
```python
from postgresdb3 import PostgresDB

db_sync = PostgresDB(
    database="my_db",
    user="postgres",
    password="my_password",
    host="localhost",
    port=5432,
    minconn=1,   # Minimal ulanishlar soni
    maxconn=20,  # Maksimal ulanishlar soni
    echo=True    # SQL so'rovlarini terminalga chiqarish (Debug)
)
```

### Asinxron ulanish (`AsyncPostgresDB`)
```python
from postgresdb3 import AsyncPostgresDB

db_async = AsyncPostgresDB(
    database="my_db",
    user="postgres",
    password="my_password",
    host="localhost",
    port=5432,
    min_size=1,
    max_size=20,
    echo=True
)
```

---

## 3. Modellarni Yaratish (Models)

Sizning modellariz bazadagi jadvallarni ifodalaydi. Sinxron modellar `Model` klassidan, asinxron modellar esa `AsyncModel` klassidan meros oladi.

```python
from postgresdb3.orm.models import Model, AsyncModel
from postgresdb3 import String, Integer

# Sinxron model
class Category(Model):
    name = String(length=50, unique=True)

    class Meta:
        table_name = "categories"  # Jadval nomi (ixtiyoriy, berilmasa klass nomi olinadi)

# Asinxron model
class AsyncCategory(AsyncModel):
    name = String(length=50, unique=True)
```

### Meta xususiyatlari:
* `table_name` yoki `db_table` (str): Bazadagi jadval nomi (masalan: `table_name = "custom_table"`).
* `abstract` (bool): `True` bo'lsa, ushbu model uchun jadval yaratilmaydi (faqat boshqa modellarga meros qoldirish uchun xizmat qiladi).
* `ordering` (list/tuple): Standart saralash tartibi (masalan: `ordering = ["-created_at", "id"]`). Bu filtrlashda avtomatik ravishda `ORDER BY created_at DESC, id ASC` ko'rinishida qo'llanadi.
* `unique_together` (tuple): Bir nechta maydonlarning birgalikdagi takrorlanmasligi sharti.
* `index_together` (tuple): Birgalikda indeks yaratiladigan maydonlar guruhi.
* `indexes` (list): Django uslubidagi murakkab indekslar ro'yxati (`Index(fields=[...], name=..., unique=..., using=..., condition=..., include=[...])`).
* `verbose_name` / `verbose_name_plural` (str): Modelning inson tushunadigan tildagi yakka/ko'plik nomi.

#### Indekslar bilan ishlash (`Index`):
```python
from postgresdb3 import Model, String, Integer, Index

class Product(Model):
    category = String(length=50)
    price = Integer()
    status = String(length=20)

    class Meta:
        indexes = [
            Index(fields=["category", "price"], name="idx_prod_cat_price"), # Ko'p ustunli indeks
            Index(fields=["-price"], name="idx_prod_price_desc"),           # Kamayish tartibidagi (DESC) indeks
            Index(fields=["status"], condition="status = 'active'"),        # Qisman (partial) indeks
            Index(fields=["category"], using="gin"),                        # Indeks turi (btree, hash, gin, gist)
        ]
```

#### Meta Merosxo'rligi (Meta Inheritance):
Ota model (Parent class) abstract bo'lsa, undan meros oluvchi subclasslar avtomatik tarzda ota klassning Meta xususiyatlarini (masalan, `ordering`, `unique_together` kabi) meros qilib oladi. Agar siz ota klass Meta xususiyatlarini saqlagan holda qo'shimcha qilmoqchi bo'lsangiz, Python'ning standart merosxo'rlik sintaksisidan foydalanishingiz mumkin:

```python
class ParentModel(Model):
    class Meta:
        abstract = True
        ordering = ["-created_at"]

class ChildModel(ParentModel):
    class Meta(ParentModel.Meta):
        db_table = "custom_child_table" # Ota klassdagi ordering avtomatik saqlanib qoladi!
```

---

## 4. Maydonlar (Fields)

PostgresDB3 juda ko'p turdagi maydonlarni taqdim etadi. Har bir maydon ma'lum bir SQL turiga to'g'ri keladi.

### Barcha maydonlar uchun umumiy parametrlar:
* **`verbose_name`** (str): Maydonning inson o'qishi uchun qulay bo'lgan nomi. Uni birinchi positional argument (masalan: `String("To'liq ism", length=50)`) yoki keyword argument (masalan: `Integer(verbose_name="Yosh")`) sifatida uzatish mumkin. Agar validation xatoligi yuzaga kelsa, ORM avtomatik ravishda ushbu nomdan foydalanib xatolik xabarini chiqaradi.
* `nullable` (bool): Maydon `NULL` qiymat qabul qiladimi? (Default: `False`)
* `default` (Any): Standart qiymat.
* `primary_key` (bool): Birlamchi kalitmi? (Default: `False`)
* `unique` (bool): Qiymat takrorlanmas bo'lishi kerakmi? (Default: `False`)
* `validators` (list): Maydon qiymatini tekshiruvchi chaqiriluvchi (callable) funksiyalar ro'yxati.

### Matematik maydonlar:
* `Integer`: Oddiy butun son (`integer`).
* `SmallInteger`: Kichik butun son (`smallint`).
* `BigInteger`: Katta butun son (`bigint`).
* `Float`: Haqiqiy son (`real`).
* `Double`: Yuqori aniqlikdagi son (`double precision`).
* `Decimal`: Belgilangan aniqlikdagi o'nli kasr son.

### Matnli maydonlar:
* `String(length)`: Belgilangan uzunlikdagi satr (`varchar`). `length` parametri majburiy.
* `Text`: Cheklanmagan uzunlikdagi matn (`text`).

### Mantiqiy va Maxsus maydonlar:
* `Boolean`: Mantiqiy maydon (`boolean`).
* `UUID`: UUID formatidagi maydon (`uuid`).
* `JSON` / `JSONB`: JSON formatidagi ma'lumotlar uchun.
* `Array(item_type)`: Massivlar uchun (masalan: `Array(Integer)` -> `integer[]`).
* `Serial` / `BigSerial`: Avtomatik o'suvchi birlamchi kalitlar.

### Aloqalar (Relationship Fields):
* **`ForeignKey(to, to_field=None, related_name=None, on_delete="CASCADE")`**: Ko'pga-bir (Many-to-One) aloqasi.
* **`OneToOneField(to, to_field=None, related_name=None, on_delete="CASCADE")`**: Birga-bir (One-to-One) aloqasi (avtomatik `unique=True` qo'shiladi).
* **`ManyToManyField(to, related_name=None)`**: Ko'pga-ko'p (Many-to-Many) aloqasi (ikkala modelni bog'laydigan uchinchi jadval yaratiladi).

#### Aloqa parametrlari:
* `to`: Bog'lanayotgan maqsadli model klassi (target model).
* `related_name` (str): Qarama-qarshi modeldan ushbu modelga murojaat qilish uchun ishlatiladigan nom. Masalan, `Post` modelida `author = ForeignKey(User, related_name="posts")` deb yozilsa, `user` obyektidan uning barcha postlarini `user.posts` orqali olish imkoni yaratiladi.
* `to_field` (str): Maqsadli modeldagi bog'lanayotgan maydon nomi (sukut bo'yicha birlamchi kalit/primary key olinadi).
* `on_delete`: Bog'langan yozuv o'chirilganda bajariladigan amal (`"CASCADE"`, `"SET NULL"`, `"RESTRICT"`, `"NO ACTION"`). Sukut bo'yicha: `"CASCADE"`.

---

## 5. Validatorlar (Validation)

Ma'lumotlar bazaga saqlanishidan oldin qiymatlarni tekshirish uchun Django uslubidagi validatorlardan foydalaniladi. Tekshiruvdan o'tmagan holatda `ValidationError` xatoligi yuzaga keladi.

### built-in validatorlar:
* **`MinValueValidator(limit_value, message=None)`**: Qiymat belgilangan miqdordan kichik bo'lmasligini tekshiradi.
* **`MaxValueValidator(limit_value, message=None)`**: Qiymat belgilangan miqdordan katta bo'lmasligini tekshiradi.
* **`MinLengthValidator(limit_value, message=None)`**: Satr/Massiv uzunligi minimal shartga javob berishini tekshiradi.
* **`MaxLengthValidator(limit_value, message=None)`**: Satr/Massiv uzunligi maksimal cheklovdan oshmasligini tekshiradi.
* **`RegexValidator(regex, message=None)`**: Qiymat muntazam ifodaga (regular expression) mos kelishini tekshiradi.
* **`EmailValidator(message=None)`**: Elektron pochta manzili formatini tekshiradi.

#### Ishlatilishi:
```python
from postgresdb3 import String, Integer, EmailValidator, MinValueValidator

class User(Model):
    age = Integer(validators=[MinValueValidator(18)])
    email = String(length=100, validators=[EmailValidator()])
```

### Maxsus validator (Custom Validator) yaratish:
Qiymat qabul qilib, xato bo'lsa `ValidationError` ko'taradigan oddiy funksiya yozish kifoya:

```python
from postgresdb3 import ValidationError

def validate_even(value):
    if value % 2 != 0:
        raise ValidationError(f"{value} juft son bo'lishi shart!")
```

---

## 6. Model Metodlari va Hooklar (Hooks)

Siz model klassi metodlarini qayta yozib (override qilib), saqlash va o'chirish jarayonlarini nazorat qilishingiz mumkin.

### 1. `clean()` - Model darajasidagi tekshiruvlar
Bir nechta maydonlarni o'zaro solishtirish uchun ishlatiladi:
```python
class User(Model):
    password = String(length=128)
    password_confirm = String(length=128)

    def clean(self):
        super().clean()  # Field validatorlarini ishga tushirish uchun!
        if self.password != self.password_confirm:
            raise ValidationError("Parollar o'zaro mos emas!")
```

### 2. `before_save()` va `after_save(created: bool)`
Ma'lumot yozilishidan oldin qiymatni o'zgartirish (masalan: parolni xeshlash) va yozilgandan keyin biron amal bajarish uchun:
```python
import hashlib

class User(Model):
    username = String(length=50)
    password = String(length=128)
    password_hash = String(length=128, nullable=True)

    def before_save(self):
        if self.password:
            self.password_hash = hashlib.sha256(self.password.encode()).hexdigest()
            self.password = None  # Asl parolni tozalaymiz

    def after_save(self, created: bool):
        if created:
            print("Yangi foydalanuvchi yaratildi!")
```

### 3. `before_delete()` va `after_delete()`
Yozuv bazadan o'chirilishidan oldin va o'chirilgandan so'ng ishga tushadi.

---

## 7. CRUD Operatsiyalari

Sinxron va asinxron modellarda yozuvlarni yaratish, o'qish, yangilash va o'chirish usullari:

### Yozuv Yaratish (Create)
```python
# Sinxron:
user = User.create(username="ali", age=25)
# Yoki:
user = User(username="ali", age=25)
user.save()

# Asinxron:
user = await AsyncUser.create(username="ali", age=25)
# Yoki:
user = AsyncUser(username="ali", age=25)
await user.save()
```

### Yozuv O'qish (Read)
```python
# Sinxron:
user = User.query().filter(id=1).first()

# Asinxron:
user = await AsyncUser.query().filter(id=1).first()
```

### Yozuv Yangilash (Update)
```python
# Sinxron:
user.age = 26
user.save()

# Asinxron:
user.age = 26
await user.save()
```

### Yozuv O'chirish (Delete)
```python
# Sinxron:
user.delete()

# Asinxron:
await user.delete()
```

---

## 8. QuerySet API (Qidiruv va Filtrlash)

QuerySet orqali bazadan ma'lumotlarni turli shartlar bilan filtrlash, tartiblash va optimallashtirish amalga oshiriladi.

### Asosiy qidiruv metodlari:
* `.filter(*args, **kwargs)`: Shartga mos yozuvlarni olish.
* `.exclude(*args, **kwargs)`: Shartga mos bo'lmagan yozuvlarni olish.
* `.order_by(field)`: Tartiblash (teskari tartiblash uchun boshiga `-` qo'yiladi: `-age`).
* `.limit(n)`: Natijalar sonini cheklash.
* `.offset(n)`: Boshidan ma'lum miqdordagi yozuvlarni tashlab yuborish.
* **`.select_for_update()`**: Tranzaksiya doirasida tanlangan yozuvlarni qulflash (Pessimistic locking). Balanslarni yangilash, to'lovlar yoki zaxira mahsulotlarini kamaytirish kabi parallel poyga holatlarining (race condition) oldini oladi.

#### Misollar:
```python
# Yosh 18 dan katta va ism 'A' harfi bilan boshlanadigan foydalanuvchilar
users = User.query().filter(age__gt=18, name__startswith="A").order_by("-age").all()
```

### Qidiruv shablonlari (Lookup field suffixes):
* `__gt` / `__gte`: Katta / Katta yoki teng.
* `__lt` / `__lte`: Kichik / Kichik yoki teng.
* `__contains` / `__icontains`: Matn ichida mavjudligi (registrsiz).
* `__startswith` / `__endswith`: Matn boshlanishi / tugashi.
* `__in`: Berilgan ro'yxat ichida mavjudligi (`id__in=[1, 2, 3]`).

### Murakkab Shartlar (`Q` va `F` Expressions):
`Q` - shartlarni `OR` (`|`) yoki `AND` (`&`) orqali bog'lash uchun.
`F` - maydon qiymatini boshqa maydon bilan solishtirish uchun.

```python
from postgresdb3 import Q, F

# Ismi 'Ali' YOKI yoshi 20 dan katta bo'lganlar
users = User.query().filter(Q(name="Ali") | Q(age__gt=20)).all()

# Ball yoshidan baland bo'lganlar
users = User.query().filter(score__gt=F("age")).all()
```

### Ommaviy Operatsiyalar (Bulk Operations)

#### 1. Query-level ommaviy yangilash va o'chirish:
Bazada birdaniga bir nechta qatorlarni Python xotirasiga yuklamasdan to'g'ridan-to'g'ri o'zgartirish yoki o'chirish (avtomatik himoyalangan: shart kiritilishi majburiy):

```python
# Yosh 18 dan kichik bo'lgan barcha foydalanuvchilar ballini 0 ga tushirish
User.query().filter(age__lt=18).update(score=0.0)

# Balli 0 bo'lgan barcha foydalanuvchilarni o'chirish
User.query().filter(score=0.0).delete()
```

#### 2. `bulk_create` (Klass darajasidagi ommaviy yaratish):
Ko'plab model nusxalarini (instances) bitta INSERT so'rovi orqali bazaga juda tez yozish uchun ishlatiladi:

```python
users = [
    User(name="User 1", age=20),
    User(name="User 2", age=25),
    User(name="User 3", age=30),
]
# Sinxron:
User.bulk_create(users)

# Asinxron:
await AsyncUser.bulk_create(async_users)
```

#### 3. `bulk_update` (Klass darajasidagi ommaviy yangilash):
Mavjud model nusxalarining belgilangan maydonlarini bitta so'rov orqali bazada yangilash uchun xizmat qiladi:

```python
# Model obyektlarining maydonlarini o'zgartiramiz
for user in users_list:
    user.age += 1

# Sinxron (faqat belgilangan 'age' maydoni bazada yangilanadi):
User.bulk_update(users_list, fields=["age"])

# Asinxron:
await AsyncUser.bulk_update(async_users_list, fields=["age"])
```

---

### Tranzaksiyalar (Transactions)

PostgresDB3 tranzaksiyalar bilan ishlashni juda qulay va xavfsiz qiladi. Buning uchun ikki xil usul mavjud:

#### 1. Context Manager sifatida (`with` / `async with`):
Kodni ma'lum bir qismini tranzaksiya ichida bajarish uchun:

```python
# Sinxron:
with User.db.transaction():
    user1 = User.create(name="Ali", age=22)
    user2 = User.create(name="Vali", age=25)

# Asinxron:
async with AsyncUser.db.transaction():
    await AsyncUser.create(name="Ali", age=22)
    await AsyncUser.create(name="Vali", age=25)
```

#### 2. Decorator sifatida (`@db.atomic()`):
Butun funksiyani avtomatik tranzaksiyaga o'rab qo'yish uchun:

```python
# Sinxron:
@User.db.atomic()
def transfer_funds(sender_id, receiver_id, amount):
    sender = User.query().select_for_update().filter(id=sender_id).first()
    receiver = User.query().select_for_update().filter(id=receiver_id).first()
    
    sender.balance -= amount
    receiver.balance += amount
    sender.save()
    receiver.save()

# Asinxron:
@AsyncUser.db.atomic()
async def async_transfer_funds(sender_id, receiver_id, amount):
    sender = await AsyncUser.query().select_for_update().filter(id=sender_id).first()
    receiver = await AsyncUser.query().select_for_update().filter(id=receiver_id).first()
    
    sender.balance -= amount
    receiver.balance += amount
    await sender.save()
    await receiver.save()
```

---

### Sahifalash (Pagination)
```python
# Sinxron (PaginationResult obyekti qaytadi):
result = User.query().paginate(page=1, per_page=10)
print(result.total)        # Jami yozuvlar soni
print(result.pages)        # Jami sahifalar
print(result.data)         # Model nusxalari ro'yxati (List[User])

# Asinxron (Lug'at ko'rinishida qaytadi):
result = await AsyncUser.query().paginate(page=1, per_page=10)
print(result["total"])
print(result["data"])      # List[AsyncUser]
```

### Aggregatsiyalar va Hisob-kitoblar (`aggregate` & `annotate`):
* `Count`, `Sum`, `Avg`, `Max`, `Min` funktsiyalarini qo'llash:

```python
from postgresdb3 import Sum, Avg, Count

# O'rtacha yosh va jami ballni hisoblash
stats = User.query().aggregate(avg_age=Avg("age"), total_score=Sum("score"))
print(stats)  # {'avg_age': 25.4, 'total_score': 1250.0}

# Har bir foydalanuvchi postlari sonini qo'shib olish
users = User.query().annotate(posts_count=Count("posts")).all()
print(users[0].posts_count)
```

### Bog'lanishlarni yuklash (N+1 muammosini hal qilish):
* Sinxron / Asinxron aloqalarni optimallashtirish:
```python
# ForeignKey uchun JOIN ishlatadi (select_related)
posts = Post.query().select_related("author").all()

# ManyToMany yoki OneToMany uchun alohida so'rov bilan yig'adi (prefetch_related)
posts = Post.query().prefetch_related("tags").all()
```

---

### Sof SQL So'rovlari (Raw SQL Queries)

Murakkab so'rovlar yoki to'g'ridan-to'g'ri SQL kodini yozish kerak bo'lgan holatlar uchun PostgresDB3 quyidagi imkoniyatlarni taqdim etadi:

#### 1. Model nusxalarini qaytaruvchi Raw SQL (`raw_sql`):
Sof SQL yozib, natijalarni avtomatik ravishda tegishli Model obyektlari (instances) ko'rinishida olish uchun:

```python
# Sinxron (psycopg2 parametrlaridan foydalanadi: %s):
users = User.raw_sql("SELECT * FROM users WHERE age > %s AND status = %s", 18, "active")
for user in users:
    print(user.name)  # Obyekt maydonlariga to'g'ridan-to'g'ri murojaat qilish

# Asinxron (asyncpg parametrlari: $1, $2):
users = await AsyncUser.raw_sql("SELECT * FROM users WHERE age > $1 AND status = $2", 18, "active")
```

#### 2. Bazaning pastki darajali drayveri orqali Raw SQL:
Model obyektlarisiz, oddiy lug'at (dictionary) yoki ro'yxat ko'rinishidagi ma'lumotlarni to'g'ridan-to'g'ri olish yoki bazaga o'zgartirish kiritish uchun:

```python
# Sinxron (db.raw orqali):
record = User.db.raw("SELECT name, balance FROM users WHERE id = %s", [1], fetchone=True)
print(record["name"])

# Asinxron (db._manager orqali):
records = await AsyncUser.db._manager("SELECT name, balance FROM users WHERE age > $1", 18, fetchall=True)
```

---

## 9. Aloqalar bilan ishlash (Relationships)

PostgresDB3 munosabatlarni to'g'ri o'rnatish, ma'lumotlarni bog'lash, so'rovlarni avtomatik optimallashtirish va Django-style qulayliklarni qo'llab-quvvatlaydi.

### A) Sinxron modellarda aloqalar bilan ishlash (`Model`)

#### 1. ForeignKey (One-to-Many) va OneToOneField (Birga-bir)
Kutubxona maydon nomini avtomatik tarzda database ustuniga (`_id` qo'shimchasi bilan) xaritlaydi va descriptorlar orqali aloqalarni boshqaradi.

```python
# Modellar:
class User(Model):
    table = "users"
    name = String()

class Order(Model):
    table = "orders"
    user = ForeignKey(User)  # Bazada 'user_id' ustuni yaratiladi
    amount = Integer()

# Ma'lumot qo'shish (Django-style, obyektning o'zini uzatish):
new_user = User.create(name="Ali")
order = Order.create(user=new_user, amount=50000)

# Yoki ID orqali saqlash:
order = Order.create(user_id=new_user.id, amount=50000)

# Bog'langan model ma'lumotini o'qish (Lazy Loading):
fetched_order = Order.filter(id=order.id).first()
related_user = fetched_order.user  # Bazadan avtomatik yuklanadi
print(related_user.name)  # Ali
```

#### 2. ManyToManyField (Ko'pga-ko'p)
ManyToMany munosabatlarida bog'liqliklar uchinchi oraliq jadvalda (`{table1}_{table2}`) saqlanadi va ularni boshqarish uchun `.add()`, `.remove()`, `.clear()` va `.all()` metodlaridan foydalaniladi.

```python
# Modellar:
class Tag(Model):
    table = "tags"
    name = String()

class Product(Model):
    table = "products"
    tags = ManyToManyField(Tag)
    price = Integer()

product = Product.create(price=15000)
tag_new = Tag.create(name="Yangi")
tag_sale = Tag.create(name="Chegirma")

# Bog'lash (Obyektlar yoki ID-lar orqali):
product.tags.add(tag_new, tag_sale)

# Bog'liqlikni o'chirish:
product.tags.remove(tag_new)

# Barcha bog'langan teglarni o'qish:
tags = product.tags.all()

# Barcha bog'liqliklarni tozalash:
product.tags.clear()
```

---

### B) Asinxron modellarda aloqalar bilan ishlash (`AsyncModel`)

Asinxron rejimda aloqalar va metodlar `await` orqali ishlatilishi lozim.

#### 1. ForeignKey va Lazy Loading
```python
# Modellar:
class AsyncUser(AsyncModel):
    table = "users"
    name = String()

class AsyncOrder(AsyncModel):
    table = "orders"
    user = ForeignKey(AsyncUser)
    amount = Integer()

# Asinxron yozuv yaratish:
user = await AsyncUser.create(name="Ali (Async)")
order = await AsyncOrder.create(user=user, amount=120000)

# Asinxron Lazy Loading (e'tibor bering, bog'lanish await qilinadi):
fetched_order = await AsyncOrder.filter(id=order.id).first()
related_user = await fetched_order.user  # COROUTINE obyekti await qilinadi
print(related_user.name)
```

#### 2. ManyToManyField
```python
# Asinxron bog'lanish qo'shish:
await product.tags.add(tag1, tag2)

# Asinxron bog'lanish o'chirish:
await product.tags.remove(tag1)

# Asinxron barcha bog'liqliklarni o'qib olish:
tags = await product.tags.all()

# Asinxron tozalash:
await product.tags.clear()
```

---

## 10. Migratsiya Tizimi (CLI va Kod orqali)

PostgresDB3 o'z ichida model o'zgarishlarini kuzatib boruvchi va bazadagi jadvallarni avtomatik yangilovchi migratsiya dvigateliga ega.

### A) Terminal orqali boshqarish (CLI)
Avvalo loyihangizda `manage.py` faylini yarating:

```python
import sys
from postgresdb3 import execute_from_command_line
from myapp.models import db_sync  # Ulanish obyekti
from myapp.models import User, Post  # Barcha modellar import qilinishi shart!

if __name__ == "__main__":
    execute_from_command_line(db_sync, sys.argv)
```

**Terminal komandalari:**
```bash
# 1. Modellarni tahlil qilib migratsiya faylini yaratish
python manage.py makemigrations initial_setup

# 1.1. CI/CD pipelines yoki avtomatlashtirilgan (Docker) tizimlarda so'rovlarsiz ishga tushirish uchun:
python manage.py makemigrations initial_setup --no-input

# 2. Yaratilgan migratsiyalarni bazaga qo'llash (jadvallarni yaratish)
python manage.py migrate

# 3. Oxirgi migratsiyani bekor qilish (Rollback)
python manage.py undo
```

### B) Dasturiy ravishda boshqarish (Programmatic)
Terminal bo'lmagan muhitlarda (masalan: dastur kodining o'zida) migratsiyalarni bajarish:

```python
from postgresdb3.migrations.engine import MigrationEngine
from myapp.models import db_sync, db_async

engine = MigrationEngine()

# 1. Migratsiya faylini tayyorlash
# (interactive=False bo'lsa, ogohlantirish so'ramaydi - CI/CD uchun qulay)
engine.makemigrations(name="auto_setup", interactive=False)

# 2. Sinxron bazani yangilash
engine.migrate(db_sync)

# 3. Asinxron bazani yangilash (asinxron funksiya ichida chaqiriladi)
await engine.async_migrate(db_async)

# 4. Sinxron/Asinxron migratsiyani orqaga qaytarish
engine.undo_migration(db_sync)
await engine.async_undo_migration(db_async)
```

---

## 📄 Litsenziya
Ushbu loyiha MIT litsenziyasi ostida tarqatiladi.
