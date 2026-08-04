#!/usr/bin/env python3
"""
prueba_llenado_una_nota.py
==========================
Llena el comparativo de balance de UNA sola nota/hoja en Workiva.
ADVERTENCIA: esto SÍ escribe valores en el archivo de Workiva.

Uso:
  py prueba_llenado_una_nota.py E110 2026 Q3 "Nota 5" --tipo IND
"""
import argparse, asyncio, json, os, re, sys, unittest.mock
from pathlib import Path

os.environ["WORKIVA_CLIENT_ID"]     = "db2c551e-e18a-417e-8e52-d182716b8ef2"
os.environ["WORKIVA_CLIENT_SECRET"] = "wk_secret:oa2c:DzlUCmBQDv6raPxG09me"
os.environ["WORKIVA_WORKSPACE_ID"]  = "w_34913aadaa38420eabd7e4d341b78a1a"

def _load_mcp():
    here = Path(__file__).parent
    path = here / "workiva_mcp_v2.py"
    if not path.exists():
        sys.exit(f"ERROR: No se encuentra {path}")
    noop = unittest.mock.MagicMock()
    noop.tool = lambda **kw: (lambda f: f)
    with unittest.mock.patch("mcp.server.fastmcp.FastMCP", return_value=noop):
        import importlib.util
        spec = importlib.util.spec_from_file_location("workiva_mcp_v2", path)
        mod  = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
    return mod

w = _load_mcp()

MES = {"Q1":"03","Q2":"06","Q3":"09","Q4":"12",
       "1":"03","2":"06","3":"09","4":"12",
       "03":"03","06":"06","09":"09","12":"12"}


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("sociedad")
    parser.add_argument("anio")
    parser.add_argument("trimestre")
    parser.add_argument("nota", help="Nombre exacto de la hoja")
    parser.add_argument("--tipo", default="CONSO", choices=["CONSO","IND"])
    args = parser.parse_args()

    soc = args.sociedad.upper()
    mm  = MES.get(args.trimestre.upper())
    if not mm:
        sys.exit(f"Trimestre '{args.trimestre}' no válido.")

    print(f"\nBuscando {soc}_{args.tipo}_{mm}-{args.anio}...")
    w._wk._client = None
    all_files = await w._load_all_files()
    patron = re.compile(rf"^{re.escape(soc)}_{args.tipo}_{mm}[-_]{args.anio}_")
    matches = {n: i for n, i in all_files.items() if patron.match(n)}

    if not matches:
        sys.exit(f"No se encontró archivo para {soc} {args.tipo} {mm}-{args.anio}")
    name, ss_id = next(iter(matches.items()))
    print(f"Archivo: {name}\n")

    # Primero dry_run para ver qué va a escribir
    id_to_name = {v: k for k, v in all_files.items()}
    _orig_read = w._read_sheet_cells
    async def _debug_read(ss_id, sheet_id):
        print(f"  [DEBUG] leyendo de: {id_to_name.get(ss_id, ss_id[:12])}")
        return await _orig_read(ss_id, sheet_id)
    w._read_sheet_cells = _debug_read

    print("--- SIMULACIÓN (dry_run=True) ---")
    w._wk._client = None
    raw = await w.workiva_fill_comparatives(
        w.FillComparativesInput(
            spreadsheet_id=ss_id, dry_run=True,
            include_sheets=[args.nota], max_sheets=1,
            detalle_filas=True, apply_default_excludes=False,
        )
    )
    r = json.loads(raw)
    if "warning" in r:
        sys.exit(f"ADVERTENCIA: {r['warning']}")

    src_efectiva = r.get('source_curr_prev') or r.get('source_balance','?')
    print(f"Fuente bal efectiva : {src_efectiva}")
    print(f"  (Dic directo sería: {r.get('source_balance','?')})")

    hojas = r.get("sheets_processed", [])
    if not hojas:
        sys.exit(f"Hoja '{args.nota}' no encontrada o sin columnas comparativas.")

    cambios = []
    for sh in hojas:
        for comp in sh.get("comparacion", []):
            for f in comp.get("filas", []):
                if f["estado"] == "HALLAZGO":
                    cambios.append(f)
                    print(f"  fila {f['fila']:>3}  declarado={f['destino']}  "
                          f"fuente={f['fuente']}  → se escribiría {f['fuente']}")

    if not cambios:
        print("\nNo hay diferencias — nada que escribir.")
        return

    print(f"\n{len(cambios)} valor(es) a escribir.")
    resp = input("¿Confirmas el llenado real en Workiva? (s/N): ").strip().lower()
    if resp != "s":
        print("Cancelado.")
        return

    print("\n--- LLENADO REAL (dry_run=False) ---")
    w._wk._client = None
    raw2 = await w.workiva_fill_comparatives(
        w.FillComparativesInput(
            spreadsheet_id=ss_id, dry_run=False,
            include_sheets=[args.nota], max_sheets=1,
            detalle_filas=True, apply_default_excludes=False,
        )
    )
    r2 = json.loads(raw2)
    for sh in r2.get("sheets_processed", []):
        print(f"Hoja: {sh['sheet']}  |  columnas escritas: {sh.get('cols_written',0)}")
        for cf in sh.get("cols_failed", []):
            print(f"  ✗ FALLÓ col {cf['col']}: {cf['motivo']}")

    fallidas = r2.get("sheets_failed", [])
    if fallidas:
        print(f"\n✗ {len(fallidas)} error(es) al escribir ({r2.get('total_cols_failed',0)} col(s)):")
        for f in fallidas:
            print(f"  · {f['sheet']}: {f['error']}")
    else:
        print("\nLlenado completado sin errores.")


if __name__ == "__main__":
    asyncio.run(main())
