"""
教练课时工资统计

工资公式（每个月）：
  total = base_salary
        + sum_per_finished_session( pay_per_session
                                  + attendees * pay_per_attendee
                                  + sum(course.price * attendees) * commission_bps / 10000 )

只计算 status=finished 的排课，attendees = 该课所有 status=attended 的预约数。
"""
from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlmodel import Session, select
from ..database import get_session
from ..models import (
    User, Coach, ClassSession, ClassSessionStatus,
    Course, Booking, BookingStatus,
)
from ..core.deps import require_admin

router = APIRouter(prefix="/api", tags=["payroll"])


def _month_range(month: str):
    """month: 'YYYY-MM' → (start_dt, end_dt) 半开区间"""
    y, m = map(int, month.split("-"))
    start = datetime(y, m, 1)
    if m == 12:
        end = datetime(y + 1, 1, 1)
    else:
        end = datetime(y, m + 1, 1)
    return start, end


class SessionEarning(BaseModel):
    session_id: int
    start_at: datetime
    course_name: str
    capacity: int
    attendees: int
    pay_per_session: int
    attendee_pay: int
    commission_pay: int
    subtotal: int


class CoachPayroll(BaseModel):
    coach_id: int
    name: str
    title: Optional[str] = None
    base_salary: int
    sessions_count: int
    total_attendees: int
    sessions_pay: int          # 各课时课时费总和
    attendee_pay: int          # 人头补贴总和
    commission_pay: int        # 提成总和
    total: int                 # 月总工资
    rates: dict                # 当前薪酬配置快照


class PayrollSummary(BaseModel):
    month: str
    total_payroll: int
    coach_count: int
    coaches: List[CoachPayroll]


@router.get("/admin/payroll", response_model=PayrollSummary, dependencies=[Depends(require_admin)])
def get_payroll(
    month: str = Query(..., regex=r"^\d{4}-\d{2}$"),
    session: Session = Depends(get_session),
):
    start, end = _month_range(month)

    coaches = session.exec(select(Coach).where(Coach.is_active == True)).all()
    users = {u.id: u for u in session.exec(select(User)).all()}
    courses = {c.id: c for c in session.exec(select(Course)).all()}

    # 该月所有 finished 排课
    finished_sessions = session.exec(
        select(ClassSession).where(
            ClassSession.status == ClassSessionStatus.finished,
            ClassSession.start_at >= start,
            ClassSession.start_at < end,
        )
    ).all()

    # 每节课的实际签到数
    session_attended = {}
    sids = [s.id for s in finished_sessions]
    if sids:
        attended_bookings = session.exec(
            select(Booking).where(
                Booking.session_id.in_(sids),
                Booking.status == BookingStatus.attended,
            )
        ).all()
        for b in attended_bookings:
            session_attended[b.session_id] = session_attended.get(b.session_id, 0) + 1

    # 按教练分组算
    out: List[CoachPayroll] = []
    for coach in coaches:
        u = users.get(coach.user_id)
        if not u:
            continue
        sessions_pay = 0
        attendee_pay = 0
        commission_pay = 0
        sessions_count = 0
        total_attendees = 0
        for cs in finished_sessions:
            if cs.coach_id != coach.id:
                continue
            attendees = session_attended.get(cs.id, 0)
            course = courses.get(cs.course_id)
            unit_price = course.price if course else 0
            sp = coach.pay_per_session
            ap = attendees * coach.pay_per_attendee
            cp = (attendees * unit_price * coach.commission_bps) // 10000
            sessions_pay += sp
            attendee_pay += ap
            commission_pay += cp
            sessions_count += 1
            total_attendees += attendees

        total = coach.base_salary + sessions_pay + attendee_pay + commission_pay
        out.append(CoachPayroll(
            coach_id=coach.id,
            name=u.name,
            title=coach.title,
            base_salary=coach.base_salary,
            sessions_count=sessions_count,
            total_attendees=total_attendees,
            sessions_pay=sessions_pay,
            attendee_pay=attendee_pay,
            commission_pay=commission_pay,
            total=total,
            rates={
                "pay_per_session": coach.pay_per_session,
                "pay_per_attendee": coach.pay_per_attendee,
                "commission_bps": coach.commission_bps,
            },
        ))

    out.sort(key=lambda x: x.total, reverse=True)
    return PayrollSummary(
        month=month,
        total_payroll=sum(c.total for c in out),
        coach_count=len(out),
        coaches=out,
    )


@router.get("/admin/payroll/{coach_id}/sessions", response_model=List[SessionEarning], dependencies=[Depends(require_admin)])
def get_coach_payroll_sessions(
    coach_id: int,
    month: str = Query(..., regex=r"^\d{4}-\d{2}$"),
    session: Session = Depends(get_session),
):
    """单个教练在某月的明细 — 每节课的明细工资"""
    start, end = _month_range(month)
    coach = session.get(Coach, coach_id)
    if not coach:
        return []
    courses = {c.id: c for c in session.exec(select(Course)).all()}

    finished = session.exec(
        select(ClassSession).where(
            ClassSession.coach_id == coach_id,
            ClassSession.status == ClassSessionStatus.finished,
            ClassSession.start_at >= start,
            ClassSession.start_at < end,
        ).order_by(ClassSession.start_at)
    ).all()

    session_attended = {}
    if finished:
        sids = [s.id for s in finished]
        attended_bookings = session.exec(
            select(Booking).where(
                Booking.session_id.in_(sids),
                Booking.status == BookingStatus.attended,
            )
        ).all()
        for b in attended_bookings:
            session_attended[b.session_id] = session_attended.get(b.session_id, 0) + 1

    rows = []
    for cs in finished:
        attendees = session_attended.get(cs.id, 0)
        course = courses.get(cs.course_id)
        unit_price = course.price if course else 0
        sp = coach.pay_per_session
        ap = attendees * coach.pay_per_attendee
        cp = (attendees * unit_price * coach.commission_bps) // 10000
        rows.append(SessionEarning(
            session_id=cs.id,
            start_at=cs.start_at,
            course_name=course.name if course else "?",
            capacity=cs.capacity,
            attendees=attendees,
            pay_per_session=sp,
            attendee_pay=ap,
            commission_pay=cp,
            subtotal=sp + ap + cp,
        ))
    return rows
