import sys
import argparse
import asyncio
from .migrations.engine import MigrationEngine
from .core import PostgresDB, AsyncPostgresDB


def execute_from_command_line(db, argv=None):
    """
    Kutubxonadan foydalanuvchilar o'z loyihalarida terminal buyruqlarini
    ishga tushirishi uchun maxsus CLI funksiyasi (xuddi Django manage.py kabi).
    """
    if argv is None:
        argv = sys.argv
        
    parser = argparse.ArgumentParser(description="PostgresDB CLI - Ma'lumotlar bazasini boshqarish")
    subparsers = parser.add_subparsers(dest="command", help="Mavjud buyruqlar")
    
                    
    make_parser = subparsers.add_parser("makemigrations", help="Modellardagi o'zgarishlar asosida yangi migratsiya fayllarini yaratadi")
    make_parser.add_argument("name", nargs="?", default="auto", help="Migratsiya nomi (masalan: initial_setup)")
    
             
    subparsers.add_parser("migrate", help="Mavjud migratsiyalarni ma'lumotlar bazasiga qo'llaydi")
    subparsers.add_parser("undo", help="Oxirgi migratsiyani bekor qiladi va bazadan o'chiradi")
    
    args = parser.parse_args(argv[1:])
    
    if args.command == "makemigrations":
        engine = MigrationEngine()
        print(f"'{args.name}' nomli migratsiya yaratilmoqda...")
        engine.makemigrations(args.name)
        
    elif args.command == "migrate":
        engine = MigrationEngine()
        if isinstance(db, PostgresDB):
            engine.migrate(db)
        elif isinstance(db, AsyncPostgresDB):
                                                                                   
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.ensure_future(engine.async_migrate(db))
            else:
                loop.run_until_complete(engine.async_migrate(db))
        else:
            print("Xato: Noma'lum DB obyekti (PostgresDB yoki AsyncPostgresDB kerak).")
            
    elif args.command == "undo":
        engine = MigrationEngine()
        if isinstance(db, PostgresDB):
            engine.undo_migration(db)
        elif isinstance(db, AsyncPostgresDB):
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.ensure_future(engine.async_undo_migration(db))
            else:
                loop.run_until_complete(engine.async_undo_migration(db))
        else:
            print("Xato: Noma'lum DB obyekti (PostgresDB yoki AsyncPostgresDB kerak).")
            
    else:
        parser.print_help()
