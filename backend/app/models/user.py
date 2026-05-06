from datetime import datetime
from enum import Enum
from typing import Optional
from sqlmodel import SQLModel, Field


class UserRole(str, Enum):
    admin = "admin"        # 店长/老板
    staff = "staff"        # 前台
    coach = "coach"        # 教练
    member = "member"      # 会员


class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    phone: str = Field(index=True, unique=True, max_length=20)
    password_hash: Optional[str] = Field(default=None, max_length=255)
    name: str = Field(max_length=64)
    role: UserRole = Field(default=UserRole.member, index=True)
    avatar: Optional[str] = Field(default=None, max_length=255)
    gender: Optional[str] = Field(default=None, max_length=8)  # male / female / other
    birthday: Optional[datetime] = None
    note: Optional[str] = Field(default=None, max_length=500)  # 店长备注
    emergency_contact_name: Optional[str] = Field(default=None, max_length=64)
    emergency_contact_phone: Optional[str] = Field(default=None, max_length=20)
    health_note: Optional[str] = Field(default=None, max_length=2000)  # 已知伤病/过敏/特殊状态
    tags: Optional[str] = Field(default=None, max_length=255)            # 会员标签：新人,VIP,流失风险，逗号分隔
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class Coach(SQLModel, table=True):
    """教练资料 — 与 User 一对一（user.role=coach），私教/团课老师都用这张表存档"""
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", unique=True, index=True)
    title: Optional[str] = Field(default=None, max_length=64)  # 例如 "高级普拉提教练"
    bio: Optional[str] = Field(default=None, max_length=1000)
    specialties: Optional[str] = Field(default=None, max_length=200)  # 逗号分隔
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
