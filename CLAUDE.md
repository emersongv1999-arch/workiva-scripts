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

# XBRL DBNeT — app aparte (`XBRL_DBNeT.exe`)

Llena las plantillas .xlsm de DBNeT directo desde Workiva, sin export manual.

| Archivo | Qué hace |
|---------|----------|
| `xbrl_app.py` | Ventana (tkinter). Empresa + período → descarga, simula, llena en su lugar, arma el archivo único |
| `xbrl_workiva.py` | API de Workiva: lista las planillas `E___ XBRL MM-AAAA` y las exporta a .xlsx |
| `llenar_dbnet_desde_workiva.py` / `fusionar_cuadros.py` | Los mismos scripts del .bat; la app los corre como `XBRL_DBNeT.exe --tarea llenar|fusionar ...` |
| `COMPILAR_XBRL.bat` | PyInstaller `--onefile --windowed` con los hidden imports de pywin32 |

Carpeta de trabajo: se elige en la app (arriba a la derecha) y se recuerda en
`%LOCALAPPDATA%\XBRL_DBNeT\config.json` (junto con la última empresa y período); no depende de dónde esté
el .exe. Dentro, una carpeta por empresa (`E211\xls\` con sus plantillas).
Las plantillas se cargan desde la app eligiendo una CARPETA (toma los .xlsm y los .zip de adentro); el juego
anterior pasa entero a `E211\plantillas_anteriores\<fecha>\`, nunca se mezcla (cambia el año en el nombre
y se llenaría dos veces). Si hay dos archivos con el mismo nombre y distinto contenido no carga nada.
La cantidad varía por empresa (E211: 41; E200: ~48). Una empresa nueva aparece sola por el nombre de su planilla.
Lo bajado de Workiva va a `%TEMP%\XBRL_llenado\<empresa>`, no a la carpeta de la empresa; el .xlsx sin
macros solo se arma si el .xlsm no pudo (sin Excel). Cada llenado deja `E211\ultimo_llenado.json`: al volver a la empresa/período la app muestra el resultado,
y si se elige otro período avisa qué período tienen hoy las plantillas.
