from datetime import datetime
from typing import Optional

from sqlmodel import Field, SQLModel


class CoupleAccount(SQLModel, table=True):
    """共享空间：成员用邀请码加入，人数上限由 max_members 决定（与 couple_member 关联）。"""

    id: Optional[int] = Field(default=None, primary_key=True)
    join_code: str = Field(unique=True, index=True, max_length=32)
    max_members: int = Field(default=2)
    created_at: datetime = Field(default_factory=datetime.now)


class CoupleMember(SQLModel, table=True):
    """避免表名 user（SQLite 保留字）冲突，使用 couple_member。"""

    __tablename__ = "couple_member"

    id: Optional[int] = Field(default=None, primary_key=True)
    couple_account_id: int = Field(foreign_key="coupleaccount.id", index=True)
    email: str = Field(unique=True, index=True, max_length=255)
    password_hash: str = Field(max_length=255)
    display_name: str = Field(default="", max_length=120)
    created_at: datetime = Field(default_factory=datetime.now)
