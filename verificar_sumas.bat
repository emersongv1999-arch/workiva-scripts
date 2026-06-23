@echo off
chcp 65001 >nul
title Verificacion de Sumas - Workiva

echo.
echo ============================================================
echo   VERIFICACION DE SUMAS - WORKIVA
echo ============================================================
echo.

py --version >nul 2>&1
if errorlevel 1 goto sin_python

cd /d "%~dp0"

set "PERIODO=%~1"
if "%PERIODO%"=="" (
    echo Ingresa el periodo formato MM-AAAA, ejemplo 03-2026
    echo.
    set /p "PERIODO=Periodo: "
)

echo.
echo Periodo: %PERIODO%
echo.

py verificar_workiva_STANDALONE_V11.py %PERIODO%

echo.
echo Proceso terminado.
echo.
pause
goto :eof

:sin_python
echo ERROR: Python no esta instalado.
echo Descargalo desde python.org/downloads
echo.
pause
