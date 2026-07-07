#!/usr/bin/env python3
"""
diagnostico_unlock.py
======================
Diagnóstico para encontrar el endpoint correcto para desbloquear celdas.
Hace GET al sheet y prueba varios endpoints posibles con logs completos.

Uso:
    py diagnostico_unlock.py
"""

import asyncio
import time
import warnings
import httpx
import json

warnings.filterwarnings("ignore")

CLIENT_ID     = "db2c551e-e18a-417e-8e52-d182716b8ef2"
CLIENT_SECRET = "wk_secret:oa2c:DzlUCmBQDv6raPxG09me"
WORKSPACE_ID  = "w_34913aadaa38420eabd7e4d341b78a1a"

TOKEN_URL    = "https://api.app.wdesk.com/iam/v1/oauth2/token"
PLATFORM_URL = "https://api.app.wdesk.com/platform/v1"
VERIFY_SSL   = False

_token    = ""
_token_ts = 0.0
_client: httpx.AsyncClient | None = None


async def _get_client():
    global _client
    if _client is None or _client.is_closed:
        _client = httpx.AsyncClient(verify=VERIFY_SSL, timeout=120.0)
    return _client


async def _get_token():
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


async def req(method, url, body=None, content_type="application/json"):
    c = await _get_client()
    token = await _get_token()
    headers = {"Authorization": f"Bearer {token}", "Content-Type": content_type}
    if method == "GET":
        r = await c.get(url, headers=headers)
    elif method == "PUT":
        r = await c.put(url, json=body, headers=headers)
    elif method == "PATCH":
        r = await c.patch(url, json=body, headers=headers)
    elif method == "POST":
        r = await c.post(url, json=body, headers=headers)
    print(f"  {method} {url.split('/platform/v1')[-1]}")
    print(f"  → {r.status_code}: {r.text[:300]}")
    return r


async def main():
    # ── Buscar archivo E110_IND_06-2026 ──────────────────────────────────────
    print("Buscando archivo E110_IND_06-2026...")
    url = f"{PLATFORM_URL}/files?workspaceId={WORKSPACE_ID}&limit=100"
    c = await _get_client()
    token = await _get_token()
    target_file_id = None
    target_sheet_id = None

    while url:
        r = await c.get(url, headers={"Authorization": f"Bearer {token}"})
        data = r.json()
        for f in data.get("data", []):
            if "06-2026" in f["name"] and f["name"].startswith("E110"):
                print(f"  Archivo: {f['name']} → {f['id']}")
                target_file_id = f["id"]
        url = data.get("@nextLink")

    if not target_file_id:
        print("No encontrado. Ajusta la búsqueda.")
        return

    # ── GET sheets ────────────────────────────────────────────────────────────
    print("\nObteniendo hojas...")
    r = await c.get(f"{PLATFORM_URL}/spreadsheets/{target_file_id}/sheets",
                    headers={"Authorization": f"Bearer {token}"})
    sheets = r.json().get("data", [])
    for s in sheets:
        if "flujo" in s["name"].lower() or s["name"].startswith("F"):
            print(f"  Hoja: {s['name']} → {s['id']}")
            target_sheet_id = s["id"]
            target_sheet_raw = s
            break

    if not target_sheet_id:
        print("No encontré hoja F. Usando la primera:")
        target_sheet_raw = sheets[0]
        target_sheet_id = sheets[0]["id"]
        print(f"  {sheets[0]['name']} → {sheets[0]['id']}")

    # ── Mostrar estructura completa del sheet ─────────────────────────────────
    print("\n── Estructura completa del sheet ──")
    r_sheet = await c.get(f"{PLATFORM_URL}/spreadsheets/{target_file_id}/sheets/{target_sheet_id}",
                          headers={"Authorization": f"Bearer {token}"})
    print(json.dumps(r_sheet.json(), indent=2, ensure_ascii=False))

    base = f"{PLATFORM_URL}/spreadsheets/{target_file_id}/sheets/{target_sheet_id}"

    # ── Probar endpoints ──────────────────────────────────────────────────────
    print("\n── Probando endpoints de desbloqueo ──")

    print("\n1. GET una celda para ver su estructura:")
    await req("GET", f"{base}/cells/H13")

    print("\n2. PUT /cells/H13/values (conocido — solo para referencia):")
    # No lo ejecutamos para no escribir datos

    print("\n3. PUT /cells/A1:ZZ1000/cellFormats con locked=false:")
    await req("PUT", f"{base}/cells/A1:ZZ1000/cellFormats", {"locked": False})

    print("\n4. PATCH /cells/A1:ZZ1000/cellFormats:")
    await req("PATCH", f"{base}/cells/A1:ZZ1000/cellFormats", {"locked": False})

    print("\n5. PUT /cells/A1:ZZ1000 con format.protection:")
    await req("PUT", f"{base}/cells/A1:ZZ1000", {"format": {"protection": {"locked": False}}})

    print("\n6. PATCH sheet (JSON Patch /protection):")
    await req("PATCH", base,
              [{"op": "replace", "path": "/protection", "value": {"locked": False}}],
              content_type="application/json-patch+json")

    print("\n7. PATCH sheet (JSON Patch /locked):")
    await req("PATCH", base,
              [{"op": "replace", "path": "/locked", "value": False}],
              content_type="application/json-patch+json")

    print("\n8. POST /cells/A1:ZZ1000/batchUpdate:")
    await req("POST", f"{base}/cells/A1:ZZ1000/batchUpdate",
              {"requests": [{"updateCellFormat": {"format": {"protection": {"locked": False}}}}]})

    print("\n9. PUT /protection:")
    await req("PUT", f"{base}/protection", {"locked": False})

    if _client:
        await _client.aclose()


asyncio.run(main())
