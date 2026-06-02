# PostgresDB3 - High-Performance Python ORM

**PostgresDB3** — bu PostgreSQL uchun mo'ljallangan zamonaviy, tezkor va ham **sinxron**, ham **asinxron** ishlash imkoniyatiga ega bo'lgan ORM (Object-Relational Mapping) kutubxonasi. 

U Django ORM kabi qulay va oson tushuniladi, lekin o'zida asinxronlik (`asyncpg`) va ko'plab yuqori texnologik xususiyatlarni mujassamlashtirgan. Kichik botlardan tortib, o'ta katta masshtabdagi (Highload) loyihalargacha bemalol ishlata olasiz!

---

## 📦 O'rnatish

Kutubxonani o'rnatish uchun terminalda quyidagi buyruqni kiriting:

```bash
pip install postgresdb3
```

---

## 🚀 Tezkor Boshlash

PostgresDB3 bir vaqtning o'zida ikkita dunyoni qo'llab-quvvatlaydi. Xohlasangiz **Sinxron**, xohlasangiz **Asinxron** loyihalarda bir xil sintaksis bilan ishlay olasiz.

### 1. Ulanishni sozlash

```python
from postgresdb3 import PostgresDB, AsyncPostgresDB

# Sinxron ulanish (psycopg2 asosida)
db_sync = PostgresDB("my_db", "user", "password", host="localhost", port=5432, echo=True)

# Asinxron ulanish (asyncpg asosida)
db_async = AsyncPostgresDB("my_db", "user", "password", host="localhost", port=5432, echo=True)
```
*(Eslatma: `echo=True` yoqilsa, barcha bajarilayotgan SQL so'rovlar terminalda ko'rinib turadi, bu debug uchun juda foydali).*

### 2. Modellarni Yaratish

```python
from postgresdb3.orm.models import Model, AsyncModel
from postgresdb3 import String, Integer, Float

# Sinxron model
Model.db = db_sync

class User(Model):
    name = String(length=50)
    age = Integer(default=18)
    score = Float(default=0.0)

# Asinxron model
AsyncModel.db = db_async

class AsyncUser(AsyncModel):
    name = String(length=50)
    age = Integer(default=18)
    score = Float(default=0.0)

    # Qo'shimcha sozlamalar (Murakkab Indekslar)
    class Meta:
        unique_together = (("name", "age"),) # Ism va yosh bir xil takrorlanmasligi kerak
        index_together = (("score",),)       # Qidiruvni tezlashtirish uchun index
```

### 3. CRUD (Yaratish, O'qish, Yangilash, O'chirish)

**Sinxron:**
```python
# Yaratish
user = User.create(name="Ali", age=25)

# Barchasini olish
users = User.all()

# Qidirish
user = User.query().filter(name="Ali").first()

# Yangilash
user.score = 99.5
user.save()

# O'chirish
user.delete()
```

**Asinxron:**
```python
# Yaratish
user = await AsyncUser.create(name="Vali", age=22)

# Barchasini olish
users = await AsyncUser.all()

# Qidirish
user = await AsyncUser.query().filter(name="Vali").first()

# Yangilash
user.score = 100.0
await user.save()

# O'chirish
await user.delete()
```

### 4. Raw SQL dan Model Olish
Ba'zida juda murakkab yoki spesifik SQL yozishga to'g'ri keladi. Shunday paytda u oddiy `dict` emas, to'g'ridan to'g'ri Model obyekti bo'lib qaytishi kerak:

```python
# Sinxron
users = User.raw_sql("SELECT * FROM users WHERE age > %s", 20)
print(users[0].name) # Bu Model Obyekti!

# Asinxron
users = await AsyncUser.raw_sql("SELECT * FROM asyncusers WHERE age > $1", 20)
```

---

## 🔄 Migratsiya (Django uslubida)

Siz o'z loyihangiz papkasida bitta `manage.py` yaratib olib, jadvallarni SQL o'qib-o'tirmasdan terminal orqali avtomatik yangilab borishingiz mumkin.

**`manage.py` yaratamiz:**
```python
import sys
from postgresdb3 import execute_from_command_line
from myapp.models import db_sync  # 1. Sizning bazaga ulangan db obyektingiz

# 2. DIQQAT: Migratsiya dvigateli modellarni ko'rishi uchun 
# ularni albatta import qilib qo'yishingiz SHART!
from myapp.models import User, Post, Tag 

if __name__ == "__main__":
    execute_from_command_line(db_sync, sys.argv)
```

**Terminalda:**
```bash
# 1. Modellar asosida migratsiya faylini tayyorlash
python manage.py makemigrations initial_setup

# 2. Bazaga jadvallarni qo'shish
python manage.py migrate

# 3. Oxirgi migratsiyani bekor qilish va qaytarish (Rollback)
python manage.py undo
```
*Tizim jadval qo'shish, ustunlarni o'zgartirish va `Meta` klassidagi indekslarni avtomatik o'zi hal qiladi! Xato qilsangiz, `undo` orqali bir soniyada hammasini orqaga qaytara olasiz.*

---

## 🔍 Murakkab Qidiruv va Filtrlar (Q va F)

**Q Obyekti (Murakkab shartlar - AND, OR):**
```python
from postgresdb3 import Q

# OR (|) sharti
users = User.query().filter(Q(age__gt=20) | Q(name="Ali")).all()

# AND (&) sharti
users = User.query().filter(Q(age__lt=30) & Q(score__gt=50)).all()
```

**F Obyekti (Ustunlarni bir-biriga solishtirish yoki yangilash):**
```python
from postgresdb3 import F

# Yoshiga nisbatan score'i katta bo'lganlarni izlash
users = User.query().filter(score__gt=F("age")).all()

# Barchaning balini bazaning o'zida +10 ga oshirish
User.query().update(score=F("score") + 10)
```

---

## 🔗 Aloqalar (Relations) va N+1 Yechimi

Loyiha `ForeignKey`, `OneToOneField` va `ManyToManyField` kabi turlarni to'liq qo'llab-quvvatlaydi.

```python
from postgresdb3 import ForeignKey, ManyToManyField

class Post(Model):
    title = String(length=100)
    author = ForeignKey(User, related_name="posts")

class Tag(Model):
    name = String(length=50)
    posts = ManyToManyField(Post, related_name="tags")
```

**N+1 xatoligini chetlab o'tish:**
Odatda chet el kalitlari bilan ishlaganda ko'plab ortiqcha so'rovlar yuzaga keladi. Bunga qarshi quyidagilardan foydalaning:

```python
# ForeignKey uchun
posts = Post.query().select_related("author").all()
print(posts[0].author.name) # 1 ta SQL query bilan ish bitadi

# ManyToMany uchun
posts = Post.query().prefetch_related("tags").all()
for p in posts:
    print(p.tags) # N+1 muammosi bo'lmaydi
```

---

## 📊 Katta Ma'lumotlar bilan Ishlash (Bulk & Pagination)

**Ommaviy Yozish (Bulk Create):**
10,000 ta obyekti birma-bir emas, bitta so'rov orqali kiritish:
```python
users = [User(name=f"U-{i}", age=20) for i in range(10000)]
User.bulk_create(users)
```

**Ommaviy Yangilash (Bulk Update):**
```python
users = User.all()
for u in users:
    u.age += 1
User.bulk_update(users, fields=["age"])
```

**Sahifalash (Pagination):**
Foydalanuvchiga ma'lumotlarni qismlab (limit/offset bilan avtomatik) taqdim etish:
```python
result = User.query().paginate(page=1, per_page=20)
print(result["total"])        # Jami elementlar soni
print(result["pages"])        # Jami sahifalar soni
print(result["has_next"])     # Keyingi sahifa bormi? (True/False)
print(result["data"])         # Modellar ro'yxati (20 ta)
```

---

## 🛡 Tranzaksiyalar (Xavfsizlik)

Muhim operatsiyalar (masalan, pul o'tkazish) vaqtida xato yuz bersa, barcha qilingan ishlarni avtomatik bekor qilish (Rollback):

**Sinxron:**
```python
with db_sync.transaction():
    user1.score -= 50
    user1.save()
    user2.score += 50
    user2.save()
    # Agar shu joyda qandaydir xatolik chiqsa, hech qaysi userning puli yechilmaydi!
```

**Asinxron:**
```python
async with db_async.transaction():
    user1.score -= 50
    await user1.save()
    user2.score += 50
    await user2.save()
```

---

## 📈 Agregatsiya (Sum, Avg, Min, Max, Count)

Baza orqali kalkulyatsiyalarni amalga oshirish:

```python
from postgresdb3 import Sum, Avg, Max

result = User.query().aggregate(
    total_score=Sum("score"),
    avg_age=Avg("age"),
    max_score=Max("score")
)
print(result) # {'total_score': 1500, 'avg_age': 25, 'max_score': 100}
```

---

*Ushbu ORM kutubxonasi tezlik va xavfsizlikni birinchi o'ringa qoyuvchi mutaxassislar uchun maxsus qurilgan. Mazza qilib foydalaning!*
