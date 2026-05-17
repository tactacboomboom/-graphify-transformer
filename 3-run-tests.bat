@echo off
chcp 65001 >nul
echo.
echo  Tests — verification du contrat
echo  =================================
python -X utf8 "%~dp0test_transformer.py"
echo.
pause
