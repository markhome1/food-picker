from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Annotated, Optional

import jwt
from fastapi import Depends, Header, HTTPException

from .config import is_auth_enabled, settings


@dataclass
class AuthContext:
    """auth_required 为 True 时必须已登录；couple_account_id 为隔离维度。"""

    auth_required: bool
    couple_account_id: Optional[int]
    user_id: Optional[int]
    email: Optional[str]


def _decode_token(token: str) -> dict:
    if not settings.jwt_secret.strip():
        raise HTTPException(status_code=503, detail="服务器未配置 JWT_SECRET")
    try:
        return jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=["HS256"],
            options={"require": ["exp", "sub", "cid"]},
        )
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="登录已过期，请重新登录") from None
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="登录无效，请重新登录") from None


def get_auth_context(
    authorization: Annotated[Optional[str], Header(alias="Authorization")] = None,
) -> AuthContext:
    if not is_auth_enabled():
        return AuthContext(
            auth_required=False,
            couple_account_id=None,
            user_id=None,
            email=None,
        )
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="请先登录")
    raw = authorization[7:].strip()
    if not raw:
        raise HTTPException(status_code=401, detail="请先登录")
    payload = _decode_token(raw)
    try:
        uid = int(payload["sub"])
        cid = int(payload["cid"])
    except (KeyError, TypeError, ValueError):
        raise HTTPException(status_code=401, detail="登录无效") from None
    email = payload.get("email")
    if isinstance(email, str):
        em = email
    else:
        em = None
    return AuthContext(
        auth_required=True,
        couple_account_id=cid,
        user_id=uid,
        email=em,
    )


def create_access_token(*, user_id: int, couple_account_id: int, email: str) -> str:
    if not settings.jwt_secret.strip():
        raise RuntimeError("JWT_SECRET is not set")
    now = datetime.now(timezone.utc)
    exp = now + timedelta(days=max(1, settings.jwt_exp_days))
    return jwt.encode(
        {
            "sub": str(user_id),
            "cid": couple_account_id,
            "email": email,
            "iat": now,
            "exp": exp,
        },
        settings.jwt_secret,
        algorithm="HS256",
    )


AuthCtxDep = Annotated[AuthContext, Depends(get_auth_context)]
