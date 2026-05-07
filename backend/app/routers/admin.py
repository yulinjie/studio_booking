"""跨模块的运营工具：CSV 导出 / 文件上传 / 注册二维码 / 审计日志查看 / 工作室配置"""
import csv, io, uuid
from datetime import datetime
from pathlib import Path
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query, Request, status
from fastapi.responses import Response, StreamingResponse
from pydantic import BaseModel
from sqlmodel import Session, select
import qrcode
from ..database import get_session
from ..models import (
    User, UserRole, AuditLog,
    Booking, BookingStatus, ClassSession, Course,
    PaymentOrder, MemberCard,
    StudioConfig,
)
from ..core.deps import require_admin, require_staff, get_current_user

router = APIRouter(prefix="/api", tags=["admin"])

# 上传根目录：backend/uploads/
UPLOAD_DIR = Path(__file__).resolve().parent.parent.parent / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)
ALLOWED_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}
MAX_BYTES = 5 * 1024 * 1024  # 5MB


# ============ 文件上传 ============

class UploadResult(BaseModel):
    url: str
    filename: str
    size: int


@router.post("/admin/upload", response_model=UploadResult, dependencies=[Depends(require_staff)])
async def upload_file(file: UploadFile = File(...)):
    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"仅支持 jpg/png/webp/gif，收到 {file.content_type}")
    content = await file.read()
    if len(content) > MAX_BYTES:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "文件过大（>5MB）")
    ext = "jpg"
    if file.filename and "." in file.filename:
        ext = file.filename.rsplit(".", 1)[-1].lower()[:8]
    fname = f"{uuid.uuid4().hex}.{ext}"
    (UPLOAD_DIR / fname).write_bytes(content)
    return UploadResult(url=f"/uploads/{fname}", filename=fname, size=len(content))


# ============ CSV 导出 ============

def _csv_response(rows: list, headers: list, filename: str) -> Response:
    buf = io.StringIO()
    buf.write("﻿")  # Excel 识别 UTF-8 的 BOM
    w = csv.writer(buf)
    w.writerow(headers)
    for r in rows:
        w.writerow(r)
    return Response(
        content=buf.getvalue().encode("utf-8"),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@router.get("/admin/export/members.csv", dependencies=[Depends(require_staff)])
def export_members(session: Session = Depends(get_session)):
    headers = ["ID", "手机号", "姓名", "角色", "性别", "生日", "紧急联系人", "紧急电话", "健康备注", "店长备注", "状态", "注册时间"]
    rows = []
    for u in session.exec(select(User).order_by(User.id)).all():
        rows.append([
            u.id, u.phone, u.name, u.role.value, u.gender or "",
            u.birthday.strftime("%Y-%m-%d") if u.birthday else "",
            u.emergency_contact_name or "", u.emergency_contact_phone or "",
            u.health_note or "", u.note or "",
            "在用" if u.is_active else "停用",
            u.created_at.strftime("%Y-%m-%d %H:%M"),
        ])
    return _csv_response(rows, headers, "members.csv")


@router.get("/admin/export/orders.csv", dependencies=[Depends(require_staff)])
def export_orders(session: Session = Depends(get_session)):
    headers = ["订单号", "会员ID", "会员姓名", "卡种ID", "应收(元)", "实收(元)", "已退(元)", "支付方式", "状态", "操作员", "创建时间", "支付时间", "退款时间", "备注"]
    users = {u.id: u for u in session.exec(select(User)).all()}
    rows = []
    for o in session.exec(select(PaymentOrder).order_by(PaymentOrder.id.desc())).all():
        m = users.get(o.member_id)
        op = users.get(o.operator_id) if o.operator_id else None
        rows.append([
            o.order_no, o.member_id, m.name if m else "",
            o.template_id,
            f"{o.amount/100:.2f}", f"{o.paid_amount/100:.2f}",
            f"{(o.refund_amount or 0)/100:.2f}",
            o.method.value if o.method else "",
            o.status.value,
            op.name if op else "",
            o.created_at.strftime("%Y-%m-%d %H:%M"),
            o.paid_at.strftime("%Y-%m-%d %H:%M") if o.paid_at else "",
            o.refunded_at.strftime("%Y-%m-%d %H:%M") if o.refunded_at else "",
            o.note or "",
        ])
    return _csv_response(rows, headers, "orders.csv")


@router.get("/admin/export/bookings.csv", dependencies=[Depends(require_staff)])
def export_bookings(
    start: Optional[datetime] = None,
    end: Optional[datetime] = None,
    session: Session = Depends(get_session),
):
    """默认导出近 30 天到未来 7 天的预约记录"""
    if not start:
        start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        from datetime import timedelta
        start = start - timedelta(days=30)
    if not end:
        from datetime import timedelta
        end = datetime.utcnow() + timedelta(days=7)

    users = {u.id: u for u in session.exec(select(User)).all()}
    courses = {c.id: c for c in session.exec(select(Course)).all()}
    sessions_by_id = {s.id: s for s in session.exec(
        select(ClassSession).where(ClassSession.start_at >= start, ClassSession.start_at < end)
    ).all()}

    headers = ["预约ID", "会员", "手机号", "课程", "上课时间", "教室", "卡ID", "状态", "候补#", "预约时间", "签到时间", "取消时间"]
    rows = []
    for b in session.exec(select(Booking).order_by(Booking.id.desc()).limit(5000)).all():
        cs = sessions_by_id.get(b.session_id)
        if not cs:
            continue
        m = users.get(b.member_id)
        c = courses.get(cs.course_id) if cs else None
        rows.append([
            b.id, m.name if m else b.member_id, m.phone if m else "",
            c.name if c else "",
            cs.start_at.strftime("%Y-%m-%d %H:%M") if cs else "",
            cs.room or "" if cs else "",
            b.card_id or "",
            b.status.value, b.waitlist_order or "",
            b.booked_at.strftime("%Y-%m-%d %H:%M"),
            b.checked_in_at.strftime("%Y-%m-%d %H:%M") if b.checked_in_at else "",
            b.cancelled_at.strftime("%Y-%m-%d %H:%M") if b.cancelled_at else "",
        ])
    return _csv_response(rows, headers, "bookings.csv")


# ============ 注册二维码 ============

@router.get("/studio/registration-qr.png")
def registration_qr(request: Request):
    """生成"会员扫码注册"的二维码 PNG。base 自动用当前请求的 host。"""
    base = f"{request.url.scheme}://{request.url.netloc}"
    target = f"{base}/#/login?mode=register"
    img = qrcode.make(target)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return Response(content=buf.getvalue(), media_type="image/png", headers={
        "Cache-Control": "no-store",
    })


@router.get("/studio/registration-url")
def registration_url(request: Request, current: User = Depends(get_current_user)):
    """文字版注册链接（管理员复制粘贴用）"""
    base = f"{request.url.scheme}://{request.url.netloc}"
    return {"url": f"{base}/#/login?mode=register"}


# ============ 工作室配置 ============

class StudioConfigUpdate(BaseModel):
    name: Optional[str] = None
    logo: Optional[str] = None
    address: Optional[str] = None
    phone: Optional[str] = None
    open_time: Optional[str] = None
    close_time: Optional[str] = None
    announcement: Optional[str] = None
    booking_rules: Optional[str] = None
    payment_qr: Optional[str] = None
    payment_note: Optional[str] = None


@router.get("/studio/config", response_model=StudioConfig)
def get_studio_config(session: Session = Depends(get_session), _: User = Depends(get_current_user)):
    cfg = session.exec(select(StudioConfig)).first()
    if not cfg:
        cfg = StudioConfig(name="工作室")
        session.add(cfg)
        session.commit()
        session.refresh(cfg)
    return cfg


@router.patch("/admin/studio/config", response_model=StudioConfig, dependencies=[Depends(require_admin)])
def update_studio_config(body: StudioConfigUpdate, session: Session = Depends(get_session)):
    cfg = session.exec(select(StudioConfig)).first()
    if not cfg:
        cfg = StudioConfig(name=body.name or "工作室")
        session.add(cfg)
        session.commit()
        session.refresh(cfg)
    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(cfg, k, v)
    cfg.updated_at = datetime.utcnow()
    session.add(cfg)
    session.commit()
    session.refresh(cfg)
    return cfg


# ============ 审计日志 ============

class AuditLogOut(BaseModel):
    id: int
    ts: datetime
    operator_id: Optional[int]
    operator_name: Optional[str]
    action: str
    target_type: Optional[str]
    target_id: Optional[int]
    detail: Optional[str]

    model_config = {"from_attributes": True}


# ============ 流失预警 ============

class AtRiskMember(BaseModel):
    id: int
    name: str
    phone: str
    last_attended_at: Optional[datetime] = None
    days_inactive: int                         # 距今天数（无记录则 9999）
    risk_level: str                            # warning | at_risk | lost
    active_cards: int                          # 在用卡数
    total_attended: int                        # 累计上课次数（参考强度）
    tags: Optional[str] = None


@router.get("/admin/at-risk-members", response_model=List[AtRiskMember], dependencies=[Depends(require_admin)])
def list_at_risk(
    level: Optional[str] = Query(None, regex="^(warning|at_risk|lost|all)?$"),
    min_total: int = Query(1, ge=0, description="只看累计上过 ≥N 节的（过滤体验未购卡的人）"),
    session: Session = Depends(get_session),
):
    """
    根据'最近一次签到'判定风险等级：
      warning   = 15-29 天未签到
      at_risk   = 30-59 天未签到
      lost      = 60+ 天未签到
    只看 role=member + is_active=true 的人。
    """
    from ..models import Booking, BookingStatus, MemberCard, CardStatus
    from sqlmodel import select as sel
    members = session.exec(
        sel(User).where(User.role == UserRole.member, User.is_active == True)
    ).all()
    now = datetime.utcnow()

    results = []
    for m in members:
        # 最近一次 attended
        last = session.exec(
            sel(Booking)
            .where(Booking.member_id == m.id, Booking.status == BookingStatus.attended)
            .order_by(Booking.checked_in_at.desc())
            .limit(1)
        ).first()
        if not last or not last.checked_in_at:
            days = 9999
            last_at = None
        else:
            days = (now - last.checked_in_at).days
            last_at = last.checked_in_at

        if days < 15:
            continue        # 还活跃，不在预警列表

        if days < 30:
            risk = "warning"
        elif days < 60:
            risk = "at_risk"
        else:
            risk = "lost"

        if level and level != "all" and level != risk:
            continue

        # 累计课次（过滤体验未购卡）
        total = session.exec(
            sel(Booking).where(Booking.member_id == m.id, Booking.status == BookingStatus.attended)
        ).all()
        if len(total) < min_total:
            continue

        # 在用卡数
        cards = session.exec(
            sel(MemberCard).where(MemberCard.member_id == m.id, MemberCard.status == CardStatus.active)
        ).all()

        results.append(AtRiskMember(
            id=m.id, name=m.name, phone=m.phone,
            last_attended_at=last_at, days_inactive=days,
            risk_level=risk,
            active_cards=len(cards),
            total_attended=len(total),
            tags=m.tags,
        ))

    # 按"距今天数 desc"排（流失越久越靠后？或越前？这里靠前 = 越久 = 更紧急）
    results.sort(key=lambda r: r.days_inactive, reverse=True)
    return results


@router.get("/admin/audit-logs", response_model=List[AuditLogOut], dependencies=[Depends(require_admin)])
def list_audit_logs(
    action: Optional[str] = None,
    operator_id: Optional[int] = None,
    target_type: Optional[str] = None,
    limit: int = Query(200, ge=1, le=1000),
    session: Session = Depends(get_session),
):
    stmt = select(AuditLog)
    if action:
        stmt = stmt.where(AuditLog.action == action)
    if operator_id:
        stmt = stmt.where(AuditLog.operator_id == operator_id)
    if target_type:
        stmt = stmt.where(AuditLog.target_type == target_type)
    return session.exec(stmt.order_by(AuditLog.id.desc()).limit(limit)).all()
