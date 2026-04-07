"""
网红打卡示例（抖音向）：写入 boards=viral、source=douyin，便于「发现美食」展示。
重复运行会跳过同名餐厅。

用法: 在 backend 目录下  python scripts/seed_viral_board.py
"""
from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from sqlmodel import Session, select  # noqa: E402

from app.database import create_db_and_tables, engine  # noqa: E402
from app.models.restaurant import (  # noqa: E402
    PriceTierEnum,
    Restaurant,
    SourceEnum,
)


# 成都相关网红向示例：图用可外链图，后续你可替换为抖音笔记截图链接
SAMPLES = [
    {
        "name": "（示例）巷巷老火锅·抖音爆款双人餐",
        "address": "成都市锦江区示例路88号",
        "latitude": 30.6586,
        "longitude": 104.0648,
        "avg_price": 78,
        "category": "火锅",
        "tags": "抖音博主推荐,网红打卡,排队王",
        "rating": 4.7,
        "image_url": "https://images.unsplash.com/photo-1563245372-f21724e3856d?w=900&q=80",
        "source_url": "https://www.douyin.com/",
    },
    {
        "name": "（示例）夜烧烤·博主深夜食堂",
        "address": "成都市武侯区示例街12号",
        "latitude": 30.625,
        "longitude": 104.043,
        "avg_price": 65,
        "category": "烧烤",
        "tags": "抖音,夜宵,本地生活",
        "rating": 4.6,
        "image_url": "https://images.unsplash.com/photo-1555939594-58d7cb561ad1?w=900&q=80",
        "source_url": "",
    },
    {
        "name": "（示例）奶油华夫饼·打卡出片",
        "address": "成都市成华区示例巷6号",
        "latitude": 30.67,
        "longitude": 104.12,
        "avg_price": 42,
        "category": "甜品",
        "tags": "网红甜品,出片,抖音同款",
        "rating": 4.5,
        "image_url": "https://images.unsplash.com/photo-1563805042-7684c019e1cb?w=900&q=80",
        "source_url": "",
    },
    {
        "name": "（示例）泰式大排档·博主联名款",
        "address": "成都市高新区示例大道168号",
        "latitude": 30.54,
        "longitude": 104.06,
        "avg_price": 88,
        "category": "东南亚菜",
        "tags": "抖音团购,网红店,泰餐",
        "rating": 4.8,
        "image_url": "https://images.unsplash.com/photo-1559314809-0d155014e29e?w=900&q=80",
        "source_url": "",
    },
]


def _tier(p: float) -> PriceTierEnum:
    if p <= 10:
        return PriceTierEnum.tier_0_10
    if p <= 20:
        return PriceTierEnum.tier_10_20
    if p <= 50:
        return PriceTierEnum.tier_20_50
    if p <= 100:
        return PriceTierEnum.tier_50_100
    return PriceTierEnum.tier_100_plus


def main() -> None:
    create_db_and_tables()
    now = datetime.now()
    inserted = 0
    with Session(engine) as session:
        existing = {r.name.strip() for r in session.exec(select(Restaurant)).all()}
        for row in SAMPLES:
            if row["name"] in existing:
                continue
            r = Restaurant(
                name=row["name"],
                address=row["address"],
                latitude=row["latitude"],
                longitude=row["longitude"],
                avg_price=row["avg_price"],
                price_tier=_tier(row["avg_price"]),
                category=row["category"],
                tags=row["tags"],
                source=SourceEnum.douyin,
                source_url=row.get("source_url") or "",
                rating=row["rating"],
                image_url=row["image_url"],
                boards="viral",
                created_at=now,
                updated_at=now,
            )
            session.add(r)
            existing.add(row["name"])
            inserted += 1
        session.commit()
    print(f"完成：新增网红示例 {inserted} 家。")


if __name__ == "__main__":
    main()
