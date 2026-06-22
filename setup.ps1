# setup.ps1 — Instala dependencias y crea el .env con las credenciales
# Ejecutar una sola vez antes de correr los scripts Python.
#
# Uso en PowerShell:
#   Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned
#   .\setup.ps1

Write-Host "=== Setup Workiva Scripts ===" -ForegroundColor Cyan

# 1. Verificar Python
$pyVersion = python --version 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Python no encontrado. Instala Python 3.9+ desde https://python.org" -ForegroundColor Red
    exit 1
}
Write-Host "Python: $pyVersion" -ForegroundColor Green

# 2. Instalar dependencias
Write-Host "`nInstalando dependencias..." -ForegroundColor Yellow
pip install -r requirements.txt --quiet
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR instalando dependencias" -ForegroundColor Red
    exit 1
}
Write-Host "Dependencias instaladas OK" -ForegroundColor Green

# 3. Crear .env si no existe
if (-Not (Test-Path ".env")) {
    Write-Host "`nCreando archivo .env con credenciales..." -ForegroundColor Yellow
    @"
WORKIVA_CLIENT_ID=db2c551e-e18a-417e-8e52-d182716b8ef2
WORKIVA_CLIENT_SECRET=wk_secret:oa2c:DzlUCmBQDv6raPxG09me
WORKIVA_WORKSPACE_ID=w_34913aadaa38420eabd7e4d341b78a1a
"@ | Out-File -FilePath ".env" -Encoding UTF8
    Write-Host ".env creado" -ForegroundColor Green
} else {
    Write-Host ".env ya existe, no se sobreescribe" -ForegroundColor Gray
}

Write-Host "`n=== Listo! Ahora ejecuta los pasos en orden ===" -ForegroundColor Cyan
Write-Host "  python 1_listar_documentos_junio.py" -ForegroundColor White
Write-Host "  python 2_descargar_docx.py" -ForegroundColor White
Write-Host "  python 3_verificar_sumas.py" -ForegroundColor White
