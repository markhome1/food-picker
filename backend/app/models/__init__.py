from .category import Category
from .couple import CoupleAccount, CoupleMember
from .space_foundation import SpaceFoundation
from .email_otp import EmailOtp
from .otp_send_log import OtpSendLog
from .restaurant import Restaurant, RestaurantCreate, RestaurantUpdate, RestaurantPublic
from .record import DiningRecord, DiningRecordCreate, DiningRecordPublic

# 解析前向引用
Restaurant.model_rebuild()
DiningRecord.model_rebuild()

__all__ = [
    "CoupleAccount",
    "CoupleMember",
    "SpaceFoundation",
    "EmailOtp",
    "OtpSendLog",
    "Restaurant", "RestaurantCreate", "RestaurantUpdate", "RestaurantPublic",
    "DiningRecord", "DiningRecordCreate", "DiningRecordPublic",
    "Category",
]
