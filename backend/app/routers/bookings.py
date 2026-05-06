"""
预约模块 — 整个系统最关键的部分。
处理：抢约（含并发）、取消（区分截止时限）、签到、爽约、候补。
"""
from datetime import datetime, timedelta
from typing import Optional, List
from threading import Lock
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlmodel import Session, select
from sqlalchemy import func, and_
from ..database import get_session
from ..models import (
    User, UserRole,
    ClassSession, ClassSessionStatus, Course, CourseCategory,
    MemberCard, CardStatus, CardType,
    Booking, BookingStatus,
)
from ..core.deps import get_current_user, require_admin, require_staff
from ..services import cards as card_svc, audit as audit_svc, sessions as session_svc

router = APIRouter(prefix="/api", tags=["bookings"])


# 进程内的"按 session 加锁"。SQLite + 单进程足够；多 worker 时换 Redis 锁。
_session_locks: dict[int, Lock] = {}
_locks_guard = Lock()


def _lock_for(session_id: int) -> Lock:
    with _locks_guard:
        lk = _session_locks.get(session_id)
        if lk is None:
            lk = Lock()
            _session_locks[session_id] = lk
        return lk


# ============ DTOs ============

class BookIn(BaseModel):
    session_id: int
    card_id: Optional[int] = None        # 不填则系统自动选一张可用卡
    member_id: Optional[int] = None      # 后台代约时填，会员自助约不填


class BookingOut(BaseModel):
    id: int
    session_id: int
    member_id: int
    card_id: Optional[int] = None
    status: BookingStatus
    waitlist_order: Optional[int] = None
    booked_at: datetime
    cancelled_at: Optional[datetime] = None
    checked_in_at: Optional[datetime] = None
    note: Optional[str] = None

    model_config = {"from_attributes": True}


class BookResult(BaseModel):
    booking: BookingOut
    waitlisted: bool
    message: str


# ============ 工具 ============

def _pick_usable_card(
    session: Session, member_id: int, course: Course, category: CourseCategory
) -> Optional[MemberCard]:
    """优先选 适用类型匹配 + 即将过期 的卡，避免占用通用卡。"""
    cards = session.exec(
        select(MemberCard).where(
            MemberCard.member_id == member_id,
            MemberCard.status == CardStatus.active,
        )
    ).all()
    candidates = []
    for c in cards:
        ok, _ = card_svc.card_is_usable_for(c, category.id)
        if not ok:
            continue
        if c.type == CardType.times or c.type == CardType.package:
            if c.remaining_credits < course.credit_cost:
                continue
        elif c.type == CardType.stored:
            if c.remaining_balance < course.price:
                continue
        candidates.append(c)
    if not candidates:
        return None

    # 排序：限定类型的卡优先 > 即将过期的优先 > 次数少的优先
    def key(c: MemberCard):
        type_specific = 0 if c.applicable_category_id == category.id else 1
        expire_ts = c.valid_until.timestamp() if c.valid_until else 9_999_999_999
        return (type_specific, expire_ts, c.remaining_credits)
    candidates.sort(key=key)
    return candidates[0]


def _today_count_on_card(session: Session, card_id: int, member_id: int, day: datetime) -> int:
    day_start = day.replace(hour=0, minute=0, second=0, microsecond=0)
    day_end = day_start + timedelta(days=1)
    return session.exec(
        select(func.count(Booking.id)).where(
            Booking.card_id == card_id,
            Booking.member_id == member_id,
            Booking.status.in_([BookingStatus.booked, BookingStatus.attended, BookingStatus.late_cancelled, BookingStatus.no_show]),
            Booking.booked_at >= day_start,
            Booking.booked_at < day_end,
        )
    ).one()


# ============ 预约 ============

@router.post("/bookings", response_model=BookResult)
def book(
    body: BookIn,
    current: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    """会员自助预约 / 后台代约（admin/staff 可填 member_id）"""
    # P0-6: 进入预约前先把已结束课节自动结算掉，避免约到已结束的课
    session_svc.settle_past_sessions(session)

    # 谁帮谁约
    if body.member_id and current.role in (UserRole.admin, UserRole.staff):
        member = session.get(User, body.member_id)
        if not member or not member.is_active:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "会员不存在")
    else:
        member = current
        if member.role != UserRole.member:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "只有会员可自助预约")

    cs = session.get(ClassSession, body.session_id)
    if not cs:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "排课不存在")
    if cs.status != ClassSessionStatus.scheduled:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"该课已 {cs.status.value}")
    if cs.start_at < datetime.utcnow():
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "课程已开始或已过")

    course = session.get(Course, cs.course_id)
    category = session.get(CourseCategory, course.category_id) if course else None
    if not course or not category:
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "课程数据异常")

    # 重复预约检查
    existing = session.exec(
        select(Booking).where(
            Booking.session_id == cs.id,
            Booking.member_id == member.id,
            Booking.status.in_([BookingStatus.booked, BookingStatus.waitlist, BookingStatus.attended]),
        )
    ).first()
    if existing:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "你已经预约过这节课")

    # 选卡
    card: Optional[MemberCard] = None
    if body.card_id:
        card = session.get(MemberCard, body.card_id)
        if not card or card.member_id != member.id:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "卡不存在或不属于该会员")
        ok, reason = card_svc.card_is_usable_for(card, category.id)
        if not ok:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, f"卡不可用：{reason}")
        if card.type in (CardType.times, CardType.package) and card.remaining_credits < course.credit_cost:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "卡次数不足")
        if card.type == CardType.stored and card.remaining_balance < course.price:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "卡余额不足")
    else:
        card = _pick_usable_card(session, member.id, course, category)
        if not card:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "没有可用的卡，请先购卡")

    # 期限卡日上限检查
    if card.type == CardType.period and card.daily_limit > 0:
        today_count = _today_count_on_card(session, card.id, member.id, cs.start_at)
        if today_count >= card.daily_limit:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "该卡今日预约已达上限")

    # === 加锁后做容量判断 + 扣次 ===
    with _lock_for(cs.id):
        session.refresh(cs)
        is_full = cs.booked_count >= cs.capacity
        operator = current if current.role in (UserRole.admin, UserRole.staff) else None

        if is_full:
            last_wait = session.exec(
                select(func.max(Booking.waitlist_order)).where(
                    Booking.session_id == cs.id,
                    Booking.status == BookingStatus.waitlist,
                )
            ).one() or 0
            booking = Booking(
                session_id=cs.id,
                member_id=member.id,
                card_id=None,        # 候补不扣卡
                status=BookingStatus.waitlist,
                waitlist_order=(last_wait or 0) + 1,
            )
            session.add(booking)
            session.commit()
            session.refresh(booking)
            return BookResult(
                booking=BookingOut.model_validate(booking),
                waitlisted=True,
                message=f"已加入候补队列，第 {booking.waitlist_order} 位",
            )

        # 扣卡
        booking = Booking(
            session_id=cs.id,
            member_id=member.id,
            card_id=card.id,
            status=BookingStatus.booked,
        )
        session.add(booking)
        session.flush()    # 拿到 booking.id

        if card.type == CardType.stored:
            card_svc.deduct_for_booking(session, card, member.id, booking.id, credits=0, balance_cost=course.price, operator=operator)
        elif card.type == CardType.period:
            card_svc.deduct_for_booking(session, card, member.id, booking.id, credits=0, balance_cost=0, operator=operator)
            # 期限卡：流水标记一下但不扣实际数量
        else:
            card_svc.deduct_for_booking(session, card, member.id, booking.id, credits=course.credit_cost, balance_cost=0, operator=operator)

        cs.booked_count += 1
        session.add(cs)
        audit_svc.log(session, operator or current, "booking.create", "booking", booking.id, {
            "session_id": cs.id, "member_id": member.id, "card_id": card.id,
        })
        session.commit()
        session.refresh(booking)

    return BookResult(
        booking=BookingOut.model_validate(booking),
        waitlisted=False,
        message="预约成功",
    )


# ============ 取消 ============

@router.post("/bookings/{bid}/cancel", response_model=BookingOut)
def cancel(
    bid: int,
    current: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    booking = session.get(Booking, bid)
    if not booking:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "预约不存在")
    if booking.member_id != current.id and current.role not in (UserRole.admin, UserRole.staff):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "无权操作")
    if booking.status not in (BookingStatus.booked, BookingStatus.waitlist):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"当前状态不可取消：{booking.status.value}")

    cs = session.get(ClassSession, booking.session_id)
    course = session.get(Course, cs.course_id)
    category = session.get(CourseCategory, course.category_id)
    operator = current if current.role in (UserRole.admin, UserRole.staff) else None

    with _lock_for(cs.id):
        session.refresh(cs)
        # 候补取消：只标状态
        if booking.status == BookingStatus.waitlist:
            booking.status = BookingStatus.cancelled
            booking.cancelled_at = datetime.utcnow()
            session.add(booking)
            session.commit()
            session.refresh(booking)
            return booking

        # 正式预约：判断是否在截止时限内
        deadline = cs.start_at - timedelta(hours=category.cancel_deadline_hours)
        is_late = datetime.utcnow() > deadline

        # 后台代取消可强制全额返还
        is_admin_cancel = current.role in (UserRole.admin, UserRole.staff)

        if is_late and not is_admin_cancel:
            booking.status = BookingStatus.late_cancelled
        else:
            booking.status = BookingStatus.cancelled
        booking.cancelled_at = datetime.utcnow()
        session.add(booking)

        # 释放容量
        cs.booked_count = max(0, cs.booked_count - 1)
        session.add(cs)

        # 退卡（late_cancelled 不退）
        if booking.status == BookingStatus.cancelled and booking.card_id:
            card = session.get(MemberCard, booking.card_id)
            if card:
                if card.type == CardType.stored:
                    card_svc.refund_for_cancel(session, card, booking.member_id, booking.id, credits=0, balance_cost=course.price, operator=operator)
                elif card.type == CardType.period:
                    card_svc.refund_for_cancel(session, card, booking.member_id, booking.id, credits=0, balance_cost=0, operator=operator)
                else:
                    card_svc.refund_for_cancel(session, card, booking.member_id, booking.id, credits=course.credit_cost, balance_cost=0, operator=operator)

        # 候补晋升：把第一位候补转为 booked + 扣他的卡
        if cs.booked_count < cs.capacity:
            next_wait = session.exec(
                select(Booking).where(
                    Booking.session_id == cs.id,
                    Booking.status == BookingStatus.waitlist,
                ).order_by(Booking.waitlist_order)
            ).first()
            if next_wait:
                wait_member = session.get(User, next_wait.member_id)
                wait_card = _pick_usable_card(session, wait_member.id, course, category) if wait_member else None
                if wait_card:
                    next_wait.status = BookingStatus.booked
                    next_wait.card_id = wait_card.id
                    next_wait.waitlist_order = None
                    session.add(next_wait)
                    if wait_card.type == CardType.stored:
                        card_svc.deduct_for_booking(session, wait_card, wait_member.id, next_wait.id, credits=0, balance_cost=course.price, operator=operator)
                    elif wait_card.type == CardType.period:
                        card_svc.deduct_for_booking(session, wait_card, wait_member.id, next_wait.id, credits=0, balance_cost=0, operator=operator)
                    else:
                        card_svc.deduct_for_booking(session, wait_card, wait_member.id, next_wait.id, credits=course.credit_cost, balance_cost=0, operator=operator)
                    cs.booked_count += 1
                    session.add(cs)

        audit_svc.log(session, operator or current, "booking.cancel", "booking", booking.id, {
            "status": booking.status.value, "by_admin": bool(operator),
        })
        session.commit()
        session.refresh(booking)

    return booking


# ============ 签到 ============

class CheckInIn(BaseModel):
    booking_id: int


@router.post("/admin/check-in", response_model=BookingOut, dependencies=[Depends(require_staff)])
def check_in(
    body: CheckInIn,
    operator: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    booking = session.get(Booking, body.booking_id)
    if not booking:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "预约不存在")
    if booking.status != BookingStatus.booked:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"当前状态不可签到：{booking.status.value}")
    booking.status = BookingStatus.attended
    booking.checked_in_at = datetime.utcnow()
    booking.checked_in_by = operator.id
    session.add(booking)
    audit_svc.log(session, operator, "booking.check_in", "booking", booking.id)
    session.commit()
    session.refresh(booking)
    return booking


@router.post("/admin/sessions/{sid}/no-show", dependencies=[Depends(require_staff)])
def mark_no_show(
    sid: int,
    operator: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    """整节课结束后，未签到的全部标爽约。"""
    cs = session.get(ClassSession, sid)
    if not cs:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "排课不存在")
    bookings = session.exec(
        select(Booking).where(
            Booking.session_id == sid, Booking.status == BookingStatus.booked,
        )
    ).all()
    n = 0
    for b in bookings:
        b.status = BookingStatus.no_show
        session.add(b)
        n += 1
    cs.status = ClassSessionStatus.finished
    session.add(cs)
    audit_svc.log(session, operator, "session.no_show", "session", cs.id, {"marked": n})
    session.commit()
    return {"ok": True, "marked": n}


# ============ 列表查询 ============

@router.get("/me/bookings", response_model=List[BookingOut])
def my_bookings(
    upcoming: bool = True,
    current: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    stmt = select(Booking).where(Booking.member_id == current.id)
    if upcoming:
        stmt = stmt.join(ClassSession, ClassSession.id == Booking.session_id).where(
            ClassSession.start_at >= datetime.utcnow(),
            Booking.status.in_([BookingStatus.booked, BookingStatus.waitlist]),
        )
    return session.exec(stmt.order_by(Booking.id.desc())).all()


@router.get("/admin/sessions/{sid}/bookings", response_model=List[BookingOut], dependencies=[Depends(require_staff)])
def session_bookings(sid: int, session: Session = Depends(get_session)):
    return session.exec(
        select(Booking).where(Booking.session_id == sid).order_by(Booking.id)
    ).all()


@router.get("/admin/bookings", response_model=List[BookingOut], dependencies=[Depends(require_staff)])
def list_all_bookings(
    member_id: Optional[int] = None,
    session: Session = Depends(get_session),
):
    stmt = select(Booking)
    if member_id is not None:
        stmt = stmt.where(Booking.member_id == member_id)
    return session.exec(stmt.order_by(Booking.id.desc()).limit(200)).all()
