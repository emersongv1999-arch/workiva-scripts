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


async def _write_column(ss_id: str, sid: str, col_idx: int,
                         values: list, start_row: int = 0) -> bool:
    cl = _col_letter(col_idx)
    r1 = start_row + 1
    r2 = r1 + len(values) - 1
    rng = f"{cl}{r1}:{cl}{r2}"
    rp = await _wk.put(
        f"{PLATFORM_URL}/spreadsheets/{ss_id}/sheets/{sid}/values/{rng}",
        json={"values": [[v] for v in values]},
    )
    if rp.status_code == 202:
        return await _poll_operation(rp.headers.get("Location", ""))
    return False


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
        ok = await _write_column(
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
            "total_cols_written": 0,
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

        # Fuente BALANCE (prior_end = dic año anterior)
        src_balance_id: str | None = None
        if bases.get("prior_end"):
            mm_b, yy_b = _date_parts(bases["prior_end"])
            for sep in ["-", "_"]:
                name = f"{prefix}{code}_{tipo}_{mm_b}{sep}{yy_b}_{suffix}"
                if name in all_files:
                    src_balance_id = all_files[name]
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
                if name in all_files:
                    src_eerr_id = all_files[name]
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
                if name in all_files:
                    src_prev_id = all_files[name]
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
                if name in all_files:
                    src_curr_prev_id = all_files[name]
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
            if sname in SKIP_SHEETS or sname in extra_excludes:
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

        # Mapeo tipo → (keyword detección en destino, archivo fuente, keyword búsqueda en fuente)
        # Orden de prioridad: quarter primero (más específico), luego eerr, prev_period, bal
        TYPE_MAP = [
            ("quarter",     kw_quarter,   src_eerr_id,       src_sheets_eerr,      kw_quarter),
            ("eerr",        kw_eerr,      src_eerr_id,       src_sheets_eerr,      kw_eerr_src),
            ("curr_prev",   kw_curr_prev, src_curr_prev_id,  src_sheets_curr_prev, kw_curr_prev),
            # bal antes que prev_period: ambos usan "2025-12-31" como keyword;
            # si prev_period va primero, reclama la columna Dic y bal nunca se procesa.
            # Con bal primero, toma la columna y lee del período anterior (Q1 para Q2, etc.).
            ("bal",         kw_bal,
             src_curr_prev_id  or src_balance_id,
             src_sheets_curr_prev if src_curr_prev_id else src_sheets_bal,
             kw_bal),
            ("prev_period", kw_prev,      src_prev_id,       src_sheets_prev,      kw_prev),
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

        comp_cols_by_name: dict[str, list[dict]] = {}
        for sname in batch:
            comp_cols: list[dict] = []
            seen: set[int] = set()
            for col_type, kw_detect, src_id, src_sh, kw_src in TYPE_MAP:
                if not kw_detect or not src_id:
                    continue
                all_rows = tgt_cells_by_name[sname]
                for i, row in enumerate(all_rows):
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
                                    comp_cols.append({
                                        "col":      j,
                                        "type":     col_type,
                                        "src_id":   src_id,
                                        "src_sh":   src_sh,
                                        "kw_src":   kw_src,
                                    })
                                    seen.add(j)
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
                    f"{_col_letter(c['col'])}({c['type']})"
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

                # Buscar columna fuente por keyword date-driven (sin offset fijo)
                src_col = _find_src_col(src_cells, kw_src)
                if src_col is None:
                    continue

                src_vals: list[Any] = []
                for i in range(len(tgt_cells)):
                    row_s = src_cells[i] if i < len(src_cells) else []
                    sv    = _cv(row_s[src_col]) if src_col < len(row_s) else None
                    src_vals.append(sv if isinstance(sv, (int, float)) else None)

                write_vals: list[Any] = [
                    None if _is_formula(tgt_cells[i], dest_col) else v
                    for i, v in enumerate(src_vals)
                ]

                n = sum(1 for v in (src_vals if params.dry_run else write_vals)
                        if v is not None)
                if n == 0:
                    continue

                if not params.dry_run:
                    ok = await _write_column(
                        params.spreadsheet_id, sid_t, dest_col, write_vals
                    )
                    sheet_report["cols_written"] += (1 if ok else 0)
                else:
                    # Modo validación
                    def _etiqueta_fila(row_e: list) -> str:
                        for j in (1, 0, 2):
                            if j < len(row_e):
                                t = _cv(row_e[j])
                                if isinstance(t, str) and t.strip():
                                    return t.strip()
                        return ""

                    equal, diff, samples, filas_det = 0, 0, [], []
                    for i, v in enumerate(src_vals):
                        if v is None:
                            continue
                        row_t   = tgt_cells[i]
                        cur     = _cv(row_t[dest_col]) if dest_col < len(row_t) else None
                        if cur is None or (isinstance(cur, str) and not cur.strip()):
                            cur_num = 0.0
                        elif isinstance(cur, (int, float)):
                            cur_num = float(cur)
                        else:
                            cur_num = None
                        if cur_num is not None and abs(cur_num - float(v)) < 1e-6:
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
