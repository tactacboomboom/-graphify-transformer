@echo off
chcp 65001 >nul
echo.
echo  Enrichissement du graphe — ECRITURE dans graph.json
echo  =====================================================
python -X utf8 "%~dp0transformer.py" --write
echo.
pause
