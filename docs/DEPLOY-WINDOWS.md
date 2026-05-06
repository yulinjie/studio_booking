# Windows 宿主机部署指南

## 一、当前状态

✅ 已完成：
- 数据库：`backend/studio.db` 已 seed
- 前端：`backend/static/` 已构建
- 服务：监听 `0.0.0.0:8000`（所有网卡）
- 防火墙：TCP 8000 已开放（rule 名："Studio Booking 8000"）

✅ 立即可用的访问地址：

| 场景 | URL |
|---|---|
| 本机浏览器 | http://127.0.0.1:8000 |
| 同一 WiFi 的手机 / 平板 / 其他电脑 | http://10.0.0.106:8000 |
| 同一 WiFi 的备用网卡 | http://10.1.200.69:8000 |

> 局域网 IP 取决于你的路由器。如果换了网络，重新跑 `ipconfig` 看 IPv4。

✅ 默认账号：
- 手机号 `13800000000`
- 密码 `admin123` ← **登录后第一件事就是右上角"修改密码"**

---

## 二、日常运维（双击 .bat 即可）

`backend/` 目录下：

| 脚本 | 作用 |
|---|---|
| `run_prod.bat` | 手动启动服务 |
| `stop_prod.bat` | 停止服务 |
| `setup_autostart.bat` | 注册"登录后自启动"的任务计划 |
| `remove_autostart.bat` | 取消自启 |
| `backup.bat` | 备份 studio.db + uploads/ 到 backups/ |

### 推荐设置

1. 双击 `setup_autostart.bat` 一次 → 以后每次登录 Windows 服务自动起
2. 在 Windows 任务计划里每天定时跑 `backup.bat`（搜"任务计划程序" → 创建基本任务）

---

## 三、暴露到公网（让会员家里也能约课）

**纯 LAN 模式只能让到店或同 WiFi 的人用。** 想让会员在家也能约课、扫二维码注册，得让公网能访问。

### 推荐：Cloudflare Tunnel（免费，免备案，免端口转发）

不需要公网 IP，不需要在路由器开端口，免费 + HTTPS 自动。

1. 注册 Cloudflare 账号（免费），把你的域名 `range.dns.navy` 托管过去
   - **要先去 dns.navy 改 NS 记录到 Cloudflare 给你的两个 NS** — 这一步可能 dns.navy 不一定支持改 NS。如果不支持，备选方案见底部。
2. 下载 [cloudflared](https://github.com/cloudflare/cloudflared/releases/latest) 的 Windows 版
3. PowerShell 跑：
   ```powershell
   cloudflared tunnel login              # 浏览器授权
   cloudflared tunnel create studio      # 创建一个 tunnel
   cloudflared tunnel route dns studio range.dns.navy
   cloudflared tunnel run --url http://localhost:8000 studio
   ```
4. 把它做成 Windows Service：
   ```powershell
   cloudflared service install
   ```

完成后 `https://range.dns.navy` 自动指向你的 Windows 机器，HTTPS 自动配，**电脑只要开机有网就能用**。

### 备选：ngrok（最快，但 URL 会变）

```powershell
ngrok http 8000
# 拿到一个 https://abc123.ngrok-free.app 的临时 URL
```

URL 每次重启都变，免费版有限制。**只适合临时演示**，不适合长期运营。

### 备选：路由器端口转发 + DDNS

需要你家有公网 IPv4（中国大陆很多 ISP 现在是 NAT，没公网 IP）。能折腾再选这个。

---

## 四、迁移到 Ubuntu 24 笔记本（未来）

Windows 当中转，Ubuntu 才是 7×24 真正可靠的承载。Linux 那套已经在 [DEPLOY.md](DEPLOY.md) 写好。简化迁移步骤：

```bash
# 在 Ubuntu 上
sudo apt install -y python3 python3-pip python3-venv git nodejs npm

# 把代码 clone 或 scp 过去
git clone <your-repo> studio_booking
# 或直接 scp -r 整个 studio_booking/ 目录过去

cd studio_booking/backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# 数据从 Windows 拷过去
# Windows 端：scp studio.db uploads/* user@laptop:~/studio_booking/backend/
# 或用 rsync

# 前端构建
cd ../frontend && npm install && npm run build && cd ../backend

# 用我们之前写好的 systemd 单元（[backend/studio.service](../backend/studio.service)）
# 仅需把里面的路径从 /home/studio/ 改成你 Ubuntu 实际用户路径
sudo cp studio.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now studio
```

Cloudflare Tunnel 在 Ubuntu 上也能跑，命令一样。

---

## 五、常见问题

**Q: 双击 run_prod.bat 一闪就关？**
A: 看是不是端口被占用。先双击 `stop_prod.bat`，再启动。

**Q: 手机连不上 LAN IP？**
A: 确认手机和电脑在**同一 WiFi**。手机数据网络访问不到内网 IP。

**Q: 关电脑了服务就停了？**
A: 是的，Windows 关机服务停。这是为啥推荐迁到 Ubuntu 笔记本（你可以让笔记本盖盖子但不睡眠 = 7×24）或买 VPS。

**Q: 默认密码 admin123 风险？**
A: **必须改**。登录后右上角"修改密码"。这是 P0 阶段我们专门做的功能。

**Q: 备份怎么恢复？**
A: 复制 `backups/yyyymmdd_hhmmss/studio.db` 覆盖 `backend/studio.db`，重启服务即可。
