#!/usr/bin/env bash
# 轮询 GitHub origin/main，发现新 commit 自动跑 deploy.sh
# 由 systemd unit /etc/systemd/system/studio-deploy.service 启动
# 安装见 docs/UBUNTU-DEPLOY.md
set -u
APP_DIR="$HOME/studio_booking"
LAST=""
cd "$APP_DIR"

# 启动时把当前 HEAD 当 baseline，避免一启动就重部署
LAST=$(git rev-parse HEAD 2>/dev/null)
echo "[$(date '+%F %T')] auto-deploy started, baseline=${LAST:0:7}"

while true; do
  if git fetch origin main --quiet 2>/dev/null; then
    REMOTE=$(git rev-parse origin/main 2>/dev/null)
    if [ -n "$REMOTE" ] && [ "$REMOTE" != "$LAST" ]; then
      echo "[$(date '+%F %T')] new commit ${REMOTE:0:7}, deploying..."
      if bash "$APP_DIR/scripts/deploy.sh" 2>&1; then
        echo "[$(date '+%F %T')] deploy ok"
        LAST="$REMOTE"
      else
        echo "[$(date '+%F %T')] deploy FAILED, will retry next cycle"
      fi
    fi
  fi
  sleep 30
done
