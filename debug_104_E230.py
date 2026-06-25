"""
debug_104_E230.py
=================
Script de diagnóstico: procesa SOLO la hoja "104.- Ingresos ordinarios"
del archivo E230_IND_09-2026 y muestra log detallado.
"""

import warnings, time, re, json
import requests
from urllib3.exceptions import InsecureRequestWarning
warnings.filterwarnings("ignore", category=InsecureRequestWarning)

# ── CREDENCIALES ───────────────────────────────────────────────────────────────
CLIENT_ID     = "db2c551e-e18a-417e-8e52-d182716b8ef2"
CLIENT_SECRET = "wk_secret:oa2c:DzlUCmBQDv6raPxG09me"
TOKEN_URL     = "https://api.app.wdesk.com/iam/v1/oauth2/token"
WORKSPACE_ID  = "w_34913aadaa38420eabd7e4d341b78a1a"
WDESK_BASE    = "https://api.app.wdesk.com"

TARGET_CODE   = "E230"
TARGET_TIPO   = "IND"
TARGET_MM     = "09"
TARGET_YYYY   = "2026"
TARGET_SHEET  = "104.- Ingresos ordinarios"

DRY_RUN = False   # True = solo muestra qué escribiría, no escribe nada
# ──────────────────────────────────────────────────────────────────────────────

def get_session():
    resp = requests.post(TOKEN_URL, data={
        "grant_type":    "client_credentials",
        "client_id":     CLIENT_ID,
        "client_secret": CLIENT_SECRET,
    }, verify=False, timeout=30)
    token = resp.json()["access_token"]
    s = requests.Session()
    s.headers.update({"Authorization": f"Bearer {token}", "X-Version": "2022-01-01"})
    s.verify = False
    return s

session = get_session()
_last_token = [time.time()]

def refresh_token():
    if time.time() - _last_token[0] > 480:
        ns = get_session()
        session.headers.update(ns.headers)
        _last_token[0] = time.time()
        print("  [Token renovado]")

def col_letter(idx):
    if idx < 26: return chr(65 + idx)
    return chr(64 + idx // 26) + chr(65 + idx % 26)

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

def poll(location):
    url = location if location.startswith("http") else WDESK_BASE + location
    for attempt in range(60):
        time.sleep(3)
        try:
            body = session.get(url, timeout=60).json()
            data = body.get("data", body)
            st   = data.get("status", body.get("status", ""))
            if st == "completed":
                return True
            if st in ("failed", "error"):
                msg = (data.get("error") or data.get("message") or
                       body.get("error") or body.get("message") or str(body)[:200])
                print(f"      [Workiva ERR] {msg}")
                return False
        except Exception as e:
            if attempt == 59:
                print(f"      [poll exception] {e}")
    return False

def unlock_sheet(ss_id, sid, sname):
    url = WDESK_BASE + "/platform/v1/spreadsheets/" + ss_id + "/sheets/" + sid + "/locks"
    try:
        r     = session.get(url, timeout=30)
        locks = r.json().get("data", [])
        if not locks:
            print(f"    [unlock] {sname}: sin locks")
            return
        for lk in locks:
            lid = lk.get("id") or lk.get("lockId")
            if not lid:
                continue
            dr = session.delete(WDESK_BASE + "/platform/v1/spreadsheets/" + ss_id
                                + "/sheets/" + sid + "/locks/" + lid, timeout=30)
            if dr.status_code == 202:
                poll(dr.headers.get("Location", ""))
        print(f"    [unlock] {sname}: {len(locks)} lock(s) eliminado(s)")
    except Exception as e:
        print(f"    [unlock] {sname}: error {e}")

def put_chunk(ss_id, sid, col_idx, row_start, values, label=""):
    cl  = col_letter(col_idx)
    r1  = row_start + 1
    r2  = r1 + len(values) - 1
    rng = f"{cl}{r1}:{cl}{r2}"
    if DRY_RUN:
        print(f"      [DRY] PUT {rng} = {values[:3]}{'...' if len(values)>3 else ''} [{label}]")
        return True
    rp = session.put(WDESK_BASE + "/platform/v1/spreadsheets/" + ss_id + "/sheets/" + sid
                     + "/values/" + rng,
                     json={"values": [[v] for v in values]}, timeout=120)
    if rp.status_code == 202:
        ok = poll(rp.headers.get("Location", ""))
        print(f"      {'OK' if ok else 'ERR'} PUT {rng} ({len(values)} vals) [{label}]")
        return ok
    print(f"      ERR HTTP {rp.status_code}: {rp.text[:120]}")
    return False

def put_col(ss_id, sid, col_idx, values, label=""):
    refresh_token()
    cl     = col_letter(col_idx)
    chunks = []
    i = 0
    while i < len(values):
        if values[i] is not None:
            j = i
            while j < len(values) and values[j] is not None:
                j += 1
            chunks.append((i, values[i:j]))
            i = j
        else:
            i += 1

    n = sum(1 for v in values if v is not None)
    if not chunks:
        print(f"    SKIP col {cl}: sin valores [{label}]")
        return True

    print(f"    col {cl}: {n} vals en {len(chunks)} chunk(s) [{label}]")
    ok_all = True
    for start, chunk in chunks:
        ok = put_chunk(ss_id, sid, col_idx, start, chunk, label)
        if not ok:
            ok_all = False
    print(f"    → {'OK' if ok_all else 'ERR'} col {cl} [{label}]")
    return ok_all

def is_formula(row, col):
    c = row[col] if col < len(row) else {}
    return str(c.get("value", "") if isinstance(c, dict) else "").startswith("=")

def get_cv(row, col):
    c = row[col] if col < len(row) else {}
    return c.get("calculatedValue") if isinstance(c, dict) else None

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

def read_bases(target_id, sheets):
    cells  = read_sheet(target_id, sheets["Bases"])
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

def date_to_mm_yyyy(date_str):
    parts = str(date_str).split("-")
    return (parts[1], parts[0]) if len(parts) >= 2 else (None, None)

PERIOD_PATTERNS = [
    ("prior_eerr_start",    "prior_eerr_end",        "eerr"),
    ("prior_eerr_start",    "prior_prev_period_end", "quarter_prev"),
    ("",                    "prior_end",             "balance"),
    ("eerr_start",          "prev_period_end",       "curr_subperiod"),
]

def detect_comp_cols(cells, bases):
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

    result     = {}
    curr_end   = bases.get("current_end", "__X__")
    eerr_end   = bases.get("eerr_end", "__X__")

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

def find_bpc_col(src_cells, tgt_cells):
    for cells in (src_cells, tgt_cells):
        for row in cells[:8]:
            for j, c in enumerate(row):
                if isinstance(c, dict) and "agrupador" in str(c.get("calculatedValue", "")).lower():
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

    anchors  = []
    used     = set()
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

def build_write_values(tgt_cells, src_cells, dest_col, src_col, verbose=False):
    row_map = build_row_mapping(tgt_cells, src_cells)
    bpc_col = find_bpc_col(src_cells, tgt_cells)

    def is_data_row(row):
        if str(get_cv(row, 1) or "").strip():
            return True
        if bpc_col is not None and get_cv(row, bpc_col) not in (None, ""):
            return True
        return False

    vals     = []
    unmapped = []
    for i, row_t in enumerate(tgt_cells):
        if is_formula(row_t, dest_col):
            vals.append(None); continue
        if not is_data_row(row_t):
            vals.append(None); continue
        src_row = row_map[i]
        if src_row is None:
            b  = get_cv(row_t, bpc_col) if bpc_col is not None else None
            lb = str(get_cv(row_t, 1) or "").strip()
            tag = str(b) if b is not None else lb[:40]
            if tag:
                unmapped.append(f"fila {i+1}:{tag}")
            vals.append(None); continue
        sv = get_cv(src_cells[src_row], src_col)
        if verbose and isinstance(sv, (int, float)) and sv != 0:
            b  = get_cv(row_t, bpc_col) if bpc_col is not None else None
            print(f"      fila {i+1} agrup={b} → src_fila={src_row+1} val={sv}")
        vals.append(sv if isinstance(sv, (int, float)) else None)

    if unmapped:
        print(f"      [sin mapeo] {', '.join(unmapped[:15])}"
              + (" ..." if len(unmapped) > 15 else ""))
    return vals

# ──────────────────────────────────────────────────────────────────────────────
def main():
    print("=" * 60)
    print(f"DEBUG: {TARGET_SHEET}")
    print(f"Target: {TARGET_CODE}_{TARGET_TIPO}_{TARGET_MM}-{TARGET_YYYY}")
    print("=" * 60)

    print("\nCargando lista de archivos...")
    all_files = load_all_files()
    print(f"  {len(all_files)} archivos en workspace")

    # Buscar archivo target
    pattern = re.compile(
        rf"^{TARGET_CODE}_{TARGET_TIPO}_{TARGET_MM}[-_]{TARGET_YYYY}_Base Notas .+$"
    )
    target = None
    for name, fid in all_files.items():
        if pattern.match(name):
            target = {"id": fid, "name": name,
                      "code": TARGET_CODE, "tipo": TARGET_TIPO,
                      "mm": TARGET_MM, "yyyy": TARGET_YYYY}
            break

    if not target:
        print(f"  ✗ No se encontró {TARGET_CODE}_{TARGET_TIPO}_{TARGET_MM}-{TARGET_YYYY}_Base Notas ...")
        return

    print(f"  ✓ Encontrado: {target['name']}")

    # Hojas del target
    print("\nCargando hojas del target...")
    tgt_sheets = get_sheets(target["id"])
    print(f"  {len(tgt_sheets)} hojas")

    if TARGET_SHEET not in tgt_sheets:
        print(f"  ✗ Hoja '{TARGET_SHEET}' no encontrada")
        print("  Hojas disponibles con '104':", [k for k in tgt_sheets if "104" in k])
        return

    # Bases
    if "Bases" not in tgt_sheets:
        print("  ✗ Sin hoja Bases")
        return

    bases = read_bases(target["id"], tgt_sheets)
    print(f"\nBases:")
    for k, v in bases.items():
        print(f"  {k}: {v}")

    # Leer hoja target
    print(f"\nLeyendo '{TARGET_SHEET}' del target...")
    tgt_cells = read_sheet(target["id"], tgt_sheets[TARGET_SHEET])
    print(f"  {len(tgt_cells)} filas")

    # Detectar columnas comparativas
    comp_cols = detect_comp_cols(tgt_cells, bases)
    print(f"\nColumnas comparativas detectadas: {len(comp_cols)}")
    for col_idx, period_key in comp_cols.items():
        print(f"  col {col_letter(col_idx)} (idx {col_idx}) → {period_key}")

    if not comp_cols:
        print("  ✗ No se detectaron columnas comparativas")
        return

    # Buscar archivos fuente
    suffix = target["name"].split(f"{TARGET_MM}-{TARGET_YYYY}_", 1)[-1]

    def find_src(mm, yy):
        for sep in ["-", "_"]:
            name = f"{TARGET_CODE}_{TARGET_TIPO}_{mm}{sep}{yy}_{suffix}"
            fid  = all_files.get(name)
            if fid:
                print(f"    ✓ {name}")
                return fid
        print(f"    ✗ no encontrado: {TARGET_CODE}_{TARGET_TIPO}_{mm}-{yy}_{suffix}")
        return None

    period_ref = {
        "balance":        bases.get("prior_end", ""),
        "eerr":           bases.get("prior_eerr_end", ""),
        "quarter_prev":   bases.get("prior_prev_period_end", ""),
        "curr_subperiod": bases.get("prev_period_end", ""),
    }

    mm_b,  yy_b  = date_to_mm_yyyy(bases.get("prior_end", ""))
    mm_e,  yy_e  = date_to_mm_yyyy(bases.get("prior_eerr_end", ""))
    mm_q,  yy_q  = date_to_mm_yyyy(bases.get("prior_prev_period_end", ""))
    mm_pp, yy_pp = date_to_mm_yyyy(bases.get("prev_period_end", ""))

    print("\nBuscando fuentes:")
    sources = {}
    if mm_b:
        sources["balance"] = find_src(mm_b, yy_b)
    if mm_e and (mm_e, yy_e) != (mm_b, yy_b):
        sources["eerr"] = find_src(mm_e, yy_e)
    else:
        sources["eerr"] = sources.get("balance")
    if mm_q and (mm_q, yy_q) not in [(mm_b, yy_b), (mm_e, yy_e)]:
        sources["quarter_prev"] = find_src(mm_q, yy_q)
    if mm_pp and yy_pp == TARGET_YYYY and mm_pp != TARGET_MM:
        sources["curr_subperiod"] = find_src(mm_pp, yy_pp)

    # Cargar hojas fuente para TARGET_SHEET
    src_cells = {}
    loaded_fids = {}
    for key, fid in sources.items():
        if not fid or fid in loaded_fids:
            if fid in loaded_fids:
                src_cells[key] = loaded_fids[fid]
            continue
        print(f"\nCargando hojas de fuente [{key}]...")
        sheets = get_sheets(fid)
        print(f"  {len(sheets)} hojas totales")
        if TARGET_SHEET in sheets:
            cells = read_sheet(fid, sheets[TARGET_SHEET])
            print(f"  '{TARGET_SHEET}': {len(cells)} filas")
            loaded_fids[fid] = cells
            src_cells[key] = cells
        else:
            print(f"  ✗ '{TARGET_SHEET}' no encontrada en fuente [{key}]")
            src_cells[key] = []

    # Desbloquear la hoja antes de escribir
    print(f"\n{'─'*60}")
    print("DESBLOQUEANDO HOJA:")
    sid_t = tgt_sheets[TARGET_SHEET]
    unlock_sheet(target["id"], sid_t, TARGET_SHEET)

    # Procesar cada columna comparativa
    print(f"\n{'─'*60}")
    print("PROCESANDO COLUMNAS:")

    for dest_col, period_key in comp_cols.items():
        cl = col_letter(dest_col)
        print(f"\n  col {cl} [{period_key}]  (prior_end: {period_ref.get(period_key, '?')})")

        if period_key == "balance" and TARGET_MM != "03":
            print("    SKIP: balance solo se llena en marzo")
            continue

        sc = src_cells.get(period_key, [])
        if not sc:
            print("    SKIP: fuente vacía")
            continue

        # Detectar offset
        kw = period_ref.get(period_key, "").lower()
        tgt_col = src_col_found = None
        for row in tgt_cells[:8]:
            for j, c in enumerate(row):
                if isinstance(c, dict) and kw and kw in str(c.get("calculatedValue", "")).lower():
                    if tgt_col is None: tgt_col = j
        for row in sc[:8]:
            for j, c in enumerate(row):
                if isinstance(c, dict) and kw and kw in str(c.get("calculatedValue", "")).lower():
                    if src_col_found is None: src_col_found = j
        if tgt_col is not None and src_col_found is not None:
            offset  = tgt_col - src_col_found
        else:
            offset = 2
        src_col = dest_col - offset
        print(f"    offset={offset}  src_col={col_letter(src_col) if src_col>=0 else '?'}(idx {src_col})")

        if src_col < 0:
            print("    SKIP: src_col negativo")
            continue

        print(f"    Comparando filas (tgt={len(tgt_cells)}, src={len(sc)})...")
        write_vals = build_write_values(tgt_cells, sc, dest_col, src_col, verbose=True)
        n = sum(1 for v in write_vals if v is not None)
        print(f"    → {n} valores a escribir")

        if n == 0:
            print("    SKIP: nada que escribir")
            continue

        put_col(target["id"], sid_t, dest_col, write_vals, period_key)
        time.sleep(0.5)

    print(f"\n{'='*60}")
    print("FIN")

if __name__ == "__main__":
    main()
