@echo off
chcp 65001 >nul
cd /d D:\tmp
echo 正在执行价格监控检查...
python D:\tmp\scripts\monitor_stock.py
echo.
echo ============ 监控检查结束，以上为报警信息 ============
pause