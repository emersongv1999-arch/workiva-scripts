@echo off
rem Arma los 5 Auditor LIVIANOS (~20 MB c/u), todos con Integracion XBRL:
rem     Auditor.exe            (Emerson)      <- verificar_workiva_GUI.py
rem     Auditor_Violeta.exe                   <- verificar_workiva_GUI_Violeta.py
rem     Auditor_Rodrigo.exe                   <- verificar_workiva_GUI_Rodrigo.py
rem     Auditor_Olympia.exe                   <- verificar_workiva_GUI_Olympia.py
rem     Auditor_EEFF.exe       (Especialistas)<- verificar_workiva_GUI_EEFF.py
rem Cada uno lleva SUS credenciales: no mezclar los .exe entre personas.
rem Hacen falta en esta misma carpeta los 5 GUI y los 5 archivos de XBRL:
rem     xbrl_app.py  xbrl_workiva.py  miles_workiva.py
rem     llenar_dbnet_desde_workiva.py  fusionar_cuadros.py
chcp 65001 >nul
cd /d "%~dp0"

py --version >nul 2>&1
if errorlevel 1 goto sin_python

for %%f in (verificar_workiva_GUI.py verificar_workiva_GUI_Violeta.py verificar_workiva_GUI_Rodrigo.py verificar_workiva_GUI_Olympia.py verificar_workiva_GUI_EEFF.py xbrl_app.py xbrl_workiva.py miles_workiva.py llenar_dbnet_desde_workiva.py fusionar_cuadros.py) do (
    if not exist "%%f" (
        echo   Falta %%f en esta carpeta.
        pause
        goto :eof
    )
)

echo   Instalando lo necesario para compilar...
py -m pip install pyinstaller openpyxl pywin32 pyodbc httpx pydantic python-dotenv requests --quiet --trusted-host pypi.org --trusted-host files.pythonhosted.org

set FALLARON=
call :compila Auditor          verificar_workiva_GUI.py
call :compila Auditor_Violeta  verificar_workiva_GUI_Violeta.py
call :compila Auditor_Rodrigo  verificar_workiva_GUI_Rodrigo.py
call :compila Auditor_Olympia  verificar_workiva_GUI_Olympia.py
call :compila Auditor_EEFF     verificar_workiva_GUI_EEFF.py

echo.
echo   ============================================================
for %%n in (Auditor Auditor_Violeta Auditor_Rodrigo Auditor_Olympia Auditor_EEFF) do (
    if exist "dist\%%n.exe" (
        for %%A in ("dist\%%n.exe") do call :peso %%n %%~zA
    )
)
if defined FALLARON (
    echo.
    echo   FALLARON:%FALLARON%  -- revisa los mensajes de arriba.
)
echo   ============================================================
echo.
pause
goto :eof

:compila
echo.
echo   Compilando %1.exe (toma unos minutos)...
rem --workpath fuera de OneDrive (dentro, OneDrive bloquea la carpeta build)
rem y uno por .exe para que no se pisen entre si.
py -m PyInstaller --noconfirm --onefile --windowed --name %1 ^
  --workpath "%LOCALAPPDATA%\AuditorBuild\%1" ^
  --hidden-import pyodbc ^
  --hidden-import httpx ^
  --hidden-import httpx._transports.default ^
  --hidden-import httpcore ^
  --hidden-import pydantic ^
  --hidden-import dotenv ^
  --hidden-import openpyxl ^
  --hidden-import winsound ^
  --hidden-import xbrl_app ^
  --hidden-import xbrl_workiva ^
  --hidden-import miles_workiva ^
  --hidden-import llenar_dbnet_desde_workiva ^
  --hidden-import fusionar_cuadros ^
  --hidden-import win32com.client ^
  --hidden-import pythoncom ^
  --hidden-import pywintypes ^
  --exclude-module mcp ^
  --exclude-module PIL ^
  --exclude-module cryptography ^
  --exclude-module rich ^
  --exclude-module pygments ^
  --exclude-module click ^
  --exclude-module typer ^
  %2
if errorlevel 1 set FALLARON=%FALLARON% %1
goto :eof

:peso
set /a MB=%2/1048576
if %MB% GTR 25 (
    echo   dist\%1.exe   %MB% MB   ^<-- OJO: pesa mas de lo esperado ^(~20 MB^)
) else (
    echo   dist\%1.exe   %MB% MB
)
goto :eof

:sin_python
echo   ERROR: Python no esta instalado.
echo   Descargalo desde python.org/downloads y marca "Add Python to PATH"
pause
goto :eof
