from datetime import datetime, timedelta
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlmodel import Session, select
from ..database import get_session
from ..models import (
    User, UserRole,
    CouponTemplate, Coupon, CouponType, CouponStatus,
)
from ..core.deps import require_admin, require_staff, get_current_user
from ..services import audit as audit_svc

router = APIRouter(prefix="/api", tags=["coupons"])


# ============ 模板 CRUD ============

class CouponTemplateIn(BaseModel):
    name: str = Field(min_length=1, max_length=64)
    type: CouponType
    value: int = Field(ge=0)
    min_amount: int = Field(default=0, ge=0)
    valid_days: int = Field(default=30, ge=1, le=3650)
    applicable_category_id: Optional[int] = None
    description: Optional[str] = None
    is_active: bool = True


@router.get("/admin/coupon-templates", response_model=List[CouponTemplate], dependencies=[Depends(require_admin)])
def list_templates(session: Session = Depends(get_session)):
    return session.exec(select(CouponTemplate).order_by(CouponTemplate.id.desc())).all()


@router.post("/admin/coupon-templates", response_model=CouponTemplate, dependencies=[Depends(require_admin)])
def create_template(body: CouponTemplateIn, session: Session = Depends(get_session)):
    tmpl = CouponTemplate(**body.model_dump())
    session.add(tmpl)
    session.commit()
    session.refresh(tmpl)
    return tmpl


@router.patch("/admin/coupon-templates/{tid}", response_model=CouponTemplate, dependencies=[Depends(require_admin)])
def update_template(tid: int, body: CouponTemplateIn, session: Session = Depends(get_session)):
    tmpl = session.get(CouponTemplate, tid)
    if not tmpl:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "模板不存在")
    for k, v in body.model_dump().items():
        setattr(tmpl, k, v)
    session.add(tmpl)
    session.commit()
    session.refresh(tmpl)
    return tmpl


# ============ 发券 ============

class GrantIn(BaseModel):
    template_id: int
    member_ids: List[int]                  # 一次发给多个会员


@router.post("/admin/coupons/grant", dependencies=[Depends(require_admin)])
def grant_coupons(
    body: GrantIn,
    operator: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    tmpl = session.get(CouponTemplate, body.template_id)
    if not tmpl or not tmpl.is_active:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "模板不存在或已停用")
    valid_until = datetime.utcnow() + timedelta(days=tmpl.valid_days) if tmpl.valid_days > 0 else None
    granted = 0
    for mid in body.member_ids:
        m = session.get(User, mid)
        if not m or m.role != UserRole.member:
            continue
        c = Coupon(
            template_id=tmpl.id, member_id=mid,
            type=tmpl.type, name=tmpl.name, value=tmpl.value,
            min_amount=tmpl.min_amount,
            valid_until=valid_until,
            applicable_category_id=tmpl.applicable_category_id,
        )
        session.add(c)
        granted += 1
    audit_svc.log(session, operator, "coupon.grant", "coupon_template", tmpl.id, {
        "template": tmpl.name, "granted": granted,
    })
    session.commit()
    return {"ok": True, "granted": granted}


# ============ 会员看自己的券 ============

@router.get("/me/coupons", response_model=List[Coupon])
def my_coupons(
    status_: Optional[CouponStatus] = Query(default=None, alias="status"),
    current: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    # 自动过期一遍
    now = datetime.utcnow()
    expired = session.exec(
        select(Coupon).where(
            Coupon.member_id == current.id,
            Coupon.status == CouponStatus.unused,
            Coupon.valid_until < now,
        )
    ).all()
    for c in expired:
        c.status = CouponStatus.expired
        session.add(c)
    if expired:
        session.commit()

    stmt = select(Coupon).where(Coupon.member_id == current.id)
    if status_:
        stmt = stmt.where(Coupon.status == status_)
    return session.exec(stmt.order_by(Coupon.id.desc())).all()


@router.get("/admin/coupons", response_model=List[Coupon], dependencies=[Depends(require_staff)])
def list_all_coupons(
    member_id: Optional[int] = None,
    template_id: Optional[int] = None,
    status_: Optional[CouponStatus] = Query(default=None, alias="status"),
    session: Session = Depends(get_session),
):
    stmt = select(Coupon)
    if member_id is not None:
        stmt = stmt.where(Coupon.member_id == member_id)
    if template_id is not None:
        stmt = stmt.where(Coupon.template_id == template_id)
    if status_:
        stmt = stmt.where(Coupon.status == status_)
    return session.exec(stmt.order_by(Coupon.id.desc()).limit(500)).all()
