@echo off
chcp 65001 >nul
echo ============================================================
echo   WORKIVA - Verificador de Sumas EE.FF.
echo ============================================================
echo.

:: 1. Verificar Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Python no esta instalado.
    echo Descargalo desde: https://www.python.org/downloads/
    echo Asegurate de marcar "Add Python to PATH" al instalar.
    pause
    exit /b 1
)
echo [OK] Python encontrado.

:: 2. Instalar librerias
echo.
echo Instalando librerias necesarias...
pip install requests python-dotenv python-docx --quiet
if %errorlevel% neq 0 (
    echo ERROR instalando librerias.
    pause
    exit /b 1
)
echo [OK] Librerias instaladas.

:: 3. Crear .env con credenciales (solo si no existe)
if not exist ".env" (
    echo.
    echo Creando archivo de credenciales .env...
    (
        echo WORKIVA_CLIENT_ID=db2c551e-e18a-417e-8e52-d182716b8ef2
        echo WORKIVA_CLIENT_SECRET=wk_secret:oa2c:DzlUCmBQDv6raPxG09me
        echo WORKIVA_WORKSPACE_ID=w_34913aadaa38420eabd7e4d341b78a1a
    ) > .env
    echo [OK] Credenciales configuradas.
) else (
    echo [OK] Credenciales ya configuradas.
)

:: 4. Ejecutar el verificador
echo.
echo ============================================================
echo   Iniciando verificador...
echo ============================================================
echo.
python verificar_eeff.py

echo.
pause
