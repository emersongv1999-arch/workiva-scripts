@echo off
cd /d "C:\Users\egarridov\OneDrive - Grupo CGE\Escritorio\Documentos\APP claude"
echo Instalando dependencias...
C:\Windows\py.exe -m pip install requests urllib3 python-dotenv --quiet
echo.
echo Archivos en la carpeta:
dir /b
echo.
echo Contenido del .env:
type .env
echo.
echo Ejecutando script...
echo.
C:\Windows\py.exe test_E1_E300_desde_E200.py
pause
