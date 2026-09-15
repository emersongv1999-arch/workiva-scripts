@echo off
rem Abre la ventana del llenado XBRL.
rem Con pythonw en vez de python para que no quede una consola negra detras.

cd /d "%~dp0"

py --version >nul 2>&1
if errorlevel 1 goto sin_python

py -m pip install openpyxl pywin32 --quiet --trusted-host pypi.org --trusted-host files.pythonhosted.org >nul 2>&1

start "" pythonw "%~dp0interfaz_xbrl.py"
goto :eof

:sin_python
echo.
echo   ERROR: Python no esta instalado.
echo   Descargalo desde python.org/downloads y marca "Add Python to PATH"
echo.
pause
