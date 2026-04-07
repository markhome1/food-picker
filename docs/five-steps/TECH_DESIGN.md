# 技术设计 - 今天吃啥

## 架构
```
Uni-app (Vue3 + Vite, H5模式)
        ↓ HTTP REST
FastAPI (Python 3.9+)
        ↓
SQLite (data/food_picker.db)
        ↓
高德 Web 服务 API (地理编码 + POI)
```

## 技术栈
- **前端**: Uni-app + Vue3 Composition API + Pinia
- **后端**: FastAPI + SQLModel + Uvicorn
- **数据库**: SQLite (本地) → PostgreSQL (后续)
- **外部API**: 高德开放平台 Web 服务

## 数据模型
| 表 | 核心字段 |
|---|---------|
| `restaurant` | id, name, address, lat, lng, avg_price, price_tier, category, tags, source, rating |
| `diningrecord` | id, restaurant_id(FK), dining_date, departure_address, actual_cost, rating, comment |
| `category` | id, name, icon |

## API 端点
| 方法 | 路径 | 说明 |
|------|------|------|
| GET/POST | `/api/restaurants` | 列表/新增 |
| GET/PATCH/DELETE | `/api/restaurants/{id}` | 详情/编辑/删除 |
| GET | `/api/restaurants/random` | 随机推荐 |
| POST | `/api/restaurants/import` | CSV导入 |
| GET/POST | `/api/records` | 就餐记录 |
| GET | `/api/records/stats` | 统计 |
| GET | `/api/amap/geocode` | 地理编码 |
| GET | `/api/amap/poi` | POI搜索 |

## 关键决策
- SQLModel 作为 ORM（与 FastAPI 原生集成）
- 使用 Optional[] 而非 X|None（兼容 Python 3.9）
- Haversine 公式计算距离（后端）
- 前端通过 uni.getLocation() 获取定位
