"""
卡相关的核心业务逻辑（开卡 / 扣次 / 退课返还 / 调整 / 过期检查）。
所有会改变卡余额的操作都必须走这一层 —— 这样流水账永远完整。
预约模块会调用 deduct_for_booking / refund_for_cancel。
"""
from datetime import datetime, timedelta
import random
from typing import Optional, Tuple
from sqlmodel import Session
from ..models import (
    User, MemberCard, CardTemplate, CardStatus, CardType,
    CardTransaction, CardTxType,
    PaymentOrder, OrderStatus, PaymentMethod,
)


def generate_order_no() -> str:
    return f"O{datetime.now().strftime('%Y%m%d%H%M%S')}{random.randint(1000, 9999)}"


def issue_card(
    session: Session,
    member: User,
    template: CardTemplate,
    operator: Optional[User],
    method: PaymentMethod,
    paid_amount: Optional[int] = None,
    note: Optional[str] = None,
) -> Tuple[MemberCard, PaymentOrder, CardTransaction]:
    """
    给会员开卡：同时建 MemberCard + PaymentOrder(已支付) + CardTransaction(购卡)。
    一个事务里完成，调用方负责 session.commit()。
    """
    now = datetime.utcnow()
    valid_until = now + timedelta(days=template.valid_days) if template.valid_days > 0 else None

    card = MemberCard(
        member_id=member.id,
        template_id=template.id,
        type=template.type,
        name=template.name,
        remaining_credits=template.initial_credits,
        remaining_balance=template.initial_balance,
        daily_limit=template.daily_limit,
        valid_from=now,
        valid_until=valid_until,
        applicable_category_id=template.applicable_category_id,
        status=CardStatus.active,
    )
    session.add(card)
    session.flush()

    order = PaymentOrder(
        order_no=generate_order_no(),
        member_id=member.id,
        template_id=template.id,
        amount=template.price,
        paid_amount=paid_amount if paid_amount is not None else template.price,
        method=method,
        status=OrderStatus.paid,
        operator_id=operator.id if operator else None,
        paid_at=now,
        created_card_id=card.id,
        note=note,
    )
    session.add(order)
    session.flush()

    tx = CardTransaction(
        card_id=card.id,
        member_id=member.id,
        type=CardTxType.purchase,
        credits_delta=template.initial_credits,
        balance_delta=template.initial_balance,
        related_order_id=order.id,
        operator_id=operator.id if operator else None,
        note=f"购卡: {template.name}",
    )
    session.add(tx)
    session.flush()

    return card, order, tx


def _refresh_card_status(card: MemberCard) -> None:
    """根据余额/次数/有效期刷新卡状态。调用方负责 session.add(card)。"""
    if card.status in (CardStatus.frozen, CardStatus.refunded):
        return
    now = datetime.utcnow()
    if card.valid_until and card.valid_until < now:
        card.status = CardStatus.expired
        return
    if card.type in (CardType.times, CardType.package) and card.remaining_credits <= 0:
        card.status = CardStatus.used_up
        return
    if card.type == CardType.stored and card.remaining_balance <= 0:
        card.status = CardStatus.used_up
        return
    card.status = CardStatus.active


def deduct_for_booking(
    session: Session,
    card: MemberCard,
    member_id: int,
    booking_id: int,
    credits: int = 1,
    balance_cost: int = 0,
    operator: Optional[User] = None,
) -> CardTransaction:
    """预约时扣卡。调用前必须检查可用性。"""
    card.remaining_credits -= credits
    card.remaining_balance -= balance_cost
    _refresh_card_status(card)
    session.add(card)
    tx = CardTransaction(
        card_id=card.id,
        member_id=member_id,
        type=CardTxType.deduct_book,
        credits_delta=-credits,
        balance_delta=-balance_cost,
        related_booking_id=booking_id,
        operator_id=operator.id if operator else None,
        note="预约扣次",
    )
    session.add(tx)
    session.flush()
    return tx


def refund_for_cancel(
    session: Session,
    card: MemberCard,
    member_id: int,
    booking_id: int,
    credits: int = 1,
    balance_cost: int = 0,
    operator: Optional[User] = None,
) -> CardTransaction:
    """取消预约（在截止时限内）返还卡次。"""
    card.remaining_credits += credits
    card.remaining_balance += balance_cost
    _refresh_card_status(card)
    session.add(card)
    tx = CardTransaction(
        card_id=card.id,
        member_id=member_id,
        type=CardTxType.refund_cancel,
        credits_delta=credits,
        balance_delta=balance_cost,
        related_booking_id=booking_id,
        operator_id=operator.id if operator else None,
        note="取消预约返还",
    )
    session.add(tx)
    session.flush()
    return tx


def adjust(
    session: Session,
    card: MemberCard,
    operator: User,
    credits_delta: int = 0,
    balance_delta: int = 0,
    note: Optional[str] = None,
) -> CardTransaction:
    """店长手工调整 — 留痕。"""
    card.remaining_credits += credits_delta
    card.remaining_balance += balance_delta
    _refresh_card_status(card)
    session.add(card)
    tx = CardTransaction(
        card_id=card.id,
        member_id=card.member_id,
        type=CardTxType.adjust,
        credits_delta=credits_delta,
        balance_delta=balance_delta,
        operator_id=operator.id,
        note=note or "手工调整",
    )
    session.add(tx)
    session.flush()
    return tx


def freeze(session: Session, card: MemberCard) -> None:
    if card.status == CardStatus.active:
        card.status = CardStatus.frozen
        session.add(card)


def unfreeze(session: Session, card: MemberCard) -> None:
    if card.status == CardStatus.frozen:
        # 先置回 active，让 _refresh_card_status 不再提前 return；它会按余额/有效期重新判定
        card.status = CardStatus.active
        _refresh_card_status(card)
        session.add(card)


def refund_card(
    session: Session,
    card: MemberCard,
    operator: User,
    refund_amount: int,
    note: Optional[str] = None,
) -> Tuple[CardTransaction, int]:
    """
    整卡退款：
    1) 取消该卡的所有未来预约（释放容量、晋升候补）
    2) 卡状态置 refunded
    3) 写一条 card_refund 流水
    4) 关联购卡订单标记 refunded
    返回 (流水记录, 取消的预约数)
    """
    from ..models import Booking, BookingStatus, ClassSession  # 避免循环
    from sqlmodel import select

    if card.status == CardStatus.refunded:
        raise ValueError("已退卡")
    now = datetime.utcnow()

    # 1. 取消未来预约
    future = session.exec(
        select(Booking)
        .join(ClassSession, ClassSession.id == Booking.session_id)
        .where(
            Booking.card_id == card.id,
            Booking.status.in_([BookingStatus.booked, BookingStatus.waitlist]),
            ClassSession.start_at > now,
        )
    ).all()
    cancelled_count = 0
    for b in future:
        if b.status == BookingStatus.booked:
            cs = session.get(ClassSession, b.session_id)
            if cs:
                cs.booked_count = max(0, cs.booked_count - 1)
                session.add(cs)
        b.status = BookingStatus.cancelled
        b.cancelled_at = now
        session.add(b)
        cancelled_count += 1

    # 2. 卡置 refunded
    prev_credits = card.remaining_credits
    prev_balance = card.remaining_balance
    card.remaining_credits = 0
    card.remaining_balance = 0
    card.status = CardStatus.refunded
    session.add(card)

    # 3. 流水（credits/balance 减成 0；refund_amount 用 detail 记金额）
    tx = CardTransaction(
        card_id=card.id,
        member_id=card.member_id,
        type=CardTxType.card_refund,
        credits_delta=-prev_credits,
        balance_delta=-prev_balance,
        operator_id=operator.id if operator else None,
        note=(note or f"整卡退款 ¥{refund_amount/100:.2f}"),
    )
    session.add(tx)

    # 4. 标记购卡订单
    order = session.exec(
        select(PaymentOrder).where(PaymentOrder.created_card_id == card.id)
    ).first()
    if order:
        order.status = OrderStatus.refunded
        order.refund_amount = (order.refund_amount or 0) + refund_amount
        order.refunded_at = now
        session.add(order)

    session.flush()
    return tx, cancelled_count


def card_is_usable_for(card: MemberCard, category_id: int) -> Tuple[bool, str]:
    """检查这张卡能不能用于某个课程类型的预约 — 返回 (是否可用, 不可用原因)"""
    if card.status != CardStatus.active:
        return False, f"卡状态：{card.status.value}"
    now = datetime.utcnow()
    if card.valid_until and card.valid_until < now:
        return False, "卡已过期"
    if card.applicable_category_id and card.applicable_category_id != category_id:
        return False, "该卡不适用于此课程类型"
    if card.type in (CardType.times, CardType.package) and card.remaining_credits <= 0:
        return False, "卡次数已用完"
    if card.type == CardType.stored and card.remaining_balance <= 0:
        return False, "余额不足"
    return True, ""
