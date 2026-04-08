#!/usr/bin/env python3
"""
本地严格校验 Resend 配置（不打印任何密钥）：
1. RESEND_FROM 使用已验证域名 fpick.asia（非 onboarding@resend.dev）
2. RESEND_API_KEY 存在
3. 调用 Resend API 列出域名，确认 fpick.asia 在账号下

用法（在 backend 目录下）:
  python scripts/verify_resend_config.py

若本地未配置密钥，请复制 backend/.env.example 到 .env.local 并填写 RESEND_* 后再运行。
"""
from __future__ import annotations

import sys
from pathlib import Path

import httpx

BACKEND = Path(__file__).resolve().parents[1]
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from app.config import settings  # noqa: E402


def main() -> int:
    errs: list[str] = []
    rf = (settings.resend_from or "").strip()
    if not rf:
        errs.append("RESEND_FROM is empty; set in .env or .env.local e.g. noreply@fpick.asia")
    elif "fpick.asia" not in rf.lower():
        errs.append("RESEND_FROM should use verified domain fpick.asia")
    if rf.lower().strip() == "onboarding@resend.dev":
        errs.append("RESEND_FROM is still onboarding@resend.dev; use @fpick.asia for production")

    key = (settings.resend_api_key or "").strip()
    if not key:
        errs.append("RESEND_API_KEY is empty; add to .env.local (never commit)")

    if errs:
        print("verify_resend_config: FAIL")
        for e in errs:
            print(f"  - {e}")
        return 1

    print("verify_resend_config: OK — from-address and API key present")

    try:
        r = httpx.get(
            "https://api.resend.com/domains",
            headers={"Authorization": f"Bearer {key}"},
            timeout=20.0,
        )
    except httpx.RequestError as e:
        print(f"verify_resend_config: FAIL — Resend API unreachable: {e}")
        return 2

    if r.status_code != 200:
        print(f"verify_resend_config: FAIL — Resend HTTP {r.status_code}")
        print((r.text or "")[:400])
        return 2

    data = r.json()
    items = data.get("data") if isinstance(data, dict) else None
    if not isinstance(items, list):
        items = []
    names = [str(d.get("name", "")).lower() for d in items if isinstance(d, dict)]
    if "fpick.asia" not in names:
        print("verify_resend_config: WARN — fpick.asia not in domain list:", names or "(empty)")
        print("  Check API key project matches Resend dashboard.")
        return 3

    print("verify_resend_config: Resend API OK — fpick.asia in domain list")
    print("verify_resend_config: ALL CHECKS PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
