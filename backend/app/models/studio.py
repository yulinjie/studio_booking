from datetime import datetime
from typing import Optional
from sqlmodel import SQLModel, Field


class StudioConfig(SQLModel, table=True):
    """单行表 — 工作室全局配置"""
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(max_length=128)
    logo: Optional[str] = Field(default=None, max_length=255)
    address: Optional[str] = Field(default=None, max_length=255)
    phone: Optional[str] = Field(default=None, max_length=32)
    open_time: str = Field(default="07:00")
    close_time: str = Field(default="22:00")
    announcement: Optional[str] = Field(default=None, max_length=1000)
    booking_rules: Optional[str] = Field(default=None, max_length=2000)   # 显示给会员看的规则
    payment_qr: Optional[str] = Field(default=None, max_length=255)       # 收款码图片 URL（会员自助买卡时显示）
    payment_note: Optional[str] = Field(default=None, max_length=500)     # 付款说明（如"备注请写姓名"）
    updated_at: datetime = Field(default_factory=datetime.utcnow)
