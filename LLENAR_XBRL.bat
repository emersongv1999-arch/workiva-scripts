@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion
title Llenado XBRL DBNeT desde Workiva

cd /d "%~dp0"

echo.
echo ============================================================
echo   LLENADO XBRL - PLANTILLAS DBNeT DESDE EXPORT DE WORKIVA
echo ============================================================
echo.

py --version >nul 2>&1
if errorlevel 1 goto sin_python

py -m pip install openpyxl pywin32 --quiet --trusted-host pypi.org --trusted-host files.pythonhosted.org >nul 2>&1

if not exist "xls"     mkdir "xls"
if not exist "workiva" mkdir "workiva"

rem Los 41 archivos llenos son un paso intermedio: el fusionador los necesita,
rem pero a nadie le sirve tenerlos a la vista. Van a una carpeta temporal y se
rem borran al terminar, SALVO que la fusion falle: ahi son el plan B, porque
rem cada uno lleva sus macros y botones funcionando por su cuenta.
set "TMPSAL=%TEMP%\XBRL_llenado"
if exist "%TMPSAL%" rmdir /s /q "%TMPSAL%"

rem ---- 1. plantillas de DBNeT --------------------------------------------
set /a N=0
for /f "delims=" %%f in ('dir /b /s "xls\*.xlsm" 2^>nul') do set /a N+=1
if !N!==0 goto sin_plantillas
echo   Plantillas DBNeT : !N! archivos en la carpeta xls\

rem ---- 2. export de Workiva ----------------------------------------------
rem Se puede arrastrar el .xlsx sobre este .bat; si no, se toma el mas
rem reciente de la carpeta workiva\
set "WK=%~1"
if not "%WK%"=="" goto tengo_wk

for /f "delims=" %%f in ('dir /b /o-d "workiva\*.xlsx" 2^>nul') do (
    set "WK=%~dp0workiva\%%f"
    goto tengo_wk
)
goto sin_workiva

:tengo_wk
for %%f in ("%WK%") do set "WK_NOMBRE=%%~nxf"
echo   Export Workiva   : %WK_NOMBRE%
echo.

rem ---- 3. simulacion ------------------------------------------------------
echo ------------------------------------------------------------
echo   PASO 1 de 2  -  Simulacion (no escribe nada)
echo ------------------------------------------------------------
echo.
py llenar_dbnet_desde_workiva.py --plantillas "xls" --workiva "%WK%" --salida "%TMPSAL%" --reporte "reporte_llenado.csv" --dry-run
if errorlevel 1 goto error

echo.
echo ------------------------------------------------------------
echo   Revisa los numeros de arriba antes de continuar.
echo   La carpeta xls\ NO se modifica: los archivos llenos se arman
echo   aparte y se juntan en un solo archivo al final.
echo ------------------------------------------------------------
echo.
set "SEGUIR="
set /p "SEGUIR=Escribir los archivos? (S/N): "
if /i not "!SEGUIR!"=="S" goto cancelado

rem ---- 4. escritura -------------------------------------------------------
echo.
echo ------------------------------------------------------------
echo   PASO 2 de 2  -  Escribiendo
echo ------------------------------------------------------------
echo.
py llenar_dbnet_desde_workiva.py --plantillas "xls" --workiva "%WK%" --salida "%TMPSAL%" --reporte "reporte_llenado.csv"
if errorlevel 1 goto error

rem ---- 5. fusion en un solo archivo, con macros funcionando ---------------
echo.
echo ------------------------------------------------------------
echo   Fusionando los cuadros en un solo archivo
echo ------------------------------------------------------------
echo.
for %%f in ("%WK%") do set "BASE=%%~nf_LLENADO"

set "CON_MACROS=1"
py fusionar_cuadros.py --origen "%TMPSAL%" --salida "!BASE!.xlsm" --con-macros --solo-workiva
if errorlevel 1 set "CON_MACROS=0"

py fusionar_cuadros.py --origen "%TMPSAL%" --salida "!BASE!.xlsx" --solo-workiva
if errorlevel 1 goto error
echo.

echo ============================================================
echo   LISTO
echo ============================================================
echo.
if "!CON_MACROS!"=="1" (
    echo   PARA DBNeT   .xlsm : %~dp0!BASE!.xlsm   ^(con macros y botones^)
    echo                .xlsx : %~dp0!BASE!.xlsx   ^(sin macros, para revisar^)
    rem La fusion con macros salio bien: los intermedios ya no hacen falta.
    if exist "%TMPSAL%" rmdir /s /q "%TMPSAL%"
) else (
    echo   AVISO: no se pudo armar el .xlsm con macros. Revisa el mensaje
    echo   de arriba ^(hace falta Excel instalado en esta maquina^).
    echo   .xlsx : %~dp0!BASE!.xlsx   ^(sin macros, para revisar^)
    echo.
    echo   Como plan B te quedan los 41 archivos por separado, cada uno
    echo   con sus macros y botones funcionando. Estan en:
    echo       %TMPSAL%
    echo   No los borres hasta resolver lo del .xlsm.
)
echo.
if exist "%~dp0REVISAR.xlsx" (
    echo   ------------------------------------------------------------
    echo   ANTES DE ENTREGAR, abre esta lista:
    echo       %~dp0REVISAR.xlsx
    echo   Dice que hoja mirar y que buscar en cada una. Es corta.
    echo   ------------------------------------------------------------
) else (
    echo   No quedo nada pendiente de revisar.
)
echo.
echo   Tambien queda un reporte_llenado.csv con el detalle completo.
echo   No hace falta leerlo: sirve para rastrear una cifra si alguna
echo   vez se ve rara, y para comparar contra el cierre anterior.
echo.
start "" "%~dp0"
echo.
pause
goto :eof

rem ---- mensajes -----------------------------------------------------------
:sin_plantillas
echo   ERROR: no hay archivos .xlsm en la carpeta xls\
echo.
echo   Copia ahi los archivos que te entrega DBNeT (los 41 .xlsm).
echo   Si vienen en un .zip hay que descomprimirlo. No importa si
echo   quedan dentro de otra subcarpeta: igual los encuentra.
echo.
start "" "%~dp0xls"
echo.
pause
goto :eof

:sin_workiva
echo   ERROR: no hay ningun .xlsx en la carpeta workiva\
echo.
echo   Copia ahi el archivo que exportaste de Workiva.
echo   Tambien puedes arrastrarlo directamente sobre este .bat.
echo.
start "" "%~dp0workiva"
echo.
pause
goto :eof

:cancelado
echo.
echo   Cancelado. No se escribio ningun archivo.
echo.
pause
goto :eof

:error
echo.
echo   El proceso termino con errores. Revisa los mensajes de arriba.
echo.
pause
goto :eof

:sin_python
echo   ERROR: Python no esta instalado.
echo   Descargalo desde python.org/downloads y marca "Add Python to PATH"
echo.
pause
