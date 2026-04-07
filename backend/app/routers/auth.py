import re
import secrets
from datetime import datetime, timedelta
from typing import Annotated, Literal

import bcrypt
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import desc, func
from sqlmodel import Session, select

from ..auth_context import AuthCtxDep, create_access_token
from ..config import is_auth_enabled, settings
from ..database import get_session
from ..mail_delivery import send_otp_email
from ..models.couple import CoupleAccount, CoupleMember
from ..models.email_otp import EmailOtp
from ..models.otp_send_log import OtpSendLog

router = APIRouter(prefix="/api/auth", tags=["auth"])

SessionDep = Annotated[Session, Depends(get_session)]

_MAX_MEMBERS = 2
_EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
_CODE_RE = re.compile(r"^\d{6}$")
_OTP_HOUR_LIMIT = 5
_OTP_RESEND_SECONDS = 60

OtpPurpose = Literal["register_couple", "join_couple"]


def _norm_join_code(code: str) -> str:
    return code.strip().upper().replace(" ", "")


def _hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def _hash_otp_code(code: str) -> str:
    return bcrypt.hashpw(code.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def _verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
    except Exception:
        return False


def _new_join_code() -> str:
    return f"{secrets.token_hex(3).upper()}-{secrets.token_hex(3).upper()}"


def _gen_six_digit() -> str:
    return str(secrets.randbelow(900_000) + 100_000)


def _email_otp_status() -> dict:
    """告知前端验证码投递方式，便于提示用户查收位置。"""
    if settings.resend_api_key.strip():
        return {"channel": "resend", "ok": True}
    from ..database import is_sqlite_url

    if is_sqlite_url(settings.database_url):
        return {"channel": "dev_log", "ok": True}
    return {"channel": "none", "ok": False}


class SendEmailCodeIn(BaseModel):
    email: str = Field(..., min_length=5, max_length=255)
    purpose: OtpPurpose


class RegisterCoupleIn(BaseModel):
    email: str = Field(..., min_length=5, max_length=255)
    password: str = Field(..., min_length=6, max_length=128)
    display_name: str = Field(default="", max_length=120)
    verification_code: str = Field(..., min_length=6, max_length=6, pattern=r"^\d{6}$")


class JoinCoupleIn(BaseModel):
    join_code: str = Field(..., min_length=4, max_length=32)
    email: str = Field(..., min_length=5, max_length=255)
    password: str = Field(..., min_length=6, max_length=128)
    display_name: str = Field(default="", max_length=120)
    verification_code: str = Field(..., min_length=6, max_length=6, pattern=r"^\d{6}$")


class LoginIn(BaseModel):
    email: str = Field(..., min_length=3, max_length=255)
    password: str = Field(..., min_length=1, max_length=128)


def _member_count(session: Session, couple_id: int) -> int:
    rows = session.exec(
        select(CoupleMember).where(CoupleMember.couple_account_id == couple_id)
    ).all()
    return len(rows)


def _verify_and_clear_otp(session: Session, email: str, purpose: str, code: str) -> None:
    code = code.strip()
    if not _CODE_RE.fullmatch(code):
        raise HTTPException(status_code=400, detail="验证码须为 6 位数字")
    row = session.exec(
        select(EmailOtp)
        .where(EmailOtp.email == email, EmailOtp.purpose == purpose)
        .order_by(desc(EmailOtp.created_at))
    ).first()
    if not row or row.expires_at < datetime.now():
        raise HTTPException(status_code=400, detail="验证码错误或已过期，请重新获取")
    try:
        ok = bcrypt.checkpw(code.encode("utf-8"), row.code_hash.encode("utf-8"))
    except Exception:
        ok = False
    if not ok:
        raise HTTPException(status_code=400, detail="验证码错误")
    for old in session.exec(
        select(EmailOtp).where(EmailOtp.email == email, EmailOtp.purpose == purpose)
    ).all():
        session.delete(old)


def _rate_check_otp_send(session: Session, email: str) -> None:
    """按邮箱限流（依赖 otp_send_log，与是否删除 EmailOtp 无关）。"""
    now = datetime.now()
    hour_ago = now - timedelta(hours=1)
    cnt = session.exec(
        select(func.count(OtpSendLog.id)).where(
            OtpSendLog.email == email,
            OtpSendLog.created_at >= hour_ago,
        )
    ).one()
    if cnt >= _OTP_HOUR_LIMIT:
        raise HTTPException(
            status_code=429,
            detail="该邮箱获取验证码次数过多，请约 1 小时后再试",
        )
    last = session.exec(
        select(OtpSendLog)
        .where(OtpSendLog.email == email)
        .order_by(desc(OtpSendLog.created_at))
    ).first()
    if last is not None and (now - last.created_at).total_seconds() < _OTP_RESEND_SECONDS:
        raise HTTPException(
            status_code=429,
            detail=f"请 {_OTP_RESEND_SECONDS} 秒后再获取验证码",
        )


@router.get("/status")
def auth_status():
    return {
        "auth_required": is_auth_enabled(),
        "email_otp": _email_otp_status(),
        "code": 200,
    }


@router.post("/send-email-code")
def send_email_code(body: SendEmailCodeIn, session: SessionDep):
    if not is_auth_enabled():
        raise HTTPException(status_code=400, detail="当前环境未开启登录")
    email = body.email.strip().lower()
    if not _EMAIL_RE.match(email):
        raise HTTPException(status_code=400, detail="邮箱格式不正确")
    exists = session.exec(select(CoupleMember).where(CoupleMember.email == email)).first()
    if exists:
        raise HTTPException(status_code=400, detail="该邮箱已注册")

    _rate_check_otp_send(session, email)

    for old in session.exec(
        select(EmailOtp).where(EmailOtp.email == email, EmailOtp.purpose == body.purpose)
    ).all():
        session.delete(old)

    plain = _gen_six_digit()
    ttl = max(5, min(60, settings.email_otp_ttl_minutes))
    expires = datetime.now() + timedelta(minutes=ttl)
    row = EmailOtp(
        email=email,
        purpose=body.purpose,
        code_hash=_hash_otp_code(plain),
        expires_at=expires,
    )
    session.add(row)
    session.add(OtpSendLog(email=email))
    session.commit()
    session.refresh(row)
    otp_id = row.id

    try:
        send_otp_email(email, plain)
    except RuntimeError as e:
        dead = session.get(EmailOtp, otp_id)
        if dead:
            session.delete(dead)
            session.commit()
        raise HTTPException(status_code=503, detail=str(e)) from None
    except Exception:
        dead = session.get(EmailOtp, otp_id)
        if dead:
            session.delete(dead)
            session.commit()
        raise HTTPException(status_code=503, detail="邮件发送失败，请稍后重试") from None

    return {"code": 200, "message": "验证码已发送，请查收邮箱（含垃圾箱）"}


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

    _verify_and_clear_otp(session, email, "register_couple", body.verification_code)

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

    _verify_and_clear_otp(session, email, "join_couple", body.verification_code)

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
