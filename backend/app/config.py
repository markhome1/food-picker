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
