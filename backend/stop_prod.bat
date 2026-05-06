@echo off
REM 停止 8000 端口的 Studio Booking 进程
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":8000.*LISTENING"') do (
  taskkill /F /PID %%a >nul 2>&1
  echo [stop] killed PID %%a
)
echo done.
