from datetime import datetime
from typing import Optional

from sqlalchemy import UniqueConstraint
from sqlmodel import Field, SQLModel


class CoupleAccount(SQLModel, table=True):
    """共享空间：成员用邀请码加入，人数上限由 max_members 决定（与 couple_member 关联）。"""

    id: Optional[int] = Field(default=None, primary_key=True)
    join_code: str = Field(unique=True, index=True, max_length=32)
    max_members: int = Field(default=2)
    created_at: datetime = Field(default_factory=datetime.now)


class CoupleMember(SQLModel, table=True):
    """同一邮箱可加入多个空间；同一空间内邮箱唯一。"""

    __tablename__ = "couple_member"
    __table_args__ = (
        UniqueConstraint("email", "couple_account_id", name="uq_couple_member_email_space"),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    couple_account_id: int = Field(foreign_key="coupleaccount.id", index=True)
    email: str = Field(index=True, max_length=255)
    password_hash: str = Field(max_length=255)
    display_name: str = Field(default="", max_length=120)
    created_at: datetime = Field(default_factory=datetime.now)
