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

## 🚀 Yangi (v2.0) Imkoniyatlari

Ushbu "Enterprise" versiyada loyihaga quyidagi gigant imkoniyatlar qo'shildi:
- **`values()` va `values_list()`** - Xotirani tejash uchun to'g'ridan to'g'ri `dict` yoki `list` qaytarish.
- **`get_or_create()` va `update_or_create()`** - Kodlarni sezilarli darajada qisqartirish.
- **`__` orqali Auto-Join** - Munosabatlarni avtomatik bog'lash (Masalan: `filter(user__profile__age__gt=18)`).
- **Mavhum Modellar (Abstract Models)** - Qayta-qayta kod yozmaslik uchun `class Meta: abstract = True`.
- **`annotate()` va `aggregate()`** - Murakkab matematik va guruhlash amallari.
- **`update()` va `delete()` (Ommaviy)** - Obyektlarni bazada bitta qatorda ommaviy tahrirlash yoki o'chirish.

---

## ⚡ Tezkor Boshlash

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

### 2. Modellarni Yaratish (Abstract Model namunasida)

```python
from postgresdb3.orm.models import Model, AsyncModel
from postgresdb3 import String, Integer, Float, Timestamp

Model.db = db_sync

class TimestampedModel(Model):
    class Meta:
        abstract = True # Jadval yaratilmaydi
        
    created_at = Timestamp(auto_now_add=True)

class User(TimestampedModel):
    name = String(length=50)
    age = Integer(default=18)
    score = Float(default=0.0)
    
    class Meta:
        unique_together = (("name", "age"),) # Ism va yosh bir xil takrorlanmasligi kerak
        index_together = (("score",),)       # Qidiruvni tezlashtirish uchun index
```

### 3. CRUD Operatsiyalari

**Yangi funksiyalar yordamida:**
```python
# Yaratish yoki o'qish (Bazada bo'lmasa yaratadi)
user, created = User.get_or_create(name="Ali", defaults={'age': 25, 'score': 10.0})

# Ommaviy yangilash (Xotirani to'ldirmasdan)
User.query().filter(age__lt=18).update(score=0.0)

# Ommaviy o'chirish
User.query().filter(score=0.0).delete()
```

**Tezkor O'qish (Values & Values List):**
Agar modellar bilan ishlash shart bo'lmasa va faqat JSON yuborish kerak bo'lsa:
```python
users_dict = User.query().values('id', 'name').all()
# [{'id': 1, 'name': 'Ali'}, {'id': 2, 'name': 'Vali'}]

names_list = User.query().values_list('name', flat=True).all()
# ['Ali', 'Vali']
```

---

## 🔄 Migratsiya Tizimi (CLI)

Siz o'z loyihangiz papkasida bitta `manage.py` yaratib olib, jadvallarni SQL o'qib-o'tirmasdan terminal orqali avtomatik yangilab borishingiz mumkin.

**`manage.py`:**
```python
import sys
from postgresdb3 import execute_from_command_line
from myapp.models import db_sync  # Sizning bazaga ulangan db obyektingiz

# Modellar dvigatelga ko'rinishi uchun barchasini import qilish SHART!
from myapp.models import User, Post 

if __name__ == "__main__":
    execute_from_command_line(db_sync, sys.argv)
```

**Terminalda:**
```bash
# Modellar asosida migratsiya faylini tayyorlash
python manage.py makemigrations initial_setup

# Bazaga jadvallarni qo'shish
python manage.py migrate

# Oxirgi migratsiyani bekor qilish va qaytarish (Rollback)
python manage.py undo
```

---

## 🔍 Murakkab Qidiruv va Aloqalar (Relations)

**Auto-Join (Bog'langan jadvallar bo'ylab o'tish):**
Qo'lda JOIN yozish o'rniga, qo'shaloq chiziqcha `__` ishlating:
```python
posts = Post.query().filter(author__name__startswith='A').all()
```

**Q va F ifodalar (Murakkab shartlar):**
```python
from postgresdb3 import Q, F

# OR (|) sharti
User.query().filter(Q(age__gt=20) | Q(name="Ali")).all()

# Yoshiga nisbatan score'i katta bo'lganlarni izlash
User.query().filter(score__gt=F("age")).all()
```

**N+1 xatoligini chetlab o'tish (select_related & prefetch_related):**
```python
# ForeignKey uchun (1 ta SQL so'rov)
posts = Post.query().select_related("author").all()

# ManyToMany uchun (Optimallashtirilgan yig'ish)
posts = Post.query().prefetch_related("tags").all()
```

---

## 📊 Katta Ma'lumotlar bilan Ishlash (Bulk & Pagination)

**Sahifalash (Pagination):**
Foydalanuvchiga ma'lumotlarni qismlab taqdim etish:
```python
result = User.query().paginate(page=1, per_page=20)
print(result['total'])        # Jami elementlar soni
print(result['has_next'])     # Keyingi sahifa bormi?
print(result['data'])         # Modellar ro'yxati (20 ta)
```

**Ommaviy Yozish (Bulk Create):**
10,000 ta obyekti birma-bir emas, bitta so'rov orqali kiritish:
```python
users = [User(name=f"U-{i}", age=20) for i in range(10000)]
User.bulk_create(users)
```

---

## 📈 Agregatsiya va Annotatsiya (GroupBy)

Baza orqali kalkulyatsiyalarni amalga oshirish:

```python
from postgresdb3 import Sum, Avg, Count

# Jami obshiy statiska:
result = User.query().aggregate(
    total_score=Sum("score"),
    avg_age=Avg("age")
)
# {'total_score': 1500, 'avg_age': 25}

# Guruhlab hisoblash (Masalan: Har bir userning postlari soni):
users_with_count = User.query().annotate(post_count=Count("posts")).all()
for u in users_with_count:
    print(u.name, u.post_count)
```

---

*Ushbu ORM kutubxonasi Python olamidagi ilg'or texnologiyalar yordamida tezlik va barqarorlikni birinchi o'ringa qo'yuvchi mutaxassislar uchun maxsus qurilgan.*
