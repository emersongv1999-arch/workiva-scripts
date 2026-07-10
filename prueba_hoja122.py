#!/usr/bin/env python3
"""
prueba_hoja122.py  — hardcodeado para E514 IND Q3-2026 "122.- Cuadros de resultados por seg..."
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
NOTA      = "122.- Cuadros de resultados por segmento"
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
    if len(matches) > 1:
        print("Más de un archivo encontrado, usando el primero:")
        for n in matches:
            print(f"  {n}")
    name, ss_id = next(iter(matches.items()))
    print(f"Archivo: {name}\n")

    # Listar hojas para verificar nombre exacto
    w._wk._client = None
    all_sheets = await w._get_sheets(ss_id)
    print("Hojas que contienen '122':")
    for n in all_sheets:
        if "122" in n:
            print(f"  >> {n!r}")
    print()

    id_to_name = {v: k for k, v in all_files.items()}
    _orig_read = w._read_sheet_cells
    async def _debug_read(ss_id, sheet_id):
        nombre = id_to_name.get(ss_id, ss_id[:12])
        print(f"  [DEBUG] leyendo hoja de: {nombre}")
        return await _orig_read(ss_id, sheet_id)
    w._read_sheet_cells = _debug_read

    # Debug: mostrar archivos E514 IND 09 disponibles y qué busca el código
    w._wk._client = None
    all_files_dbg = await w._load_all_files()
    print("Archivos E514_IND_09 disponibles (sin prefijo):")
    for n in sorted(all_files_dbg):
        if "E514_IND_09" in n and not n.startswith("("):
            print(f"  {n!r}")
    print()

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

    src_bal_efectiva = r.get('source_curr_prev') or r.get('source_balance', '?')
    print(f"Período actual        : {r.get('current_end','?')}")
    print(f"Comparativo bal (Dic) : {r.get('prior_end','?')}")
    print(f"Fuente bal EFECTIVA   : {src_bal_efectiva}")
    print(f"Fuente EERR           : {r.get('source_eerr','?')}")
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
            print(f"\n  Tipo col : {comp.get('tipo','?')}")
            print(f"  iguales={comp['iguales']}  distintos={comp['distintos']}")
            hallazgos = [f for f in comp.get("filas", []) if f["estado"] == "HALLAZGO"]
            oks       = [f for f in comp.get("filas", []) if f["estado"] == "OK"]
            print(f"  OK={len(oks)}  HALLAZGOS={len(hallazgos)}")
            for f in comp.get("filas", []):
                estado = f["estado"]
                marca  = "✓" if estado == "OK" else "✗" if estado == "HALLAZGO" else "?"
                print(f"    {marca} fila {f['fila']:>3}  {str(f['etiqueta'])[:40]:<40}"
                      f"  declarado={f['destino']}  fuente={f['fuente']}  [{estado}]")


if __name__ == "__main__":
    asyncio.run(main())
