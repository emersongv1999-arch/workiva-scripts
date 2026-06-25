@echo off
chcp 65001 >nul
echo.
echo ============================================================
echo   Compilando: CGE Cash Management Tool
echo ============================================================
echo.

where python >nul 2>&1
if errorlevel 1 (
    where py >nul 2>&1
    if errorlevel 1 (
        echo ERROR: Python no encontrado en el PATH.
        pause & exit /b 1
    )
    set PYTHON=py
) else (
    set PYTHON=python
)

%PYTHON% -m pip install pyinstaller --quiet --disable-pip-version-check

echo Compilando...
%PYTHON% -m PyInstaller ^
    --onefile ^
    --windowed ^
    --name "CGECashManagementTool" ^
    --hidden-import=tkinter ^
    --hidden-import=tkinter.ttk ^
    --hidden-import=tkinter.messagebox ^
    cashpooling_tool.py

if errorlevel 1 (
    echo.
    echo ERROR durante la compilacion.
    pause & exit /b 1
)

echo.
echo ============================================================
echo   Listo! El ejecutable esta en:
echo   dist\CGECashManagementTool.exe
echo ============================================================
echo.
pause
