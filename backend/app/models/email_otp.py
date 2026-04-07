from datetime import datetime
from typing import Optional

from sqlmodel import Field, SQLModel


class EmailOtp(SQLModel, table=True):
    """注册/加入前的邮箱验证码（短期有效）。"""

    __tablename__ = "email_otp"

    id: Optional[int] = Field(default=None, primary_key=True)
    email: str = Field(index=True, max_length=255)
    purpose: str = Field(index=True, max_length=32)
    code_hash: str = Field(max_length=255)
    expires_at: datetime
    created_at: datetime = Field(default_factory=datetime.now)
