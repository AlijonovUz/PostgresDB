import os
import importlib
import inspect

class MigrationEngine:
    def __init__(self, models_module_path):
        self.models_module_path = models_module_path
        self.migrations_dir = os.path.join(os.getcwd(), "migrations")
        if not os.path.exists(self.migrations_dir):
            os.makedirs(self.migrations_dir)

    def makemigrations(self):
        print("Model o'zgarishlari tekshirilmoqda...")
                                             
        pass

    def migrate(self, db):
        print("Migratsiyalar bazaga yozilmoqda...")
                                               
        pass
