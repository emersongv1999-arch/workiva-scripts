#!/usr/bin/env python3
"""
workiva_mcp.py
==============
Servidor MCP (Model Context Protocol) para Workiva / Wdesk.

Expone herramientas para:
  - Descubrir y leer spreadsheets (Platform API)
  - Escribir valores en celdas (Platform API)
  - Consultar tablas y queries (WData Prep API)
  - Flujos de alto nivel: llenar comparativos, verificar sumas, cruzar notas

TRANSPORTE: stdio (corre en tu máquina → tiene acceso a la red corporativa)

INICIO RÁPIDO:
  pip install mcp httpx python-dotenv
  python workiva_mcp.py

CONFIG Claude Desktop (claude_desktop_config.json):
  {
    "mcpServers": {
      "workiva": {
        "command": "python",
        "args": ["C:/Users/safloreso/Desktop/CLAUDE/proyecto1/workiva_mcp.py"],
        "env": {}
      }
    }
  }
"""

from __future__ import annotations

import asyncio
import csv
import io
import json
import os
import re
import time
import warnings
from contextlib import asynccontextmanager
from typing import Any, Optional

import httpx
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel, ConfigDict, Field

# ── Credenciales ─────────────────────────────────────────────────────────────
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), ".env"))

CLIENT_ID     = os.getenv("WORKIVA_CLIENT_ID", "")
CLIENT_SECRET = os.getenv("WORKIVA_CLIENT_SECRET", "")
WORKSPACE_ID  = os.getenv("WORKIVA_WORKSPACE_ID", "")

# ── Endpoints ─────────────────────────────────────────────────────────────────
TOKEN_URL    = "https://api.app.wdesk.com/iam/v1/oauth2/token"
PLATFORM_URL = "https://api.app.wdesk.com/platform/v1"
WDATA_URL    = "https://h.app.wdesk.com/s/wdata/prep/api/v1"

# La red corporativa usa inspección SSL
VERIFY_SSL = False
warnings.filterwarnings("ignore")


# ══════════════════════════════════════════════════════════════════════════════
# CLIENTE COMPARTIDO CON REFRESH DE TOKEN
# ══════════════════════════════════════════════════════════════════════════════

class WorkivaClient:
    """Cliente HTTP con renovación automática de token (expira en 10 min)."""

    def __init__(self) -> None:
        self._token: str = ""
        self._token_ts: float = 0.0
        self._client: httpx.AsyncClient | None = None

    async def _ensure_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(verify=VERIFY_SSL, timeout=120.0)
        return self._client

    async def _get_token(self) -> str:
        """Obtiene o renueva el token OAuth2."""
        if time.time() - self._token_ts < 540 and self._token:  # 9 min
            return self._token
        client = await self._ensure_client()
        resp = await client.post(
            TOKEN_URL,
            json={
                "grant_type":    "client_credentials",
                "client_id":     CLIENT_ID,
                "client_secret": CLIENT_SECRET,
            },
            headers={"Content-Type": "application/json"},
        )
        resp.raise_for_status()
        self._token    = resp.json()["access_token"]
        self._token_ts = time.time()
        return self._token

    async def _headers(self) -> dict[str, str]:
        token = await self._get_token()
        return {
            "Authorization": f"Bearer {token}",
            "Content-Type":  "application/json",
            "X-Version":     "2022-01-01",
        }

    async def get(self, url: str, **kwargs) -> httpx.Response:
        client = await self._ensure_client()
        return await client.get(url, headers=await self._headers(), **kwargs)

    async def put(self, url: str, **kwargs) -> httpx.Response:
        client = await self._ensure_client()
        return await client.put(url, headers=await self._headers(), **kwargs)

    async def post(self, url: str, **kwargs) -> httpx.Response:
        client = await self._ensure_client()
        return await client.post(url, headers=await self._headers(), **kwargs)

    async def close(self) -> None:
        if self._client and not self._client.is_closed:
            await self._client.aclose()


_wk = WorkivaClient()


# ══════════════════════════════════════════════════════════════════════════════
# HELPERS INTERNOS
# ══════════════════════════════════════════════════════════════════════════════

_PREFIX_RE = re.compile(r"^\s*\([^)]*\)\s*")


def _strip_prefix(name: str) -> str:
    """Quita prefijos entre paréntesis al inicio del nombre: '(CHN) E215_...' → 'E215_...'."""
    return _PREFIX_RE.sub("", name or "").strip()


_MESES = {
    "enero": 1, "febrero": 2, "marzo": 3, "abril": 4, "mayo": 5, "junio": 6,
    "julio": 7, "agosto": 8, "septiembre": 9, "setiembre": 9, "octubre": 10,
    "noviembre": 11, "diciembre": 12,
}

# Hojas con patrón "bloque doble": el bloque superior tiene datos del período actual
# y el bloque inferior es el comparativo que debe llenarse desde el archivo fuente.
# Valor: (split_cell, period_cell)
#   split_cell:  referencia de la celda cuya FILA indica dónde empieza el bloque inferior
#   period_cell: referencia de la celda cuyo VALOR contiene la fecha del período fuente
# Búsqueda por prefijo del nombre de hoja para tolerar variaciones entre plantillas.
_DOUBLE_BLOCK_CONFIG: dict[str, tuple[str, str]] = {
    "E.- Estado de cambios de patrimonio":                         ("D45", "D71"),
    "L.- Nota de riesgo":                                          ("B18", "B18"),
    "N.- Nota de riesgo":                                          ("B18", "B18"),
    "O.- Resumen de deuda":                                        ("B15", "B15"),
    "1,b Efectivo y equivalentes al efectivo":                     ("B33", "B33"),
    "9.- Instrumentos financieros a valor razonable con cambios":  ("D24", "D24"),
    "10.- Instrumentos financieros medidos a valor razonable":     ("D25", "D25"),
    "11.- Instrumentos financieros medidos a valor razonable":     ("D24", "D24"),
    "12.- Activos financieros disponibles para la venta":          ("D25", "D25"),
    "19.- Estratificación de la cartera":                          ("B23", "B23"),
    "21.- Cartera en cobranza judicial":                           ("B18", "B18"),
    "34.- Movimiento de inversiones en asociadas":                  ("AD21", "AD21"),
    "35.- Inversiones en asociadas":                               ("F17", "F17"),
    "36.- Movimiento de inversiones en sociedades con control":     ("AD23", "AD23"),
    "37.- Inversiones en sociedades con control conjunto":         ("F19", "F19"),
    "38.- Otra información de inversiones en sociedades":          ("AD20", "AD20"),
    "39.- Movimiento de inversiones en sociedades subsidiarias":   ("D25", "D25"),
    "40.- Inversiones en sociedades subsidiarias directas":        ("F29", "F29"),
    "41.- Activos Intangibles":                                    ("D22", "D22"),
    "43.- Movimientos en activos intangibles":                     ("D41", "D41"),
    "44.- Detalle de otros activos identificables al":             ("B22", "B22"),
    "82.- Obligaciones con el público pagarés":                    ("R20", "R20"),
    "86.- Cuentas comerciales con pagos al día":                   ("D44", "D44"),
    "88.- Movimiento de las provisiones":                          ("P37", "P37"),
    "93.- Hipótesis actuariales":                                  ("D49", "D49"),
    "101.- Transacciones con participaciones no controladoras":    ("D24", "D24"),
}


def _get_double_block_cfg(sname: str):
    """Retorna (split_cell, period_cell) para la hoja, o None. Búsqueda por prefijo."""
    if sname in _DOUBLE_BLOCK_CONFIG:
        return _DOUBLE_BLOCK_CONFIG[sname]
    for key, val in _DOUBLE_BLOCK_CONFIG.items():
        if sname.startswith(key):
            return val
    return None


def _parse_fecha(s: Any) -> str | None:
    """Normaliza una fecha a 'YYYY-MM-DD'. Acepta ISO, DD-MM-YYYY, DD/MM/YYYY
    y texto en español ('31 de diciembre de 2025')."""
    t = str(s or "").strip().lower()
    if not t:
        return None
    m = re.search(r"(\d{4})-(\d{1,2})-(\d{1,2})", t)
    if m:
        y, mo, d = m.groups()
        return f"{y}-{int(mo):02d}-{int(d):02d}"
    m = re.search(r"(\d{1,2})[/.-](\d{1,2})[/.-](\d{4})", t)
    if m:
        d, mo, y = m.groups()
        if 1 <= int(mo) <= 12:
            return f"{y}-{int(mo):02d}-{int(d):02d}"
    m = re.search(r"(\d{1,2})\s+de\s+([a-záéíóúñ]+)\s+(?:de\s+|del\s+)?(\d{4})", t)
    if m:
        d, mes_txt, y = m.groups()
        mo = _MESES.get(mes_txt)
        if mo:
            return f"{y}-{mo:02d}-{int(d):02d}"
    return None


def _kw_variants(iso: str, raw: Any = None) -> list[str]:
    """Formas en que una fecha puede aparecer en un encabezado de columna."""
    y, mo, d = iso.split("-")
    mes_nombre = next(k for k, v in _MESES.items() if v == int(mo))
    variants = {
        iso,
        f"{d}-{mo}-{y}", f"{int(d)}-{int(mo)}-{y}",
        f"{d}/{mo}/{y}", f"{int(d)}/{int(mo)}/{y}",
        f"{d}.{mo}.{y}",
        f"{int(d)} de {mes_nombre} de {y}",
        f"{int(d)} de {mes_nombre} del {y}",
        f"{mes_nombre} {y}", f"{mes_nombre} de {y}",
        f"{mes_nombre[:3]}-{y}", f"{mes_nombre[:3]}-{y[2:]}",
        f"{mes_nombre[:3]}.{y[2:]}", f"{mes_nombre[:3]} {y}",
    }
    if raw:
        variants.add(str(raw).strip())
    return [v.lower() for v in variants if v]


def _col_letter(idx: int) -> str:
    if idx < 26:
        return chr(65 + idx)
    return chr(64 + idx // 26) + chr(65 + idx % 26)


def _parse_cell_ref(ref: str) -> tuple[int, int]:
    """'B18' → (row=17, col=1), 0-indexed. Returns (-1,-1) si no parseable."""
    m = re.match(r"([A-Za-z]+)(\d+)", ref.strip())
    if not m:
        return (-1, -1)
    col_str, row_str = m.groups()
    col = 0
    for ch in col_str.upper():
        col = col * 26 + (ord(ch) - ord("A") + 1)
    return (int(row_str) - 1, col - 1)  # 0-indexed


def _cv(cell: Any) -> Any:
    """Retorna el calculatedValue de una celda."""
    if isinstance(cell, dict):
        return cell.get("calculatedValue")
    return None


def _is_formula(row: list, col: int) -> bool:
    if col >= len(row):
        return False
    c = row[col]
    return str(c.get("value", "") if isinstance(c, dict) else "").startswith("=")


def _row_label(row: list, col_limit: int) -> str:
    """Primera etiqueta de texto en columnas A..col_limit-1 de la fila."""
    for ci in range(min(col_limit, len(row))):
        v = _cv(row[ci]) if isinstance(row[ci], dict) else None
        if v and isinstance(v, str) and v.strip():
            return v.strip()
    return ""


async def _get_json(url: str, attempts: int = 4) -> dict:
    """GET con reintentos ante rate limits o respuestas no-JSON transitorias."""
    last_exc: Exception | None = None
    for k in range(attempts):
        try:
            r = await _wk.get(url)
            r.raise_for_status()
            return r.json()
        except Exception as e:
            last_exc = e
            if k < attempts - 1:
                await asyncio.sleep(3 * (k + 1))
    raise last_exc  # type: ignore[misc]


async def _get_sheets(ss_id: str) -> dict[str, str]:
    """name → id para todas las hojas de un spreadsheet."""
    result: dict[str, str] = {}
    url = f"{PLATFORM_URL}/spreadsheets/{ss_id}/sheets"
    while url:
        data = await _get_json(url)
        for s in data.get("data", []):
            result[s["name"]] = s["id"]
        url = data.get("@nextLink")
    return result


async def _read_sheet_cells(ss_id: str, sheet_id: str) -> list[list]:
    """Retorna cells (lista de filas, cada fila lista de celdas).

    Lanza httpx.HTTPStatusError si la lectura falla — el llamador decide
    si reintenta o reporta; una hoja que falla nunca pasa como vacía.
    """
    url = (
        f"{PLATFORM_URL}/spreadsheets/{ss_id}/sheets/{sheet_id}"
        "/sheetdata?$fields=cells.calculatedValue,cells.value&$maxcellsperpage=50000"
    )
    r = await _wk.get(url)
    r.raise_for_status()
    return r.json().get("data", {}).get("cells", [])


async def _read_sheet_cells_retry(ss_id: str, sheet_id: str,
                                   attempts: int = 3) -> list[list]:
    """_read_sheet_cells con reintentos y pausa creciente ante fallos transitorios."""
    last_exc: Exception | None = None
    for k in range(attempts):
        try:
            return await _read_sheet_cells(ss_id, sheet_id)
        except Exception as e:
            last_exc = e
            if k < attempts - 1:
                await asyncio.sleep(3 * (k + 1))
    raise last_exc  # type: ignore[misc]


async def _poll_operation(location: str, max_attempts: int = 40) -> bool:
    """Espera a que una operación async de Platform API termine."""
    if not location.startswith("http"):
        location = "https://api.app.wdesk.com" + location
    for _ in range(max_attempts):
        await asyncio.sleep(3)
        try:
            body = (await _wk.get(location)).json()
            st   = body.get("status", body.get("data", {}).get("status", ""))
            if st == "completed":
                return True
            if st in ("failed", "error"):
                return False
        except Exception:
            pass
    return False


async def _write_column(ss_id: str, sid: str, col_idx: int,
                         values: list, start_row: int = 0) -> bool:
    """Escribe la columna col_idx en segmentos contiguos de valores no-None.
    Si un segmento falla (p.ej. celda con link Workiva), reintenta celda a celda
    dentro de ese segmento, salteando las celdas que fallen y loguéandolas.
    Retorna True si al menos todos los segmentos con datos se escribieron
    sin error irrecuperable (las celdas saltadas no son error)."""
    cl = _col_letter(col_idx)
    base_url = f"{PLATFORM_URL}/spreadsheets/{ss_id}/sheets/{sid}/values"

    # Armar segmentos contiguos de valores non-None
    segments: list[tuple[int, int]] = []  # (offset_inicio, offset_fin_exclusive)
    i = 0
    while i < len(values):
        if values[i] is not None:
            j = i + 1
            while j < len(values) and values[j] is not None:
                j += 1
            segments.append((i, j))
            i = j
        else:
            i += 1

    all_ok = True
    for seg_start, seg_end in segments:
        seg_vals = values[seg_start:seg_end]
        r1 = start_row + seg_start + 1
        r2 = start_row + seg_end      # último fila 1-indexed = start_row + seg_end
        rng = f"{cl}{r1}:{cl}{r2}"
        rp = await _wk.put(
            f"{base_url}/{rng}",
            json={"values": [[v] for v in seg_vals]},
        )
        if rp.status_code == 202:
            if not await _poll_operation(rp.headers.get("Location", "")):
                all_ok = False
            continue
        # El segmento falló → intentar celda a celda
        print(f"  [write_column] segmento {rng} ({rp.status_code}), reintentando celda a celda")
        for k, v in enumerate(seg_vals):
            row_1idx = r1 + k
            cell_rng = f"{cl}{row_1idx}"
            rp2 = await _wk.put(
                f"{base_url}/{cell_rng}",
                json={"values": [[v]]},
            )
            if rp2.status_code == 202:
                if not await _poll_operation(rp2.headers.get("Location", "")):
                    print(f"  [write_column] FALLO poll {cell_rng}")
                    all_ok = False
            else:
                print(f"  [write_column] {rp2.status_code} {cell_rng} (link/protegida, se salta): {rp2.text[:200]}")
                # Celda con link Workiva u otra protección: se salta, no es error de la columna
    return all_ok


async def _load_all_files() -> dict[str, str]:
    """Retorna name → id de todos los archivos del workspace."""
    result: dict[str, str] = {}
    url = f"{PLATFORM_URL}/files?workspaceId={WORKSPACE_ID}&limit=100"
    while url:
        data = await _get_json(url)
        for f in data.get("data", []):
            result[f["name"]] = f["id"]
        url = data.get("@nextLink")
    return result


def _handle_error(e: Exception) -> str:
    if isinstance(e, httpx.HTTPStatusError):
        code = e.response.status_code
        if code == 401:
            return "Error: No autenticado. Verifica CLIENT_ID y CLIENT_SECRET en .env"
        if code == 403:
            return "Error: Sin permisos para este recurso."
        if code == 404:
            return "Error: Recurso no encontrado. Verifica el ID."
        if code == 429:
            return "Error: Rate limit alcanzado. Espera un momento."
        return f"Error HTTP {code}: {e.response.text[:200]}"
    if isinstance(e, httpx.TimeoutException):
        return "Error: Timeout. La operación tardó demasiado."
    return f"Error inesperado: {type(e).__name__}: {e}"


# ══════════════════════════════════════════════════════════════════════════════
# SERVIDOR MCP
# ══════════════════════════════════════════════════════════════════════════════

@asynccontextmanager
async def lifespan(server):  # type: ignore[type-arg]
    yield
    await _wk.close()


mcp = FastMCP("workiva_mcp", lifespan=lifespan)


# ─── 1. LISTAR ARCHIVOS ──────────────────────────────────────────────────────

class ListFilesInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    pattern:  Optional[str] = Field(default=None, description="Patrón regex para filtrar por nombre (ej: 'E200.*06-2026')")
    limit:    int            = Field(default=50,   description="Máximo de resultados", ge=1, le=500)
    offset:   int            = Field(default=0,    description="Desplazamiento para paginación", ge=0)


@mcp.tool(
    name="workiva_list_files",
    annotations={"readOnlyHint": True, "destructiveHint": False,
                  "idempotentHint": True, "openWorldHint": True}
)
async def workiva_list_files(params: ListFilesInput) -> str:
    """Lista archivos (spreadsheets) del workspace de Workiva.

    Usa esto para descubrir IDs de archivos "Base Notas" antes de operar sobre ellos.

    Args:
        params.pattern: Regex para filtrar por nombre (ej: 'E200_IND_06-2026')
        params.limit:   Máximo de resultados (default 50)
        params.offset:  Para paginación

    Returns:
        JSON con lista de {name, id} filtrada y paginada.
    """
    try:
        all_files = await _load_all_files()
        items = list(all_files.items())

        if params.pattern:
            rx    = re.compile(params.pattern, re.IGNORECASE)
            items = [(n, i) for n, i in items if rx.search(n)]

        total     = len(items)
        page      = items[params.offset: params.offset + params.limit]
        has_more  = total > params.offset + len(page)

        return json.dumps({
            "total":       total,
            "count":       len(page),
            "offset":      params.offset,
            "has_more":    has_more,
            "next_offset": params.offset + len(page) if has_more else None,
            "files":       [{"name": n, "id": i} for n, i in page],
        }, indent=2, ensure_ascii=False)
    except Exception as e:
        return _handle_error(e)


# ─── 2. LISTAR HOJAS DE UN SPREADSHEET ───────────────────────────────────────

class GetSheetsInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    spreadsheet_id: str = Field(..., description="ID del spreadsheet (obtenido con workiva_list_files)")


@mcp.tool(
    name="workiva_get_sheets",
    annotations={"readOnlyHint": True, "destructiveHint": False,
                  "idempotentHint": True, "openWorldHint": True}
)
async def workiva_get_sheets(params: GetSheetsInput) -> str:
    """Lista todas las hojas de un spreadsheet de Workiva.

    Args:
        params.spreadsheet_id: ID del archivo (de workiva_list_files)

    Returns:
        JSON con {name, id} de cada hoja.
    """
    try:
        sheets = await _get_sheets(params.spreadsheet_id)
        return json.dumps({
            "spreadsheet_id": params.spreadsheet_id,
            "count":  len(sheets),
            "sheets": [{"name": n, "id": i} for n, i in sheets.items()],
        }, indent=2, ensure_ascii=False)
    except Exception as e:
        return _handle_error(e)


# ─── 3. LEER HOJA ─────────────────────────────────────────────────────────────

class ReadSheetInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    spreadsheet_id: str      = Field(..., description="ID del spreadsheet")
    sheet_name:     str      = Field(..., description="Nombre de la hoja (ej: 'A.- Activos', 'Bases')")
    max_rows:       int      = Field(default=200, description="Máximo de filas a retornar", ge=1, le=2000)
    skip_empty:     bool     = Field(default=True,  description="Si True, omite filas completamente vacías")
    col_start:      int      = Field(default=0,     description="Columna inicial (base 0)", ge=0)
    col_end:        Optional[int] = Field(default=None, description="Columna final exclusiva (base 0). None = todas")


@mcp.tool(
    name="workiva_read_sheet",
    annotations={"readOnlyHint": True, "destructiveHint": False,
                  "idempotentHint": True, "openWorldHint": True}
)
async def workiva_read_sheet(params: ReadSheetInput) -> str:
    """Lee el contenido de una hoja de Workiva y retorna las celdas con sus valores calculados.

    Útil para revisar datos, verificar sumas o extraer comparativos.

    Args:
        params.spreadsheet_id: ID del archivo
        params.sheet_name:     Nombre exacto de la hoja
        params.max_rows:       Máximo de filas (default 200)
        params.skip_empty:     Omitir filas vacías (default True)
        params.col_start:      Columna inicial base-0 (default 0)
        params.col_end:        Columna final base-0 exclusiva (default None = todas)

    Returns:
        JSON con filas [{row_idx, values: [col0, col1, ...]}]
    """
    try:
        sheets = await _get_sheets(params.spreadsheet_id)
        sid    = sheets.get(params.sheet_name)
        if not sid:
            available = ", ".join(sheets.keys())
            return f"Error: Hoja '{params.sheet_name}' no encontrada. Hojas disponibles: {available}"

        cells = await _read_sheet_cells(params.spreadsheet_id, sid)
        rows  = []
        for i, row in enumerate(cells[: params.max_rows]):
            col_end = params.col_end if params.col_end is not None else len(row)
            vals    = [_cv(row[j]) if j < len(row) else None
                       for j in range(params.col_start, col_end)]
            str_vals = [str(v) if v is not None else "" for v in vals]
            if params.skip_empty and not any(v for v in str_vals):
                continue
            rows.append({"row_idx": i, "values": vals})

        return json.dumps({
            "spreadsheet_id": params.spreadsheet_id,
            "sheet_name":     params.sheet_name,
            "total_rows":     len(cells),
            "returned_rows":  len(rows),
            "col_start":      params.col_start,
            "rows":           rows,
        }, indent=2, ensure_ascii=False)
    except Exception as e:
        return _handle_error(e)


# ─── 4. ESCRIBIR COLUMNA ─────────────────────────────────────────────────────

class WriteColumnInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    spreadsheet_id: str         = Field(..., description="ID del spreadsheet")
    sheet_name:     str         = Field(..., description="Nombre exacto de la hoja")
    col_index:      int         = Field(..., description="Columna a escribir (base 0, ej: 0=A, 1=B)", ge=0)
    values:         list[Any]   = Field(..., description="Lista de valores a escribir (None = celda vacía)")
    start_row:      int         = Field(default=0, description="Fila inicial (base 0, default 0=fila 1)", ge=0)


@mcp.tool(
    name="workiva_write_column",
    annotations={"readOnlyHint": False, "destructiveHint": False,
                  "idempotentHint": True, "openWorldHint": True}
)
async def workiva_write_column(params: WriteColumnInput) -> str:
    """Escribe una columna de valores en una hoja de Workiva.

    Escribe params.values comenzando en la celda (start_row, col_index).
    Las celdas con fórmulas NO se sobreescriben (es responsabilidad del llamador
    enviar None en esas posiciones si no se quieren tocar).

    Args:
        params.spreadsheet_id: ID del archivo
        params.sheet_name:     Nombre exacto de la hoja
        params.col_index:      Columna base-0 (0=A, 1=B, ...)
        params.values:         Lista de valores. None = no escribe esa celda.
        params.start_row:      Fila inicial base-0 (default 0)

    Returns:
        JSON con resultado de la operación.
    """
    try:
        sheets = await _get_sheets(params.spreadsheet_id)
        sid    = sheets.get(params.sheet_name)
        if not sid:
            return f"Error: Hoja '{params.sheet_name}' no encontrada."

        ok = await _write_column(
            params.spreadsheet_id, sid,
            params.col_index, params.values, params.start_row
        )
        n_written = sum(1 for v in params.values if v is not None)
        return json.dumps({
            "success":     ok,
            "sheet_name":  params.sheet_name,
            "col_letter":  _col_letter(params.col_index),
            "start_row":   params.start_row + 1,
            "end_row":     params.start_row + len(params.values),
            "n_values":    n_written,
        }, indent=2, ensure_ascii=False)
    except Exception as e:
        return _handle_error(e)


# ─── 5. LISTAR TABLAS WDATA ──────────────────────────────────────────────────

class ListTablesInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    pattern: Optional[str] = Field(default=None, description="Regex para filtrar por nombre")
    limit:   int            = Field(default=50,   description="Máximo de resultados", ge=1, le=200)
    offset:  int            = Field(default=0,    description="Desplazamiento para paginación", ge=0)


@mcp.tool(
    name="workiva_list_tables",
    annotations={"readOnlyHint": True, "destructiveHint": False,
                  "idempotentHint": True, "openWorldHint": True}
)
async def workiva_list_tables(params: ListTablesInput) -> str:
    """Lista las tablas disponibles en el workspace WData de Workiva.

    Las tablas contienen los datos importados (trial balance, activo fijo,
    deudores, etc.) que alimentan los spreadsheets de EE.FF.

    Args:
        params.pattern: Regex para filtrar por nombre de tabla
        params.limit:   Máximo de resultados
        params.offset:  Para paginación

    Returns:
        JSON con lista de {id, name, description} de tablas.
    """
    try:
        url  = f"{WDATA_URL}/table?workspaceId={WORKSPACE_ID}"
        r    = await _wk.get(url)
        data = r.json()
        items: list[dict] = data.get("data", [])

        if params.pattern:
            rx    = re.compile(params.pattern, re.IGNORECASE)
            items = [t for t in items if rx.search(t.get("name", ""))]

        total = len(items)
        page  = items[params.offset: params.offset + params.limit]

        return json.dumps({
            "total":       total,
            "count":       len(page),
            "offset":      params.offset,
            "has_more":    total > params.offset + len(page),
            "tables":      [{"id":   t.get("id"),
                              "name": t.get("name"),
                              "desc": t.get("description", "")} for t in page],
        }, indent=2, ensure_ascii=False)
    except Exception as e:
        return _handle_error(e)


# ─── 6. LISTAR QUERIES WDATA ─────────────────────────────────────────────────

class ListQueriesInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    pattern: Optional[str] = Field(default=None, description="Regex para filtrar por nombre")
    limit:   int            = Field(default=50,   description="Máximo de resultados", ge=1, le=200)
    offset:  int            = Field(default=0,    description="Desplazamiento", ge=0)


@mcp.tool(
    name="workiva_list_queries",
    annotations={"readOnlyHint": True, "destructiveHint": False,
                  "idempotentHint": True, "openWorldHint": True}
)
async def workiva_list_queries(params: ListQueriesInput) -> str:
    """Lista las queries guardadas en WData de Workiva.

    Estas queries en SQL extraen datos de las tablas (trial balance, jerarquías,
    activo fijo, etc.) para alimentar los cuadros de los EE.FF.

    Args:
        params.pattern: Regex para filtrar por nombre
        params.limit:   Máximo de resultados
        params.offset:  Para paginación

    Returns:
        JSON con lista de {id, name, statement} de queries.
    """
    try:
        url  = f"{WDATA_URL}/query?workspaceId={WORKSPACE_ID}"
        r    = await _wk.get(url)
        data = r.json()
        items: list[dict] = data.get("data", [])

        if params.pattern:
            rx    = re.compile(params.pattern, re.IGNORECASE)
            items = [q for q in items if rx.search(q.get("name", ""))]

        total = len(items)
        page  = items[params.offset: params.offset + params.limit]

        return json.dumps({
            "total":   total,
            "count":   len(page),
            "offset":  params.offset,
            "has_more": total > params.offset + len(page),
            "queries": [{"id":        q.get("id"),
                          "name":      q.get("name"),
                          "statement": (q.get("statement") or "")[:200]} for q in page],
        }, indent=2, ensure_ascii=False)
    except Exception as e:
        return _handle_error(e)


# ─── 7. EJECUTAR QUERY WDATA ─────────────────────────────────────────────────

class RunQueryInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    query_id:   str              = Field(..., description="ID de la query (de workiva_list_queries)")
    parameters: Optional[dict[str, str]] = Field(
        default=None,
        description="Parámetros para sobreescribir en la query (ej: {'periodo': '2026-03-31'})"
    )
    max_rows:   int              = Field(default=500, description="Máximo de filas a retornar", ge=1, le=5000)


@mcp.tool(
    name="workiva_run_query",
    annotations={"readOnlyHint": True, "destructiveHint": False,
                  "idempotentHint": False, "openWorldHint": True}
)
async def workiva_run_query(params: RunQueryInput) -> str:
    """Ejecuta una query guardada en WData y retorna los resultados como tabla.

    El flujo es: ejecutar → polling hasta COMPLETE → descargar CSV → parsear.
    Puede tardar unos segundos dependiendo del volumen de datos.

    Args:
        params.query_id:   ID de la query (de workiva_list_queries)
        params.parameters: Parámetros a sobreescribir (opcional)
        params.max_rows:   Máximo de filas en resultado (default 500)

    Returns:
        JSON con {columns: [...], rows: [[...], ...], total_rows, truncated}
    """
    try:
        # Ejecutar query
        body: dict[str, Any] = {}
        if params.parameters:
            body["parameters"] = [{"name": k, "value": v}
                                   for k, v in params.parameters.items()]
        r = await _wk.post(
            f"{WDATA_URL}/query/{params.query_id}/result",
            json=body or None,
        )
        if r.status_code not in (200, 201, 202):
            return f"Error al lanzar query: HTTP {r.status_code} — {r.text[:200]}"

        result_id = r.json().get("data", {}).get("id") or r.json().get("id")
        if not result_id:
            return "Error: No se obtuvo ID de resultado de la query."

        # Polling
        for _ in range(60):
            await asyncio.sleep(3)
            poll = await _wk.get(f"{WDATA_URL}/query/{params.query_id}/result/{result_id}")
            status = poll.json().get("data", {}).get("status", "")
            if status == "COMPLETE":
                break
            if status == "ERROR":
                err = poll.json().get("data", {}).get("error", "")
                return f"Error en la query: {err}"

        # Descargar CSV
        dl = await _wk.get(
            f"{WDATA_URL}/query/{params.query_id}/result/{result_id}/download"
        )
        if dl.status_code != 200:
            return f"Error al descargar resultado: HTTP {dl.status_code}"

        reader  = csv.DictReader(io.StringIO(dl.text))
        columns = reader.fieldnames or []
        rows    = [list(row.values()) for row in reader]

        truncated = len(rows) > params.max_rows
        rows      = rows[: params.max_rows]

        return json.dumps({
            "query_id":   params.query_id,
            "result_id":  result_id,
            "columns":    list(columns),
            "total_rows": len(rows),
            "truncated":  truncated,
            "rows":       rows,
        }, indent=2, ensure_ascii=False)
    except Exception as e:
        return _handle_error(e)


# ─── 8. LLENAR COMPARATIVOS ──────────────────────────────────────────────────

class FillComparativesInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    spreadsheet_id: str = Field(..., description="ID del archivo Base Notas destino")
    dry_run:        bool = Field(
        default=True,
        description="Si True, solo reporta qué se escribiría sin modificar Workiva (recomendado para revisar primero)"
    )
    sheet_offset:   int  = Field(default=0,     description="Índice de hoja inicial para paginación", ge=0)
    max_sheets:     int  = Field(default=50,    description="Máximo de hojas a procesar en este lote", ge=1, le=500)
    detalle_filas:  bool = Field(default=False, description="Si True, incluye detalle fila por fila (comparacion por hoja)")


@mcp.tool(
    name="workiva_fill_comparatives",
    annotations={"readOnlyHint": False, "destructiveHint": False,
                  "idempotentHint": True, "openWorldHint": True}
)
async def workiva_fill_comparatives(params: FillComparativesInput) -> str:
    """Llena las columnas comparativas de un archivo 'Base Notas' en Workiva.

    Lee la hoja 'Bases' del archivo destino para determinar el período actual
    y el período comparativo (prior_end, prior_eerr_end, etc.), busca los
    archivos fuente correspondientes, y copia los valores de período anterior
    a las columnas comparativas del destino.

    IMPORTANTE: Usa dry_run=True primero para revisar qué se modificaría.

    Args:
        params.spreadsheet_id: ID del archivo Base Notas (de workiva_list_files)
        params.dry_run:        Si True, solo reporta sin escribir (default True)

    Returns:
        JSON con resumen de hojas procesadas, columnas detectadas y operaciones
        realizadas (o que se realizarían en modo dry_run).
    """
    SKIP_SHEETS = {
        "CP", "Bases", "Query BPC", "Query HANA AF", "Reporte en $",
        "Query - HANA - Deudores", "A.- Activos PPT",
        "B.- Patrimonio y Pasivos PPT", "C.- Estado de resultado por función PPT",
        "E1 Res Acumulado", "F1 Cuadraje Hoja A.- Saldo Inicial de Caja",
    }

    try:
        # 1. Leer hojas del destino
        tgt_sheets = await _get_sheets(params.spreadsheet_id)
        if "Bases" not in tgt_sheets:
            return "Error: El archivo no tiene hoja 'Bases'. Verifica que sea un archivo Base Notas."

        # 2. Leer Bases — el bloque de fechas se ancla por la etiqueta
        # "Estados financieros" y tolera filas en blanco intercaladas,
        # en vez de asumir filas fijas 13-17 (layouts varían entre plantillas).
        bases_cells = await _read_sheet_cells_retry(params.spreadsheet_id, tgt_sheets["Bases"])
        bases: dict[str, str] = {}
        block_keys = [
            ("current_end",     "prior_end"),
            ("eerr_start",      "prior_eerr_start"),
            ("eerr_end",        "prior_eerr_end"),
            ("quarter_start",   "prior_quarter_start"),
            ("prev_period_end", "prior_prev_period_end"),
        ]

        def _row_dates(row: list) -> list[str]:
            """Fechas (ISO) encontradas en las primeras columnas de la fila."""
            found = []
            for c in row[:10]:
                iso = _parse_fecha(_cv(c)) if isinstance(c, dict) else None
                if iso:
                    found.append(iso)
            return found

        anchor = 12  # fallback: layout clásico
        for idx, row in enumerate(bases_cells[:40]):
            labels = " ".join(str(_cv(c) or "") for c in row[:4]
                              if isinstance(c, dict)).lower()
            if "estados financieros" in labels:
                anchor = idx
                break

        # Una fila solo consume una clave del bloque si contiene fechas;
        # filas en blanco o de puro texto (encabezados) se saltan.
        row_idx, key_idx = anchor, 0
        while key_idx < len(block_keys) and row_idx < min(len(bases_cells), anchor + 20):
            fechas = _row_dates(bases_cells[row_idx])
            if fechas:
                key_c, key_p = block_keys[key_idx]
                bases[key_c] = fechas[0]
                if len(fechas) > 1:
                    bases[key_p] = fechas[1]
                key_idx += 1
            row_idx += 1

        curr_end  = bases.get("current_end", "?")
        prior_end = bases.get("prior_end", "?")

        report: dict[str, Any] = {
            "spreadsheet_id": params.spreadsheet_id,
            "dry_run":        params.dry_run,
            "current_end":    curr_end,
            "prior_end":      prior_end,
            "bases":          bases,
            "sheet_offset":               params.sheet_offset,
            "batch_size":                 0,
            "has_more":                   False,
            "next_offset":                None,
            "total_candidate_sheets":     0,
            "skipped_desglose_sociedad":  0,
            "sheets_processed": [],
            "sheets_skipped":   [],
            "sheets_failed":    [],
            "total_cols_written": 0,
            "total_cols_failed":  0,
        }

        # 3. Buscar archivos fuente (a partir del nombre del destino)
        all_files = await _load_all_files()
        # Obtener nombre del archivo destino
        id_to_name = {v: k for k, v in all_files.items()}
        target_name = id_to_name.get(params.spreadsheet_id, "")

        # Parsear el nombre ignorando prefijos '(CHN) ', '(LC) ', etc.:
        # [(PREFIJO) ]E{code}_{tipo}_{MM}-{YYYY}_{suffix}
        m = re.match(r"(E\d+)_(IND|CONSO)_(\d{2})[-_](\d{4})_(.*)",
                     _strip_prefix(target_name), re.IGNORECASE)
        if not m:
            report["warning"] = (
                f"Nombre '{target_name}' no sigue el patrón esperado "
                "(se aceptan prefijos entre paréntesis, ej: '(CHN) E215_IND_MM-YYYY_...'). "
                "Se omite la búsqueda de fuentes automática."
            )
            return json.dumps(report, indent=2, ensure_ascii=False)

        code, tipo, mm, yyyy, suffix = m.groups()

        # El balance comparativo es siempre diciembre del año anterior al del
        # nombre del archivo. Si Bases no entregó un prior_end válido (layouts
        # de plantilla distintos, fechas en texto, etc.), se deriva del nombre.
        expected_prior = f"{int(yyyy) - 1}-12-31"
        prior_iso = _parse_fecha(bases.get("prior_end"))
        if not prior_iso or not prior_iso.startswith(f"{int(yyyy) - 1}-12"):
            report["prior_end_nota"] = (
                f"prior_end de Bases era '{bases.get('prior_end', '(vacío)')}'; "
                f"se usa {expected_prior} derivado del nombre del archivo."
            )
            prior_iso = expected_prior
        prior_end = prior_iso
        report["prior_end"] = prior_end

        if curr_end == "?":
            import calendar
            last_day = calendar.monthrange(int(yyyy), int(mm))[1]
            curr_end = f"{yyyy}-{mm}-{last_day:02d}"
            report["current_end"] = f"{curr_end} (derivado del nombre)"

        def _date_parts(d: str) -> tuple[str, str]:
            parts = str(d).split("-")
            return (parts[1], parts[0]) if len(parts) >= 2 else ("", "")

        # Extraer el prefijo del destino (ej: "(CHN) ", "(LC) ", "")
        # La fuente debe tener el MISMO prefijo que el destino: son entidades
        # distintas y no deben mezclarse entre sí.
        m_prefix = re.match(r"^(\s*\([^)]*\)\s*)", target_name)
        dest_prefix = m_prefix.group(1) if m_prefix else ""

        # Índice case-insensitive del nombre sin prefijo → (nombre real, id)
        norm_files: dict[str, tuple[str, str]] = {}
        for fname, fid_ in all_files.items():
            norm_files.setdefault(_strip_prefix(fname).lower(), (fname, fid_))

        # ── Resolución de archivos fuente por período ─────────────────────
        # Cada columna comparativa puede apuntar a un período distinto:
        #   · balance y notas de saldo → dic del año anterior (12-2025)
        #   · EERR y notas de resultado → mismo mes del año anterior (09-2025)
        #   · períodos intermedios → 06-2025, etc.
        # La fuente debe tener el MISMO prefijo que el destino.
        lower_files = {n.lower(): n for n in all_files}
        _src_cache: dict[str, Any] = {}

        async def _resolve_source(mm_s: str, yy_s: str):
            """(mm, yyyy) → {'name','id','sheets'} de la fuente, o None."""
            key = f"{mm_s}-{yy_s}"
            if key in _src_cache:
                return _src_cache[key]
            found = None
            for sep in ["-", "_"]:
                bare = f"{code}_{tipo}_{mm_s}{sep}{yy_s}_{suffix}"
                cand = (dest_prefix + bare).strip().lower()
                if cand in lower_files:
                    name = lower_files[cand]
                    found = {"name": name, "id": all_files[name]}
                    break
                if not dest_prefix:
                    hit = norm_files.get(bare.lower())
                    if hit:
                        found = {"name": hit[0], "id": hit[1]}
                        break
            if found:
                found["sheets"] = await _get_sheets(found["id"])
            _src_cache[key] = found
            report["sources"][key] = found["name"] if found else None
            return found

        report["sources"] = {}
        prior_year = str(int(yyyy) - 1)
        _BLOQUE_RE = re.compile(r"movimiento\s+(?:del\s+)?a[ñn]o\s+(\d{4})",
                                re.IGNORECASE)

        def _year_markers(cells: list) -> list[tuple[int, str]]:
            """Filas que abren un bloque anual: [(fila, año), ...]."""
            out = []
            for ri, row in enumerate(cells):
                for cell in row[:4]:
                    if isinstance(cell, dict):
                        m_b = _BLOQUE_RE.search(str(_cv(cell) or ""))
                        if m_b:
                            out.append((ri, m_b.group(1)))
                            break
            return out

        # Fuente balance (dic año anterior): la principal, informativa
        mm_b, yy_b = _date_parts(prior_end)
        src_balance = await _resolve_source(mm_b, yy_b)
        if src_balance:
            report["source_balance"] = src_balance["name"]

        # 4. Por cada hoja del destino, detectar y llenar columnas comparativas.
        # Cada hoja se lee y escribe de inmediato (commit por hoja): si algo
        # falla a mitad de camino, lo ya escrito persiste y una nueva corrida
        # retoma solo lo pendiente gracias a la idempotencia por columna.
        #
        # Reglas por tipo de hoja (derivadas de la estructura real de los
        # archivos Base Notas):
        #   1. Columnas con fecha del año anterior en el encabezado → se
        #      llenan desde el archivo del período de esa fecha (12-2025 para
        #      balance, 09-2025 / 06-2025 para EERR), columna fuente = -2.
        #   2. A.- y B.- (balance) solo se llenan en cierres de marzo.
        #   3. Hojas de bloques anuales ("Movimiento año YYYY", ej. hoja 60):
        #      el bloque del año anterior se copia desde el archivo de
        #      diciembre del año anterior, donde ese movimiento es el bloque
        #      del año en curso (offset de filas, mismas columnas).

        # Pre-pase: clasificar hojas en omitidas (fijas/desglose) y candidatas.
        _DESGLOSE_RE = re.compile(r"desglose\s+(?:por\s+)?sociedad", re.IGNORECASE)
        candidate_sheets: list[tuple[str, str]] = []
        for sname_c, sid_c in tgt_sheets.items():
            if sname_c in SKIP_SHEETS:
                report["sheets_skipped"].append(sname_c)
            elif _DESGLOSE_RE.search(sname_c):
                report["skipped_desglose_sociedad"] += 1
            else:
                candidate_sheets.append((sname_c, sid_c))

        total_cands = len(candidate_sheets)
        report["total_candidate_sheets"] = total_cands
        p_start = params.sheet_offset
        p_end   = params.sheet_offset + params.max_sheets
        page_sheets = candidate_sheets[p_start:p_end]
        report["batch_size"] = len(page_sheets)
        report["has_more"]   = total_cands > p_end
        report["next_offset"] = p_end if report["has_more"] else None

        for sname, sid_t in page_sheets:

            try:
                tgt_cells = await _read_sheet_cells_retry(params.spreadsheet_id, sid_t)
            except Exception as e:
                report["sheets_failed"].append(
                    {"sheet": sname, "error": _handle_error(e)}
                )
                continue
            if not tgt_cells:
                report["sheets_skipped"].append(f"{sname} (vacía)")
                continue

            # Fecha fin de cada columna: la mayor fecha parseable de sus
            # encabezados (una columna del/al tiene dos fechas; manda el fin).
            col_dates: dict[int, str] = {}
            for row in tgt_cells[:8]:
                for j, cell in enumerate(row):
                    if isinstance(cell, dict):
                        for val_key in ("calculatedValue", "value"):
                            iso = _parse_fecha(cell.get(val_key))
                            if iso:
                                if j not in col_dates or iso > col_dates[j]:
                                    col_dates[j] = iso
                                break

            # Comparativas = columnas cuya fecha fin es del año anterior y
            # es un cierre real (día ≥ 28); fechas sueltas como 01-01 (inicio
            # de período) o días intermedios no definen columna comparativa.
            comp_cols: dict[int, str] = {
                j: d for j, d in col_dates.items()
                if d[:4] == prior_year and int(d[8:10]) >= 28
            }

            is_balance_sheet = re.match(r"^[AB]\.-", sname)

            # ── REGLA 1 y 2: columnas comparativas por fecha ─────────────────
            if comp_cols:
                def _col_filled(col: int) -> bool:
                    for row in tgt_cells[6:]:
                        if col < len(row):
                            v = _cv(row[col])
                            if isinstance(v, (int, float)) and v != 0:
                                return True
                    return False

                sheet_report: dict[str, Any] = {
                    "sheet":     sname,
                    "comp_cols": {_col_letter(c): d
                                  for c, d in sorted(comp_cols.items())},
                    "cols_written": 0,
                    "cols_failed":  [],
                    "cols_skipped": [],
                }
                if params.detalle_filas:
                    sheet_report["comparacion"] = []
                src_data_cache: dict[str, Any] = {}

                for dest_col, d_iso in sorted(comp_cols.items()):
                    letra = _col_letter(dest_col)
                    if is_balance_sheet and mm != "03":
                        sheet_report["skipped_reason"] = (
                            "Hoja de balance: solo se llena en mes 03")
                        continue
                    src_col = dest_col - 2
                    if src_col < 0:
                        continue

                    mm_s, yy_s = _date_parts(d_iso)
                    src = await _resolve_source(mm_s, yy_s)
                    if not src:
                        sheet_report["cols_skipped"].append(
                            f"{letra} (sin archivo fuente {mm_s}-{yy_s})")
                        continue
                    if sname not in src["sheets"]:
                        sheet_report["cols_skipped"].append(
                            f"{letra} (hoja no está en fuente {mm_s}-{yy_s})")
                        continue

                    # Camino rápido: dry_run sin detalle_filas → solo contar
                    if params.dry_run and not params.detalle_filas:
                        sheet_report["cols_written"] += 1
                        report["total_cols_written"] += 1
                        continue

                    # Para escritura real o para detalle_filas se necesitan celdas fuente
                    key = f"{mm_s}-{yy_s}"
                    if key not in src_data_cache:
                        try:
                            src_data_cache[key] = await _read_sheet_cells_retry(
                                src["id"], src["sheets"][sname])
                        except Exception as e:
                            src_data_cache[key] = None
                            report["sheets_failed"].append(
                                {"sheet": sname,
                                 "error": f"fuente {key}: {_handle_error(e)}"})
                    src_cells = src_data_cache[key]
                    if src_cells is None:
                        sheet_report["cols_failed"].append(letra)
                        report["total_cols_failed"] += 1
                        continue

                    # Idempotencia: solo en modo escritura real
                    if not params.dry_run and _col_filled(dest_col):
                        sheet_report["cols_skipped"].append(f"{letra} (ya llenada)")
                        continue

                    write_vals: list[Any] = []
                    comp_filas: list[dict] = []
                    for i, row_t in enumerate(tgt_cells):
                        if _is_formula(row_t, dest_col):
                            write_vals.append(None)
                            continue
                        # Solo escribir en filas que pertenecen al cuadro de datos del
                        # destino. Si ninguna celda antes de src_col tiene valor (número,
                        # string no vacío o fórmula), la fila está fuera de la tabla
                        # (zona de cálculo). Evita escribir en filas 30+ de la fuente que
                        # tienen valores de cálculo pero que no existen en el destino.
                        if i >= 6:
                            row_in_table = any(
                                _is_formula(row_t, ci) or (
                                    isinstance(row_t[ci], dict)
                                    and _cv(row_t[ci]) not in (None, "")
                                )
                                for ci in range(min(src_col, len(row_t)))
                            )
                            if not row_in_table:
                                write_vals.append(None)
                                continue
                        row_s = src_cells[i] if i < len(src_cells) else []
                        sv    = _cv(row_s[src_col]) if src_col < len(row_s) else None
                        nv    = sv if isinstance(sv, (int, float)) else None
                        write_vals.append(nv)
                        if params.detalle_filas and nv is not None:
                            dest_v = _cv(row_t[dest_col] if dest_col < len(row_t) else None)
                            etiq   = _row_label(row_t, src_col)
                            if not isinstance(dest_v, (int, float)):
                                estado = "NO PROCESADO"
                            elif dest_v == nv:
                                estado = "OK"
                            else:
                                estado = "HALLAZGO"
                            comp_filas.append({
                                "fila":     i + 1,
                                "etiqueta": etiq,
                                "destino":  dest_v,
                                "fuente":   nv,
                                "estado":   estado,
                            })

                    if params.detalle_filas:
                        iguales   = sum(1 for f in comp_filas if f["estado"] == "OK")
                        distintos = sum(1 for f in comp_filas if f["estado"] != "OK")
                        sheet_report["comparacion"].append({
                            "col":       letra,
                            "contexto":  d_iso,
                            "iguales":   iguales,
                            "distintos": distintos,
                            "filas":     comp_filas,
                        })

                    if params.dry_run:
                        sheet_report["cols_written"] += 1
                        report["total_cols_written"] += 1
                        continue

                    if not any(v is not None for v in write_vals):
                        continue

                    try:
                        ok = await _write_column(
                            params.spreadsheet_id, sid_t, dest_col, write_vals
                        )
                    except Exception:
                        ok = False
                    if ok:
                        sheet_report["cols_written"] += 1
                        report["total_cols_written"] += 1
                    else:
                        sheet_report["cols_failed"].append(letra)
                        report["total_cols_failed"] += 1

                for k in ("cols_failed", "cols_skipped"):
                    if not sheet_report[k]:
                        del sheet_report[k]
                report["sheets_processed"].append(sheet_report)
                continue

            # ── REGLA 4: bloques dobles (cuadro arriba = actual; cuadro abajo = comparativo)
            # La celda indicadora (split_cell) marca dónde empieza el bloque inferior y
            # la celda de período (period_cell) contiene la fecha del archivo fuente.
            # Se copia: source_rows[0..split_row-1] → dest_rows[split_row..end], omitiendo fórmulas.
            double_cfg = _get_double_block_cfg(sname)
            if double_cfg:
                split_cell, period_cell = double_cfg
                split_row, _           = _parse_cell_ref(split_cell)
                period_row, period_col = _parse_cell_ref(period_cell)

                if split_row < 0 or period_row < 0:
                    report["sheets_skipped"].append(
                        f"{sname} (bloque doble: celda indicadora '{split_cell}' inválida)")
                    continue
                if split_row >= len(tgt_cells):
                    report["sheets_skipped"].append(
                        f"{sname} (bloque doble: split_row {split_row+1} fuera de rango, hoja tiene {len(tgt_cells)} filas)")
                    continue

                period_val = (
                    _cv(tgt_cells[period_row][period_col])
                    if period_row < len(tgt_cells) and period_col < len(tgt_cells[period_row])
                    else None
                )
                period_iso = _parse_fecha(period_val)

                # Fallback: si la celda configurada no tiene fecha (está combinada o
                # tiene texto/número), escanear columnas A-E del bloque inferior buscando
                # la fecha más tardía del año anterior. Funciona en todos los templates
                # donde la fecha está embebida en etiquetas de fila (ej. "al 30 de junio de 2025").
                if not period_iso:
                    for dr in range(split_row, min(split_row + 40, len(tgt_cells))):
                        for ci in range(6):  # columnas A a F
                            cell = tgt_cells[dr][ci] if ci < len(tgt_cells[dr]) else None
                            iso = _parse_fecha(_cv(cell) if isinstance(cell, dict) else None)
                            if iso and iso[:4] == prior_year:
                                if period_iso is None or iso > period_iso:
                                    period_iso = iso

                if not period_iso:
                    report["sheets_skipped"].append(
                        f"{sname} (bloque doble: no se encontró fecha del año {prior_year} "
                        f"en celda {period_cell} ni en primeras filas del bloque inferior)")
                    continue

                mm_s, yy_s = _date_parts(period_iso)
                src4 = await _resolve_source(mm_s, yy_s)
                if not src4:
                    report["sheets_skipped"].append(
                        f"{sname} (bloque doble: sin fuente para {mm_s}-{yy_s})")
                    continue
                if sname not in src4["sheets"]:
                    report["sheets_skipped"].append(
                        f"{sname} (bloque doble: hoja no existe en fuente {mm_s}-{yy_s})")
                    continue

                try:
                    src4_cells = await _read_sheet_cells_retry(
                        src4["id"], src4["sheets"][sname])
                except Exception as exc4:
                    report["sheets_failed"].append(
                        {"sheet": sname,
                         "error": f"bloque doble fuente {mm_s}-{yy_s}: {_handle_error(exc4)}"})
                    continue

                # Idempotencia: si el bloque inferior ya tiene valores numéricos no-fórmula, saltar
                if not params.dry_run:
                    ya_lleno4 = False
                    for dr in range(split_row, len(tgt_cells)):
                        for ci_ch, _ in enumerate(tgt_cells[dr]):
                            if not _is_formula(tgt_cells[dr], ci_ch):
                                v4 = _cv(tgt_cells[dr][ci_ch])
                                if isinstance(v4, (int, float)) and v4 != 0:
                                    ya_lleno4 = True
                                    break
                        if ya_lleno4:
                            break
                    if ya_lleno4:
                        report["sheets_skipped"].append(
                            f"{sname} (bloque doble: bloque inferior ya llenado)")
                        continue

                # Columnas con valores numéricos en el bloque superior de la fuente
                data_cols4: set[int] = set()
                for si4 in range(min(split_row, len(src4_cells))):
                    for ci4, cell4 in enumerate(src4_cells[si4]):
                        v4 = _cv(cell4)
                        if isinstance(v4, (int, float)) and v4 != 0:
                            data_cols4.add(ci4)

                sheet_report4: dict[str, Any] = {
                    "sheet":          sname,
                    "bloque_tipo":    "doble",
                    "periodo_fuente": f"{mm_s}-{yy_s}",
                    "fuente":         src4["name"],
                    "split_row":      split_row + 1,
                    "cols_written":   0,
                    "cols_failed":    [],
                }

                if params.dry_run:
                    sheet_report4["cols_written"] = len(data_cols4)
                    report["total_cols_written"] += len(data_cols4)
                    del sheet_report4["cols_failed"]
                    report["sheets_processed"].append(sheet_report4)
                    continue

                for ci4 in sorted(data_cols4):
                    vals4: list[Any] = []
                    for dr in range(split_row, len(tgt_cells)):
                        src_ri = dr - split_row
                        if _is_formula(tgt_cells[dr], ci4):
                            vals4.append(None)
                            continue
                        row_s4 = src4_cells[src_ri] if src_ri < len(src4_cells) else []
                        sv4 = _cv(row_s4[ci4]) if ci4 < len(row_s4) else None
                        vals4.append(sv4 if isinstance(sv4, (int, float)) else None)

                    if not any(v is not None for v in vals4):
                        continue

                    # Idempotencia: verificar si los valores del bloque inferior ya coinciden
                    dest_vals4: list[Any] = []
                    for dr in range(split_row, len(tgt_cells)):
                        if not _is_formula(tgt_cells[dr], ci4):
                            cell = tgt_cells[dr][ci4] if ci4 < len(tgt_cells[dr]) else None
                            dest_vals4.append(_cv(cell) if isinstance(cell, dict) else None)
                    src_nonnull = [v for v in vals4 if v is not None]
                    dst_nonnull = [v for v in dest_vals4 if isinstance(v, (int, float))]
                    if src_nonnull and src_nonnull == dst_nonnull:
                        sheet_report4.setdefault("cols_skipped", []).append(
                            f"{_col_letter(ci4)} (ya llenada)")
                        continue

                    try:
                        ok4 = await _write_column(
                            params.spreadsheet_id, sid_t, ci4, vals4,
                            start_row=split_row)
                    except Exception:
                        ok4 = False

                    if ok4:
                        sheet_report4["cols_written"] += 1
                        report["total_cols_written"] += 1
                    else:
                        sheet_report4["cols_failed"].append(_col_letter(ci4))
                        report["total_cols_failed"] += 1

                if not sheet_report4["cols_failed"]:
                    del sheet_report4["cols_failed"]
                report["sheets_processed"].append(sheet_report4)
                continue

            # ── REGLA 3: hojas de bloques anuales (ej. 60.- activo fijo) ────
            markers = _year_markers(tgt_cells)
            dest_marker = next(((ri, y) for ri, y in markers
                                if y == prior_year), None)
            if not dest_marker:
                continue  # hoja sin comparativos detectables

            src = await _resolve_source("12", prior_year)
            if not src or sname not in src["sheets"]:
                report["sheets_skipped"].append(
                    f"{sname} (bloque {prior_year}: sin fuente 12-{prior_year})")
                continue
            try:
                src_cells = await _read_sheet_cells_retry(
                    src["id"], src["sheets"][sname])
            except Exception as e:
                report["sheets_failed"].append(
                    {"sheet": sname, "error": f"fuente: {_handle_error(e)}"})
                continue

            src_markers = _year_markers(src_cells)
            src_marker = next(((ri, y) for ri, y in src_markers
                               if y == prior_year), None)
            if not src_marker:
                report["sheets_skipped"].append(
                    f"{sname} (bloque {prior_year} no está en la fuente)")
                continue

            d0, s0 = dest_marker[0], src_marker[0]
            d_next = next((ri for ri, _ in markers if ri > d0), len(tgt_cells))
            s_next = next((ri for ri, _ in src_markers if ri > s0), len(src_cells))
            blk_len = min(d_next - d0, s_next - s0)

            # Columnas del bloque = las que traen datos numéricos en la fuente
            blk_cols: set[int] = set()
            for i in range(blk_len):
                if s0 + i >= len(src_cells):
                    break
                for j, cell in enumerate(src_cells[s0 + i]):
                    v = _cv(cell)
                    if isinstance(v, (int, float)) and v != 0:
                        blk_cols.add(j)

            if not blk_cols:
                report["sheets_skipped"].append(
                    f"{sname} (bloque {prior_year} sin datos en fuente)")
                continue

            sheet_report = {
                "sheet":      sname,
                "bloque_año": prior_year,
                "filas":      f"{d0 + 1}-{d0 + blk_len}",
                "cols_written": 0,
                "cols_failed":  [],
            }

            # Idempotencia: bloque destino ya tiene números (solo celdas
            # sin fórmula, para no confundir totales calculados)
            ya_llenado = False
            for i in range(1, blk_len):
                if d0 + i >= len(tgt_cells):
                    break
                row_d = tgt_cells[d0 + i]
                for j in blk_cols:
                    if j < len(row_d) and not _is_formula(row_d, j):
                        v = _cv(row_d[j])
                        if isinstance(v, (int, float)) and v != 0:
                            ya_llenado = True
                            break
                if ya_llenado:
                    break
            if ya_llenado:
                report["sheets_skipped"].append(
                    f"{sname} (bloque {prior_year} ya llenado)")
                continue

            if params.dry_run:
                sheet_report["cols_written"] = len(blk_cols)
                report["total_cols_written"] += len(blk_cols)
                del sheet_report["cols_failed"]
                report["sheets_processed"].append(sheet_report)
                continue

            for j in sorted(blk_cols):
                vals: list[Any] = []
                for i in range(blk_len):
                    row_d = tgt_cells[d0 + i] if d0 + i < len(tgt_cells) else []
                    if _is_formula(row_d, j):
                        vals.append(None)
                        continue
                    row_s = src_cells[s0 + i] if s0 + i < len(src_cells) else []
                    sv = _cv(row_s[j]) if j < len(row_s) else None
                    vals.append(sv if isinstance(sv, (int, float)) else None)
                if not any(v is not None for v in vals):
                    continue
                try:
                    ok = await _write_column(
                        params.spreadsheet_id, sid_t, j, vals, start_row=d0
                    )
                except Exception:
                    ok = False
                if ok:
                    sheet_report["cols_written"] += 1
                    report["total_cols_written"] += 1
                else:
                    sheet_report["cols_failed"].append(_col_letter(j))
                    report["total_cols_failed"] += 1

            if not sheet_report["cols_failed"]:
                del sheet_report["cols_failed"]
            report["sheets_processed"].append(sheet_report)

        # Aviso si no se pudo hacer nada por falta de fuentes
        if not report["sheets_processed"] and report["total_cols_written"] == 0:
            faltantes = [k for k, v in report["sources"].items() if v is None]
            if faltantes:
                parecidos = [n for n in all_files
                             if _strip_prefix(n).upper().startswith(f"{code.upper()}_")]
                report["warning_fuentes"] = (
                    f"Sin archivo fuente para los períodos {faltantes}. "
                    f"Archivos existentes de {code}: {sorted(parecidos)[:40]}"
                )

        if params.dry_run:
            report["message"] = (
                "MODO DRY-RUN: No se escribió nada. "
                "Llama con dry_run=False para aplicar los cambios."
            )

        return json.dumps(report, indent=2, ensure_ascii=False)
    except Exception as e:
        return _handle_error(e)


# ─── 9. VERIFICAR SUMAS ──────────────────────────────────────────────────────

class VerifySumsInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    spreadsheet_id: str           = Field(..., description="ID del spreadsheet")
    sheet_name:     str           = Field(..., description="Nombre de la hoja a verificar")
    sum_col:        int           = Field(...,  description="Columna que contiene subtotales/totales (base 0)", ge=0)
    detail_cols:    list[int]     = Field(...,  description="Columnas de detalle que deben sumar al total (base 0)")
    tolerance:      float         = Field(default=1.0, description="Diferencia máxima aceptable (default 1 unidad)", ge=0)
    header_rows:    int           = Field(default=5,   description="Filas de encabezado a saltarse", ge=0)


@mcp.tool(
    name="workiva_verify_sums",
    annotations={"readOnlyHint": True, "destructiveHint": False,
                  "idempotentHint": True, "openWorldHint": True}
)
async def workiva_verify_sums(params: VerifySumsInput) -> str:
    """Verifica aritméticamente que los subtotales y totales de una hoja de Workiva cuadren.

    Lee la hoja y para cada fila no vacía, compara el valor de la columna 'sum_col'
    contra la suma de las 'detail_cols'. Reporta PASS / FAIL con la diferencia.

    Args:
        params.spreadsheet_id: ID del spreadsheet
        params.sheet_name:     Nombre de la hoja
        params.sum_col:        Columna del total/subtotal (base 0)
        params.detail_cols:    Columnas de detalle que deben sumar al total
        params.tolerance:      Diferencia absoluta máxima aceptable (default 1)
        params.header_rows:    Filas a ignorar al inicio (default 5)

    Returns:
        JSON con resumen {pass_count, fail_count, failures: [{row, label, expected, actual, diff}]}
    """
    try:
        sheets = await _get_sheets(params.spreadsheet_id)
        sid    = sheets.get(params.sheet_name)
        if not sid:
            return f"Error: Hoja '{params.sheet_name}' no encontrada."

        cells    = await _read_sheet_cells(params.spreadsheet_id, sid)
        pass_cnt = 0
        fail_cnt = 0
        failures: list[dict] = []

        for i, row in enumerate(cells[params.header_rows:], start=params.header_rows):
            total_val = _cv(row[params.sum_col]) if params.sum_col < len(row) else None
            if not isinstance(total_val, (int, float)):
                continue

            detail_sum = 0.0
            for dc in params.detail_cols:
                v = _cv(row[dc]) if dc < len(row) else None
                if isinstance(v, (int, float)):
                    detail_sum += v

            label = str(_cv(row[1]) if len(row) > 1 else f"fila {i+1}") or f"fila {i+1}"
            diff  = abs(total_val - detail_sum)

            if diff <= params.tolerance:
                pass_cnt += 1
            else:
                fail_cnt += 1
                failures.append({
                    "row":      i + 1,
                    "label":    label,
                    "expected": round(detail_sum, 2),
                    "actual":   round(total_val, 2),
                    "diff":     round(diff, 2),
                })

        status = "OK" if fail_cnt == 0 else "DIFERENCIAS ENCONTRADAS"
        return json.dumps({
            "spreadsheet_id": params.spreadsheet_id,
            "sheet_name":     params.sheet_name,
            "status":         status,
            "pass_count":     pass_cnt,
            "fail_count":     fail_cnt,
            "tolerance":      params.tolerance,
            "failures":       failures,
        }, indent=2, ensure_ascii=False)
    except Exception as e:
        return _handle_error(e)


# ─── 10. CRUZAR NOTAS CON ESTADO PRIMARIO ────────────────────────────────────

class CheckNoteConsistencyInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    spreadsheet_id:   str = Field(..., description="ID del spreadsheet que contiene ambas hojas")
    primary_sheet:    str = Field(..., description="Nombre de la hoja de estado primario (ej: 'A.- Activos')")
    note_sheet:       str = Field(..., description="Nombre de la hoja de la nota a cruzar")
    primary_col:      int = Field(..., description="Columna del valor en el estado primario (base 0)", ge=0)
    note_col:         int = Field(..., description="Columna del valor en la nota (base 0)", ge=0)
    primary_row:      int = Field(..., description="Fila del valor en el estado primario (base 0)", ge=0)
    note_total_row:   int = Field(..., description="Fila del total en la nota (base 0)", ge=0)
    tolerance:        float = Field(default=1.0, description="Diferencia máxima aceptable", ge=0)
    label:            str = Field(default="Cruce", description="Descripción del cruce (para el reporte)")


@mcp.tool(
    name="workiva_check_note_consistency",
    annotations={"readOnlyHint": True, "destructiveHint": False,
                  "idempotentHint": True, "openWorldHint": True}
)
async def workiva_check_note_consistency(params: CheckNoteConsistencyInput) -> str:
    """Cruza un valor entre un estado primario y una nota para verificar consistencia.

    Compara el valor en una celda del estado primario con el total de la nota.
    Reporta PASS si la diferencia está dentro de la tolerancia, FAIL en caso contrario.

    Args:
        params.spreadsheet_id: ID del spreadsheet (puede contener ambas hojas)
        params.primary_sheet:  Nombre de la hoja del estado primario
        params.note_sheet:     Nombre de la hoja de la nota
        params.primary_col:    Columna del valor en el estado primario (base 0)
        params.note_col:       Columna del total en la nota (base 0)
        params.primary_row:    Fila del valor en el estado primario (base 0)
        params.note_total_row: Fila del total en la nota (base 0)
        params.tolerance:      Diferencia máxima aceptable (default 1)
        params.label:          Descripción del cruce (para el reporte)

    Returns:
        JSON con {status, label, primary_value, note_value, diff, pass}
    """
    try:
        sheets = await _get_sheets(params.spreadsheet_id)

        async def _get_val(sheet_name: str, row: int, col: int) -> float | None:
            sid = sheets.get(sheet_name)
            if not sid:
                return None
            cells = await _read_sheet_cells(params.spreadsheet_id, sid)
            if row >= len(cells):
                return None
            row_data = cells[row]
            v = _cv(row_data[col]) if col < len(row_data) else None
            return float(v) if isinstance(v, (int, float)) else None

        primary_val = await _get_val(params.primary_sheet, params.primary_row, params.primary_col)
        note_val    = await _get_val(params.note_sheet,    params.note_total_row, params.note_col)

        if primary_val is None:
            return f"Error: No se pudo leer el valor en {params.primary_sheet} fila {params.primary_row+1} col {_col_letter(params.primary_col)}"
        if note_val is None:
            return f"Error: No se pudo leer el valor en {params.note_sheet} fila {params.note_total_row+1} col {_col_letter(params.note_col)}"

        diff   = abs(primary_val - note_val)
        passed = diff <= params.tolerance

        return json.dumps({
            "label":         params.label,
            "status":        "PASS" if passed else "FAIL",
            "primary_sheet": params.primary_sheet,
            "note_sheet":    params.note_sheet,
            "primary_value": round(primary_val, 2),
            "note_value":    round(note_val, 2),
            "diff":          round(diff, 2),
            "tolerance":     params.tolerance,
        }, indent=2, ensure_ascii=False)
    except Exception as e:
        return _handle_error(e)


# ══════════════════════════════════════════════════════════════════════════════
# ENTRY POINT
# ══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    if not CLIENT_ID or not CLIENT_SECRET:
        import sys
        print(
            "ERROR: Falta WORKIVA_CLIENT_ID o WORKIVA_CLIENT_SECRET en el archivo .env",
            file=sys.stderr,
        )
        sys.exit(1)
    mcp.run()  # stdio transport por defecto
