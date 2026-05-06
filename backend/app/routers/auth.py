from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlmodel import Session, select
from ..database import get_session
from ..models import User, UserRole
from ..core.security import hash_password, verify_password, create_access_token
from ..core.deps import get_current_user

router = APIRouter(prefix="/api/auth", tags=["auth"])


class LoginIn(BaseModel):
    phone: str = Field(min_length=4, max_length=20)
    password: str = Field(min_length=4, max_length=64)


class RegisterIn(BaseModel):
    phone: str = Field(min_length=4, max_length=20)
    password: str = Field(min_length=4, max_length=64)
    name: str = Field(min_length=1, max_length=64)


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: dict


def _user_public(u: User) -> dict:
    return {"id": u.id, "phone": u.phone, "name": u.name, "role": u.role.value, "avatar": u.avatar}


@router.post("/register", response_model=TokenOut)
def register(body: RegisterIn, session: Session = Depends(get_session)):
    """会员自助注册（H5 端用），新用户默认 role=member"""
    existing = session.exec(select(User).where(User.phone == body.phone)).first()
    if existing:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "该手机号已注册")
    user = User(
        phone=body.phone,
        password_hash=hash_password(body.password),
        name=body.name,
        role=UserRole.member,
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    token = create_access_token(user.id, user.role.value)
    return TokenOut(access_token=token, user=_user_public(user))


@router.post("/login", response_model=TokenOut)
def login(body: LoginIn, session: Session = Depends(get_session)):
    user = session.exec(select(User).where(User.phone == body.phone)).first()
    if not user or not user.is_active:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "账号或密码错误")
    if not verify_password(body.password, user.password_hash or ""):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "账号或密码错误")
    token = create_access_token(user.id, user.role.value)
    return TokenOut(access_token=token, user=_user_public(user))


@router.get("/me")
def me(current: User = Depends(get_current_user)):
    return _user_public(current)
