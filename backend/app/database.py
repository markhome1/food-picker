import shutil
from pathlib import Path
from typing import Optional

from sqlalchemy import inspect, text
from sqlalchemy.pool import NullPool
from sqlmodel import SQLModel, Session, create_engine

from .config import settings


def is_sqlite_url(database_url: str) -> bool:
    return database_url.startswith("sqlite:///")


def normalize_database_url(database_url: str) -> str:
    if database_url.startswith("postgres://"):
        return "postgresql+psycopg://" + database_url[len("postgres://"):]
    if database_url.startswith("postgresql://"):
        return "postgresql+psycopg://" + database_url[len("postgresql://"):]
    return database_url


def _sqlite_file_path(database_url: str) -> Optional[Path]:
    prefix = "sqlite:///"
    if not database_url.startswith(prefix):
        return None
    return Path(database_url[len(prefix):])


def _prepare_sqlite_file() -> None:
    db_file = _sqlite_file_path(settings.database_url)
    if db_file is None:
        return

    db_file.parent.mkdir(parents=True, exist_ok=True)

    if db_file.exists():
        return

    seed_file = Path(settings.sqlite_seed_path)
    if seed_file.exists() and seed_file.resolve() != db_file.resolve():
        shutil.copy2(seed_file, db_file)


_raw_database_url = settings.database_url
_normalized_database_url = normalize_database_url(_raw_database_url)
_prepare_sqlite_file()

engine_kwargs = {}
if is_sqlite_url(_raw_database_url):
    engine_kwargs["connect_args"] = {"check_same_thread": False}
else:
    # Serverless functions should not keep long-lived DB pools per instance.
    engine_kwargs["poolclass"] = NullPool
    engine_kwargs["pool_pre_ping"] = True

engine = create_engine(_normalized_database_url, **engine_kwargs)


def _migrate_sqlite_columns():
    """SQLite 无自动迁移：为旧库补列。"""
    if not is_sqlite_url(_raw_database_url):
        return
    insp = inspect(engine)
    if "restaurant" not in insp.get_table_names():
        return
    cols = {c["name"] for c in insp.get_columns("restaurant")}
    with engine.begin() as conn:
        if "boards" not in cols:
            conn.execute(text("ALTER TABLE restaurant ADD COLUMN boards VARCHAR(500) DEFAULT ''"))
        migrations = [
            ("dianping_rating", "REAL"),
            ("dianping_url", "VARCHAR(800) DEFAULT ''"),
            ("dianping_snippet", "VARCHAR(800) DEFAULT ''"),
            ("authority_label", "VARCHAR(120) DEFAULT ''"),
            ("authority_rating", "REAL"),
            ("authority_url", "VARCHAR(800) DEFAULT ''"),
        ]
        for col_name, col_type in migrations:
            if col_name not in cols:
                conn.execute(text(f"ALTER TABLE restaurant ADD COLUMN {col_name} {col_type}"))


def create_db_and_tables():
    SQLModel.metadata.create_all(engine)
    _migrate_sqlite_columns()


def get_session():
    with Session(engine) as session:
        yield session
