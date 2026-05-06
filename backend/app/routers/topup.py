"""储值卡充值（含充送规则）"""
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlmodel import Session, select
from ..database import get_session
from ..models import (
    User, MemberCard, CardType, CardStatus,
    CardTransaction, CardTxType,
    PaymentOrder, OrderStatus, PaymentMethod,
)
from ..core.deps import require_admin, get_current_user
from ..services import audit as audit_svc, cards as card_svc

router = APIRouter(prefix="/api", tags=["topup"])


class TopupIn(BaseModel):
    card_id: int
    paid_amount: int = Field(gt=0, description="实付金额（分）")
    bonus_amount: int = Field(default=0, ge=0, description="充送（分），如充1000送200则paid=100000, bonus=20000")
    method: PaymentMethod = PaymentMethod.cash
    note: Optional[str] = None


@router.post("/admin/cards/{card_id}/topup", dependencies=[Depends(require_admin)])
def topup_card(
    card_id: int,
    body: TopupIn,
    operator: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    """给储值卡充值。可选充送：bonus_amount > 0 时一并加到余额，但订单只记 paid_amount"""
    card = session.get(MemberCard, card_id)
    if not card:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "卡不存在")
    if card.type != CardType.stored:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "只有储值卡支持充值")
    if card.status not in (CardStatus.active, CardStatus.used_up):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"卡当前状态不可充值：{card.status.value}")

    now = datetime.utcnow()
    total_credit = body.paid_amount + body.bonus_amount

    # 更新余额
    card.remaining_balance += total_credit
    if card.status == CardStatus.used_up:
        card.status = CardStatus.active
    session.add(card)

    # 流水
    note_text = body.note or f"充值 ¥{body.paid_amount/100:.2f}" + (f" 送 ¥{body.bonus_amount/100:.2f}" if body.bonus_amount else "")
    tx = CardTransaction(
        card_id=card.id, member_id=card.member_id,
        type=CardTxType.topup,
        credits_delta=0,
        balance_delta=total_credit,
        operator_id=operator.id,
        note=note_text,
    )
    session.add(tx)

    # 订单
    order = PaymentOrder(
        order_no=card_svc.generate_order_no(),
        member_id=card.member_id,
        template_id=card.template_id,
        amount=body.paid_amount,
        paid_amount=body.paid_amount,
        method=body.method,
        status=OrderStatus.paid,
        operator_id=operator.id,
        paid_at=now,
        created_card_id=card.id,
        note=note_text,
    )
    session.add(order)

    audit_svc.log(session, operator, "card.topup", "card", card.id, {
        "paid": body.paid_amount, "bonus": body.bonus_amount, "method": body.method.value,
    })

    session.commit()
    session.refresh(card)
    session.refresh(order)
    return {
        "card_id": card.id,
        "new_balance": card.remaining_balance,
        "paid": body.paid_amount,
        "bonus": body.bonus_amount,
        "order_no": order.order_no,
    }
