@echo off
chcp 65001 >nul
title Llenado de Comparativos - Workiva

echo.
echo ============================================================
echo   LLENADO DE COMPARATIVOS - WORKIVA
echo ============================================================
echo.

py --version >nul 2>&1
if errorlevel 1 goto sin_python

cd /d "%~dp0"

py -m pip install requests --quiet --trusted-host pypi.org --trusted-host files.pythonhosted.org >nul 2>&1

py llenar_comparativos_STANDALONE.py

echo.
pause
goto :eof

:sin_python
echo ERROR: Python no esta instalado.
echo Descargalo desde python.org/downloads y marca "Add Python to PATH"
echo.
pause
