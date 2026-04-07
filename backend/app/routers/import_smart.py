"""
智能导入：抖音链接解析入库、截图 OCR 候选店名。
抖音页多为前端渲染，解析失败时请在前端手动改店名后重试。
OCR 依赖 OCR Space（免费注册 https://ocr.space/ocrapi ），配置 .env 中 OCR_SPACE_API_KEY。
"""
from __future__ import annotations

import io
import re
import unicodedata
from datetime import datetime
from html import unescape
from typing import List, Optional

import httpx
from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel, Field
from sqlmodel import Session, select

from ..auth_context import AuthCtxDep
from ..config import settings
from ..database import get_session
from ..models.restaurant import (
    Restaurant,
    PriceTierEnum,
    SourceEnum,
)
from ..routers.restaurants import _price_to_tier, _boards_join, _boards_tokens, _stmt_restaurants_for_ctx

router = APIRouter(prefix="/api/import", tags=["import"])

SessionDep = Annotated[Session, Depends(get_session)]


class DouyinUrlIn(BaseModel):
    url: str = Field(..., min_length=8, description="抖音分享页或视频链接")


class AddByNameIn(BaseModel):
    """OCR 选中店名后补全坐标并入库"""
    name: str = Field(..., min_length=1, max_length=120)
    source_url: str = ""
    boards: str = "my_pick"


def _clean_douyin_title(raw: str) -> str:
    if not raw:
        return ""
    s = unescape(raw).strip()
    for cut in (" - 抖音", " - 抖音短视频", "_抖音", " | 抖音", "抖音短视频"):
        if cut in s:
            s = s.split(cut)[0].strip()
    s = re.sub(r"^[@#]\S+\s*", "", s)
    return s[:120]


def _extract_from_html(html: str) -> tuple[str, str]:
    title = ""
    desc = ""
    m = re.search(r'<meta\s+property="og:title"\s+content="([^"]*)"', html, re.I)
    if m:
        title = _clean_douyin_title(m.group(1))
    m2 = re.search(r'<meta\s+property="og:description"\s+content="([^"]*)"', html, re.I)
    if m2:
        desc = unescape(m2.group(1)).strip()[:500]
    if not title:
        m3 = re.search(r'"desc"\s*:\s*"((?:[^"\\]|\\.)*)"', html)
        if m3:
            title = _clean_douyin_title(
                m3.group(1).encode("utf-8").decode("unicode_escape", errors="ignore")
            )
    if not title:
        m4 = re.search(r"<title>([^<]{2,200})</title>", html, re.I)
        if m4:
            title = _clean_douyin_title(m4.group(1))
    return title, desc


async def _amap_geocode(address: str) -> Optional[dict]:
    if not settings.amap_key:
        return None
    url = "https://restapi.amap.com/v3/geocode/geo"
    params = {"key": settings.amap_key, "address": address, "city": "成都"}
    async with httpx.AsyncClient() as client:
        r = await client.get(url, params=params, timeout=15.0)
        data = r.json()
    if data.get("status") != "1" or not data.get("geocodes"):
        return None
    geo = data["geocodes"][0]
    lng, lat = geo["location"].split(",")
    return {
        "formatted_address": geo.get("formatted_address", ""),
        "latitude": float(lat),
        "longitude": float(lng),
    }


async def _amap_first_poi(keyword: str) -> Optional[dict]:
    if not settings.amap_key:
        return None
    url = "https://restapi.amap.com/v3/place/text"
    params = {
        "key": settings.amap_key,
        "keywords": keyword[:80],
        "city": "成都",
        "types": "050000",
        "offset": 3,
        "page": 1,
        "extensions": "all",
    }
    async with httpx.AsyncClient() as client:
        r = await client.get(url, params=params, timeout=15.0)
        data = r.json()
    if data.get("status") != "1" or not data.get("pois"):
        return None
    p = data["pois"][0]
    loc = p.get("location") or ""
    parts = (loc.split(",") + ["", ""])[:2]
    lng, lat = parts[0], parts[1]
    if not lat or not lng:
        return None
    biz = p.get("biz_ext") or {}
    photos = p.get("photos") or []
    img = ""
    if photos and isinstance(photos[0], dict):
        img = (photos[0].get("url") or "").strip()
    return {
        "name": (p.get("name") or "").strip(),
        "address": (p.get("address") or "").strip(),
        "latitude": float(lat),
        "longitude": float(lng),
        "category": ((p.get("type") or "").split(";")[0] if p.get("type") else "") or "餐饮服务",
        "rating": float(biz["rating"]) if biz.get("rating") not in (None, "") else None,
        "avg_price": float(biz["cost"]) if biz.get("cost") not in (None, "") else None,
        "image_url": img,
        "tag": (p.get("tag") or "").strip(),
    }


@router.post("/douyin")
async def import_from_douyin(body: DouyinUrlIn, session: SessionDep, ctx: AuthCtxDep):
    u = body.url.strip()
    if "douyin.com" not in u and "iesdouyin.com" not in u:
        raise HTTPException(status_code=400, detail="请粘贴抖音链接（含 douyin.com）")

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        ),
        "Accept-Language": "zh-CN,zh;q=0.9",
    }
    try:
        async with httpx.AsyncClient(follow_redirects=True, timeout=25.0) as client:
            resp = await client.get(u, headers=headers)
            html = resp.text
    except httpx.HTTPError as e:
        raise HTTPException(status_code=502, detail=f"无法打开链接: {e!s}") from e

    title, desc = _extract_from_html(html)
    guess = title or ""
    if not guess and desc:
        # 取描述第一行作店名猜测
        guess = desc.split("\n")[0].split("。")[0].strip()[:80]

    if not guess:
        raise HTTPException(
            status_code=422,
            detail="未能从页面读出标题（抖音多为动态加载）。请改用「截图识别」或手动新增，店名可手填后再地理编码。",
        )

    poi = await _amap_first_poi(guess)
    geo = None
    if not poi:
        geo = await _amap_geocode(guess + " 成都")

    now = datetime.now()
    if poi:
        avg = poi.get("avg_price") or 45.0
        r = Restaurant(
            name=poi["name"] or guess,
            address=poi.get("address") or "",
            latitude=poi["latitude"],
            longitude=poi["longitude"],
            avg_price=avg,
            price_tier=_price_to_tier(avg),
            category=poi.get("category") or "餐饮服务",
            tags=f"抖音导入,{poi.get('tag') or ''}".strip(","),
            source=SourceEnum.douyin,
            source_url=u[:500],
            rating=poi.get("rating") or 4.2,
            image_url=(poi.get("image_url") or "").replace("http://", "https://", 1),
            boards=_boards_join({"my_pick"}),
            created_at=now,
            updated_at=now,
            couple_account_id=ctx.couple_account_id if ctx.auth_required else None,
        )
    elif geo:
        r = Restaurant(
            name=guess[:120],
            address=geo.get("formatted_address") or "",
            latitude=geo["latitude"],
            longitude=geo["longitude"],
            avg_price=45.0,
            price_tier=_price_to_tier(45.0),
            category="餐饮服务",
            tags="抖音导入,地理编码",
            source=SourceEnum.douyin,
            source_url=u[:500],
            rating=4.2,
            image_url="",
            boards=_boards_join({"my_pick"}),
            created_at=now,
            updated_at=now,
            couple_account_id=ctx.couple_account_id if ctx.auth_required else None,
        )
    else:
        raise HTTPException(
            status_code=422,
            detail=f"已解析标题「{guess}」，但高德未找到坐标。请用地图批量加或截图识别后选店名。",
        )

    dup_stmt = _stmt_restaurants_for_ctx(select(Restaurant).where(Restaurant.name == r.name), ctx)
    dup = session.exec(dup_stmt).first()
    if dup:
        bset = _boards_tokens(dup.boards)
        bset.add("my_pick")
        dup.boards = _boards_join(bset)
        if not dup.source_url and u:
            dup.source_url = u[:500]
        dup.updated_at = now
        session.add(dup)
        session.commit()
        session.refresh(dup)
        return {
            "code": 200,
            "message": "同名店铺已存在，已并入自己精选并补充来源链接",
            "restaurant_id": dup.id,
            "merged": True,
        }

    session.add(r)
    session.commit()
    session.refresh(r)
    return {
        "code": 200,
        "message": "已加入自己精选",
        "restaurant_id": r.id,
        "merged": False,
        "parsed_title": guess,
    }


@router.post("/ocr-candidates")
async def ocr_shop_candidates(file: UploadFile = File(...)):
    if not settings.ocr_space_api_key:
        raise HTTPException(
            status_code=503,
            detail="未配置 OCR_SPACE_API_KEY，请到 ocr.space 注册后在 backend/.env 填写",
        )
    content = await file.read()
    if len(content) > 4 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="图片请小于 4MB")

    async with httpx.AsyncClient(timeout=60.0) as client:
        r = await client.post(
            "https://api.ocr.space/parse/image",
            files={"file": ("shot.jpg", io.BytesIO(content), file.content_type or "image/jpeg")},
            data={
                "apikey": settings.ocr_space_api_key,
                "language": "chs",
                "isOverlayRequired": "false",
                "scale": "true",
            },
        )
    try:
        data = r.json()
    except Exception:
        raise HTTPException(status_code=502, detail="OCR 服务返回异常") from None

    if data.get("IsErroredOnProcessing"):
        msg = (data.get("ErrorMessage") or data.get("ParsedResults") or "OCR 失败")[:200]
        raise HTTPException(status_code=502, detail=str(msg))

    texts: List[str] = []
    for block in data.get("ParsedResults") or []:
        t = (block.get("ParsedText") or "").strip()
        if t:
            texts.append(t)

    raw = "\n".join(texts)
    candidates: List[str] = []
    seen = set()
    for line in re.split(r"[\r\n]+", raw):
        line = line.strip()
        line = "".join(ch for ch in line if not unicodedata.category(ch).startswith("C"))
        if len(line) < 2 or len(line) > 60:
            continue
        if re.fullmatch(r"[\d\s\-.￥¥元.,]+", line):
            continue
        if line in seen:
            continue
        seen.add(line)
        candidates.append(line)

    return {"code": 200, "candidates": candidates[:30], "raw_preview": raw[:300]}


@router.post("/add-by-name")
async def add_restaurant_by_name(body: AddByNameIn, session: SessionDep, ctx: AuthCtxDep):
    """根据店名高德检索 POI，加入自己精选（用于 OCR 选中后）。"""
    name = body.name.strip()
    if not name:
        raise HTTPException(status_code=400, detail="店名为空")

    poi = await _amap_first_poi(name)
    geo = None
    if not poi:
        geo = await _amap_geocode(name + " 成都")

    now = datetime.now()
    if poi:
        avg = poi.get("avg_price") or 45.0
        r = Restaurant(
            name=poi["name"] or name,
            address=poi.get("address") or "",
            latitude=poi["latitude"],
            longitude=poi["longitude"],
            avg_price=avg,
            price_tier=_price_to_tier(avg),
            category=poi.get("category") or "餐饮服务",
            tags="截图识别," + (poi.get("tag") or ""),
            source=SourceEnum.manual,
            source_url=(body.source_url or "")[:500],
            rating=poi.get("rating") or 4.2,
            image_url=(poi.get("image_url") or "").replace("http://", "https://", 1),
            boards=_boards_join(_boards_tokens(body.boards) or {"my_pick"}),
            created_at=now,
            updated_at=now,
            couple_account_id=ctx.couple_account_id if ctx.auth_required else None,
        )
    elif geo:
        r = Restaurant(
            name=name[:120],
            address=geo.get("formatted_address") or "",
            latitude=geo["latitude"],
            longitude=geo["longitude"],
            avg_price=45.0,
            price_tier=_price_to_tier(45.0),
            category="餐饮服务",
            tags="截图识别",
            source=SourceEnum.manual,
            source_url=(body.source_url or "")[:500],
            rating=4.2,
            image_url="",
            boards=_boards_join(_boards_tokens(body.boards) or {"my_pick"}),
            created_at=now,
            updated_at=now,
            couple_account_id=ctx.couple_account_id if ctx.auth_required else None,
        )
    else:
        raise HTTPException(status_code=422, detail="高德未找到该店，请换关键词或用手动新增")

    dup_stmt = _stmt_restaurants_for_ctx(select(Restaurant).where(Restaurant.name == r.name), ctx)
    dup = session.exec(dup_stmt).first()
    if dup:
        bset = _boards_tokens(dup.boards)
        bset.update(_boards_tokens(body.boards) or {"my_pick"})
        dup.boards = _boards_join(bset)
        dup.updated_at = now
        session.add(dup)
        session.commit()
        return {"code": 200, "message": "已合并榜单", "restaurant_id": dup.id, "merged": True}

    session.add(r)
    session.commit()
    session.refresh(r)
    return {"code": 200, "message": "已加入", "restaurant_id": r.id, "merged": False}
