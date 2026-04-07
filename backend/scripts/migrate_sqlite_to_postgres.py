"""
将本地 SQLite 数据导入到 Postgres。

用法：
    python scripts/migrate_sqlite_to_postgres.py

要求：
    1. backend/.env.local 或环境变量中已设置 DATABASE_URL（Postgres）
    2. SQLite 源库默认读取 backend/data/food_picker.db
"""

from pathlib import Path
import sys

BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from sqlmodel import Session, SQLModel, create_engine, select

from app.config import settings
from app.models.record import DiningRecord
from app.models.restaurant import Restaurant


def _source_sqlite_url() -> str:
    sqlite_path = Path(settings.sqlite_seed_path).resolve()
    return f"sqlite:///{sqlite_path.as_posix()}"


def _target_pg_url() -> str:
    url = settings.database_url
    if url.startswith("postgres://"):
        return "postgresql+psycopg://" + url[len("postgres://"):]
    if url.startswith("postgresql://"):
        return "postgresql+psycopg://" + url[len("postgresql://"):]
    return url


def main() -> None:
    if not settings.database_url.startswith(("postgres://", "postgresql://")):
        raise SystemExit("DATABASE_URL 不是 Postgres，停止迁移。")

    source_engine = create_engine(
        _source_sqlite_url(),
        connect_args={"check_same_thread": False},
    )
    target_engine = create_engine(_target_pg_url())

    SQLModel.metadata.create_all(target_engine)

    with Session(source_engine) as source, Session(target_engine) as target:
        restaurants = source.exec(select(Restaurant)).all()
        records = source.exec(select(DiningRecord)).all()

        existing_restaurants = {
            row.name: row.id for row in target.exec(select(Restaurant)).all()
        }
        id_map: dict[int, int] = {}

        created_restaurants = 0
        for row in restaurants:
            if row.id is None:
                continue
            if row.name in existing_restaurants:
                id_map[row.id] = existing_restaurants[row.name]
                continue

            payload = row.model_dump(exclude={"id", "records"})
            new_row = Restaurant(**payload)
            target.add(new_row)
            target.commit()
            target.refresh(new_row)
            id_map[row.id] = new_row.id
            created_restaurants += 1

        existing_record_keys = {
            (r.restaurant_id, r.dining_date, r.comment, r.actual_cost)
            for r in target.exec(select(DiningRecord)).all()
        }
        created_records = 0
        for row in records:
            if row.restaurant_id not in id_map:
                continue
            dedupe_key = (
                id_map[row.restaurant_id],
                row.dining_date,
                row.comment,
                row.actual_cost,
            )
            if dedupe_key in existing_record_keys:
                continue

            payload = row.model_dump(exclude={"id", "restaurant"})
            payload["restaurant_id"] = id_map[row.restaurant_id]
            target.add(DiningRecord(**payload))
            created_records += 1

        target.commit()

    print(
        f"迁移完成：新增餐厅 {created_restaurants} 家，新增就餐记录 {created_records} 条。"
    )


if __name__ == "__main__":
    main()
