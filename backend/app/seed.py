"""
初始化数据：管理员账号、课程类型、几节示例课程、几张示例卡种、工作室配置。
重复执行安全（已存在则跳过）。

运行：python -m app.seed
"""
import sys
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

from datetime import datetime
from sqlmodel import Session, select
from .config import settings
from .database import engine, init_db
from .models import (
    User, UserRole,
    CourseCategory, Course,
    CardTemplate, CardType,
    StudioConfig,
)
from .core.security import hash_password


def seed():
    init_db()
    with Session(engine) as s:
        # 1. 管理员
        admin = s.exec(select(User).where(User.phone == settings.admin_phone)).first()
        if not admin:
            admin = User(
                phone=settings.admin_phone,
                password_hash=hash_password(settings.admin_password),
                name="店长",
                role=UserRole.admin,
            )
            s.add(admin)
            print(f"[seed] 管理员已创建：{settings.admin_phone} / {settings.admin_password}")
        else:
            print("[seed] 管理员已存在，跳过")

        # 2. 工作室配置（单行）
        cfg = s.exec(select(StudioConfig)).first()
        if not cfg:
            s.add(StudioConfig(name=settings.studio_name))
            print(f"[seed] 工作室配置已创建：{settings.studio_name}")

        # 3. 课程类型（4 种常见）
        cats_data = [
            ("团课", "group", 1, 12, True, 60, 24, True, 1),
            ("私教", "private", 1, 1, True, 60, 2, True, 2),
            ("双人课", "duet", 2, 2, True, 60, 12, True, 3),
            ("小班", "semi", 2, 6, True, 60, 12, True, 4),
        ]
        cat_by_code = {}
        for name, code, mn, mx, rc, dur, cancel, ns, sort in cats_data:
            cat = s.exec(select(CourseCategory).where(CourseCategory.code == code)).first()
            if not cat:
                cat = CourseCategory(
                    name=name, code=code,
                    min_capacity=mn, max_capacity=mx,
                    requires_coach=rc, default_duration_minutes=dur,
                    cancel_deadline_hours=cancel, no_show_deduct=ns,
                    sort_order=sort,
                )
                s.add(cat)
                s.flush()
                print(f"[seed] 课程类型已创建：{name}")
            cat_by_code[code] = cat

        # 4. 示例课程
        courses_data = [
            ("group", "流瑜伽", "舒缓流动，适合所有水平", 60, 12, 1, 8800),
            ("group", "普拉提团课", "塾上普拉提，提升核心控制", 60, 12, 1, 9800),
            ("private", "普拉提器械私教1v1", "床/椅/梯桶器械私教", 60, 1, 1, 38000),
        ]
        for code, cname, desc, dur, cap, credit, price in courses_data:
            cat = cat_by_code.get(code)
            if not cat:
                continue
            existing = s.exec(select(Course).where(Course.name == cname)).first()
            if not existing:
                s.add(Course(
                    category_id=cat.id, name=cname, description=desc,
                    duration_minutes=dur, capacity=cap, credit_cost=credit, price=price,
                ))
                print(f"[seed] 示例课程已创建：{cname}")

        # 5. 示例卡种
        cards_data = [
            ("10 次团课卡", CardType.times, 88000, 10, 0, 180, None, "group", "10 次任选团课，180 天有效"),
            ("月卡（团课不限次）", CardType.period, 68000, 0, 0, 30, None, "group", "30 天内任意约团课"),
            ("私教 10 次包", CardType.package, 380000, 10, 0, 365, None, "private", "私教器械 10 节，1 年内有效"),
            ("储值卡 1000 元", CardType.stored, 100000, 0, 100000, 0, None, None, "充 1000 元，按价扣"),
        ]
        for name, ctype, price, credits, balance, valid_days, daily_limit, cat_code, desc in cards_data:
            existing = s.exec(select(CardTemplate).where(CardTemplate.name == name)).first()
            if existing:
                continue
            cat_id = cat_by_code[cat_code].id if cat_code else None
            s.add(CardTemplate(
                name=name, type=ctype, price=price,
                initial_credits=credits, initial_balance=balance,
                valid_days=valid_days, daily_limit=daily_limit or 0,
                applicable_category_id=cat_id, description=desc,
            ))
            print(f"[seed] 卡种已创建：{name}")

        s.commit()
    print("[seed] 完成。")


if __name__ == "__main__":
    seed()
