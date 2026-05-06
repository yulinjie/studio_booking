from datetime import datetime
from typing import Optional
from sqlmodel import SQLModel, Field


class CourseEvaluation(SQLModel, table=True):
    """课后评价（会员给课程 / 教练打分）"""
    id: Optional[int] = Field(default=None, primary_key=True)
    booking_id: int = Field(foreign_key="booking.id", unique=True, index=True)
    member_id: int = Field(foreign_key="user.id", index=True)
    coach_id: Optional[int] = Field(default=None, foreign_key="coach.id", index=True)
    course_id: int = Field(foreign_key="course.id")
    rating: int = Field(ge=1, le=5)                              # 1-5 星
    comment: Optional[str] = Field(default=None, max_length=1000)
    is_anonymous: bool = Field(default=False)
    created_at: datetime = Field(default_factory=datetime.utcnow, index=True)
