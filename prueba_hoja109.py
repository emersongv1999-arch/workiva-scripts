#!/usr/bin/env python3
"""
prueba_hoja109.py  — hardcodeado para E514 IND Q3-2026 "109.- Depreciación y amortización"
"""
import asyncio, json, os, re, sys
from pathlib import Path

os.environ["WORKIVA_CLIENT_ID"]     = "db2c551e-e18a-417e-8e52-d182716b8ef2"
os.environ["WORKIVA_CLIENT_SECRET"] = "wk_secret:oa2c:DzlUCmBQDv6raPxG09me"
os.environ["WORKIVA_WORKSPACE_ID"]  = "w_34913aadaa38420eabd7e4d341b78a1a"

SOCIEDAD  = "E514"
ANIO      = "2026"
TRIMESTRE = "Q3"
TIPO      = "IND"
NOTA      = "109.- Depreciación y amortización"
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

    print(f"Período actual   : {r.get('current_end','?')}")
    print(f"Fuente EERR      : {r.get('source_eerr','?')}")
    print(f"Fuente curr_prev : {r.get('source_curr_prev','?')}")
    print(f"Fuente prev_per  : {r.get('source_prev_period','?')}")
    print("-" * 60)

    hojas = r.get("sheets_processed", [])
    if not hojas:
        print(f"Hoja '{NOTA}' no encontrada o sin columnas comparativas.")
        print(f"Hojas omitidas : {r.get('sheets_skipped', [])}")
        return

    for sh in hojas:
        print(f"\nHoja: {sh['sheet']}")
        print(f"Columnas detectadas: {sh.get('comp_cols', [])}")
        for dbg in sh.get("_debug_src_cols", []):
            print(f"  [SRC] {dbg}")
        for comp in sh.get("comparacion", []):
            print(f"\n  Tipo col : {comp.get('tipo','?')}  "
                  f"iguales={comp['iguales']}  distintos={comp['distintos']}")
            for f in comp.get("filas", []):
                estado = f["estado"]
                marca  = "✓" if estado == "OK" else "✗" if estado == "HALLAZGO" else "?"
                print(f"    {marca} fila {f['fila']:>3}  {str(f['etiqueta'])[:40]:<40}"
                      f"  declarado={f['destino']}  fuente={f['fuente']}  [{estado}]")


if __name__ == "__main__":
    asyncio.run(main())
