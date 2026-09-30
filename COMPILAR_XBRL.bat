@echo off
rem Arma XBRL_DBNeT.exe a partir de los .py de esta carpeta.
rem Hacen falta, juntos en la misma carpeta que este .bat:
rem     xbrl_app.py  xbrl_workiva.py  llenar_dbnet_desde_workiva.py  fusionar_cuadros.py
chcp 65001 >nul
cd /d "%~dp0"

py --version >nul 2>&1
if errorlevel 1 goto sin_python

for %%f in (xbrl_app.py xbrl_workiva.py llenar_dbnet_desde_workiva.py fusionar_cuadros.py) do (
    if not exist "%%f" (
        echo   Falta %%f en esta carpeta.
        pause
        goto :eof
    )
)

echo   Instalando lo necesario para compilar...
py -m pip install pyinstaller openpyxl pywin32 --quiet --trusted-host pypi.org --trusted-host files.pythonhosted.org

echo   Compilando XBRL_DBNeT.exe (toma uno o dos minutos)...
rem win32com, pythoncom y pywintypes van explicitos: fusionar_cuadros los
rem importa dentro de una funcion, y sin ellos el .exe arma el archivo unico
rem sin macros.
py -m PyInstaller --noconfirm --onefile --windowed --name XBRL_DBNeT ^
  --hidden-import openpyxl ^
  --hidden-import win32com.client ^
  --hidden-import pythoncom ^
  --hidden-import pywintypes ^
  xbrl_app.py
if errorlevel 1 goto error

copy /y "dist\XBRL_DBNeT.exe" "XBRL_DBNeT.exe" >nul
echo.
echo   Listo: %~dp0XBRL_DBNeT.exe
echo.
echo   Abrelo con doble clic. Las plantillas de DBNeT de cada empresa
echo   se cargan desde la misma app, con "Cargar plantillas de DBNeT".
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
