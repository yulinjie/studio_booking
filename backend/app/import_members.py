"""
从 CSV 导入会员（首次切换系统时用）。

CSV 格式（第一行表头，编码 UTF-8）：
phone,name,gender,note
13800001111,张三,female,老客户
13800002222,李四,male,
...

可选：补一列 card_template_id，会同时给会员开一张卡。
phone,name,gender,note,card_template_id
13800001111,张三,female,老客户,1

跑：
    python -m app.import_members members.csv
重复执行安全：手机号已存在的会跳过。
"""
import sys, csv
import sqlmodel
from sqlmodel import Session, select
from .config import settings
from .database import engine, init_db
from .models import User, UserRole, CardTemplate, PaymentMethod
from .core.security import hash_password
from .services import cards as card_svc

def run(csv_path: str):
    init_db()
    created, skipped, issued = 0, 0, 0
    with open(csv_path, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        with Session(engine) as s:
            admin = s.exec(select(User).where(User.phone == settings.admin_phone)).first()
            for row in reader:
                phone = (row.get("phone") or "").strip()
                name = (row.get("name") or "").strip()
                if not phone or not name:
                    continue
                if s.exec(select(User).where(User.phone == phone)).first():
                    skipped += 1
                    continue
                user = User(
                    phone=phone,
                    name=name,
                    password_hash=hash_password(phone[-6:]),
                    role=UserRole.member,
                    gender=(row.get("gender") or None) or None,
                    note=(row.get("note") or None) or None,
                )
                s.add(user)
                s.flush()
                created += 1
                tid = (row.get("card_template_id") or "").strip()
                if tid:
                    tmpl = s.get(CardTemplate, int(tid))
                    if tmpl:
                        card_svc.issue_card(s, user, tmpl, admin, PaymentMethod.cash, note="批量导入")
                        issued += 1
            s.commit()
    print(f"导入完成：新建 {created} 人，跳过 {skipped} 人，附带开卡 {issued} 张")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法：python -m app.import_members <csv 文件路径>")
        sys.exit(1)
    run(sys.argv[1])
