from datetime import datetime, timedelta
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlmodel import Session, select
from sqlalchemy import func
from ..database import get_session
from ..models import (
    User, UserRole,
    CourseCategory, Course, ClassSession, ClassSessionStatus, Coach,
)
from ..core.deps import get_current_user, require_admin, require_staff
from ..services import audit as audit_svc, sessions as session_svc

router = APIRouter(prefix="/api", tags=["courses"])


# ============ 课程类型（4 种基础类型，店长可配） ============

class CategoryIn(BaseModel):
    name: str = Field(min_length=1, max_length=32)
    code: str = Field(min_length=1, max_length=32)
    min_capacity: int = 1
    max_capacity: int = 12
    requires_coach: bool = True
    default_duration_minutes: int = 60
    book_window_hours: int = 24 * 30
    cancel_deadline_hours: int = 24
    no_show_deduct: bool = True
    sort_order: int = 0
    is_active: bool = True


class CategoryUpdate(BaseModel):
    name: Optional[str] = None
    min_capacity: Optional[int] = None
    max_capacity: Optional[int] = None
    requires_coach: Optional[bool] = None
    default_duration_minutes: Optional[int] = None
    book_window_hours: Optional[int] = None
    cancel_deadline_hours: Optional[int] = None
    no_show_deduct: Optional[bool] = None
    sort_order: Optional[int] = None
    is_active: Optional[bool] = None


@router.get("/course-categories", response_model=List[CourseCategory])
def list_categories(session: Session = Depends(get_session), _: User = Depends(get_current_user)):
    return session.exec(
        select(CourseCategory).where(CourseCategory.is_active == True).order_by(CourseCategory.sort_order)
    ).all()


@router.get("/admin/course-categories", response_model=List[CourseCategory], dependencies=[Depends(require_admin)])
def list_all_categories(session: Session = Depends(get_session)):
    return session.exec(select(CourseCategory).order_by(CourseCategory.sort_order)).all()


@router.post("/admin/course-categories", response_model=CourseCategory, dependencies=[Depends(require_admin)])
def create_category(body: CategoryIn, session: Session = Depends(get_session)):
    if session.exec(select(CourseCategory).where(CourseCategory.code == body.code)).first():
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "code 已存在")
    cat = CourseCategory(**body.model_dump())
    session.add(cat)
    session.commit()
    session.refresh(cat)
    return cat


@router.patch("/admin/course-categories/{cid}", response_model=CourseCategory, dependencies=[Depends(require_admin)])
def update_category(cid: int, body: CategoryUpdate, session: Session = Depends(get_session)):
    cat = session.get(CourseCategory, cid)
    if not cat:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "课程类型不存在")
    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(cat, k, v)
    session.add(cat)
    session.commit()
    session.refresh(cat)
    return cat


# ============ 课程模板 ============

class CourseIn(BaseModel):
    category_id: int
    name: str = Field(min_length=1, max_length=64)
    description: Optional[str] = None
    cover: Optional[str] = None
    duration_minutes: int = 60
    capacity: int = Field(default=12, ge=1)
    credit_cost: int = Field(default=1, ge=0)
    price: int = Field(default=0, ge=0)
    difficulty: int = Field(default=2, ge=1, le=5)
    tags: Optional[str] = None
    suitable_for: Optional[str] = None
    is_active: bool = True


class CourseUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    cover: Optional[str] = None
    duration_minutes: Optional[int] = None
    capacity: Optional[int] = None
    credit_cost: Optional[int] = None
    price: Optional[int] = None
    difficulty: Optional[int] = Field(default=None, ge=1, le=5)
    tags: Optional[str] = None
    suitable_for: Optional[str] = None
    is_active: Optional[bool] = None


@router.get("/courses", response_model=List[Course])
def list_courses(
    category_id: Optional[int] = None,
    session: Session = Depends(get_session),
    _: User = Depends(get_current_user),
):
    stmt = select(Course).where(Course.is_active == True)
    if category_id is not None:
        stmt = stmt.where(Course.category_id == category_id)
    return session.exec(stmt.order_by(Course.id.desc())).all()


@router.get("/admin/courses", response_model=List[Course], dependencies=[Depends(require_admin)])
def list_all_courses(session: Session = Depends(get_session)):
    return session.exec(select(Course).order_by(Course.id.desc())).all()


@router.post("/admin/courses", response_model=Course, dependencies=[Depends(require_admin)])
def create_course(body: CourseIn, session: Session = Depends(get_session)):
    cat = session.get(CourseCategory, body.category_id)
    if not cat:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "课程类型不存在")
    course = Course(**body.model_dump())
    session.add(course)
    session.commit()
    session.refresh(course)
    return course


@router.patch("/admin/courses/{cid}", response_model=Course, dependencies=[Depends(require_admin)])
def update_course(cid: int, body: CourseUpdate, session: Session = Depends(get_session)):
    course = session.get(Course, cid)
    if not course:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "课程不存在")
    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(course, k, v)
    session.add(course)
    session.commit()
    session.refresh(course)
    return course


# ============ 教练（简版：先用 User+Coach） ============

class CoachIn(BaseModel):
    user_id: int
    title: Optional[str] = None
    bio: Optional[str] = None
    specialties: Optional[str] = None
    is_active: bool = True


@router.get("/coaches", response_model=List[Coach])
def list_coaches(session: Session = Depends(get_session), _: User = Depends(get_current_user)):
    return session.exec(select(Coach).where(Coach.is_active == True).order_by(Coach.id.desc())).all()


@router.post("/admin/coaches", response_model=Coach, dependencies=[Depends(require_admin)])
def create_coach(body: CoachIn, session: Session = Depends(get_session)):
    user = session.get(User, body.user_id)
    if not user:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "用户不存在")
    if user.role != UserRole.coach:
        user.role = UserRole.coach    # 自动提升为教练角色
        session.add(user)
    if session.exec(select(Coach).where(Coach.user_id == body.user_id)).first():
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "该用户已经是教练")
    coach = Coach(**body.model_dump())
    session.add(coach)
    session.commit()
    session.refresh(coach)
    return coach


# ============ 排课（ClassSession） ============

class SessionIn(BaseModel):
    course_id: int
    coach_id: Optional[int] = None
    start_at: datetime
    end_at: Optional[datetime] = None    # 不填则按 course.duration_minutes 推
    capacity: Optional[int] = None       # 不填则按 course.capacity
    room: Optional[str] = None
    note: Optional[str] = None


class BatchSessionIn(BaseModel):
    """批量排课 — 例如"每周一三五 19:00 流瑜伽"，自动生成 N 周。"""
    course_id: int
    coach_id: Optional[int] = None
    weekdays: List[int] = Field(description="0=周一 ... 6=周日")
    time_of_day: str = Field(pattern=r"^\d{2}:\d{2}$", description="HH:MM")
    start_date: datetime = Field(description="第一周的起始日期（含）")
    weeks: int = Field(default=4, ge=1, le=52)
    capacity: Optional[int] = None
    room: Optional[str] = None


class SessionOut(BaseModel):
    id: int
    course_id: int
    coach_id: Optional[int] = None
    start_at: datetime
    end_at: datetime
    capacity: int
    booked_count: int
    room: Optional[str] = None
    status: ClassSessionStatus
    note: Optional[str] = None

    model_config = {"from_attributes": True}


@router.get("/sessions", response_model=List[SessionOut])
def list_sessions(
    start: Optional[datetime] = Query(default=None, description="起始时间（含）"),
    end: Optional[datetime] = Query(default=None, description="结束时间（不含）"),
    course_id: Optional[int] = None,
    coach_id: Optional[int] = None,
    category_id: Optional[int] = None,
    only_open: bool = Query(default=False, description="只看未满未结的"),
    session: Session = Depends(get_session),
    _: User = Depends(get_current_user),
):
    """
    会员/前台都用这个看课表。默认 7 天内的。
    P0-6: 进入前先 lazy settle 一遍，把已结束课节状态推进。
    """
    session_svc.settle_past_sessions(session)
    if not start:
        start = datetime.utcnow()
    if not end:
        end = start + timedelta(days=7)
    stmt = select(ClassSession).where(ClassSession.start_at >= start, ClassSession.start_at < end)
    if course_id is not None:
        stmt = stmt.where(ClassSession.course_id == course_id)
    if coach_id is not None:
        stmt = stmt.where(ClassSession.coach_id == coach_id)
    if category_id is not None:
        stmt = stmt.join(Course, Course.id == ClassSession.course_id).where(Course.category_id == category_id)
    if only_open:
        stmt = stmt.where(ClassSession.status == ClassSessionStatus.scheduled)
    return session.exec(stmt.order_by(ClassSession.start_at)).all()


@router.post("/admin/sessions", response_model=SessionOut, dependencies=[Depends(require_staff)])
def create_session(body: SessionIn, session: Session = Depends(get_session)):
    course = session.get(Course, body.course_id)
    if not course:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "课程不存在")
    capacity = body.capacity if body.capacity is not None else course.capacity
    end_at = body.end_at or (body.start_at + timedelta(minutes=course.duration_minutes))
    if body.coach_id is not None:
        if not session.get(Coach, body.coach_id):
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "教练不存在")
    cs = ClassSession(
        course_id=course.id,
        coach_id=body.coach_id,
        start_at=body.start_at,
        end_at=end_at,
        capacity=capacity,
        room=body.room,
        note=body.note,
    )
    session.add(cs)
    session.commit()
    session.refresh(cs)
    return cs


@router.post("/admin/sessions/batch", response_model=List[SessionOut], dependencies=[Depends(require_staff)])
def batch_create_sessions(body: BatchSessionIn, session: Session = Depends(get_session)):
    """循环排课：例如周一三五每周 19:00 流瑜伽，连排 4 周。"""
    course = session.get(Course, body.course_id)
    if not course:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "课程不存在")
    if body.coach_id is not None and not session.get(Coach, body.coach_id):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "教练不存在")
    hh, mm = (int(x) for x in body.time_of_day.split(":"))
    capacity = body.capacity if body.capacity is not None else course.capacity
    duration = course.duration_minutes

    created: List[ClassSession] = []
    for w in range(body.weeks):
        week_start = body.start_date + timedelta(days=7 * w)
        for wd in body.weekdays:
            base = week_start + timedelta(days=(wd - week_start.weekday()) % 7)
            start_at = base.replace(hour=hh, minute=mm, second=0, microsecond=0)
            cs = ClassSession(
                course_id=course.id,
                coach_id=body.coach_id,
                start_at=start_at,
                end_at=start_at + timedelta(minutes=duration),
                capacity=capacity,
                room=body.room,
            )
            session.add(cs)
            created.append(cs)
    session.commit()
    for c in created:
        session.refresh(c)
    return created


@router.patch("/admin/sessions/{sid}", response_model=SessionOut, dependencies=[Depends(require_staff)])
def update_session(
    sid: int,
    body: SessionIn,
    session: Session = Depends(get_session),
):
    cs = session.get(ClassSession, sid)
    if not cs:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "排课不存在")
    if cs.booked_count > 0 and (body.capacity is not None and body.capacity < cs.booked_count):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "新容量不能小于已预约人数")
    cs.course_id = body.course_id
    cs.coach_id = body.coach_id
    cs.start_at = body.start_at
    if body.end_at:
        cs.end_at = body.end_at
    if body.capacity is not None:
        cs.capacity = body.capacity
    cs.room = body.room
    cs.note = body.note
    session.add(cs)
    session.commit()
    session.refresh(cs)
    return cs


@router.post("/admin/sessions/{sid}/cancel")
def cancel_session(
    sid: int,
    operator: User = Depends(require_staff),
    session: Session = Depends(get_session),
):
    """取消整节课 — 后续 booking 模块会处理给已预约会员返还卡次。MVP 这里先标状态。"""
    cs = session.get(ClassSession, sid)
    if not cs:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "排课不存在")
    cs.status = ClassSessionStatus.cancelled
    session.add(cs)
    audit_svc.log(session, operator, "session.cancel", "session", cs.id)
    session.commit()
    return {"ok": True}
