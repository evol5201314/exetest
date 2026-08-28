@echo off
chcp 65001 >nul
cd /d D:\tmp
echo 面板已启动，访问地址http://127.0.0.1:5000
python D:\tmp\scripts\app.py
echo.
echo ============ 面板已启动，以上为报警信息 ============
pause
