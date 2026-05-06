"""课节自动结算 — lazy 触发，不依赖 cron。"""
from datetime import datetime
from sqlmodel import Session, select
from ..models import (
    ClassSession, ClassSessionStatus,
    Booking, BookingStatus,
)


def settle_past_sessions(session: Session) -> int:
    """
    把所有 end_at < now 且 status=scheduled 的课节结算掉：
    - status → finished
    - 仍 booked 状态的预约 → no_show
    - 仍 waitlist 状态的预约 → cancelled（机会过去了）
    返回结算的课节数。
    """
    now = datetime.utcnow()
    past = session.exec(
        select(ClassSession).where(
            ClassSession.status == ClassSessionStatus.scheduled,
            ClassSession.end_at < now,
        )
    ).all()
    if not past:
        return 0

    for cs in past:
        bookings = session.exec(
            select(Booking).where(Booking.session_id == cs.id)
        ).all()
        for b in bookings:
            if b.status == BookingStatus.booked:
                b.status = BookingStatus.no_show
                session.add(b)
            elif b.status == BookingStatus.waitlist:
                b.status = BookingStatus.cancelled
                b.cancelled_at = now
                session.add(b)
        cs.status = ClassSessionStatus.finished
        session.add(cs)

    session.commit()
    return len(past)
