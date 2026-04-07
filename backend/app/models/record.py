from datetime import datetime, date
from typing import Optional, TYPE_CHECKING
from sqlmodel import Field, SQLModel, Relationship

if TYPE_CHECKING:
    from .restaurant import Restaurant


class DiningRecordBase(SQLModel):
    restaurant_id: int = Field(foreign_key="restaurant.id")
    dining_date: date = Field(default_factory=date.today)
    departure_address: str = ""
    departure_lat: Optional[float] = None
    departure_lng: Optional[float] = None
    actual_cost: Optional[float] = None
    rating: Optional[float] = None
    comment: str = ""


class DiningRecord(DiningRecordBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.now)

    restaurant: Optional["Restaurant"] = Relationship(back_populates="records")


class DiningRecordCreate(DiningRecordBase):
    pass


class DiningRecordPublic(DiningRecordBase):
    id: int
    created_at: datetime
    restaurant_name: str = ""
