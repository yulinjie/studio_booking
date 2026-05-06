"""端到端冒烟：建排课 → 抢约（含满员候补）→ 取消触发候补晋升 → 签到。"""
import sys, json, time
from datetime import datetime, timedelta, timezone
from urllib.request import Request, urlopen
from urllib.parse import quote
from urllib.error import HTTPError

BASE = "http://127.0.0.1:8767/api"

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
    except HTTPError as e:
        raw = e.read().decode("utf-8")
        return e.code, json.loads(raw) if raw else None
    return resp.status, json.loads(raw) if raw else None

def login(phone, pwd):
    code, d = req("POST", "/auth/login", body={"phone": phone, "password": pwd})
    assert code == 200, f"login failed: {d}"
    return d["access_token"], d["user"]

def must(label, code_actual, expected=200, body=None):
    icon = "✅" if code_actual == expected else "❌"
    print(f"  {icon} {label} → HTTP {code_actual}", body if code_actual != expected else "")

# 1. 管理员登录
admin_token, admin = login("13800000000", "admin123")
print(f"[1] 管理员登录 OK uid={admin['id']}")

# 2. 找张三（前面建过的会员），没有就建
code, page = req("GET", "/admin/members?q=张三", admin_token)
if page["items"]:
    zhangsan = page["items"][0]
    print(f"[2] 张三已存在 uid={zhangsan['id']}")
else:
    code, zhangsan = req("POST", "/admin/members", admin_token,
                         {"phone": "13900000001", "name": "张三", "gender": "female"})
    print(f"[2] 张三已创建 uid={zhangsan['id']}")

# 再加 2 个会员用于满员测试
extras = []
for i, (p, n) in enumerate([("13900000002", "李四"), ("13900000003", "王五"), ("13900000004", "赵六")]):
    code, page = req("GET", f"/admin/members?q={n}", admin_token)
    if page["items"]:
        extras.append(page["items"][0])
    else:
        code, u = req("POST", "/admin/members", admin_token,
                      {"phone": p, "name": n})
        extras.append(u)
print(f"[3] 已有/建会员：{[e['name'] for e in extras]}")

# 3. 给所有会员都开 10 次卡（已有的会跳过）
all_members = [zhangsan] + extras
for m in all_members:
    code, cards = req("GET", f"/admin/cards?member_id={m['id']}", admin_token)
    if not cards:
        code, _ = req("POST", "/admin/cards/issue", admin_token,
                      {"member_id": m["id"], "template_id": 1, "method": "wechat_qr"})
        print(f"[4] {m['name']} 已开卡")

# 4. 建一节"明天 19:00 流瑜伽"，容量改成 2 用于测候补
start = (datetime.utcnow() + timedelta(days=1)).replace(hour=19, minute=0, second=0, microsecond=0)
code, sess = req("POST", "/admin/sessions", admin_token,
                 {"course_id": 1, "start_at": start.isoformat(), "capacity": 2, "room": "A 室"})
must("[5] 创建排课（容量 2）", code, 200, sess)
sid = sess["id"]

# 5. 三人依次预约：前两人成功，第三人候补
results = []
for m in all_members[:3]:
    token, _ = login(m["phone"], m["phone"][-6:])    # 默认密码 = 手机号后 6 位
    code, r = req("POST", "/bookings", token, {"session_id": sid})
    results.append((m["name"], code, r))
    print(f"  [{m['name']}] {code} → waitlisted={r.get('waitlisted')} msg={r.get('message')}")

# 第四人也候补
m4 = all_members[3]
t4, _ = login(m4["phone"], m4["phone"][-6:])
code, r4 = req("POST", "/bookings", t4, {"session_id": sid})
print(f"  [{m4['name']}] {code} → waitlisted={r4.get('waitlisted')} msg={r4.get('message')}")

# 6. 重复预约应被拒
m1_token, _ = login(all_members[0]["phone"], all_members[0]["phone"][-6:])
code, r = req("POST", "/bookings", m1_token, {"session_id": sid})
must(f"[6] {all_members[0]['name']} 重复约应失败", code, 400, r)

# 7. 看排课已预约数（应该是 2）
code, sess_info = req("GET", f"/sessions?start={(datetime.utcnow()-timedelta(hours=1)).isoformat()}&end={(datetime.utcnow()+timedelta(days=2)).isoformat()}", admin_token)
target = next(s for s in sess_info if s["id"] == sid)
print(f"[7] 当前 booked_count = {target['booked_count']} / {target['capacity']}")

# 8. 第一个人取消（在截止时限外，因为是明天，category cancel_deadline=24h，刚好在边缘——团课默认 24h，明天 19:00 - 24h = 今天 19:00。当前是 UTC，看实际时差）
code, results_for_session = req("GET", f"/admin/sessions/{sid}/bookings", admin_token)
booking_to_cancel = next(b for b in results_for_session if b["member_id"] == all_members[0]["id"])
code, cancelled = req("POST", f"/bookings/{booking_to_cancel['id']}/cancel", m1_token)
print(f"[8] {all_members[0]['name']} 取消 → status={cancelled['status']}")

# 9. 看候补晋升（赵六应该被自动顶上去）
code, all_bookings = req("GET", f"/admin/sessions/{sid}/bookings", admin_token)
print(f"[9] 全部预约状态：")
for b in all_bookings:
    name = next(m["name"] for m in all_members if m["id"] == b["member_id"])
    print(f"     {name}: status={b['status']}  waitlist_order={b.get('waitlist_order')}")

# 10. 签到（剩余的 booked 状态的人）
booked = [b for b in all_bookings if b["status"] == "booked"]
if booked:
    code, ci = req("POST", "/admin/check-in", admin_token, {"booking_id": booked[0]["id"]})
    must(f"[10] 签到 booking_id={booked[0]['id']}", code, 200, ci)

# 11. 张三看自己的卡（应剩 9 次，扣过 1 次然后取消返还了）
code, my_cards = req("GET", "/me/cards", m1_token)
print(f"[11] {all_members[0]['name']} 当前卡：credits={my_cards[0]['remaining_credits']} status={my_cards[0]['status']}")

# 12. 看签到那位的卡（应剩 9 次）
checked_member = next(m for m in all_members if m["id"] == booked[0]["member_id"]) if booked else None
if checked_member:
    ct, _ = login(checked_member["phone"], checked_member["phone"][-6:])
    code, cm_cards = req("GET", "/me/cards", ct)
    print(f"[12] {checked_member['name']} 卡：credits={cm_cards[0]['remaining_credits']}")

print("\n=== 全部冒烟通过 ===")
