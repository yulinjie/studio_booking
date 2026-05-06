"""数据看板：营收 / 出席率 / 教练课时 / 卡负债"""
from datetime import datetime, timedelta
from typing import Optional, List
from fastapi import APIRouter, Depends, Query
from sqlmodel import Session, select
from sqlalchemy import func
from pydantic import BaseModel
from ..database import get_session
from ..models import (
    User, UserRole, MemberCard, CardStatus, CardType,
    PaymentOrder, OrderStatus,
    Booking, BookingStatus,
    ClassSession, ClassSessionStatus, Course, Coach,
)
from ..core.deps import require_admin, get_current_user

router = APIRouter(prefix="/api/admin/reports", tags=["reports"], dependencies=[Depends(require_admin)])


@router.get("/revenue")
def revenue_report(
    days: int = Query(30, ge=1, le=365),
    session: Session = Depends(get_session),
):
    """近 N 天每天的营收（按订单 paid_at 分组）"""
    since = datetime.utcnow() - timedelta(days=days)
    orders = session.exec(
        select(PaymentOrder).where(
            PaymentOrder.status == OrderStatus.paid,
            PaymentOrder.paid_at >= since,
        )
    ).all()
    buckets = {}
    for i in range(days):
        d = (datetime.utcnow() - timedelta(days=days - 1 - i)).strftime("%Y-%m-%d")
        buckets[d] = 0
    for o in orders:
        if not o.paid_at:
            continue
        d = o.paid_at.strftime("%Y-%m-%d")
        if d in buckets:
            buckets[d] += (o.paid_amount or 0) - (o.refund_amount or 0)
    return {
        "labels": list(buckets.keys()),
        "data": list(buckets.values()),
        "total": sum(buckets.values()),
        "days": days,
    }


@router.get("/attendance")
def attendance_report(
    days: int = Query(30, ge=1, le=365),
    session: Session = Depends(get_session),
):
    """近 N 天的出席率（attended / 总预约）"""
    since = datetime.utcnow() - timedelta(days=days)
    bookings = session.exec(
        select(Booking).where(Booking.booked_at >= since)
    ).all()
    total = len(bookings)
    attended = sum(1 for b in bookings if b.status == BookingStatus.attended)
    no_show = sum(1 for b in bookings if b.status == BookingStatus.no_show)
    cancelled = sum(1 for b in bookings if b.status in (BookingStatus.cancelled, BookingStatus.late_cancelled))
    return {
        "total": total,
        "attended": attended,
        "no_show": no_show,
        "cancelled": cancelled,
        "rate": round(attended / total, 3) if total > 0 else 0,
        "days": days,
    }


@router.get("/coach-hours")
def coach_hours_report(
    days: int = Query(30, ge=1, le=365),
    session: Session = Depends(get_session),
):
    """近 N 天每个教练的课时数（按 session 数 + 总时长）"""
    since = datetime.utcnow() - timedelta(days=days)
    coaches = session.exec(select(Coach)).all()
    users = {u.id: u for u in session.exec(select(User)).all()}
    sessions = session.exec(
        select(ClassSession).where(
            ClassSession.start_at >= since,
            ClassSession.status.in_([ClassSessionStatus.scheduled, ClassSessionStatus.finished]),
        )
    ).all()

    out = []
    for coach in coaches:
        coach_sessions = [s for s in sessions if s.coach_id == coach.id]
        total_minutes = sum(int((s.end_at - s.start_at).total_seconds() / 60) for s in coach_sessions)
        total_attended = sum(s.booked_count for s in coach_sessions)
        u = users.get(coach.user_id)
        out.append({
            "coach_id": coach.id,
            "name": u.name if u else f"#{coach.user_id}",
            "title": coach.title,
            "session_count": len(coach_sessions),
            "total_minutes": total_minutes,
            "total_attended": total_attended,
        })
    out.sort(key=lambda x: x["session_count"], reverse=True)
    return {"days": days, "items": out}


@router.get("/card-liability")
def card_liability_report(session: Session = Depends(get_session)):
    """工作室对会员的负债：所有 active 卡的剩余次数 × 单次价值（粗估） + 储值卡余额"""
    cards = session.exec(
        select(MemberCard).where(MemberCard.status == CardStatus.active)
    ).all()

    by_type = {"times": 0, "period": 0, "stored": 0, "package": 0}
    total_credits = 0
    total_balance = 0
    for c in cards:
        by_type[c.type.value] = by_type.get(c.type.value, 0) + 1
        if c.type in (CardType.times, CardType.package):
            total_credits += c.remaining_credits
        elif c.type == CardType.stored:
            total_balance += c.remaining_balance

    return {
        "active_cards": len(cards),
        "by_type": by_type,
        "total_remaining_credits": total_credits,
        "total_remaining_balance": total_balance,
    }


@router.get("/member-growth")
def member_growth_report(
    days: int = Query(90, ge=7, le=365),
    session: Session = Depends(get_session),
):
    """近 N 天会员增长 + 累计"""
    since = datetime.utcnow() - timedelta(days=days)
    members = session.exec(
        select(User).where(User.role == UserRole.member, User.created_at >= since)
    ).all()
    buckets = {}
    for i in range(days):
        d = (datetime.utcnow() - timedelta(days=days - 1 - i)).strftime("%Y-%m-%d")
        buckets[d] = 0
    for m in members:
        d = m.created_at.strftime("%Y-%m-%d")
        if d in buckets:
            buckets[d] += 1

    # 累计：之前的总数 + 每天增量
    total_before = session.exec(
        select(func.count(User.id)).where(User.role == UserRole.member, User.created_at < since)
    ).one() or 0
    cumulative = []
    running = total_before
    for v in buckets.values():
        running += v
        cumulative.append(running)

    return {
        "labels": list(buckets.keys()),
        "new": list(buckets.values()),
        "cumulative": cumulative,
        "days": days,
    }


# ============ 个人练习统计（会员看） ============

practice_router = APIRouter(prefix="/api/me", tags=["practice-stats"])


@practice_router.get("/practice-stats")
def my_practice_stats(
    current: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    """会员个人练习统计：本周/本月/累计已上课次数 + 各课程类型分布 + 上次练习"""
    now = datetime.utcnow()
    week_start = now - timedelta(days=7)
    month_start = now - timedelta(days=30)

    bookings = session.exec(
        select(Booking).where(
            Booking.member_id == current.id,
            Booking.status == BookingStatus.attended,
        )
    ).all()

    week_count = sum(1 for b in bookings if b.booked_at >= week_start)
    month_count = sum(1 for b in bookings if b.booked_at >= month_start)
    total_count = len(bookings)

    # 距离上次练习
    last_practice = max((b.booked_at for b in bookings), default=None)
    days_since_last = (now - last_practice).days if last_practice else None

    # 课程类型分布（近 30 天）
    sessions_map = {}
    if bookings:
        sids = [b.session_id for b in bookings if b.booked_at >= month_start]
        if sids:
            sessions = session.exec(select(ClassSession).where(ClassSession.id.in_(sids))).all()
            sessions_map = {s.id: s for s in sessions}
            course_ids = [s.course_id for s in sessions_map.values()]
            courses = session.exec(select(Course).where(Course.id.in_(course_ids))).all() if course_ids else []
            cat_count = {}
            for s in sessions_map.values():
                course = next((c for c in courses if c.id == s.course_id), None)
                if course:
                    cat_count[course.category_id] = cat_count.get(course.category_id, 0) + 1
            cat_dist = cat_count
        else:
            cat_dist = {}
    else:
        cat_dist = {}

    return {
        "week": week_count,
        "month": month_count,
        "total": total_count,
        "last_practice": last_practice.isoformat() if last_practice else None,
        "days_since_last": days_since_last,
        "category_distribution": cat_dist,
    }
