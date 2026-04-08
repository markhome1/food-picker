import re
import secrets
from datetime import datetime, timedelta
from typing import Annotated, Literal, Optional

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
from ..models.space_foundation import SpaceFoundation

router = APIRouter(prefix="/api/auth", tags=["auth"])

SessionDep = Annotated[Session, Depends(get_session)]

# 单空间人数上限（创建时可设更小，全局不超过此值）
_ABSOLUTE_MEMBER_CAP = 20
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
    max_members: Optional[int] = Field(default=None, ge=2, le=_ABSOLUTE_MEMBER_CAP)
    join_code: Optional[str] = Field(default=None, max_length=32)


class RegisterCoupleIn(BaseModel):
    email: str = Field(..., min_length=5, max_length=255)
    password: str = Field(..., min_length=6, max_length=128)
    display_name: str = Field(default="", max_length=120)
    verification_code: str = Field(..., min_length=6, max_length=6, pattern=r"^\d{6}$")
    max_members: int = Field(default=2, ge=2, le=_ABSOLUTE_MEMBER_CAP)


class JoinCoupleIn(BaseModel):
    join_code: str = Field(..., min_length=4, max_length=32)
    email: str = Field(..., min_length=5, max_length=255)
    password: str = Field(..., min_length=6, max_length=128)
    display_name: str = Field(default="", max_length=120)
    verification_code: str = Field(..., min_length=6, max_length=6, pattern=r"^\d{6}$")


class LoginIn(BaseModel):
    email: str = Field(..., min_length=3, max_length=255)
    password: str = Field(..., min_length=1, max_length=128)
    couple_account_id: Optional[int] = Field(default=None)


def _foundation_kind_for_max_members(max_members: int) -> str:
    return "pair" if int(max_members) == 2 else "group"


def _raise_if_cannot_found_space(session: Session, email: str, max_members: int) -> None:
    """同一邮箱作为创建者：情侣（2 人）空间与好友组队（3+ 人）空间各仅能创建一次。"""
    cap = min(max(int(max_members), 2), _ABSOLUTE_MEMBER_CAP)
    kind = _foundation_kind_for_max_members(cap)
    ex = session.exec(
        select(SpaceFoundation).where(
            SpaceFoundation.email == email,
            SpaceFoundation.foundation_kind == kind,
        )
    ).first()
    if ex:
        if kind == "pair":
            raise HTTPException(
                status_code=400,
                detail="该邮箱已创建过情侣（2 人）空间，无法再次创建",
            )
        raise HTTPException(
            status_code=400,
            detail="该邮箱已创建过好友组队空间，无法再次创建",
        )


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

    if body.purpose == "register_couple":
        max_m = body.max_members if body.max_members is not None else 2
        max_m = min(max(int(max_m), 2), _ABSOLUTE_MEMBER_CAP)
        _raise_if_cannot_found_space(session, email, max_m)
    elif body.purpose == "join_couple":
        jc = (body.join_code or "").strip()
        if not jc:
            raise HTTPException(status_code=400, detail="加入空间请先填写邀请码")
        code = _norm_join_code(jc)
        acc = session.exec(select(CoupleAccount).where(CoupleAccount.join_code == code)).first()
        if not acc:
            raise HTTPException(status_code=400, detail="邀请码无效")
        in_space = session.exec(
            select(CoupleMember).where(
                CoupleMember.email == email,
                CoupleMember.couple_account_id == acc.id,
            )
        ).first()
        if in_space:
            raise HTTPException(status_code=400, detail="该邮箱已在该空间中")

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
    cap = min(
        (acc.max_members if acc and acc.max_members else 2),
        _ABSOLUTE_MEMBER_CAP,
    )
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
        "member_cap": cap,
        "max_members": cap,
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

    cap = min(max(int(body.max_members), 2), _ABSOLUTE_MEMBER_CAP)
    _raise_if_cannot_found_space(session, email, cap)

    _verify_and_clear_otp(session, email, "register_couple", body.verification_code)

    _raise_if_cannot_found_space(session, email, cap)

    for _ in range(8):
        code = _new_join_code()
        taken = session.exec(select(CoupleAccount).where(CoupleAccount.join_code == code)).first()
        if not taken:
            break
    else:
        raise HTTPException(status_code=500, detail="无法生成邀请码，请重试")

    acc = CoupleAccount(join_code=code, max_members=cap)
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
    session.add(
        SpaceFoundation(
            email=email,
            foundation_kind=_foundation_kind_for_max_members(cap),
            couple_account_id=acc.id,
        )
    )
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
    cap = min(int(acc.max_members or 2), _ABSOLUTE_MEMBER_CAP)
    if cap < 2:
        cap = 2
    if _member_count(session, acc.id) >= cap:
        raise HTTPException(
            status_code=400,
            detail=f"该空间已满员（最多 {cap} 人）",
        )

    email = body.email.strip().lower()
    if not _EMAIL_RE.match(email):
        raise HTTPException(status_code=400, detail="邮箱格式不正确")
    already = session.exec(
        select(CoupleMember).where(
            CoupleMember.email == email,
            CoupleMember.couple_account_id == acc.id,
        )
    ).first()
    if already:
        raise HTTPException(status_code=400, detail="该邮箱已在该空间中")

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
    cands = session.exec(select(CoupleMember).where(CoupleMember.email == email)).all()
    matches = [u for u in cands if _verify_password(body.password, u.password_hash)]
    if not matches:
        raise HTTPException(status_code=400, detail="邮箱或密码错误")
    if len(matches) > 1:
        if body.couple_account_id is None:
            spaces = []
            for u in matches:
                a = session.get(CoupleAccount, u.couple_account_id)
                spaces.append(
                    {
                        "couple_account_id": u.couple_account_id,
                        "join_code": (a.join_code if a else ""),
                    }
                )
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "pick_space",
                    "message": "该邮箱在多个空间中，请选择要登录的空间",
                    "spaces": spaces,
                },
            )
        user = next(
            (u for u in matches if u.couple_account_id == body.couple_account_id),
            None,
        )
        if user is None:
            raise HTTPException(status_code=400, detail="所选空间与邮箱或密码不匹配")
    else:
        user = matches[0]
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
