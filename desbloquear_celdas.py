#!/usr/bin/env python3
"""
desbloquear_celdas.py
=====================
Desbloquea todas las celdas de todas las hojas de todos los archivos
de un mes/año dado en Workiva (IND, CONSO, con cualquier prefijo).

Uso:
    py desbloquear_celdas.py

Luego ingresa mes (ej: 06) y año (ej: 2026) cuando lo pida.

Requisitos:
    pip install httpx python-dotenv
"""

import asyncio
import time
import warnings
import re
import sys

import httpx

warnings.filterwarnings("ignore")

# ── Credenciales ───────────────────────────────────────────────────────────────
CLIENT_ID     = "db2c551e-e18a-417e-8e52-d182716b8ef2"
CLIENT_SECRET = "wk_secret:oa2c:DzlUCmBQDv6raPxG09me"
WORKSPACE_ID  = "w_34913aadaa38420eabd7e4d341b78a1a"

TOKEN_URL    = "https://api.app.wdesk.com/iam/v1/oauth2/token"
PLATFORM_URL = "https://api.app.wdesk.com/platform/v1"
VERIFY_SSL   = False

# ── Cliente HTTP ───────────────────────────────────────────────────────────────
_token    = ""
_token_ts = 0.0
_client: httpx.AsyncClient | None = None


async def _get_client() -> httpx.AsyncClient:
    global _client
    if _client is None or _client.is_closed:
        _client = httpx.AsyncClient(verify=VERIFY_SSL, timeout=120.0)
    return _client


async def _get_token() -> str:
    global _token, _token_ts
    if time.time() - _token_ts < 540 and _token:
        return _token
    c = await _get_client()
    r = await c.post(TOKEN_URL, json={
        "grant_type": "client_credentials",
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
    }, headers={"Content-Type": "application/json"})
    r.raise_for_status()
    _token    = r.json()["access_token"]
    _token_ts = time.time()
    return _token


async def _get(url: str) -> httpx.Response:
    c = await _get_client()
    r = await c.get(url, headers={"Authorization": f"Bearer {await _get_token()}"})
    r.raise_for_status()
    return r


async def _put(url: str, body: dict) -> httpx.Response:
    c = await _get_client()
    r = await c.put(url, json=body,
                    headers={"Authorization": f"Bearer {await _get_token()}"})
    return r


async def _patch(url: str, body: dict) -> httpx.Response:
    c = await _get_client()
    r = await c.patch(url, json=body,
                      headers={"Authorization": f"Bearer {await _get_token()}"})
    return r


# ── Funciones Workiva ──────────────────────────────────────────────────────────

async def load_all_files() -> dict[str, str]:
    """Retorna {nombre: id} de todos los archivos del workspace."""
    result = {}
    url = f"{PLATFORM_URL}/files?workspaceId={WORKSPACE_ID}&limit=100"
    while url:
        r    = await _get(url)
        data = r.json()
        for f in data.get("data", []):
            result[f["name"]] = f["id"]
        url = data.get("@nextLink")
    return result


async def get_sheets(ss_id: str) -> dict[str, str]:
    """Retorna {nombre_hoja: sheet_id}."""
    r    = await _get(f"{PLATFORM_URL}/spreadsheets/{ss_id}/sheets")
    data = r.json()
    return {s["name"]: s["id"] for s in data.get("data", [])}


async def unlock_sheet(ss_id: str, sheet_id: str, sheet_name: str) -> str:
    """
    Intenta desbloquear todas las celdas de una hoja.
    Prueba el endpoint de cellFormats con rango completo.
    Retorna "OK", "SKIP" o descripción del error.
    """
    full_range = "A1:ZZ100000"

    # Intento 1: PUT cellFormats (formato de rango)
    url1 = f"{PLATFORM_URL}/spreadsheets/{ss_id}/sheets/{sheet_id}/cellformats/{full_range}"
    r1 = await _put(url1, {"format": {"protection": {"locked": False}}})
    if r1.status_code in (200, 202, 204):
        return f"OK ({r1.status_code})"

    # Intento 2: PATCH al sheet completo (protección a nivel hoja)
    url2 = f"{PLATFORM_URL}/spreadsheets/{ss_id}/sheets/{sheet_id}"
    r2 = await _patch(url2, {"isProtected": False})
    if r2.status_code in (200, 202, 204):
        return f"OK vía isProtected ({r2.status_code})"

    # Ninguno funcionó — reportar respuesta para diagnóstico
    return (
        f"ERROR: PUT cellformats={r1.status_code} '{r1.text[:120]}' | "
        f"PATCH sheet={r2.status_code} '{r2.text[:120]}'"
    )


# ── Main ───────────────────────────────────────────────────────────────────────

async def main():
    # Pedir mes y año
    print("=" * 60)
    print("Desbloquear celdas Workiva — todos los archivos de un período")
    print("=" * 60)
    mes = input("\nMes (ej: 06): ").strip().zfill(2)
    ano = input("Año (ej: 2026): ").strip()
    patron = f"{mes}-{ano}"
    print(f"\nBuscando archivos con patrón '{patron}'...")

    all_files = await load_all_files()

    # Filtrar archivos que contengan mm-yyyy en su nombre
    matches = {
        name: fid
        for name, fid in all_files.items()
        if re.search(re.escape(patron), name)
    }

    if not matches:
        print(f"\nNo se encontraron archivos con '{patron}'.")
        print("Archivos disponibles (primeros 20):")
        for n in list(all_files)[:20]:
            print(f"  {n}")
        return

    print(f"\nArchivos encontrados ({len(matches)}):")
    for name in sorted(matches):
        print(f"  {name}")

    confirmar = input(f"\n¿Desbloquear TODAS las celdas de estos {len(matches)} archivos? (s/n): ").strip().lower()
    if confirmar != "s":
        print("Cancelado.")
        return

    print()
    total_hojas = 0
    total_ok    = 0
    total_err   = 0

    for fname, fid in sorted(matches.items()):
        print(f"\n{'─'*60}")
        print(f"Archivo: {fname}")
        try:
            sheets = await get_sheets(fid)
        except Exception as e:
            print(f"  ERROR obteniendo hojas: {e}")
            continue

        print(f"  Hojas: {len(sheets)}")
        for sname, sid in sheets.items():
            total_hojas += 1
            try:
                resultado = await unlock_sheet(fid, sid, sname)
                if resultado.startswith("OK"):
                    total_ok += 1
                    print(f"  ✓ {sname} — {resultado}")
                else:
                    total_err += 1
                    print(f"  ✗ {sname} — {resultado}")
            except Exception as e:
                total_err += 1
                print(f"  ✗ {sname} — Excepción: {e}")

    print(f"\n{'='*60}")
    print(f"RESUMEN")
    print(f"  Archivos procesados : {len(matches)}")
    print(f"  Hojas procesadas    : {total_hojas}")
    print(f"  OK                  : {total_ok}")
    print(f"  Con error           : {total_err}")

    if _client:
        await _client.aclose()


asyncio.run(main())
