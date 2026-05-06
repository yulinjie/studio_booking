#!/usr/bin/env bash
#
# Ubuntu 24 一次性环境初始化脚本
# 用法（在 Ubuntu 上 SSH 进去后跑）：
#
#   git clone https://github.com/yulinjie/studio_booking ~/studio_booking
#   cd ~/studio_booking
#   bash scripts/setup-ubuntu.sh
#
# 这个脚本是幂等的——重复跑没问题。
#
# 跑完会：
#   - 装好 Python / Node / Caddy / sqlite
#   - 创建 systemd 服务 studio
#   - 配置 Caddy 反代 + 自动 HTTPS
#   - 配置 UFW 放行 80 / 443 / 22
#   - 给当前用户加上免密 sudo 重启权限

set -euo pipefail

APP_DIR="$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )/.." &> /dev/null && pwd )"
APP_USER="${USER}"
DOMAIN="${STUDIO_DOMAIN:-range.dns.navy}"
EMAIL="${STUDIO_EMAIL:-335337006@qq.com}"

cyan() { printf "\033[36m[setup] %s\033[0m\n" "$1"; }
green() { printf "\033[32m[ok]    %s\033[0m\n" "$1"; }
yellow() { printf "\033[33m[!]     %s\033[0m\n" "$1"; }

cyan "===== 云舍 Studio Booking 一键安装 ====="
cyan "App dir : $APP_DIR"
cyan "User    : $APP_USER"
cyan "Domain  : $DOMAIN"
cyan "Email   : $EMAIL"
echo

# ---------- 1. 系统包 ----------
cyan "[1/9] 安装系统依赖..."
sudo apt-get update -qq
sudo apt-get install -y -q \
  python3 python3-venv python3-pip \
  git curl ca-certificates \
  sqlite3 ufw \
  debian-keyring debian-archive-keyring apt-transport-https \
  fonts-noto-cjk fonts-noto-cjk-extra

# ---------- 2. Node 20 ----------
if ! command -v node > /dev/null || [[ "$(node -v)" != v2[0-9]* ]]; then
  cyan "[2/9] 安装 Node.js 20..."
  curl -fsSL https://deb.nodesource.com/setup_20.x | sudo bash -
  sudo apt-get install -y -q nodejs
else
  green "Node.js $(node -v) 已就位"
fi

# ---------- 3. Caddy ----------
if ! command -v caddy > /dev/null; then
  cyan "[3/9] 安装 Caddy..."
  curl -fsSL https://dl.cloudsmith.io/public/caddy/stable/gpg.key | sudo gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
  curl -fsSL https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt | sudo tee /etc/apt/sources.list.d/caddy-stable.list > /dev/null
  sudo apt-get update -qq
  sudo apt-get install -y -q caddy
else
  green "Caddy $(caddy version | head -1) 已就位"
fi

# ---------- 4. Python venv + 依赖 ----------
cyan "[4/9] 配置后端..."
cd "$APP_DIR/backend"
[ -d .venv ] || python3 -m venv .venv
source .venv/bin/activate
pip install -q --upgrade pip
pip install -q -r requirements.txt
deactivate

# ---------- 5. .env ----------
if [ ! -f "$APP_DIR/backend/.env" ]; then
  cyan "[5/9] 生成 .env（首次）..."
  SECRET=$(python3 -c "import secrets;print(secrets.token_urlsafe(48))")
  cat > "$APP_DIR/backend/.env" <<EOF
APP_NAME=Studio Booking
SECRET_KEY=$SECRET
ACCESS_TOKEN_EXPIRE_MINUTES=10080
DATABASE_URL=sqlite:///./studio.db
ADMIN_PHONE=13800000000
ADMIN_PASSWORD=admin123
STUDIO_NAME=云舍
TIMEZONE=Asia/Shanghai
EOF
  yellow ".env 已创建。默认管理员 13800000000/admin123，部署后请立即在网页修改密码"
else
  green "[5/9] .env 已存在，跳过"
fi

# ---------- 6. seed + 前端构建 ----------
cyan "[6/9] 数据库 seed + 前端构建..."
cd "$APP_DIR/backend"
source .venv/bin/activate
python -m app.seed > /tmp/studio_seed.log 2>&1 || yellow "seed 跳过（数据已存在）"
deactivate

cd "$APP_DIR/frontend"
[ -d node_modules ] || npm ci --silent
npm run build --silent
green "前端已构建到 backend/static/"

# ---------- 7. systemd ----------
cyan "[7/9] 配置 systemd 服务..."
sudo tee /etc/systemd/system/studio.service > /dev/null <<EOF
[Unit]
Description=Studio Booking FastAPI
After=network.target

[Service]
Type=simple
User=$APP_USER
Group=$APP_USER
WorkingDirectory=$APP_DIR/backend
EnvironmentFile=$APP_DIR/backend/.env
ExecStart=$APP_DIR/backend/.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000
Restart=always
RestartSec=5
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=full
ReadWritePaths=$APP_DIR/backend

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable studio
sudo systemctl restart studio

# ---------- 8. Caddy ----------
cyan "[8/9] 配置 Caddy ($DOMAIN)..."
sudo tee /etc/caddy/Caddyfile > /dev/null <<EOF
{
    email $EMAIL
}

$DOMAIN {
    encode gzip
    reverse_proxy 127.0.0.1:8000

    @assets path /assets/* /uploads/*
    header @assets Cache-Control "public, max-age=86400"

    log {
        output file /var/log/caddy/studio.log {
            roll_size 50mb
            roll_keep 5
        }
    }
}
EOF

sudo systemctl reload caddy 2>/dev/null || sudo systemctl restart caddy

# ---------- 9. UFW + 免密 sudo（给 GHA runner 用） ----------
cyan "[9/9] 防火墙 + sudoers..."
if sudo ufw status | grep -q "Status: inactive"; then
  sudo ufw allow OpenSSH > /dev/null
  sudo ufw allow 80/tcp > /dev/null
  sudo ufw allow 443/tcp > /dev/null
  echo "y" | sudo ufw enable > /dev/null
else
  sudo ufw allow 80/tcp > /dev/null
  sudo ufw allow 443/tcp > /dev/null
fi

sudo tee /etc/sudoers.d/studio-deploy > /dev/null <<EOF
# 允许 deploy.sh 免密重启服务
$APP_USER ALL=(ALL) NOPASSWD: /bin/systemctl restart studio
$APP_USER ALL=(ALL) NOPASSWD: /bin/systemctl status studio
$APP_USER ALL=(ALL) NOPASSWD: /usr/bin/systemctl restart studio
$APP_USER ALL=(ALL) NOPASSWD: /usr/bin/systemctl status studio
EOF
sudo chmod 0440 /etc/sudoers.d/studio-deploy

# ---------- 9.5 自动备份（systemd timer 每天 03:00） ----------
cyan "[9.5/9] 配置每日自动备份..."
chmod +x "$APP_DIR/scripts/auto-backup.sh" 2>/dev/null || true
mkdir -p "$HOME/backups"
sudo cp "$APP_DIR/backend/studio-backup.service" /etc/systemd/system/
sudo cp "$APP_DIR/backend/studio-backup.timer"   /etc/systemd/system/
sudo touch /var/log/studio-backup.log
sudo chown range:range /var/log/studio-backup.log 2>/dev/null || true
sudo systemctl daemon-reload
sudo systemctl enable --now studio-backup.timer
green "已开启：每天 03:00 自动备份到 ~/backups/，保留 30 份"

# ---------- 收尾 ----------
echo
green "========================================"
green " 安装完成！"
green "========================================"
echo
echo " 检查服务状态："
echo "   systemctl status studio --no-pager"
echo "   systemctl status caddy --no-pager"
echo
echo " 验证："
echo "   本机：    curl http://127.0.0.1:8000/api/health"
echo "   公网：    curl https://$DOMAIN/api/health"
echo
echo " 默认管理员（务必在网页改密码）："
echo "   手机号: 13800000000"
echo "   密码:   admin123"
echo
yellow " 接下来去 https://github.com/yulinjie/studio_booking/settings/actions/runners/new 注册 self-hosted runner"
yellow " 选 Linux x64，4 行命令复制粘贴到 Ubuntu 跑（在 ~/actions-runner 目录），最后 sudo ./svc.sh install + sudo ./svc.sh start 就能开机自启"
