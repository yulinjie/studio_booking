"""
会员自助购卡：下单（pending）→ 上传付款凭证 → 后台审核 → 自动开卡

流程：
  1. 会员选卡种 → POST /me/orders                   → 创建 pending 订单
  2. 会员付款（线下扫码）→ PATCH /me/orders/{id}    → 上传截图 url
  3. 后台审核                                        → 看截图
  4. 后台 POST /admin/orders/{id}/approve            → 自动开卡 + 标 paid
     或   POST /admin/orders/{id}/reject             → 标 cancelled + 写原因
"""
from datetime import datetime, timedelta
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlmodel import Session, select
from ..database import get_session
from ..models import (
    User, UserRole,
    CardTemplate, MemberCard, CardStatus, CardType, CardTransaction, CardTxType,
    PaymentOrder, OrderStatus, PaymentMethod,
)
from ..core.deps import get_current_user, require_admin, require_staff
from ..services import audit as audit_svc, cards as card_svc

router = APIRouter(prefix="/api", tags=["selfserve"])


# ==================== 会员侧 ====================

class CreateOrderIn(BaseModel):
    template_id: int
    payment_proof: Optional[str] = None         # 可选：下单时已传截图
    note: Optional[str] = Field(default=None, max_length=255)


class OrderOut(BaseModel):
    id: int
    order_no: str
    member_id: int
    template_id: int
    template_name: str
    amount: int                                 # 应付（分）
    paid_amount: int
    status: OrderStatus
    method: Optional[PaymentMethod] = None
    payment_proof: Optional[str] = None
    reject_reason: Optional[str] = None
    source: str
    created_at: datetime
    paid_at: Optional[datetime] = None
    note: Optional[str] = None


def _to_out(o: PaymentOrder, tmpl_name: str) -> OrderOut:
    return OrderOut(
        id=o.id, order_no=o.order_no, member_id=o.member_id,
        template_id=o.template_id, template_name=tmpl_name,
        amount=o.amount, paid_amount=o.paid_amount,
        status=o.status, method=o.method,
        payment_proof=o.payment_proof, reject_reason=o.reject_reason,
        source=o.source, created_at=o.created_at, paid_at=o.paid_at,
        note=o.note,
    )


@router.post("/me/orders", response_model=OrderOut)
def create_my_order(
    body: CreateOrderIn,
    current: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    """会员自助下单。订单状态 pending，等待后台审核截图后自动开卡。"""
    if current.role != UserRole.member:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "只有会员可以购卡")
    tmpl = session.get(CardTemplate, body.template_id)
    if not tmpl or not tmpl.is_active:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "卡种不存在或已下架")

    # 限制：同一会员同一模板，存在 pending 订单的话不允许再下单
    pending = session.exec(
        select(PaymentOrder).where(
            PaymentOrder.member_id == current.id,
            PaymentOrder.template_id == tmpl.id,
            PaymentOrder.status == OrderStatus.pending,
        )
    ).first()
    if pending:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            f"你有未完成的订单 #{pending.order_no}，请先在'我的订单'里继续完成或取消",
        )

    order = PaymentOrder(
        order_no=card_svc.generate_order_no(),
        member_id=current.id,
        template_id=tmpl.id,
        amount=tmpl.price,
        paid_amount=0,
        status=OrderStatus.pending,
        source="self",
        payment_proof=body.payment_proof,
        note=body.note,
    )
    session.add(order)
    session.commit()
    session.refresh(order)
    return _to_out(order, tmpl.name)


class UploadProofIn(BaseModel):
    payment_proof: str                          # /uploads/xxx.png


@router.patch("/me/orders/{order_id}", response_model=OrderOut)
def upload_proof(
    order_id: int,
    body: UploadProofIn,
    current: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    """会员补交付款凭证"""
    order = session.get(PaymentOrder, order_id)
    if not order or order.member_id != current.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "订单不存在")
    if order.status != OrderStatus.pending:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"订单状态：{order.status.value}，不能修改")
    order.payment_proof = body.payment_proof
    session.add(order)
    session.commit()
    session.refresh(order)
    tmpl = session.get(CardTemplate, order.template_id)
    return _to_out(order, tmpl.name if tmpl else "?")


@router.post("/me/orders/{order_id}/cancel")
def cancel_my_order(
    order_id: int,
    current: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    """会员取消自己的 pending 订单"""
    order = session.get(PaymentOrder, order_id)
    if not order or order.member_id != current.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "订单不存在")
    if order.status != OrderStatus.pending:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"订单状态：{order.status.value}，不能取消")
    order.status = OrderStatus.cancelled
    session.add(order)
    session.commit()
    return {"ok": True}


@router.get("/me/orders", response_model=List[OrderOut])
def list_my_orders(
    current: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    orders = session.exec(
        select(PaymentOrder)
        .where(PaymentOrder.member_id == current.id)
        .order_by(PaymentOrder.id.desc())
    ).all()
    tmpls = {t.id: t for t in session.exec(select(CardTemplate)).all()}
    return [_to_out(o, (tmpls.get(o.template_id) or CardTemplate(name="?", type=CardType.times, price=0)).name) for o in orders]


# ==================== 后台审核 ====================

class ApproveIn(BaseModel):
    paid_amount: Optional[int] = None           # 实收金额（不填默认 = 应付）
    method: PaymentMethod = PaymentMethod.wechat_qr
    note: Optional[str] = None


class RejectIn(BaseModel):
    reason: str = Field(min_length=1, max_length=255)


@router.get("/admin/orders/pending", response_model=List[OrderOut], dependencies=[Depends(require_staff)])
def list_pending_orders(
    session: Session = Depends(get_session),
):
    """后台待审核订单（status=pending 且 source=self）"""
    orders = session.exec(
        select(PaymentOrder)
        .where(PaymentOrder.status == OrderStatus.pending, PaymentOrder.source == "self")
        .order_by(PaymentOrder.id.desc())
    ).all()
    tmpls = {t.id: t for t in session.exec(select(CardTemplate)).all()}
    return [_to_out(o, (tmpls.get(o.template_id) or CardTemplate(name="?", type=CardType.times, price=0)).name) for o in orders]


@router.post("/admin/orders/{order_id}/approve", response_model=OrderOut, dependencies=[Depends(require_staff)])
def approve_order(
    order_id: int,
    body: ApproveIn,
    operator: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    """通过订单 → 自动开卡 + 标 paid"""
    order = session.get(PaymentOrder, order_id)
    if not order:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "订单不存在")
    if order.status != OrderStatus.pending:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"订单状态：{order.status.value}，不能通过")

    member = session.get(User, order.member_id)
    tmpl = session.get(CardTemplate, order.template_id)
    if not member or not tmpl:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "订单关联的会员/卡种不存在")

    now = datetime.utcnow()
    valid_until = now + timedelta(days=tmpl.valid_days) if tmpl.valid_days > 0 else None

    # 直接建卡 + 流水（不重新建 order，复用现有 order）
    card = MemberCard(
        member_id=member.id,
        template_id=tmpl.id,
        type=tmpl.type,
        name=tmpl.name,
        remaining_credits=tmpl.initial_credits,
        remaining_balance=tmpl.initial_balance,
        daily_limit=tmpl.daily_limit,
        valid_from=now,
        valid_until=valid_until,
        applicable_category_id=tmpl.applicable_category_id,
        status=CardStatus.active,
    )
    session.add(card)
    session.flush()

    # 更新订单
    order.status = OrderStatus.paid
    order.paid_amount = body.paid_amount if body.paid_amount is not None else tmpl.price
    order.method = body.method
    order.operator_id = operator.id
    order.paid_at = now
    order.created_card_id = card.id
    if body.note:
        order.note = (order.note or "") + f"\n[审核通过] {body.note}"
    session.add(order)

    # 流水
    tx = CardTransaction(
        card_id=card.id,
        member_id=member.id,
        type=CardTxType.purchase,
        credits_delta=tmpl.initial_credits,
        balance_delta=tmpl.initial_balance,
        related_order_id=order.id,
        operator_id=operator.id,
        note=f"会员自助购卡: {tmpl.name}",
    )
    session.add(tx)

    audit_svc.log(session, operator, "order.approve", "order", order.id, {
        "member_id": member.id, "template_id": tmpl.id,
        "card_id": card.id, "paid_amount": order.paid_amount,
    })
    session.commit()
    session.refresh(order)
    return _to_out(order, tmpl.name)


@router.post("/admin/orders/{order_id}/reject", response_model=OrderOut, dependencies=[Depends(require_staff)])
def reject_order(
    order_id: int,
    body: RejectIn,
    operator: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    order = session.get(PaymentOrder, order_id)
    if not order:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "订单不存在")
    if order.status != OrderStatus.pending:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"订单状态：{order.status.value}，不能驳回")

    order.status = OrderStatus.cancelled
    order.reject_reason = body.reason
    session.add(order)

    audit_svc.log(session, operator, "order.reject", "order", order.id, {"reason": body.reason})
    session.commit()
    session.refresh(order)
    tmpl = session.get(CardTemplate, order.template_id)
    return _to_out(order, tmpl.name if tmpl else "?")
