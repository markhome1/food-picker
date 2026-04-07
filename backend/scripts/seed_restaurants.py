"""
从高德 POI 拉取成都餐饮（含必吃榜相关关键词），写入本地 SQLite。
需配置 backend/.env 中的 AMAP_KEY（Web 服务）。

用法（在 backend 目录下）:
    python scripts/seed_restaurants.py
"""
from __future__ import annotations

import hashlib
import sys
from datetime import datetime
from pathlib import Path

import httpx

# 包路径
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from sqlmodel import Session, select  # noqa: E402

from app.config import settings  # noqa: E402
from app.database import create_db_and_tables, engine  # noqa: E402
from app.models.restaurant import (  # noqa: E402
    PriceTierEnum,
    Restaurant,
    SourceEnum,
)

# 无高德配图时的备用图（可公开访问的餐饮场景图）
FALLBACK_IMAGES = [
    "https://images.unsplash.com/photo-1517248135467-4c7edcad34c4?w=900&q=80",
    "https://images.unsplash.com/photo-1414235077428-338989a2e8c0?w=900&q=80",
    "https://images.unsplash.com/photo-1555396273-367ea4eb4db5?w=900&q=80",
    "https://images.unsplash.com/photo-1552566626-52f8b828add9?w=900&q=80",
    "https://images.unsplash.com/photo-1544148103-07737bf555ca?w=900&q=80",
    "https://images.unsplash.com/photo-1559339352-11d035aa65de?w=900&q=80",
    "https://images.unsplash.com/photo-1504674900247-0877df9cc836?w=900&q=80",
    "https://images.unsplash.com/photo-1551218808-94e220e084d2?w=900&q=80",
]

# 成都信息工程大学（航空港校区）附近 — 高德 GCJ-02，lng,lat
CUIT_CENTER = "103.9986,30.5865"

# 覆盖必吃榜、热门商圈、品类
SEARCH_KEYWORDS = [
    "必吃榜",
    "成都必吃",
    "黑珍珠餐厅",
    "春熙路火锅",
    "太古里美食",
    "宽窄巷子餐厅",
    "建设路美食",
    "川菜馆",
    "串串香",
    "烧烤",
    "米其林 成都",
    "咖啡 成都",
]

# 成信大周边补充关键词（place/around）
CUIT_AROUND_KEYWORDS = ["", "火锅", "中餐", "小吃", "奶茶", "烧烤", "咖啡"]


def _price_to_tier(price: float) -> PriceTierEnum:
    if price <= 10:
        return PriceTierEnum.tier_0_10
    if price <= 20:
        return PriceTierEnum.tier_10_20
    if price <= 50:
        return PriceTierEnum.tier_20_50
    if price <= 100:
        return PriceTierEnum.tier_50_100
    return PriceTierEnum.tier_100_plus


def _num(v):
    if v is None or v == "":
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _fallback_image(name: str) -> str:
    h = int(hashlib.md5(name.encode("utf-8"), usedforsecurity=False).hexdigest(), 16)
    return FALLBACK_IMAGES[h % len(FALLBACK_IMAGES)]


def fetch_pois(keyword: str, page: int, client: httpx.Client) -> list[dict]:
    url = "https://restapi.amap.com/v3/place/text"
    params = {
        "key": settings.amap_key,
        "keywords": keyword,
        "city": "成都",
        "types": "050000",
        "offset": 25,
        "page": page,
        "extensions": "all",
    }
    r = client.get(url, params=params, timeout=20.0)
    data = r.json()
    if data.get("status") != "1":
        return []
    out = []
    for p in data.get("pois", []):
        loc = p.get("location") or ""
        parts = (loc.split(",") + ["", ""])[:2]
        lng, lat = parts[0], parts[1]
        photos = p.get("photos") or []
        image_url = ""
        if photos and isinstance(photos[0], dict):
            image_url = (photos[0].get("url") or "").strip()
        biz = p.get("biz_ext") or {}
        typ = p.get("type") or ""
        category = typ.split(";")[0] if typ else ""
        out.append(
            {
                "name": (p.get("name") or "").strip(),
                "address": (p.get("address") or "").strip(),
                "latitude": float(lat) if lat else None,
                "longitude": float(lng) if lng else None,
                "category": category,
                "rating": _num(biz.get("rating")),
                "avg_price": _num(biz.get("cost")),
                "image_url": image_url,
                "poi_tag": (p.get("tag") or "").strip(),
            }
        )
    return out


def fetch_pois_around(keyword: str, page: int, client: httpx.Client) -> list[dict]:
    """以成信大航空港校区为中心，周边餐饮 POI（高德 place/around）。"""
    url = "https://restapi.amap.com/v3/place/around"
    params = {
        "key": settings.amap_key,
        "location": CUIT_CENTER,
        "radius": "4500",
        "types": "050000",
        "offset": 25,
        "page": page,
        "extensions": "all",
    }
    if keyword:
        params["keywords"] = keyword
    r = client.get(url, params=params, timeout=20.0)
    data = r.json()
    if data.get("status") != "1":
        return []
    out = []
    for p in data.get("pois", []):
        loc = p.get("location") or ""
        parts = (loc.split(",") + ["", ""])[:2]
        lng, lat = parts[0], parts[1]
        photos = p.get("photos") or []
        image_url = ""
        if photos and isinstance(photos[0], dict):
            image_url = (photos[0].get("url") or "").strip()
        biz = p.get("biz_ext") or {}
        typ = p.get("type") or ""
        category = typ.split(";")[0] if typ else ""
        out.append(
            {
                "name": (p.get("name") or "").strip(),
                "address": (p.get("address") or "").strip(),
                "latitude": float(lat) if lat else None,
                "longitude": float(lng) if lng else None,
                "category": category,
                "rating": _num(biz.get("rating")),
                "avg_price": _num(biz.get("cost")),
                "image_url": image_url,
                "poi_tag": (p.get("tag") or "").strip(),
            }
        )
    return out


def build_tags(keyword: str, poi_tag: str) -> str:
    tags = ["高德POI"]
    if "成信大" in keyword or "信息工程大学" in keyword or keyword == "成信大周边":
        tags.insert(0, "成信大周边")
    if "必吃" in keyword or "必吃" in poi_tag:
        tags.insert(0, "必吃榜")
    if "黑珍珠" in keyword or "黑珍珠" in poi_tag:
        tags.append("黑珍珠")
    if "米其林" in keyword or "米其林" in poi_tag:
        tags.append("米其林")
    return ",".join(dict.fromkeys(tags))


def main() -> None:
    if not settings.amap_key:
        print("错误: 请在 backend/.env 设置 AMAP_KEY 后重试。")
        sys.exit(1)

    create_db_and_tables()

    with Session(engine) as session:
        existing = {r.name.strip() for r in session.exec(select(Restaurant)).all()}

    collected: dict[str, dict] = {}

    with httpx.Client() as client:
        # 优先：成信大航空港 4.5km 内餐饮
        cuit_kw = "成信大周边"
        for kw in CUIT_AROUND_KEYWORDS:
            for page in (1, 2, 3):
                rows = fetch_pois_around(kw, page, client)
                for row in rows:
                    name = row["name"]
                    if not name or name in collected:
                        continue
                    if not row["latitude"] or not row["longitude"]:
                        continue
                    row["_seed_keyword"] = cuit_kw
                    collected[name] = row
                if len(collected) >= 100:
                    break
            if len(collected) >= 100:
                break

        for kw in SEARCH_KEYWORDS:
            for page in (1, 2):
                rows = fetch_pois(kw, page, client)
                for row in rows:
                    name = row["name"]
                    if not name or name in collected:
                        continue
                    if not row["latitude"] or not row["longitude"]:
                        continue
                    row["_seed_keyword"] = kw
                    collected[name] = row
                if len(collected) >= 140:
                    break
            if len(collected) >= 140:
                break

    if not collected:
        print("未从高德获取到 POI，请检查 Key 权限与城市配额。")
        sys.exit(1)

    inserted = 0
    skipped = 0
    now = datetime.now()

    with Session(engine) as session:
        for name, row in collected.items():
            if name in existing:
                skipped += 1
                continue
            avg = row["avg_price"] or 45.0
            tier = _price_to_tier(avg)
            img = row["image_url"] or _fallback_image(name)
            if img.startswith("http://"):
                img = "https://" + img[7:]
            kw = row["_seed_keyword"]
            r = Restaurant(
                name=name,
                address=row["address"] or f"成都市（{name}）",
                latitude=row["latitude"],
                longitude=row["longitude"],
                avg_price=avg,
                price_tier=tier,
                category=row["category"] or "餐饮服务",
                tags=build_tags(kw, row["poi_tag"]),
                source=SourceEnum.amap,
                source_url="",
                rating=row["rating"] if row["rating"] else 4.2,
                image_url=img,
                created_at=now,
                updated_at=now,
            )
            session.add(r)
            inserted += 1
        session.commit()

    print(f"完成: 新增 {inserted} 家，跳过已存在 {skipped} 家，去重后候选 {len(collected)} 家。")


if __name__ == "__main__":
    main()
