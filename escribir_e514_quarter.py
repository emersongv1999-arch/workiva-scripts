#!/usr/bin/env python3
"""
escribir_e514_quarter.py — Escribe SOLO las hojas con columnas quarter (trimestral)
que mostraron hallazgos en el diagnóstico de E514 IND Q3-2026.
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

# Hojas con columnas quarter con hallazgos (filtro por número/letra de hoja)
HOJAS_QUARTER = [
    "D.-",      # Estado de resultado integral
    "28.-",     # Remuneraciones personal clave
    "30.-",     # Otra información inventarios
    "92.-",     # Gastos reconocidos
    "104.-",    # Ingresos ordinarios
    "107.-",    # Gastos por naturaleza
    "107 Copy", # copia de 107
    "108.-",    # Gastos personal
    "110.-",    # Otras ganancias
    "111.-",    # Resultado financiero
    "112.-",    # Diferencias de cambio
    "113.-",    # Unidades de reajuste
    "114.-",    # Efecto impuesto
    "116.-",    # Localización efecto impuesto
    "117.-",    # Conciliación impto tasa efectiva
    "118.-",    # Efecto resultados integrales
    "122.-",    # Cuadros de resultados por segmento
]
# Nota: hoja 109 se omite — fila 41 tiene destino con valor y fuente=0 (caso especial)

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

    print("Hojas objetivo (quarter hallazgos):")
    for h in HOJAS_QUARTER:
        print(f"  - {h}")
    print()

    # ── Dry run primero para ver qué va a escribir ────────────────────
    mostrar_dry = input("¿Ver dry_run antes de escribir? (s/N): ").strip().lower()
    if mostrar_dry == "s":
        print("\nCorriendo dry_run...")
        w._wk._client = None
        raw = await w.workiva_fill_comparatives(
            w.FillComparativesInput(
                spreadsheet_id         = ss_id,
                dry_run                = True,
                include_sheets         = HOJAS_QUARTER,
                detalle_filas          = True,
                apply_default_excludes = False,
                max_sheets             = 100,
            )
        )
        r = json.loads(raw)
        if "warning" in r:
            sys.exit(f"ADVERTENCIA: {r['warning']}")

        hojas = r.get("sheets_processed", [])
        omitidas = r.get("sheets_skipped", [])
        print(f"\nHojas encontradas: {len(hojas)}  |  Omitidas: {len(omitidas)}")
        for sh in hojas:
            hallazgos: dict[str, int] = {}
            for comp in sh.get("comparacion", []):
                d = comp.get("distintos", 0)
                if d > 0:
                    t = comp.get("tipo", "?")
                    hallazgos[t] = hallazgos.get(t, 0) + d
            estado = "HALLAZGO" if hallazgos else "OK"
            detalle = "  ".join(f"{t}:{n}" for t, n in sorted(hallazgos.items()))
            print(f"  {sh['sheet'][:55]:<55}  {estado:<10}  {detalle}")
        if omitidas:
            print(f"\nOMITIDAS: {omitidas}")
        print()

    # ── Escritura ─────────────────────────────────────────────────────
    confirm = input("¿Escribir en Workiva? (s/N): ").strip().lower()
    if confirm != "s":
        print("Cancelado.")
        return

    print("\nEscribiendo...")
    w._wk._client = None
    raw2 = await w.workiva_fill_comparatives(
        w.FillComparativesInput(
            spreadsheet_id         = ss_id,
            dry_run                = False,
            include_sheets         = HOJAS_QUARTER,
            apply_default_excludes = False,
            max_sheets             = 100,
        )
    )
    r2 = json.loads(raw2)
    if "warning" in r2:
        print(f"ADVERTENCIA: {r2['warning']}")
        return

    all_written = r2.get("sheets_written", [])
    total_celdas = sum(s.get("cells_written", 0) for s in all_written)

    print(f"\n{'─'*70}")
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
