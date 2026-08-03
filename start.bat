@echo off
chcp 65001 > nul
cd /d %~dp0
echo IRON LOG サーバーを起動しています...
echo.
python backend\app.py
pause