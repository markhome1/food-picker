"""发送邮箱验证码（优先 Resend HTTP API）。"""
from __future__ import annotations

import logging

import httpx

from .config import settings
from .database import is_sqlite_url

logger = logging.getLogger(__name__)


def send_otp_email(to_email: str, code: str) -> None:
    """发送 6 位验证码；失败抛异常由路由转为 HTTP 错误。"""
    ttl = max(5, min(60, settings.email_otp_ttl_minutes))
    subject = f"{settings.app_name} 验证码"
    text_body = f"你的验证码是 {code} ，{ttl} 分钟内有效。如非本人操作请忽略。"

    if settings.resend_api_key.strip():
        from_addr = (settings.resend_from or "").strip() or "onboarding@resend.dev"
        payload = {
            "from": from_addr,
            "to": [to_email],
            "subject": subject,
            "text": text_body,
        }
        with httpx.Client(timeout=20.0) as client:
            r = client.post(
                "https://api.resend.com/emails",
                headers={
                    "Authorization": f"Bearer {settings.resend_api_key.strip()}",
                    "Content-Type": "application/json",
                },
                json=payload,
            )
        if r.status_code >= 400:
            detail = (r.text or "")[:300]
            logger.error("Resend error %s: %s", r.status_code, detail)
            raise RuntimeError("邮件服务暂时不可用，请稍后重试")
        return

    # 仅本地 SQLite：未配置 Resend 时写入日志，便于开发自测（勿用于公网）
    if is_sqlite_url(settings.database_url):
        logger.warning("EMAIL_OTP dev (no RESEND_API_KEY) to=%s code=%s", to_email, code)
        return

    raise RuntimeError("未配置 RESEND_API_KEY，无法发送验证码邮件")
