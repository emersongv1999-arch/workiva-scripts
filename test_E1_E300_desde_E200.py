"""
test_E1_E300_desde_E200.py
==========================
SCRIPT DE PRUEBA — NO USAR EN PRODUCCIÓN

Llena la hoja "E1 Res Acumulado" del archivo E300_IND_03-2026
usando como fuente los saldos del archivo E200_IND_12-2025.

Ejecutar: python test_E1_E300_desde_E200.py
"""

import warnings, time, os, requests
from urllib3.exceptions import InsecureRequestWarning

warnings.filterwarnings("ignore", category=InsecureRequestWarning)

# ─── CREDENCIALES (hardcoded para prueba) ─────────────────────────────────────
os.environ["WORKIVA_CLIENT_ID"]     = "db2c551e-e18a-417e-8e52-d182716b8ef2"
os.environ["WORKIVA_CLIENT_SECRET"] = "wk_secret:oa2c:DzlUCmBQDv6raPxG09me"
os.environ["WORKIVA_WORKSPACE_ID"]  = "w_34913aadaa38420eabd7e4d341b78a1a"
# ──────────────────────────────────────────────────────────────────────────────

from workiva_client import get_session

# ─── CONFIGURACIÓN ────────────────────────────────────────────────────────────
WORKSPACE_ID  = "w_34913aadaa38420eabd7e4d341b78a1a"
WDESK_BASE    = "https://api.app.wdesk.com"

TARGET_CODE   = "E300"
SOURCE_CODE   = "E200"
TARGET_MM     = "03"
TARGET_YYYY   = "2026"
SOURCE_MM     = "12"
SOURCE_YYYY   = "2025"
TIPO          = "IND"
SHEET_NAME    = "K.- Tipos de deuda"
# ──────────────────────────────────────────────────────────────────────────────

session = get_session()
session.headers.update({"X-Version": "2022-01-01"})

_last_token = [time.time()]
def refresh_token():
    if time.time() - _last_token[0] > 480:
        ns = get_session()
        ns.headers.update({"X-Version": "2022-01-01"})
        for k, v in ns.headers.items():
            session.headers[k] = v
        _last_token[0] = time.time()
        print("  [Token renovado]")

# ─── HELPERS ──────────────────────────────────────────────────────────────────
def col_letter(idx):
    if idx < 26: return chr(65 + idx)
    return chr(64 + idx // 26) + chr(65 + idx % 26)

def load_all_files():
    all_files = {}
    url = WDESK_BASE + "/platform/v1/files?workspaceId=" + WORKSPACE_ID + "&limit=100"
    while url:
        r    = session.get(url, timeout=90)
        data = r.json()
        for f in data.get("data", []):
            all_files[f["name"]] = f["id"]
        url = data.get("@nextLink")
    return all_files

def find_file(code, mm, yyyy, all_files):
    """Busca archivo E{code}_IND_{MM}-{YYYY}_Base Notas ... con ambos separadores."""
    for sep in ["-", "_"]:
        for name, fid in all_files.items():
            if name.startswith(f"{code}_{TIPO}_{mm}{sep}{yyyy}_Base Notas"):
                return name, fid
    return None, None

def get_sheets(ss_id):
    result = {}
    url = WDESK_BASE + "/platform/v1/spreadsheets/" + ss_id + "/sheets"
    for _ in range(20):
        try:
            r    = session.get(url, timeout=90)
            data = r.json()
            for s in data.get("data", []):
                result[s["name"]] = s["id"]
            url = data.get("@nextLink")
            if not url:
                return result
        except Exception:
            time.sleep(5)
    return result

def read_sheet(ss_id, sheet_id):
    url = (WDESK_BASE + "/platform/v1/spreadsheets/" + ss_id + "/sheets/" + sheet_id
           + "/sheetdata?$fields=cells.calculatedValue,cells.value&$maxcellsperpage=50000")
    for _ in range(5):
        try:
            return session.get(url, timeout=120).json().get("data", {}).get("cells", [])
        except Exception:
            time.sleep(5)
    return []

def read_bases(ss_id, sheets):
    cells = read_sheet(ss_id, sheets["Bases"])
    result = {}
    row_map = {
        13: ("current_end",   "prior_end"),
        14: ("eerr_start",    "prior_eerr_start"),
        15: ("eerr_end",      "prior_eerr_end"),
        16: ("quarter_start", "prior_quarter_start"),
        17: ("prev_period_end", "prior_prev_period_end"),
    }
    for row_idx, (key_c, key_p) in row_map.items():
        if row_idx >= len(cells): continue
        row = cells[row_idx]
        for col_idx, key in [(3, key_c), (5, key_p)]:
            if col_idx < len(row):
                c  = row[col_idx]
                cv = c.get("calculatedValue", "") if isinstance(c, dict) else ""
                if cv: result[key] = str(cv)
    return result

def poll(location):
    url = location if location.startswith("http") else WDESK_BASE + location
    for _ in range(40):
        time.sleep(3)
        try:
            body = session.get(url, timeout=60).json()
            st   = body.get("status", body.get("data", {}).get("status", ""))
            if st == "completed": return True
            if st in ("failed", "error"): return False
        except Exception:
            pass
    return False

def put_col(ss_id, sid, col_idx, values, label=""):
    refresh_token()
    cl  = col_letter(col_idx)
    rng = f"{cl}1:{cl}{len(values)}"
    rp  = session.put(WDESK_BASE + "/platform/v1/spreadsheets/" + ss_id + "/sheets/" + sid
                      + "/values/" + rng,
                      json={"values": [[v] for v in values]}, timeout=120)
    if rp.status_code == 202:
        ok = poll(rp.headers.get("Location", ""))
        n  = sum(1 for v in values if v is not None)
        print(f"    {'OK' if ok else 'ERR'} col {cl}: {n} vals [{label}]")
        return ok
    print(f"    ERR HTTP {rp.status_code}: {rp.text[:60]}")
    return False

def is_formula(row, col):
    c = row[col] if col < len(row) else {}
    return str(c.get("value", "") if isinstance(c, dict) else "").startswith("=")

def get_cv(row, col):
    c = row[col] if col < len(row) else {}
    return c.get("calculatedValue") if isinstance(c, dict) else None

def find_bpc_col(src_cells, tgt_cells):
    for cells in (src_cells, tgt_cells):
        for row in cells[:8]:
            for j, c in enumerate(row):
                if isinstance(c, dict):
                    cv = str(c.get("calculatedValue", "")).lower()
                    if "agrupador" in cv:
                        return j
    return None

def build_row_mapping(tgt_cells, src_cells):
    diff = len(tgt_cells) - len(src_cells)
    if diff == 0:
        return list(range(len(tgt_cells)))

    bpc_col = find_bpc_col(src_cells, tgt_cells)

    def lbl(row): return str(get_cv(row, 1) or "").strip()
    def bpc(row):
        if bpc_col is None: return None
        b = get_cv(row, bpc_col)
        return str(b) if b is not None and str(b).strip() else None

    src_bpc = {}
    for i, r in enumerate(src_cells):
        b = bpc(r)
        if b: src_bpc.setdefault(b, i)
    src_lbl = {}
    for i, r in enumerate(src_cells):
        l = lbl(r)
        if l: src_lbl.setdefault(l, []).append(i)

    anchors = []
    used    = set()
    last_src = -1
    for ti, rt in enumerate(tgt_cells):
        si = None
        b  = bpc(rt)
        if b and b in src_bpc and src_bpc[b] > last_src and src_bpc[b] not in used:
            si = src_bpc[b]
        else:
            l = lbl(rt)
            if l and l in src_lbl:
                for cand in src_lbl[l]:
                    if cand > last_src and cand not in used:
                        si = cand; break
        if si is not None:
            anchors.append((ti, si))
            used.add(si); last_src = si

    mapping = [None] * len(tgt_cells)
    for ti, si in anchors:
        mapping[ti] = si

    for k in range(len(anchors) - 1):
        t0, s0 = anchors[k]
        t1, s1 = anchors[k + 1]
        for ti in range(t0 + 1, t1):
            if not lbl(tgt_cells[ti]):
                continue
            si = s0 + (ti - t0)
            if s0 < si < s1:
                mapping[ti] = si

    return mapping

def detect_comp_cols(cells, bases):
    """Detecta columnas con fechas comparativas en las primeras 8 filas."""
    PERIOD_PATTERNS = [
        ("prior_eerr_start",    "prior_eerr_end",        "eerr"),
        ("prior_eerr_start",    "prior_prev_period_end", "quarter_prev"),
        ("",                    "prior_end",             "balance"),
        ("eerr_start",          "prev_period_end",       "curr_subperiod"),
    ]
    col_texts = {}
    for row in cells[:8]:
        for j, c in enumerate(row):
            if isinstance(c, dict):
                for val in [str(c.get("calculatedValue", "")), str(c.get("value", ""))]:
                    if val and val not in ("None", ""):
                        col_texts.setdefault(j, []).append(val.lower())

    date_fields = {
        "prior_end":             bases.get("prior_end", ""),
        "prior_eerr_end":        bases.get("prior_eerr_end", ""),
        "prior_eerr_start":      bases.get("prior_eerr_start", ""),
        "prior_prev_period_end": bases.get("prior_prev_period_end", ""),
        "prev_period_end":       bases.get("prev_period_end", ""),
        "eerr_start":            bases.get("eerr_start", ""),
    }

    result   = {}
    curr_end = bases.get("current_end", "__X__")
    eerr_end = bases.get("eerr_end", "__X__")

    for col_idx, texts in col_texts.items():
        combined = " ".join(texts)
        if any(k in combined for k in [curr_end, eerr_end, "query", "sumif", "bpc", "actual"]):
            continue
        for skw, ekw, period_key in PERIOD_PATTERNS:
            sd = date_fields.get(skw, skw).lower()
            ed = date_fields.get(ekw, ekw).lower()
            if (not sd or sd in combined) and (ed and ed in combined):
                result[col_idx] = period_key
                break
    return result

def find_offset(tgt_cells, src_cells, date_kw):
    tgt_col = src_col = None
    kw = str(date_kw).lower() if date_kw else ""
    for row in tgt_cells[:8]:
        for j, c in enumerate(row):
            if isinstance(c, dict) and kw and kw in str(c.get("calculatedValue", "")).lower():
                if tgt_col is None: tgt_col = j
    for row in src_cells[:8]:
        for j, c in enumerate(row):
            if isinstance(c, dict) and kw and kw in str(c.get("calculatedValue", "")).lower():
                if src_col is None: src_col = j
    if tgt_col is not None and src_col is not None: return tgt_col - src_col
    return 2

def build_write_values(tgt_cells, src_cells, dest_col, src_col):
    row_map = build_row_mapping(tgt_cells, src_cells)
    bpc_col = find_bpc_col(src_cells, tgt_cells)

    def is_data_row(row):
        if str(get_cv(row, 1) or "").strip():
            return True
        if bpc_col is not None and get_cv(row, bpc_col) not in (None, ""):
            return True
        return False

    vals = []
    for i in range(len(tgt_cells)):
        row_t = tgt_cells[i] if i < len(tgt_cells) else []
        if is_formula(row_t, dest_col):
            vals.append(None); continue
        if not is_data_row(row_t):
            vals.append(None); continue
        src_row = row_map[i]
        if src_row is None: vals.append(None); continue
        sv = get_cv(src_cells[src_row], src_col)
        if isinstance(sv, (int, float)):
            vals.append(sv)
        else:
            vals.append(0)  # limpia celdas que en la fuente están vacías
    return vals

# ─── MAIN ─────────────────────────────────────────────────────────────────────
def main():
    print("=" * 60)
    print(f"PRUEBA: {SHEET_NAME}")
    print(f"  TARGET : {TARGET_CODE}_IND_{TARGET_MM}-{TARGET_YYYY}")
    print(f"  FUENTE : {SOURCE_CODE}_IND_{SOURCE_MM}-{SOURCE_YYYY}")
    print("=" * 60)

    refresh_token()
    print("\nCargando lista de archivos...")
    all_files = load_all_files()

    # Buscar archivos
    tgt_name, tgt_id = find_file(TARGET_CODE, TARGET_MM, TARGET_YYYY, all_files)
    src_name, src_id = find_file(SOURCE_CODE, SOURCE_MM, SOURCE_YYYY, all_files)

    if not tgt_id:
        print(f"✗ No se encontró archivo target: {TARGET_CODE}_IND_{TARGET_MM}-{TARGET_YYYY}_Base Notas ...")
        return
    if not src_id:
        print(f"✗ No se encontró archivo fuente: {SOURCE_CODE}_IND_{SOURCE_MM}-{SOURCE_YYYY}_Base Notas ...")
        return

    print(f"\n✓ Target : {tgt_name}  [{tgt_id}]")
    print(f"✓ Fuente : {src_name}  [{src_id}]")

    # Hojas
    print("\nLeyendo hojas del target...")
    tgt_sheets = get_sheets(tgt_id)
    print("Leyendo hojas del fuente...")
    src_sheets = get_sheets(src_id)

    if "Bases" not in tgt_sheets:
        print("✗ Target sin hoja 'Bases'"); return
    if SHEET_NAME not in tgt_sheets:
        print(f"✗ Hoja '{SHEET_NAME}' no encontrada en target"); return
    if SHEET_NAME not in src_sheets:
        print(f"✗ Hoja '{SHEET_NAME}' no encontrada en fuente"); return

    # Bases del target (para detectar fechas comparativas)
    bases = read_bases(tgt_id, tgt_sheets)
    print(f"\nPeríodo actual : {bases.get('current_end', '?')}")
    print(f"Comparativo    : {bases.get('prior_end', '?')}")

    # Leer celdas
    print(f"\nLeyendo '{SHEET_NAME}' del target...")
    tgt_cells = read_sheet(tgt_id, tgt_sheets[SHEET_NAME])
    print(f"Leyendo '{SHEET_NAME}' del fuente...")
    src_cells = read_sheet(src_id, src_sheets[SHEET_NAME])

    print(f"\nFilas target: {len(tgt_cells)} | Filas fuente: {len(src_cells)}")

    # Detectar columnas comparativas
    comp_cols = detect_comp_cols(tgt_cells, bases)
    if not comp_cols:
        print("✗ No se detectaron columnas comparativas en la hoja target.")
        return

    print(f"\nColumnas comparativas detectadas: {comp_cols}")

    sid_t = tgt_sheets[SHEET_NAME]
    prior_end = bases.get("prior_end", "")
    ok_total = 0

    for dest_col, period_key in comp_cols.items():
        if period_key != "balance":
            print(f"  Saltando col {col_letter(dest_col)} ({period_key}) — solo se llena 'balance' en prueba")
            continue

        print(f"\n  Procesando col {col_letter(dest_col)} → period_key='{period_key}'")
        offset  = find_offset(tgt_cells, src_cells, prior_end)
        src_col = dest_col - offset
        if src_col < 0:
            print(f"  ✗ src_col negativo (offset={offset}), saltando")
            continue

        print(f"  dest_col={dest_col}  src_col={src_col}  offset={offset}")
        write_vals = build_write_values(tgt_cells, src_cells, dest_col, src_col)
        n = sum(1 for v in write_vals if v is not None)
        print(f"  Valores a escribir: {n}")

        if n == 0:
            print("  ✗ Sin valores, saltando")
            continue

        confirm = input(f"\n  ¿Escribir {n} valores en col {col_letter(dest_col)} de '{tgt_name}'? (s/n): ").strip().lower()
        if confirm != "s":
            print("  Cancelado por el usuario.")
            continue

        ok = put_col(tgt_id, sid_t, dest_col, write_vals, period_key)
        if ok: ok_total += 1

    print(f"\n{'='*60}")
    print(f"LISTO — columnas escritas: {ok_total}")
    print("=" * 60)

if __name__ == "__main__":
    main()
