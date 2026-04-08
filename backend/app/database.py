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


def _migrate_coupleaccount_max_members():
    """为 coupleaccount 补 max_members（旧库默认 2，与原先「仅两人」行为一致）。"""
    insp = inspect(engine)
    if "coupleaccount" not in insp.get_table_names():
        return
    cols = {c["name"] for c in insp.get_columns("coupleaccount")}
    if "max_members" in cols:
        return
    with engine.begin() as conn:
        if engine.dialect.name == "sqlite":
            conn.execute(
                text("ALTER TABLE coupleaccount ADD COLUMN max_members INTEGER NOT NULL DEFAULT 2")
            )
        else:
            conn.execute(
                text(
                    "ALTER TABLE coupleaccount ADD COLUMN IF NOT EXISTS "
                    "max_members INTEGER NOT NULL DEFAULT 2"
                )
            )


def _migrate_couple_columns():
    """为旧库补 couple_account_id（SQLite / Postgres）。"""
    insp = inspect(engine)
    tables = set(insp.get_table_names())
    with engine.begin() as conn:
        if "restaurant" in tables:
            cols = {c["name"] for c in insp.get_columns("restaurant")}
            if "couple_account_id" not in cols:
                if engine.dialect.name == "sqlite":
                    conn.execute(text("ALTER TABLE restaurant ADD COLUMN couple_account_id INTEGER"))
                else:
                    conn.execute(
                        text(
                            "ALTER TABLE restaurant ADD COLUMN IF NOT EXISTS "
                            "couple_account_id INTEGER REFERENCES coupleaccount(id)"
                        )
                    )
        if "diningrecord" in tables:
            cols2 = {c["name"] for c in insp.get_columns("diningrecord")}
            if "couple_account_id" not in cols2:
                if engine.dialect.name == "sqlite":
                    conn.execute(text("ALTER TABLE diningrecord ADD COLUMN couple_account_id INTEGER"))
                else:
                    conn.execute(
                        text(
                            "ALTER TABLE diningrecord ADD COLUMN IF NOT EXISTS "
                            "couple_account_id INTEGER REFERENCES coupleaccount(id)"
                        )
                    )


def create_db_and_tables():
    # 确保情侣空间等表类已注册（某些入口可能先于 routers 加载 database）
    from .models import couple as _couple_models  # noqa: F401
    from .models import email_otp as _email_otp_models  # noqa: F401
    from .models import otp_send_log as _otp_send_log_models  # noqa: F401

    SQLModel.metadata.create_all(engine)
    _migrate_sqlite_columns()
    _migrate_couple_columns()
    _migrate_coupleaccount_max_members()


def get_session():
    with Session(engine) as session:
        yield session
