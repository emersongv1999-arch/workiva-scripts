#!/usr/bin/env python3
"""
llenar_todos.py
===============
Llena los comparativos de TODOS los archivos IND de un período,
usando la misma lógica de workiva_mcp.py, sin límite de tiempo
y sin intervención manual.

Corre workiva_mcp.py como módulo (import directo), NO a través del
protocolo MCP: no hay ventana de timeout del host. La escritura es
por hoja/columna con idempotencia, así que reintentar retoma solo
lo pendiente.

USO:
    python llenar_todos.py --mes 09 --anio 2026
    python llenar_todos.py --mes 09 --anio 2026 --dry-run   # simulación, no escribe nada
    python llenar_todos.py --mes 09 --anio 2026 --solo E215  # solo ese código

REQUISITOS:
    - workiva_mcp.py en la misma carpeta
    - .env con las credenciales en la misma carpeta
"""

from __future__ import annotations

import argparse
import asyncio
import json
import re
import sys
import time
from pathlib import Path

# ── Cargar workiva_mcp desde la misma carpeta ────────────────────────────────
import importlib.util


def _load_mcp():
    here = Path(__file__).parent
    mcp_path = here / "workiva_mcp.py"
    if not mcp_path.exists():
        print(f"ERROR: No se encuentra {mcp_path}")
        sys.exit(1)
    spec = importlib.util.spec_from_file_location("workiva_mcp", mcp_path)
    mod  = importlib.util.module_from_spec(spec)
    sys.modules["workiva_mcp"] = mod
    spec.loader.exec_module(mod)
    return mod


# Prefijos entre paréntesis al inicio del nombre: '(CHN) E215_...' → 'E215_...'
_PREFIX_RE = re.compile(r"^\s*\([^)]*\)\s*")


def _strip_prefix(name: str) -> str:
    return _PREFIX_RE.sub("", name or "").strip()


# ── Runner principal ──────────────────────────────────────────────────────────

async def run(mes: str, anio: str, dry_run: bool, solo: str | None):
    mcp = _load_mcp()

    print("=" * 60)
    print(f"  Llenar Comparativos — {mes}-{anio}")
    print(f"  Modo: {'DRY-RUN (simulación)' if dry_run else 'ESCRITURA REAL'}")
    if solo:
        print(f"  Filtro: solo {solo}")
    print("=" * 60)

    # 1. Buscar todos los archivos IND del período
    print("\nBuscando archivos IND...")
    mcp._wk._client = None
    all_files = await mcp._load_all_files()

    pattern = re.compile(
        rf"^E\d+_IND_{mes}[-_]{anio}_Base Notas .+$", re.IGNORECASE
    )
    solo_code = f"E{solo.upper().lstrip('E')}_" if solo else None
    archivos = []
    for name, fid in all_files.items():
        clean = _strip_prefix(name)
        if not pattern.match(clean):
            continue
        if solo_code and not clean.upper().startswith(solo_code):
            continue
        archivos.append({"name": name, "id": fid})
    archivos.sort(key=lambda x: _strip_prefix(x["name"]).upper())

    if not archivos:
        print("  No se encontraron archivos para ese período.")
        return

    print(f"  {len(archivos)} archivo(s) encontrado(s):\n")
    for a in archivos:
        print(f"    · {a['name']}")

    # 2. Procesar cada archivo
    resumen = []
    t_inicio = time.time()

    for i, archivo in enumerate(archivos, 1):
        nombre = archivo["name"]
        fid    = archivo["id"]
        print(f"\n{'─'*60}")
        print(f"[{i}/{len(archivos)}] {nombre}")
        print(f"{'─'*60}")

        intentos = 0
        max_intentos = 5
        completado = False
        ultimo_resultado = None

        while intentos < max_intentos and not completado:
            intentos += 1
            if intentos > 1:
                espera = min(5 * 2 ** (intentos - 2), 60)  # 5, 10, 20, 40 s
                print(f"  Reintento {intentos}/{max_intentos} (espera {espera}s)...")
                await asyncio.sleep(espera)

            try:
                mcp._wk._client = None  # nuevo cliente por cada llamada
                params = mcp.FillComparativesInput(
                    spreadsheet_id=fid,
                    dry_run=dry_run,
                )
                raw = await mcp.workiva_fill_comparatives(params)

                try:
                    result = json.loads(raw)
                except Exception:
                    print(f"  ERROR respuesta no-JSON: {raw[:200]}")
                    continue

                ultimo_resultado = result

                # Mostrar resultado
                if "warning" in result:
                    print(f"  ⚠  {result['warning']}")
                    resumen.append({
                        "archivo": nombre,
                        "estado":  "warning",
                        "detalle": result["warning"],
                    })
                    completado = True
                    continue

                n_hojas     = len(result.get("sheets_processed", []))
                n_saltadas  = len(result.get("sheets_skipped", []))
                n_cols      = result.get("total_cols_written", 0)
                fallidas    = result.get("sheets_failed", [])
                cols_fail   = result.get("total_cols_failed", 0)

                print(f"  Período actual : {result.get('current_end', '?')}")
                print(f"  Período comp.  : {result.get('prior_end', '?')}")
                print(f"  Fuente         : {result.get('source_balance', '?')}")
                print(f"  Hojas proc.    : {n_hojas}")
                print(f"  Hojas saltadas : {n_saltadas}")
                print(f"  Columnas {'simuladas' if dry_run else 'escritas'}: {n_cols}")

                # Detalle de hojas saltadas por ya llenadas
                ya_llenadas = [s for s in result.get("sheets_skipped", [])
                               if "(ya llenada)" in s]
                if ya_llenadas:
                    print(f"  Ya llenadas    : {len(ya_llenadas)} hojas (idempotencia)")

                # Hojas con 0 columnas (info)
                sin_cols = [s["sheet"] for s in result.get("sheets_processed", [])
                            if s.get("cols_written", 0) == 0]
                if sin_cols:
                    print(f"  Sin cols escritas: {', '.join(sin_cols[:5])}"
                          + (" ..." if len(sin_cols) > 5 else ""))

                # Hojas o columnas que fallaron → reintentar el archivo:
                # la idempotencia hace que solo se retome lo pendiente.
                if fallidas or cols_fail:
                    print(f"  ⚠ Hojas con error : {len(fallidas)}"
                          f" | columnas fallidas: {cols_fail}")
                    for f in fallidas[:5]:
                        print(f"      · {f.get('sheet')}: {f.get('error')}")
                    continue

                estado = "ok" if n_cols > 0 else "sin_cambios"
                resumen.append({
                    "archivo":  nombre,
                    "estado":   estado,
                    "hojas":    n_hojas,
                    "columnas": n_cols,
                })
                completado = True

            except Exception as e:
                print(f"  ERROR intento {intentos}: {e}")

        if not completado:
            if ultimo_resultado:
                fallidas = ultimo_resultado.get("sheets_failed", [])
                resumen.append({
                    "archivo": nombre,
                    "estado":  "incompleto",
                    "detalle": (
                        f"{ultimo_resultado.get('total_cols_written', 0)} columnas escritas; "
                        f"{len(fallidas)} hoja(s) con error tras {max_intentos} intentos: "
                        + ", ".join(f.get("sheet", "?") for f in fallidas[:5])
                    ),
                })
                print(f"  ⚠ Quedó incompleto tras {max_intentos} intentos "
                      "(lo escrito persiste; re-ejecutar retoma lo pendiente).")
            else:
                resumen.append({
                    "archivo": nombre,
                    "estado":  "error",
                    "detalle": f"Falló tras {max_intentos} intentos",
                })
                print(f"  ✗ No se pudo procesar tras {max_intentos} intentos.")

    # 3. Resumen final
    elapsed = time.time() - t_inicio
    print(f"\n{'='*60}")
    print(f"  RESUMEN FINAL — {'DRY-RUN' if dry_run else 'ESCRITURA REAL'}")
    print(f"  Tiempo total: {elapsed/60:.1f} min")
    print(f"{'='*60}")

    ok        = [r for r in resumen if r["estado"] == "ok"]
    sin_camb  = [r for r in resumen if r["estado"] == "sin_cambios"]
    warnings  = [r for r in resumen if r["estado"] == "warning"]
    incompl   = [r for r in resumen if r["estado"] == "incompleto"]
    errores   = [r for r in resumen if r["estado"] == "error"]

    print(f"\n  ✓ OK          : {len(ok)}")
    for r in ok:
        print(f"    · {r['archivo']} → {r['columnas']} columnas")

    if sin_camb:
        print(f"\n  ~ Sin cambios : {len(sin_camb)}")
        for r in sin_camb:
            print(f"    · {r['archivo']}")

    if warnings:
        print(f"\n  ⚠ Warnings    : {len(warnings)}")
        for r in warnings:
            print(f"    · {r['archivo']}: {r['detalle']}")

    if incompl:
        print(f"\n  ⚠ Incompletos : {len(incompl)} (re-ejecutar para retomar lo pendiente)")
        for r in incompl:
            print(f"    · {r['archivo']}: {r['detalle']}")

    if errores:
        print(f"\n  ✗ Errores     : {len(errores)}")
        for r in errores:
            print(f"    · {r['archivo']}: {r['detalle']}")

    if dry_run:
        print("\n  [DRY-RUN] No se escribió nada en Workiva.")
        print("  Para aplicar los cambios, corre sin --dry-run.")


# ── Entry point ───────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Llena comparativos de todos los IND de un período"
    )
    parser.add_argument("--mes",     required=True, help="Mes (ej: 09)")
    parser.add_argument("--anio",    required=True, help="Año (ej: 2026)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Simulación: no escribe nada en Workiva")
    parser.add_argument("--solo",    default=None,
                        help="Procesar solo este código (ej: E215 o 215)")
    args = parser.parse_args()

    anio = args.anio.strip()
    if len(anio) == 2:  # '26' → '2026'
        anio = "20" + anio

    asyncio.run(run(
        mes     = args.mes.strip().zfill(2),
        anio    = anio,
        dry_run = args.dry_run,
        solo    = args.solo,
    ))


if __name__ == "__main__":
    main()
