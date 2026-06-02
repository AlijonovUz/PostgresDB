import os
import json
import datetime
from postgresdb3.orm.meta import model_registry

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
                fields[field_name] = field_sql.split(" ", 1)[1] if " " in field_sql else field_sql
                if getattr(field, "primary_key", False):
                    fields[field_name] += " PRIMARY KEY"
            
            if not any(getattr(f, "primary_key", False) for f in model._fields.values()):
                ordered_fields = {model.get_pk_name(): "SERIAL PRIMARY KEY"}
                ordered_fields.update(fields)
                fields = ordered_fields
                
            meta_options = getattr(model, "_meta_options", {})
            state[table_name] = {
                "fields": fields,
                "meta_options": meta_options
            }
        return state

    def _get_previous_state(self):
        files = sorted([f for f in os.listdir(self.migrations_dir) if f.endswith(".json")])
        if not files:
            return {}
        with open(os.path.join(self.migrations_dir, files[-1]), "r", encoding="utf-8") as f:
            data = json.load(f)
            return data.get("state", {})

    def makemigrations(self, message="auto"):
        current_state = self._get_current_state()
        previous_state = self._get_previous_state()

        operations = []
        reverse_operations = []

        for table, current_data in current_state.items():
            fields = current_data["fields"]
            meta_options = current_data.get("meta_options", {})
            unique_together = meta_options.get("unique_together", ())
            index_together = meta_options.get("index_together", ())
            
            if table not in previous_state:
                cols = ", ".join([f"{name} {sql}" for name, sql in fields.items()])
                
                unique_constraints = []
                for idx, cols_tuple in enumerate(unique_together):
                    unique_constraints.append(f"UNIQUE ({', '.join(cols_tuple)})")
                
                if unique_constraints:
                    cols += ", " + ", ".join(unique_constraints)
                    
                operations.append(f"CREATE TABLE IF NOT EXISTS {table} ({cols});")
                reverse_operations.append(f"DROP TABLE IF EXISTS {table} CASCADE;")
                
                for idx, cols_tuple in enumerate(index_together):
                    idx_name = f"idx_{table}_{idx}"
                    operations.append(f"CREATE INDEX IF NOT EXISTS {idx_name} ON {table} ({', '.join(cols_tuple)});")
                    reverse_operations.append(f"DROP INDEX IF EXISTS {idx_name};")
            else:
                prev_data = previous_state[table]
                if isinstance(prev_data, dict) and "fields" not in prev_data:
                    prev_fields = prev_data
                    prev_meta = {}
                else:
                    prev_fields = prev_data.get("fields", {})
                    prev_meta = prev_data.get("meta_options", {})
                    
                for field_name, field_sql in fields.items():
                    if field_name not in prev_fields:
                        operations.append(f"ALTER TABLE {table} ADD COLUMN {field_name} {field_sql};")
                        reverse_operations.append(f"ALTER TABLE {table} DROP COLUMN {field_name};")
                    elif prev_fields[field_name] != field_sql:
                        clean_type = field_sql.split(" DEFAULT ")[0].replace(" PRIMARY KEY", "").replace(" UNIQUE", "").replace(" NOT NULL", "").strip()
                        operations.append(f"ALTER TABLE {table} ALTER COLUMN {field_name} TYPE {clean_type} USING {field_name}::{clean_type};")
                        
                        prev_sql = prev_fields[field_name]
                        prev_clean = prev_sql.split(" DEFAULT ")[0].replace(" PRIMARY KEY", "").replace(" UNIQUE", "").replace(" NOT NULL", "").strip()
                        reverse_operations.append(f"ALTER TABLE {table} ALTER COLUMN {field_name} TYPE {prev_clean} USING {field_name}::{prev_clean};")

        for table, prev_data in previous_state.items():
            if isinstance(prev_data, dict) and "fields" not in prev_data:
                prev_fields = prev_data
            else:
                prev_fields = prev_data.get("fields", {})
                
            if table not in current_state:
                operations.append(f"DROP TABLE IF EXISTS {table} CASCADE;")
                cols = ", ".join([f"{name} {sql}" for name, sql in prev_fields.items()])
                reverse_operations.append(f"CREATE TABLE IF NOT EXISTS {table} ({cols});")
            else:
                curr_fields = current_state[table]["fields"]
                for field_name in prev_fields:
                    if field_name not in curr_fields:
                        operations.append(f"ALTER TABLE {table} DROP COLUMN {field_name};")
                        reverse_operations.append(f"ALTER TABLE {table} ADD COLUMN {field_name} {prev_fields[field_name]};")

        if not operations:
            print("O'zgarishlar topilmadi.")
            return

        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{timestamp}_{message}.json"
        filepath = os.path.join(self.migrations_dir, filename)

        migration_data = {
            "message": message,
            "operations": operations,
            "reverse_operations": reverse_operations,
            "state": current_state
        }

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(migration_data, f, indent=4)

        print(f"Migratsiya yaratildi: {filename}")
        for op in operations:
            print(f"  - {op}")

    def migrate(self, db):
                                                                                     
        import asyncio
        
                                                              
        create_table_sql = """
        CREATE TABLE IF NOT EXISTS postgresdb3_migrations (
            id SERIAL PRIMARY KEY,
            name VARCHAR(255) UNIQUE,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """
        
        import asyncio
        is_async = asyncio.iscoroutinefunction(db._manager)
        
        if is_async:
            raise ValueError("Asinxron obyekt uchun 'await engine.async_migrate(db)' ishlating.")
            
        db._manager(create_table_sql, commit=True)
        applied_records = db.select("postgresdb3_migrations", "name")
            
        applied_migrations = {r["name"] if isinstance(r, dict) else r[0] for r in applied_records} if applied_records else set()

        files = sorted([f for f in os.listdir(self.migrations_dir) if f.endswith(".json")])
        
        for file in files:
            if file not in applied_migrations:
                print(f"Qo'llanilmoqda: {file}...")
                with open(os.path.join(self.migrations_dir, file), "r", encoding="utf-8") as f:
                    data = json.load(f)
                
                for op in data.get("operations", []):
                    db._manager(op, commit=True)
                
                db.insert("postgresdb3_migrations", "name", (file,))
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
        
        applied_migrations = {r["name"] if isinstance(r, dict) else r[0] for r in applied_records} if applied_records else set()

        files = sorted([f for f in os.listdir(self.migrations_dir) if f.endswith(".json")])
        
        for file in files:
            if file not in applied_migrations:
                print(f"Qo'llanilmoqda: {file}...")
                with open(os.path.join(self.migrations_dir, file), "r", encoding="utf-8") as f:
                    data = json.load(f)
                
                for op in data.get("operations", []):
                    await db._manager(op, commit=True)
                
                await db.insert("postgresdb3_migrations", "name", [file])
                print(f"Muvaffaqiyatli qo'llanildi: {file}")

    def undo_migration(self, db):
        import asyncio
        is_async = asyncio.iscoroutinefunction(db._manager)
        if is_async:
            raise ValueError("Asinxron obyekt uchun 'await engine.async_undo_migration(db)' ishlating.")

        files = sorted([f for f in os.listdir(self.migrations_dir) if f.endswith(".json")])
        if not files:
            print("Orqaga qaytarish uchun migratsiyalar topilmadi.")
            return

        last_file = files[-1]
        print(f"Orqaga qaytarilmoqda: {last_file}...")

        with open(os.path.join(self.migrations_dir, last_file), "r", encoding="utf-8") as f:
            data = json.load(f)

        for op in reversed(data.get("reverse_operations", [])):
            db._manager(op, commit=True)

        db.delete("postgresdb3_migrations", "name", last_file)
        os.remove(os.path.join(self.migrations_dir, last_file))
        print(f"Muvaffaqiyatli bekor qilindi va o'chirildi: {last_file}")

    async def async_undo_migration(self, db):
        files = sorted([f for f in os.listdir(self.migrations_dir) if f.endswith(".json")])
        if not files:
            print("Orqaga qaytarish uchun migratsiyalar topilmadi.")
            return

        last_file = files[-1]
        print(f"Orqaga qaytarilmoqda: {last_file}...")

        with open(os.path.join(self.migrations_dir, last_file), "r", encoding="utf-8") as f:
            data = json.load(f)

        for op in reversed(data.get("reverse_operations", [])):
            await db._manager(op, commit=True)

        await db.delete("postgresdb3_migrations", "name", last_file)
        os.remove(os.path.join(self.migrations_dir, last_file))
        print(f"Muvaffaqiyatli bekor qilindi va o'chirildi: {last_file}")
