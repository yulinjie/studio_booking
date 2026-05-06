@echo off
schtasks /Delete /TN "Studio Booking" /F
echo 自启已删除。手动启动：双击 run_prod.bat
pause
