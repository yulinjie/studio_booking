"""
会员成长系统：连续打卡、累计课时、徽章。
所有数据从 Booking + ClassSession 实时聚合，无新表。
"""
from datetime import datetime, timedelta
from typing import List, Optional
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlmodel import Session, select
from ..database import get_session
from ..models import User, Booking, BookingStatus, ClassSession, Course
from ..core.deps import get_current_user

router = APIRouter(prefix="/api", tags=["growth"])


# 徽章定义：按门槛解锁
BADGES = [
    # (key, name, emoji, condition_key, threshold, description)
    ("first_class",   "初次见面",   "🌱", "total_attended",   1,   "完成第一节课"),
    ("ten_classes",   "入门",       "🎋", "total_attended",   10,  "累计 10 节"),
    ("fifty_classes", "持之以恒",   "🌳", "total_attended",   50,  "累计 50 节"),
    ("hundred",       "老学员",     "🏆", "total_attended",   100, "累计 100 节"),
    ("streak_2w",     "坚持者",     "🔥", "current_streak_weeks", 2,  "连续 2 周打卡"),
    ("streak_4w",     "自律",       "💎", "current_streak_weeks", 4,  "连续 4 周打卡"),
    ("streak_12w",    "习惯成自然", "⭐", "current_streak_weeks", 12, "连续 12 周打卡"),
    ("hours_50",      "精进",       "🎖", "practiced_hours",  50,  "累计 50 小时"),
    ("hours_100",     "资深",       "👑", "practiced_hours",  100, "累计 100 小时"),
]


def _compute_weekly_streak(attended_weeks: List[str]) -> int:
    """attended_weeks: 该会员有过 attended 的周（'YYYY-WW' 格式）, 倒序排"""
    if not attended_weeks:
        return 0
    weeks_set = set(attended_weeks)
    today = datetime.utcnow()
    # 从这周往前数，连续命中几周
    streak = 0
    cursor = today
    for _ in range(200):  # 最多回溯 200 周
        ywk = cursor.strftime("%Y-%W")
        if ywk in weeks_set:
            streak += 1
            cursor -= timedelta(weeks=1)
        else:
            # 允许这周还没练（看下周也算的话才打破）
            if streak == 0 and cursor.strftime("%Y-%W") == today.strftime("%Y-%W"):
                cursor -= timedelta(weeks=1)
                continue
            break
    return streak


class BadgeOut(BaseModel):
    key: str
    name: str
    emoji: str
    description: str
    unlocked: bool
    progress: int           # 当前值
    threshold: int          # 解锁阈值


class GrowthStats(BaseModel):
    total_attended: int           # 累计上课次数
    practiced_minutes: int        # 累计练习分钟
    practiced_hours: int          # 累计小时（向下取整）
    current_streak_weeks: int     # 当前连续周数
    longest_streak_weeks: int     # 历史最长连续周数
    last_attended_at: Optional[datetime] = None
    classes_this_week: int        # 本周已练
    classes_this_month: int       # 本月已练
    next_badge: Optional[BadgeOut] = None      # 下一个待解锁的徽章
    badges: List[BadgeOut] = []


@router.get("/me/growth", response_model=GrowthStats)
def get_my_growth(
    current: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    # 1. 拉所有该会员 attended 的预约 + 关联 session/course
    attended_q = (
        select(Booking, ClassSession, Course)
        .join(ClassSession, ClassSession.id == Booking.session_id)
        .join(Course, Course.id == ClassSession.course_id)
        .where(Booking.member_id == current.id, Booking.status == BookingStatus.attended)
        .order_by(ClassSession.start_at.desc())
    )
    rows = session.exec(attended_q).all()

    total_attended = len(rows)
    practiced_minutes = sum(c.duration_minutes for _b, _s, c in rows)
    practiced_hours = practiced_minutes // 60
    last_attended_at = rows[0][1].start_at if rows else None

    # 2. 本周 / 本月
    now = datetime.utcnow()
    week_start = (now - timedelta(days=now.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    classes_this_week = sum(1 for _b, s, _c in rows if s.start_at >= week_start)
    classes_this_month = sum(1 for _b, s, _c in rows if s.start_at >= month_start)

    # 3. 周连续
    week_keys = sorted({s.start_at.strftime("%Y-%W") for _b, s, _c in rows}, reverse=True)
    current_streak_weeks = _compute_weekly_streak(week_keys)

    # 历史最长连续：把所有周排序，找最长连续段
    longest_streak_weeks = 0
    if week_keys:
        sorted_weeks = sorted(set(week_keys))
        cur = 1
        longest_streak_weeks = 1
        for i in range(1, len(sorted_weeks)):
            y1, w1 = map(int, sorted_weeks[i-1].split("-"))
            y2, w2 = map(int, sorted_weeks[i].split("-"))
            # 简化：周差 = (y2-y1)*53 + (w2-w1)，假设连续相差为 1
            delta = (y2 * 53 + w2) - (y1 * 53 + w1)
            if delta == 1:
                cur += 1
                longest_streak_weeks = max(longest_streak_weeks, cur)
            else:
                cur = 1

    metrics = {
        "total_attended": total_attended,
        "current_streak_weeks": current_streak_weeks,
        "longest_streak_weeks": longest_streak_weeks,
        "practiced_hours": practiced_hours,
    }

    # 4. 徽章
    badges_out: List[BadgeOut] = []
    for key, name, emoji, cond_key, threshold, desc in BADGES:
        progress = metrics.get(cond_key, 0)
        unlocked = progress >= threshold
        badges_out.append(BadgeOut(
            key=key, name=name, emoji=emoji, description=desc,
            unlocked=unlocked, progress=progress, threshold=threshold,
        ))

    # 下一个待解锁徽章：未解锁的里 progress / threshold 比例最高的
    locked = [b for b in badges_out if not b.unlocked]
    next_badge = None
    if locked:
        next_badge = max(locked, key=lambda b: b.progress / max(b.threshold, 1))

    return GrowthStats(
        total_attended=total_attended,
        practiced_minutes=practiced_minutes,
        practiced_hours=practiced_hours,
        current_streak_weeks=current_streak_weeks,
        longest_streak_weeks=longest_streak_weeks,
        last_attended_at=last_attended_at,
        classes_this_week=classes_this_week,
        classes_this_month=classes_this_month,
        next_badge=next_badge,
        badges=badges_out,
    )
