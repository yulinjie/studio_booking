from datetime import datetime
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlmodel import Session, select
from sqlalchemy import func
from ..database import get_session
from ..models import (
    User, Booking, BookingStatus, CourseEvaluation,
    ClassSession, Course, Coach,
)
from ..core.deps import get_current_user, require_staff

router = APIRouter(prefix="/api", tags=["evaluations"])


class EvalIn(BaseModel):
    booking_id: int
    rating: int = Field(ge=1, le=5)
    comment: Optional[str] = Field(default=None, max_length=1000)
    is_anonymous: bool = False


@router.post("/evaluations", response_model=CourseEvaluation)
def create_evaluation(
    body: EvalIn,
    current: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    booking = session.get(Booking, body.booking_id)
    if not booking or booking.member_id != current.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "预约不存在")
    if booking.status != BookingStatus.attended:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "只能评价已上课的预约")
    existing = session.exec(
        select(CourseEvaluation).where(CourseEvaluation.booking_id == body.booking_id)
    ).first()
    if existing:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "已评价过")

    cs = session.get(ClassSession, booking.session_id)
    ev = CourseEvaluation(
        booking_id=booking.id, member_id=current.id,
        coach_id=cs.coach_id if cs else None,
        course_id=cs.course_id if cs else 0,
        rating=body.rating, comment=body.comment, is_anonymous=body.is_anonymous,
    )
    session.add(ev)
    session.commit()
    session.refresh(ev)
    return ev


@router.get("/me/pending-evaluations", response_model=List[Booking])
def my_pending_evaluations(
    current: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    """近 30 天已上课但未评价的预约"""
    from datetime import timedelta
    since = datetime.utcnow() - timedelta(days=30)
    attended = session.exec(
        select(Booking).where(
            Booking.member_id == current.id,
            Booking.status == BookingStatus.attended,
            Booking.checked_in_at >= since,
        )
    ).all()
    evaluated = session.exec(
        select(CourseEvaluation.booking_id).where(CourseEvaluation.member_id == current.id)
    ).all()
    evaluated_set = set(evaluated)
    return [b for b in attended if b.id not in evaluated_set]


@router.get("/admin/evaluations", response_model=List[CourseEvaluation], dependencies=[Depends(require_staff)])
def list_all_evaluations(
    coach_id: Optional[int] = None,
    course_id: Optional[int] = None,
    session: Session = Depends(get_session),
):
    stmt = select(CourseEvaluation)
    if coach_id is not None:
        stmt = stmt.where(CourseEvaluation.coach_id == coach_id)
    if course_id is not None:
        stmt = stmt.where(CourseEvaluation.course_id == course_id)
    return session.exec(stmt.order_by(CourseEvaluation.id.desc()).limit(200)).all()


@router.get("/coaches/{coach_id}/rating")
def coach_rating(coach_id: int, session: Session = Depends(get_session), _: User = Depends(get_current_user)):
    """教练平均分 + 评价数"""
    rows = session.exec(
        select(func.avg(CourseEvaluation.rating), func.count(CourseEvaluation.id))
        .where(CourseEvaluation.coach_id == coach_id)
    ).one()
    avg, cnt = rows
    return {
        "coach_id": coach_id,
        "average": round(float(avg), 2) if avg else None,
        "count": cnt or 0,
    }
