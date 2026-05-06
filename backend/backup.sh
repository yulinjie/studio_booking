#!/usr/bin/env bash
# 简易 SQLite 备份脚本，给 cron 调用
# 用法：bash backup.sh
set -e
HERE="$(cd "$(dirname "$0")" && pwd)"
BACKUP_DIR="${HERE}/backups"
mkdir -p "$BACKUP_DIR"
DATE="$(date +%Y%m%d_%H%M%S)"

# .backup 比 cp 安全（避开 WAL 半写状态）
sqlite3 "$HERE/studio.db" ".backup '$BACKUP_DIR/studio.${DATE}.db'"

# 只保留最近 14 份
ls -1t "$BACKUP_DIR"/studio.*.db | tail -n +15 | xargs -r rm -f
echo "[backup] $BACKUP_DIR/studio.${DATE}.db"
