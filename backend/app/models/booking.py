from datetime import datetime
from enum import Enum
from typing import Optional
from sqlmodel import SQLModel, Field


class BookingStatus(str, Enum):
    booked = "booked"          # 已预约
    cancelled = "cancelled"    # 已取消（在截止时限前）
    late_cancelled = "late_cancelled"  # 超时取消（仍扣次）
    no_show = "no_show"        # 爽约
    attended = "attended"      # 已上课
    waitlist = "waitlist"      # 候补（满员排队）


class Booking(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    session_id: int = Field(foreign_key="classsession.id", index=True)
    member_id: int = Field(foreign_key="user.id", index=True)
    card_id: Optional[int] = Field(default=None, foreign_key="membercard.id")  # 用哪张卡扣的
    status: BookingStatus = Field(default=BookingStatus.booked, index=True)
    waitlist_order: Optional[int] = Field(default=None)        # 候补队列位置
    booked_at: datetime = Field(default_factory=datetime.utcnow)
    cancelled_at: Optional[datetime] = None
    checked_in_at: Optional[datetime] = None
    checked_in_by: Optional[int] = Field(default=None, foreign_key="user.id")
    note: Optional[str] = Field(default=None, max_length=255)
