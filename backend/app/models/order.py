from datetime import datetime
from enum import Enum
from typing import Optional
from sqlmodel import SQLModel, Field


class OrderStatus(str, Enum):
    pending = "pending"          # 待支付
    paid = "paid"                # 已支付（线下/微信收款码人工确认）
    cancelled = "cancelled"
    refunded = "refunded"


class PaymentMethod(str, Enum):
    cash = "cash"                # 现金
    wechat_qr = "wechat_qr"      # 微信收款码
    alipay_qr = "alipay_qr"      # 支付宝收款码
    bank = "bank"                # 银行转账
    other = "other"


class PaymentOrder(SQLModel, table=True):
    """购卡订单 — 一期不接在线支付，由店长后台标记"已收款"完成"""
    id: Optional[int] = Field(default=None, primary_key=True)
    order_no: str = Field(max_length=32, unique=True, index=True)
    member_id: int = Field(foreign_key="user.id", index=True)
    template_id: int = Field(foreign_key="cardtemplate.id")
    amount: int                                                # 应收（分）
    paid_amount: int = Field(default=0)                        # 实收（分）
    method: Optional[PaymentMethod] = None
    status: OrderStatus = Field(default=OrderStatus.pending, index=True)
    operator_id: Optional[int] = Field(default=None, foreign_key="user.id")
    paid_at: Optional[datetime] = None
    created_card_id: Optional[int] = Field(default=None, foreign_key="membercard.id")
    refund_amount: int = Field(default=0)                     # 已退金额（分）
    refunded_at: Optional[datetime] = None
    payment_proof: Optional[str] = Field(default=None, max_length=255)  # 会员上传的付款截图 URL
    reject_reason: Optional[str] = Field(default=None, max_length=255)  # 驳回原因
    source: str = Field(default="admin", max_length=16)       # admin（后台开卡）/ self（会员自助）
    note: Optional[str] = Field(default=None, max_length=255)
    created_at: datetime = Field(default_factory=datetime.utcnow, index=True)
