"""记录邮箱作为创建者已创建的空间类型（情侣 2 人 / 好友组队 3+ 人），每类至多一次。"""

from datetime import datetime
from typing import Optional

from sqlalchemy import UniqueConstraint
from sqlmodel import Field, SQLModel


class SpaceFoundation(SQLModel, table=True):
    __tablename__ = "space_foundation"
    __table_args__ = (UniqueConstraint("email", "foundation_kind", name="uq_space_foundation_email_kind"),)

    id: Optional[int] = Field(default=None, primary_key=True)
    email: str = Field(index=True, max_length=255)
    foundation_kind: str = Field(max_length=16)  # "pair" | "group"
    couple_account_id: int = Field(foreign_key="coupleaccount.id", index=True)
    created_at: datetime = Field(default_factory=datetime.now)
