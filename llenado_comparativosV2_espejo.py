#!/usr/bin/env python3
"""
llenado_comparativosV2_espejo.py  ←  ESPEJO que usa workiva_mcp_v2.py
======================================================================
Idéntico a llenado_comparativosV2.py pero carga workiva_mcp_v2.py
en lugar de workiva_mcp.py para:
  - Detectar y llenar columnas EERR (hoja C y equivalentes) en Q2/Q3/Q4.
  - Restricción mes 03 aplica solo a columnas de BALANCE.

USO:
    python llenado_comparativosV2_espejo.py --mes 09 --anio 2026
    python llenado_comparativosV2_espejo.py --mes 09 --anio 2026 --dry-run
    python llenado_comparativosV2_espejo.py --mes 09 --anio 2026 --solo E200

REQUISITOS:
    - workiva_mcp_v2.py en la misma carpeta
    - .env con las credenciales en la misma carpeta
"""

from __future__ import annotations

import argparse
import asyncio
import importlib.util
import json
import re
import sys
import time
from pathlib import Path


# ── Cargar workiva_mcp_v2 desde la misma carpeta ─────────────────────────────

def _load_mcp():
    here     = Path(__file__).parent
    mcp_path = here / "workiva_mcp_v2.py"
    if not mcp_path.exists():
        print(f"ERROR: No se encuentra {mcp_path}")
        sys.exit(1)
    spec = importlib.util.spec_from_file_location("workiva_mcp_v2", mcp_path)
    mod  = importlib.util.module_from_spec(spec)
    sys.modules["workiva_mcp_v2"] = mod
    spec.loader.exec_module(mod)
    return mod


_PREFIX_RE = re.compile(r"^\s*\([^)]*\)\s*")


def _strip_prefix(name: str) -> str:
    return _PREFIX_RE.sub("", name or "").strip()


MES_POR_TRIMESTRE = {
    "Q1": "03", "Q2": "06", "Q3": "09", "Q4": "12",
    "1": "03", "2": "06", "3": "09", "4": "12",
    "03": "03", "06": "06", "09": "09", "12": "12",
}


# ── Modo interactivo ──────────────────────────────────────────────────────────

def _pedir(texto: str, validar, default: str | None = None) -> str:
    while True:
        v = input(texto)
        for bom in (chr(0xFEFF), chr(0xEF) + chr(0xBB) + chr(0xBF)):
            v = v.removeprefix(bom)
        v = v.strip()
        if not v and default is not None:
            return default
        if validar(v):
            return v
        print("   Valor no válido, intenta de nuevo.")


def pedir_opciones() -> tuple[str, str, bool, str | None, int]:
    print("=== Llenado de Comparativos V2 Espejo (EERR) — modo interactivo ===\n")
    mes_raw = _pedir(
        "Trimestre o mes  (Q1/Q2/Q3/Q4  o  03/06/09/12): ",
        lambda v: v.upper() in MES_POR_TRIMESTRE,
    )
    mes  = MES_POR_TRIMESTRE[mes_raw.upper()]
    anio = _pedir("Año (ej 2026): ",
                  lambda v: re.fullmatch(r"\d{4}", v) is not None)
    modo = _pedir(
        "Modo  [1] DRY-RUN (simulación)  [2] ESCRITURA REAL  (Enter = DRY-RUN): ",
        lambda v: v in ("1", "2"),
        default="1",
    )
    dry_run  = (modo == "1")
    solo_raw = _pedir("Sociedad específica (ej E215) o Enter para TODAS: ",
                      lambda v: True, default="")
    solo     = solo_raw.strip() or None
    lote_raw = _pedir("Hojas por lote (Enter = 50): ",
                      lambda v: v.isdigit() and 1 <= int(v) <= 100, default="50")
    lote     = int(lote_raw)
    print()
    return mes, anio, dry_run, solo, lote


# ── Procesar un archivo completo (con paginación) ────────────────────────────

async def _procesar_archivo(mcp, fid: str, nombre: str,
                             dry_run: bool, lote: int) -> dict:
    offset      = 0
    total_cols  = 0
    total_hojas = 0
    encabezado  = False

    while True:
        mcp._wk._client = None
        params = mcp.FillComparativesInput(
            spreadsheet_id=fid,
            dry_run=dry_run,
            sheet_offset=offset,
            max_sheets=lote,
        )
        raw = await mcp.workiva_fill_comparatives(params)

        try:
            r = json.loads(raw)
        except json.JSONDecodeError:
            return {"estado": "error", "detalle": f"Respuesta no-JSON: {raw[:200]}"}

        if "warning" in r:
            return {"estado": "warning", "detalle": r["warning"]}

        if "message" in r and "sheet_offset" not in r:
            return {"estado": "warning", "detalle": r["message"]}

        if not encabezado:
            candidatas = r.get("total_candidate_sheets", "?")
            print(f"  Período actual  : {r.get('current_end', '?')}")
            print(f"  Período comp.   : {r.get('prior_end', '?')}")
            print(f"  Fuente balance  : {r.get('source_balance', '?')}")
            print(f"  Fuente EERR     : {r.get('source_eerr', 'No encontrado')}")
            print(f"  Hojas candidatas: {candidatas}"
                  f" (excluidos {r.get('skipped_desglose_sociedad', 0)} desgloses)")
            encabezado = True

        hojas_lote  = len(r.get("sheets_processed", []))
        cols_lote   = r.get("total_cols_written", 0)
        total_hojas += hojas_lote
        total_cols  += cols_lote

        accion = "simuladas" if dry_run else "escritas"
        print(f"  lote offset {r.get('sheet_offset', offset):>3}: "
              f"{r.get('batch_size', hojas_lote)} hojas | {cols_lote} columnas {accion}")

        fallidas  = r.get("sheets_failed", [])
        cols_fail = r.get("total_cols_failed", 0)
        if fallidas or cols_fail:
            print(f"  ⚠ Errores en lote: {len(fallidas)} hojas, {cols_fail} cols fallidas")
            for f in fallidas[:5]:
                print(f"      · {f.get('sheet')}: {f.get('error')}")
            return {
                "estado":   "incompleto",
                "detalle":  (
                    f"{total_cols} columnas {accion}; "
                    f"{len(fallidas)} hoja(s) con error en lote offset {offset}: "
                    + ", ".join(f.get("sheet", "?") for f in fallidas[:5])
                ),
                "hojas":    total_hojas,
                "columnas": total_cols,
            }

        if not r.get("has_more"):
            break
        offset = r["next_offset"]

    estado = "ok" if total_cols > 0 else "sin_cambios"
    return {"estado": estado, "hojas": total_hojas, "columnas": total_cols}


# ── Runner principal ──────────────────────────────────────────────────────────

async def run(mes: str, anio: str, dry_run: bool, solo: str | None, lote: int) -> int:
    mcp = _load_mcp()

    print("=" * 65)
    print(f"  Llenado Comparativos V2 Espejo (EERR) — {mes}-{anio}")
    print(f"  Modo  : {'DRY-RUN (simulación)' if dry_run else 'ESCRITURA REAL'}")
    print(f"  Lote  : {lote} hojas por llamada")
    if solo:
        print(f"  Filtro: solo {solo}")
    print("=" * 65)

    print("\nBuscando archivos IND...")
    mcp._wk._client = None
    all_files = await mcp._load_all_files()

    patron    = re.compile(rf"^E\d+_IND_{mes}[-_]{anio}_Base Notas .+$", re.IGNORECASE)
    solo_code = f"E{solo.upper().lstrip('E')}_" if solo else None

    archivos = []
    for name, fid in all_files.items():
        clean = _strip_prefix(name)
        if not patron.match(clean):
            continue
        if solo_code and not clean.upper().startswith(solo_code):
            continue
        archivos.append({"name": name, "id": fid})
    archivos.sort(key=lambda x: _strip_prefix(x["name"]).upper())

    if not archivos:
        print("  No se encontraron archivos para ese período.")
        return 1

    print(f"  {len(archivos)} archivo(s) encontrado(s):\n")
    for a in archivos:
        print(f"    · {a['name']}")

    MAX_INTENTOS = 5
    resumen      = []
    t_inicio     = time.time()

    for i, archivo in enumerate(archivos, 1):
        nombre = archivo["name"]
        fid    = archivo["id"]
        print(f"\n{'─' * 65}")
        print(f"[{i}/{len(archivos)}] {nombre}")
        print(f"{'─' * 65}")

        completado       = False
        ultimo_resultado = None

        for intento in range(1, MAX_INTENTOS + 1):
            if intento > 1:
                espera = min(5 * 2 ** (intento - 2), 60)
                print(f"  Reintento {intento}/{MAX_INTENTOS} (espera {espera}s)...")
                await asyncio.sleep(espera)

            try:
                resultado = await _procesar_archivo(mcp, fid, nombre, dry_run, lote)
            except Exception as e:
                print(f"  ERROR intento {intento}: {e}")
                continue

            ultimo_resultado = resultado

            if resultado["estado"] == "warning":
                print(f"  ⚠  {resultado['detalle']}")
                resumen.append({"archivo": nombre, **resultado})
                completado = True
                break

            if resultado["estado"] == "incompleto":
                print("  Lote con errores — se reintentará el archivo completo.")
                continue

            accion = "simuladas" if dry_run else "escritas"
            print(f"  {'✓' if resultado['estado'] == 'ok' else '~'} "
                  f"{resultado['hojas']} hojas | {resultado['columnas']} columnas {accion}")
            resumen.append({"archivo": nombre, **resultado})
            completado = True
            break

        if not completado:
            if ultimo_resultado and ultimo_resultado.get("columnas", 0) > 0:
                print(f"  ⚠ Incompleto tras {MAX_INTENTOS} intentos (re-ejecutar retoma).")
                resumen.append({
                    "archivo":  nombre, "estado": "incompleto",
                    "detalle":  ultimo_resultado.get("detalle", ""),
                    "hojas":    ultimo_resultado.get("hojas", 0),
                    "columnas": ultimo_resultado.get("columnas", 0),
                })
            else:
                print(f"  ✗ No se pudo procesar tras {MAX_INTENTOS} intentos.")
                resumen.append({
                    "archivo": nombre, "estado": "error",
                    "detalle": f"Falló tras {MAX_INTENTOS} intentos",
                })

    elapsed = time.time() - t_inicio
    print(f"\n{'=' * 65}")
    print(f"  RESUMEN FINAL — {'DRY-RUN' if dry_run else 'ESCRITURA REAL'}")
    print(f"  Tiempo total: {elapsed / 60:.1f} min")
    print(f"{'=' * 65}")

    ok       = [r for r in resumen if r["estado"] == "ok"]
    sin_camb = [r for r in resumen if r["estado"] == "sin_cambios"]
    warnings = [r for r in resumen if r["estado"] == "warning"]
    incompl  = [r for r in resumen if r["estado"] == "incompleto"]
    errores  = [r for r in resumen if r["estado"] == "error"]

    accion = "simuladas" if dry_run else "escritas"

    print(f"\n  ✓ OK           : {len(ok)}")
    for r in ok:
        print(f"    · {r['archivo']} → {r['hojas']} hojas, {r['columnas']} columnas {accion}")
    if sin_camb:
        print(f"\n  ~ Sin cambios  : {len(sin_camb)}")
        for r in sin_camb:
            print(f"    · {r['archivo']}")
    if warnings:
        print(f"\n  ⚠ Warnings     : {len(warnings)}")
        for r in warnings:
            print(f"    · {r['archivo']}: {r['detalle']}")
    if incompl:
        print(f"\n  ⚠ Incompletos  : {len(incompl)} (re-ejecutar para retomar)")
        for r in incompl:
            print(f"    · {r['archivo']}: {r['detalle']}")
    if errores:
        print(f"\n  ✗ Errores      : {len(errores)}")
        for r in errores:
            print(f"    · {r['archivo']}: {r['detalle']}")

    if dry_run:
        print("\n  [DRY-RUN] No se escribió nada en Workiva.")

    return 2 if (incompl or errores) else 0


# ── Entry point ───────────────────────────────────────────────────────────────

def main():
    if len(sys.argv) == 1:
        try:
            mes, anio, dry_run, solo, lote = pedir_opciones()
        except KeyboardInterrupt:
            print("\nCancelado.")
            input("\nPresiona Enter para cerrar...")
            sys.exit(1)
        codigo = asyncio.run(run(mes=mes, anio=anio, dry_run=dry_run, solo=solo, lote=lote))
        input("\nPresiona Enter para cerrar...")
        sys.exit(codigo)

    parser = argparse.ArgumentParser(
        description="Llena comparativos (balance + EERR) de todos los IND de un período",
    )
    parser.add_argument("--mes",     required=True)
    parser.add_argument("--anio",    required=True)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--solo",    default=None)
    parser.add_argument("--lote",    type=int, default=50)
    args = parser.parse_args()

    anio = args.anio.strip()
    if len(anio) == 2:
        anio = "20" + anio

    try:
        codigo = asyncio.run(run(
            mes     = args.mes.strip().zfill(2),
            anio    = anio,
            dry_run = args.dry_run,
            solo    = args.solo,
            lote    = max(1, min(args.lote, 100)),
        ))
    except KeyboardInterrupt:
        print("\nCancelado.")
        sys.exit(1)
    sys.exit(codigo)


if __name__ == "__main__":
    main()
