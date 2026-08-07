#!/usr/bin/env python3
"""
workiva_mcp_v2.py  ←  ESPEJO con soporte EERR para Q2/Q3/Q4
=============================================================
Igual que workiva_mcp.py con estos cambios en workiva_fill_comparatives:

  1. Busca un segundo archivo fuente para EERR (prior_eerr_end).
  2. Detecta columnas comparativas de BALANCE (prior_end) Y de EERR
     (prior_eerr_end) en los encabezados de cada hoja.
  3. La restricción "solo mes 03 escribe" se aplica únicamente a las
     columnas de BALANCE; las columnas EERR se escriben en cualquier mes.

Todo lo demás es idéntico al original.
"""

from __future__ import annotations

import asyncio
import csv
import io
import json
import os
import re
import time
import unicodedata
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

VERIFY_SSL = False
warnings.filterwarnings("ignore")


# ══════════════════════════════════════════════════════════════════════════════
# CLIENTE COMPARTIDO CON REFRESH DE TOKEN
# ══════════════════════════════════════════════════════════════════════════════

class WorkivaClient:
    def __init__(self) -> None:
        self._token: str = ""
        self._token_ts: float = 0.0
        self._client: httpx.AsyncClient | None = None

    async def _ensure_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(verify=VERIFY_SSL, timeout=120.0)
        return self._client

    async def _get_token(self) -> str:
        if time.time() - self._token_ts < 540 and self._token:
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
        last: httpx.Response | None = None
        for attempt in range(3):
            try:
                r = await client.get(url, headers=await self._headers(), **kwargs)
            except httpx.TransportError:
                if attempt == 2:
                    raise
                await asyncio.sleep(1 + 2 * attempt)
                continue
            transient = (
                r.status_code in (429, 500, 502, 503, 504)
                or (r.status_code == 200 and not r.content)
            )
            if not transient:
                return r
            last = r
            if attempt < 2:
                retry_after = r.headers.get("Retry-After", "")
                delay = float(retry_after) if retry_after.isdigit() else 1 + 2 * attempt
                await asyncio.sleep(delay)
        return last

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

def _col_letter(idx: int) -> str:
    if idx < 26:
        return chr(65 + idx)
    return chr(64 + idx // 26) + chr(65 + idx % 26)


def _cv(cell: Any) -> Any:
    if isinstance(cell, dict):
        return cell.get("calculatedValue")
    return None


def _is_formula(row: list, col: int) -> bool:
    if col >= len(row):
        return False
    c = row[col]
    return str(c.get("value", "") if isinstance(c, dict) else "").startswith("=")


def _etiqueta_fila(row_e: list) -> str:
    """Rótulo descriptivo de la fila (columna B, con fallback a A y C)."""
    for j in (1, 0, 2):
        if j < len(row_e):
            t = _cv(row_e[j])
            if isinstance(t, str) and t.strip():
                return t.strip()
    return ""


def _norm_lbl(s: str) -> str:
    s = unicodedata.normalize("NFKD", s or "")
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    return re.sub(r"\s+", " ", s.strip().lower().rstrip(".:; "))


async def _get_sheets(ss_id: str) -> dict[str, str]:
    result: dict[str, str] = {}
    url = f"{PLATFORM_URL}/spreadsheets/{ss_id}/sheets"
    while url:
        r    = await _wk.get(url)
        data = r.json()
        for s in data.get("data", []):
            result[s["name"]] = s["id"]
        url = data.get("@nextLink")
    return result


async def _read_sheet_cells(ss_id: str, sheet_id: str) -> list[list]:
    url = (
        f"{PLATFORM_URL}/spreadsheets/{ss_id}/sheets/{sheet_id}"
        "/sheetdata?$fields=cells.calculatedValue,cells.value&$maxcellsperpage=50000"
    )
    r = await _wk.get(url)
    if r.status_code != 200:
        return []
    return r.json().get("data", {}).get("cells", [])


async def _poll_operation(location: str, max_attempts: int = 40) -> bool:
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


async def _verify_write(ss_id: str, sid: str, col_idx: int, start_row: int,
                         values: list, cl: str) -> list[str]:
    """Relee la hoja completa (mismo camino ya probado que usa el resto de
    la app para leer celdas: _read_sheet_cells + calculatedValue) y devuelve
    las celdas cuyo valor NO coincide con lo que se intentó escribir
    (indicio de celda bloqueada/protegida que Workiva ignoró en silencio
    al completar el PUT).

    Reintenta con espera porque Workiva puede tardar en propagar la
    escritura a la lectura (consistencia eventual).
    """
    mismatches: list[str] = []
    for intento in range(3):
        if intento > 0:
            await asyncio.sleep(2 * intento)
        try:
            cells = await _read_sheet_cells(ss_id, sid)
        except Exception:
            return []

        mismatches = []
        for i, want in enumerate(values):
            if want is None:
                continue
            row_i = start_row + i
            row   = cells[row_i] if row_i < len(cells) else []
            got   = _cv(row[col_idx]) if col_idx < len(row) else None
            got_num = got if isinstance(got, (int, float)) else None
            if got_num is None or abs(got_num - float(want)) > 0.5:
                mismatches.append(f"{cl}{start_row + i + 1}")

        if not mismatches:
            return []
    return mismatches


async def _write_column(ss_id: str, sid: str, col_idx: int,
                         values: list, start_row: int = 0) -> tuple[bool, str | None]:
    """Escribe una columna. Retorna (ok, motivo_error) — motivo_error es None si ok."""
    cl = _col_letter(col_idx)
    r1 = start_row + 1
    r2 = r1 + len(values) - 1
    rng = f"{cl}{r1}:{cl}{r2}"
    rp = await _wk.put(
        f"{PLATFORM_URL}/spreadsheets/{ss_id}/sheets/{sid}/values/{rng}",
        json={"values": [[v] for v in values]},
    )
    if rp.status_code == 202:
        ok = await _poll_operation(rp.headers.get("Location", ""))
        if not ok:
            return False, f"La operación de escritura en {rng} falló (timeout u operación cancelada)."

        # Workiva puede responder "completed" e ignorar en silencio las
        # celdas bloqueadas/protegidas dentro del rango — se verifica releyendo.
        mismatches = await _verify_write(ss_id, sid, col_idx, start_row, values, cl)
        if mismatches:
            motivo = (
                f"Celda(s) {', '.join(mismatches[:10])} no se actualizaron tras escribir "
                f"(probablemente BLOQUEADA(S)/PROTEGIDA(S) en Workiva)"
            )
            return False, motivo
        return True, None

    try:
        body = rp.json()
        msg  = body.get("message") or body.get("error") or str(body)
    except Exception:
        msg = rp.text[:300]

    if rp.status_code in (400, 403, 409, 422) and re.search(r'lock|protect|bloque', msg, re.I):
        motivo = f"Celda(s) {rng} BLOQUEADA(S)/PROTEGIDA(S) en Workiva: {msg[:200]}"
    else:
        motivo = f"Error HTTP {rp.status_code} al escribir {rng}: {msg[:200]}"
    return False, motivo


async def _load_all_files() -> dict[str, str]:
    result: dict[str, str] = {}
    url = f"{PLATFORM_URL}/files?workspaceId={WORKSPACE_ID}&limit=100"
    while url:
        r    = await _wk.get(url)
        data = r.json()
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


mcp = FastMCP("workiva_mcp_v2", lifespan=lifespan)


# ─── 1. LISTAR ARCHIVOS ──────────────────────────────────────────────────────

class ListFilesInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    pattern:  Optional[str] = Field(default=None)
    limit:    int            = Field(default=50, ge=1, le=500)
    offset:   int            = Field(default=0, ge=0)


@mcp.tool(name="workiva_list_files",
          annotations={"readOnlyHint": True, "destructiveHint": False,
                       "idempotentHint": True, "openWorldHint": True})
async def workiva_list_files(params: ListFilesInput) -> str:
    """Lista archivos del workspace de Workiva."""
    try:
        all_files = await _load_all_files()
        items = list(all_files.items())
        if params.pattern:
            rx    = re.compile(params.pattern, re.IGNORECASE)
            items = [(n, i) for n, i in items if rx.search(n)]
        total    = len(items)
        page     = items[params.offset: params.offset + params.limit]
        has_more = total > params.offset + len(page)
        return json.dumps({
            "total": total, "count": len(page), "offset": params.offset,
            "has_more": has_more,
            "next_offset": params.offset + len(page) if has_more else None,
            "files": [{"name": n, "id": i} for n, i in page],
        }, indent=2, ensure_ascii=False)
    except Exception as e:
        return _handle_error(e)


# ─── 2. LISTAR HOJAS ─────────────────────────────────────────────────────────

class GetSheetsInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    spreadsheet_id: str = Field(...)


@mcp.tool(name="workiva_get_sheets",
          annotations={"readOnlyHint": True, "destructiveHint": False,
                       "idempotentHint": True, "openWorldHint": True})
async def workiva_get_sheets(params: GetSheetsInput) -> str:
    """Lista todas las hojas de un spreadsheet."""
    try:
        sheets = await _get_sheets(params.spreadsheet_id)
        return json.dumps({
            "spreadsheet_id": params.spreadsheet_id,
            "count": len(sheets),
            "sheets": [{"name": n, "id": i} for n, i in sheets.items()],
        }, indent=2, ensure_ascii=False)
    except Exception as e:
        return _handle_error(e)


# ─── 3. LEER HOJA ─────────────────────────────────────────────────────────────

class ReadSheetInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    spreadsheet_id: str      = Field(...)
    sheet_name:     str      = Field(...)
    max_rows:       int      = Field(default=200, ge=1, le=2000)
    skip_empty:     bool     = Field(default=True)
    col_start:      int      = Field(default=0, ge=0)
    col_end:        Optional[int] = Field(default=None)


@mcp.tool(name="workiva_read_sheet",
          annotations={"readOnlyHint": True, "destructiveHint": False,
                       "idempotentHint": True, "openWorldHint": True})
async def workiva_read_sheet(params: ReadSheetInput) -> str:
    """Lee el contenido de una hoja de Workiva."""
    try:
        sheets = await _get_sheets(params.spreadsheet_id)
        sid    = sheets.get(params.sheet_name)
        if not sid:
            available = ", ".join(sheets.keys())
            return f"Error: Hoja '{params.sheet_name}' no encontrada. Disponibles: {available}"
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
            "sheet_name": params.sheet_name,
            "total_rows": len(cells),
            "returned_rows": len(rows),
            "col_start": params.col_start,
            "rows": rows,
        }, indent=2, ensure_ascii=False)
    except Exception as e:
        return _handle_error(e)


# ─── 4. ESCRIBIR COLUMNA ─────────────────────────────────────────────────────

class WriteColumnInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    spreadsheet_id: str       = Field(...)
    sheet_name:     str       = Field(...)
    col_index:      int       = Field(..., ge=0)
    values:         list[Any] = Field(...)
    start_row:      int       = Field(default=0, ge=0)


@mcp.tool(name="workiva_write_column",
          annotations={"readOnlyHint": False, "destructiveHint": False,
                       "idempotentHint": True, "openWorldHint": True})
async def workiva_write_column(params: WriteColumnInput) -> str:
    """Escribe una columna de valores en una hoja de Workiva."""
    try:
        sheets = await _get_sheets(params.spreadsheet_id)
        sid    = sheets.get(params.sheet_name)
        if not sid:
            return f"Error: Hoja '{params.sheet_name}' no encontrada."
        ok, motivo = await _write_column(
            params.spreadsheet_id, sid,
            params.col_index, params.values, params.start_row
        )
        n_written = sum(1 for v in params.values if v is not None)
        return json.dumps({
            "success": ok, "sheet_name": params.sheet_name,
            "col_letter": _col_letter(params.col_index),
            "start_row": params.start_row + 1,
            "end_row":   params.start_row + len(params.values),
            "n_values":  n_written,
            "error":     motivo,
        }, indent=2, ensure_ascii=False)
    except Exception as e:
        return _handle_error(e)


# ─── 5. LISTAR TABLAS WDATA ──────────────────────────────────────────────────

class ListTablesInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    pattern: Optional[str] = Field(default=None)
    limit:   int            = Field(default=50, ge=1, le=200)
    offset:  int            = Field(default=0, ge=0)


@mcp.tool(name="workiva_list_tables",
          annotations={"readOnlyHint": True, "destructiveHint": False,
                       "idempotentHint": True, "openWorldHint": True})
async def workiva_list_tables(params: ListTablesInput) -> str:
    """Lista tablas WData."""
    try:
        url   = f"{WDATA_URL}/table?workspaceId={WORKSPACE_ID}"
        r     = await _wk.get(url)
        items = r.json().get("data", [])
        if params.pattern:
            rx    = re.compile(params.pattern, re.IGNORECASE)
            items = [t for t in items if rx.search(t.get("name", ""))]
        total = len(items)
        page  = items[params.offset: params.offset + params.limit]
        return json.dumps({
            "total": total, "count": len(page), "offset": params.offset,
            "has_more": total > params.offset + len(page),
            "tables": [{"id": t.get("id"), "name": t.get("name"),
                        "desc": t.get("description", "")} for t in page],
        }, indent=2, ensure_ascii=False)
    except Exception as e:
        return _handle_error(e)


# ─── 6. LISTAR QUERIES WDATA ─────────────────────────────────────────────────

class ListQueriesInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    pattern: Optional[str] = Field(default=None)
    limit:   int            = Field(default=50, ge=1, le=200)
    offset:  int            = Field(default=0, ge=0)


@mcp.tool(name="workiva_list_queries",
          annotations={"readOnlyHint": True, "destructiveHint": False,
                       "idempotentHint": True, "openWorldHint": True})
async def workiva_list_queries(params: ListQueriesInput) -> str:
    """Lista queries WData."""
    try:
        url   = f"{WDATA_URL}/query?workspaceId={WORKSPACE_ID}"
        r     = await _wk.get(url)
        items = r.json().get("data", [])
        if params.pattern:
            rx    = re.compile(params.pattern, re.IGNORECASE)
            items = [q for q in items if rx.search(q.get("name", ""))]
        total = len(items)
        page  = items[params.offset: params.offset + params.limit]
        return json.dumps({
            "total": total, "count": len(page), "offset": params.offset,
            "has_more": total > params.offset + len(page),
            "queries": [{"id": q.get("id"), "name": q.get("name"),
                         "statement": (q.get("statement") or "")[:200]} for q in page],
        }, indent=2, ensure_ascii=False)
    except Exception as e:
        return _handle_error(e)


# ─── 7. EJECUTAR QUERY WDATA ─────────────────────────────────────────────────

class RunQueryInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    query_id:   str                       = Field(...)
    parameters: Optional[dict[str, str]]  = Field(default=None)
    max_rows:   int                       = Field(default=500, ge=1, le=5000)


@mcp.tool(name="workiva_run_query",
          annotations={"readOnlyHint": True, "destructiveHint": False,
                       "idempotentHint": False, "openWorldHint": True})
async def workiva_run_query(params: RunQueryInput) -> str:
    """Ejecuta una query WData y retorna resultados."""
    try:
        body: dict[str, Any] = {}
        if params.parameters:
            body["parameters"] = [{"name": k, "value": v}
                                   for k, v in params.parameters.items()]
        r = await _wk.post(f"{WDATA_URL}/query/{params.query_id}/result",
                           json=body or None)
        if r.status_code not in (200, 201, 202):
            return f"Error al lanzar query: HTTP {r.status_code} — {r.text[:200]}"
        result_id = r.json().get("data", {}).get("id") or r.json().get("id")
        if not result_id:
            return "Error: No se obtuvo ID de resultado."
        for _ in range(60):
            await asyncio.sleep(3)
            poll   = await _wk.get(f"{WDATA_URL}/query/{params.query_id}/result/{result_id}")
            status = poll.json().get("data", {}).get("status", "")
            if status == "COMPLETE":
                break
            if status == "ERROR":
                return f"Error en la query: {poll.json().get('data', {}).get('error', '')}"
        dl = await _wk.get(
            f"{WDATA_URL}/query/{params.query_id}/result/{result_id}/download")
        if dl.status_code != 200:
            return f"Error al descargar resultado: HTTP {dl.status_code}"
        reader  = csv.DictReader(io.StringIO(dl.text))
        columns = reader.fieldnames or []
        rows    = [list(row.values()) for row in reader]
        truncated = len(rows) > params.max_rows
        rows      = rows[: params.max_rows]
        return json.dumps({
            "query_id": params.query_id, "result_id": result_id,
            "columns": list(columns), "total_rows": len(rows),
            "truncated": truncated, "rows": rows,
        }, indent=2, ensure_ascii=False)
    except Exception as e:
        return _handle_error(e)


# ─── 8. LLENAR COMPARATIVOS (V2 — con soporte EERR) ──────────────────────────

class FillComparativesInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    spreadsheet_id:          str       = Field(...)
    dry_run:                 bool      = Field(default=True)
    sheet_offset:            int       = Field(default=0, ge=0)
    max_sheets:              int       = Field(default=20, ge=1, le=100)
    exclude_sheets:          list[str] = Field(default_factory=list)
    include_sheets:          list[str] = Field(default_factory=list)
    apply_default_excludes:  bool      = Field(default=True)
    max_ejemplos:            int       = Field(default=3, ge=1, le=1000)
    detalle_filas:           bool      = Field(default=False)


@mcp.tool(
    name="workiva_fill_comparatives",
    annotations={"readOnlyHint": False, "destructiveHint": False,
                 "idempotentHint": True, "openWorldHint": True}
)
async def workiva_fill_comparatives(params: FillComparativesInput) -> str:
    """
    Llena columnas comparativas de un archivo Base Notas.

    CAMBIOS vs versión original:
    - Detecta y procesa columnas EERR (prior_eerr_end) además de balance (prior_end).
    - La restricción de mes 03 aplica solo a columnas de BALANCE; las columnas
      EERR se escriben en cualquier mes.
    - Reporta source_eerr además de source_balance.
    """
    SKIP_SHEETS = {
        "CP", "Bases", "Query BPC", "Query HANA AF", "Reporte en $",
        "Query - HANA - Deudores", "A.- Activos PPT",
        "B.- Patrimonio y Pasivos PPT", "C.- Estado de resultado por función PPT",
        "E1 Res Acumulado", "F1 Cuadraje Hoja A.- Saldo Inicial de Caja",
        "26.-",  # Transacciones con relacionadas — estructura especial, llenado manual
    }
    AUX_SKIP_SHEETS = {
        "Query HANA", "Reporte consolidado en $", "Plantilla consolidación",
        "VP", "Sociedades", "Participación accionaria", "Conversiones monedas",
        "Traducción Notas", "Relacionadas", "detalle efe tx GN-GL",
    }
    SOCIEDAD_RE = re.compile(r"(CGEM|Edelmag|Edelamg)\s*$", re.IGNORECASE)

    try:
        # 1. Leer hojas del destino
        tgt_sheets = await _get_sheets(params.spreadsheet_id)
        if "Bases" not in tgt_sheets:
            return "Error: El archivo no tiene hoja 'Bases'."

        # 2. Leer hoja Bases
        bases_cells = await _read_sheet_cells(params.spreadsheet_id, tgt_sheets["Bases"])
        bases: dict[str, str] = {}
        label_map = {
            "estados financieros":            ("current_end",         "prior_end"),
            "estado de resultados - inicial": ("eerr_start",          "prior_eerr_start"),
            "estado de resultados - final":   ("eerr_end",            "prior_eerr_end"),
            "estado de resultados - quarters":("quarter_start",       "prior_quarter_start"),
            "estados financieros anteriores": ("prev_period_end",     "prior_prev_period_end"),
        }
        for row in bases_cells:
            label = str(_cv(row[1]) or "").strip().lower() if len(row) > 1 else ""
            keys  = label_map.get(label)
            if not keys:
                continue
            for col_idx, key in [(3, keys[0]), (5, keys[1])]:
                cv = _cv(row[col_idx]) if col_idx < len(row) else None
                if cv:
                    bases[key] = str(cv)

        curr_end  = bases.get("current_end", "?")
        prior_end = bases.get("prior_end", "?")

        report: dict[str, Any] = {
            "spreadsheet_id":   params.spreadsheet_id,
            "dry_run":          params.dry_run,
            "current_end":      curr_end,
            "prior_end":        prior_end,
            "bases":            bases,
            "sheets_processed": [],
            "sheets_skipped":   [],
            "sheets_failed":    [],
            "total_cols_written": 0,
            "total_cols_failed":  0,
        }

        # 3. Buscar archivos fuente
        all_files  = await _load_all_files()
        id_to_name = {v: k for k, v in all_files.items()}
        target_name = id_to_name.get(params.spreadsheet_id, "")

        m = re.match(r"(\((?:CHN|LC)\)\s*)?(E\d+)_(IND|CONSO)_(\d{2})[-_](\d{4})_(.*)",
                     target_name)
        if not m:
            report["warning"] = (
                f"Nombre '{target_name}' no sigue el patrón esperado."
            )
            return json.dumps(report, indent=2, ensure_ascii=False)

        prefix, code, tipo, mm, yyyy, suffix = m.groups()
        prefix = prefix or ""

        def _date_parts(d: str) -> tuple[str, str]:
            parts = str(d).split("-")
            return (parts[1], parts[0]) if len(parts) >= 2 else ("", "")

        # Índice de all_files normalizado (espacios múltiples → uno)
        _all_files_norm: dict[str, str] = {
            re.sub(r"\s+", " ", k): v for k, v in all_files.items()
        }

        def _find_file(name: str) -> str | None:
            """Busca en all_files normalizando espacios múltiples."""
            norm = re.sub(r"\s+", " ", name)
            return _all_files_norm.get(norm)

        # Fuente BALANCE (prior_end = dic año anterior)
        src_balance_id: str | None = None
        if bases.get("prior_end"):
            mm_b, yy_b = _date_parts(bases["prior_end"])
            for sep in ["-", "_"]:
                name = f"{prefix}{code}_{tipo}_{mm_b}{sep}{yy_b}_{suffix}"
                fid  = _find_file(name)
                if fid:
                    src_balance_id = fid
                    report["source_balance"] = name
                    break

        if not src_balance_id:
            report["warning"] = "No se encontró el archivo fuente de balance comparativo."
            return json.dumps(report, indent=2, ensure_ascii=False)

        # Fuente EERR/QUARTER (prior_eerr_end = mismo período año anterior, ej. 09-2025)
        src_eerr_id: str | None = None
        if bases.get("prior_eerr_end"):
            mm_e, yy_e = _date_parts(bases["prior_eerr_end"])
            for sep in ["-", "_"]:
                name = f"{prefix}{code}_{tipo}_{mm_e}{sep}{yy_e}_{suffix}"
                fid  = _find_file(name)
                if fid:
                    src_eerr_id = fid
                    report["source_eerr"] = name
                    break
        if not src_eerr_id:
            report["source_eerr"] = "No encontrado"

        # Fuente PERÍODO ANTERIOR comparativo (prior_prev_period_end = ej. 06-2025 para Q3)
        src_prev_id: str | None = None
        if bases.get("prior_prev_period_end"):
            mm_p, yy_p = _date_parts(bases["prior_prev_period_end"])
            for sep in ["-", "_"]:
                name = f"{prefix}{code}_{tipo}_{mm_p}{sep}{yy_p}_{suffix}"
                fid  = _find_file(name)
                if fid:
                    src_prev_id = fid
                    report["source_prev_period"] = name
                    break
        if not src_prev_id:
            report["source_prev_period"] = "No encontrado"

        # Fuente PERÍODO ANTERIOR actual (prev_period_end = ej. 06-2026 para Q3)
        src_curr_prev_id: str | None = None
        if bases.get("prev_period_end"):
            mm_cp, yy_cp = _date_parts(bases["prev_period_end"])
            for sep in ["-", "_"]:
                name = f"{prefix}{code}_{tipo}_{mm_cp}{sep}{yy_cp}_{suffix}"
                fid  = _find_file(name)
                if fid:
                    src_curr_prev_id = fid
                    report["source_curr_prev"] = name
                    break
        if not src_curr_prev_id:
            report["source_curr_prev"] = "No encontrado"

        src_sheets_bal       = await _get_sheets(src_balance_id)
        src_sheets_eerr      = await _get_sheets(src_eerr_id)       if src_eerr_id       else {}
        src_sheets_prev      = await _get_sheets(src_prev_id)       if src_prev_id       else {}
        src_sheets_curr_prev = await _get_sheets(src_curr_prev_id)  if src_curr_prev_id  else {}

        # 4. Candidatas
        extra_excludes  = set(params.exclude_sheets)
        include_lower   = [s.lower() for s in params.include_sheets] if params.include_sheets else None
        candidates: list[str] = []
        skipped_sociedad = 0
        for sname in tgt_sheets:
            if include_lower is not None and not any(kw in sname.lower() for kw in include_lower):
                continue
            if sname in SKIP_SHEETS or any(sname.startswith(p) for p in SKIP_SHEETS) or sname in extra_excludes:
                if params.sheet_offset == 0:
                    report["sheets_skipped"].append(sname)
            elif params.apply_default_excludes and sname in AUX_SKIP_SHEETS:
                if params.sheet_offset == 0:
                    report["sheets_skipped"].append(f"{sname} (auxiliar)")
            elif params.apply_default_excludes and SOCIEDAD_RE.search(sname):
                skipped_sociedad += 1
            elif sname not in src_sheets_bal and sname not in src_sheets_eerr and sname not in src_sheets_prev and sname not in src_sheets_curr_prev:
                if params.sheet_offset == 0:
                    report["sheets_skipped"].append(f"{sname} (no en fuente)")
            else:
                candidates.append(sname)
        if params.apply_default_excludes:
            report["skipped_desglose_sociedad"] = skipped_sociedad

        batch      = candidates[params.sheet_offset: params.sheet_offset + params.max_sheets]
        next_offset = params.sheet_offset + len(batch)
        report["total_candidate_sheets"] = len(candidates)
        report["sheet_offset"]           = params.sheet_offset
        report["batch_size"]             = len(batch)
        report["has_more"]               = next_offset < len(candidates)
        if report["has_more"]:
            report["next_offset"] = next_offset

        # 5. Leer celdas del lote en paralelo
        sem = asyncio.Semaphore(6)

        async def _read_lim(ss_id: str, sid: str) -> list[list]:
            async with sem:
                return await _read_sheet_cells(ss_id, sid)

        tgt_cells_by_name = dict(zip(
            batch,
            await asyncio.gather(
                *(_read_lim(params.spreadsheet_id, tgt_sheets[s]) for s in batch)
            ),
        ))

        # 6. Detectar columnas comparativas por fecha en encabezado.
        #    Tipos y keywords de detección (en orden de prioridad para evitar ambigüedades):
        #      "quarter"    → prior_quarter_start  (ej. 2025-07-01, única para el quarter)
        #      "eerr"       → prior_eerr_end       (ej. 2025-09-30, acumulado anual)
        #      "prev_period"→ prior_prev_period_end (ej. 2025-06-30, semestre anterior)
        #      "bal"        → prior_end            (ej. 2025-12-31, balance)
        #
        #    Para encontrar la columna fuente se busca en el archivo fuente la columna
        #    que contenga la keyword característica de cada tipo (date-driven, sin offset fijo).
        #    La keyword de búsqueda en el fuente:
        #      "quarter"    → prior_quarter_start  (col del quarter en fuente 09-aaaa)
        #      "eerr"       → prior_eerr_start     (inicio EERR, distingue de quarter)
        #      "prev_period"→ prior_prev_period_end (col actual en fuente 06-aaaa)
        #      "bal"        → prior_end            (col actual en fuente 12-aaaa)

        kw_bal       = str(bases.get("prior_end",             "")).lower()
        kw_eerr      = str(bases.get("prior_eerr_end",        "")).lower()
        kw_quarter   = str(bases.get("prior_quarter_start",   "")).lower()
        kw_prev      = str(bases.get("prior_prev_period_end", "")).lower()
        kw_curr_prev = str(bases.get("prev_period_end",       "")).lower()
        # Para buscar en fuente: usar start del EERR (distingue EERR vs quarter)
        kw_eerr_src = str(bases.get("prior_eerr_start", "")).lower() or kw_eerr

        def _year_start(date_str: str) -> str:
            """'2026-06-30' → '2026-01-01'  (inicio de año para filtrar columna YTD)"""
            return (date_str[:4] + "-01-01") if date_str and len(date_str) >= 4 else date_str

        # Para curr_prev y prev_period en la FUENTE, buscar por el inicio de año ('YYYY-01-01')
        # en lugar del fin del período ('YYYY-06-30'). Así se distingue la columna acumulada YTD
        # ("01-01-2026/30-06-2026") de la trimestral ("01-04-2026/30-06-2026"), que en el
        # archivo fuente ambas terminan en la misma fecha pero solo la YTD contiene '01-01'.
        kw_curr_prev_src = _year_start(kw_curr_prev)
        kw_prev_src      = _year_start(kw_prev)

        # Mapeo tipo → (keyword detección en destino, archivo fuente, keyword búsqueda en fuente)
        # Orden de prioridad: quarter primero (más específico), luego eerr, prev_period, bal
        TYPE_MAP = [
            ("quarter",     kw_quarter,   src_eerr_id,       src_sheets_eerr,      kw_quarter),
            ("eerr",        kw_eerr,      src_eerr_id,       src_sheets_eerr,      kw_eerr_src),
            ("curr_prev",   kw_curr_prev, src_curr_prev_id,  src_sheets_curr_prev, kw_curr_prev_src),
            # bal antes que prev_period: ambos usan "2025-12-31" como keyword;
            # si prev_period va primero, reclama la columna Dic y bal nunca se procesa.
            # Con bal primero, toma la columna y lee del período anterior (Q1 para Q2, etc.).
            ("bal",         kw_bal,
             src_curr_prev_id  or src_balance_id,
             src_sheets_curr_prev if src_curr_prev_id else src_sheets_bal,
             kw_bal),
            ("prev_period", kw_prev,      src_prev_id,       src_sheets_prev,      kw_prev_src),
        ]

        def _find_src_col(src_cells: list[list], kw: str) -> int | None:
            """Busca en las primeras 8 filas la primera columna cuyo header contenga kw."""
            if not kw:
                return None
            for row in src_cells[:8]:
                for j, cell in enumerate(row):
                    if not isinstance(cell, dict):
                        continue
                    for val_key in ("calculatedValue", "value"):
                        v = str(cell.get(val_key, "") or "").lower()
                        if kw in v:
                            return j
            return None

        def _find_src_col_nth(src_cells: list[list], kw: str, n: int) -> int | None:
            """Busca la N-ésima columna (0-based) cuyo header contenga kw en las primeras 8 filas."""
            if not kw:
                return None
            seen_cols: list[int] = []
            seen_set: set[int] = set()
            for row in src_cells[:8]:
                for j, cell in enumerate(row):
                    if j in seen_set or not isinstance(cell, dict):
                        continue
                    for val_key in ("calculatedValue", "value"):
                        v = str(cell.get(val_key, "") or "").lower()
                        if kw in v:
                            seen_cols.append(j)
                            seen_set.add(j)
                            break
            return seen_cols[n] if n < len(seen_cols) else (seen_cols[-1] if seen_cols else None)

        def _find_segment_label(all_rows: list, col_j: int, header_row: int) -> str:
            """
            Detecta el nombre de segmento que "posee" la columna col_j.
            Busca en las filas anteriores al header de fecha (header_row)
            escaneando hacia la izquierda desde col_j hasta encontrar una
            celda con texto no-vacío que no sea una fecha ni M$.
            """
            _skip = {"m$", "%", ""}
            _date_re = re.compile(r"\d{4}-\d{2}-\d{2}|\d{2}-\d{4}|\d{4}/\d{2}/\d{2}")
            for ri in range(header_row - 1, -1, -1):
                row = all_rows[ri]
                for jj in range(col_j, -1, -1):
                    if jj >= len(row):
                        continue
                    cell = row[jj]
                    if not isinstance(cell, dict):
                        continue
                    for vk in ("calculatedValue", "value"):
                        raw = str(cell.get(vk, "") or "").strip()
                        lo  = raw.lower()
                        if lo in _skip or _date_re.search(lo):
                            continue
                        if len(raw) >= 3:
                            return lo
            return ""

        def _next_companion_col_in_src(src_cells: list[list], parent_col: int, n: int = 1) -> int | None:
            """Companion en fuente: siguiente col bajo el mismo período de fecha que parent_col.
            Acepta cols sin fecha (merge) O con la misma fecha que el padre (no merge).
            Para si hay una fecha DIFERENTE (nuevo período)."""
            _dp = re.compile(r"\d{4}-\d{2}-\d{2}|\d{2}-\d{4}")
            def _col_dates(col):
                dates = set()
                for row in src_cells[:8]:
                    if col < len(row):
                        cv = str(row[col].get("calculatedValue") or row[col].get("value") or "") if isinstance(row[col], dict) else ""
                        for m in _dp.findall(cv):
                            dates.add(m)
                return dates
            parent_dates = _col_dates(parent_col)
            found = 0
            col = parent_col + 1
            while col < parent_col + 20:
                col_dates = _col_dates(col)
                # Si tiene fechas distintas al padre → nuevo período, parar
                if col_dates and not col_dates.issubset(parent_dates):
                    break
                # Companion: tiene M$ (o "efecto" en sub-encabezado)
                has_ms = any(
                    str(row[col].get("calculatedValue") or row[col].get("value") or "").strip().lower() in ("m$", "$") if isinstance(row[col], dict) else False
                    for row in src_cells[:12] if col < len(row)
                )
                has_efecto = any(
                    "efecto" in str(row[col].get("calculatedValue") or row[col].get("value") or "").lower() if isinstance(row[col], dict) else False
                    for row in src_cells[5:13] if col < len(row)
                )
                if has_ms or has_efecto:
                    found += 1
                    if found >= n:
                        return col
                col += 1
            return None

        # Palabras que invierten el sentido de un segmento. Si la diferencia
        # entre dos etiquetas se reduce a una de estas, NO son el mismo
        # segmento por más que una contenga a la otra.
        _NEGACIONES = {"no", "non", "sin"}

        def _find_src_col_by_segment(
            src_cells: list[list], kw_src: str, segment_label: str,
            occurrence_index: int = 0
        ) -> int | None:
            """
            Busca en el fuente la columna que (a) está bajo el mismo segmento
            y (b) contiene kw_src en el encabezado.
            Si no hay segmento o no se encuentra, usa índice de ocurrencia (Nth match).
            """
            if not kw_src:
                return None
            if not segment_label:
                # Usar índice de ocurrencia (no ignorarlo como hacía _find_src_col)
                result = _find_src_col_nth(src_cells, kw_src, occurrence_index)
                if result is None and occurrence_index > 0:
                    base_col = _find_src_col_nth(src_cells, kw_src, 0)
                    if base_col is not None:
                        result = base_col + occurrence_index
                return result

            _date_re = re.compile(r"\d{4}-\d{2}-\d{2}|\d{2}-\d{4}|\d{4}/\d{2}/\d{2}")
            _skip = {"m$", "%", ""}

            # Paso 1: encontrar todas las columnas de inicio de segmento en el fuente
            # Un "inicio de segmento" es una celda con texto no-fecha en las primeras 8 filas
            seg_starts: list[tuple[int, int, str]] = []  # (fila, col, label)
            for ri, row in enumerate(src_cells[:8]):
                for jj, cell in enumerate(row):
                    if not isinstance(cell, dict):
                        continue
                    for vk in ("calculatedValue", "value"):
                        raw = str(cell.get(vk, "") or "").strip()
                        lo  = raw.lower()
                        if lo in _skip or _date_re.search(lo) or len(raw) < 3:
                            continue
                        seg_starts.append((ri, jj, lo))

            # Paso 2: encontrar cuál segmento del fuente coincide con segment_label
            # Solo usar seg_starts si los valores son texto real (no fórmulas)
            real_segs = [(ri, jj, lbl) for ri, jj, lbl in seg_starts
                         if not lbl.startswith("=")]

            matched_col: int | None = None
            if real_segs and segment_label and not segment_label.startswith("="):
                # 1) Coincidencia exacta: siempre gana.
                #    Sin esto "Corrientes" se lleva por delante a "No corrientes",
                #    porque una es subcadena de la otra y aparece antes.
                for _, jj, lbl in real_segs:
                    if lbl == segment_label:
                        matched_col = jj
                        break

                # 2) Sin exacta: subcadena, pero solo si lo que sobra entre las
                #    dos etiquetas no es una negación. Así "corrientes" nunca
                #    calza con "no corrientes" (ni al revés), que son segmentos
                #    opuestos y contiguos en casi todas las notas.
                if matched_col is None:
                    for _, jj, lbl in real_segs:
                        if segment_label not in lbl and lbl not in segment_label:
                            continue
                        if _NEGACIONES & (set(lbl.split()) ^ set(segment_label.split())):
                            continue
                        matched_col = jj
                        break

            if matched_col is not None:
                # Paso 3: dentro del segmento, buscar kw_src
                next_seg_col = min(
                    (jj for _, jj, _ in real_segs if jj > matched_col),
                    default=9999
                )
                for row in src_cells[:8]:
                    for jj in range(matched_col, min(next_seg_col, len(row))):
                        cell = row[jj]
                        if not isinstance(cell, dict):
                            continue
                        for vk in ("calculatedValue", "value"):
                            v = str(cell.get(vk, "") or "").lower()
                            if kw_src in v:
                                return jj

            # Segmento no encontrado o sin texto real → usar índice de ocurrencia.
            # Si la Nth ocurrencia no existe (celdas fusionadas: solo la 1ra tiene fecha),
            # fallback: col de occ=0 + offset (columnas contiguas dentro del mismo merge).
            result = _find_src_col_nth(src_cells, kw_src, occurrence_index)
            if result is None and occurrence_index > 0:
                base_col = _find_src_col_nth(src_cells, kw_src, 0)
                if base_col is not None:
                    result = base_col + occurrence_index
            return result

        comp_cols_by_name: dict[str, list[dict]] = {}
        for sname in batch:
            comp_cols: list[dict] = []
            seen: set[int] = set()
            occurrence_counts: dict[tuple, int] = {}
            def _fila_en_blanco(row: list) -> bool:
                """True si la fila no tiene ningún texto (separador entre tablas)."""
                for cell in row[:30]:
                    if not isinstance(cell, dict):
                        continue
                    v = str(cell.get("calculatedValue") or cell.get("value") or "").strip()
                    if v:
                        return False
                return True

            for col_type, kw_detect, src_id, src_sh, kw_src in TYPE_MAP:
                if not kw_detect or not src_id:
                    continue
                all_rows = tgt_cells_by_name[sname]
                # Notas con dos tablas apiladas y estructura NO relacionada (ej. tabla de
                # este período arriba, tabla del período anterior "tal cual se reportó"
                # abajo) pueden repetir por coincidencia la misma fecha que busca este
                # col_type, pero en una columna de la tabla de abajo que no tiene nada
                # que ver. Para no mezclarlas: una vez encontrada la primera coincidencia,
                # dejar de buscar columnas NUEVAS más allá de la primera fila en blanco
                # (separador de tabla). El mecanismo de "doble sub-tabla" (sub2_header_row,
                # más abajo) sigue funcionando igual: busca dentro de la MISMA columna,
                # no se ve afectado por este límite.
                primer_match_row: int | None = None
                for i, row in enumerate(all_rows):
                    if primer_match_row is not None and i > primer_match_row and _fila_en_blanco(row):
                        break
                    # Más allá de fila 7: solo procesar si la keyword aparece en
                    # ≥2 celdas de esta fila (indica celda fusionada = encabezado real).
                    # Filas 0-7: aceptar incluso match único (encabezado principal).
                    if i >= 8:
                        matches_in_row = sum(
                            1 for c in row
                            if isinstance(c, dict) and kw_detect in str(
                                c.get("calculatedValue") or c.get("value") or ""
                            ).lower()
                        )
                        if matches_in_row < 2:
                            continue
                    for j, cell in enumerate(row):
                        if j in seen or not isinstance(cell, dict):
                            continue
                        for val_key in ("calculatedValue", "value"):
                            v = str(cell.get(val_key, "") or "").lower()
                            if kw_detect in v:
                                if primer_match_row is None:
                                    primer_match_row = i
                                # Skip % columns: check surrounding rows (±4) for "%" label
                                win_s = max(0, i - 4)
                                win_e = min(len(all_rows), i + 5)
                                def _cell_str(cell_d):
                                    if not isinstance(cell_d, dict):
                                        return ""
                                    return str(
                                        cell_d.get("calculatedValue") or
                                        cell_d.get("value") or ""
                                    ).strip()
                                # Buscar "%" siempre en las primeras 10 filas
                                # (donde están los encabezados M$/%),
                                # independientemente de en qué fila se detectó la fecha.
                                is_pct = any(
                                    _cell_str(r[j]) == "%"
                                    for r in all_rows[:10]
                                    if j < len(r)
                                )
                                if not is_pct:
                                    # Detectar segmento horizontal (tablas multi-segmento)
                                    seg_label = _find_segment_label(all_rows, j, i)

                                    # Detectar doble sub-tabla: buscar si la misma
                                    # keyword aparece de nuevo en la misma columna j
                                    # en filas posteriores (sub-tabla inferior).
                                    sub2_header_row = None
                                    sub2_data_start = None
                                    for i2, row2 in enumerate(all_rows[i + 1:], start=i + 1):
                                        cell2 = row2[j] if j < len(row2) else None
                                        if not isinstance(cell2, dict):
                                            continue
                                        for vk2 in ("calculatedValue", "value"):
                                            v2 = str(cell2.get(vk2, "") or "").lower()
                                            if kw_detect in v2:
                                                sub2_header_row = i2
                                                break
                                        if sub2_header_row is not None:
                                            break
                                    if sub2_header_row is not None:
                                        # Encontrar primera fila de datos tras el encabezado inferior
                                        for i3 in range(sub2_header_row + 1, len(all_rows)):
                                            cell3 = all_rows[i3][j] if j < len(all_rows[i3]) else None
                                            has_kw3 = isinstance(cell3, dict) and any(
                                                kw_detect in str(cell3.get(vk3, "") or "").lower()
                                                for vk3 in ("calculatedValue", "value")
                                            )
                                            if not has_kw3:
                                                sub2_data_start = i3
                                                break
                                    occ_key = (col_type, kw_detect)
                                    occ_idx = occurrence_counts.get(occ_key, 0)
                                    occurrence_counts[occ_key] = occ_idx + 1
                                    comp_cols.append({
                                        "col":              j,
                                        "type":             col_type,
                                        "src_id":           src_id,
                                        "src_sh":           src_sh,
                                        "kw_src":           kw_src,
                                        "first_header_row": i,
                                        "segment_label":    seg_label,
                                        "occurrence_index": occ_idx,
                                        "sub2_header_row":  sub2_header_row,
                                        "sub2_data_start":  sub2_data_start,
                                        "sub_table_offset": (sub2_header_row - i) if sub2_header_row else None,
                                    })
                                    seen.add(j)
                                    # Columnas compañeras bajo el mismo merge de fecha:
                                    # la celda de fecha solo existe en la 1ra col del merge;
                                    # las siguientes (ej. "Efecto en resultados") tienen fecha vacía.
                                    _date_pat = re.compile(r"\d{4}-\d{2}-\d{2}|\d{2}-\d{4}")
                                    jj = j + 1
                                    _skipped_sep = 0
                                    _companion_idx = 0  # cuántas companions ya añadimos
                                    while jj < 500 and jj not in seen:
                                        # Parar si la col tiene cualquier fecha en encabezado
                                        def _col_has_date(col):
                                            for rr in all_rows[:8]:
                                                if col >= len(rr): continue
                                                cv = str(rr[col].get("calculatedValue") or rr[col].get("value") or "") if isinstance(rr[col], dict) else ""
                                                if _date_pat.search(cv):
                                                    return True
                                            return False
                                        if _col_has_date(jj):
                                            break
                                        # Debe tener M$ en alguna fila de encabezado (col de datos)
                                        def _col_has_ms(col):
                                            for rr in all_rows[:12]:
                                                if col >= len(rr): continue
                                                cv = str(rr[col].get("calculatedValue") or rr[col].get("value") or "").strip() if isinstance(rr[col], dict) else ""
                                                if cv.lower() in ("m$", "$"):
                                                    return True
                                            return False
                                        if not _col_has_ms(jj):
                                            # Permitir hasta 2 cols separadoras vacías antes de rendirse
                                            _skipped_sep += 1
                                            if _skipped_sep > 2:
                                                break
                                            jj += 1
                                            continue
                                        _skipped_sep = 0
                                        # Saltar columnas %
                                        if any(_cell_str(r[jj]) == "%" for r in all_rows[:10] if jj < len(r)):
                                            jj += 1
                                            continue
                                        _companion_idx += 1
                                        occ_key_c = (col_type, kw_detect)
                                        occ_idx_c = occurrence_counts.get(occ_key_c, 0)
                                        occurrence_counts[occ_key_c] = occ_idx_c + 1
                                        comp_cols.append({
                                            "col":                  jj,
                                            "type":                 col_type,
                                            "src_id":               src_id,
                                            "src_sh":               src_sh,
                                            "kw_src":               kw_src,
                                            "first_header_row":     i,
                                            "segment_label":        seg_label,
                                            "occurrence_index":     occ_idx_c,
                                            "sub2_header_row":      sub2_header_row,
                                            "sub2_data_start":      sub2_data_start,
                                            "sub_table_offset":     (sub2_header_row - i) if sub2_header_row else None,
                                            "is_companion":         True,
                                            "companion_src_offset": _companion_idx,  # saltar N cols M$ en fuente desde src_col
                                        })
                                        seen.add(jj)
                                        jj += 1
                                break
            if comp_cols:
                comp_cols_by_name[sname] = comp_cols

        with_cols = list(comp_cols_by_name)

        # 7. Leer celdas fuente agrupadas por (src_id, sheet) para evitar lecturas duplicadas
        #    Clave: (src_id, sname) → cells
        src_read_keys: list[tuple[str, str, str]] = []  # (src_id, sheet_id, sname)
        seen_reads: set[tuple[str, str]] = set()
        for sname in with_cols:
            for col_info in comp_cols_by_name[sname]:
                sid_src = col_info["src_id"]
                src_sh  = col_info["src_sh"]
                if not sid_src or sname not in src_sh:
                    continue
                key = (sid_src, sname)
                if key not in seen_reads:
                    seen_reads.add(key)
                    src_read_keys.append((sid_src, src_sh[sname], sname))

        src_cells_cache: dict[tuple[str, str], list[list]] = {}
        if src_read_keys:
            results = await asyncio.gather(
                *(_read_lim(sid, sheet_id) for sid, sheet_id, _ in src_read_keys)
            )
            for (sid, _, sname), cells in zip(src_read_keys, results):
                src_cells_cache[(sid, sname)] = cells

        # 8. Procesar cada hoja
        for sname in with_cols:
            sid_t     = tgt_sheets[sname]
            tgt_cells = tgt_cells_by_name[sname]

            sheet_report: dict[str, Any] = {
                "sheet": sname,
                "comp_cols": [
                    f"{_col_letter(c['col'])}({c['type']},seg={c.get('segment_label','')!r})"
                    for c in comp_cols_by_name[sname]
                ],
                "cols_written": 0,
            }

            for col_info in comp_cols_by_name[sname]:
                dest_col = col_info["col"]
                col_type = col_info["type"]
                src_id   = col_info["src_id"]
                kw_src   = col_info["kw_src"]

                # Obtener celdas fuente desde cache
                src_cells = src_cells_cache.get((src_id, sname), [])
                if not src_cells:
                    continue

                # Buscar columna fuente por segmento + keyword (para tablas multi-segmento)
                seg_label       = col_info.get("segment_label", "")
                occurrence_index = col_info.get("occurrence_index", 0)
                src_col = _find_src_col_by_segment(src_cells, kw_src, seg_label, occurrence_index)
                companion_offset = col_info.get("companion_src_offset", 0)
                if companion_offset and src_col is not None:
                    src_col = _next_companion_col_in_src(src_cells, src_col, companion_offset)
                sheet_report.setdefault("_debug_src_cols", []).append(
                    f"{_col_letter(dest_col)}({col_type}): seg={seg_label!r} occ={occurrence_index} kw={kw_src!r} -> src_col={src_col}"
                    + (f" [companion+{companion_offset}]" if companion_offset else "")
                )
                if src_col is None:
                    continue

                sub2_data_start  = col_info.get("sub2_data_start")
                sub_table_offset = col_info.get("sub_table_offset")

                # Realineación por etiqueta: cuando la plantilla del archivo fuente
                # tiene filas de más o de menos respecto al destino, la fila i del
                # destino NO corresponde a la fila i del fuente. Se busca en el
                # fuente la fila con la misma etiqueta dentro de una ventana cercana
                # y se usa esa. Si las plantillas están alineadas (caso normal) la
                # etiqueta calza en la misma fila y el comportamiento no cambia.
                _VENTANA_ALINEACION = 8

                src_vals: list[Any] = []
                src_corr: list[bool] = []   # False = la fila no existe en el fuente
                for i in range(len(tgt_cells)):
                    # Doble sub-tabla: filas de la sub-tabla inferior del destino
                    # se remapean a las filas de la sub-tabla superior del fuente,
                    # PERO solo si la fuente no tiene ya datos en la misma fila.
                    # Cuando ambas sub-tablas están en las mismas filas (ej. nota 85),
                    # el offset no hace falta y aplicarlo remapea al lugar incorrecto.
                    if sub2_data_start and sub_table_offset and i >= sub2_data_start:
                        row_orig = src_cells[i] if 0 <= i < len(src_cells) else []
                        sv_orig  = _cv(row_orig[src_col]) if src_col < len(row_orig) else None
                        if sv_orig is not None:
                            src_row_i = i          # fuente tiene datos aquí: no aplicar offset
                        else:
                            src_row_i = i - sub_table_offset
                    else:
                        src_row_i = i

                    lbl_t = _norm_lbl(_etiqueta_fila(tgt_cells[i]))
                    row_b = src_cells[src_row_i] if 0 <= src_row_i < len(src_cells) else []
                    if lbl_t and _norm_lbl(_etiqueta_fila(row_b)) != lbl_t:
                        # Desfase: buscar la etiqueta cerca, de la fila más próxima a
                        # la más lejana. La búsqueda NO cruza una fila en blanco (sin
                        # etiqueta): eso marca el borde de la tabla/bloque, y notas con
                        # dos tablas apiladas (año actual / año anterior) repiten las
                        # mismas etiquetas — cruzar el borde mezclaría ambos bloques.
                        hallada = None
                        for signo in (-1, 1):
                            for d in range(1, _VENTANA_ALINEACION + 1):
                                cand = src_row_i + signo * d
                                if not (0 <= cand < len(src_cells)):
                                    break
                                lbl_cand = _norm_lbl(_etiqueta_fila(src_cells[cand]))
                                if not lbl_cand:
                                    break   # fila en blanco: no seguir en esta dirección
                                if lbl_cand == lbl_t:
                                    hallada = cand
                                    break
                            if hallada is not None:
                                break
                        if hallada is None:
                            src_vals.append(None)
                            src_corr.append(False)
                            continue
                        src_row_i = hallada

                    row_s = src_cells[src_row_i] if 0 <= src_row_i < len(src_cells) else []
                    sv    = _cv(row_s[src_col]) if src_col < len(row_s) else None
                    src_vals.append(sv if isinstance(sv, (int, float)) else None)
                    src_corr.append(True)

                write_vals: list[Any] = []
                for i, v in enumerate(src_vals):
                    if _is_formula(tgt_cells[i], dest_col):
                        write_vals.append(None)
                    elif not src_corr[i]:
                        # La fila no existe en el archivo fuente: no se inventa un
                        # valor ni se pisa el que ya está. Queda para revisión manual.
                        write_vals.append(None)
                    elif v is None:
                        # Si la fuente es None pero el destino tiene valor numérico, escribir 0
                        # para limpiar valores erróneos previos en Workiva
                        dest_cv = _cv(tgt_cells[i][dest_col]) if dest_col < len(tgt_cells[i]) else None
                        write_vals.append(0 if isinstance(dest_cv, (int, float)) and dest_cv != 0 else None)
                    else:
                        write_vals.append(v)

                n = sum(1 for v in (src_vals if params.dry_run else write_vals)
                        if v is not None)
                if n == 0:
                    continue

                if not params.dry_run:
                    # Columnas de BALANCE: solo escribir en mes 03 (restricción contable)
                    # EERR, quarter y prev_period se escriben en cualquier mes
                    if col_type == "bal" and mm != "03":
                        sheet_report.setdefault("cols_skipped_bal_restriction", []).append(
                            _col_letter(dest_col)
                        )
                        continue
                    ok, motivo = await _write_column(
                        params.spreadsheet_id, sid_t, dest_col, write_vals
                    )
                    if ok:
                        sheet_report["cols_written"] += 1
                        report["total_cols_written"] += 1
                    else:
                        sheet_report.setdefault("cols_failed", []).append({
                            "col": _col_letter(dest_col), "motivo": motivo,
                        })
                        report["sheets_failed"].append({
                            "sheet": sname,
                            "error": f"Col {_col_letter(dest_col)}: {motivo}",
                        })
                        report["total_cols_failed"] += 1
                    continue
                else:
                    # Modo validación
                    equal, diff, sin_corr, samples, filas_det = 0, 0, 0, [], []
                    for i in range(len(src_vals)):
                        row_t = tgt_cells[i]
                        if not src_corr[i]:
                            # La fila no existe en el archivo fuente. Se reporta para
                            # revisión manual en lugar de descartarla en silencio.
                            _c = _cv(row_t[dest_col]) if dest_col < len(row_t) else None
                            if not isinstance(_c, (int, float)) or _c == 0:
                                # Encabezados (fechas, "M$"), texto y celdas vacías o en
                                # cero no son candidatos a comparación: no son hallazgo.
                                continue
                            sin_corr += 1
                            if params.detalle_filas:
                                filas_det.append({
                                    "fila":     i + 1,
                                    "etiqueta": _etiqueta_fila(row_t),
                                    "destino":  _c,
                                    "fuente":   None,
                                    "estado":   "SIN CORRESPONDENCIA",
                                })
                            continue
                        v = src_vals[i]
                        if v is None:
                            continue
                        cur     = _cv(row_t[dest_col]) if dest_col < len(row_t) else None
                        if cur is None or (isinstance(cur, str) and not cur.strip()):
                            cur_num = 0.0
                        elif isinstance(cur, (int, float)):
                            cur_num = float(cur)
                        else:
                            cur_num = None
                        # Tolerancia 1.000 pesos: montos se presentan en M$,
                        # diferencias menores a 1.000 son insignificantes (redondeo)
                        if cur_num is not None and abs(cur_num - float(v)) < 1000:
                            equal += 1
                            estado = "OK"
                        else:
                            diff  += 1
                            estado = "HALLAZGO" if cur_num is not None else "NO PROCESADO"
                            if len(samples) < params.max_ejemplos:
                                samples.append({"fila": i + 1, "destino": cur, "fuente": v})
                        if params.detalle_filas:
                            filas_det.append({
                                "fila":     i + 1,
                                "etiqueta": _etiqueta_fila(row_t),
                                "destino":  cur,
                                "fuente":   v,
                                "estado":   estado,
                            })

                    comp: dict[str, Any] = {
                        "col":            _col_letter(dest_col),
                        "tipo":           col_type,
                        "valores_fuente": n,
                        "iguales":        equal,
                        "distintos":      diff,
                    }
                    if sin_corr:
                        comp["sin_correspondencia"] = sin_corr
                    if samples:
                        comp["ejemplos_distintos"] = samples
                    if params.detalle_filas:
                        kw_active = {
                            "bal": kw_bal, "eerr": kw_eerr,
                            "quarter": kw_quarter, "prev_period": kw_prev,
                        }.get(col_type, "")
                        textos: list[str] = []
                        for row_h in tgt_cells[:8]:
                            for c_h in (dest_col, dest_col - 1, dest_col - 2):
                                if 0 <= c_h < len(row_h):
                                    t = _cv(row_h[c_h])
                                    s = str(t).strip() if t is not None else ""
                                    if (s and s not in ("M$", "Agrupador")
                                            and not re.fullmatch(r"\d{4}-\d{2}-\d{2}", s)
                                            and (not kw_active or kw_active not in s.lower())
                                            and s not in textos):
                                        textos.append(s)
                                        break
                        comp["contexto"] = " ".join(textos)
                        comp["filas"]    = filas_det

                    sheet_report.setdefault("comparacion", []).append(comp)
                    sheet_report["cols_written"] += 1
                    report["total_cells_equal"] = report.get("total_cells_equal", 0) + equal
                    report["total_cells_diff"]  = report.get("total_cells_diff", 0) + diff
                    report["total_cols_written"] += 1

            report["sheets_processed"].append(sheet_report)

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
    spreadsheet_id: str       = Field(...)
    sheet_name:     str       = Field(...)
    sum_col:        int       = Field(..., ge=0)
    detail_cols:    list[int] = Field(...)
    tolerance:      float     = Field(default=1.0, ge=0)
    header_rows:    int       = Field(default=5, ge=0)


@mcp.tool(name="workiva_verify_sums",
          annotations={"readOnlyHint": True, "destructiveHint": False,
                       "idempotentHint": True, "openWorldHint": True})
async def workiva_verify_sums(params: VerifySumsInput) -> str:
    """Verifica aritméticamente subtotales y totales de una hoja."""
    try:
        sheets = await _get_sheets(params.spreadsheet_id)
        sid    = sheets.get(params.sheet_name)
        if not sid:
            return f"Error: Hoja '{params.sheet_name}' no encontrada."
        cells    = await _read_sheet_cells(params.spreadsheet_id, sid)
        pass_cnt = fail_cnt = 0
        failures: list[dict] = []
        for i, row in enumerate(cells[params.header_rows:], start=params.header_rows):
            total_val = _cv(row[params.sum_col]) if params.sum_col < len(row) else None
            if not isinstance(total_val, (int, float)):
                continue
            detail_sum = sum(
                (_cv(row[dc]) or 0) for dc in params.detail_cols
                if dc < len(row) and isinstance(_cv(row[dc]), (int, float))
            )
            label = str(_cv(row[1]) if len(row) > 1 else f"fila {i+1}") or f"fila {i+1}"
            diff  = abs(total_val - detail_sum)
            if diff <= params.tolerance:
                pass_cnt += 1
            else:
                fail_cnt += 1
                failures.append({
                    "row": i + 1, "label": label,
                    "expected": round(detail_sum, 2),
                    "actual":   round(total_val, 2),
                    "diff":     round(diff, 2),
                })
        return json.dumps({
            "spreadsheet_id": params.spreadsheet_id,
            "sheet_name":     params.sheet_name,
            "status":         "OK" if fail_cnt == 0 else "DIFERENCIAS ENCONTRADAS",
            "pass_count":     pass_cnt, "fail_count": fail_cnt,
            "tolerance":      params.tolerance, "failures": failures,
        }, indent=2, ensure_ascii=False)
    except Exception as e:
        return _handle_error(e)


# ─── 10. CRUZAR NOTAS CON ESTADO PRIMARIO ────────────────────────────────────

class CheckNoteConsistencyInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    spreadsheet_id: str   = Field(...)
    primary_sheet:  str   = Field(...)
    note_sheet:     str   = Field(...)
    primary_col:    int   = Field(..., ge=0)
    note_col:       int   = Field(..., ge=0)
    primary_row:    int   = Field(..., ge=0)
    note_total_row: int   = Field(..., ge=0)
    tolerance:      float = Field(default=1.0, ge=0)
    label:          str   = Field(default="Cruce")


@mcp.tool(name="workiva_check_note_consistency",
          annotations={"readOnlyHint": True, "destructiveHint": False,
                       "idempotentHint": True, "openWorldHint": True})
async def workiva_check_note_consistency(params: CheckNoteConsistencyInput) -> str:
    """Cruza un valor entre estado primario y nota."""
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
        note_val    = await _get_val(params.note_sheet, params.note_total_row, params.note_col)

        if primary_val is None:
            return f"Error: No se pudo leer {params.primary_sheet} fila {params.primary_row+1}"
        if note_val is None:
            return f"Error: No se pudo leer {params.note_sheet} fila {params.note_total_row+1}"

        diff   = abs(primary_val - note_val)
        passed = diff <= params.tolerance
        return json.dumps({
            "label": params.label, "status": "PASS" if passed else "FAIL",
            "primary_sheet": params.primary_sheet, "note_sheet": params.note_sheet,
            "primary_value": round(primary_val, 2), "note_value": round(note_val, 2),
            "diff": round(diff, 2), "tolerance": params.tolerance,
        }, indent=2, ensure_ascii=False)
    except Exception as e:
        return _handle_error(e)


# ══════════════════════════════════════════════════════════════════════════════
# ENTRY POINT
# ══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    if not CLIENT_ID or not CLIENT_SECRET:
        import sys
        print("ERROR: Falta WORKIVA_CLIENT_ID o WORKIVA_CLIENT_SECRET en .env",
              file=sys.stderr)
        sys.exit(1)
    mcp.run()
