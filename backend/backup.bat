@echo off
REM 备份 SQLite + uploads/ 到 backups/yyyymmdd_HHmmss/
REM 使用 PowerShell 处理时间戳和文件操作（比 cmd 自带的工具稳定得多）
cd /d %~dp0

powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$ts = Get-Date -Format 'yyyyMMdd_HHmmss';" ^
  "$dest = Join-Path 'backups' $ts;" ^
  "New-Item -ItemType Directory -Path $dest -Force | Out-Null;" ^
  "& '.venv\Scripts\python.exe' -c \"import sqlite3, sys; src=sqlite3.connect('studio.db'); dst=sqlite3.connect(sys.argv[1]); src.backup(dst); src.close(); dst.close()\" (Join-Path $dest 'studio.db');" ^
  "if (Test-Path 'uploads') { Copy-Item -Recurse 'uploads' (Join-Path $dest 'uploads') };" ^
  "Write-Host ('backup -> ' + $dest);" ^
  "Get-ChildItem 'backups' -Directory | Sort-Object LastWriteTime -Descending | Select-Object -Skip 30 | Remove-Item -Recurse -Force"
