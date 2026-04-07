import enum
from datetime import datetime
from typing import Optional, List, TYPE_CHECKING
from sqlmodel import Field, SQLModel, Relationship

if TYPE_CHECKING:
    from .record import DiningRecord


class SourceEnum(str, enum.Enum):
    manual = "manual"
    douyin = "douyin"
    amap = "amap"
    dianping = "dianping"


class PriceTierEnum(str, enum.Enum):
    tier_0_10 = "0-10"
    tier_10_20 = "10-20"
    tier_20_50 = "20-50"
    tier_50_100 = "50-100"
    tier_100_plus = "100+"


# --- Base / Table / Create / Update / Public ---

class RestaurantBase(SQLModel):
    name: str = Field(index=True)
    address: str = ""
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    avg_price: Optional[float] = None
    price_tier: PriceTierEnum = PriceTierEnum.tier_20_50
    category: str = ""
    tags: str = ""  # 逗号分隔
    source: SourceEnum = SourceEnum.manual
    source_url: str = ""
    rating: Optional[float] = None
    image_url: str = ""
    # 大众点评：须从 APP/网页核对后手工录入（平台无面向第三方的免费评分 API，本站不抓取评论正文）
    dianping_rating: Optional[float] = None
    dianping_url: str = ""
    dianping_snippet: str = ""
    # 其它权威来源（如高德指南、黑珍珠、米其林榜单页等）：名称 + 评分 + 官方链接
    authority_label: str = ""
    authority_rating: Optional[float] = None
    authority_url: str = ""
    # 分号分隔榜单：my_pick=自己精选，viral=网红打卡（抖音向）；高分推荐为查询条件非存储
    boards: str = ""


class Restaurant(RestaurantBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    couple_account_id: Optional[int] = Field(
        default=None,
        foreign_key="coupleaccount.id",
        index=True,
    )
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

    records: List["DiningRecord"] = Relationship(back_populates="restaurant")


class RestaurantCreate(RestaurantBase):
    pass


class RestaurantUpdate(SQLModel):
    name: Optional[str] = None
    address: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    avg_price: Optional[float] = None
    price_tier: Optional[PriceTierEnum] = None
    category: Optional[str] = None
    tags: Optional[str] = None
    source: Optional[SourceEnum] = None
    source_url: Optional[str] = None
    rating: Optional[float] = None
    image_url: Optional[str] = None
    dianping_rating: Optional[float] = None
    dianping_url: Optional[str] = None
    dianping_snippet: Optional[str] = None
    authority_label: Optional[str] = None
    authority_rating: Optional[float] = None
    authority_url: Optional[str] = None
    boards: Optional[str] = None


class RestaurantPublic(RestaurantBase):
    id: int
    created_at: datetime
    updated_at: datetime
    visit_count: int = 0  # 动态计算
    distance_km: Optional[float] = None  # 动态计算
