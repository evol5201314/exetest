@echo off
chcp 65001 >nul
cd /d D:\tmp
echo 面板已启动，以下为报警信息...
python D:\tmp\scripts\app.py
echo.
echo ============ 面板已启动，以上为报警信息 ============
pause
