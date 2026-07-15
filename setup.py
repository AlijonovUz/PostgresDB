import os
import sys
import subprocess
from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as f:
    long_description = f.read()

force_source = os.environ.get("POSTGRESDB_SOURCE_PSYCOPG2", "0") == "1"

if force_source:
    psycopg_dependency = "psycopg2>=2.9"
else:
    has_pq_dev = False
    try:
        res = subprocess.run(["pg_config", "--includedir"], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True)
        if res.returncode == 0:
            includedir = res.stdout.strip()
            if os.path.exists(os.path.join(includedir, "pg_config.h")):
                has_pq_dev = True
    except Exception:
        pass

    is_building_dist = any(arg in sys.argv for arg in ["bdist_wheel", "dist_info", "egg_info", "sdist"])
    
    if is_building_dist:
        psycopg_dependency = "psycopg2-binary>=2.9"
    elif has_pq_dev:
        psycopg_dependency = "psycopg2>=2.9"
    else:
        psycopg_dependency = "psycopg2-binary>=2.9"

setup(
    name="postgresdb3",
    version="2.0.4",
    packages=find_packages(),
    install_requires=[
        psycopg_dependency,
        "asyncpg>=0.31.0"
    ],
    author="Abdulbosit Alijonov",
    description="High-Performance Sync and Async PostgreSQL ORM for Python",
    long_description=long_description,
    long_description_content_type="text/markdown",
    project_urls={
        "Source Code": "https://github.com/AlijonovUz/PostgresDB",
    },
    classifiers=[
        "Programming Language :: Python :: 3.9",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.9',
)