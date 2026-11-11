@echo off
rem Arma "Auditor.exe" con todos sus modulos, incluido Integracion XBRL.
rem Hacen falta, juntos en la misma carpeta que este .bat:
rem     verificar_workiva_GUI.py
rem     xbrl_app.py  xbrl_workiva.py  miles_workiva.py
rem     llenar_dbnet_desde_workiva.py  fusionar_cuadros.py
chcp 65001 >nul
cd /d "%~dp0"

py --version >nul 2>&1
if errorlevel 1 goto sin_python

for %%f in (verificar_workiva_GUI.py xbrl_app.py xbrl_workiva.py miles_workiva.py llenar_dbnet_desde_workiva.py fusionar_cuadros.py) do (
    if not exist "%%f" (
        echo   Falta %%f en esta carpeta.
        pause
        goto :eof
    )
)

echo   Instalando lo necesario para compilar...
py -m pip install pyinstaller openpyxl pywin32 pyodbc httpx pydantic python-dotenv requests --quiet --trusted-host pypi.org --trusted-host files.pythonhosted.org

echo   Compilando Auditor.exe (toma unos minutos)...
rem --workpath fuera de OneDrive: dentro, OneDrive bloquea la carpeta build.
rem Los modulos de XBRL van explicitos: el Auditor los importa recien al
rem abrir el modulo, y el llenado y la fusion se cargan dentro de una
rem funcion (el .exe se llama a si mismo con --tarea). win32com, pythoncom y
rem pywintypes: sin ellos el archivo unico para DBNeT sale sin macros.
rem Los --exclude-module dejan fuera librerias que el Auditor no usa
rem (el .exe baja de ~33 MB a ~19 MB).
py -m PyInstaller --noconfirm --onefile --windowed --name Auditor ^
  --workpath "%LOCALAPPDATA%\AuditorBuild" ^
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
  verificar_workiva_GUI.py
if errorlevel 1 goto error

echo.
echo   Listo: %~dp0dist\Auditor.exe
echo.
echo   Integracion XBRL queda como un modulo mas del menu de la izquierda.
echo   Usa la misma carpeta de trabajo y las mismas plantillas que
echo   "Integracion XBRL.exe": no hay que cargar nada de nuevo.
echo.
pause
goto :eof

:sin_python
echo   ERROR: Python no esta instalado.
echo   Descargalo desde python.org/downloads y marca "Add Python to PATH"
pause
goto :eof

:error
echo.
echo   La compilacion fallo. Revisa los mensajes de arriba.
pause
