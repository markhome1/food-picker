from datetime import datetime
from typing import Optional

from sqlmodel import Field, SQLModel


class OtpSendLog(SQLModel, table=True):
    """邮箱验证码发送记录（只增不删，用于限流统计）。"""

    __tablename__ = "otp_send_log"

    id: Optional[int] = Field(default=None, primary_key=True)
    email: str = Field(index=True, max_length=255)
    created_at: datetime = Field(default_factory=datetime.now)
