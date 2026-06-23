"""
llenar_comparativos (Rodrigo).py
==================================
Script para completar columnas de periodos en archivos "Base Notas"
de todas las sociedades de un periodo.

Credenciales: Rodrigo

USO:
    python llenar_comparativos_STANDALONE.py
"""

import re, time, warnings

import requests
from urllib3.exceptions import InsecureRequestWarning
warnings.filterwarnings("ignore", category=InsecureRequestWarning)

# ---------------------------------------------------------------------------
# CREDENCIALES — se leen de config_comparativos.json o se piden al usuario
# ---------------------------------------------------------------------------
WORKSPACE_ID = "w_34913aadaa38420eabd7e4d341b78a1a"   # igual para todos
TOKEN_URL    = "https://api.app.wdesk.com/iam/v1/oauth2/token"
WDESK_BASE   = "https://api.app.wdesk.com"
VERIFY_SSL   = False

CLIENT_ID     = "8eb96491-aee9-4a94-8ecd-1651efd1c3e5"
CLIENT_SECRET = "wk_secret:oa2c:A2tzB4CsbsKSA2jw4uph"

# ---------------------------------------------------------------------------
# AUTH
# ---------------------------------------------------------------------------
def get_token():
    resp = requests.post(
        TOKEN_URL,
        json={
            "grant_type":    "client_credentials",
            "client_id":     CLIENT_ID,
            "client_secret": CLIENT_SECRET,
        },
        headers={"Content-Type": "application/json"},
        timeout=30,
        verify=VERIFY_SSL,
    )
    resp.raise_for_status()
    return resp.json()["access_token"]

def get_session():
    token = get_token()
    s = requests.Session()
    s.headers.update({
        "Authorization": f"Bearer {token}",
        "Content-Type":  "application/json",
        "X-Version":     "2022-01-01",
    })
    s.verify = VERIFY_SSL
    return s

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

# ---------------------------------------------------------------------------
# CONFIGURACION
# ---------------------------------------------------------------------------
FULL_COPY_PAIRS = {
    "79.- Prestamos bancarios - desglose de monedas (b)":
    "78.- Prestamos bancarios - desglose de monedas (b)",
}

BLOCK_COPY_SHEETS = {
    "60.- Cuadro movimiento activo fijo":                          (11, 36, 51, 76),
    "62.- Propiedades, planta y equipos en arrendamiento, neto":   (31, 44, 46, 59),
}

SKIP_SHEETS = {
    "CP","Bases","Query BPC","Query HANA AF","Reporte en $",
    "Query - HANA - Deudores","A.- Activos PPT",
    "B.- Patrimonio y Pasivos PPT","C.- Estado de resultado por funcion PPT",
    "E1 Res Acumulado","F1 Cuadraje Hoja A.- Saldo Inicial de Caja",
}

TEST_MODE    = False
TEST_FILE_ID = "14d9f44f879640ca9efd1d14d7fd9393"
TEST_CODE    = "E215"
TEST_MM      = "09"
TEST_YYYY    = "2026"
TEST_SUFFIX  = "Base Notas CGECx"

# ---------------------------------------------------------------------------
# HELPERS
# ---------------------------------------------------------------------------
def col_letter(idx):
    if idx < 26: return chr(65+idx)
    return chr(64+idx//26)+chr(65+idx%26)

def get_sheets(ss_id):
    result = {}
    url = WDESK_BASE+"/platform/v1/spreadsheets/"+ss_id+"/sheets"
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
    url = (WDESK_BASE+"/platform/v1/spreadsheets/"+ss_id+"/sheets/"+sheet_id
           +"/sheetdata?$fields=cells.calculatedValue,cells.value&$maxcellsperpage=50000")
    for _ in range(5):
        try:
            return session.get(url, timeout=120).json().get("data",{}).get("cells",[])
        except Exception: time.sleep(5)
    return []

def poll(location):
    url = location if location.startswith("http") else WDESK_BASE+location
    for _ in range(40):
        time.sleep(3)
        try:
            body = session.get(url, timeout=60).json()
            st   = body.get("status", body.get("data",{}).get("status",""))
            if st == "completed": return True
            if st in ("failed","error"): return False
        except Exception: pass
    return False

def put_col(ss_id, sid, col_idx, values, label=""):
    refresh_token()
    cl  = col_letter(col_idx)
    rng = f"{cl}1:{cl}{len(values)}"
    rp  = session.put(WDESK_BASE+"/platform/v1/spreadsheets/"+ss_id+"/sheets/"+sid
                      +"/values/"+rng,
                      json={"values":[[v] for v in values]}, timeout=120)
    if rp.status_code == 202:
        ok = poll(rp.headers.get("Location",""))
        n  = sum(1 for v in values if v is not None)
        print(f"    {'OK' if ok else 'ERR'} col {cl}: {n} vals [{label}]")
        return ok
    print(f"    ERR HTTP {rp.status_code}: {rp.text[:60]}")
    return False

def put_col_range(ss_id, sid, col_idx, start_row, values, label=""):
    refresh_token()
    cl = col_letter(col_idx)
    r1 = start_row + 1
    r2 = r1 + len(values) - 1
    rng = f"{cl}{r1}:{cl}{r2}"
    rp  = session.put(WDESK_BASE+"/platform/v1/spreadsheets/"+ss_id+"/sheets/"+sid
                      +"/values/"+rng,
                      json={"values":[[v] for v in values]}, timeout=120)
    if rp.status_code == 202:
        ok = poll(rp.headers.get("Location",""))
        n  = sum(1 for v in values if v is not None)
        print(f"    {'OK' if ok else 'ERR'} col {cl}[{r1}:{r2}]: {n} vals [{label}]")
        return ok
    print(f"    ERR HTTP {rp.status_code}: {rp.text[:60]}")
    return False

def is_formula(row, col):
    c = row[col] if col < len(row) else {}
    return str(c.get("value","") if isinstance(c,dict) else "").startswith("=")

def get_cv(row, col):
    c = row[col] if col < len(row) else {}
    return c.get("calculatedValue") if isinstance(c,dict) else None

# ---------------------------------------------------------------------------
# PASO 1: Cargar archivos del workspace
# ---------------------------------------------------------------------------
def load_all_files():
    all_files = {}
    url = WDESK_BASE+"/platform/v1/files?workspaceId="+WORKSPACE_ID+"&limit=100"
    while url:
        r    = session.get(url, timeout=90)
        data = r.json()
        for f in data.get("data",[]):
            all_files[f["name"]] = f["id"]
        url = data.get("@nextLink")
    return all_files

# ---------------------------------------------------------------------------
# PASO 2: Encontrar archivos destino
# ---------------------------------------------------------------------------
def find_target_files(mm, yyyy, tipo, all_files):
    pattern = re.compile(rf"^E\d+_{tipo}_{mm}[-_]{yyyy}_Base Notas .+$")
    targets = []
    for name, fid in all_files.items():
        if pattern.match(name):
            parsed = re.match(rf"(E\d+)_({tipo})_(\d{{2}})[-_](\d{{4}})_(.*)", name)
            if parsed:
                targets.append({
                    "id":     fid,
                    "name":   name,
                    "code":   parsed.group(1),
                    "tipo":   parsed.group(2),
                    "mm":     parsed.group(3),
                    "yyyy":   parsed.group(4),
                    "suffix": parsed.group(5),
                })
    return sorted(targets, key=lambda x: x["code"])

# ---------------------------------------------------------------------------
# PASO 3: Leer Bases
# ---------------------------------------------------------------------------
def read_bases(target_id, sheets):
    cells = read_sheet(target_id, sheets["Bases"])
    result = {}
    row_map = {
        13: ("current_end","prior_end"),
        14: ("eerr_start","prior_eerr_start"),
        15: ("eerr_end","prior_eerr_end"),
        16: ("quarter_start","prior_quarter_start"),
        17: ("prev_period_end","prior_prev_period_end"),
    }
    for row_idx,(key_c,key_p) in row_map.items():
        if row_idx >= len(cells): continue
        row = cells[row_idx]
        for col_idx,key in [(3,key_c),(5,key_p)]:
            if col_idx < len(row):
                c  = row[col_idx]
                cv = c.get("calculatedValue","") if isinstance(c,dict) else ""
                if cv: result[key] = str(cv)
    return result

# ---------------------------------------------------------------------------
# PASO 4: Buscar archivos fuente
# ---------------------------------------------------------------------------
def date_to_mm_yyyy(date_str):
    parts = str(date_str).split("-")
    return (parts[1], parts[0]) if len(parts) >= 2 else (None, None)

def find_source_files(parsed, bases, all_files):
    code, suffix = parsed["code"], parsed["suffix"]
    tipo = parsed.get("tipo", "IND")
    mm_curr, yyyy_curr = parsed["mm"], parsed["yyyy"]

    def find(mm, yyyy, label):
        for sep in ["-", "_"]:
            name = f"{code}_{tipo}_{mm}{sep}{yyyy}_{suffix}"
            fid  = all_files.get(name)
            if fid:
                print(f"    OK: {name}")
                return fid
        print(f"    No encontrado: {code}_{tipo}_{mm}-{yyyy}_{suffix}")
        return None

    sources = {}
    mm_b,  yy_b  = date_to_mm_yyyy(bases.get("prior_end",""))
    mm_e,  yy_e  = date_to_mm_yyyy(bases.get("prior_eerr_end",""))
    mm_q,  yy_q  = date_to_mm_yyyy(bases.get("prior_prev_period_end",""))
    mm_pp, yy_pp = date_to_mm_yyyy(bases.get("prev_period_end",""))

    if mm_b:
        sources["balance"] = find(mm_b, yy_b, f"Balance DIC-{yy_b}")
    if mm_e and (mm_e,yy_e) != (mm_b,yy_b):
        sources["eerr"] = find(mm_e, yy_e, f"EERR {mm_e}-{yy_e}")
    else:
        sources["eerr"] = sources.get("balance")
    if mm_q and (mm_q,yy_q) not in [(mm_b,yy_b),(mm_e,yy_e)]:
        sources["quarter_prev"] = find(mm_q, yy_q, f"Q1-prev {mm_q}-{yy_q}")
    if mm_pp and yy_pp == yyyy_curr and mm_pp != mm_curr:
        sources["curr_subperiod"] = find(mm_pp, yy_pp, f"Sub-periodo actual {mm_pp}-{yy_pp}")

    return sources

# ---------------------------------------------------------------------------
# PASO 5: Cargar datos de fuentes
# ---------------------------------------------------------------------------
def load_sources(sources):
    loaded = {}
    for key, fid in sources.items():
        if not fid or fid in loaded: continue
        sheets = get_sheets(fid)
        loaded[fid] = {"sheets": sheets, "cells": {}}
        for sname, sid in sheets.items():
            loaded[fid]["cells"][sname] = read_sheet(fid, sid)
        print(f"    Cargado ({key}): {len(sheets)} hojas")
    return loaded

# ---------------------------------------------------------------------------
# PASO 6: Detectar columnas comparativas
# ---------------------------------------------------------------------------
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
            if isinstance(c,dict):
                for val in [str(c.get("calculatedValue","")), str(c.get("value",""))]:
                    if val and val not in ("None",""):
                        col_texts.setdefault(j,[]).append(val.lower())

    date_fields = {
        "prior_end":             bases.get("prior_end",""),
        "prior_eerr_end":        bases.get("prior_eerr_end",""),
        "prior_eerr_start":      bases.get("prior_eerr_start",""),
        "prior_prev_period_end": bases.get("prior_prev_period_end",""),
        "prev_period_end":       bases.get("prev_period_end",""),
        "eerr_start":            bases.get("eerr_start",""),
    }

    result = {}
    curr_end = bases.get("current_end","__X__")
    eerr_end = bases.get("eerr_end","__X__")

    for col_idx, texts in col_texts.items():
        combined = " ".join(texts)
        if any(k in combined for k in [curr_end, eerr_end, "query","sumif","bpc","actual"]):
            continue
        for skw, ekw, period_key in PERIOD_PATTERNS:
            sd = date_fields.get(skw, skw).lower()
            ed = date_fields.get(ekw, ekw).lower()
            if (not sd or sd in combined) and (ed and ed in combined):
                result[col_idx] = period_key
                break
    return result

def detect_vertical_blocks(cells, bases):
    curr  = bases.get("current_end", "")
    prior = bases.get("prior_end", "")
    if not curr or not prior:
        return None
    actual_rows = []
    comp_rows   = []
    for i, row in enumerate(cells):
        cv = str(get_cv(row, 1) or "").strip()
        if curr in cv:
            actual_rows.append(i)
        if prior in cv:
            comp_rows.append(i)
    if not actual_rows or not comp_rows:
        return None
    if comp_rows[0] <= actual_rows[0]:
        return None
    return {
        "actual_start": actual_rows[0],
        "comp_start":   comp_rows[0],
        "actual_rows":  actual_rows,
        "comp_rows":    comp_rows,
    }

def fill_vertical_sheet(target_id, sid_t, tgt_cells, src_cells, blocks, bases):
    prior = bases.get("prior_end", "")
    src_actual_rows = [i for i, row in enumerate(src_cells)
                       if prior in str(get_cv(row, 1) or "").strip()]
    if not src_actual_rows:
        print("    Bloque actual no encontrado en fuente")
        return 0

    tgt_comp_rows = blocks.get("comp_rows", [blocks["comp_start"]])
    n_blocks = min(len(src_actual_rows), len(tgt_comp_rows))
    write_map = {}

    for b in range(n_blocks):
        src_start = src_actual_rows[b]
        tgt_start = tgt_comp_rows[b]
        src_end   = src_actual_rows[b+1] if b+1 < len(src_actual_rows) else len(src_cells)
        tgt_end   = tgt_comp_rows[b+1]   if b+1 < len(tgt_comp_rows)   else len(tgt_cells)
        block_h   = min(src_end - src_start, tgt_end - tgt_start)

        for offset in range(block_h):
            si = src_start + offset
            ti = tgt_start + offset
            if si >= len(src_cells) or ti >= len(tgt_cells):
                break
            row_src = src_cells[si]
            row_tgt = tgt_cells[ti]
            for col in range(max(len(row_src), len(row_tgt))):
                if is_formula(row_tgt, col):
                    continue
                val = get_cv(row_src, col)
                if not isinstance(val, (int, float)):
                    continue
                write_map.setdefault(col, {})[ti] = val

    written = 0
    for col_idx, row_vals in sorted(write_map.items()):
        if not row_vals:
            continue
        min_row = min(row_vals)
        max_row = max(row_vals)
        values  = [row_vals.get(i) for i in range(min_row, max_row + 1)]
        if all(v is None for v in values):
            continue
        ok = put_col_range(target_id, sid_t, col_idx, min_row, values, "vertical")
        if ok:
            written += 1
        time.sleep(0.2)
    return written

# ---------------------------------------------------------------------------
# PASO 7: Offset y mapeo de filas
# ---------------------------------------------------------------------------
def find_offset(tgt_cells, src_cells, date_kw):
    tgt_col = src_col = None
    kw = str(date_kw).lower() if date_kw else ""
    for row in tgt_cells[:8]:
        for j, c in enumerate(row):
            if isinstance(c,dict) and kw and kw in str(c.get("calculatedValue","")).lower():
                if tgt_col is None: tgt_col = j
    for row in src_cells[:8]:
        for j, c in enumerate(row):
            if isinstance(c,dict) and kw and kw in str(c.get("calculatedValue","")).lower():
                if src_col is None: src_col = j
    if tgt_col is not None and src_col is not None: return tgt_col - src_col
    return 2

def find_bpc_col(src_cells, tgt_cells):
    for cells in (src_cells, tgt_cells):
        for row in cells[:8]:
            for j, c in enumerate(row):
                if isinstance(c, dict):
                    cv = str(c.get("calculatedValue","")).lower()
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
    used = set()
    last_src = -1
    for ti, rt in enumerate(tgt_cells):
        si = None
        b = bpc(rt)
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
        vals.append(sv if isinstance(sv,(int,float)) else None)
    return vals

# ---------------------------------------------------------------------------
# PASO 8: Copia de hojas especiales
# ---------------------------------------------------------------------------
def copy_detail_sheet(target_id, tgt_sid, src_cells, tgt_cells):
    cols = {j for row in src_cells for j,c in enumerate(row)
            if isinstance(c,dict) and not is_formula(row,j)
            and c.get("calculatedValue") not in (None,"",0)}
    ok = 0
    for col_idx in sorted(cols):
        w   = []
        has = False
        for i in range(len(tgt_cells)):
            rs = src_cells[i] if i < len(src_cells) else []
            rt = tgt_cells[i] if i < len(tgt_cells) else []
            if is_formula(rt, col_idx) or is_formula(rs, col_idx):
                w.append(None); continue
            cv = (rs[col_idx] if col_idx < len(rs) else {})
            cv = cv.get("calculatedValue") if isinstance(cv,dict) else None
            w.append(cv if cv not in (None,"") else None)
            if cv not in (None,"",0): has = True
        if not has: continue
        while len(w) < len(tgt_cells): w.append(None)
        cl = col_letter(col_idx)
        rp = session.put(WDESK_BASE+"/platform/v1/spreadsheets/"+target_id+"/sheets/"+tgt_sid
                         +"/values/"+f"{cl}1:{cl}{len(w)}",
                         json={"values":[[v] for v in w]}, timeout=120)
        if rp.status_code == 202 and poll(rp.headers.get("Location","")): ok += 1
        time.sleep(0.2)
    print(f"    {ok} columnas copiadas")

def copy_block_sheet(target_id, tgt_sid, src_cells, tgt_cells, src_start, src_end, tgt_start, tgt_end):
    block_h = min(src_end - src_start, tgt_end - tgt_start)
    write_map = {}
    for offset in range(block_h):
        si = src_start + offset
        ti = tgt_start + offset
        if si >= len(src_cells) or ti >= len(tgt_cells):
            break
        row_src = src_cells[si]
        row_tgt = tgt_cells[ti]
        for col in range(max(len(row_src), len(row_tgt))):
            if is_formula(row_tgt, col):
                continue
            val = get_cv(row_src, col)
            if not isinstance(val, (int, float)):
                continue
            write_map.setdefault(col, {})[ti] = val

    written = 0
    for col_idx, row_vals in sorted(write_map.items()):
        if not row_vals:
            continue
        min_row = min(row_vals)
        max_row = max(row_vals)
        values  = [row_vals.get(i) for i in range(min_row, max_row + 1)]
        if all(v is None for v in values):
            continue
        ok = put_col_range(target_id, tgt_sid, col_idx, min_row, values, "block")
        if ok:
            written += 1
        time.sleep(0.2)
    print(f"    {written} columnas escritas")

# ---------------------------------------------------------------------------
# PROCESAR UN ARCHIVO
# ---------------------------------------------------------------------------
def process_file(target_info, all_files):
    fid    = target_info["id"]
    name   = target_info["name"]
    parsed = target_info

    print(f"\n{'─'*60}")
    print(f"Procesando: {name}")
    print(f"{'─'*60}")

    tgt_sheets = get_sheets(fid)
    if "Bases" not in tgt_sheets:
        print("  Sin hoja Bases — saltando")
        return 0, 0

    bases = read_bases(fid, tgt_sheets)
    print(f"  Periodo: {bases.get('current_end','?')} | Compar: {bases.get('prior_end','?')}")

    sources = find_source_files(parsed, bases, all_files)
    print("  Cargando fuentes...")
    loaded = load_sources(sources)

    period_ref = {
        "balance":        bases.get("prior_end",""),
        "eerr":           bases.get("prior_eerr_end",""),
        "quarter_prev":   bases.get("prior_prev_period_end",""),
        "curr_subperiod": bases.get("prev_period_end",""),
    }

    def get_src(key):
        fid2 = sources.get(key)
        if not fid2 or fid2 not in loaded: return None, {}
        return fid2, loaded[fid2]["cells"]

    to_process = {n:sid for n,sid in tgt_sheets.items() if n not in SKIP_SHEETS}
    ok_total = err_total = 0

    for sname, sid_t in to_process.items():
        refresh_token()

        if sname in FULL_COPY_PAIRS:
            src_name = FULL_COPY_PAIRS[sname]
            _, cmap  = get_src("balance")
            src_c    = cmap.get(src_name, [])
            tgt_c    = read_sheet(fid, sid_t)
            print(f"  [COPIA] {sname}")
            if src_c: copy_detail_sheet(fid, sid_t, src_c, tgt_c)
            else:     print("    Fuente no encontrada")
            continue

        if sname in BLOCK_COPY_SHEETS:
            ss, se, ts, te = BLOCK_COPY_SHEETS[sname]
            _, cmap = get_src("balance")
            src_c   = cmap.get(sname, [])
            tgt_c   = read_sheet(fid, sid_t)
            print(f"  [BLOQUE] {sname} (src {ss+1}:{se} -> tgt {ts+1}:{te})")
            if src_c: copy_block_sheet(fid, sid_t, src_c, tgt_c, ss, se, ts, te)
            else:     print("    Fuente no encontrada")
            continue

        tgt_cells = read_sheet(fid, sid_t)
        if not tgt_cells: continue

        comp_cols = detect_comp_cols(tgt_cells, bases)

        if not comp_cols:
            blocks = detect_vertical_blocks(tgt_cells, bases)
            if blocks:
                _, cmap   = get_src("balance")
                src_cells = cmap.get(sname, [])
                if src_cells:
                    print(f"  [VERTICAL] {sname}")
                    n = fill_vertical_sheet(fid, sid_t, tgt_cells, src_cells, blocks, bases)
                    if n: ok_total += n
                    else: print("    Sin valores escritos")
            continue

        print(f"  [{sname}] — {len(comp_cols)} col(s)")

        for dest_col, period_key in comp_cols.items():
            if period_key == "balance" and parsed["mm"] != "03":
                continue

            _, cmap   = get_src(period_key)
            src_cells = cmap.get(sname, [])
            if not src_cells: continue

            offset  = find_offset(tgt_cells, src_cells, period_ref.get(period_key,""))
            src_col = dest_col - offset
            if src_col < 0: continue

            write_vals = build_write_values(tgt_cells, src_cells, dest_col, src_col)
            n = sum(1 for v in write_vals if v is not None)
            if n == 0: continue

            ok = put_col(fid, sid_t, dest_col, write_vals, period_key)
            if ok: ok_total += 1
            else:  err_total += 1
            time.sleep(0.3)

    print(f"  Resultado: OK={ok_total}  ERR={err_total}")
    return ok_total, err_total

# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------
def main():
    print("="*60)
    print("LLENADO DE COMPARATIVOS")
    print("="*60)

    if TEST_MODE:
        print(f"\n[MODO PRUEBA] Archivo: {TEST_FILE_ID}")
        refresh_token()
        all_files    = load_all_files()
        target_files = [{
            "id": TEST_FILE_ID, "name": f"(prueba) {TEST_CODE}_{TEST_MM}-{TEST_YYYY}",
            "code": TEST_CODE, "tipo": "IND", "mm": TEST_MM, "yyyy": TEST_YYYY, "suffix": TEST_SUFFIX,
        }]
    else:
        print()
        yyyy = input("Ano del periodo (ej: 2026): ").strip()
        mm   = input("Mes del periodo (ej: 06): ").strip().zfill(2)
        tipo = input("Tipo de archivo (IND o CONSO): ").strip().upper()

        if not yyyy.isdigit() or not mm.isdigit() or not (1 <= int(mm) <= 12):
            print("Ano o mes invalido.")
            input("\nEnter para salir...")
            return
        if tipo not in ("IND", "CONSO"):
            print("Tipo invalido. Debe ser IND o CONSO.")
            input("\nEnter para salir...")
            return

        print(f"\nBuscando archivos {tipo} para {mm}-{yyyy}...")
        refresh_token()

        all_files    = load_all_files()
        target_files = find_target_files(mm, yyyy, tipo, all_files)

    if not target_files:
        print("No se encontraron archivos para el periodo indicado.")
        input("\nEnter para salir...")
        return

    print(f"\nArchivos encontrados ({len(target_files)}):")
    for i, t in enumerate(target_files, 1):
        print(f"  {i}. {t['name']}")

    if not TEST_MODE:
        confirm = input("\nProcesar todos (s), elegir uno por uno (e), o cancelar (n)? ").strip().lower()
        if confirm == "n":
            print("Cancelado.")
            input("\nEnter para salir...")
            return
        elif confirm == "e":
            seleccionados = []
            for t in target_files:
                resp = input(f"  Procesar {t['name']}? (s/n): ").strip().lower()
                if resp == "s":
                    seleccionados.append(t)
            if not seleccionados:
                print("No se selecciono ningun archivo.")
                input("\nEnter para salir...")
                return
            target_files = seleccionados

    total_ok = total_err = 0
    for t in target_files:
        ok, err = process_file(t, all_files)
        total_ok  += ok
        total_err += err

    print(f"\n{'='*60}")
    print(f"RESUMEN FINAL: {len(target_files)} archivos procesados")
    print(f"  Operaciones OK:  {total_ok}")
    print(f"  Errores:         {total_err}")
    print("="*60)
    input("\nEnter para salir...")

if __name__ == "__main__":
    main()
