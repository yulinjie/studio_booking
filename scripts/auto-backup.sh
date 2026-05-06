#!/usr/bin/env bash
# 每天定时运行，备份 SQLite 主库 + uploads 目录
# 由 systemd timer studio-backup.timer 触发

set -u
APP_DIR="$HOME/studio_booking"
BACKUP_ROOT="$HOME/backups"
KEEP=30                                  # 保留最近 N 份

TS=$(date '+%Y%m%d_%H%M%S')
DEST="$BACKUP_ROOT/$TS"
mkdir -p "$DEST"

cd "$APP_DIR/backend"

# SQLite 用 .backup 是最安全的（避免读到 WAL 半写状态）
sqlite3 studio.db ".backup '$DEST/studio.db'" 2>>"$DEST/backup.log"

# uploads 直接复制
if [ -d uploads ]; then
  cp -r uploads "$DEST/uploads" 2>>"$DEST/backup.log"
fi

# 写元数据
{
  echo "# Studio Booking backup"
  echo "timestamp:    $TS"
  echo "host:         $(hostname)"
  echo "git_commit:   $(cd "$APP_DIR" && git rev-parse --short HEAD 2>/dev/null || echo unknown)"
  echo "db_size:      $(stat -c%s "$DEST/studio.db" 2>/dev/null) bytes"
  echo "uploads_dir:  $([ -d "$DEST/uploads" ] && du -sh "$DEST/uploads" | cut -f1 || echo 'absent')"
} > "$DEST/MANIFEST.txt"

# 滚动清理：保留最近 KEEP 份
cd "$BACKUP_ROOT"
ls -1dt 20*_* 2>/dev/null | tail -n +$((KEEP + 1)) | xargs -r rm -rf

echo "[$TS] backup done -> $DEST"
