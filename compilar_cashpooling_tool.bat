@echo off
chcp 65001 >nul
echo.
echo ============================================================
echo   Compilando: CGE Cash Management Tool
echo ============================================================
echo.

py -m pip install pyinstaller --quiet --disable-pip-version-check

echo Compilando...
py -m PyInstaller ^
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
