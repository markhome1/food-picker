import math
import re
from typing import Any, Dict, List, Optional

import httpx
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import Response

from ..config import settings

router = APIRouter(prefix="/api/amap", tags=["amap"])


def _haversine_m(lng1: float, lat1: float, lng2: float, lat2: float) -> float:
    """两点球面距离（米）。"""
    r = 6371000.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dl = math.radians(lng2 - lng1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(max(0.0, 1.0 - a)))
    return r * c


def _is_junk_poi_name(name: Optional[str]) -> bool:
    """过滤高德偶发的无效/占位名称（如仅「CQ」）。"""
    if name is None:
        return True
    s = str(name).strip()
    if len(s) < 2:
        return True
    if re.fullmatch(r"\d+", s):
        return True
    # 两位全大写拉丁字母，多为脏数据
    if re.fullmatch(r"[A-Z]{2}", s):
        return True
    return False


def _drop_junk_pois(pois: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """剔除无效店名，保持高德返回顺序（周边检索仍以距离为主）。"""
    return [p for p in (pois or []) if not _is_junk_poi_name((p or {}).get("name"))]


def _num(v):
    if v is None or v == "":
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _poi_from_regeo_item(p: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """逆地理周边 POI 单条 → 与关键词/周边接口统一结构。"""
    if not p:
        return None
    loc = p.get("location", "")
    parts = (loc.split(",") + ["", ""])[:2]
    lng_s, lat_s = parts[0], parts[1]
    try:
        lng_f = float(lng_s) if lng_s else None
        lat_f = float(lat_s) if lat_s else None
    except (TypeError, ValueError):
        lng_f, lat_f = None, None
    type_str = p.get("type") or ""
    if "餐饮" not in type_str and "美食" not in type_str:
        return None
    photos = p.get("photos") or []
    image_url = ""
    if photos and isinstance(photos[0], dict):
        image_url = photos[0].get("url") or ""
    nm = p.get("name")
    if _is_junk_poi_name(nm):
        return None
    return {
        "name": nm,
        "address": p.get("address") or "",
        "latitude": lat_f,
        "longitude": lng_f,
        "category": type_str.split(";")[0] if type_str else "餐饮服务",
        "rating": None,
        "avg_price": None,
        "image_url": image_url,
        "tag": type_str,
    }


def _pois_from_amap_list(raw_pois: list) -> list:
    out = []
    for p in raw_pois or []:
        loc = p.get("location", "")
        lng, lat = (loc.split(",") + ["", ""])[:2]
        photos = p.get("photos") or []
        image_url = ""
        if photos and isinstance(photos[0], dict):
            image_url = photos[0].get("url") or ""
        biz = p.get("biz_ext") or {}
        out.append(
            {
                "name": p.get("name"),
                "address": p.get("address") or "",
                "latitude": float(lat) if lat else None,
                "longitude": float(lng) if lng else None,
                "category": (p.get("type") or "").split(";")[0] if p.get("type") else "",
                "rating": _num(biz.get("rating")),
                "avg_price": _num(biz.get("cost")),
                "image_url": image_url,
                "tag": p.get("tag") or "",
            }
        )
    return out


@router.get("/geocode")
async def geocode(address: str):
    """地理编码：地址 -> 经纬度"""
    if not settings.amap_key:
        raise HTTPException(status_code=500, detail="未配置高德 API Key")
    url = "https://restapi.amap.com/v3/geocode/geo"
    params = {"key": settings.amap_key, "address": address, "city": "成都"}
    async with httpx.AsyncClient() as client:
        resp = await client.get(url, params=params)
        data = resp.json()
    if data.get("status") != "1" or not data.get("geocodes"):
        info = data.get("info") or ""
        hint = ""
        if info == "USERKEY_PLAT_NOMATCH":
            hint = "（高德控制台需为该 Key 勾选「Web服务」平台，与 JS API 可同时启用）"
        elif info == "INVALID_USER_KEY":
            hint = "（Key 无效或未开通对应服务）"
        msg = f"地理编码失败: {info}{hint}" if info else "未找到地址"
        return {"code": 404, "message": msg, "data": None}
    geo = data["geocodes"][0]
    lng, lat = geo["location"].split(",")
    return {
        "code": 200,
        "data": {
            "formatted_address": geo["formatted_address"],
            "latitude": float(lat),
            "longitude": float(lng),
        },
    }


@router.get("/staticmap")
async def static_map(latitude: float, longitude: float):
    """代理高德静态地图，使用服务端 Key，供前端 <image> 展示。"""
    if not settings.amap_key:
        raise HTTPException(status_code=500, detail="未配置高德 API Key")
    amap_url = (
        "https://restapi.amap.com/v3/staticmap"
        f"?location={longitude},{latitude}&zoom=15&size=750*400"
        f"&markers=mid,,A:{longitude},{latitude}&key={settings.amap_key}"
    )
    async with httpx.AsyncClient() as client:
        resp = await client.get(amap_url, timeout=15.0)
    if resp.status_code != 200:
        raise HTTPException(status_code=502, detail="静态地图请求失败")
    return Response(content=resp.content, media_type="image/png")


@router.get("/poi")
async def search_poi(keyword: str, page: int = 1):
    """POI 搜索：按关键词搜索成都餐厅"""
    if not settings.amap_key:
        raise HTTPException(status_code=500, detail="未配置高德 API Key")
    url = "https://restapi.amap.com/v3/place/text"
    params = {
        "key": settings.amap_key,
        "keywords": keyword,
        "city": "成都",
        "types": "050000",  # 餐饮服务大类
        "offset": 20,
        "page": page,
        "extensions": "all",
    }
    async with httpx.AsyncClient() as client:
        resp = await client.get(url, params=params)
        data = resp.json()
    if data.get("status") != "1":
        return {"code": 500, "message": "高德 API 调用失败", "data": None}

    return {"code": 200, "data": _drop_junk_pois(_pois_from_amap_list(data.get("pois", [])))}


@router.get("/regeo-pois")
async def regeo_pois(
    longitude: float,
    latitude: float,
    radius: int = Query(default=120, ge=40, le=300),
):
    """点击地图某点：逆地理 + 周边 POI，筛餐饮，按距离排序，用于点选图面店铺。"""
    if not settings.amap_key:
        raise HTTPException(status_code=500, detail="未配置高德 API Key")
    url = "https://restapi.amap.com/v3/geocode/regeo"
    params = {
        "key": settings.amap_key,
        "location": f"{longitude},{latitude}",
        "extensions": "all",
        "radius": str(radius),
    }
    async with httpx.AsyncClient() as client:
        resp = await client.get(url, params=params, timeout=20.0)
        data = resp.json()
    if data.get("status") != "1":
        info = data.get("info") or ""
        return {"code": 500, "message": f"逆地理失败: {info}", "data": None}
    regeo = data.get("regeocode") or {}
    raw_pois = regeo.get("pois") or []
    out: List[Dict[str, Any]] = []
    for p in raw_pois:
        item = _poi_from_regeo_item(p)
        if item and item.get("name") and item.get("latitude") is not None:
            lg = item.get("longitude")
            lt = item.get("latitude")
            if lg is not None and lt is not None:
                item["distance_from_click_m"] = round(
                    _haversine_m(longitude, latitude, float(lg), float(lt)), 1
                )
            out.append(item)
    # 按点击点球面距离排序（高德返回的 distance 可能与视觉点击不一致）
    out.sort(key=lambda x: x.get("distance_from_click_m", 999999.0))
    out = _drop_junk_pois(out)
    return {"code": 200, "data": out[:15]}


@router.get("/enrich-poi")
async def enrich_poi(
    name: str,
    longitude: float,
    latitude: float,
    radius: int = Query(default=400, ge=150, le=800),
):
    """按店名+坐标周边检索，补全首图/评分（逆地理条目常无图）。"""
    if not settings.amap_key:
        raise HTTPException(status_code=500, detail="未配置高德 API Key")
    nm = (name or "").strip()
    if not nm:
        return {"code": 400, "message": "缺少店名", "data": None}
    url = "https://restapi.amap.com/v3/place/around"
    params = {
        "key": settings.amap_key,
        "location": f"{longitude},{latitude}",
        "keywords": nm[:60],
        "radius": str(radius),
        "types": "050000",
        "offset": 20,
        "page": 1,
        "extensions": "all",
    }
    async with httpx.AsyncClient() as client:
        resp = await client.get(url, params=params, timeout=20.0)
        data = resp.json()
    if data.get("status") != "1":
        info = data.get("info") or ""
        return {"code": 500, "message": f"检索失败: {info}", "data": None}
    pois = _drop_junk_pois(_pois_from_amap_list(data.get("pois", [])))
    if not pois:
        return {"code": 404, "message": "未找到匹配店铺", "data": None}

    def rank(p: Dict[str, Any]) -> tuple:
        plng, plat = p.get("longitude"), p.get("latitude")
        if plng is None or plat is None:
            return (0, 999999.0)
        d = _haversine_m(longitude, latitude, float(plng), float(plat))
        pn = p.get("name") or ""
        hit = 0
        if nm == pn:
            hit = 4
        elif nm in pn or pn in nm:
            hit = 3
        elif len(nm) >= 4 and (nm[:4] in pn or (len(pn) >= 4 and pn[:4] in nm)):
            hit = 2
        elif len(nm) >= 2 and nm[:2] in pn:
            hit = 1
        return (-hit, d)

    best = min(pois, key=rank)
    return {"code": 200, "data": best}


@router.get("/poi-around")
async def search_poi_around(
    longitude: float,
    latitude: float,
    radius: int = Query(default=3000, ge=200, le=5000),
    page: int = Query(default=1, ge=1, le=5),
):
    """以某点为中心检索周边餐饮（place/around），用于地图选点后批量加店。"""
    if not settings.amap_key:
        raise HTTPException(status_code=500, detail="未配置高德 API Key")
    url = "https://restapi.amap.com/v3/place/around"
    params = {
        "key": settings.amap_key,
        "location": f"{longitude},{latitude}",
        "radius": str(radius),
        "types": "050000",
        "offset": 25,
        "page": page,
        "extensions": "all",
    }
    async with httpx.AsyncClient() as client:
        resp = await client.get(url, params=params, timeout=20.0)
        data = resp.json()
    if data.get("status") != "1":
        info = data.get("info") or ""
        return {"code": 500, "message": f"高德周边检索失败: {info}", "data": None}
    raw = _pois_from_amap_list(data.get("pois", []))
    return {"code": 200, "data": _drop_junk_pois(raw)}
