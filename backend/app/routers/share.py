"""
打卡海报 — 用 PIL 服务端生成图片，会员保存到相册分享朋友圈。
GET /api/share/poster/{booking_id}.png?token=...

token 是会员自己 JWT 的 access_token（直接走 Authorization header 也行）。
"""
import io
import textwrap
from datetime import datetime
from pathlib import Path
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import Response
from sqlmodel import Session, select
from PIL import Image, ImageDraw, ImageFont
import qrcode

from ..database import get_session
from ..models import (
    User, Booking, BookingStatus, ClassSession,
    Course, Coach, StudioConfig,
)
from ..core.deps import get_current_user

router = APIRouter(prefix="/api", tags=["share"])

# 海报尺寸（朋友圈友好）
W, H = 750, 1334

# 莫兰迪色板
COLOR_BG = (247, 243, 236)        # 米白
COLOR_BG_DEEP = (221, 229, 220)   # 鼠尾草浅
COLOR_PRIMARY = (110, 123, 115)   # 鼠尾草深
COLOR_TEXT = (63, 60, 58)
COLOR_MUTED = (158, 152, 144)
COLOR_ACCENT = (164, 131, 107)    # 焦糖

# 中文字体（Linux/Mac/Win 都尝试一遍）
FONT_CANDIDATES = [
    "/usr/share/fonts/opentype/noto/NotoSerifCJK-Regular.ttc",
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc",
    "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",
    "/System/Library/Fonts/PingFang.ttc",
    "C:\\Windows\\Fonts\\msyh.ttc",
    "C:\\Windows\\Fonts\\simhei.ttf",
]

QUOTES = [
    "向内觉知，向外舒展",
    "每一次呼吸都是新的开始",
    "稳稳地，一点一点向前",
    "保持耐心，相信过程",
    "今天的练习，是明天的自己",
    "不为完美，只为存在",
    "身体记得每一次的坚持",
]


def _font(size: int) -> ImageFont.FreeTypeFont:
    for path in FONT_CANDIDATES:
        if Path(path).exists():
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                continue
    return ImageFont.load_default()


def _quote_for(member_id: int, day: datetime) -> str:
    """同一会员同一天稳定的鸡汤"""
    seed = (member_id * 31 + day.toordinal()) % len(QUOTES)
    return QUOTES[seed]


def _draw_avatar(draw: ImageDraw.ImageDraw, x: int, y: int, r: int, name: str):
    """空头像 = 渐变圆 + 首字"""
    # 圆背景
    draw.ellipse([x, y, x + 2*r, y + 2*r], fill=COLOR_BG_DEEP, outline=COLOR_PRIMARY, width=2)
    # 首字
    initial = (name[:1] or "?").upper()
    f = _font(int(r * 0.9))
    bbox = draw.textbbox((0, 0), initial, font=f)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]
    draw.text((x + r - tw // 2, y + r - th // 2 - 5), initial, fill=COLOR_PRIMARY, font=f)


def _build_qr(text: str, size: int = 150) -> Image.Image:
    qr = qrcode.QRCode(version=1, box_size=4, border=2)
    qr.add_data(text)
    qr.make(fit=True)
    img = qr.make_image(fill_color=(63, 60, 58), back_color=(247, 243, 236)).convert("RGB")
    return img.resize((size, size), Image.LANCZOS)


@router.get("/share/poster/{booking_id}.png")
def share_poster(
    booking_id: int,
    request: Request,
    current: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    booking = session.get(Booking, booking_id)
    if not booking:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "记录不存在")
    if booking.member_id != current.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "无权生成他人海报")
    if booking.status != BookingStatus.attended:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "只有已上课的预约可生成海报")

    cs = session.get(ClassSession, booking.session_id)
    course = session.get(Course, cs.course_id) if cs else None
    coach = session.get(Coach, cs.coach_id) if cs and cs.coach_id else None
    studio = session.exec(select(StudioConfig)).first()

    coach_user = None
    if coach:
        coach_user = session.get(User, coach.user_id)

    # 计算累计课次
    all_attended = session.exec(
        select(Booking).where(Booking.member_id == current.id, Booking.status == BookingStatus.attended)
    ).all()
    total = len(all_attended)

    # ====== 开画 ======
    img = Image.new("RGB", (W, H), COLOR_BG)
    draw = ImageDraw.Draw(img)

    # 顶部渐变（手画 — sage 米白渐变）
    for y in range(0, 380):
        ratio = y / 380
        r = int(221 + (247 - 221) * ratio)
        g = int(229 + (243 - 229) * ratio)
        b = int(220 + (236 - 220) * ratio)
        draw.line([(0, y), (W, y)], fill=(r, g, b))

    # 装饰云朵线
    draw.arc([60, 120, 200, 260], start=200, end=340, fill=COLOR_PRIMARY, width=2)
    draw.arc([550, 200, 690, 340], start=200, end=340, fill=COLOR_ACCENT, width=2)

    # ====== Logo + 工作室名 ======
    studio_name = studio.name if studio else "云舍"
    f_logo = _font(56)
    bbox = draw.textbbox((0, 0), studio_name, font=f_logo)
    draw.text(((W - (bbox[2] - bbox[0])) // 2, 70), studio_name,
              fill=COLOR_TEXT, font=f_logo)
    f_tag = _font(20)
    tag = "YOGA · PILATES"
    bbox = draw.textbbox((0, 0), tag, font=f_tag)
    draw.text(((W - (bbox[2] - bbox[0])) // 2, 140), tag,
              fill=COLOR_MUTED, font=f_tag)

    # ====== 头像 + 名字 ======
    _draw_avatar(draw, W // 2 - 60, 200, 60, current.name)
    f_name = _font(36)
    bbox = draw.textbbox((0, 0), current.name, font=f_name)
    draw.text(((W - (bbox[2] - bbox[0])) // 2, 340), current.name,
              fill=COLOR_TEXT, font=f_name)

    # ====== 主标语 ======
    f_main = _font(60)
    main = "完成今日练习"
    bbox = draw.textbbox((0, 0), main, font=f_main)
    draw.text(((W - (bbox[2] - bbox[0])) // 2, 430), main,
              fill=COLOR_PRIMARY, font=f_main)

    # ====== 课程信息卡 ======
    card_y = 540
    card_h = 280
    draw.rounded_rectangle([60, card_y, W - 60, card_y + card_h],
                           radius=20, fill=(255, 255, 255), outline=COLOR_BG_DEEP, width=2)

    f_label = _font(20)
    f_value = _font(32)
    f_value_big = _font(40)

    # 课程名
    course_name = course.name if course else "练习"
    draw.text((100, card_y + 30), "课程", fill=COLOR_MUTED, font=f_label)
    draw.text((100, card_y + 56), course_name, fill=COLOR_TEXT, font=f_value_big)

    # 教练 + 时长 + 时间 (3 列)
    col_y = card_y + 150
    coach_name = coach_user.name if coach_user else "—"
    duration = f"{course.duration_minutes} 分钟" if course else "—"
    when = cs.start_at.strftime("%m月%d日 %H:%M") if cs else "—"

    cols = [("教练", coach_name), ("时长", duration), ("时间", when)]
    col_w = (W - 120) // 3
    for i, (k, v) in enumerate(cols):
        cx = 100 + i * col_w
        draw.text((cx, col_y), k, fill=COLOR_MUTED, font=f_label)
        draw.text((cx, col_y + 28), v, fill=COLOR_TEXT, font=f_value)

    # ====== 累计课次徽标 ======
    f_total_num = _font(72)
    f_total_lbl = _font(22)
    total_y = 880
    total_x = W // 2
    n_text = str(total)
    bbox = draw.textbbox((0, 0), n_text, font=f_total_num)
    nw = bbox[2] - bbox[0]
    draw.text((total_x - nw // 2, total_y), n_text,
              fill=COLOR_ACCENT, font=f_total_num)
    lbl = "累计完成"
    bbox = draw.textbbox((0, 0), lbl, font=f_total_lbl)
    draw.text((total_x - (bbox[2] - bbox[0]) // 2, total_y + 90), lbl,
              fill=COLOR_MUTED, font=f_total_lbl)

    # 装饰底线
    draw.line([(W // 2 - 40, total_y + 130), (W // 2 + 40, total_y + 130)],
              fill=COLOR_BG_DEEP, width=2)

    # ====== 鸡汤 ======
    quote = _quote_for(current.id, datetime.utcnow())
    f_quote = _font(28)
    bbox = draw.textbbox((0, 0), quote, font=f_quote)
    draw.text(((W - (bbox[2] - bbox[0])) // 2, 1050), quote,
              fill=COLOR_PRIMARY, font=f_quote)

    # ====== QR 二维码 + 提示 ======
    base = f"{request.url.scheme}://{request.url.netloc}"
    qr_url = f"{base}/#/login?mode=register"
    qr_img = _build_qr(qr_url, size=140)
    img.paste(qr_img, (W // 2 - 70, 1140))

    f_qr_tip = _font(18)
    qr_tip = "扫码加入 · 与你一起练"
    bbox = draw.textbbox((0, 0), qr_tip, font=f_qr_tip)
    draw.text(((W - (bbox[2] - bbox[0])) // 2, 1290), qr_tip,
              fill=COLOR_MUTED, font=f_qr_tip)

    # ====== 输出 ======
    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=True)
    return Response(content=buf.getvalue(), media_type="image/png", headers={
        "Cache-Control": "private, max-age=3600",
    })
