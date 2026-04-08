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


def _migrate_couple_member_email_constraints() -> None:
    """去掉 couple_member.email 全局唯一，改为 (email, couple_account_id) 联合唯一。"""
    insp = inspect(engine)
    if "couple_member" not in insp.get_table_names():
        return

    def _has_uq_email_space() -> bool:
        for uq in insp.get_unique_constraints("couple_member"):
            cols = set(uq.get("column_names") or [])
            if cols == {"email", "couple_account_id"}:
                return True
        for ix in insp.get_indexes("couple_member"):
            if ix.get("unique") and set(ix.get("column_names") or []) == {"email", "couple_account_id"}:
                return True
        return False

    if _has_uq_email_space():
        return

    if engine.dialect.name == "sqlite":
        with engine.begin() as conn:
            conn.execute(
                text(
                    """
                    CREATE TABLE couple_member_new (
                        id INTEGER NOT NULL PRIMARY KEY,
                        couple_account_id INTEGER NOT NULL,
                        email VARCHAR(255) NOT NULL,
                        password_hash VARCHAR(255) NOT NULL,
                        display_name VARCHAR(120) NOT NULL DEFAULT '',
                        created_at DATETIME,
                        FOREIGN KEY(couple_account_id) REFERENCES coupleaccount(id),
                        CONSTRAINT uq_couple_member_email_space UNIQUE (email, couple_account_id)
                    )
                    """
                )
            )
            conn.execute(
                text(
                    """
                    INSERT INTO couple_member_new
                    (id, couple_account_id, email, password_hash, display_name, created_at)
                    SELECT id, couple_account_id, email, password_hash, display_name, created_at
                    FROM couple_member
                    """
                )
            )
            conn.execute(text("DROP TABLE couple_member"))
            conn.execute(text("ALTER TABLE couple_member_new RENAME TO couple_member"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS ix_couple_member_email ON couple_member (email)"))
            conn.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS ix_couple_member_couple_account_id "
                    "ON couple_member (couple_account_id)"
                )
            )
        return

    with engine.begin() as conn:
        for name in (
            "couple_member_email_key",
            "couplemember_email_key",
        ):
            conn.execute(text(f'ALTER TABLE couple_member DROP CONSTRAINT IF EXISTS "{name}"'))
        conn.execute(text("DROP INDEX IF EXISTS ix_couple_member_email"))
        conn.execute(
            text(
                "CREATE UNIQUE INDEX IF NOT EXISTS uq_couple_member_email_space "
                "ON couple_member (email, couple_account_id)"
            )
        )
        conn.execute(
            text(
                "CREATE INDEX IF NOT EXISTS ix_couple_member_email ON couple_member (email)"
            )
        )


def _backfill_space_foundation() -> None:
    """为历史空间补创建记录，避免老用户重复创建同类空间。"""
    from sqlmodel import Session, select

    from .models.couple import CoupleAccount, CoupleMember
    from .models.space_foundation import SpaceFoundation

    insp = inspect(engine)
    if "space_foundation" not in insp.get_table_names():
        return
    if "couple_member" not in insp.get_table_names():
        return

    with Session(engine) as session:
        accounts = session.exec(select(CoupleAccount)).all()
        for acc in accounts:
            members = session.exec(
                select(CoupleMember)
                .where(CoupleMember.couple_account_id == acc.id)
                .order_by(CoupleMember.created_at)
            ).all()
            if not members:
                continue
            founder = members[0]
            kind = "pair" if (acc.max_members or 2) == 2 else "group"
            exists = session.exec(
                select(SpaceFoundation).where(
                    SpaceFoundation.email == founder.email,
                    SpaceFoundation.foundation_kind == kind,
                )
            ).first()
            if exists:
                continue
            session.add(
                SpaceFoundation(
                    email=founder.email,
                    foundation_kind=kind,
                    couple_account_id=acc.id,
                )
            )
        session.commit()


def create_db_and_tables():
    # 确保情侣空间等表类已注册（某些入口可能先于 routers 加载 database）
    from .models import couple as _couple_models  # noqa: F401
    from .models import email_otp as _email_otp_models  # noqa: F401
    from .models import otp_send_log as _otp_send_log_models  # noqa: F401
    from .models import space_foundation as _space_foundation_models  # noqa: F401

    SQLModel.metadata.create_all(engine)
    _migrate_sqlite_columns()
    _migrate_couple_columns()
    _migrate_coupleaccount_max_members()
    _migrate_couple_member_email_constraints()
    _backfill_space_foundation()


def get_session():
    with Session(engine) as session:
        yield session
