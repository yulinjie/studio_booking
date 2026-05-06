from datetime import datetime
from enum import Enum
from typing import Optional
from sqlmodel import SQLModel, Field


class CardType(str, Enum):
    times = "times"          # 次卡：买 N 次，按节扣
    period = "period"        # 期限卡：N 天内不限次（可加上单日上限）
    stored = "stored"        # 储值卡：充值余额，按价扣
    package = "package"      # 课包：私教 N 节，与 category 绑定


class CardTemplate(SQLModel, table=True):
    """卡种模板 — 店长在后台配置"""
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(max_length=64)                                  # "10 次普拉提卡"
    type: CardType = Field(index=True)
    price: int                                                        # 售价（分）
    initial_credits: int = Field(default=0)                           # 次卡/课包：N 次
    initial_balance: int = Field(default=0)                           # 储值卡：初始余额（分）
    valid_days: int = Field(default=0)                                # 期限卡/次卡有效期（0=永久）
    daily_limit: int = Field(default=0)                               # 期限卡每日最多上几节（0=不限）
    applicable_category_id: Optional[int] = Field(default=None, foreign_key="coursecategory.id")
    description: Optional[str] = Field(default=None, max_length=500)
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class CardStatus(str, Enum):
    active = "active"        # 可用
    used_up = "used_up"      # 用完
    expired = "expired"      # 过期
    frozen = "frozen"        # 冻结
    refunded = "refunded"    # 已退


class MemberCard(SQLModel, table=True):
    """会员持有的卡（每张卡一行）"""
    id: Optional[int] = Field(default=None, primary_key=True)
    member_id: int = Field(foreign_key="user.id", index=True)
    template_id: int = Field(foreign_key="cardtemplate.id")
    type: CardType
    name: str = Field(max_length=64)                                  # 拷贝自 template，避免改名穿越
    remaining_credits: int = Field(default=0)
    remaining_balance: int = Field(default=0)                          # 分
    daily_limit: int = Field(default=0)
    valid_from: datetime = Field(default_factory=datetime.utcnow)
    valid_until: Optional[datetime] = Field(default=None, index=True)
    applicable_category_id: Optional[int] = Field(default=None, foreign_key="coursecategory.id")
    status: CardStatus = Field(default=CardStatus.active, index=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class CardTxType(str, Enum):
    purchase = "purchase"        # 购卡
    deduct_book = "deduct_book"  # 预约扣次
    refund_cancel = "refund_cancel"  # 取消返还
    deduct_no_show = "deduct_no_show"  # 爽约扣次
    topup = "topup"              # 充值
    adjust = "adjust"            # 店长手工调整
    expire = "expire"            # 过期清零
    card_refund = "card_refund"  # 整卡退款（卡作废）


class CardTransaction(SQLModel, table=True):
    """卡的流水账 — 每一次次数/余额变动都记录，余额字段必须由流水推算（防止数据穿越）"""
    id: Optional[int] = Field(default=None, primary_key=True)
    card_id: int = Field(foreign_key="membercard.id", index=True)
    member_id: int = Field(foreign_key="user.id", index=True)
    type: CardTxType
    credits_delta: int = Field(default=0)                  # 次数变化（正/负）
    balance_delta: int = Field(default=0)                  # 余额变化（分，正/负）
    related_booking_id: Optional[int] = Field(default=None, foreign_key="booking.id")
    related_order_id: Optional[int] = Field(default=None, foreign_key="paymentorder.id")
    operator_id: Optional[int] = Field(default=None, foreign_key="user.id")  # 谁操作的
    note: Optional[str] = Field(default=None, max_length=255)
    created_at: datetime = Field(default_factory=datetime.utcnow, index=True)
