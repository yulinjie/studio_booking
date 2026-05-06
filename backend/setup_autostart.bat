@echo off
REM 注册 Windows 任务计划：登录后自动启动 Studio Booking
REM 普通用户权限即可，不需要管理员

set SCRIPT=%~dp0run_prod.bat

schtasks /Create /TN "Studio Booking" /SC ONLOGON /TR "\"%SCRIPT%\"" /RL LIMITED /F
if errorlevel 1 goto :err

echo.
echo ========================================
echo  开机自启已设置
echo  下次 Windows 登录时会自动起服务
echo  立即起服务：双击 run_prod.bat
echo  取消自启：双击 remove_autostart.bat
echo ========================================
pause
exit /b 0

:err
echo [!] 注册失败
pause
exit /b 1
