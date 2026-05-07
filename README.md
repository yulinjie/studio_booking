# 云舍 · Studio Booking

普拉提 / 瑜伽工作室自用约课系统。

- **后端**：FastAPI + SQLModel + SQLite
- **前端**：Vue 3 + Vite + Element Plus（后台）+ Vant（H5 会员端）
- **部署**：Ubuntu + Tailscale Funnel（自动 HTTPS + 公网穿透）+ systemd
- **CI/CD**：GitHub Actions Self-hosted Runner

## 在线访问

https://range-n89z.taild789ab.ts.net

> 早期使用 `range.dns.navy` + Caddy 自管证书，但家宽 ISP 封 80/443 入站，ACME 验证走不通。改走 Tailscale Funnel 后由 Tailscale 的边缘节点中继公网流量，绕开端口封锁。

## 部署

完整步骤见 [docs/UBUNTU-DEPLOY.md](docs/UBUNTU-DEPLOY.md)。一句话版：

```bash
# 在 Ubuntu 上：
git clone https://github.com/yulinjie/studio_booking ~/studio_booking
cd ~/studio_booking
bash scripts/setup-ubuntu.sh
```

之后每次 `git push` 自动部署。

## 本地开发

```bash
# 后端
cd backend
python -m venv .venv && source .venv/Scripts/activate    # Windows: .venv\Scripts\activate.bat
pip install -r requirements.txt
cp .env.example .env
python -m app.seed
uvicorn app.main:app --reload --port 8000

# 前端（另一个终端）
cd frontend
npm install
npm run dev    # http://localhost:5173 ，自动代理 /api 到 8000
```

默认管理员：`13800000000` / `admin123`（生产环境务必改）

## 文档

- [Ubuntu 部署](docs/UBUNTU-DEPLOY.md)
- [Windows 本地部署](docs/DEPLOY-WINDOWS.md)
- [架构总览（旧 Vultr 方案）](docs/DEPLOY.md)（已弃用）

## 功能

**会员端（H5）**：首页 / 课表 / 课程详情 / 我的预约 / 卡包 / 优惠券 / 课后评价 / 个人资料

**后台**：仪表盘 / 报表中心 / 排课（周日历）/ 今日签到 / 会员（含标签）/ 教练 / 卡种 / 课程 / 优惠券 / 设置 / 操作日志
