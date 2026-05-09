#!/usr/bin/env bash
#
# 每次 git push 时由 GitHub Actions self-hosted runner 调用
# 完整路径：$HOME/studio_booking/scripts/deploy.sh
#
# 这个脚本是幂等的，但要求 setup-ubuntu.sh 已经跑过一次。

set -euo pipefail

APP_DIR="$HOME/studio_booking"
cd "$APP_DIR"

ts() { date '+%H:%M:%S'; }
log() { echo "[$(ts)] $1"; }

log "===== Deploying $(git rev-parse --short HEAD 2>/dev/null || echo unknown) ====="

# ---------- 1. 拉最新代码（带 retry 应对家宽 ISP 的 TLS 握手抖动） ----------
log "[1/5] git fetch..."
fetch_ok=0
for attempt in 1 2 3; do
  if git fetch origin --depth=1 main; then
    fetch_ok=1
    break
  fi
  log "    git fetch 失败（第 $attempt 次），5 秒后重试..."
  sleep 5
done
if [ "$fetch_ok" -ne 1 ]; then
  log "    git fetch 重试 3 次仍失败，部署中止"
  exit 1
fi
git reset --hard origin/main
log "    HEAD: $(git log -1 --format='%h %s')"

# ---------- 2. 后端依赖 ----------
log "[2/5] backend pip install..."
cd "$APP_DIR/backend"
[ -d .venv ] || python3 -m venv .venv
source .venv/bin/activate
pip install -q --upgrade pip
pip install -q -r requirements.txt
deactivate

# ---------- 3. 前端构建 ----------
log "[3/5] frontend npm + build..."
cd "$APP_DIR/frontend"
if [ -f package-lock.json ]; then
  npm ci --silent
else
  npm install --silent
fi
npm run build --silent

# ---------- 4. seed / migrate ----------
log "[4/5] seed (数据库自动迁移)..."
cd "$APP_DIR/backend"
source .venv/bin/activate
python -m app.seed > /tmp/studio_seed.log 2>&1 || true
deactivate

# ---------- 5. 重启服务 ----------
log "[5/5] systemctl restart studio..."
sudo systemctl restart studio

log "===== Done ====="
