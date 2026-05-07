# Ubuntu 24 一键部署 + GitHub 自动化部署

适用场景：
- Ubuntu 24，宿主在家宽 / 普通住宅网络下 —— ISP 大概率封 80 / 443 入站，无法做 Let's Encrypt 等 ACME 验证
- 用 **Tailscale Funnel** 把 `127.0.0.1:8000` 直接暴露到公网（自动 HTTPS、不需开 80/443）
- 拥有 GitHub 账号，且能用 `git clone` 拉本仓库

整体架构：

```
开发机 (Windows)
   │ git push
   ▼
GitHub 仓库 yulinjie/studio_booking
   │ 触发 workflow
   ▼
Self-hosted Runner (装在 Ubuntu)
   │ pull → install → build → restart
   ▼
Ubuntu 24
   ├─ uvicorn :8000 (studio.service)
   └─ tailscaled (Funnel)
       ▲
       │ Tailscale 边缘节点中继
[公网] https://<host>-n89z.<tailnet>.ts.net
```

> **为什么不用 Caddy + 自有域名（如 `range.dns.navy`）**：试过。家宽 ISP 封 80/443 入站，Let's Encrypt / ZeroSSL 任何 challenge（http-01、tls-alpn-01）都 timeout。DNS-01 能签证书但公网仍连不进来。Tailscale Funnel 走 Tailscale 自家边缘节点的 TCP 中继，绕开 ISP 端口封锁。

---

## 第一步 · Tailscale + Funnel 准备

```bash
# 1) 安装 Tailscale
curl -fsSL https://tailscale.com/install.sh | sh

# 2) 登录加入 tailnet
sudo tailscale up

# 3) 启用 Funnel，把 127.0.0.1:8000 暴露到公网（自动签 *.ts.net 证书）
sudo tailscale funnel --bg http://127.0.0.1:8000

# 4) 查看分配到的公网 URL
tailscale funnel status
# Funnel on:
#   - https://<host>-<suffix>.<tailnet>.ts.net
```

记下输出的 URL，这就是后续的"在线访问"地址。

> Funnel 默认入口 443/8443/10000 任选其一；以上命令用 443。要改端口可加 `--https=8443`。

---

## 第二步 · 拉代码 + 一键安装应用

SSH 到 Ubuntu，执行：

```bash
git clone https://github.com/yulinjie/studio_booking ~/studio_booking
cd ~/studio_booking
bash scripts/setup-ubuntu.sh
```

跑完应该看到：

```
[ok]    ========================================
[ok]     安装完成！
[ok]    ========================================
```

> 脚本里有装 Caddy 的步骤 —— 在本部署模式下用不到，可以让脚本装但**不要 enable / start Caddy**，或者把那段跳过。生产实际只依赖 `studio.service`，Caddy 留着无害但没用。

立即验证：

```bash
# 应用本身（内网）
curl http://127.0.0.1:8000/api/health
# {"ok":true,"name":"Studio Booking"}

# 通过 Funnel 公网回环
curl https://<your-funnel-url>/api/health
# {"ok":true,"name":"Studio Booking"}
```

浏览器开 Funnel URL → 看到登录页（含 HTTPS 锁标）= ✅ 成功。

> 默认账号：手机号 `13800000000` / 密码 `admin123`
> **登录后立即在右上角"修改密码"改掉默认密码**

---

## 第三步 · 注册 self-hosted runner（自动化部署）

打开浏览器：

> https://github.com/yulinjie/studio_booking/settings/actions/runners/new

选 **Linux** + **x64**，GitHub 会显示安装命令，类似：

```bash
mkdir -p ~/actions-runner && cd ~/actions-runner
curl -o actions-runner-linux-x64-X.XXX.X.tar.gz -L https://github.com/.../actions-runner-linux-x64-X.XXX.X.tar.gz
tar xzf ./actions-runner-linux-x64-X.XXX.X.tar.gz
./config.sh --unattended \
  --url https://github.com/yulinjie/studio_booking \
  --token <一次性 token> \
  --name <runner-name> \
  --replace
```

> tarball 下载从国内速度通常 200-400 KB/s（215MB 下完约 8-12 分钟）。如果断了用 `curl -fL -C -` 续传。

把 runner 做成开机自启：

```bash
cd ~/actions-runner
sudo ./svc.sh install $USER
sudo ./svc.sh start
sudo ./svc.sh status     # 应看到 active (running)
```

GitHub 仓库 Settings → Actions → Runners 应能看到一个 **Idle** 状态的 runner。

### 关键：sudoers 免密

Runner 是非交互的，但 `scripts/deploy.sh` 最后一步要 `sudo systemctl restart studio`。给 runner 用户配免密：

```bash
sudo visudo -f /etc/sudoers.d/studio-runner
```

加入（`<runner-user>` 改成实际跑 runner 的用户）：

```
<runner-user> ALL=(ALL) NOPASSWD: /usr/bin/systemctl restart studio
<runner-user> ALL=(ALL) NOPASSWD: /bin/systemctl restart studio
```

存盘退出（visudo 会校验语法）。

---

## 第四步 · 验证自动化

在 Windows 上：

```powershell
echo "# test" >> README.md
git add . ; git commit -m "test deploy" ; git push
```

去 GitHub → Actions 看 workflow 跑起来。1-3 分钟后，浏览器刷新 Funnel URL 应能看到新版。

---

## 日常运维命令

```bash
# 查服务状态
systemctl status studio --no-pager
sudo journalctl -u 'actions.runner.*' -n 50 --no-pager

# 看实时日志
journalctl -u studio -f

# 手动重启
sudo systemctl restart studio

# Funnel 状态
tailscale funnel status

# 备份数据库（推荐每天 cron；项目里也有 studio-backup.service + .timer 可用）
sqlite3 ~/studio_booking/backend/studio.db ".backup '/tmp/studio.$(date +%F).db'"
```

每天定时备份的 cron（`crontab -e`）：

```
0 3 * * * sqlite3 $HOME/studio_booking/backend/studio.db ".backup '$HOME/backups/studio.$(date +\%Y\%m\%d).db'" && find $HOME/backups -name 'studio.*.db' -mtime +14 -delete
```

记得先建目录：`mkdir -p ~/backups`

---

## 常见问题

### Q1. 部署失败，Actions 红色

GitHub Actions 看具体错误日志。常见原因：
- `npm ci` 失败 → 网络/缓存，重跑 workflow
- `pip install` 失败 → 同上
- `systemctl restart` 失败 → SSH 上去 `journalctl -u studio -n 50` 看堆栈
- sudoers 没配 → runner 报 `sudo: a terminal is required` 之类，按第三步配免密
- 旧版仍在跑（systemd 不重启失败的服务），所以**部署失败不影响线上**

### Q2. Funnel URL 打不开 / Tailscale 重启后失效

```bash
tailscale status            # 看本机是否还登录在 tailnet
tailscale funnel status     # 看 Funnel 是否还 on
sudo tailscale funnel --bg http://127.0.0.1:8000   # 重新启用
```

如果 Tailscale 账号过期或 ACL 改了，重新 `sudo tailscale up` 一次。

### Q3. 改了 .env 怎么办

`.env` 不在 git 里（防泄漏），直接 SSH 上去改 `~/studio_booking/backend/.env`，然后：

```bash
sudo systemctl restart studio
```

### Q4. 数据库会被部署覆盖吗

不会。`studio.db` 和 `uploads/` 在 `.gitignore` 里，git 永远不动。Deploy 只刷代码、依赖、前端构建产物。

### Q5. 想回滚到上个版本

最稳：在 Windows 上 `git revert <sha> ; git push`，让自动化跑回滚。

或者直接在 Ubuntu 上：

```bash
cd ~/studio_booking
git log --oneline -10
git reset --hard <某个 sha>
cd frontend && npm run build
sudo systemctl restart studio
```

> 注意 `git reset --hard` 不会触发 Actions，下一次 push 会被当成新 commit；自动化和你 reset 的版本可能错位。除非你清楚后果，否则尽量用 `git revert`。

### Q6. 想换回自管域名 + 自有 HTTPS

唯一可行路径：换非家宽（不封 80/443 的商业宽带），然后启用 `/etc/caddy/Caddyfile` 里现成的配置 + `sudo systemctl enable --now caddy`。在家宽下别折腾 ACME，会一直 timeout。
