@echo off
chcp 65001 >nul
cd /d "%~dp0"
python renombrar_hojas_cashpooling.py
if errorlevel 1 (
    echo.
    echo ERROR: Verifica que Python este instalado.
    pause
)
