# 部署指南（海外 VPS + Caddy）

适用于 `range.dns.navy` 这种 `.navy` 后缀域名（无法在国内云备案）。
推荐 **Vultr 东京 / 首尔**，对中国大陆速度最好，$5/月起。

> 全程一台 1 核 1G 的 VPS 即可。SQLite 数据库不需要单独的 DB server。

---

## 第 1 步 · 买 VPS 并拿到 IP

任选一家：
- [Vultr](https://www.vultr.com/) — 推荐 Tokyo / Seoul，1C/1G $5/月
- [甲骨文 Oracle Cloud Free Tier](https://www.oracle.com/cloud/free/) — 免费 4C/24G ARM（永久免费，但注册要外币卡）
- [DigitalOcean](https://www.digitalocean.com/) — Singapore，1C/1G $4/月

镜像选 **Ubuntu 22.04 LTS** 或 24.04。

> 拿到的公网 IP 假设为 `1.2.3.4`，下文以此代替。

---

## 第 2 步 · DNS 解析

到你域名的 DNS 控制台（你用的 dns.navy）：
- 添加 A 记录：`range.dns.navy → 1.2.3.4`
- TTL 600 秒就行

等 1-5 分钟，本机 ping 通即可：
```bash
ping range.dns.navy
```

---

## 第 3 步 · VPS 上一次性环境准备

SSH 登上去：
```bash
ssh root@1.2.3.4
```

运行这些命令（一气呵成，每行都安全可重复执行）：

```bash
# 系统更新
apt update && apt upgrade -y

# 安装 Python 3.11+ 和系统依赖
apt install -y python3 python3-pip python3-venv git curl

# 安装 Node.js 20 LTS（用于在 VPS 上构建前端，也可以本地构建好上传）
curl -fsSL https://deb.nodesource.com/setup_20.x | bash -
apt install -y nodejs

# 安装 Caddy（反代 + 自动 HTTPS）
apt install -y debian-keyring debian-archive-keyring apt-transport-https
curl -fsSL https://dl.cloudsmith.io/public/caddy/stable/gpg.key | gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
curl -fsSL https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt | tee /etc/apt/sources.list.d/caddy-stable.list
apt update && apt install -y caddy

# 创建一个非 root 用户运行应用
useradd -m -s /bin/bash studio
```

---

## 第 4 步 · 上传代码

**方法 A（推荐）** — 用 git 推到一个仓库，VPS 上 clone 下来：
```bash
su - studio
cd ~
git clone <你的仓库 URL> studio_booking
cd studio_booking
```

**方法 B** — 本地打包 SCP 上传：
```bash
# 本地（Windows Git Bash）：
cd /c/Users/Administrator/Desktop/TraeProject
tar --exclude='studio_booking/backend/.venv' --exclude='studio_booking/frontend/node_modules' --exclude='studio_booking/backend/static' -czf studio_booking.tar.gz studio_booking/
scp studio_booking.tar.gz root@1.2.3.4:/home/studio/

# VPS:
su - studio
cd ~
tar -xzf studio_booking.tar.gz
cd studio_booking
```

---

## 第 5 步 · 后端首次启动

```bash
# 仍以 studio 用户身份
cd ~/studio_booking/backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# 配置环境变量 — 改密码、改 SECRET_KEY！
cp .env.example .env
nano .env
# 至少改：
#   SECRET_KEY=随机长字符串(64字符)
#   ADMIN_PASSWORD=你自己的强密码
#   STUDIO_NAME=你的工作室名

# 初始化数据
python -m app.seed

# 测试启动
uvicorn app.main:app --host 127.0.0.1 --port 8000
# Ctrl+C 停止，下面用 systemd 永久运行
```

---

## 第 6 步 · 构建前端

```bash
cd ~/studio_booking/frontend
npm config set registry https://registry.npmmirror.com   # 可选：提速
npm install
npm run build
# 构建结果在 ../backend/static/，FastAPI 会自动 serve
```

---

## 第 7 步 · systemd 守护进程

回到 root：
```bash
exit  # 退出 studio 用户回到 root
```

写 systemd 服务文件（已经在 [`backend/studio.service`](../backend/studio.service)）：
```bash
cp /home/studio/studio_booking/backend/studio.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable --now studio
systemctl status studio    # 应该显示 active (running)
```

如果 status 报错，查日志：
```bash
journalctl -u studio -n 50
```

---

## 第 8 步 · Caddy 反代 + HTTPS

把 [`Caddyfile`](../backend/Caddyfile) 内容写入 `/etc/caddy/Caddyfile`（**改成你的真实域名**）：

```bash
nano /etc/caddy/Caddyfile   # 把 range.dns.navy 改成你的域名（如果不一样）
systemctl reload caddy
```

Caddy 会自动从 Let's Encrypt 申请 HTTPS 证书。

打开浏览器访问 `https://range.dns.navy`，应能看到登录页。

---

## 第 9 步 · 简单备份

每天定时把 SQLite 数据库复制一份：
```bash
crontab -e -u studio
# 加这一行（每天凌晨 3 点备份，保留 7 天）：
0 3 * * * cp ~/studio_booking/backend/studio.db ~/studio_booking/backups/studio.$(date +\%Y\%m\%d).db && find ~/studio_booking/backups/ -name 'studio.*.db' -mtime +7 -delete
```

记得先建目录：
```bash
mkdir -p /home/studio/studio_booking/backups
```

---

## 后续更新代码

```bash
su - studio
cd ~/studio_booking
git pull   # 或重新 scp 上传

cd backend
source .venv/bin/activate
pip install -r requirements.txt        # 如果有新依赖
# 如果有新数据模型，先备份再删 db 重新 seed（MVP 阶段没有 alembic 迁移）
exit

cd ../frontend
npm run build

exit  # 回到 root
systemctl restart studio
```

---

## 常见问题

**Q: 为什么不用 Docker?**
A: 单店自用 + SQLite，systemd 跑一个 uvicorn 进程更省资源、更好排查。`docker-compose` 在 1G 内存上跑会很挤。

**Q: 1 核 1G 够吗?**
A: 不到 50 个会员、不到 100 个并发请求，绰绰有余。SQLite 也能撑到几千会员的规模。

**Q: 想加微信支付/小程序?**
A: 先把营业执照办下来（个体户也行，1-3 天），再申请微信支付商户号 V3，然后开发新接口对接。这是 v2 的事。

**Q: 数据库怎么从 VPS 拉到本地看?**
A: `scp studio@1.2.3.4:~/studio_booking/backend/studio.db ./` 然后用 [DB Browser for SQLite](https://sqlitebrowser.org/) 直接打开。

**Q: 怎么改管理员密码?**
A: 暂时通过 `/api/admin/members/{id}/reset-password` 接口（要先用旧密码登录拿 token）。后续可以做个修改密码 UI。
