"""发送邮箱验证码（优先 Resend HTTP API）。"""
from __future__ import annotations

import json
import logging

import httpx

from .config import settings
from .database import is_sqlite_url

logger = logging.getLogger(__name__)


def _resend_user_message(status_code: int, body_text: str) -> str:
    """把 Resend 错误转成用户可理解的提示（不含密钥）。"""
    try:
        data = json.loads(body_text) if body_text.strip() else {}
    except json.JSONDecodeError:
        data = {}
    raw = (data.get("message") or data.get("error") or "").strip()
    low = raw.lower()

    if status_code == 401 or "api key" in low or "unauthorized" in low:
        return "邮件服务密钥无效或未配置，请检查环境变量 RESEND_API_KEY。"
    if status_code == 403 and "onboarding" in low:
        return "当前使用 Resend 测试发件地址，只能发到授权测试邮箱；请配置已验证域名下的 RESEND_FROM，或到 Resend 添加收件测试邮箱。"
    if "from" in low or "domain" in low or "verify" in low:
        return "发件人地址无效或域名未在 Resend 完成验证，请检查 RESEND_FROM（须为 @fpick.asia 等已验证域名下的邮箱）。"
    if raw:
        return f"邮件服务返回：{raw[:240]}"
    return "邮件服务暂时不可用，请稍后重试"


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
            detail = (r.text or "")[:800]
            logger.error("Resend error %s: %s", r.status_code, detail)
            raise RuntimeError(_resend_user_message(r.status_code, detail))
        return

    # 仅本地 SQLite：未配置 Resend 时写入日志，便于开发自测（勿用于公网）
    if is_sqlite_url(settings.database_url):
        logger.warning("EMAIL_OTP dev (no RESEND_API_KEY) to=%s code=%s", to_email, code)
        return

    raise RuntimeError("未配置 RESEND_API_KEY，无法发送验证码邮件")
