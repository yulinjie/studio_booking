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
    """新建教练 — 直接传手机号 + 姓名一步到位
    若该手机号已注册：
      - 若已是 coach 角色 → 报 400
      - 若是其他角色（admin/staff/member）→ 提升为 coach 并保留原账号
    若手机号没注册过 → 新建 User（role=coach）+ Coach 记录
    """
    phone: str = Field(min_length=4, max_length=20)
    name: str = Field(min_length=1, max_length=64)
    password: Optional[str] = None        # 不填 = 手机号后 6 位
    title: Optional[str] = None
    bio: Optional[str] = None
    specialties: Optional[str] = None
    base_salary: int = 0
    pay_per_session: int = 0
    commission_bps: int = 0
    pay_per_attendee: int = 0
    is_active: bool = True


class CoachUpdate(BaseModel):
    title: Optional[str] = None
    bio: Optional[str] = None
    specialties: Optional[str] = None
    base_salary: Optional[int] = None
    pay_per_session: Optional[int] = None
    commission_bps: Optional[int] = None
    pay_per_attendee: Optional[int] = None
    is_active: Optional[bool] = None


@router.get("/coaches", response_model=List[Coach])
def list_coaches(session: Session = Depends(get_session), _: User = Depends(get_current_user)):
    return session.exec(select(Coach).where(Coach.is_active == True).order_by(Coach.id.desc())).all()


class CoachProfile(BaseModel):
    """教练公开主页 — 给会员端看的"""
    id: int
    user_id: int
    name: str
    avatar: Optional[str] = None
    title: Optional[str] = None
    bio: Optional[str] = None
    specialties: Optional[str] = None
    is_active: bool

    avg_rating: Optional[float] = None         # 平均评分（保留 1 位小数）
    rating_count: int                          # 评分人数
    total_sessions_taught: int                 # 历史带过的课节数（finished）
    upcoming_sessions: List[dict]              # 未来 14 天的可约课节（含 course/room/cap/booked）


@router.get("/coaches/{coach_id}/profile", response_model=CoachProfile)
def get_coach_profile(
    coach_id: int,
    session: Session = Depends(get_session),
    _: User = Depends(get_current_user),
):
    from datetime import datetime, timedelta
    from sqlalchemy import func as sa_func
    from ..models import Booking, BookingStatus, Evaluation

    coach = session.get(Coach, coach_id)
    if not coach:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "教练不存在")
    user = session.get(User, coach.user_id)

    # 评分：取该教练所有 finished 课的所有 evaluation 的均值
    # Evaluation.booking → Booking → ClassSession.coach_id
    eval_rows = session.exec(
        select(Evaluation, Booking, ClassSession)
        .join(Booking, Booking.id == Evaluation.booking_id)
        .join(ClassSession, ClassSession.id == Booking.session_id)
        .where(ClassSession.coach_id == coach_id)
    ).all()
    avg_rating = None
    rating_count = len(eval_rows)
    if rating_count > 0:
        avg_rating = round(sum(e[0].rating for e in eval_rows) / rating_count, 1)

    # 历史已结课节数
    total_sessions = session.exec(
        select(sa_func.count(ClassSession.id)).where(
            ClassSession.coach_id == coach_id,
            ClassSession.status == ClassSessionStatus.finished,
        )
    ).one()

    # 未来 14 天可约课节
    now = datetime.utcnow()
    end = now + timedelta(days=14)
    upcoming = session.exec(
        select(ClassSession).where(
            ClassSession.coach_id == coach_id,
            ClassSession.start_at >= now,
            ClassSession.start_at < end,
            ClassSession.status == ClassSessionStatus.scheduled,
        ).order_by(ClassSession.start_at)
    ).all()
    courses_map = {c.id: c for c in session.exec(select(Course)).all()}
    upcoming_out = [{
        "id": s.id,
        "course_id": s.course_id,
        "course_name": (courses_map.get(s.course_id) or Course(name="?")).name if courses_map.get(s.course_id) else "?",
        "start_at": s.start_at.isoformat(),
        "end_at": s.end_at.isoformat(),
        "capacity": s.capacity,
        "booked_count": s.booked_count,
        "room": s.room,
    } for s in upcoming]

    return CoachProfile(
        id=coach.id,
        user_id=coach.user_id,
        name=user.name if user else "?",
        avatar=user.avatar if user else None,
        title=coach.title,
        bio=coach.bio,
        specialties=coach.specialties,
        is_active=coach.is_active,
        avg_rating=avg_rating,
        rating_count=rating_count,
        total_sessions_taught=total_sessions,
        upcoming_sessions=upcoming_out,
    )


@router.post("/admin/coaches", response_model=Coach, dependencies=[Depends(require_admin)])
def create_coach(body: CoachIn, session: Session = Depends(get_session)):
    from ..core.security import hash_password

    existing = session.exec(select(User).where(User.phone == body.phone)).first()
    if existing:
        # 已经是教练
        if existing.role == UserRole.coach:
            existing_coach = session.exec(select(Coach).where(Coach.user_id == existing.id)).first()
            if existing_coach:
                raise HTTPException(status.HTTP_400_BAD_REQUEST, f"{body.phone} 已经是教练")
            # 极少数情况：role=coach 但没 Coach 记录，下面给他补
            user = existing
        else:
            # 其他角色 → 提升为教练
            existing.role = UserRole.coach
            existing.name = body.name        # 同步更新姓名
            session.add(existing)
            user = existing
    else:
        # 新建 User
        pwd = body.password or (body.phone[-6:] if len(body.phone) >= 6 else body.phone)
        user = User(
            phone=body.phone,
            name=body.name,
            role=UserRole.coach,
            password_hash=hash_password(pwd),
        )
        session.add(user)
        session.flush()

    coach = Coach(
        user_id=user.id,
        title=body.title, bio=body.bio, specialties=body.specialties,
        base_salary=body.base_salary, pay_per_session=body.pay_per_session,
        commission_bps=body.commission_bps, pay_per_attendee=body.pay_per_attendee,
        is_active=body.is_active,
    )
    session.add(coach)
    session.commit()
    session.refresh(coach)
    return coach


@router.patch("/admin/coaches/{coach_id}", response_model=Coach, dependencies=[Depends(require_admin)])
def update_coach(coach_id: int, body: CoachUpdate, session: Session = Depends(get_session)):
    coach = session.get(Coach, coach_id)
    if not coach:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "教练不存在")
    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(coach, k, v)
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


def _detect_conflicts(
    session: Session,
    start_at: datetime,
    end_at: datetime,
    coach_id: Optional[int],
    room: Optional[str],
    exclude_session_id: Optional[int] = None,
) -> List[dict]:
    """返回与该时间段冲突的现有 scheduled 课节（同教练或同教室）"""
    stmt = select(ClassSession).where(
        ClassSession.status == ClassSessionStatus.scheduled,
        ClassSession.start_at < end_at,
        ClassSession.end_at > start_at,
    )
    if exclude_session_id is not None:
        stmt = stmt.where(ClassSession.id != exclude_session_id)
    overlaps = session.exec(stmt).all()
    courses_map = {c.id: c for c in session.exec(select(Course)).all()}
    out = []
    for o in overlaps:
        is_coach_clash = coach_id is not None and o.coach_id == coach_id
        is_room_clash = bool(room and o.room and o.room == room)
        if not (is_coach_clash or is_room_clash):
            continue
        c = courses_map.get(o.course_id)
        out.append({
            "id": o.id,
            "course_name": c.name if c else "?",
            "start_at": o.start_at.isoformat(),
            "end_at": o.end_at.isoformat(),
            "room": o.room,
            "coach_id": o.coach_id,
            "reason": "教练" if is_coach_clash else "教室",
        })
    return out


@router.post("/admin/sessions/check-conflict", dependencies=[Depends(require_staff)])
def check_session_conflict(body: SessionIn, session: Session = Depends(get_session)):
    """干跑检查 — 不真创建，只看会不会冲突。前端排课前调一下。"""
    course = session.get(Course, body.course_id)
    if not course:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "课程不存在")
    end_at = body.end_at or (body.start_at + timedelta(minutes=course.duration_minutes))
    conflicts = _detect_conflicts(session, body.start_at, end_at, body.coach_id, body.room)
    return {"conflicts": conflicts, "ok": not conflicts}


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
    conflicts = _detect_conflicts(session, body.start_at, end_at, body.coach_id, body.room)
    if conflicts:
        c = conflicts[0]
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            f"{c['reason']}冲突：{c['course_name']} {c['start_at'][:16].replace('T',' ')}（room={c['room']}）",
        )
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


class CloneRangeIn(BaseModel):
    """克隆指定时间区间的所有 scheduled 排课到目标偏移天数"""
    from_start: datetime          # 源区间起（含）
    from_end: datetime            # 源区间止（不含）
    offset_days: int              # 目标 = 源 + offset 天（如 7 = 下周同时间）
    course_ids: Optional[List[int]] = None       # 可选过滤；空 = 全部
    skip_finished: bool = True    # 跳过已结/已取消的源
    only_status: List[ClassSessionStatus] = [ClassSessionStatus.scheduled, ClassSessionStatus.finished]


class CloneResult(BaseModel):
    cloned: int
    skipped: int
    new_session_ids: List[int]


@router.post("/admin/sessions/clone-range", response_model=CloneResult, dependencies=[Depends(require_staff)])
def clone_range(body: CloneRangeIn, session: Session = Depends(get_session)):
    """
    例如克隆"本周（5-7~5-14）"到下周：from_start=2026-05-07, from_end=2026-05-14, offset_days=7
    返回新建的 session_id 列表。教练 / 教室 / 容量 / 课程都保留。
    """
    stmt = select(ClassSession).where(
        ClassSession.start_at >= body.from_start,
        ClassSession.start_at < body.from_end,
    )
    if body.course_ids:
        stmt = stmt.where(ClassSession.course_id.in_(body.course_ids))

    sources = session.exec(stmt).all()
    new_ids = []
    skipped = 0
    delta = timedelta(days=body.offset_days)

    for src in sources:
        if body.skip_finished and src.status not in body.only_status:
            skipped += 1
            continue
        new_session = ClassSession(
            course_id=src.course_id,
            coach_id=src.coach_id,
            start_at=src.start_at + delta,
            end_at=src.end_at + delta,
            capacity=src.capacity,
            booked_count=0,
            room=src.room,
            note=src.note,
            status=ClassSessionStatus.scheduled,
        )
        session.add(new_session)
        session.flush()
        new_ids.append(new_session.id)

    session.commit()
    return CloneResult(cloned=len(new_ids), skipped=skipped, new_session_ids=new_ids)


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
