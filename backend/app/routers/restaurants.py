import random
from datetime import datetime
from typing import Annotated, Optional, List, Set

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
from pydantic import BaseModel
from sqlmodel import Session, select, func, col
import csv
import io

from ..auth_context import AuthCtxDep, AuthContext
from ..database import get_session
from ..models.restaurant import (
    Restaurant,
    RestaurantCreate,
    RestaurantUpdate,
    RestaurantPublic,
    PriceTierEnum,
    SourceEnum,
)
from ..models.record import DiningRecord
from ..utils.geo import haversine_distance
from ..config import settings

router = APIRouter(prefix="/api/restaurants", tags=["restaurants"])

SessionDep = Annotated[Session, Depends(get_session)]


def _stmt_restaurants_for_ctx(stmt, ctx: AuthContext):
    if ctx.auth_required and ctx.couple_account_id is not None:
        return stmt.where(Restaurant.couple_account_id == ctx.couple_account_id)
    return stmt


def _assert_restaurant_couple(r: Restaurant, ctx: AuthContext) -> None:
    if not ctx.auth_required:
        return
    if r.couple_account_id != ctx.couple_account_id:
        raise HTTPException(status_code=404, detail="餐厅不存在")


def _boards_tokens(s: Optional[str]) -> Set[str]:
    if not s:
        return set()
    return {x.strip() for x in s.split(";") if x.strip()}


def _boards_join(tokens: Set[str]) -> str:
    return ";".join(sorted(tokens))


class RestaurantBatchItem(BaseModel):
    name: str
    address: str = ""
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    avg_price: Optional[float] = None
    category: str = ""
    tags: str = ""
    image_url: str = ""
    rating: Optional[float] = None
    source: SourceEnum = SourceEnum.amap
    boards: str = "my_pick"
    source_url: str = ""


class RestaurantBatchIn(BaseModel):
    items: List[RestaurantBatchItem]


@router.post("", response_model=RestaurantPublic)
def create_restaurant(restaurant: RestaurantCreate, session: SessionDep, ctx: AuthCtxDep):
    db_obj = Restaurant.model_validate(restaurant)
    if ctx.auth_required:
        db_obj.couple_account_id = ctx.couple_account_id
    session.add(db_obj)
    session.commit()
    session.refresh(db_obj)
    return _to_public(db_obj, session, ctx=ctx)


@router.get("", response_model=List[RestaurantPublic])
def list_restaurants(
    session: SessionDep,
    ctx: AuthCtxDep,
    price_tier: Optional[PriceTierEnum] = None,
    category: Optional[str] = None,
    keyword: Optional[str] = None,
    board: Optional[str] = Query(
        default=None,
        description="my_pick=自己精选 viral=网红打卡 high_score=评分≥4.5",
    ),
    user_lat: Optional[float] = None,
    user_lng: Optional[float] = None,
    max_distance_km: Optional[float] = None,
    sort_by: str = Query(default="name", pattern="^(name|avg_price|rating|distance)$"),
    offset: int = 0,
    limit: Annotated[int, Query(le=200)] = 50,
):
    stmt = _stmt_restaurants_for_ctx(select(Restaurant), ctx)

    if price_tier:
        stmt = stmt.where(Restaurant.price_tier == price_tier)
    if category:
        stmt = stmt.where(col(Restaurant.category).contains(category))
    if keyword:
        stmt = stmt.where(
            col(Restaurant.name).contains(keyword)
            | col(Restaurant.tags).contains(keyword)
        )

    results = session.exec(stmt).all()
    visit_counts = _load_visit_counts(
        session, [r.id for r in results if r.id is not None], ctx
    )

    if board == "high_score":
        results = [r for r in results if (r.rating or 0) >= 4.5]
    elif board in ("my_pick", "viral"):
        results = [r for r in results if board in _boards_tokens(r.boards)]

    # 计算距离 & 过滤（与 /random 一致：选了距离且带了用户坐标时，只保留有坐标且在范围内的店）
    public_list: List[RestaurantPublic] = []
    for r in results:
        pub = _to_public(
            r,
            session,
            user_lat,
            user_lng,
            visit_count=visit_counts.get(r.id, 0),
            ctx=ctx,
        )
        if (
            max_distance_km is not None
            and user_lat is not None
            and user_lng is not None
        ):
            if pub.distance_km is None:
                continue
            if pub.distance_km > max_distance_km:
                continue
        public_list.append(pub)

    # 排序
    if sort_by == "distance" and user_lat is not None:
        public_list.sort(key=lambda x: x.distance_km if x.distance_km is not None else 99999)
    elif sort_by == "avg_price":
        public_list.sort(key=lambda x: x.avg_price if x.avg_price is not None else 99999)
    elif sort_by == "rating":
        public_list.sort(key=lambda x: x.rating if x.rating is not None else 0, reverse=True)
    else:
        public_list.sort(key=lambda x: x.name)

    return public_list[offset: offset + limit]


@router.get("/random", response_model=RestaurantPublic)
def random_restaurant(
    session: SessionDep,
    ctx: AuthCtxDep,
    price_tier: Optional[PriceTierEnum] = None,
    category: Optional[str] = None,
    user_lat: Optional[float] = None,
    user_lng: Optional[float] = None,
    max_distance_km: Optional[float] = None,
):
    """随机推荐一家餐厅"""
    stmt = _stmt_restaurants_for_ctx(select(Restaurant), ctx)
    if price_tier:
        stmt = stmt.where(Restaurant.price_tier == price_tier)
    if category:
        stmt = stmt.where(col(Restaurant.category).contains(category))

    results = session.exec(stmt).all()

    # 距离过滤
    if max_distance_km and user_lat is not None and user_lng is not None:
        results = [
            r for r in results
            if r.latitude and r.longitude
            and haversine_distance(user_lat, user_lng, r.latitude, r.longitude) <= max_distance_km
        ]

    if not results:
        raise HTTPException(status_code=404, detail="没有符合条件的餐厅")

    chosen = random.choice(results)
    return _to_public(chosen, session, user_lat, user_lng, ctx=ctx)


@router.get("/{restaurant_id}", response_model=RestaurantPublic)
def get_restaurant(restaurant_id: int, session: SessionDep, ctx: AuthCtxDep):
    r = session.get(Restaurant, restaurant_id)
    if not r:
        raise HTTPException(status_code=404, detail="餐厅不存在")
    _assert_restaurant_couple(r, ctx)
    return _to_public(r, session, ctx=ctx)


@router.patch("/{restaurant_id}", response_model=RestaurantPublic)
def update_restaurant(restaurant_id: int, data: RestaurantUpdate, session: SessionDep, ctx: AuthCtxDep):
    r = session.get(Restaurant, restaurant_id)
    if not r:
        raise HTTPException(status_code=404, detail="餐厅不存在")
    _assert_restaurant_couple(r, ctx)
    update_data = data.model_dump(exclude_unset=True)
    r.sqlmodel_update(update_data)
    session.add(r)
    session.commit()
    session.refresh(r)
    return _to_public(r, session, ctx=ctx)


@router.delete("/{restaurant_id}")
def delete_restaurant(restaurant_id: int, session: SessionDep, ctx: AuthCtxDep):
    r = session.get(Restaurant, restaurant_id)
    if not r:
        raise HTTPException(status_code=404, detail="餐厅不存在")
    _assert_restaurant_couple(r, ctx)
    session.delete(r)
    session.commit()
    return {"code": 200, "message": "已删除"}


@router.post("/batch")
def batch_create_restaurants(body: RestaurantBatchIn, session: SessionDep, ctx: AuthCtxDep):
    """批量新增（地图 POI 多选等）。同名已存在则跳过。"""
    if len(body.items) > 40:
        raise HTTPException(status_code=400, detail="单次最多添加 40 家")
    if not body.items:
        return {"code": 200, "created": 0, "skipped": 0, "message": "无数据"}
    name_q = _stmt_restaurants_for_ctx(select(Restaurant), ctx)
    existing_names = {r.name.strip() for r in session.exec(name_q).all()}
    now = datetime.now()
    created = 0
    skipped = 0
    for it in body.items:
        nm = it.name.strip()
        if not nm or nm in existing_names:
            skipped += 1
            continue
        avg = it.avg_price if it.avg_price is not None else 45.0
        tier = _price_to_tier(avg)
        bset = _boards_tokens(it.boards)
        if not bset:
            bset = {"my_pick"}
        r = Restaurant(
            name=nm,
            address=(it.address or "").strip(),
            latitude=it.latitude,
            longitude=it.longitude,
            avg_price=avg,
            price_tier=tier,
            category=(it.category or "餐饮服务").strip() or "餐饮服务",
            tags=(it.tags or "").strip(),
            source=it.source,
            source_url=(it.source_url or "").strip(),
            rating=it.rating if it.rating is not None else 4.2,
            image_url=(it.image_url or "").strip(),
            boards=_boards_join(bset),
            created_at=now,
            updated_at=now,
            couple_account_id=ctx.couple_account_id if ctx.auth_required else None,
        )
        session.add(r)
        existing_names.add(nm)
        created += 1
    session.commit()
    return {"code": 200, "created": created, "skipped": skipped}


@router.post("/import")
async def import_csv(session: SessionDep, ctx: AuthCtxDep, file: UploadFile = File(...)):
    """CSV 批量导入餐厅。CSV 列: name,address,avg_price,category,tags,source"""
    content = await file.read()
    text = content.decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(text))
    count = 0
    for row in reader:
        avg = float(row.get("avg_price", 0) or 0)
        tier = _price_to_tier(avg)
        r = Restaurant(
            name=row.get("name", ""),
            address=row.get("address", ""),
            avg_price=avg,
            price_tier=tier,
            category=row.get("category", ""),
            tags=row.get("tags", ""),
            source=row.get("source", "manual"),
            boards=(row.get("boards") or "").strip(),
            couple_account_id=ctx.couple_account_id if ctx.auth_required else None,
        )
        session.add(r)
        count += 1
    session.commit()
    return {"code": 200, "message": f"成功导入 {count} 家餐厅"}


# --- helpers ---

def _price_to_tier(price: float) -> PriceTierEnum:
    if price <= 10:
        return PriceTierEnum.tier_0_10
    elif price <= 20:
        return PriceTierEnum.tier_10_20
    elif price <= 50:
        return PriceTierEnum.tier_20_50
    elif price <= 100:
        return PriceTierEnum.tier_50_100
    else:
        return PriceTierEnum.tier_100_plus


def _load_visit_counts(
    session: Session, restaurant_ids: List[int], ctx: AuthContext
) -> dict[int, int]:
    if not restaurant_ids:
        return {}
    stmt = (
        select(DiningRecord.restaurant_id, func.count(DiningRecord.id))
        .where(DiningRecord.restaurant_id.in_(restaurant_ids))
    )
    if ctx.auth_required and ctx.couple_account_id is not None:
        stmt = stmt.where(DiningRecord.couple_account_id == ctx.couple_account_id)
    stmt = stmt.group_by(DiningRecord.restaurant_id)
    return {restaurant_id: count for restaurant_id, count in session.exec(stmt).all()}


def _to_public(
    r: Restaurant,
    session: Session,
    user_lat: Optional[float] = None,
    user_lng: Optional[float] = None,
    visit_count: Optional[int] = None,
    ctx: Optional[AuthContext] = None,
) -> RestaurantPublic:
    if visit_count is None:
        vc_stmt = select(func.count(DiningRecord.id)).where(DiningRecord.restaurant_id == r.id)
        if ctx and ctx.auth_required and ctx.couple_account_id is not None:
            vc_stmt = vc_stmt.where(DiningRecord.couple_account_id == ctx.couple_account_id)
        visit_count = session.exec(vc_stmt).one()

    distance = None
    if user_lat and user_lng and r.latitude and r.longitude:
        distance = round(haversine_distance(user_lat, user_lng, r.latitude, r.longitude), 2)

    return RestaurantPublic(
        **r.model_dump(),
        visit_count=visit_count,
        distance_km=distance,
    )
