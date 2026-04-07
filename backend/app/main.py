from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import is_auth_enabled, settings
from .database import create_db_and_tables
from .routers import amap, auth, import_smart, records, restaurants


@asynccontextmanager
async def lifespan(app: FastAPI):
    if is_auth_enabled() and not (settings.jwt_secret or "").strip():
        raise RuntimeError(
            "已启用登录隔离（Postgres 或非 SQLite），请在环境变量中设置 JWT_SECRET（随机长字符串）。"
        )
    yield


app = FastAPI(
    title="今天吃啥 API",
    description="成都餐厅随机选择器",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(restaurants.router)
app.include_router(records.router)
app.include_router(amap.router)
app.include_router(import_smart.router)

# 在全部 router（及 model）加载后再建表，避免 TestClient / 部分入口下 lifespan 早于 metadata 完整
create_db_and_tables()


@app.get("/")
def root():
    return {"message": "今天吃啥 API 🍜", "docs": "/docs"}
