"""
会员生日礼遇 SOP

设计：
- 后台可在 StudioConfig 配置一张'生日券模板 ID'
- 每月 1 号或访问 /admin/birthday 页面时，触发 ensure_birthdays_for_month()
- 该函数找出本月生日且 active 的会员，每人发一张券（需未拿过本年度同模板的）
- 端点：
    GET /admin/birthday/this-month → 本月生日列表（含是否已发券）
    POST /admin/birthday/run → 手工触发当月发放
"""
from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlmodel import Session, select
from sqlalchemy import func, extract
from ..database import get_session
from ..models import (
    User, UserRole, StudioConfig, Coupon, CouponTemplate, CouponStatus,
)
from ..core.deps import require_admin, get_current_user
from ..services import audit as audit_svc

router = APIRouter(prefix="/api", tags=["birthday"])


class BirthdayMember(BaseModel):
    id: int
    name: str
    phone: str
    birthday: datetime
    age: int
    coupon_granted_year: bool         # 今年是否已发过生日券


def _list_this_month_birthdays(session: Session, year: int, month: int) -> List[User]:
    return session.exec(
        select(User).where(
            User.role == UserRole.member,
            User.is_active == True,
            User.birthday.is_not(None),
            extract("month", User.birthday) == month,
        )
    ).all()


@router.get("/admin/birthday/this-month", response_model=List[BirthdayMember], dependencies=[Depends(require_admin)])
def list_this_month(session: Session = Depends(get_session)):
    now = datetime.utcnow()
    members = _list_this_month_birthdays(session, now.year, now.month)
    out = []
    for m in members:
        # 检查今年是否已经被发过生日券
        # 简化：检查今年内有没有 note 含 birthday 的 coupon
        cps = session.exec(
            select(Coupon).where(
                Coupon.member_id == m.id,
                Coupon.created_at >= datetime(now.year, 1, 1),
            )
        ).all()
        has_birthday_coupon = any(
            "生日" in (c.name or "") or "birthday" in (c.name or "").lower()
            for c in cps
        )
        age = now.year - m.birthday.year
        if (now.month, now.day) < (m.birthday.month, m.birthday.day):
            age -= 1
        out.append(BirthdayMember(
            id=m.id, name=m.name, phone=m.phone, birthday=m.birthday, age=age,
            coupon_granted_year=has_birthday_coupon,
        ))
    return out


class RunResult(BaseModel):
    template_id: int
    template_name: str
    candidates: int        # 本月寿星总数
    skipped: int           # 已发过的跳过数
    granted: int           # 实际发券数


class RunIn(BaseModel):
    template_id: int       # 用哪张券模板（必须是名字含'生日'的，避免误发）


@router.post("/admin/birthday/run", response_model=RunResult)
def run_birthday(
    body: RunIn,
    operator: User = Depends(require_admin),
    session: Session = Depends(get_session),
):
    """手工触发当月生日券发放（重复执行会跳过已发的）"""
    from datetime import timedelta as _td

    tmpl = session.get(CouponTemplate, body.template_id)
    if not tmpl or not tmpl.is_active:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "券模板不存在或已停用")

    now = datetime.utcnow()
    members = _list_this_month_birthdays(session, now.year, now.month)
    valid_until = now + _td(days=tmpl.valid_days) if tmpl.valid_days > 0 else None

    granted = 0
    skipped = 0
    for m in members:
        existing = session.exec(
            select(Coupon).where(
                Coupon.member_id == m.id,
                Coupon.template_id == tmpl.id,
                Coupon.created_at >= datetime(now.year, 1, 1),
            )
        ).first()
        if existing:
            skipped += 1
            continue
        c = Coupon(
            template_id=tmpl.id, member_id=m.id,
            type=tmpl.type, name=tmpl.name, value=tmpl.value,
            min_amount=tmpl.min_amount,
            valid_until=valid_until,
            applicable_category_id=tmpl.applicable_category_id,
        )
        session.add(c)
        granted += 1

    audit_svc.log(session, operator, "birthday.batch", "coupon_template", tmpl.id, {
        "month": now.strftime("%Y-%m"),
        "candidates": len(members), "skipped": skipped, "granted": granted,
    })
    session.commit()
    return RunResult(
        template_id=tmpl.id, template_name=tmpl.name,
        candidates=len(members), skipped=skipped, granted=granted,
    )
