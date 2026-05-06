@echo off
REM 生产启动脚本 - 双击运行 / 加到 Windows 任务计划
cd /d %~dp0
if not exist .venv (
  echo [!] .venv 不存在，请先运行 run_dev.bat 一次以完成依赖安装
  pause
  exit /b 1
)
call .venv\Scripts\activate.bat
set PYTHONIOENCODING=utf-8

REM 确保静态文件存在（前端构建产物）
if not exist static\index.html (
  echo [!] 前端未构建，请到 ../frontend 跑 npm install + npm run build
  pause
  exit /b 1
)

REM 首次运行迁移和 seed（幂等）
python -m app.seed >nul 2>&1

echo.
echo ========================================
echo  Studio Booking 已启动
echo  本机访问：  http://127.0.0.1:8000
echo  局域网访问：http://10.0.0.106:8000
echo              http://10.1.200.69:8000
echo  默认账号：  13800000000 / admin123
echo  停止：      关闭本窗口
echo ========================================
echo.

uvicorn app.main:app --host 0.0.0.0 --port 8000 --log-level info
