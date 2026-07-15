#!/usr/bin/env python3
"""
escribir_e514.py — Escribe comparativos E514 IND Q3-2026 directamente en Workiva.
Va a todas las hojas (paginado), sin dry_run previo.
"""
import asyncio, json, os, re, sys
from pathlib import Path

os.environ["WORKIVA_CLIENT_ID"]     = "db2c551e-e18a-417e-8e52-d182716b8ef2"
os.environ["WORKIVA_CLIENT_SECRET"] = "wk_secret:oa2c:DzlUCmBQDv6raPxG09me"
os.environ["WORKIVA_WORKSPACE_ID"]  = "w_34913aadaa38420eabd7e4d341b78a1a"

SOCIEDAD  = "E514"
ANIO      = "2026"
TIPO      = "IND"
MM        = "09"

import importlib.util, unittest.mock

def _load_mcp():
    here = Path(__file__).parent
    path = here / "workiva_mcp_v2 (1).py"
    if not path.exists():
        sys.exit(f"ERROR: No se encuentra {path}")
    noop = unittest.mock.MagicMock()
    noop.tool = lambda **kw: (lambda f: f)
    with unittest.mock.patch("mcp.server.fastmcp.FastMCP", return_value=noop):
        spec = importlib.util.spec_from_file_location("workiva_mcp_v2", path)
        mod  = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
    return mod

w = _load_mcp()


async def main():
    print(f"\nBuscando {SOCIEDAD}_{TIPO}_{MM}-{ANIO}...")
    w._wk._client = None
    all_files = await w._load_all_files()
    patron = re.compile(rf"^{re.escape(SOCIEDAD)}_{TIPO}_{MM}[-_]{ANIO}_")
    matches = {n: i for n, i in all_files.items() if patron.match(n)}

    if not matches:
        sys.exit(f"No se encontró ningún archivo para {SOCIEDAD} {TIPO} {MM}-{ANIO}")
    name, ss_id = next(iter(matches.items()))
    print(f"Archivo: {name}\n")

    confirm = input("¿Escribir en Workiva? (s/N): ").strip().lower()
    if confirm != "s":
        print("Cancelado.")
        return

    print("\nEscribiendo (paginado)...")
    all_written: list = []
    offset = 0
    page   = 0
    while True:
        page += 1
        print(f"  Página {page} (offset={offset})...")
        w._wk._client = None
        raw = await w.workiva_fill_comparatives(
            w.FillComparativesInput(
                spreadsheet_id         = ss_id,
                dry_run                = False,
                apply_default_excludes = False,
                max_sheets             = 100,
                sheet_offset           = offset,
            )
        )
        r = json.loads(raw)
        if "warning" in r:
            print(f"ADVERTENCIA: {r['warning']}")
            break
        all_written.extend(r.get("sheets_written", []))
        if not r.get("has_more", False):
            break
        offset += r.get("batch_size", 100)

    print(f"\n{'─'*70}")
    total_celdas = sum(s.get("cells_written", 0) for s in all_written)
    print(f"Hojas escritas : {len(all_written)}")
    print(f"Celdas totales : {total_celdas}")
    print(f"{'─'*70}")

    for s in all_written:
        celdas = s.get("cells_written", 0)
        errores = s.get("errors", [])
        if celdas > 0 or errores:
            print(f"  {s['sheet'][:60]:<60}  celdas={celdas}")
            for e in errores:
                print(f"    ERROR: {e}")

    if total_celdas == 0:
        print("\nNo se escribió ninguna celda.")


if __name__ == "__main__":
    asyncio.run(main())
