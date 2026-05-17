@echo off
chcp 65001 >nul
echo.
echo  Simulation — rien ne sera modifie
echo  ===================================
python -X utf8 "%~dp0transformer.py"
echo.
pause
