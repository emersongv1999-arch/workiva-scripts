@echo off
chcp 65001 >nul
echo.
echo ============================================================
echo   Compilando: Renombrar Hojas Cash Management
echo ============================================================
echo.

where python >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python no encontrado en el PATH.
    pause & exit /b 1
)

python -m pip install pyinstaller --quiet --disable-pip-version-check

echo Compilando...
python -m PyInstaller ^
    --onefile ^
    --windowed ^
    --name "RenombrarHojasCashManagement" ^
    --hidden-import=tkinter ^
    --hidden-import=tkinter.ttk ^
    --hidden-import=tkinter.messagebox ^
    renombrar_hojas_cashpooling.py

if errorlevel 1 (
    echo.
    echo ERROR durante la compilacion.
    pause & exit /b 1
)

echo.
echo ============================================================
echo   Listo! El ejecutable esta en: dist\RenombrarHojasCashManagement.exe
echo ============================================================
echo.
pause
