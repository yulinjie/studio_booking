from datetime import datetime
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlmodel import Session, select
from sqlalchemy import func
from ..database import get_session
from ..models import (
    User, UserRole,
    CardTemplate, CardType, MemberCard, CardStatus, CardTransaction,
    PaymentOrder, OrderStatus, PaymentMethod,
)
from ..core.deps import get_current_user, require_admin, require_staff
from ..services import cards as card_svc, audit as audit_svc

router = APIRouter(prefix="/api", tags=["cards"])


# ============ 卡种模板 ============

class CardTemplateIn(BaseModel):
    name: str = Field(min_length=1, max_length=64)
    type: CardType
    price: int = Field(ge=0)                          # 分
    initial_credits: int = Field(default=0, ge=0)
    initial_balance: int = Field(default=0, ge=0)    # 分
    valid_days: int = Field(default=0, ge=0)
    daily_limit: int = Field(default=0, ge=0)
    applicable_category_id: Optional[int] = None
    description: Optional[str] = Field(default=None, max_length=500)
    is_active: bool = True


class CardTemplateUpdate(BaseModel):
    name: Optional[str] = None
    price: Optional[int] = None
    initial_credits: Optional[int] = None
    initial_balance: Optional[int] = None
    valid_days: Optional[int] = None
    daily_limit: Optional[int] = None
    applicable_category_id: Optional[int] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None


@router.get("/card-templates", response_model=List[CardTemplate])
def list_active_templates(session: Session = Depends(get_session), _: User = Depends(get_current_user)):
    """会员端：浏览可购买的卡"""
    return session.exec(select(CardTemplate).where(CardTemplate.is_active == True).order_by(CardTemplate.id.desc())).all()


@router.get("/admin/card-templates", response_model=List[CardTemplate], dependencies=[Depends(require_admin)])
def list_all_templates(session: Session = Depends(get_session)):
    return session.exec(select(CardTemplate).order_by(CardTemplate.id.desc())).all()


@router.post("/admin/card-templates", response_model=CardTemplate, dependencies=[Depends(require_admin)])
def create_template(body: CardTemplateIn, session: Session = Depends(get_session)):
    tmpl = CardTemplate(**body.model_dump())
    session.add(tmpl)
    session.commit()
    session.refresh(tmpl)
    return tmpl


@router.patch("/admin/card-templates/{tid}", response_model=CardTemplate, dependencies=[Depends(require_admin)])
def update_template(tid: int, body: CardTemplateUpdate, session: Session = Depends(get_session)):
    tmpl = session.get(CardTemplate, tid)
    if not tmpl:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "卡种不存在")
    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(tmpl, k, v)
    session.add(tmpl)
    session.commit()
    session.refresh(tmpl)
    return tmpl


@router.delete("/admin/card-templates/{tid}", dependencies=[Depends(require_admin)])
def deactivate_template(tid: int, session: Session = Depends(get_session)):
    """软删除：is_active=False，不真删（已有会员卡仍引用）"""
    tmpl = session.get(CardTemplate, tid)
    if not tmpl:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "卡种不存在")
    tmpl.is_active = False
    session.add(tmpl)
    session.commit()
    return {"ok": True}


# ============ 会员卡 ============

class IssueCardIn(BaseModel):
    member_id: int
    template_id: int
    method: PaymentMethod = PaymentMethod.cash
    paid_amount: Optional[int] = None        # 不填默认 = template.price
    note: Optional[str] = Field(default=None, max_length=255)


class CardOut(BaseModel):
    id: int
    member_id: int
    template_id: int
    type: CardType
    name: str
    remaining_credits: int
    remaining_balance: int
    daily_limit: int
    valid_from: datetime
    valid_until: Optional[datetime] = None
    applicable_category_id: Optional[int] = None
    status: CardStatus
    created_at: datetime

    model_config = {"from_attributes": True}


class IssueResult(BaseModel):
    card: CardOut
    order_id: int
    order_no: str


class CardAdjust(BaseModel):
    credits_delta: int = 0
    balance_delta: int = 0
    note: Optional[str] = Field(default=None, max_length=255)


@router.post("/admin/cards/issue", response_model=IssueResult, dependencies=[Depends(require_staff)])
def issue_card(
    body: IssueCardIn,
    session: Session = Depends(get_session),
    operator: User = Depends(get_current_user),
):
    member = session.get(User, body.member_id)
    if not member:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "会员不存在")
    if member.role != UserRole.member:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "只能给会员开卡")
    tmpl = session.get(CardTemplate, body.template_id)
    if not tmpl or not tmpl.is_active:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "卡种不存在或已停售")

    card, order, _tx = card_svc.issue_card(
        session, member, tmpl, operator, body.method, body.paid_amount, body.note,
    )
    audit_svc.log(session, operator, "card.issue", "card", card.id, {
        "member_id": member.id, "template_id": tmpl.id,
        "method": body.method.value, "paid_amount": body.paid_amount or tmpl.price,
    })
    session.commit()
    session.refresh(card)
    session.refresh(order)
    return IssueResult(card=CardOut.model_validate(card), order_id=order.id, order_no=order.order_no)


@router.get("/admin/cards", response_model=List[CardOut], dependencies=[Depends(require_staff)])
def list_cards(
    member_id: Optional[int] = None,
    status_: Optional[CardStatus] = Query(default=None, alias="status"),
    session: Session = Depends(get_session),
):
    stmt = select(MemberCard)
    if member_id is not None:
        stmt = stmt.where(MemberCard.member_id == member_id)
    if status_ is not None:
        stmt = stmt.where(MemberCard.status == status_)
    return session.exec(stmt.order_by(MemberCard.id.desc())).all()


@router.get("/admin/cards/{card_id}", response_model=CardOut, dependencies=[Depends(require_staff)])
def get_card(card_id: int, session: Session = Depends(get_session)):
    card = session.get(MemberCard, card_id)
    if not card:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "卡不存在")
    return card


@router.get("/admin/cards/{card_id}/transactions", response_model=List[CardTransaction], dependencies=[Depends(require_staff)])
def list_card_transactions(card_id: int, session: Session = Depends(get_session)):
    card = session.get(MemberCard, card_id)
    if not card:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "卡不存在")
    return session.exec(
        select(CardTransaction).where(CardTransaction.card_id == card_id).order_by(CardTransaction.id.desc())
    ).all()


@router.post("/admin/cards/{card_id}/freeze")
def freeze_card(
    card_id: int,
    operator: User = Depends(require_admin),
    session: Session = Depends(get_session),
):
    card = session.get(MemberCard, card_id)
    if not card:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "卡不存在")
    card_svc.freeze(session, card)
    audit_svc.log(session, operator, "card.freeze", "card", card.id)
    session.commit()
    return {"ok": True}


@router.post("/admin/cards/{card_id}/unfreeze")
def unfreeze_card(
    card_id: int,
    operator: User = Depends(require_admin),
    session: Session = Depends(get_session),
):
    card = session.get(MemberCard, card_id)
    if not card:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "卡不存在")
    card_svc.unfreeze(session, card)
    audit_svc.log(session, operator, "card.unfreeze", "card", card.id)
    session.commit()
    return {"ok": True}


@router.post("/admin/cards/{card_id}/adjust")
def adjust_card(
    card_id: int,
    body: CardAdjust,
    operator: User = Depends(require_admin),
    session: Session = Depends(get_session),
):
    card = session.get(MemberCard, card_id)
    if not card:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "卡不存在")
    if body.credits_delta == 0 and body.balance_delta == 0:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "未指定变更")
    card_svc.adjust(session, card, operator, body.credits_delta, body.balance_delta, body.note)
    audit_svc.log(session, operator, "card.adjust", "card", card.id, {
        "credits_delta": body.credits_delta, "balance_delta": body.balance_delta,
        "note": body.note,
    })
    session.commit()
    session.refresh(card)
    return CardOut.model_validate(card)


# ============ 退卡退款 ============

class RefundIn(BaseModel):
    refund_amount: int = Field(ge=0, description="退款金额（分）")
    note: Optional[str] = Field(default=None, max_length=255)


class RefundResult(BaseModel):
    card: CardOut
    cancelled_bookings: int
    refund_amount: int


@router.post("/admin/cards/{card_id}/refund", response_model=RefundResult)
def refund_card_endpoint(
    card_id: int,
    body: RefundIn,
    operator: User = Depends(require_admin),
    session: Session = Depends(get_session),
):
    """整卡退款。会先取消该卡所有未来未上的预约（释放容量），再标记 status=refunded。"""
    card = session.get(MemberCard, card_id)
    if not card:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "卡不存在")
    try:
        _tx, cancelled = card_svc.refund_card(session, card, operator, body.refund_amount, body.note)
    except ValueError as e:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(e))
    audit_svc.log(session, operator, "card.refund", "card", card.id, {
        "refund_amount": body.refund_amount, "cancelled_bookings": cancelled,
        "note": body.note,
    })
    session.commit()
    session.refresh(card)
    return RefundResult(
        card=CardOut.model_validate(card),
        cancelled_bookings=cancelled,
        refund_amount=body.refund_amount,
    )


# ============ 会员自己看卡 ============

@router.get("/me/cards", response_model=List[CardOut])
def my_cards(
    current: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    return session.exec(
        select(MemberCard).where(MemberCard.member_id == current.id).order_by(MemberCard.id.desc())
    ).all()


@router.get("/me/cards/{card_id}/transactions", response_model=List[CardTransaction])
def my_card_transactions(
    card_id: int,
    current: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    card = session.get(MemberCard, card_id)
    if not card or card.member_id != current.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "卡不存在")
    return session.exec(
        select(CardTransaction).where(CardTransaction.card_id == card_id).order_by(CardTransaction.id.desc())
    ).all()


# ============ 订单（购卡历史） ============

@router.get("/admin/orders", response_model=List[PaymentOrder], dependencies=[Depends(require_staff)])
def list_orders(
    member_id: Optional[int] = None,
    status_: Optional[OrderStatus] = Query(default=None, alias="status"),
    session: Session = Depends(get_session),
):
    stmt = select(PaymentOrder)
    if member_id is not None:
        stmt = stmt.where(PaymentOrder.member_id == member_id)
    if status_ is not None:
        stmt = stmt.where(PaymentOrder.status == status_)
    return session.exec(stmt.order_by(PaymentOrder.id.desc())).all()
