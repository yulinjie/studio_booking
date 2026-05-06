"""
全面回归测试 — 覆盖所有 33 个 API + 边界场景 + 权限。

用法：
    1) 确保 backend 启动：uvicorn app.main:app --port 8769
    2) 删掉 studio.db, 重 seed: python -m app.seed
    3) 运行：python test_regression.py
"""
import sys, json, time
from datetime import datetime, timedelta
from urllib.request import Request, urlopen
from urllib.parse import quote
from urllib.error import HTTPError, URLError

BASE = "http://127.0.0.1:8769/api"

# ---------- 测试框架 ----------
PASS = 0
FAIL = 0
FAILED_LIST = []

def req(method, path, token=None, body=None):
    data = json.dumps(body).encode("utf-8") if body is not None else None
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    safe_path = quote(path, safe="/?&=,:.%-+")
    r = Request(f"{BASE}{safe_path}", data=data, headers=headers, method=method)
    try:
        resp = urlopen(r, timeout=10)
        raw = resp.read().decode("utf-8")
        return resp.status, (json.loads(raw) if raw else None)
    except HTTPError as e:
        raw = e.read().decode("utf-8")
        return e.code, (json.loads(raw) if raw else None)

def expect(label, actual, expected, body=None, predicate=None):
    """expected 是值；callable 用于自定义判定；tuple 直接做相等比较（不再当作 OR）"""
    global PASS, FAIL
    if predicate:
        ok = predicate(actual, body)
    elif callable(expected):
        ok = expected(actual)
    else:
        ok = actual == expected
    if ok:
        PASS += 1
        print(f"  ✅ {label}")
    else:
        FAIL += 1
        FAILED_LIST.append(label)
        print(f"  ❌ {label} → 实际 {actual}, 期望 {expected}; body={body}")
    return ok

def section(title):
    print(f"\n=== {title} ===")

def login(phone, pwd):
    code, d = req("POST", "/auth/login", body={"phone": phone, "password": pwd})
    if code != 200:
        raise SystemExit(f"login failed for {phone}: {d}")
    return d["access_token"], d["user"]


# ============================================
# 0. 健康检查 + 服务可用性
# ============================================
section("0. 服务可用性")
try:
    code, d = req("GET", "/health")
except URLError:
    print("❌ 后端未启动，请先 uvicorn app.main:app --port 8769")
    sys.exit(1)
expect("GET /api/health 返回 200", code, 200)
expect("health body ok=True", d.get("ok"), True)


# ============================================
# 1. 认证 Auth
# ============================================
section("1. 认证 (Auth)")

code, d = req("POST", "/auth/login", body={"phone": "13800000000", "password": "wrong"})
expect("错误密码登录 → 401", code, 401)

code, d = req("POST", "/auth/login", body={"phone": "13800000000", "password": "admin123"})
expect("正确密码登录 → 200", code, 200)
expect("登录返回 access_token", "access_token" in (d or {}), True)
expect("登录用户 role=admin", d["user"]["role"], "admin")
admin_token = d["access_token"]

code, d = req("GET", "/auth/me", admin_token)
expect("GET /auth/me with token → 200", code, 200)

code, d = req("GET", "/auth/me")
expect("GET /auth/me 无 token → 401", code, 401)

code, d = req("GET", "/auth/me", "invalid.token.value")
expect("GET /auth/me 错误 token → 401", code, 401)

code, d = req("POST", "/auth/register", body={"phone": "19900000001", "password": "test1234", "name": "回归测试"})
expect("注册新用户 → 200", code, 200)
expect("注册用户 role=member", d["user"]["role"], "member")
test_member_token = d["access_token"]
test_member_id = d["user"]["id"]

code, d = req("POST", "/auth/register", body={"phone": "19900000001", "password": "test1234", "name": "重复"})
expect("重复手机号注册 → 400", code, 400)


# ============================================
# 2. 会员管理 Members
# ============================================
section("2. 会员管理 (Members)")

# 后台创建会员
body = {"phone": "19900001001", "name": "测试甲", "gender": "female"}
code, member1 = req("POST", "/admin/members", admin_token, body)
expect("admin 创建会员 → 200", code, 200)
expect("默认 role=member", member1["role"], "member")

# 重复手机号
code, _ = req("POST", "/admin/members", admin_token, body)
expect("重复手机号创建 → 400", code, 400)

# 用默认密码登录（手机号后 6 位）
code, d = req("POST", "/auth/login", body={"phone": "19900001001", "password": "001001"})
expect("默认密码 = 手机号后6位，可登录 → 200", code, 200)

# 列表
code, page = req("GET", "/admin/members", admin_token)
expect("管理员列会员 → 200", code, 200)
expect("列表分页含 items/total/page/size", set(page.keys()) >= {"items","total","page","size"}, True)

# 搜索
code, page = req("GET", "/admin/members?q=测试甲", admin_token)
expect("按姓名搜索匹配", any(m["name"] == "测试甲" for m in page["items"]), True)

# 角色过滤
code, page = req("GET", "/admin/members?role=admin", admin_token)
expect("按 role=admin 过滤只返回 admin", all(m["role"] == "admin" for m in page["items"]), True)

# 分页
code, page = req("GET", "/admin/members?page=1&size=2", admin_token)
expect("分页 size=2 返回 ≤2 条", len(page["items"]) <= 2, True)

# 详情
code, d = req("GET", f"/admin/members/{member1['id']}", admin_token)
expect("会员详情 → 200", code, 200)

code, d = req("GET", "/admin/members/99999", admin_token)
expect("不存在会员 → 404", code, 404)

# 更新
code, d = req("PATCH", f"/admin/members/{member1['id']}", admin_token, {"note": "回归备注"})
expect("更新会员备注 → 200", code, 200)
expect("note 已更新", d["note"], "回归备注")

# 重置密码
code, _ = req("POST", f"/admin/members/{member1['id']}/reset-password", admin_token, {"new_password": "newpass1"})
expect("重置密码 → 200", code, 200)
code, _ = req("POST", "/auth/login", body={"phone": "19900001001", "password": "newpass1"})
expect("新密码可登录 → 200", code, 200)

# 停用
code, _ = req("POST", f"/admin/members/{member1['id']}/deactivate", admin_token)
expect("停用会员 → 200", code, 200)
code, _ = req("POST", "/auth/login", body={"phone": "19900001001", "password": "newpass1"})
expect("停用后无法登录 → 401", code, 401)

# 启用
code, _ = req("POST", f"/admin/members/{member1['id']}/activate", admin_token)
expect("启用会员 → 200", code, 200)
code, d = req("POST", "/auth/login", body={"phone": "19900001001", "password": "newpass1"})
expect("启用后可登录 → 200", code, 200)
member1_token = d["access_token"]

# 自助更新
code, d = req("PATCH", "/me", member1_token, {"name": "测试甲改名"})
expect("会员自助改名 → 200", code, 200)
expect("name 已更新", d["name"], "测试甲改名")

# 权限：会员调 admin 接口
code, d = req("GET", "/admin/members", member1_token)
expect("会员调 /admin/members → 403", code, 403)

# 权限：无 token
code, _ = req("POST", "/admin/members", body={"phone": "x", "name": "y"})
expect("无 token 创建会员 → 401", code, 401)


# ============================================
# 3. 卡种模板
# ============================================
section("3. 卡种模板 (CardTemplate)")

code, lst = req("GET", "/card-templates", admin_token)
expect("列卡种 → 200", code, 200)
expect("种子已建 4 张卡", len(lst) >= 4, True)

code, lst = req("GET", "/admin/card-templates", admin_token)
expect("admin 列卡种 → 200", code, 200)

# 新建卡种
body = {"name": "回归测试-50次卡", "type": "times", "price": 200000, "initial_credits": 50, "valid_days": 365}
code, tmpl = req("POST", "/admin/card-templates", admin_token, body)
expect("创建卡种 → 200", code, 200)

# 更新
code, _ = req("PATCH", f"/admin/card-templates/{tmpl['id']}", admin_token, {"price": 180000})
expect("更新价格 → 200", code, 200)

# 软删除
code, _ = req("DELETE", f"/admin/card-templates/{tmpl['id']}", admin_token)
expect("下架卡种 → 200", code, 200)
code, lst = req("GET", "/card-templates", admin_token)
expect("下架后不在 active 列表", any(t["id"] == tmpl["id"] for t in lst), False)
code, lst = req("GET", "/admin/card-templates", admin_token)
expect("下架后仍在 admin 列表（软删）", any(t["id"] == tmpl["id"] for t in lst), True)

# 权限
code, _ = req("POST", "/admin/card-templates", member1_token, body)
expect("会员创建卡种 → 403", code, 403)


# ============================================
# 4. 会员卡 + 流水
# ============================================
section("4. 会员卡 (MemberCard) + 流水")

# 给 member1 开 4 种卡
issued = {}
for tid, label in [(1, "次卡"), (2, "期限卡"), (3, "课包"), (4, "储值卡")]:
    body = {"member_id": member1["id"], "template_id": tid, "method": "wechat_qr"}
    code, r = req("POST", "/admin/cards/issue", admin_token, body)
    expect(f"开{label}（template_id={tid}） → 200", code, 200)
    if r:
        issued[tid] = r["card"]

# 列卡
code, cards = req("GET", f"/admin/cards?member_id={member1['id']}", admin_token)
expect("列会员卡 ≥ 4 张", len(cards) >= 4, True)

# 按 status 过滤
code, cards = req("GET", "/admin/cards?status=active", admin_token)
expect("按 status=active 过滤 → 200", code, 200)
expect("过滤结果都是 active", all(c["status"] == "active" for c in cards), True)

# 卡详情
times_card = issued[1]
code, d = req("GET", f"/admin/cards/{times_card['id']}", admin_token)
expect("卡详情 → 200", code, 200)

# 流水
code, txs = req("GET", f"/admin/cards/{times_card['id']}/transactions", admin_token)
expect("初始流水 = 1 条 (purchase)", len(txs) == 1 and txs[0]["type"] == "purchase", True)

# 调整次数
code, d = req("POST", f"/admin/cards/{times_card['id']}/adjust", admin_token, {"credits_delta": 5, "note": "回归测试"})
expect("调整 +5 次 → 200", code, 200)
expect("调整后剩余次数 = 10+5 = 15", d["remaining_credits"], 15)

# 调整 0/0
code, _ = req("POST", f"/admin/cards/{times_card['id']}/adjust", admin_token, {"credits_delta": 0, "balance_delta": 0})
expect("调整 0/0 → 400", code, 400)

# 冻结/解冻
code, _ = req("POST", f"/admin/cards/{times_card['id']}/freeze", admin_token)
expect("冻结卡 → 200", code, 200)
code, d = req("GET", f"/admin/cards/{times_card['id']}", admin_token)
expect("冻结后 status=frozen", d["status"], "frozen")
code, _ = req("POST", f"/admin/cards/{times_card['id']}/unfreeze", admin_token)
code, d = req("GET", f"/admin/cards/{times_card['id']}", admin_token)
expect("解冻后 status=active", d["status"], "active")

# 会员看自己的卡
code, my_cards = req("GET", "/me/cards", member1_token)
expect("会员看自己卡 → 200", code, 200)
expect("会员看自己卡数 = admin 看到的", len(my_cards) == len(issued), True)

# 看流水
code, _ = req("GET", f"/me/cards/{times_card['id']}/transactions", member1_token)
expect("会员看自己卡流水 → 200", code, 200)

# 看别人的卡
admin_card_id = times_card["id"]
test_member_login_code, _ = req("POST", "/auth/login", body={"phone": "19900000001", "password": "test1234"})
test_token, _ = login("19900000001", "test1234")
code, _ = req("GET", f"/me/cards/{admin_card_id}/transactions", test_token)
expect("跨账号看别人卡 → 404", code, 404)

# 订单
code, orders = req("GET", "/admin/orders", admin_token)
expect("列订单 → 200", code, 200)
expect("有 4 个购卡订单", len(orders) >= 4, True)


# ============================================
# 5. 课程类型 / 课程
# ============================================
section("5. 课程类型 + 课程")

code, cats = req("GET", "/course-categories", admin_token)
expect("列课程类型 → 200", code, 200)
expect("种子有 4 个类型", len(cats) >= 4, True)

# 新建类型
code, _ = req("POST", "/admin/course-categories", admin_token, {
    "name": "回归测试类型", "code": "regression_test", "min_capacity": 1, "max_capacity": 5,
})
expect("创建课程类型 → 200", code, 200)

# 重复 code
code, _ = req("POST", "/admin/course-categories", admin_token, {
    "name": "重复code", "code": "regression_test", "min_capacity": 1, "max_capacity": 5,
})
expect("重复 code → 400", code, 400)

# 课程
code, courses = req("GET", "/courses", admin_token)
expect("列课程 → 200", code, 200)

code, course = req("POST", "/admin/courses", admin_token, {
    "category_id": 1, "name": "回归测试-阴瑜伽", "duration_minutes": 75, "capacity": 8, "credit_cost": 1, "price": 9000,
})
expect("创建课程 → 200", code, 200)

code, _ = req("POST", "/admin/courses", admin_token, {
    "category_id": 9999, "name": "x", "duration_minutes": 60,
})
expect("创建课程引用不存在的 category → 400", code, 400)

code, _ = req("PATCH", f"/admin/courses/{course['id']}", admin_token, {"capacity": 10})
expect("更新课程容量 → 200", code, 200)


# ============================================
# 6. 排课 (ClassSession)
# ============================================
section("6. 排课 (Sessions)")

# 单节
start_at = (datetime.utcnow() + timedelta(days=2)).replace(hour=10, minute=0, second=0, microsecond=0)
code, sess = req("POST", "/admin/sessions", admin_token, {
    "course_id": course["id"], "start_at": start_at.isoformat(), "capacity": 3, "room": "A室",
})
expect("单节排课 → 200", code, 200)
single_sid = sess["id"]
expect("end_at 自动按时长推算", sess["end_at"] is not None, True)

# 引用不存在课程
code, _ = req("POST", "/admin/sessions", admin_token, {
    "course_id": 99999, "start_at": start_at.isoformat(),
})
expect("不存在课程排课 → 400", code, 400)

# 批量
code, batch = req("POST", "/admin/sessions/batch", admin_token, {
    "course_id": course["id"], "weekdays": [0, 2, 4], "time_of_day": "20:00",
    "start_date": (datetime.utcnow() + timedelta(days=14)).isoformat(),
    "weeks": 4, "capacity": 6, "room": "B室",
})
expect("批量排课 (3 天/周 × 4 周) → 200", code, 200)
expect("批量返回 12 节课", len(batch) == 12, True)

# 查列表
end = (datetime.utcnow() + timedelta(days=60)).isoformat()
start = (datetime.utcnow() - timedelta(days=1)).isoformat()
code, lst = req("GET", f"/sessions?start={start}&end={end}", admin_token)
expect("列排课（含批量产生的） → 200", code, 200)
expect("能看到 ≥13 节（单+批）", len(lst) >= 13, True)

# 按课程过滤
code, lst = req("GET", f"/sessions?start={start}&end={end}&course_id={course['id']}", admin_token)
expect("按 course_id 过滤", all(s["course_id"] == course["id"] for s in lst), True)

# only_open
code, lst = req("GET", f"/sessions?start={start}&end={end}&only_open=true", admin_token)
expect("only_open 过滤", all(s["status"] == "scheduled" for s in lst), True)

# 修改容量低于已预约（先不在这测，没人预约这个 session）
# 取消整节
code, batch_to_cancel = req("POST", "/admin/sessions", admin_token, {
    "course_id": course["id"], "start_at": (datetime.utcnow() + timedelta(days=20)).isoformat(),
})
code, _ = req("POST", f"/admin/sessions/{batch_to_cancel['id']}/cancel", admin_token)
expect("取消整节排课 → 200", code, 200)
code, d = req("GET", f"/sessions?start={start}&end={end}", admin_token)
sd = next((s for s in d if s["id"] == batch_to_cancel["id"]), None)
expect("取消后 status=cancelled", sd["status"] if sd else None, "cancelled")


# ============================================
# 7. 预约 Booking — 主战场
# ============================================
section("7. 预约 (Booking) — 满员/候补/取消/签到/爽约")

# 准备 4 个会员都有 10 次卡（次卡 template_id=1）
booking_members = []
for i, (p, n) in enumerate([
    ("19900007001", "甲乙"), ("19900007002", "丙丁"), ("19900007003", "戊己"), ("19900007004", "庚辛"),
]):
    code, m = req("POST", "/admin/members", admin_token, {"phone": p, "name": n})
    if code != 200:
        # 已存在 → 拉
        code, page = req("GET", f"/admin/members?q={n}", admin_token)
        m = page["items"][0] if page["items"] else None
    if m:
        # 开次卡（团课用）
        req("POST", "/admin/cards/issue", admin_token, {
            "member_id": m["id"], "template_id": 1, "method": "wechat_qr",
        })
    booking_members.append(m)

# 用流瑜伽（团课，course_id=1）建一节容量=2 的课，明天
session_start = (datetime.utcnow() + timedelta(days=1)).replace(hour=15, minute=0, second=0, microsecond=0)
code, b_sess = req("POST", "/admin/sessions", admin_token, {
    "course_id": 1, "start_at": session_start.isoformat(), "capacity": 2, "room": "测试室",
})
expect("建容量=2 的测试排课 → 200", code, 200)
b_sid = b_sess["id"]

# 4 人依次约
booking_results = []
for m in booking_members:
    t, _ = login(m["phone"], m["phone"][-6:])
    code, r = req("POST", "/bookings", t, {"session_id": b_sid})
    booking_results.append((m, t, code, r))

expect("4 人都能 POST → 200", all(c == 200 for _, _, c, _ in booking_results), True)
expect("第 1 人成功（waitlisted=False）", booking_results[0][3]["waitlisted"], False)
expect("第 2 人成功（waitlisted=False）", booking_results[1][3]["waitlisted"], False)
expect("第 3 人候补（waitlisted=True, order=1）",
       booking_results[2][3]["waitlisted"] and booking_results[2][3]["booking"]["waitlist_order"] == 1, True)
expect("第 4 人候补（waitlisted=True, order=2）",
       booking_results[3][3]["waitlisted"] and booking_results[3][3]["booking"]["waitlist_order"] == 2, True)

# 重复预约
m1, t1, _, r1 = booking_results[0]
code, _ = req("POST", "/bookings", t1, {"session_id": b_sid})
expect("重复预约 → 400", code, 400)

# 已开始的课不能约（用 -1 天）
past_at = (datetime.utcnow() - timedelta(days=1)).isoformat()
code, past_sess = req("POST", "/admin/sessions", admin_token, {"course_id": 1, "start_at": past_at})
code, _ = req("POST", "/bookings", t1, {"session_id": past_sess["id"]})
expect("已过开始时间的课 → 400", code, 400)

# 状态=cancelled 的课不能约
req("POST", f"/admin/sessions/{batch_to_cancel['id']}/cancel", admin_token)  # 再 cancel 一次幂等
code, _ = req("POST", "/bookings", t1, {"session_id": batch_to_cancel["id"]})
expect("已取消的课不能约 → 400", code, 400)

# 不存在 session
code, _ = req("POST", "/bookings", t1, {"session_id": 99999})
expect("不存在 session 预约 → 404", code, 404)

# 看 booked_count
code, all_sessions = req("GET", f"/sessions?start={start}&end={end}", admin_token)
target = next(s for s in all_sessions if s["id"] == b_sid)
expect("booked_count = 2", target["booked_count"], 2)
expect("capacity = 2", target["capacity"], 2)

# 看 m1 卡次数：从 10 变 9（约了 1 次）
code, m1_cards = req("GET", "/me/cards", t1)
times_card_m1 = next((c for c in m1_cards if c["type"] == "times" and c["applicable_category_id"] == 1), m1_cards[0])
expect("约后次卡 -1 次 (10→9)", times_card_m1["remaining_credits"], 9)

# m1 取消（明天 15:00 - 24h = 今天 15:00，可能已超时也可能没过；按团课默认 24h）
m1_booking_id = booking_results[0][3]["booking"]["id"]
code, cancelled = req("POST", f"/bookings/{m1_booking_id}/cancel", t1)
expect("m1 取消 → 200", code, 200)
# 这里取决于当前时间和明天的距离：>24h 应该 cancelled，≤24h 应该 late_cancelled
# 不强行断定，但记录
print(f"      [信息] m1 取消状态 = {cancelled['status']}")

# 候补晋升：取消（含 late_cancelled）都释放容量，所以 m3 都应被晋升
# 区别仅在 late_cancelled 不退卡次（m1 卡 -1，cancelled 时退回）
code, all_b = req("GET", f"/admin/sessions/{b_sid}/bookings", admin_token)
m3 = booking_members[2]
m3_b = next(b for b in all_b if b["member_id"] == m3["id"])
expect("取消后 m3 候补晋升为 booked", m3_b["status"], "booked")
# 验证 m1 卡次（如 late_cancelled，不返还）
code, m1_cards_after = req("GET", "/me/cards", t1)
times_m1_after = next((c for c in m1_cards_after if c["type"] == "times" and c["applicable_category_id"] == 1), m1_cards_after[0])
if cancelled["status"] == "cancelled":
    expect("正常取消返还次数（10→10）", times_m1_after["remaining_credits"], 10)
else:
    expect("超时取消不返还（仍 9）", times_m1_after["remaining_credits"], 9)

# 取消候补
m4 = booking_members[3]
t4, _ = login(m4["phone"], m4["phone"][-6:])
m4_booking_id = booking_results[3][3]["booking"]["id"]
code, cancelled4 = req("POST", f"/bookings/{m4_booking_id}/cancel", t4)
expect("候补取消 → 200", code, 200)
expect("候补取消状态 = cancelled", cancelled4["status"], "cancelled")

# 后台代取消（强制返还）
m2, t2, _, r2 = booking_results[1]
m2_booking_id = booking_results[1][3]["booking"]["id"]
code, ac = req("POST", f"/bookings/{m2_booking_id}/cancel", admin_token)
expect("后台代取消 → 200", code, 200)
expect("后台代取消即使超时也按 cancelled", ac["status"], "cancelled")

# 签到 — 找一个还在 booked 状态的预约
code, bs = req("GET", f"/admin/sessions/{b_sid}/bookings", admin_token)
booked_ones = [b for b in bs if b["status"] == "booked"]
if booked_ones:
    code, ci = req("POST", "/admin/check-in", admin_token, {"booking_id": booked_ones[0]["id"]})
    expect("签到 → 200", code, 200)
    expect("签到后 status=attended", ci["status"], "attended")

# 签到非法状态（已取消的不能签到）
if cancelled["status"] in ("cancelled", "late_cancelled"):
    code, _ = req("POST", "/admin/check-in", admin_token, {"booking_id": m1_booking_id})
    expect("已取消预约签到 → 400", code, 400)

# 不存在的 booking
code, _ = req("POST", "/admin/check-in", admin_token, {"booking_id": 99999})
expect("不存在 booking 签到 → 404", code, 404)

# 批量爽约
batch_no_show_at = (datetime.utcnow() + timedelta(days=3)).replace(hour=10, minute=0, second=0, microsecond=0)
code, ns_sess = req("POST", "/admin/sessions", admin_token, {
    "course_id": 1, "start_at": batch_no_show_at.isoformat(), "capacity": 5,
})
m1_again_t, _ = login(booking_members[0]["phone"], booking_members[0]["phone"][-6:])
req("POST", "/bookings", m1_again_t, {"session_id": ns_sess["id"]})
code, ns_r = req("POST", f"/admin/sessions/{ns_sess['id']}/no-show", admin_token)
expect("课后批量爽约 → 200", code, 200)
expect("标记数 ≥ 1", ns_r["marked"] >= 1, True)

# 我的预约
code, my_b = req("GET", "/me/bookings", t1)
expect("会员看自己预约 → 200", code, 200)
expect("upcoming=true 默认", isinstance(my_b, list), True)

code, all_my_b = req("GET", "/me/bookings?upcoming=false", t1)
expect("upcoming=false 看全部预约 → 200", code, 200)

# 后台代约 — 用一节全新的、未 finished 的课
agent_at = (datetime.utcnow() + timedelta(days=4)).replace(hour=11, minute=0, second=0, microsecond=0)
code, agent_sess = req("POST", "/admin/sessions", admin_token, {
    "course_id": 1, "start_at": agent_at.isoformat(), "capacity": 5,
})
code, admin_book = req("POST", "/bookings", admin_token, {
    "session_id": agent_sess["id"], "member_id": booking_members[1]["id"],
})
expect("后台代约 → 200", code, 200)
expect("代约者 = 指定 member", admin_book["booking"]["member_id"], booking_members[1]["id"])

# 非会员（admin）自助预约
code, _ = req("POST", "/bookings", admin_token, {"session_id": agent_sess["id"]})
expect("admin 不带 member_id 预约自己 → 400", code, 400)

# 后台 list_all_bookings
code, all_b = req("GET", "/admin/bookings", admin_token)
expect("后台列所有预约 → 200", code, 200)


# ============================================
# 8. 跨权限 / 边界
# ============================================
section("8. 权限 + 边界")

# member 不能看后台预约列表
code, _ = req("GET", "/admin/bookings", t1)
expect("会员调 /admin/bookings → 403", code, 403)

# member 不能签到别人
code, _ = req("POST", "/admin/check-in", t1, {"booking_id": 1})
expect("会员调签到 → 403", code, 403)

# member 不能取消别人的预约
m1_active = next((b for b in all_b if b["member_id"] == booking_members[0]["id"] and b["status"] == "booked"), None)
if m1_active:
    code, _ = req("POST", f"/bookings/{m1_active['id']}/cancel", t2)
    expect("会员取消别人预约 → 403", code, 403)


# ============================================
# 9. P0 新功能 — 修改密码 / 退卡 / 导出 / 上传 / 二维码 / 自动结算 / 紧急联系 / 审计
# ============================================
section("9. P0 紧急联系人 + 健康备注")

# 创建带紧急字段的会员
import json as _json
body = {
    "phone": "19900099001", "name": "紧急测试",
    "emergency_contact_name": "妈妈", "emergency_contact_phone": "13899998888",
    "health_note": "颈椎旧伤，避免后弯",
}
code, m_emerg = req("POST", "/admin/members", admin_token, body)
expect("创建会员（带紧急字段） → 200", code, 200)
expect("emergency_contact_name 已保存", m_emerg.get("emergency_contact_name"), "妈妈")
expect("health_note 已保存", m_emerg.get("health_note"), "颈椎旧伤，避免后弯")

# 自助修改紧急联系人
emerg_token, _ = login("19900099001", "099001")
code, d = req("PATCH", "/me", emerg_token, {"emergency_contact_name": "爸爸"})
expect("会员自助改紧急联系人", d.get("emergency_contact_name"), "爸爸")

# 后台编辑紧急字段
code, d = req("PATCH", f"/admin/members/{m_emerg['id']}", admin_token, {"health_note": "已恢复"})
expect("后台修改 health_note", d.get("health_note"), "已恢复")


section("10. P0 自动结算（lazy settle）")

import sqlite3
import os
db_path = os.environ.get("DATABASE_URL", "sqlite:///./regression.db").replace("sqlite:///", "")
conn = sqlite3.connect(db_path)
cur = conn.cursor()
past_start = (datetime.utcnow() - timedelta(hours=2)).isoformat()
past_end = (datetime.utcnow() - timedelta(hours=1)).isoformat()
cur.execute(
    "INSERT INTO classsession (course_id, start_at, end_at, capacity, booked_count, status, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
    (1, past_start, past_end, 5, 0, "scheduled", past_start),
)
past_sid = cur.lastrowid
conn.commit()
conn.close()

# 触发 GET /sessions 应该自动结算
range_start = (datetime.utcnow() - timedelta(days=1)).isoformat()
range_end = (datetime.utcnow() + timedelta(days=1)).isoformat()
code, lst = req("GET", f"/sessions?start={range_start}&end={range_end}", admin_token)
target = next((s for s in lst if s["id"] == past_sid), None)
expect("已结束课节自动 finished", target.get("status") if target else None, "finished")


section("11. P0 退卡退款")

# 给"紧急测试"开一张卡
code, r = req("POST", "/admin/cards/issue", admin_token, {
    "member_id": m_emerg["id"], "template_id": 1, "method": "wechat_qr",
})
expect("开卡 → 200", code, 200)
refund_card_id = r["card"]["id"]

# 让他先约一节未来的课
future_start = (datetime.utcnow() + timedelta(days=5)).replace(hour=14, minute=0, second=0, microsecond=0)
code, fut_sess = req("POST", "/admin/sessions", admin_token, {"course_id": 1, "start_at": future_start.isoformat()})
emerg_token, _ = login("19900099001", "099001")
code, b_r = req("POST", "/bookings", emerg_token, {"session_id": fut_sess["id"]})
expect("退卡前先预约一节 → 200", code, 200)

# 退卡
code, refund_r = req("POST", f"/admin/cards/{refund_card_id}/refund", admin_token, {
    "refund_amount": 80000, "note": "回归测试-退卡",
})
expect("退卡 → 200", code, 200)
expect("退卡返回 refund_amount=80000", refund_r.get("refund_amount"), 80000)
expect("退卡级联取消 ≥1 条预约", refund_r.get("cancelled_bookings", 0) >= 1, True)
expect("退卡后 status=refunded", refund_r["card"]["status"], "refunded")

# 重复退卡
code, _ = req("POST", f"/admin/cards/{refund_card_id}/refund", admin_token, {"refund_amount": 100, "note": "x"})
expect("已退卡再退 → 400", code, 400)

# 验证流水有 card_refund
code, txs = req("GET", f"/admin/cards/{refund_card_id}/transactions", admin_token)
expect("流水包含 card_refund", any(t["type"] == "card_refund" for t in txs), True)


section("12. P0 数据导出 CSV")

import urllib.request as _u

def _raw_get(path: str) -> tuple:
    r = _u.urlopen(_u.Request(f"{BASE}{path}", headers={"Authorization": f"Bearer {admin_token}"}))
    return r.status, r.read()

for endpoint in ("members", "orders", "bookings"):
    status, body = _raw_get(f"/admin/export/{endpoint}.csv")
    expect(f"{endpoint}.csv → 200", status, 200)
    expect(f"{endpoint}.csv 含 UTF-8 BOM", body.startswith(b"\xef\xbb\xbf"), True)

_, csv_bytes = _raw_get("/admin/export/members.csv")
expect("members.csv 含中文表头'紧急联系人'", "紧急联系人".encode("utf-8") in csv_bytes, True)
expect("members.csv 至少 2 行（表头+1）", csv_bytes.count(b"\n") >= 2, True)


section("13. P0 文件上传 + 二维码")

# 上传图片
import uuid as _uuid
png_bytes = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\rIDATx\x9cc\xfc\xcf\xc0\x00\x00\x00\x03\x00\x01\x9bX\x88\x80\x00\x00\x00\x00IEND\xaeB`\x82'
boundary = _uuid.uuid4().hex
mp_body = b''
mp_body += f"--{boundary}\r\n".encode()
mp_body += b'Content-Disposition: form-data; name="file"; filename="t.png"\r\n'
mp_body += b'Content-Type: image/png\r\n\r\n'
mp_body += png_bytes + b'\r\n'
mp_body += f"--{boundary}--\r\n".encode()
r = _u.Request(f"{BASE}/admin/upload", data=mp_body, headers={
    "Authorization": f"Bearer {admin_token}",
    "Content-Type": f"multipart/form-data; boundary={boundary}",
})
resp = _u.urlopen(r)
upload_data = _json.loads(resp.read().decode())
expect("上传图片 → 200", resp.status, 200)
expect("返回 url 以 /uploads/ 开头", upload_data.get("url", "").startswith("/uploads/"), True)

# GET 上传的图片
url = upload_data["url"]
r = _u.urlopen(f"{BASE.replace('/api','')}{url}")
expect("上传后可 GET 图片", r.status, 200)

# 上传非图片（应被拒）
mp_body = (
    f"--{boundary}\r\n".encode() +
    b'Content-Disposition: form-data; name="file"; filename="t.exe"\r\n'
    b'Content-Type: application/octet-stream\r\n\r\n'
    b'fake' + b'\r\n' +
    f"--{boundary}--\r\n".encode()
)
r = _u.Request(f"{BASE}/admin/upload", data=mp_body, headers={
    "Authorization": f"Bearer {admin_token}",
    "Content-Type": f"multipart/form-data; boundary={boundary}",
})
try:
    _u.urlopen(r)
    expect("上传非图片应 400", "200", "400")  # 不应到这里
except _u.HTTPError as e:
    expect("上传非图片应 400", e.code, 400)

# 二维码
r = _u.urlopen(f"{BASE}/studio/registration-qr.png")
qr_bytes = r.read()
expect("二维码 PNG → 200", r.status, 200)
expect("PNG 头部正确", qr_bytes.startswith(b"\x89PNG"), True)

code, d = req("GET", "/studio/registration-url", admin_token)
expect("注册链接含 mode=register", "mode=register" in d.get("url", ""), True)


section("14. P0 审计日志")

code, logs = req("GET", "/admin/audit-logs", admin_token)
expect("查审计日志 → 200", code, 200)

# 验证关键 action 都记录了
actions = {l["action"] for l in logs}
for expected_action in ["card.issue", "card.refund", "booking.create", "booking.cancel", "booking.check_in"]:
    expect(f"审计日志包含 {expected_action}", expected_action in actions, True)

# 按 action 过滤
code, refund_logs = req("GET", "/admin/audit-logs?action=card.refund", admin_token)
expect("按 card.refund 过滤", all(l["action"] == "card.refund" for l in refund_logs), True)

# 会员不能看审计日志
code, _ = req("GET", "/admin/audit-logs", emerg_token)
expect("会员看审计日志 → 403", code, 403)


section("15. P0 修改密码（放最后，改完后重新登录）")

# 错原密码
code, _ = req("POST", "/me/change-password", admin_token, {"old_password": "wrong", "new_password": "newpass99"})
expect("错原密码改密 → 400", code, 400)

# 新旧相同
code, _ = req("POST", "/me/change-password", admin_token, {"old_password": "admin123", "new_password": "admin123"})
expect("新密码与原密码相同 → 400", code, 400)

# 正确改密
code, _ = req("POST", "/me/change-password", admin_token, {"old_password": "admin123", "new_password": "newpass99"})
expect("修改密码 → 200", code, 200)

# 用新密码登录
code, d = req("POST", "/auth/login", body={"phone": "13800000000", "password": "newpass99"})
expect("新密码可登录", code, 200)

# 旧密码失败
code, _ = req("POST", "/auth/login", body={"phone": "13800000000", "password": "admin123"})
expect("旧密码不能登录 → 401", code, 401)


# ============================================
# 总结
# ============================================
print(f"\n{'=' * 60}")
print(f"全部测试：{PASS + FAIL} 项 | ✅ {PASS} 通过 | ❌ {FAIL} 失败")
if FAILED_LIST:
    print("\n失败用例：")
    for f in FAILED_LIST:
        print(f"  - {f}")
sys.exit(0 if FAIL == 0 else 1)
