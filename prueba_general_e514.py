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

    # ── DRY RUN completo ──────────────────────────────────────────────
    print("Corriendo dry_run completo (esto puede tardar varios minutos)...")
    w._wk._client = None
    raw = await w.workiva_fill_comparatives(
        w.FillComparativesInput(
            spreadsheet_id         = ss_id,
            dry_run                = True,
            detalle_filas          = True,
            apply_default_excludes = True,
        )
    )

    r = json.loads(raw)

    if "warning" in r:
        sys.exit(f"ADVERTENCIA: {r['warning']}")

    print(f"\nFuentes detectadas:")
    print(f"  EERR      : {r.get('source_eerr','?')}")
    print(f"  curr_prev : {r.get('source_curr_prev','?')}")
    print(f"  prev_per  : {r.get('source_prev_period','?')}")
    print(f"  balance   : {r.get('source_balance','?')}")
    print()

    hojas = r.get("sheets_processed", [])
    omitidas = r.get("sheets_skipped", [])

    # ── Resumen por hoja ──────────────────────────────────────────────
    print(f"{'─'*70}")
    print(f"RESUMEN: {len(hojas)} hojas procesadas, {len(omitidas)} omitidas")
    print(f"{'─'*70}")

    hojas_con_hallazgo = []
    for sh in hojas:
        hallazgos_por_tipo: dict[str, int] = {}
        for comp in sh.get("comparacion", []):
            d = comp.get("distintos", 0)
            if d > 0:
                t = comp.get("tipo", "?")
                hallazgos_por_tipo[t] = hallazgos_por_tipo.get(t, 0) + d
        if hallazgos_por_tipo:
            hojas_con_hallazgo.append((sh["sheet"], hallazgos_por_tipo))

    hojas_ok = [sh["sheet"] for sh in hojas if sh["sheet"] not in
                {n for n, _ in hojas_con_hallazgo}]

    print(f"\nHojas OK (sin diferencias): {len(hojas_ok)}")

    print(f"\nHojas con HALLAZGOS ({len(hojas_con_hallazgo)}):")
    for nombre, tipos in hojas_con_hallazgo:
        detalle = "  ".join(f"{t}:{n}" for t, n in sorted(tipos.items()))
        print(f"  {nombre[:55]:<55}  [{detalle}]")

    if not hojas_con_hallazgo:
        print("  (ninguna)")
        return

    # ── Detalle de hallazgos por hoja ────────────────────────────────
    print(f"\n{'─'*70}")
    mostrar_detalle = input("\n¿Mostrar detalle fila por fila de los hallazgos? (s/N): ").strip().lower()
    if mostrar_detalle == "s":
        for sh in hojas:
            tiene = any(comp.get("distintos", 0) > 0 for comp in sh.get("comparacion", []))
            if not tiene:
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

    print("\nEscribiendo...")
    w._wk._client = None
    raw2 = await w.workiva_fill_comparatives(
        w.FillComparativesInput(
            spreadsheet_id         = ss_id,
            dry_run                = False,
            apply_default_excludes = True,
        )
    )
    r2 = json.loads(raw2)
    escritas = r2.get("sheets_written", [])
    total_celdas = sum(s.get("cells_written", 0) for s in escritas)
    print(f"\nHojas escritas: {len(escritas)}  |  Celdas totales: {total_celdas}")
    for s in escritas:
        if s.get("cells_written", 0) > 0 or s.get("errors"):
            print(f"  {s['sheet'][:55]:<55}  celdas={s.get('cells_written',0)}")
            for e in s.get("errors", []):
                print(f"    ERROR: {e}")


if __name__ == "__main__":
    asyncio.run(main())
