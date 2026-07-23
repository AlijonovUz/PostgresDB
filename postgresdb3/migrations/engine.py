import os
import json
import datetime
from postgresdb3.orm.meta import model_registry
from postgresdb3.orm.indexes import Index


class MigrationEngine:
    def __init__(self, migrations_dir="migrations"):
        self.migrations_dir = os.path.abspath(migrations_dir)
        if not os.path.exists(self.migrations_dir):
            os.makedirs(self.migrations_dir)

    def _get_current_state(self):
        state = {}
        for model in model_registry:
            table_name = model.table
            fields = {}
            for field_name, field in model._fields.items():
                field_sql = field.to_sql()
                if not field_sql:
                    continue
                fields[field_name] = (
                    field_sql.split(" ", 1)[1] if " " in field_sql else field_sql
                )

            pk_fields = [
                fname
                for fname, f in model._fields.items()
                if getattr(f, "primary_key", False)
            ]
            meta_options = getattr(model, "_meta_options", {}).copy()

            if len(pk_fields) > 1:
                clean_fields = {}
                for fname, fsql in fields.items():
                    clean_fields[fname] = fsql.replace(" PRIMARY KEY", "")
                fields = clean_fields
                meta_options["composite_pk"] = tuple(pk_fields)
            elif not pk_fields:
                pk_name = model.get_pk_name()
                if isinstance(pk_name, str):
                    ordered_fields = {pk_name: "SERIAL PRIMARY KEY"}
                    ordered_fields.update(fields)
                    fields = ordered_fields
            if "indexes" in meta_options:
                meta_options["indexes"] = [
                    idx.to_dict() if isinstance(idx, Index) else idx
                    for idx in meta_options["indexes"]
                ]
            state[table_name] = {"fields": fields, "meta_options": meta_options}
        return state

    def validate_and_format_default(self, val_str, sql_type):
        """
        Kiritilgan matnni sql_type turiga mosligini tekshiradi va SQL uchun tayyor default qiymat stringini qaytaradi.
        Noto'g'ri tur kiritilgan bo'lsa ValueError beradi.
        """
        val_str = val_str.strip()
        clean_type = (
            sql_type.upper()
            .split("(")[0]
            .replace("NOT NULL", "")
            .replace("PRIMARY KEY", "")
            .replace("UNIQUE", "")
            .strip()
        )

        # 1. INTEGER turlari
        if clean_type in ("INTEGER", "INT", "BIGINT", "SMALLINT"):
            try:
                val = int(val_str)
                return str(val)
            except ValueError:
                raise ValueError(
                    f"'{val_str}' - {clean_type} uchun yaroqli int (butun son) emas! Masalan: 0, 10, -5"
                )

        # 2. FLOAT / DOUBLE / NUMERIC turlari
        elif clean_type in ("REAL", "FLOAT", "DOUBLE PRECISION", "NUMERIC", "DECIMAL"):
            try:
                val = float(val_str)
                return str(val)
            except ValueError:
                raise ValueError(
                    f"'{val_str}' - {clean_type} uchun yaroqli float (haqiqiy son) emas! Masalan: 3.14, 0.0"
                )

        # 3. BOOLEAN
        elif clean_type == "BOOLEAN":
            val_lower = val_str.lower()
            if val_lower in ("true", "1", "t", "yes", "y"):
                return "TRUE"
            elif val_lower in ("false", "0", "f", "no", "n"):
                return "FALSE"
            else:
                raise ValueError(
                    f"'{val_str}' - BOOLEAN turiga mos kelmaydi! Faqat 'true', 'false', '1', '0', 'yes', 'no' kiritishingiz mumkin."
                )

        # 4. TIME
        elif clean_type == "TIME":
            if val_str.upper() in ("CURRENT_TIME", "NOW()", "LOCALTIME"):
                return val_str.upper()
            clean_val = val_str.strip("'\"")
            try:
                datetime.time.fromisoformat(clean_val)
                return f"'{clean_val}'"
            except ValueError:
                raise ValueError(
                    f"'{val_str}' - TIME formati noto'g'ri! Masalan: '14:30:00', '09:00:00' yoki CURRENT_TIME"
                )

        # 5. DATE
        elif clean_type == "DATE":
            if val_str.upper() in ("CURRENT_DATE", "NOW()", "LOCALDATE"):
                return val_str.upper()
            clean_val = val_str.strip("'\"")
            try:
                datetime.date.fromisoformat(clean_val)
                return f"'{clean_val}'"
            except ValueError:
                raise ValueError(
                    f"'{val_str}' - DATE formati noto'g'ri! YYYY-MM-DD ko'rinishida kiriting (Masalan: '2025-01-01') yoki CURRENT_DATE"
                )

        # 6. TIMESTAMP / TIMESTAMPTZ
        elif clean_type in ("TIMESTAMP", "TIMESTAMPTZ", "DATETIME"):
            if val_str.upper() in ("CURRENT_TIMESTAMP", "NOW()"):
                return val_str.upper()
            clean_val = val_str.strip("'\"")
            try:
                datetime.datetime.fromisoformat(clean_val.replace(" ", "T"))
                return f"'{clean_val}'"
            except ValueError:
                raise ValueError(
                    f"'{val_str}' - TIMESTAMP formati noto'g'ri! 'YYYY-MM-DD HH:MM:SS' ko'rinishida kiriting yoki CURRENT_TIMESTAMP"
                )

        # 7. UUID
        elif clean_type == "UUID":
            clean_val = val_str.strip("'\"")
            try:
                import uuid

                uuid.UUID(clean_val)
                return f"'{clean_val}'"
            except ValueError:
                raise ValueError(
                    f"'{val_str}' - yaroqli UUID emas! (Masalan: '123e4567-e89b-12d3-a456-426614174000')"
                )

        # 8. JSON / JSONB
        elif clean_type in ("JSON", "JSONB"):
            clean_val = val_str.strip("'\"")
            try:
                json.loads(clean_val)
                return f"'{clean_val}'"
            except Exception:
                raise ValueError(
                    f"'{val_str}' - yaroqli JSON formati emas! (Masalan: '{{\"key\": \"value\"}}' yoki '[]')"
                )

        # 9. TEXT / VARCHAR / CHAR va boshqalar
        else:
            clean_val = val_str.strip("'\"")
            return f"'{clean_val}'"

    def _get_previous_state(self):
        files = sorted(
            [f for f in os.listdir(self.migrations_dir) if f.endswith(".json")]
        )
        if not files:
            return {}
        with open(
            os.path.join(self.migrations_dir, files[-1]), "r", encoding="utf-8"
        ) as f:
            data = json.load(f)
            return data.get("state", {})

    def makemigrations(self, message="auto", interactive=True, dry_run=False):
        current_state = self._get_current_state()
        previous_state = self._get_previous_state()

        operations = []
        reverse_operations = []

        if interactive:
            prev_tables = set(previous_state.keys())
            curr_tables = set(current_state.keys())
            deleted_tables = list(prev_tables - curr_tables)
            added_tables = list(curr_tables - prev_tables)

            for old_t in list(deleted_tables):
                for new_t in list(added_tables):
                    ans = input(
                        f"Jadval nomi '{old_t}' dan '{new_t}' ga o'zgartirildimi? [y/N]: "
                    )
                    if ans.lower() == "y":
                        operations.append(f"ALTER TABLE {old_t} RENAME TO {new_t};")
                        reverse_operations.append(
                            f"ALTER TABLE {new_t} RENAME TO {old_t};"
                        )
                        previous_state[new_t] = previous_state.pop(old_t)
                        deleted_tables.remove(old_t)
                        added_tables.remove(new_t)
                        break

        for table, current_data in current_state.items():
            fields = current_data["fields"]
            meta_options = current_data.get("meta_options", {})
            unique_together = meta_options.get("unique_together", ())
            index_together = meta_options.get("index_together", ())

            if table not in previous_state:
                cols = ", ".join([f"{name} {sql}" for name, sql in fields.items()])

                unique_constraints = []
                for cols_tuple in unique_together:
                    constraint_name = f"uq_{table}_{'_'.join(cols_tuple)}"
                    unique_constraints.append(
                        f"CONSTRAINT {constraint_name} UNIQUE ({', '.join(cols_tuple)})"
                    )

                composite_pk = meta_options.get("composite_pk")
                if composite_pk:
                    cols += f", PRIMARY KEY ({', '.join(composite_pk)})"

                if unique_constraints:
                    cols += ", " + ", ".join(unique_constraints)

                operations.append(f"CREATE TABLE IF NOT EXISTS {table} ({cols});")
                reverse_operations.append(f"DROP TABLE IF EXISTS {table} CASCADE;")

                for cols_tuple in index_together:
                    idx_name = f"idx_{table}_{'_'.join(cols_tuple)}"
                    operations.append(
                        f"CREATE INDEX IF NOT EXISTS {idx_name} ON {table} ({', '.join(cols_tuple)});"
                    )
                    reverse_operations.append(f"DROP INDEX IF EXISTS {idx_name};")

                indexes = meta_options.get("indexes", [])
                for idx in indexes:
                    idx_obj = idx if isinstance(idx, Index) else Index.from_dict(idx)
                    operations.append(idx_obj.to_sql(table))
                    reverse_operations.append(idx_obj.to_drop_sql(table))
            else:
                prev_data = previous_state[table]
                if isinstance(prev_data, dict) and "fields" not in prev_data:
                    prev_fields = prev_data
                    prev_meta = {}
                else:
                    prev_fields = prev_data.get("fields", {})
                    prev_meta = prev_data.get("meta_options", {})

                if interactive:
                    curr_fields_list = list(fields.keys())
                    prev_fields_list = list(prev_fields.keys())
                    deleted_fields = [
                        f for f in prev_fields_list if f not in curr_fields_list
                    ]
                    added_fields = [
                        f for f in curr_fields_list if f not in prev_fields_list
                    ]

                    for old_f in list(deleted_fields):
                        for new_f in list(added_fields):
                            ans = input(
                                f"'{table}' jadvalidagi '{old_f}' ustuni '{new_f}' ga o'zgartirildimi? [y/N]: "
                            )
                            if ans.lower() == "y":
                                operations.append(
                                    f"ALTER TABLE {table} RENAME COLUMN {old_f} TO {new_f};"
                                )
                                reverse_operations.append(
                                    f"ALTER TABLE {table} RENAME COLUMN {new_f} TO {old_f};"
                                )
                                prev_fields[new_f] = prev_fields.pop(old_f)
                                deleted_fields.remove(old_f)
                                added_fields.remove(new_f)
                                break

                for field_name, field_sql in fields.items():
                    if field_name not in prev_fields:
                        is_not_null = "NOT NULL" in field_sql
                        has_default = "DEFAULT " in field_sql
                        is_pk = "PRIMARY KEY" in field_sql
                        is_serial = "SERIAL" in field_sql or "BIGSERIAL" in field_sql

                        if (
                            is_not_null
                            and not has_default
                            and not is_pk
                            and not is_serial
                        ):
                            if interactive:
                                f_type = (
                                    field_sql.replace("NOT NULL", "")
                                    .replace("PRIMARY KEY", "")
                                    .replace("UNIQUE", "")
                                    .strip()
                                )
                                print(
                                    f"\n[!] DIQQAT: '{table}' jadvaliga NOT NULL bo'lgan '{field_name}' ({f_type}) ustuni default qiymatsiz qo'shilmoqda."
                                )
                                print(
                                    f"    Mavjud ma'lumotlar omboridagi yozuvlar uchun default qiymat berishingiz kerak."
                                )
                                print("    1) Bir martalik default qiymat kiritish")
                                print(
                                    "    2) Bekor qilish (models.py faylida default ko'rsatish uchun)"
                                )

                                chosen = False
                                while not chosen:
                                    choice = input(
                                        "Tanlang [1/2] (default: 1): "
                                    ).strip()
                                    if choice in ("", "1"):
                                        while True:
                                            val_input = input(
                                                f"'{field_name}' ({f_type}) uchun default qiymatni kiriting: "
                                            )
                                            try:
                                                formatted_def = (
                                                    self.validate_and_format_default(
                                                        val_input, f_type
                                                    )
                                                )
                                                field_sql += f" DEFAULT {formatted_def}"
                                                chosen = True
                                                break
                                            except ValueError as e:
                                                print(f"❌ {e}")
                                    elif choice == "2":
                                        print("Migratsiya bekor qilindi.")
                                        return
                                    else:
                                        print("Noto'g'ri tanlov. 1 yoki 2 ni kiriting.")

                        operations.append(
                            f"ALTER TABLE {table} ADD COLUMN {field_name} {field_sql};"
                        )
                        reverse_operations.append(
                            f"ALTER TABLE {table} DROP COLUMN {field_name};"
                        )
                    elif prev_fields[field_name] != field_sql:

                        def parse_field_sql(sql_str):
                            parts = sql_str.split(" DEFAULT ")
                            def_part = parts[1].strip() if len(parts) > 1 else None

                            clean = (
                                parts[0]
                                .replace(" PRIMARY KEY", "")
                                .replace(" UNIQUE", "")
                            )
                            is_not_null = " NOT NULL" in clean
                            clean = clean.replace(" NOT NULL", "")
                            f_type = clean.strip()
                            is_unique = " UNIQUE" in parts[0]

                            return f_type, is_not_null, def_part, is_unique

                        curr_type, curr_nn, curr_def, curr_uq = parse_field_sql(
                            field_sql
                        )
                        prev_type, prev_nn, prev_def, prev_uq = parse_field_sql(
                            prev_fields[field_name]
                        )

                        if curr_type != prev_type:
                            operations.append(
                                f"ALTER TABLE {table} ALTER COLUMN {field_name} TYPE {curr_type} USING {field_name}::{curr_type};"
                            )
                            reverse_operations.append(
                                f"ALTER TABLE {table} ALTER COLUMN {field_name} TYPE {prev_type} USING {field_name}::{prev_type};"
                            )

                        if curr_def != prev_def:
                            if curr_def:
                                operations.append(
                                    f"ALTER TABLE {table} ALTER COLUMN {field_name} SET DEFAULT {curr_def};"
                                )
                            else:
                                operations.append(
                                    f"ALTER TABLE {table} ALTER COLUMN {field_name} DROP DEFAULT;"
                                )

                            if prev_def:
                                reverse_operations.append(
                                    f"ALTER TABLE {table} ALTER COLUMN {field_name} SET DEFAULT {prev_def};"
                                )
                            else:
                                reverse_operations.append(
                                    f"ALTER TABLE {table} ALTER COLUMN {field_name} DROP DEFAULT;"
                                )

                        if curr_nn != prev_nn:
                            if curr_nn:
                                operations.append(
                                    f"ALTER TABLE {table} ALTER COLUMN {field_name} SET NOT NULL;"
                                )
                                reverse_operations.append(
                                    f"ALTER TABLE {table} ALTER COLUMN {field_name} DROP NOT NULL;"
                                )
                            else:
                                operations.append(
                                    f"ALTER TABLE {table} ALTER COLUMN {field_name} DROP NOT NULL;"
                                )
                                reverse_operations.append(
                                    f"ALTER TABLE {table} ALTER COLUMN {field_name} SET NOT NULL;"
                                )

                        if curr_uq != prev_uq:
                            if curr_uq:
                                operations.append(
                                    f"ALTER TABLE {table} ADD CONSTRAINT {table}_{field_name}_key UNIQUE ({field_name});"
                                )
                                reverse_operations.append(
                                    f"ALTER TABLE {table} DROP CONSTRAINT IF EXISTS {table}_{field_name}_key;"
                                )
                            else:
                                operations.append(
                                    f"ALTER TABLE {table} DROP CONSTRAINT IF EXISTS {table}_{field_name}_key;"
                                )
                                reverse_operations.append(
                                    f"ALTER TABLE {table} ADD CONSTRAINT {table}_{field_name}_key UNIQUE ({field_name});"
                                )

                prev_unique = [tuple(c) for c in prev_meta.get("unique_together", ())]
                prev_index = [tuple(c) for c in prev_meta.get("index_together", ())]
                unique_together_tuples = [tuple(c) for c in unique_together]
                index_together_tuples = [tuple(c) for c in index_together]

                for cols_tuple in unique_together_tuples:
                    if cols_tuple not in prev_unique:
                        constraint_name = f"uq_{table}_{'_'.join(cols_tuple)}"
                        operations.append(
                            f"ALTER TABLE {table} ADD CONSTRAINT {constraint_name} UNIQUE ({', '.join(cols_tuple)});"
                        )
                        reverse_operations.append(
                            f"ALTER TABLE {table} DROP CONSTRAINT IF EXISTS {constraint_name};"
                        )

                for cols_tuple in prev_unique:
                    if cols_tuple not in unique_together_tuples:
                        constraint_name = f"uq_{table}_{'_'.join(cols_tuple)}"
                        operations.append(
                            f"ALTER TABLE {table} DROP CONSTRAINT IF EXISTS {constraint_name};"
                        )
                        reverse_operations.append(
                            f"ALTER TABLE {table} ADD CONSTRAINT {constraint_name} UNIQUE ({', '.join(cols_tuple)});"
                        )

                for cols_tuple in index_together_tuples:
                    if cols_tuple not in prev_index:
                        idx_name = f"idx_{table}_{'_'.join(cols_tuple)}"
                        operations.append(
                            f"CREATE INDEX IF NOT EXISTS {idx_name} ON {table} ({', '.join(cols_tuple)});"
                        )
                        reverse_operations.append(f"DROP INDEX IF EXISTS {idx_name};")

                for cols_tuple in prev_index:
                    if cols_tuple not in index_together_tuples:
                        idx_name = f"idx_{table}_{'_'.join(cols_tuple)}"
                        operations.append(f"DROP INDEX IF EXISTS {idx_name};")
                        reverse_operations.append(
                            f"CREATE INDEX IF NOT EXISTS {idx_name} ON {table} ({', '.join(cols_tuple)});"
                        )

                prev_indexes_raw = prev_meta.get("indexes", [])
                prev_indexes = [
                    idx if isinstance(idx, Index) else Index.from_dict(idx)
                    for idx in prev_indexes_raw
                ]

                curr_indexes_raw = meta_options.get("indexes", [])
                curr_indexes = [
                    idx if isinstance(idx, Index) else Index.from_dict(idx)
                    for idx in curr_indexes_raw
                ]

                for idx in curr_indexes:
                    if idx not in prev_indexes:
                        operations.append(idx.to_sql(table))
                        reverse_operations.append(idx.to_drop_sql(table))

                for idx in prev_indexes:
                    if idx not in curr_indexes:
                        operations.append(idx.to_drop_sql(table))
                        reverse_operations.append(idx.to_sql(table))

        for table, prev_data in previous_state.items():
            if isinstance(prev_data, dict) and "fields" not in prev_data:
                prev_fields = prev_data
                prev_meta = {}
            else:
                prev_fields = prev_data.get("fields", {})
                prev_meta = prev_data.get("meta_options", {})

            if table not in current_state:
                if interactive:
                    ans = input(
                        f"DIQQAT: '{table}' jadvali o'chirilmoqda. Bu barcha ma'lumotlarni yo'qotadi! Davom etasizmi? [y/N]: "
                    )
                    if ans.lower() != "y":
                        print(f"Bexosdan o'chirish bekor qilindi: {table}")
                        continue
                operations.append(f"DROP TABLE IF EXISTS {table} CASCADE;")
                cols = ", ".join([f"{name} {sql}" for name, sql in prev_fields.items()])

                unique_together = prev_meta.get("unique_together", ())
                index_together = prev_meta.get("index_together", ())

                unique_constraints = []
                for idx, cols_tuple in enumerate(unique_together):
                    unique_constraints.append(f"UNIQUE ({', '.join(cols_tuple)})")

                if unique_constraints:
                    cols += ", " + ", ".join(unique_constraints)

                reverse_operations.append(
                    f"CREATE TABLE IF NOT EXISTS {table} ({cols});"
                )

                for idx, cols_tuple in enumerate(index_together):
                    idx_name = f"idx_{table}_{idx}"
                    reverse_operations.append(
                        f"CREATE INDEX IF NOT EXISTS {idx_name} ON {table} ({', '.join(cols_tuple)});"
                    )

                indexes = prev_meta.get("indexes", [])
                for idx in indexes:
                    idx_obj = idx if isinstance(idx, Index) else Index.from_dict(idx)
                    reverse_operations.append(idx_obj.to_sql(table))

            else:
                curr_fields = current_state[table]["fields"]
                for field_name in prev_fields:
                    if field_name not in curr_fields:
                        if interactive:
                            ans = input(
                                f"DIQQAT: '{table}' jadvalidagi '{field_name}' ustuni o'chirilmoqda. Barcha tegishli ma'lumotlar yo'qoladi! Davom etasizmi? [y/N]: "
                            )
                            if ans.lower() != "y":
                                print(
                                    f"Ustunni o'chirish bekor qilindi: {table}.{field_name}"
                                )
                                continue
                        operations.append(
                            f"ALTER TABLE {table} DROP COLUMN {field_name};"
                        )
                        reverse_operations.append(
                            f"ALTER TABLE {table} ADD COLUMN {field_name} {prev_fields[field_name]};"
                        )

        if not operations:
            print("O'zgarishlar topilmadi.")
            return

        if dry_run:
            print("\n[DRY RUN] Hosil bo'ladigan SQL operatsiyalar:")
            for op in operations:
                print(f"  - {op}")
            return

        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{timestamp}_{message}.json"
        filepath = os.path.join(self.migrations_dir, filename)

        migration_data = {
            "message": message,
            "operations": operations,
            "reverse_operations": reverse_operations,
            "state": current_state,
        }

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(migration_data, f, indent=4)

        print(f"Migratsiya yaratildi: {filename}")
        for op in operations:
            print(f"  - {op}")

    def create_data_migration(
        self,
        message: str = "data_migration",
        operations: list = None,
        reverse_operations: list = None,
    ):
        """
        Ma'lumotlar migratsiyasini (Data Migration) yaratish uchun maxsus metod.
        Custom SQL so'rovlarini migratsiya zanjiriga kiritish uchun ishlatiladi.
        """
        if not operations:
            print("Ma'lumotlar migratsiyasi uchun kamida bitta SQL operatsiyasi kerak.")
            return

        current_state = self._get_previous_state()
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{timestamp}_{message}.json"
        filepath = os.path.join(self.migrations_dir, filename)

        migration_data = {
            "message": message,
            "operations": operations,
            "reverse_operations": reverse_operations or [],
            "state": current_state,
        }

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(migration_data, f, indent=4)

        print(f"Ma'lumotlar migratsiyasi yaratildi: {filename}")
        for op in operations:
            print(f"  - {op}")

    def dumpdata(
        self, db, filename: str = "fixture.json", model_names: list[str] = None
    ):
        """
        Ma'lumotlar bazasidagi modellardan ma'lumotlarni JSON faylga eksport qilish (Fixtures).
        """
        from postgresdb3.orm.meta import model_registry

        fixtures = []

        for model in model_registry:
            if (
                model_names
                and model.__name__ not in model_names
                and model.table not in model_names
            ):
                continue

            records = model.query().values().all()
            for rec in records:
                fixtures.append(
                    {
                        "model": model.__name__,
                        "table": model.table,
                        "fields": rec,
                    }
                )

        with open(filename, "w", encoding="utf-8") as f:
            json.dump(fixtures, f, indent=4, default=str)

        print(f"Fixtures '{filename}' fayliga saqlandi. Jami yozuvlar: {len(fixtures)}")

    def loaddata(self, db, filename: str = "fixture.json"):
        """
        JSON fixture faylidan ma'lumotlarni ma'lumotlar bazasiga yuklash (Seed data).
        """
        from postgresdb3.orm.meta import model_registry

        if not os.path.exists(filename):
            print(f"Xato: '{filename}' fixture fayli topilmadi.")
            return

        with open(filename, "r", encoding="utf-8") as f:
            fixtures = json.load(f)

        model_map = {m.__name__: m for m in model_registry}
        model_map.update({m.table: m for m in model_registry})

        loaded_count = 0
        with db.transaction():
            for item in fixtures:
                m_name = item.get("model") or item.get("table")
                model_cls = model_map.get(m_name)
                if not model_cls:
                    print(
                        f"Ogohlantirish: '{m_name}' modeli topilmadi, o'tkazib yuborilmoqda."
                    )
                    continue

                fields_data = item.get("fields", {})
                model_cls.get_or_create(**fields_data)
                loaded_count += 1

        print(f"Fixtures bazaga muvaffaqiyatli yuklandi: {loaded_count} ta yozuv.")

    def showmigrations(self, db):
        import asyncio

        is_async = asyncio.iscoroutinefunction(db._manager)
        if is_async:
            raise ValueError(
                "Asinxron obyekt uchun 'await engine.async_showmigrations(db)' ishlating."
            )

        create_table_sql = """
        CREATE TABLE IF NOT EXISTS postgresdb3_migrations (
            id SERIAL PRIMARY KEY,
            name VARCHAR(255) UNIQUE,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """
        db._manager(create_table_sql, commit=True)
        applied_records = db.select("postgresdb3_migrations", "name")
        applied_migrations = (
            {r["name"] if isinstance(r, dict) else r[0] for r in applied_records}
            if applied_records
            else set()
        )

        files = sorted(
            [f for f in os.listdir(self.migrations_dir) if f.endswith(".json")]
        )
        print("\nMigratsiyalar ro'yxati:")
        if not files:
            print("  (Migratsiya fayllari topilmadi)")
            return

        for file in files:
            status = "[X]" if file in applied_migrations else "[ ]"
            print(f"  {status} {file}")
        print()

    async def async_showmigrations(self, db):
        create_table_sql = """
        CREATE TABLE IF NOT EXISTS postgresdb3_migrations (
            id SERIAL PRIMARY KEY,
            name VARCHAR(255) UNIQUE,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """
        await db._manager(create_table_sql, commit=True)
        applied_records = await db.select("postgresdb3_migrations", "name")
        applied_migrations = (
            {r["name"] if isinstance(r, dict) else r[0] for r in applied_records}
            if applied_records
            else set()
        )

        files = sorted(
            [f for f in os.listdir(self.migrations_dir) if f.endswith(".json")]
        )
        print("\nMigratsiyalar ro'yxati:")
        if not files:
            print("  (Migratsiya fayllari topilmadi)")
            return

        for file in files:
            status = "[X]" if file in applied_migrations else "[ ]"
            print(f"  {status} {file}")
        print()

    def migrate(self, db):
        import asyncio

        create_table_sql = """
        CREATE TABLE IF NOT EXISTS postgresdb3_migrations (
            id SERIAL PRIMARY KEY,
            name VARCHAR(255) UNIQUE,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """

        import inspect

        is_async = inspect.iscoroutinefunction(db._manager)

        if is_async:
            raise ValueError(
                "Asinxron obyekt uchun 'await engine.async_migrate(db)' ishlating."
            )

        db._manager(create_table_sql, commit=True)
        applied_records = db.select("postgresdb3_migrations", "name")

        applied_migrations = (
            {r["name"] if isinstance(r, dict) else r[0] for r in applied_records}
            if applied_records
            else set()
        )

        files = sorted(
            [f for f in os.listdir(self.migrations_dir) if f.endswith(".json")]
        )

        with db.transaction():
            for file in files:
                if file not in applied_migrations:
                    print(f"Qo'llanilmoqda: {file}...")
                    with open(
                        os.path.join(self.migrations_dir, file), "r", encoding="utf-8"
                    ) as f:
                        data = json.load(f)

                    for op in data.get("operations", []):
                        db._manager(op)

                    db.insert("postgresdb3_migrations", "name", [file])
                    print(f"Muvaffaqiyatli qo'llanildi: {file}")

    async def async_migrate(self, db):
        create_table_sql = """
        CREATE TABLE IF NOT EXISTS postgresdb3_migrations (
            id SERIAL PRIMARY KEY,
            name VARCHAR(255) UNIQUE,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """

        await db._manager(create_table_sql, commit=True)
        applied_records = await db.select("postgresdb3_migrations", "name")

        applied_migrations = (
            {r["name"] if isinstance(r, dict) else r[0] for r in applied_records}
            if applied_records
            else set()
        )

        files = sorted(
            [f for f in os.listdir(self.migrations_dir) if f.endswith(".json")]
        )

        async with db.transaction():
            for file in files:
                if file not in applied_migrations:
                    print(f"Qo'llanilmoqda: {file}...")
                    with open(
                        os.path.join(self.migrations_dir, file), "r", encoding="utf-8"
                    ) as f:
                        data = json.load(f)

                    for op in data.get("operations", []):
                        await db._manager(op, commit=True)

                    await db.insert("postgresdb3_migrations", "name", [file])
                    print(f"Muvaffaqiyatli qo'llanildi: {file}")

    def undo_migration(self, db):
        import asyncio
        import inspect

        is_async = inspect.iscoroutinefunction(db._manager)
        if is_async:
            raise ValueError(
                "Asinxron obyekt uchun 'await engine.async_undo_migration(db)' ishlating."
            )

        create_table_sql = """
        CREATE TABLE IF NOT EXISTS postgresdb3_migrations (
            id SERIAL PRIMARY KEY,
            name VARCHAR(255) UNIQUE,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """
        db._manager(create_table_sql, commit=True)
        applied_records = db.select("postgresdb3_migrations", "name")
        applied_migrations = (
            {r["name"] if isinstance(r, dict) else r[0] for r in applied_records}
            if applied_records
            else set()
        )

        files = sorted(
            [f for f in os.listdir(self.migrations_dir) if f.endswith(".json")]
        )
        if not files:
            print("Orqaga qaytarish uchun migratsiyalar topilmadi.")
            return

        last_applied = None
        for file in reversed(files):
            if file in applied_migrations:
                last_applied = file
                break

        if not last_applied:
            print("Orqaga qaytarish uchun qo'llanilgan migratsiya topilmadi.")
            return

        print(f"Orqaga qaytarilmoqda: {last_applied}...")

        with open(
            os.path.join(self.migrations_dir, last_applied), "r", encoding="utf-8"
        ) as f:
            data = json.load(f)

        with db.transaction():
            for op in reversed(data.get("reverse_operations", [])):
                db._manager(op)
            db.delete("postgresdb3_migrations", "name", last_applied)

        os.remove(os.path.join(self.migrations_dir, last_applied))
        print(f"Muvaffaqiyatli bekor qilindi va o'chirildi: {last_applied}")

    async def async_undo_migration(self, db):
        create_table_sql = """
        CREATE TABLE IF NOT EXISTS postgresdb3_migrations (
            id SERIAL PRIMARY KEY,
            name VARCHAR(255) UNIQUE,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """
        await db._manager(create_table_sql, commit=True)
        applied_records = await db.select("postgresdb3_migrations", "name")
        applied_migrations = (
            {r["name"] if isinstance(r, dict) else r[0] for r in applied_records}
            if applied_records
            else set()
        )

        files = sorted(
            [f for f in os.listdir(self.migrations_dir) if f.endswith(".json")]
        )
        if not files:
            print("Orqaga qaytarish uchun migratsiyalar topilmadi.")
            return

        last_applied = None
        for file in reversed(files):
            if file in applied_migrations:
                last_applied = file
                break

        if not last_applied:
            print("Orqaga qaytarish uchun qo'llanilgan migratsiya topilmadi.")
            return

        print(f"Orqaga qaytarilmoqda: {last_applied}...")

        with open(
            os.path.join(self.migrations_dir, last_applied), "r", encoding="utf-8"
        ) as f:
            data = json.load(f)

        async with db.transaction():
            for op in reversed(data.get("reverse_operations", [])):
                await db._manager(op, commit=True)
            await db.delete("postgresdb3_migrations", "name", last_applied)

        os.remove(os.path.join(self.migrations_dir, last_applied))
        print(f"Muvaffaqiyatli bekor qilindi va o'chirildi: {last_applied}")
