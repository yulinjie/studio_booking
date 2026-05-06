from datetime import datetime
from enum import Enum
from typing import Optional
from sqlmodel import SQLModel, Field


class CourseCategory(SQLModel, table=True):
    """
    课程类型（后台可配置）—— 决定排课规则。
    例如：
      团课:   capacity 12,  扣 1 次,    24h 前可取消
      私教:   capacity  1,  扣 1 次,     2h 前可取消
      双人课: capacity  2
      小班:   capacity  6
    """
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(max_length=32, unique=True)              # "团课" / "私教" / "双人课" / "小班"
    code: str = Field(max_length=32, unique=True)              # group / private / duet / semi
    min_capacity: int = Field(default=1)
    max_capacity: int = Field(default=12)
    requires_coach: bool = Field(default=True)
    default_duration_minutes: int = Field(default=60)
    book_window_hours: int = Field(default=24 * 30)            # 提前多久能约
    cancel_deadline_hours: int = Field(default=24)             # 提前多久取消不扣次
    no_show_deduct: bool = Field(default=True)                 # 爽约扣次
    sort_order: int = Field(default=0)
    is_active: bool = Field(default=True)


class Course(SQLModel, table=True):
    """
    课程定义（一种"课"的模板）。
    例如：流瑜伽 / 普拉提团课 / 普拉提器械私教1v1
    """
    id: Optional[int] = Field(default=None, primary_key=True)
    category_id: int = Field(foreign_key="coursecategory.id", index=True)
    name: str = Field(max_length=64)
    description: Optional[str] = Field(default=None, max_length=1000)
    cover: Optional[str] = Field(default=None, max_length=255)
    duration_minutes: int = Field(default=60)
    capacity: int = Field(default=12)                          # 该课的容量（覆盖 category 默认）
    credit_cost: int = Field(default=1)                        # 扣几次次卡
    price: int = Field(default=0)                              # 单节价格（分）
    difficulty: int = Field(default=2)                         # 1-5 星，强度等级
    tags: Optional[str] = Field(default=None, max_length=255)  # 逗号分隔，如"瘦腰,核心,新人友好"
    suitable_for: Optional[str] = Field(default=None, max_length=200)  # 适合人群描述
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class ClassSessionStatus(str, Enum):
    scheduled = "scheduled"   # 已排
    ongoing = "ongoing"       # 进行中
    finished = "finished"     # 已结
    cancelled = "cancelled"   # 已取消


class ClassSession(SQLModel, table=True):
    """具体一节课（某天某时段）"""
    id: Optional[int] = Field(default=None, primary_key=True)
    course_id: int = Field(foreign_key="course.id", index=True)
    coach_id: Optional[int] = Field(default=None, foreign_key="coach.id", index=True)
    start_at: datetime = Field(index=True)
    end_at: datetime
    capacity: int                                              # 排课时拷贝过来，可以临时调整
    booked_count: int = Field(default=0)                       # 缓存字段，简化查询
    room: Optional[str] = Field(default=None, max_length=32)
    status: ClassSessionStatus = Field(default=ClassSessionStatus.scheduled, index=True)
    note: Optional[str] = Field(default=None, max_length=500)
    created_at: datetime = Field(default_factory=datetime.utcnow)
