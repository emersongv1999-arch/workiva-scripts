@echo off
chcp 65001 >nul
title Verificacion de Sumas - Workiva

echo.
echo ============================================================
echo   VERIFICACION DE SUMAS - WORKIVA
echo ============================================================
echo.

:: Verificar que Python este instalado
py --version >nul 2>&1
if errorlevel 1 (
    echo  ERROR: Python no esta instalado o no se encuentra.
    echo  Descargalo desde https://www.python.org/downloads/
    echo.
    pause
    exit /b 1
)

:: Ir a la carpeta donde esta este .bat
cd /d "%~dp0"

:: Pedir el periodo si no se paso como argumento
set PERIODO=%1
if "%PERIODO%"=="" (
    echo  Ingresa el periodo a procesar (formato MM-AAAA):
    echo  Ejemplo: 03-2026
    echo.
    set /p PERIODO="  Periodo: "
)

echo.
echo  Periodo: %PERIODO%
echo  Buscando spreadsheet: verificacion de sumas %PERIODO%
echo.
echo ============================================================
echo.

py verificar_workiva_STANDALONE_V11.py %PERIODO%

echo.
echo ============================================================
echo   Proceso terminado.
echo ============================================================
echo.
pause
