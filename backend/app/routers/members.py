from datetime import datetime
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlmodel import Session, select
from sqlalchemy import func, or_
from ..database import get_session
from ..models import User, UserRole
from ..core.deps import get_current_user, require_admin, require_staff
from ..core.security import hash_password, verify_password
from ..services import audit as audit_svc

router = APIRouter(prefix="/api", tags=["members"])


class MemberCreate(BaseModel):
    phone: str = Field(min_length=4, max_length=20)
    name: str = Field(min_length=1, max_length=64)
    password: Optional[str] = None        # 不填则用手机号后 6 位
    role: UserRole = UserRole.member
    gender: Optional[str] = Field(default=None, max_length=8)
    birthday: Optional[datetime] = None
    note: Optional[str] = Field(default=None, max_length=500)
    emergency_contact_name: Optional[str] = Field(default=None, max_length=64)
    emergency_contact_phone: Optional[str] = Field(default=None, max_length=20)
    health_note: Optional[str] = Field(default=None, max_length=2000)
    tags: Optional[str] = Field(default=None, max_length=255)


class MemberUpdate(BaseModel):
    name: Optional[str] = Field(default=None, max_length=64)
    avatar: Optional[str] = Field(default=None, max_length=255)
    gender: Optional[str] = Field(default=None, max_length=8)
    birthday: Optional[datetime] = None
    note: Optional[str] = Field(default=None, max_length=500)
    emergency_contact_name: Optional[str] = Field(default=None, max_length=64)
    emergency_contact_phone: Optional[str] = Field(default=None, max_length=20)
    health_note: Optional[str] = Field(default=None, max_length=2000)
    tags: Optional[str] = Field(default=None, max_length=255)


class SelfUpdate(BaseModel):
    name: Optional[str] = Field(default=None, max_length=64)
    avatar: Optional[str] = Field(default=None, max_length=255)
    gender: Optional[str] = Field(default=None, max_length=8)
    birthday: Optional[datetime] = None
    emergency_contact_name: Optional[str] = Field(default=None, max_length=64)
    emergency_contact_phone: Optional[str] = Field(default=None, max_length=20)
    health_note: Optional[str] = Field(default=None, max_length=2000)


class PasswordReset(BaseModel):
    new_password: str = Field(min_length=4, max_length=64)


class PasswordChange(BaseModel):
    old_password: str = Field(min_length=1, max_length=64)
    new_password: str = Field(min_length=4, max_length=64)


class MemberOut(BaseModel):
    id: int
    phone: str
    name: str
    role: UserRole
    avatar: Optional[str] = None
    gender: Optional[str] = None
    birthday: Optional[datetime] = None
    note: Optional[str] = None
    emergency_contact_name: Optional[str] = None
    emergency_contact_phone: Optional[str] = None
    health_note: Optional[str] = None
    tags: Optional[str] = None
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class MemberPage(BaseModel):
    items: List[MemberOut]
    total: int
    page: int
    size: int


# ===== 会员自助 =====

@router.patch("/me", response_model=MemberOut)
def update_me(
    body: SelfUpdate,
    current: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    data = body.model_dump(exclude_unset=True)
    for k, v in data.items():
        setattr(current, k, v)
    session.add(current)
    session.commit()
    session.refresh(current)
    return current


@router.post("/me/change-password")
def change_my_password(
    body: PasswordChange,
    current: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    """所有角色都用这个改自己的密码（包括管理员/前台/教练/会员）"""
    if not verify_password(body.old_password, current.password_hash or ""):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "原密码错误")
    if body.old_password == body.new_password:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "新密码不能与原密码相同")
    current.password_hash = hash_password(body.new_password)
    session.add(current)
    audit_svc.log(session, current, "user.change_password", "user", current.id)
    session.commit()
    return {"ok": True}


# ===== 后台 CRUD =====

@router.get("/admin/members", response_model=MemberPage, dependencies=[Depends(require_staff)])
def list_members(
    q: Optional[str] = None,
    is_active: Optional[bool] = None,
    tag: Optional[str] = None,           # 标签 LIKE 过滤
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=200),
    session: Session = Depends(get_session),
):
    """只列会员（role=member）。员工/教练分别在 /admin/staff、/admin/coaches。"""
    stmt = select(User).where(User.role == UserRole.member)
    cnt_stmt = select(func.count(User.id)).where(User.role == UserRole.member)
    conds = []
    if q:
        like = f"%{q}%"
        conds.append(or_(User.phone.like(like), User.name.like(like)))
    if is_active is not None:
        conds.append(User.is_active == is_active)
    if tag:
        conds.append(User.tags.like(f"%{tag}%"))
    for c in conds:
        stmt = stmt.where(c)
        cnt_stmt = cnt_stmt.where(c)
    total = session.exec(cnt_stmt).one()
    items = session.exec(
        stmt.order_by(User.id.desc()).offset((page - 1) * size).limit(size)
    ).all()
    return MemberPage(items=items, total=total, page=page, size=size)


@router.post("/admin/members", response_model=MemberOut)
def create_member(
    body: MemberCreate,
    operator: User = Depends(require_staff),    # admin / staff 都可建会员
    session: Session = Depends(get_session),
):
    """创建会员（角色强制为 member）。建员工请用 /admin/staff，建教练请用 /admin/coaches。"""
    if body.role != UserRole.member:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "本接口只能创建会员。建员工请用 /admin/staff，建教练请用 /admin/coaches",
        )
    if session.exec(select(User).where(User.phone == body.phone)).first():
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "该手机号已存在")
    pwd = body.password or (body.phone[-6:] if len(body.phone) >= 6 else body.phone)
    data = body.model_dump(exclude={"password"})
    data["role"] = UserRole.member          # 强制 member
    user = User(**data, password_hash=hash_password(pwd))
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


@router.get("/admin/members/{member_id}", response_model=MemberOut, dependencies=[Depends(require_staff)])
def get_member(member_id: int, session: Session = Depends(get_session)):
    user = session.get(User, member_id)
    if not user:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "会员不存在")
    return user


@router.patch("/admin/members/{member_id}", response_model=MemberOut, dependencies=[Depends(require_admin)])
def update_member(member_id: int, body: MemberUpdate, session: Session = Depends(get_session)):
    user = session.get(User, member_id)
    if not user:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "会员不存在")
    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(user, k, v)
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


@router.post("/admin/members/{member_id}/deactivate")
def deactivate_member(
    member_id: int,
    operator: User = Depends(require_admin),
    session: Session = Depends(get_session),
):
    user = session.get(User, member_id)
    if not user:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "会员不存在")
    user.is_active = False
    session.add(user)
    audit_svc.log(session, operator, "user.deactivate", "user", user.id)
    session.commit()
    return {"ok": True}


@router.post("/admin/members/{member_id}/activate")
def activate_member(
    member_id: int,
    operator: User = Depends(require_admin),
    session: Session = Depends(get_session),
):
    user = session.get(User, member_id)
    if not user:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "会员不存在")
    user.is_active = True
    session.add(user)
    audit_svc.log(session, operator, "user.activate", "user", user.id)
    session.commit()
    return {"ok": True}


@router.post("/admin/members/{member_id}/reset-password")
def reset_password(
    member_id: int,
    body: PasswordReset,
    operator: User = Depends(require_admin),
    session: Session = Depends(get_session),
):
    user = session.get(User, member_id)
    if not user:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "会员不存在")
    user.password_hash = hash_password(body.new_password)
    session.add(user)
    audit_svc.log(session, operator, "user.reset_password", "user", user.id)
    session.commit()
    return {"ok": True}
