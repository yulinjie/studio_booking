from datetime import datetime
from enum import Enum
from typing import Optional
from sqlmodel import SQLModel, Field


class CouponType(str, Enum):
    discount = "discount"          # 满减券（满 X 减 Y）
    percent = "percent"            # 折扣券（X%）
    free_class = "free_class"      # 免费体验课（送 1 节）
    cash = "cash"                  # 现金券（直接抵扣 N 元）


class CouponStatus(str, Enum):
    unused = "unused"
    used = "used"
    expired = "expired"


class CouponTemplate(SQLModel, table=True):
    """优惠券模板。店长创建一个模板，再批量发放给会员"""
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(max_length=64)                             # 例如"新人体验券"
    type: CouponType
    value: int                                                   # 满减/现金的金额（分），折扣的百分比，体验券的次数
    min_amount: int = Field(default=0)                           # 满减门槛（分），0 = 无门槛
    valid_days: int = Field(default=30)                          # 发放后多少天内有效
    applicable_category_id: Optional[int] = Field(default=None, foreign_key="coursecategory.id")
    description: Optional[str] = Field(default=None, max_length=500)
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class Coupon(SQLModel, table=True):
    """会员持有的优惠券（一张一行）"""
    id: Optional[int] = Field(default=None, primary_key=True)
    template_id: int = Field(foreign_key="coupontemplate.id", index=True)
    member_id: int = Field(foreign_key="user.id", index=True)
    type: CouponType
    name: str = Field(max_length=64)                             # 拷贝自 template
    value: int
    min_amount: int = Field(default=0)
    valid_until: Optional[datetime] = Field(default=None, index=True)
    applicable_category_id: Optional[int] = None
    status: CouponStatus = Field(default=CouponStatus.unused, index=True)
    granted_at: datetime = Field(default_factory=datetime.utcnow)
    used_at: Optional[datetime] = None
    related_order_id: Optional[int] = Field(default=None, foreign_key="paymentorder.id")
    related_booking_id: Optional[int] = Field(default=None, foreign_key="booking.id")
