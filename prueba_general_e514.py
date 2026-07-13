#!/usr/bin/env python3
"""
prueba_general_e514.py — corre llenado completo E514 IND Q3-2026 en dry_run
y muestra resumen de hojas con hallazgos por tipo de columna.
Al final pide confirmación para escribir en Workiva.
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

    # ── DRY RUN completo (con paginación) ────────────────────────────
    print("Corriendo dry_run completo (paginado, puede tardar varios minutos)...")

    all_processed: list = []
    all_skipped:   list = []
    r = {}
    offset = 0
    page   = 0
    while True:
        page += 1
        print(f"  Página {page} (offset={offset})...")
        w._wk._client = None
        raw = await w.workiva_fill_comparatives(
            w.FillComparativesInput(
                spreadsheet_id         = ss_id,
                dry_run                = True,
                detalle_filas          = True,
                apply_default_excludes = False,
                max_sheets             = 100,
                sheet_offset           = offset,
            )
        )
        r = json.loads(raw)
        if "warning" in r:
            sys.exit(f"ADVERTENCIA: {r['warning']}")
        all_processed.extend(r.get("sheets_processed", []))
        if offset == 0:
            all_skipped = r.get("sheets_skipped", [])
        if not r.get("has_more", False):
            break
        offset += r.get("batch_size", 100)

    r["sheets_processed"] = all_processed
    r["sheets_skipped"]   = all_skipped

    print(f"\nFuentes detectadas:")
    print(f"  EERR      : {r.get('source_eerr','?')}")
    print(f"  curr_prev : {r.get('source_curr_prev','?')}")
    print(f"  prev_per  : {r.get('source_prev_period','?')}")
    print(f"  balance   : {r.get('source_balance','?')}")
    print()

    hojas = r.get("sheets_processed", [])
    omitidas = r.get("sheets_skipped", [])

    # ── Clasificar hojas ──────────────────────────────────────────────
    def _resumen_hoja(sh):
        hallazgos: dict[str, int] = {}
        for comp in sh.get("comparacion", []):
            d = comp.get("distintos", 0)
            if d > 0:
                t = comp.get("tipo", "?")
                hallazgos[t] = hallazgos.get(t, 0) + d
        return hallazgos

    print(f"{'─'*70}")
    print(f"DIAGNÓSTICO COMPLETO: {len(hojas)} hojas procesadas, {len(omitidas)} omitidas")
    print(f"{'─'*70}")

    # ── Tabla resumen: TODAS las hojas procesadas ─────────────────────
    print(f"\n{'HOJA':<55}  {'ESTADO':<10}  COLUMNAS DETECTADAS")
    print(f"{'─'*70}")
    for sh in hojas:
        hallazgos = _resumen_hoja(sh)
        if hallazgos:
            estado = "HALLAZGO"
            detalle = "  ".join(f"{t}:{n}" for t, n in sorted(hallazgos.items()))
        else:
            estado = "OK"
            detalle = ""
        cols = ", ".join(sh.get("comp_cols", []))
        print(f"  {sh['sheet'][:53]:<53}  {estado:<10}  {detalle}")
        print(f"    cols: {cols[:100]}")

    # ── Hojas omitidas ────────────────────────────────────────────────
    if omitidas:
        print(f"\nHOJAS OMITIDAS ({len(omitidas)}):")
        for o in omitidas:
            print(f"  {o}")

    # ── Detalle de hallazgos por hoja ────────────────────────────────
    print(f"\n{'─'*70}")
    mostrar_detalle = input("\n¿Mostrar detalle fila por fila de los HALLAZGOS? (s/N): ").strip().lower()
    if mostrar_detalle == "s":
        for sh in hojas:
            hallazgos = _resumen_hoja(sh)
            if not hallazgos:
                continue
            print(f"\n{'='*60}")
            print(f"Hoja: {sh['sheet']}")
            print(f"Columnas: {sh.get('comp_cols', [])}")
            for comp in sh.get("comparacion", []):
                if comp.get("distintos", 0) == 0:
                    continue
                print(f"\n  Tipo: {comp.get('tipo','?')}  distintos={comp['distintos']}")
                for f in comp.get("filas", []):
                    if f["estado"] == "HALLAZGO":
                        print(f"    ✗ fila {f['fila']:>3}  {str(f['etiqueta'])[:38]:<38}"
                              f"  dec={f['destino']}  fte={f['fuente']}")

    # ── Escritura ────────────────────────────────────────────────────
    print(f"\n{'─'*70}")
    confirm = input("\n¿Escribir en Workiva? (s/N): ").strip().lower()
    if confirm != "s":
        print("Cancelado.")
        return

    print("\nEscribiendo (paginado)...")
    all_written: list = []
    offset2 = 0
    page2   = 0
    while True:
        page2 += 1
        print(f"  Página {page2} (offset={offset2})...")
        w._wk._client = None
        raw2 = await w.workiva_fill_comparatives(
            w.FillComparativesInput(
                spreadsheet_id         = ss_id,
                dry_run                = False,
                apply_default_excludes = False,
                max_sheets             = 100,
                sheet_offset           = offset2,
            )
        )
        r2 = json.loads(raw2)
        all_written.extend(r2.get("sheets_written", []))
        if not r2.get("has_more", False):
            break
        offset2 += r2.get("batch_size", 100)

    total_celdas = sum(s.get("cells_written", 0) for s in all_written)
    print(f"\nHojas escritas: {len(all_written)}  |  Celdas totales: {total_celdas}")
    for s in all_written:
        if s.get("cells_written", 0) > 0 or s.get("errors"):
            print(f"  {s['sheet'][:55]:<55}  celdas={s.get('cells_written',0)}")
            for e in s.get("errors", []):
                print(f"    ERROR: {e}")


if __name__ == "__main__":
    asyncio.run(main())
