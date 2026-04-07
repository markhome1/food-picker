import os
from pathlib import Path
from typing import Dict, Tuple

from pydantic_settings import BaseSettings


BACKEND_DIR = Path(__file__).resolve().parents[1]
DEFAULT_SQLITE_FILE = (BACKEND_DIR / "data" / "food_picker.db").resolve()


def _default_database_url() -> str:
    from_env = os.getenv("DATABASE_URL")
    if from_env:
        return from_env
    if os.getenv("VERCEL"):
        return "sqlite:////tmp/food_picker.db"
    return f"sqlite:///{DEFAULT_SQLITE_FILE.as_posix()}"


class Settings(BaseSettings):
    app_name: str = "今天吃啥"
    database_url: str = _default_database_url()
    sqlite_seed_path: str = str(DEFAULT_SQLITE_FILE)
    # 登录 JWT；生产 Postgres 时配合 is_auth_enabled() 使用
    jwt_secret: str = ""
    jwt_exp_days: int = 30
    # 注册/加入邮箱验证码（Resend：https://resend.com ）
    resend_api_key: str = ""
    resend_from: str = ""
    email_otp_ttl_minutes: int = 15
    amap_key: str = ""
    # https://ocr.space/ocrapi 免费注册，用于截图识别店名
    ocr_space_api_key: str = ""

    # 价格档位配置
    price_tiers: Dict[str, Tuple[int, int]] = {
        "0-10": (0, 10),
        "10-20": (10, 20),
        "20-50": (20, 50),
        "50-100": (50, 100),
        "100+": (100, 99999),
    }

    model_config = {
        "env_file": (BACKEND_DIR / ".env", BACKEND_DIR / ".env.local"),
        "env_file_encoding": "utf-8",
    }


settings = Settings()


def is_auth_enabled() -> bool:
    """是否要求登录并按情侣空间隔离数据。AUTH_ENABLED 显式优先，否则非 SQLite 默认开启。"""
    v = os.getenv("AUTH_ENABLED")
    if v is not None:
        return v.strip().lower() in ("1", "true", "yes")
    return not settings.database_url.startswith("sqlite")
