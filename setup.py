from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as f:
    long_description = f.read()

setup(
    name="postgresdb3",
    version="0.2.3",
    packages=find_packages(),
    install_requires=[
        "psycopg2>=2.9",
        "asyncpg>=0.31.0"
    ],
    author="Abdulbosit Alijonov",
    description="Python uchun oddiy PostgreSQL wrapper",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/AlijonovUz/PostgresDB",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.7',
)