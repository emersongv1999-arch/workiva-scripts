#!/usr/bin/env python3
"""
prueba_una_nota.py
==================
Valida el comparativo de balance (Dic) de UNA sola nota/hoja,
usando la nueva regla: lee del archivo del período anterior (Q1 para Q2, etc.)

Uso:
  py prueba_una_nota.py E110 2026 Q2 "Nota 5"
  py prueba_una_nota.py E200 2026 Q3 "Nota 12" --tipo IND
"""
import argparse, asyncio, json, os, re, sys
from pathlib import Path

# ── Credenciales ──────────────────────────────────────────────────────────────
os.environ["WORKIVA_CLIENT_ID"]     = "db2c551e-e18a-417e-8e52-d182716b8ef2"
os.environ["WORKIVA_CLIENT_SECRET"] = "wk_secret:oa2c:DzlUCmBQDv6raPxG09me"
os.environ["WORKIVA_WORKSPACE_ID"]  = "w_34913aadaa38420eabd7e4d341b78a1a"

# ── Cargar workiva_mcp_v2 sin activar el servidor FastMCP ────────────────────
import importlib.util, types, unittest.mock

def _load_mcp():
    here = Path(__file__).parent
    path = here / "workiva_mcp_v2.py"
    if not path.exists():
        sys.exit(f"ERROR: No se encuentra {path}")
    # Sustituir FastMCP por un mock para que los decoradores @mcp.tool no fallen
    noop = unittest.mock.MagicMock()
    noop.tool = lambda **kw: (lambda f: f)
    with unittest.mock.patch("mcp.server.fastmcp.FastMCP", return_value=noop):
        spec = importlib.util.spec_from_file_location("workiva_mcp_v2", path)
        mod  = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
    return mod

w = _load_mcp()

MES = {"Q1":"03","Q2":"06","Q3":"09","Q4":"12",
       "1":"03","2":"06","3":"09","4":"12",
       "03":"03","06":"06","09":"09","12":"12"}


async def main():
    parser = argparse.ArgumentParser(description="Prueba comparativo de UNA nota")
    parser.add_argument("sociedad")
    parser.add_argument("anio")
    parser.add_argument("trimestre")
    parser.add_argument("nota",  help="Nombre exacto de la hoja, ej: 'Nota 5'")
    parser.add_argument("--tipo", default="CONSO", choices=["CONSO","IND"])
    args = parser.parse_args()

    soc  = args.sociedad.upper()
    mm   = MES.get(args.trimestre.upper())
    if not mm:
        sys.exit(f"Trimestre '{args.trimestre}' no válido. Usa Q1-Q4 o 03/06/09/12.")

    # 1. Resolver archivo
    print(f"\nBuscando {soc}_{args.tipo}_{mm}-{args.anio}...")
    w._wk._client = None
    all_files = await w._load_all_files()
    patron = re.compile(rf"^{re.escape(soc)}_{args.tipo}_{mm}[-_]{args.anio}_")
    matches = {n: i for n, i in all_files.items() if patron.match(n)}

    if not matches:
        sys.exit(f"No se encontró ningún archivo para {soc} {args.tipo} {mm}-{args.anio}")
    if len(matches) > 1:
        print("Más de un archivo encontrado, usando el primero:")
        for n in matches: print(f"  {n}")
    name, ss_id = next(iter(matches.items()))
    print(f"Archivo: {name}\n")

    # 2. Debug: interceptar _read_sheet_cells para ver qué archivos se leen
    id_to_name = {v: k for k, v in all_files.items()}
    _orig_read = w._read_sheet_cells
    async def _debug_read(ss_id, sheet_id):
        nombre = id_to_name.get(ss_id, ss_id[:12])
        print(f"  [DEBUG] leyendo hoja de: {nombre}")
        return await _orig_read(ss_id, sheet_id)
    w._read_sheet_cells = _debug_read

    # 2. Correr validación solo en la nota indicada
    w._wk._client = None
    raw = await w.workiva_fill_comparatives(
        w.FillComparativesInput(
            spreadsheet_id  = ss_id,
            dry_run         = True,
            include_sheets  = [args.nota],
            max_sheets      = 1,
            detalle_filas   = True,
            apply_default_excludes = False,
        )
    )

    r = json.loads(raw)

    if "warning" in r:
        sys.exit(f"ADVERTENCIA: {r['warning']}")

    # 3. Mostrar fuentes
    src_bal_efectiva = r.get('source_curr_prev') or r.get('source_balance','?')
    print(f"Período actual        : {r.get('current_end','?')}")
    print(f"Comparativo bal (Dic) : {r.get('prior_end','?')}")
    print(f"Fuente bal EFECTIVA   : {src_bal_efectiva}   ← debe ser Q anterior")
    print(f"  (Dic directo sería) : {r.get('source_balance','?')}")
    print(f"Fuente EERR           : {r.get('source_eerr','?')}")
    print("-" * 60)

    hojas = r.get("sheets_processed", [])
    if not hojas:
        print(f"Hoja '{args.nota}' no encontrada o sin columnas comparativas.")
        print(f"Hojas omitidas : {r.get('sheets_skipped', [])}")
        return

    for sh in hojas:
        print(f"\nHoja: {sh['sheet']}  |  columnas: {sh.get('comp_cols', [])}")
        for comp in sh.get("comparacion", []):
            print(f"  Tipo col: {comp.get('tipo','?')}  |  "
                  f"iguales={comp['iguales']}  distintos={comp['distintos']}")
            for f in comp.get("filas", []):
                estado = f["estado"]
                marca  = "✓" if estado == "OK" else "✗" if estado == "HALLAZGO" else "?"
                print(f"    {marca} fila {f['fila']:>3}  {str(f['etiqueta'])[:45]:<45}"
                      f"  declarado={f['destino']}  fuente={f['fuente']}  [{estado}]")


if __name__ == "__main__":
    asyncio.run(main())
