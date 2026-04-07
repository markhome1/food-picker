from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .database import create_db_and_tables
from .routers import restaurants, records, amap, import_smart


@asynccontextmanager
async def lifespan(app: FastAPI):
    create_db_and_tables()
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

app.include_router(restaurants.router)
app.include_router(records.router)
app.include_router(amap.router)
app.include_router(import_smart.router)


@app.get("/")
def root():
    return {"message": "今天吃啥 API 🍜", "docs": "/docs"}
