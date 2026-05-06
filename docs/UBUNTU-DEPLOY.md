# Ubuntu 24 一键部署 + GitHub 自动化部署

适用场景：
- Ubuntu 24 已能从公网通过域名 `range.dns.navy` 直接访问（DDNS 已经把公网 IP 自动绑定到域名）
- 80 / 443 端口未被占用（如果占用，先停掉冲突服务）
- 拥有 GitHub 账号，且能用 `git clone` 拉本仓库

整个体系架构：

```
开发机 (Windows)
   │ git push
   ▼
GitHub 仓库 yulinjie/studio_booking
   │ webhook
   ▼
Self-hosted Runner (装在 Ubuntu)
   │ pull → install → build → restart
   ▼
Ubuntu 24
   ├─ uvicorn :8000
   └─ Caddy :80 / :443 (auto HTTPS)
   ▲
   │
[公网] https://range.dns.navy
```

---

## 第一步 · 在 Ubuntu 上跑一次安装脚本

SSH 到 Ubuntu，执行：

```bash
# 1) 拉代码
git clone https://github.com/yulinjie/studio_booking ~/studio_booking
cd ~/studio_booking

# 2) 一键安装（约 5-8 分钟，会装 Python/Node/Caddy + 配 systemd + 配 Caddy）
bash scripts/setup-ubuntu.sh
```

跑完应该能看到：

```
[ok]    ========================================
[ok]     安装完成！
[ok]    ========================================
```

立即验证：

```bash
curl http://127.0.0.1:8000/api/health
# {"ok":true,"name":"Studio Booking"}

curl https://range.dns.navy/api/health
# 第一次会等 30-60 秒等 Caddy 申请 Let's Encrypt 证书
# {"ok":true,"name":"Studio Booking"}
```

浏览器开 `https://range.dns.navy` → 看到登录页（含 HTTPS 锁标）= ✅ 成功。

> 默认账号：手机号 `13800000000` / 密码 `admin123`
> **登录后立即在右上角"修改密码"改掉默认密码**

---

## 第二步 · 注册 self-hosted runner（自动化部署）

打开浏览器：

> https://github.com/yulinjie/studio_booking/settings/actions/runners/new

选 **Linux** + **x64**，GitHub 会显示 4-5 行复制即用的命令，类似：

```bash
mkdir actions-runner && cd actions-runner
curl -o actions-runner-linux-x64-X.XXX.X.tar.gz -L https://github.com/.../actions-runner-linux-x64-X.XXX.X.tar.gz
tar xzf ./actions-runner-linux-x64-X.XXX.X.tar.gz
./config.sh --url https://github.com/yulinjie/studio_booking --token AABBCC...
./run.sh                              # 临时跑（前台）
```

测试 OK 后，把它做成开机自启：

```bash
cd ~/actions-runner
sudo ./svc.sh install
sudo ./svc.sh start
sudo ./svc.sh status                  # 应该看到 active (running)
```

去 GitHub 仓库 Settings → Actions → Runners 应能看到一个绿色的 runner，name 就是你 Ubuntu 的 hostname。

---

## 第三步 · 验证自动化

在 Windows 上随便改一个文件：

```powershell
echo "# test" >> README.md
git add . ; git commit -m "test deploy" ; git push
```

去 GitHub → Actions 看 workflow 跑起来。30 秒-2 分钟后，浏览器刷新 `https://range.dns.navy` 应能看到新版。

---

## 日常运维命令

```bash
# 查服务状态
systemctl status studio --no-pager
systemctl status caddy --no-pager

# 看实时日志
journalctl -u studio -f
journalctl -u caddy -f

# 看 Caddy 访问日志
sudo tail -f /var/log/caddy/studio.log

# 手动重启
sudo systemctl restart studio
sudo systemctl reload caddy

# 备份数据库（推荐每天 cron）
sqlite3 ~/studio_booking/backend/studio.db ".backup '/tmp/studio.$(date +%F).db'"
```

每天定时备份的 cron（`crontab -e`）：

```
0 3 * * * sqlite3 $HOME/studio_booking/backend/studio.db ".backup '$HOME/backups/studio.$(date +\%Y\%m\%d).db'" && find $HOME/backups -name 'studio.*.db' -mtime +14 -delete
```

记得先建目录：`mkdir -p ~/backups`

---

## 常见问题

### Q1. 部署失败，actions 红色

去 GitHub Actions 看具体错误日志。常见原因：
- npm install 失败 → 网络问题，重跑
- pip install 失败 → 同上
- systemctl restart 失败 → SSH 上去 `journalctl -u studio -n 50` 看堆栈
- 旧版仍在跑（systemd 不重启失败的服务），所以**部署失败不影响线上**，可以放心修了再 push

### Q2. https 证书申请失败

```bash
sudo journalctl -u caddy -n 100
```

通常原因：
- 80 端口未通：`curl -I http://range.dns.navy` 应能直接通到 Caddy
- DNS 还没刷新：`dig range.dns.navy` 看是否解析到 Ubuntu 公网 IP

### Q3. 改了 .env 怎么办

`.env` 不在 git 里（防泄漏），直接 SSH 上去改 `~/studio_booking/backend/.env`，然后 `sudo systemctl restart studio`。

### Q4. 数据库会被部署覆盖吗

不会。`studio.db` 和 `uploads/` 在 `.gitignore` 里，git 永远不动。Deploy 只刷代码、依赖、前端构建产物。

### Q5. 想回滚到上个版本

```bash
cd ~/studio_booking
git log --oneline -10                 # 看历史
git reset --hard <某个 sha>
cd ../frontend && npm run build
sudo systemctl restart studio
```

或者：在 Windows 上 `git revert <sha> ; git push`，让自动化跑回滚。
