"""
员工管理（admin + staff）— 与会员管理彻底分离

权限规则：
  - 仅 admin 可访问所有 /admin/staff 端点
  - 不允许把自己改成 member 或停用自己（防失锁）
  - 不允许把最后一个 admin 降级 / 停用
"""
from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlmodel import Session, select
from sqlalchemy import func, or_
from ..database import get_session
from ..models import User, UserRole
from ..core.deps import require_admin, get_current_user
from ..core.security import hash_password
from ..services import audit as audit_svc

router = APIRouter(prefix="/api", tags=["staff"])


class StaffCreate(BaseModel):
    phone: str = Field(min_length=4, max_length=20)
    name: str = Field(min_length=1, max_length=64)
    role: UserRole = UserRole.staff               # 默认前台
    password: Optional[str] = None                # 不填则手机号后 6 位
    note: Optional[str] = Field(default=None, max_length=500)


class StaffUpdate(BaseModel):
    name: Optional[str] = None
    role: Optional[UserRole] = None
    note: Optional[str] = None


class StaffOut(BaseModel):
    id: int
    phone: str
    name: str
    role: UserRole
    avatar: Optional[str] = None
    note: Optional[str] = None
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


def _ensure_role_is_employee(role: UserRole):
    if role not in (UserRole.admin, UserRole.staff):
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "员工角色只能是 admin（店长）或 staff（前台）。教练请去 /admin/coaches",
        )


def _count_active_admins(session: Session, exclude_id: Optional[int] = None) -> int:
    stmt = select(func.count(User.id)).where(
        User.role == UserRole.admin, User.is_active == True,
    )
    if exclude_id is not None:
        stmt = stmt.where(User.id != exclude_id)
    return session.exec(stmt).one()


@router.get("/admin/staff", response_model=List[StaffOut], dependencies=[Depends(require_admin)])
def list_staff(
    q: Optional[str] = None,
    role: Optional[UserRole] = None,         # admin / staff
    session: Session = Depends(get_session),
):
    stmt = select(User).where(User.role.in_([UserRole.admin, UserRole.staff]))
    if role is not None:
        _ensure_role_is_employee(role)
        stmt = stmt.where(User.role == role)
    if q:
        like = f"%{q}%"
        stmt = stmt.where(or_(User.phone.like(like), User.name.like(like)))
    return session.exec(stmt.order_by(User.id.desc())).all()


@router.post("/admin/staff", response_model=StaffOut)
def create_staff(
    body: StaffCreate,
    operator: User = Depends(require_admin),
    session: Session = Depends(get_session),
):
    _ensure_role_is_employee(body.role)
    if session.exec(select(User).where(User.phone == body.phone)).first():
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "该手机号已存在")
    pwd = body.password or (body.phone[-6:] if len(body.phone) >= 6 else body.phone)
    user = User(
        phone=body.phone,
        name=body.name,
        role=body.role,
        note=body.note,
        password_hash=hash_password(pwd),
    )
    session.add(user)
    audit_svc.log(session, operator, "staff.create", "user", None, {
        "phone": body.phone, "role": body.role.value,
    })
    session.commit()
    session.refresh(user)
    return user


@router.patch("/admin/staff/{user_id}", response_model=StaffOut)
def update_staff(
    user_id: int,
    body: StaffUpdate,
    operator: User = Depends(require_admin),
    session: Session = Depends(get_session),
):
    user = session.get(User, user_id)
    if not user:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "员工不存在")
    if user.role not in (UserRole.admin, UserRole.staff):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "该用户不是员工，请去对应页编辑")

    data = body.model_dump(exclude_unset=True)
    if "role" in data:
        _ensure_role_is_employee(data["role"])
        # 防失锁：不能把最后一个 admin 改成 staff
        if user.role == UserRole.admin and data["role"] != UserRole.admin:
            if _count_active_admins(session, exclude_id=user.id) == 0:
                raise HTTPException(
                    status.HTTP_400_BAD_REQUEST,
                    "至少要有一位 admin（店长），不能把最后一个降级",
                )
        # 不能改自己的角色
        if user.id == operator.id:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "不能改自己的角色")

    for k, v in data.items():
        setattr(user, k, v)
    session.add(user)
    audit_svc.log(session, operator, "staff.update", "user", user.id, data)
    session.commit()
    session.refresh(user)
    return user


@router.post("/admin/staff/{user_id}/reset-password")
def reset_staff_password(
    user_id: int,
    body: dict,
    operator: User = Depends(require_admin),
    session: Session = Depends(get_session),
):
    new_pwd = body.get("new_password")
    if not new_pwd or len(new_pwd) < 4:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "新密码至少 4 位")
    user = session.get(User, user_id)
    if not user or user.role not in (UserRole.admin, UserRole.staff):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "员工不存在")
    user.password_hash = hash_password(new_pwd)
    session.add(user)
    audit_svc.log(session, operator, "staff.reset_password", "user", user.id)
    session.commit()
    return {"ok": True}


@router.post("/admin/staff/{user_id}/deactivate")
def deactivate_staff(
    user_id: int,
    operator: User = Depends(require_admin),
    session: Session = Depends(get_session),
):
    user = session.get(User, user_id)
    if not user or user.role not in (UserRole.admin, UserRole.staff):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "员工不存在")
    if user.id == operator.id:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "不能停用自己")
    if user.role == UserRole.admin and _count_active_admins(session, exclude_id=user.id) == 0:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "至少要有一位 admin（店长），不能停用最后一个",
        )
    user.is_active = False
    session.add(user)
    audit_svc.log(session, operator, "staff.deactivate", "user", user.id)
    session.commit()
    return {"ok": True}


@router.post("/admin/staff/{user_id}/activate")
def activate_staff(
    user_id: int,
    operator: User = Depends(require_admin),
    session: Session = Depends(get_session),
):
    user = session.get(User, user_id)
    if not user or user.role not in (UserRole.admin, UserRole.staff):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "员工不存在")
    user.is_active = True
    session.add(user)
    audit_svc.log(session, operator, "staff.activate", "user", user.id)
    session.commit()
    return {"ok": True}
