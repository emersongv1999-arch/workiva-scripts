#!/usr/bin/env python3
"""
llenado_comparativosV2.py
=========================
Llena los comparativos de TODOS los archivos IND de un período en Workiva,
paginando correctamente todas las hojas de cada archivo (sin límite de 20).

Usa workiva_mcp.py como módulo directo (no vía protocolo MCP) para evitar
timeouts del host. La escritura es idempotente por columna, así que
re-ejecutar retoma solo lo pendiente.

USO:
    python llenado_comparativosV2.py --mes 09 --anio 2026
    python llenado_comparativosV2.py --mes 09 --anio 2026 --dry-run   # simulación, no escribe
    python llenado_comparativosV2.py --mes 09 --anio 2026 --solo E215 # solo ese código
    python llenado_comparativosV2.py --mes 03 --anio 2026 --lote 50   # hojas por lote

REQUISITOS:
    - workiva_mcp.py en la misma carpeta
    - .env con las credenciales en la misma carpeta

SALIDA: exit code 0 = todo OK, 2 = algún archivo incompleto/con error, 1 = error fatal.
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


MES_POR_TRIMESTRE = {
    "Q1": "03", "Q2": "06", "Q3": "09", "Q4": "12",
    "1": "03", "2": "06", "3": "09", "4": "12",
    "03": "03", "06": "06", "09": "09", "12": "12",
}


# ── Modo interactivo (doble clic en Windows) ──────────────────────────────────

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
    """Menú interactivo para cuando se ejecuta sin argumentos (doble clic)."""
    print("=== Llenado de Comparativos V2 — modo interactivo ===\n")
    mes_raw = _pedir(
        "Trimestre o mes  (Q1/Q2/Q3/Q4  o  03/06/09/12): ",
        lambda v: v.upper() in MES_POR_TRIMESTRE,
    )
    mes = MES_POR_TRIMESTRE[mes_raw.upper()]
    anio = _pedir(
        "Año (ej 2026): ",
        lambda v: re.fullmatch(r"\d{4}", v) is not None,
    )
    modo = _pedir(
        "Modo  [1] DRY-RUN (simulación)  [2] ESCRITURA REAL  (Enter = DRY-RUN): ",
        lambda v: v in ("1", "2"),
        default="1",
    )
    dry_run = (modo == "1")
    solo_raw = _pedir(
        "Sociedad específica (ej E215) o Enter para TODAS: ",
        lambda v: True,
        default="",
    )
    solo = solo_raw.strip() or None
    lote_raw = _pedir(
        "Hojas por lote (Enter = 50): ",
        lambda v: v.isdigit() and 1 <= int(v) <= 100,
        default="50",
    )
    lote = int(lote_raw)
    print()
    return mes, anio, dry_run, solo, lote


# ── Cargar workiva_mcp desde la misma carpeta ────────────────────────────────

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


# ── Procesar un archivo completo (con paginación) ────────────────────────────

async def _procesar_archivo(
    mcp,
    fid: str,
    nombre: str,
    dry_run: bool,
    lote: int,
) -> dict:
    """
    Pagina todas las hojas del archivo llamando fill_comparatives en bucle
    hasta que has_more sea False. Retorna un dict de resumen.
    """
    offset = 0
    total_cols   = 0
    total_hojas  = 0
    candidatas   = "?"
    encabezado   = False

    while True:
        mcp._wk._client = None  # cliente fresco en cada lote
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

        # workiva_mcp solo permite escritura real en mes 03 (regla 11).
        # Para otros meses devuelve "message" y no incluye sheet_offset/batch_size.
        if "message" in r and "sheet_offset" not in r:
            return {"estado": "warning", "detalle": r["message"]}

        # Imprimir encabezado una sola vez (primer lote)
        if not encabezado:
            candidatas = r.get("total_candidate_sheets", "?")
            print(f"  Período actual : {r.get('current_end', '?')}")
            print(f"  Período comp.  : {r.get('prior_end', '?')}")
            print(f"  Fuente         : {r.get('source_balance', '?')}")
            print(f"  Hojas candidatas: {candidatas}"
                  f" (excluidos {r.get('skipped_desglose_sociedad', 0)} desgloses por sociedad)")
            encabezado = True

        hojas_lote = len(r.get("sheets_processed", []))
        cols_lote  = r.get("total_cols_written", 0)
        total_hojas += hojas_lote
        total_cols  += cols_lote

        accion = "simuladas" if dry_run else "escritas"
        print(f"  lote offset {r.get('sheet_offset', offset):>3}: {r.get('batch_size', hojas_lote)} hojas | "
              f"{cols_lote} columnas {accion}")

        # Hojas o columnas con error en este lote
        fallidas  = r.get("sheets_failed", [])
        cols_fail = r.get("total_cols_failed", 0)
        if fallidas or cols_fail:
            print(f"  ⚠ Errores en lote: {len(fallidas)} hojas, {cols_fail} columnas fallidas")
            for f in fallidas[:5]:
                print(f"      · {f.get('sheet')}: {f.get('error')}")
            # Reportar incompleto; el llamador decidirá si reintenta
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
    print(f"  Llenado Comparativos V2 — {mes}-{anio}")
    print(f"  Modo  : {'DRY-RUN (simulación, no escribe nada)' if dry_run else 'ESCRITURA REAL'}")
    print(f"  Lote  : {lote} hojas por llamada")
    if solo:
        print(f"  Filtro: solo {solo}")
    print("=" * 65)

    # Workiva solo permite escritura de comparativo de balance en mes 03.
    # Para otros meses advertir, pero continuar (el conector lo bloqueará por archivo).
    if mes != "03" and not dry_run:
        print(f"\n  AVISO: workiva_mcp solo escribe comparativos de balance en archivos de")
        print(f"  mes 03. El mes seleccionado es {mes}, por lo que la escritura será")
        print(f"  bloqueada por el conector. Usa --dry-run para validar sin restricción de mes.")
        print()

    # 1. Descubrir archivos IND del período
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

    # 2. Procesar cada archivo con reintentos
    MAX_INTENTOS = 5
    resumen      = []
    t_inicio     = time.time()

    for i, archivo in enumerate(archivos, 1):
        nombre = archivo["name"]
        fid    = archivo["id"]
        print(f"\n{'─' * 65}")
        print(f"[{i}/{len(archivos)}] {nombre}")
        print(f"{'─' * 65}")

        completado      = False
        ultimo_resultado = None

        for intento in range(1, MAX_INTENTOS + 1):
            if intento > 1:
                espera = min(5 * 2 ** (intento - 2), 60)  # 5, 10, 20, 40 s
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
                # Dejar que el loop de reintentos retome desde offset=0
                # (idempotencia garantiza que solo se procesan columnas pendientes)
                print(f"  Lote con errores — se reintentará el archivo completo.")
                continue

            # ok o sin_cambios
            accion = "simuladas" if dry_run else "escritas"
            print(f"  {'✓' if resultado['estado'] == 'ok' else '~'} "
                  f"{resultado['hojas']} hojas | {resultado['columnas']} columnas {accion}")
            resumen.append({"archivo": nombre, **resultado})
            completado = True
            break

        if not completado:
            if ultimo_resultado and ultimo_resultado.get("columnas", 0) > 0:
                print(f"  ⚠ Quedó incompleto tras {MAX_INTENTOS} intentos "
                      "(lo escrito persiste; re-ejecutar retoma lo pendiente).")
                resumen.append({
                    "archivo": nombre,
                    "estado":  "incompleto",
                    "detalle": ultimo_resultado.get("detalle", ""),
                    "hojas":   ultimo_resultado.get("hojas", 0),
                    "columnas": ultimo_resultado.get("columnas", 0),
                })
            else:
                print(f"  ✗ No se pudo procesar tras {MAX_INTENTOS} intentos.")
                resumen.append({
                    "archivo": nombre,
                    "estado":  "error",
                    "detalle": f"Falló tras {MAX_INTENTOS} intentos sin resultado válido",
                })

    # 3. Resumen final
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
        print("  Para aplicar los cambios, corre sin --dry-run.")

    tiene_problemas = bool(incompl or errores)
    return 2 if tiene_problemas else 0


# ── Entry point ───────────────────────────────────────────────────────────────

def main():
    # Sin argumentos → modo interactivo (doble clic en Windows)
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
        description="Llena comparativos de todos los IND de un período (paginación completa)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Ej: python llenado_comparativosV2.py --mes 03 --anio 2026\n"
            "    python llenado_comparativosV2.py --mes 09 --anio 2026 --dry-run\n"
            "    python llenado_comparativosV2.py --mes 06 --anio 2026 --solo E215"
        ),
    )
    parser.add_argument("--mes",     required=True, help="Mes en 2 dígitos (ej: 03, 09, 12)")
    parser.add_argument("--anio",    required=True, help="Año (ej: 2026 o 26)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Simulación: compara pero no escribe nada en Workiva")
    parser.add_argument("--solo",    default=None,
                        help="Procesar solo este código de sociedad (ej: E215 o 215)")
    parser.add_argument("--lote",    type=int, default=50,
                        help="Hojas por lote/llamada (default 50, máx 100)")
    args = parser.parse_args()

    anio = args.anio.strip()
    if len(anio) == 2:
        anio = "20" + anio

    lote = max(1, min(args.lote, 100))

    try:
        codigo = asyncio.run(run(
            mes     = args.mes.strip().zfill(2),
            anio    = anio,
            dry_run = args.dry_run,
            solo    = args.solo,
            lote    = lote,
        ))
    except KeyboardInterrupt:
        print("\nCancelado.")
        sys.exit(1)
    sys.exit(codigo)


if __name__ == "__main__":
    main()
