from datetime import datetime
from typing import Optional
from sqlmodel import SQLModel, Field


class AuditLog(SQLModel, table=True):
    """关键 mutation 留痕。出纠纷或排查问题时回查。"""
    id: Optional[int] = Field(default=None, primary_key=True)
    ts: datetime = Field(default_factory=datetime.utcnow, index=True)
    operator_id: Optional[int] = Field(default=None, foreign_key="user.id", index=True)
    operator_name: Optional[str] = Field(default=None, max_length=64)
    action: str = Field(max_length=64, index=True)               # "booking.cancel"
    target_type: Optional[str] = Field(default=None, max_length=32)  # "booking" / "card" / "user"
    target_id: Optional[int] = Field(default=None, index=True)
    detail: Optional[str] = Field(default=None, max_length=2000)     # JSON 字符串
