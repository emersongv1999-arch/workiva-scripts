#!/usr/bin/env python3
"""
prueba_hoja26.py — dry_run de la hoja 26 de E211 IND Q3-2026
para verificar el fix de columnas adyacentes bajo merge de fecha.
"""
import asyncio, json, os, re, sys
from pathlib import Path

os.environ["WORKIVA_CLIENT_ID"]     = "db2c551e-e18a-417e-8e52-d182716b8ef2"
os.environ["WORKIVA_CLIENT_SECRET"] = "wk_secret:oa2c:DzlUCmBQDv6raPxG09me"
os.environ["WORKIVA_WORKSPACE_ID"]  = "w_34913aadaa38420eabd7e4d341b78a1a"

SOCIEDAD  = "E211"
ANIO      = "2026"
TIPO      = "IND"
MM        = "09"
NOTA      = "26.-"

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

    # Dry run
    print("Corriendo dry_run hoja 26...")
    w._wk._client = None
    raw = await w.workiva_fill_comparatives(
        w.FillComparativesInput(
            spreadsheet_id         = ss_id,
            dry_run                = True,
            include_sheets         = [NOTA],
            max_sheets             = 1,
            detalle_filas          = True,
            apply_default_excludes = False,
        )
    )
    r = json.loads(raw)
    if "warning" in r:
        sys.exit(f"ADVERTENCIA: {r['warning']}")

    bases = r.get("bases", {})
    print(f"Bases del archivo:")
    for k, v in bases.items():
        print(f"  {k} = {v!r}")
    print()
    print(f"Fuente curr_prev : {r.get('source_curr_prev','?')}")
    print(f"Fuente EERR      : {r.get('source_eerr','?')}")
    print(f"Fuente prev_per  : {r.get('source_prev_period','?')}")
    print("-" * 60)

    hojas = r.get("sheets_processed", [])
    if not hojas:
        print(f"Hoja '{NOTA}' no encontrada.")
        print(f"Omitidas: {r.get('sheets_skipped', [])}")
        return

    for sh in hojas:
        print(f"\nHoja: {sh['sheet']}")
        print(f"Columnas detectadas: {sh.get('comp_cols', [])}")
        for dbg in sh.get("_debug_src_cols", []):
            print(f"  [SRC] {dbg}")
        for comp in sh.get("comparacion", []):
            d = comp.get("distintos", 0)
            i = comp.get("iguales", 0)
            print(f"\n  Tipo: {comp.get('tipo','?')}  iguales={i}  distintos={d}")
            if d > 0:
                for f in comp.get("filas", []):
                    if f["estado"] == "HALLAZGO":
                        print(f"    ✗ fila {f['fila']:>3}  {str(f['etiqueta'])[:38]:<38}"
                              f"  dec={f['destino']}  fte={f['fuente']}")

    # Escribir si OK
    print(f"\n{'─'*60}")
    confirm = input("\n¿Escribir en Workiva? (s/N): ").strip().lower()
    if confirm != "s":
        print("Cancelado.")
        return

    w._wk._client = None
    raw2 = await w.workiva_fill_comparatives(
        w.FillComparativesInput(
            spreadsheet_id         = ss_id,
            dry_run                = False,
            include_sheets         = [NOTA],
            max_sheets             = 1,
            apply_default_excludes = False,
        )
    )
    r2 = json.loads(raw2)
    hojas2 = r2.get("sheets_processed", [])
    for s in hojas2:
        print(f"  {s['sheet']}  cols={s.get('cols_written',0)}")
        for e in s.get("errors", []):
            print(f"    ERROR: {e}")


if __name__ == "__main__":
    asyncio.run(main())
