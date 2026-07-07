# Auditor — CGE Workiva

Aplicación GUI en tkinter para automatizar tareas de auditoría en Workiva para CGE.

## Archivo principal
`verificar_workiva_GUI.py` — GUI completa (~2800 líneas). Compilar con PyInstaller (ver abajo).

## Credenciales (hardcodeadas, líneas 15-17)
- `CLIENT_ID`, `CLIENT_SECRET`, `WORKSPACE_ID` para Workiva CGE

## Módulos del GUI (NAV_ITEMS)
| ID | Nombre |
|----|--------|
| mod1 | Verificar Workiva |
| mod2 | Llenar Comparativos |
| mod3 | Extractor de Flujo de Efectivo |
| mod4 | (reservado) |
| mod5 | (reservado) |
| mod6 | Validar Comparativos |

## Scripts embebidos (base64 en el GUI)
- `_MCP_V2_SRC` → `workiva_mcp_v2.py` — cliente async MCP v2 (httpx + FastMCP)
- `_LLENAR_V2_SRC` → `llenado_comparativosV2_espejo.py` — llenado de comparativos
- `_VALIDAR_V2_SRC` → `validar_comparativos_v2.py` — validación de comparativos
- `_FLUJO_SRC` → `genera_flujo_efectivo.py` — extractor de flujo

## Cómo actualizar un script embebido
1. Editar el archivo fuente (ej. `workiva_mcp_v2.py`)
2. Re-encodear: `base64.b64encode(open("archivo.py","rb").read()).decode()`
3. Reemplazar la constante `_XXX_SRC` en el GUI
4. Recompilar con PyInstaller

## Compilación
```
pyinstaller --onefile --windowed --name Auditor ^
  --hidden-import pyodbc ^
  --hidden-import httpx ^
  --hidden-import httpx._transports.default ^
  --hidden-import httpcore ^
  --hidden-import mcp ^
  --hidden-import pydantic ^
  --hidden-import dotenv ^
  --hidden-import openpyxl ^
  verificar_workiva_GUI.py
```

## Reglas de negocio — Llenar Comparativos
- Archivos **target**: sin prefijo `(CHN)` ni `(LC)` en el nombre
- Archivos **fuente** (balance, EERR, prev): con prefijo `(CHN)` o `(LC)`
- Se omiten hojas en `SKIP_SHEETS` y `AUX_SKIP_SHEETS` (definidas en workiva_mcp_v2.py)
- Columnas `%` (con valor exacto `"%"` en encabezado) se omiten — solo se llenan columnas M$
- El escaneo de encabezados abarca **todas las filas** de la hoja (no solo las primeras 8), para detectar sub-tablas con encabezados propios

## Branch de desarrollo
`claude/serene-heisenberg-lhy1mh`
