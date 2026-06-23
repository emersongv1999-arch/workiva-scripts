@echo off
chcp 65001 >nul
title Auditoria de Linking - Workiva

echo.
echo ============================================================
echo   AUDITORIA DE LINKING - WORKIVA
echo ============================================================
echo.

py --version >nul 2>&1
if errorlevel 1 goto sin_python

cd /d "%~dp0"

py -m pip install requests openpyxl --quiet --trusted-host pypi.org --trusted-host files.pythonhosted.org >nul 2>&1

py auditar_linking.py

echo.
pause
goto :eof

:sin_python
echo ERROR: Python no esta instalado.
echo Descargalo desde python.org/downloads y marca "Add Python to PATH"
echo.
pause
