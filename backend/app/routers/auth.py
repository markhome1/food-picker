import re
import secrets
from typing import Annotated, Optional

import bcrypt
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlmodel import Session, select

from ..auth_context import AuthCtxDep, create_access_token
from ..config import is_auth_enabled, settings
from ..database import get_session
from ..models.couple import CoupleAccount, CoupleMember

router = APIRouter(prefix="/api/auth", tags=["auth"])

SessionDep = Annotated[Session, Depends(get_session)]

_MAX_MEMBERS = 2
_EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")


def _norm_join_code(code: str) -> str:
    return code.strip().upper().replace(" ", "")


def _hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def _verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
    except Exception:
        return False


def _new_join_code() -> str:
    return f"{secrets.token_hex(3).upper()}-{secrets.token_hex(3).upper()}"


class RegisterCoupleIn(BaseModel):
    email: str = Field(..., min_length=5, max_length=255)
    password: str = Field(..., min_length=6, max_length=128)
    display_name: str = Field(default="", max_length=120)


class JoinCoupleIn(BaseModel):
    join_code: str = Field(..., min_length=4, max_length=32)
    email: str = Field(..., min_length=5, max_length=255)
    password: str = Field(..., min_length=6, max_length=128)
    display_name: str = Field(default="", max_length=120)


class LoginIn(BaseModel):
    email: str = Field(..., min_length=3, max_length=255)
    password: str = Field(..., min_length=1, max_length=128)


def _member_count(session: Session, couple_id: int) -> int:
    rows = session.exec(
        select(CoupleMember).where(CoupleMember.couple_account_id == couple_id)
    ).all()
    return len(rows)


@router.get("/status")
def auth_status():
    return {
        "auth_required": is_auth_enabled(),
        "code": 200,
    }


@router.get("/me")
def auth_me(session: SessionDep, ctx: AuthCtxDep):
    if not ctx.auth_required:
        return {
            "code": 200,
            "auth_required": False,
            "user": None,
        }
    u = session.get(CoupleMember, ctx.user_id)
    if not u or u.couple_account_id != ctx.couple_account_id:
        raise HTTPException(status_code=401, detail="登录无效")
    acc = session.get(CoupleAccount, u.couple_account_id)
    n = _member_count(session, u.couple_account_id)
    return {
        "code": 200,
        "auth_required": True,
        "user": {
            "id": u.id,
            "email": u.email,
            "display_name": u.display_name,
            "couple_account_id": u.couple_account_id,
        },
        "join_code": acc.join_code if acc else None,
        "member_count": n,
        "member_cap": _MAX_MEMBERS,
    }


@router.post("/register-couple")
def register_couple(body: RegisterCoupleIn, session: SessionDep):
    if not is_auth_enabled():
        raise HTTPException(status_code=400, detail="当前环境未开启登录（SQLite 本地模式）")
    if not settings.jwt_secret.strip():
        raise HTTPException(status_code=503, detail="服务器未配置 JWT_SECRET")
    email = body.email.strip().lower()
    if not _EMAIL_RE.match(email):
        raise HTTPException(status_code=400, detail="邮箱格式不正确")
    exists = session.exec(select(CoupleMember).where(CoupleMember.email == email)).first()
    if exists:
        raise HTTPException(status_code=400, detail="该邮箱已注册")

    for _ in range(8):
        code = _new_join_code()
        taken = session.exec(select(CoupleAccount).where(CoupleAccount.join_code == code)).first()
        if not taken:
            break
    else:
        raise HTTPException(status_code=500, detail="无法生成邀请码，请重试")

    acc = CoupleAccount(join_code=code)
    session.add(acc)
    session.commit()
    session.refresh(acc)

    user = CoupleMember(
        couple_account_id=acc.id,
        email=email,
        password_hash=_hash_password(body.password),
        display_name=(body.display_name or "").strip()[:120],
    )
    session.add(user)
    session.commit()
    session.refresh(user)

    token = create_access_token(
        user_id=user.id,
        couple_account_id=acc.id,
        email=user.email,
    )
    return {
        "code": 200,
        "access_token": token,
        "token_type": "bearer",
        "join_code": acc.join_code,
        "couple_account_id": acc.id,
        "user": {"id": user.id, "email": user.email, "display_name": user.display_name},
    }


@router.post("/join-couple")
def join_couple(body: JoinCoupleIn, session: SessionDep):
    if not is_auth_enabled():
        raise HTTPException(status_code=400, detail="当前环境未开启登录")
    if not settings.jwt_secret.strip():
        raise HTTPException(status_code=503, detail="服务器未配置 JWT_SECRET")
    code = _norm_join_code(body.join_code)
    acc = session.exec(select(CoupleAccount).where(CoupleAccount.join_code == code)).first()
    if not acc:
        raise HTTPException(status_code=400, detail="邀请码无效")
    if _member_count(session, acc.id) >= _MAX_MEMBERS:
        raise HTTPException(status_code=400, detail="该情侣空间已满员（仅支持两人）")

    email = body.email.strip().lower()
    if not _EMAIL_RE.match(email):
        raise HTTPException(status_code=400, detail="邮箱格式不正确")
    exists = session.exec(select(CoupleMember).where(CoupleMember.email == email)).first()
    if exists:
        raise HTTPException(status_code=400, detail="该邮箱已注册")

    user = CoupleMember(
        couple_account_id=acc.id,
        email=email,
        password_hash=_hash_password(body.password),
        display_name=(body.display_name or "").strip()[:120],
    )
    session.add(user)
    session.commit()
    session.refresh(user)

    token = create_access_token(
        user_id=user.id,
        couple_account_id=acc.id,
        email=user.email,
    )
    return {
        "code": 200,
        "access_token": token,
        "token_type": "bearer",
        "couple_account_id": acc.id,
        "user": {"id": user.id, "email": user.email, "display_name": user.display_name},
    }


@router.post("/login")
def login(body: LoginIn, session: SessionDep):
    if not is_auth_enabled():
        raise HTTPException(status_code=400, detail="当前环境未开启登录")
    if not settings.jwt_secret.strip():
        raise HTTPException(status_code=503, detail="服务器未配置 JWT_SECRET")
    email = body.email.strip().lower()
    user = session.exec(select(CoupleMember).where(CoupleMember.email == email)).first()
    if not user or not _verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=400, detail="邮箱或密码错误")
    token = create_access_token(
        user_id=user.id,
        couple_account_id=user.couple_account_id,
        email=user.email,
    )
    return {
        "code": 200,
        "access_token": token,
        "token_type": "bearer",
        "couple_account_id": user.couple_account_id,
        "user": {"id": user.id, "email": user.email, "display_name": user.display_name},
    }
