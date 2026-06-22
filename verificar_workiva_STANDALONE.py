# verificar_workiva_STANDALONE.py
# NO necesita instalar ninguna libreria. Solo Python puro (stdlib).
# Verifica sumas en tablas de archivos Word (.docx) descargados desde Workiva
# y escribe los hallazgos directamente en la spreadsheet "verificacion de sumas".
# Logica de verificacion basada en verificar_sumas.py (motor PDF depurado).

import json, re, ssl, time, urllib.request, urllib.error, zipfile
import xml.etree.ElementTree as ET
from pathlib import Path
from collections import defaultdict

# ---------------------------------------------------------------------------
# CREDENCIALES
# ---------------------------------------------------------------------------
CLIENT_ID     = "db2c551e-e18a-417e-8e52-d182716b8ef2"
CLIENT_SECRET = "wk_secret:oa2c:DzlUCmBQDv6raPxG09me"
WORKSPACE_ID  = "w_34913aadaa38420eabd7e4d341b78a1a"

TOKEN_URL  = "https://api.app.wdesk.com/iam/v1/oauth2/token"
WDESK_BASE = "https://api.app.wdesk.com"

SS_VERIF_NAME = "verificacion de sumas"
DOCX_DIR      = Path("docx_tmp_verif")
SS_CACHE      = Path(__file__).parent / ".ss_verif_id"

MESES = {
    "1":"01","01":"01","enero":"01","2":"02","02":"02","febrero":"02",
    "3":"03","03":"03","marzo":"03","4":"04","04":"04","abril":"04",
    "5":"05","05":"05","mayo":"05","6":"06","06":"06","junio":"06",
    "7":"07","07":"07","julio":"07","8":"08","08":"08","agosto":"08",
    "9":"09","09":"09","septiembre":"09","10":"10","octubre":"10",
    "11":"11","noviembre":"11","12":"12","diciembre":"12",
}

UMBRAL = 1000  # diferencias <= UMBRAL M$ -> hallazgo prioritario

# ---------------------------------------------------------------------------
# SSL (red corporativa)
# ---------------------------------------------------------------------------
CTX = ssl.create_default_context()
CTX.check_hostname = False
CTX.verify_mode    = ssl.CERT_NONE

# ---------------------------------------------------------------------------
# HTTP helpers
# ---------------------------------------------------------------------------
def http(method, url, headers=None, body=None, timeout=60):
    data = json.dumps(body).encode() if body is not None else None
    h = {
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Python/3.13",
        **(headers or {}),
    }
    req = urllib.request.Request(url, data=data, headers=h, method=method)
    last_err = None
    for attempt in range(4):
        try:
            with urllib.request.urlopen(req, context=CTX, timeout=timeout) as resp:
                raw = resp.read()
                return resp.status, json.loads(raw) if raw else {}
        except urllib.error.HTTPError as e:
            raw = e.read()
            return e.code, json.loads(raw) if raw else {}
        except Exception as e:
            last_err = e
            time.sleep(2 ** attempt)
    raise last_err

def http_bytes(url, headers=None, timeout=120):
    req = urllib.request.Request(url, headers=headers or {}, method="GET")
    last_err = None
    for attempt in range(4):
        try:
            with urllib.request.urlopen(req, context=CTX, timeout=timeout) as resp:
                return resp.read()
        except Exception as e:
            last_err = e
            time.sleep(2 ** attempt)
    raise last_err

# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------
_token = None
_token_expiry = 0

def get_token():
    global _token, _token_expiry
    if _token and time.time() < _token_expiry:
        return _token
    status, data = http("POST", TOKEN_URL, body={
        "grant_type":    "client_credentials",
        "client_id":     CLIENT_ID,
        "client_secret": CLIENT_SECRET,
    })
    if status != 200:
        raise RuntimeError(f"Auth fallida: {status} {data}")
    _token = data["access_token"]
    _token_expiry = time.time() + data.get("expires_in", 3600) - 60
    return _token

def api_get(path, params=""):
    url = f"{WDESK_BASE}{path}{params}" if path.startswith("/") else path
    token = get_token()
    status, data = http("GET", url, headers={
        "Authorization": f"Bearer {token}",
        "X-Version": "2022-01-01",
    })
    if status not in (200,):
        raise RuntimeError(f"GET {path} -> {status}: {data}")
    return data

def api_post(path, body):
    last_err = None
    for attempt in range(4):
        token = get_token()
        req = urllib.request.Request(
            f"{WDESK_BASE}{path}",
            data=json.dumps(body).encode(),
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Python/3.13",
                "X-Version": "2022-01-01",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, context=CTX, timeout=60) as resp:
                return resp.status, {}, resp.getheader("Location", "")
        except urllib.error.HTTPError as e:
            return e.code, json.loads(e.read() or b"{}"), e.headers.get("Location", "")
        except Exception as e:
            last_err = e
            time.sleep(2 ** attempt)
    raise last_err

def api_put(path, body):
    last_err = None
    for attempt in range(4):
        token = get_token()
        req = urllib.request.Request(
            f"{WDESK_BASE}{path}",
            data=json.dumps(body).encode(),
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Python/3.13",
                "X-Version": "2022-01-01",
            },
            method="PUT",
        )
        try:
            with urllib.request.urlopen(req, context=CTX, timeout=90) as resp:
                return resp.status, {}, resp.getheader("Location", "")
        except urllib.error.HTTPError as e:
            return e.code, json.loads(e.read() or b"{}"), e.headers.get("Location", "")
        except Exception as e:
            last_err = e
            time.sleep(2 ** attempt)
    raise last_err

def poll_operation(location, max_tries=40, wait=3):
    token = get_token()
    for _ in range(max_tries):
        time.sleep(wait)
        status, data = http("GET", location, headers={
            "Authorization": f"Bearer {token}",
            "X-Version": "2022-01-01",
        })
        s = data.get("status", "")
        if s == "completed":
            return data
        if "fail" in s or "error" in s:
            raise RuntimeError(f"Operacion fallida: {data}")
    raise RuntimeError("Timeout esperando operacion")

# ---------------------------------------------------------------------------
# Workiva: buscar documentos
# ---------------------------------------------------------------------------
def buscar_documentos(mes, anio, idioma):
    print("  Descargando catalogo...", end=" ", flush=True)
    patron = f"EE.FF {mes}-{anio}"
    docs = []
    url = "/platform/v1/documents?$top=100"
    while url:
        data = api_get(url)
        for d in data.get("value", data.get("data", [])):
            nombre = d.get("name", "")
            if patron not in nombre:
                continue
            if idioma != "AMBOS":
                if f"({idioma})" not in nombre:
                    continue
            docs.append({"id": d["id"], "nombre": nombre})
        url = data.get("@nextLink") or data.get("nextLink") or None
    docs.sort(key=lambda x: x["nombre"])
    print(f"{len(docs)} documentos encontrados.")
    return docs

def seleccionar_docs(docs):
    print("\n  Seleccionar todos? [TODOS / NINGUNO / uno por uno]: ", end="")
    modo = input().strip().upper()
    if modo == "TODOS":
        return docs
    if modo == "NINGUNO":
        return []
    sel = []
    for i, d in enumerate(docs, 1):
        print(f"  {i:>3}. {d['nombre']} [S/N]: ", end="")
        if input().strip().upper() == "S":
            sel.append(d)
    return sel

# ---------------------------------------------------------------------------
# Workiva: spreadsheet verificacion
# ---------------------------------------------------------------------------
def buscar_spreadsheet_verif():
    if SS_CACHE.exists():
        cached = SS_CACHE.read_text().strip()
        if cached:
            print(f"  Spreadsheet (cache): {cached}")
            return cached
    print("  Buscando spreadsheet (puede tardar)...", end=" ", flush=True)
    url = "/platform/v1/spreadsheets?$top=100"
    while url:
        if url.startswith("/"):
            data = api_get(url)
        else:
            _, data = http("GET", url, headers={
                "Authorization": f"Bearer {get_token()}",
                "X-Version": "2022-01-01",
            })
        for ss in data.get("value", data.get("data", [])):
            if SS_VERIF_NAME in ss.get("name", "").lower():
                sid = ss["id"]
                print(f"encontrado: '{ss['name']}' [{sid}]")
                SS_CACHE.write_text(sid)
                return sid
        url = data.get("@nextLink") or data.get("nextLink") or None
    print("NO encontrado.")
    return None

def obtener_o_crear_hoja(ss_id, nombre_hoja):
    data = api_get(f"/platform/v1/spreadsheets/{ss_id}/sheets?$top=50")
    for s in data.get("value", data.get("data", [])):
        if s.get("name", "").lower() == nombre_hoja.lower():
            return s["id"], False
    status, resp, _ = api_post(f"/platform/v1/spreadsheets/{ss_id}/sheets", {"name": nombre_hoja})
    if status not in (200, 201, 202):
        raise RuntimeError(f"No se pudo crear hoja: {status}")
    sid = resp.get("id") or resp.get("data", {}).get("id")
    return sid, True

def contar_filas(ss_id, sheet_id):
    try:
        data = api_get(f"/platform/v1/spreadsheets/{ss_id}/sheets/{sheet_id}/values/A1:A2000")
        rows = data.get("values", [])
        last = 0
        for i, row in enumerate(rows, 1):
            if row and any(str(c).strip() for c in row):
                last = i
        return last
    except Exception:
        return 0

def put_range(ss_id, sheet_id, rango, values):
    status, _, location = api_put(
        f"/platform/v1/spreadsheets/{ss_id}/sheets/{sheet_id}/values/{rango}",
        {"values": values}
    )
    if status == 202 and location:
        poll_operation(location, wait=2)

# ---------------------------------------------------------------------------
# Exportar .docx desde Workiva
# ---------------------------------------------------------------------------
def exportar_docx(doc):
    nombre = re.sub(r'[\\/:*?"<>|]', "-", doc["nombre"]) + ".docx"
    ruta = DOCX_DIR / nombre
    if ruta.exists():
        return ruta
    status, _, location = api_post(f"/platform/v1/documents/{doc['id']}/export", {"format": "docx"})
    if status != 202:
        raise RuntimeError(f"Export fallo: {status}")
    data = poll_operation(location, max_tries=40, wait=3)
    url  = data.get("resourceUrl", "")
    content = http_bytes(url, headers={"Authorization": f"Bearer {get_token()}"})
    ruta.write_bytes(content)
    return ruta

# ---------------------------------------------------------------------------
# Parsear .docx: extraer cuerpo con deteccion de fila azul (fondo oscuro)
# ---------------------------------------------------------------------------
WNS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"

def _wtag(name):
    return f"{{{WNS}}}{name}"

def get_cell_text(tc):
    return "".join(t.text for t in tc.iter(_wtag("t")) if t.text).strip()

def _fill_color(el):
    shd = el.find(_wtag("shd"))
    if shd is None:
        return None
    fill = shd.get(_wtag("fill")) or shd.get("fill") or ""
    return fill.upper() if fill and fill.upper() not in ("AUTO", "", "FFFFFF") else None

def _is_dark(hex_color):
    if not hex_color or len(hex_color) < 6:
        return False
    try:
        r, g, b = int(hex_color[0:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16)
        return (r * 299 + g * 587 + b * 114) / 1000 < 128
    except Exception:
        return False

def _row_is_blue(tr):
    """True si la fila tiene fondo oscuro (encabezado/total/subtotal)."""
    trPr = tr.find(_wtag("trPr"))
    if trPr is not None:
        c = _fill_color(trPr)
        if c and _is_dark(c):
            return True
    tcs = tr.findall(_wtag("tc"))
    dark = sum(1 for tc in tcs
               for tcPr in [tc.find(_wtag("tcPr"))]
               if tcPr is not None and _is_dark(_fill_color(tcPr) or ""))
    if tcs and dark / len(tcs) >= 0.5:
        return True
    # texto blanco >= 60% de runs
    runs = tr.findall(f".//{_wtag('rPr')}")
    white = sum(1 for rPr in runs
                for color in [rPr.find(_wtag("color"))]
                if color is not None and (color.get(_wtag("val")) or "").upper() == "FFFFFF")
    if runs and white / len(runs) >= 0.6:
        return True
    return False

def es_titulo_seccion(texto):
    if len(texto) < 10:
        return False
    if re.match(r"^Movimiento al\b", texto, re.I):
        return False
    if re.match(r"^\d{2}-\d{2}-\d{4}", texto):
        return False
    return True

def extraer_cuerpo_docx(ruta):
    """Devuelve lista de {'tipo':'parrafo'|'tabla', 'texto':str | 'filas':[{'cells':[],'blue':bool}]}."""
    elementos = []
    with zipfile.ZipFile(ruta) as z:
        with z.open("word/document.xml") as f:
            tree = ET.parse(f)
    body = tree.getroot().find(_wtag("body"))
    if body is None:
        return elementos
    for child in list(body):
        tag = child.tag.split("}")[-1] if "}" in child.tag else child.tag
        if tag == "p":
            texto = "".join(t.text for t in child.iter(_wtag("t")) if t.text).strip()
            if texto:
                elementos.append({"tipo": "parrafo", "texto": texto})
        elif tag == "tbl":
            filas = []
            for tr in child.findall(_wtag("tr")):
                celdas = [get_cell_text(tc) for tc in tr.findall(_wtag("tc"))]
                filas.append({"cells": celdas, "blue": _row_is_blue(tr)})
            if filas:
                elementos.append({"tipo": "tabla", "filas": filas})
    return elementos

# ---------------------------------------------------------------------------
# Logica de verificacion — igual a verificar_sumas.py (motor PDF depurado)
# ---------------------------------------------------------------------------
KW = re.compile(
    r'(total|totales|subtotal|sub-total|saldo\s+final|saldos?\s+al|'
    r'patrimonio\s+(total|al\s+final)|ganancia\s+bruta|'
    r'ganancia\s*\(p[eé]rdida\)\s*(bruta|antes|del|\b)|'
    r'resultado\s+integral\s+total|incremento\s*\(disminuci[oó]n\))', re.I)

KW_FLAG = re.compile(
    r'(\b(total(?:es)?|sub-?total)\b|saldo\s+(final|al\b)|total\s+d[eo]l?\b|patrimonio\s+total)', re.I)

BAL    = re.compile(r'(saldo\b|patrimonio\s+al\b)', re.I)
TOTMOV = re.compile(r'(total.*(increment|movimiento|disminuci|cambios|'
                    r'resultado\s+integral|del\s+per[ií]odo|patrimonio)'
                    r'|^cambios[,\s]+total)', re.I)
REF_NOTA = re.compile(r'\(nota\s+\d+[\.\d]*\)', re.I)

def parse_num(s):
    """Formato chileno: 1.234.567; negativos en parentesis."""
    if s is None:
        return None
    t = s.strip().replace('\n', '').replace(' ', '')
    if t in ('', '-', '—', '–'):
        return None
    neg = False
    if t.startswith('(') and t.endswith(')'):
        neg = True; t = t[1:-1]
    if t.startswith('-'):
        neg = True; t = t[1:]
    if ',' in t:
        return None
    core = t.replace('.', '')
    if not re.fullmatch(r'\d+', core):
        return None
    v = int(core)
    return -v if neg else v

def cell(r, j):
    return r['cells'][j] if j < len(r['cells']) else ''

def amount_cols(rows):
    """Columnas de monto: excluye col0 (etiqueta), columnas de notas.
    Devuelve (cols, htxt) donde htxt[j] es el texto del encabezado de col j."""
    ncol = max((len(r['cells']) for r in rows), default=0)
    htxt = [''] * ncol
    for r in rows:
        if not r['blue']:
            break
        for j, c in enumerate(r['cells']):
            if j < ncol:
                htxt[j] += ' ' + c.lower()

    def colvals(j):
        return [r['cells'][j].strip() for r in rows
                if j < len(r['cells']) and parse_num(r['cells'][j]) is not None]

    numeric = [j for j in range(1, ncol) if colvals(j)]
    note_col = None
    blob = ' '.join(htxt).lower()
    weak_header = not (('m$' in blob) or bool(re.search(r'\d{2}-\d{2}-\d{4}', blob)))
    if numeric and weak_header:
        jL = numeric[0]
        vs = colvals(jL)
        small_nonzero = (vs
                         and all(re.fullmatch(r'\d{1,2}', v) for v in vs)
                         and any(parse_num(v) != 0 for v in vs))
        big_right = any(
            any(len(re.sub(r'\D', '', x)) > 2 for x in colvals(jr))
            for jr in numeric[1:]
        )
        if small_nonzero and big_right:
            note_col = jL

    cols = [j for j in numeric if j != note_col and 'nota' not in htxt[j]]
    return cols, htxt

def colhdr(htxt, j):
    """Texto limpio del encabezado de la columna j."""
    h = re.sub(r'\s+', ' ', htxt[j]).strip() if j < len(htxt) else ''
    return h[:40] if h else f'col{j}'

def is_movement_table(rows, cols):
    nbal = sum(1 for r in rows
               if BAL.search(r['cells'][0] if r['cells'] else '')
               and any(parse_num(cell(r, j)) is not None for j in cols))
    ntot = sum(1 for r in rows
               if TOTMOV.search(r['cells'][0] if r['cells'] else ''))
    return nbal >= 1 and (nbal >= 2 or ntot >= 1)

def verify(rows, cols):
    """Verifica sumas verticales en cuadros generales.
    Reglas: A_bloque, F_bloque_abajo, G_subitem, B_acumulativo, E_acum_total,
    C_subtotales, S_jerarquia. Identica a verificar_sumas.py."""
    contrast = any(
        (not r['blue']) and any(parse_num(cell(r, j)) is not None for j in cols)
        for r in rows
    )

    def numeric(r):
        return any(parse_num(cell(r, j)) is not None for j in cols)

    def is_ckpt(r):
        if not numeric(r):
            return False
        lab = r['cells'][0] if r['cells'] else ''
        if REF_NOTA.search(lab):
            return False
        if KW.search(lab):
            return True
        if r['blue'] and contrast:
            return True
        return False

    klass = ['ckpt' if is_ckpt(r) else ('add' if numeric(r) else 'none') for r in rows]
    res = []
    for j in cols:
        fwd = {}
        fwd_sub = {}
        for i in range(len(rows)):
            if klass[i] != 'ckpt':
                continue
            s_all = None
            s_sub = None
            for k in range(i + 1, len(rows)):
                if klass[k] == 'ckpt':
                    break
                if klass[k] == 'add':
                    v = parse_num(cell(rows[k], j))
                    if v is not None:
                        s_all = (s_all or 0) + v
                    lab_k = rows[k]['cells'][0] if rows[k]['cells'] else ''
                    is_sub = bool(re.match(r'^[\-•–]\s', lab_k)
                                  or re.match(r'^\s{2,}', lab_k))
                    if is_sub and v is not None:
                        s_sub = (s_sub or 0) + v
                    elif not is_sub and s_sub is not None:
                        break
            fwd[i] = s_all
            fwd_sub[i] = s_sub

        stack_ok = {}
        units = []
        for i in range(len(rows)):
            if klass[i] == 'add':
                v = parse_num(cell(rows[i], j))
                if v is not None:
                    units.append(v)
            elif klass[i] == 'ckpt':
                P = parse_num(cell(rows[i], j))
                if P is None:
                    continue
                acc = 0
                found = None
                for k in range(1, len(units) + 1):
                    acc += units[-k]
                    if acc == P:
                        found = k
                        break
                if found is not None:
                    units[-found:] = [P]
                    stack_ok[i] = True
                else:
                    units.append(P)
                    stack_ok[i] = False

        prev = None
        block = []
        cum = 0
        subs = []
        for i, r in enumerate(rows):
            v = parse_num(cell(r, j))
            if klass[i] == 'ckpt':
                if v is None:
                    block = []
                    continue
                P = v
                cands = {}
                if block:
                    cands['A_bloque'] = sum(block)
                if fwd.get(i) is not None:
                    cands['F_bloque_abajo'] = fwd[i]
                if fwd_sub.get(i) is not None:
                    cands['G_subitem'] = fwd_sub[i]
                if prev is not None:
                    cands['B_acumulativo'] = prev + sum(block)
                cands['E_acum_total'] = cum
                if subs:
                    cands['C_subtotales'] = sum(subs)
                if stack_ok.get(i):
                    cands['S_jerarquia'] = P
                avail = {n: c for n, c in cands.items() if c is not None}
                lab = r['cells'][0] if r['cells'] else ''
                difs = {n: (P - c) for n, c in avail.items()}
                best = min(difs, key=lambda n: abs(difs[n])) if difs else None
                if best is not None and difs[best] == 0:
                    res.append({'col': j, 'label': lab, 'printed': P, 'dif': 0,
                                'metodo': best, 'clase': 'check'})
                    if best in ('E_acum_total', 'C_subtotales'):
                        cum = 0
                        subs = []
                elif KW_FLAG.search(lab) and best is not None:
                    bd = difs[best]
                    if P == 0 and abs(bd) > 1000:
                        res.append({'col': j, 'label': lab, 'printed': P,
                                    'dif': None, 'clase': 'linea'})
                    elif P != 0 and abs(bd) > abs(P):
                        res.append({'col': j, 'label': lab, 'printed': P,
                                    'dif': None, 'clase': 'linea'})
                    else:
                        res.append({'col': j, 'label': lab, 'printed': P,
                                    'dif': bd, 'metodo': best, 'clase': 'check'})
                else:
                    res.append({'col': j, 'label': lab, 'printed': P,
                                'dif': None, 'clase': 'linea'})
                prev = P
                subs.append(P)
                block = []
            elif klass[i] == 'add':
                if v is not None:
                    block.append(v)
                    cum += v
    return res

def verify_movement(rows, cols):
    """Verifica tablas de movimiento: saldo_final = saldo_inicial + Σ movimientos.
    Identica a verificar_sumas.py."""
    res = []
    for j in cols:
        opening = None
        summov = 0
        have_open = False
        for r in rows:
            lab = r['cells'][0] if r['cells'] else ''
            v = parse_num(cell(r, j))
            is_bal = bool(BAL.search(lab)) or bool(
                r['blue'] and re.match(r'^Sald', lab, re.I)
                and not have_open and v is not None
            )
            if is_bal:
                if v is None:
                    continue
                if not have_open:
                    opening = v
                    have_open = True
                else:
                    exp = (opening or 0) + summov
                    res.append({'col': j, 'label': lab, 'printed': v, 'dif': v - exp,
                                'metodo': 'Movimiento: saldo inicial + movimientos',
                                'clase': 'check'})
                    opening = v
                    summov = 0
            elif REF_NOTA.search(lab):
                pass
            elif 'total' in lab.lower() or TOTMOV.search(lab):
                if v is None:
                    continue
                d_sub = v - summov
                d_close = (v - ((opening or 0) + summov)) if have_open else None
                if d_close == 0:
                    res.append({'col': j, 'label': lab, 'printed': v, 'dif': 0,
                                'metodo': 'Movimiento: saldo final = inicial + movimientos',
                                'clase': 'check'})
                    opening = v
                    summov = 0
                elif d_sub == 0:
                    res.append({'col': j, 'label': lab, 'printed': v, 'dif': 0,
                                'metodo': 'Suma de movimientos', 'clase': 'check'})
                elif d_close is not None and abs(d_close) < abs(d_sub):
                    res.append({'col': j, 'label': lab, 'printed': v, 'dif': d_close,
                                'metodo': 'Movimiento: saldo final = inicial + movimientos',
                                'clase': 'check'})
                    opening = v
                    summov = 0
                else:
                    res.append({'col': j, 'label': lab, 'printed': v, 'dif': d_sub,
                                'metodo': 'Suma de movimientos', 'clase': 'check'})
            else:
                if v is not None:
                    summov += v
    return res

def causa_probable(label, dif, localizado, calc, tipo_tabla):
    """Causa probable del hallazgo — identica a verificar_sumas.py."""
    lab = (label or '').lower()
    if localizado:
        return ('Diferencia LOCALIZADA: otras columnas del mismo cuadro cuadran '
                '— probable error real, REVISAR')
    if tipo_tabla == 'movimiento':
        return ('Movimiento NO cuadra: saldo final != saldo inicial + '
                'suma movimientos — REVISAR')
    if calc == 0:
        return ('Fila rotulada "total" sin detalle sumable arriba '
                '(posible cifra derivada/conciliacion) — revisar')
    if 'atribuible a' in lab:
        return 'Desagregacion (propietarios / no controladoras): no es suma lineal'
    if 'comienzo' in lab or 'al final' in lab or lab.startswith('saldo'):
        return 'Esquema de movimiento (saldo inicial + movimientos = saldo final)'
    if abs(dif) <= UMBRAL:
        return 'DIFERENCIA PEQUENA: posible redondeo o error real — REVISAR'
    return 'Total que combina secciones, estado matricial o estructura no estandar — revisar'

# ---------------------------------------------------------------------------
# Verificar archivo .docx — devuelve {ok, hallazgos, revisar, indice}
# ---------------------------------------------------------------------------
def verificar_docx(ruta):
    elementos = extraer_cuerpo_docx(ruta)
    seccion = ""
    tablas_con_seccion = []
    for elem in elementos:
        if elem["tipo"] == "parrafo":
            if es_titulo_seccion(elem["texto"]):
                seccion = elem["texto"]
        else:
            tablas_con_seccion.append((seccion, elem["filas"]))

    rows_ok = []
    rows_chk = []
    tablas = []

    for i_tabla, (sec, filas) in enumerate(tablas_con_seccion, 1):
        cols, htxt = amount_cols(filas)
        if not cols:
            continue

        tipo = "movimiento" if is_movement_table(filas, cols) else "general"
        res  = verify_movement(filas, cols) if tipo == "movimiento" else verify(filas, cols)
        checks = [r for r in res if r['clase'] == 'check']
        if not checks:
            continue

        nok = 0
        nz  = 0
        per_col = {}
        for r in checks:
            d = per_col.setdefault(r['col'], [0, 0])
            d[0] += 1
            if r['dif'] == 0:
                d[1] += 1
        fully_ok_cols = {c for c, (n, z) in per_col.items() if n > 0 and z == n}

        for r in checks:
            col_nombre = colhdr(htxt, r['col'])
            dif   = r['dif']
            calc  = r['printed'] - (dif or 0) if dif is not None else 0
            label = re.sub(r'\s+', ' ', r['label']).strip()[:80]
            rec = {
                'n_tabla':  i_tabla,
                'seccion':  sec[:80],
                'tabla_idx': 0,
                'fila':     label,
                'columna':  col_nombre,
                'impreso':  r['printed'],
                'calc':     calc,
                'dif':      dif,
                'metodo':   r.get('metodo', ''),
            }
            if dif == 0:
                nok += 1
                rows_ok.append(rec)
            elif dif is not None:
                nz += 1
                localizado = (r['col'] not in fully_ok_cols
                              and bool(fully_ok_cols)
                              and r['printed'] != 0)
                rec['localizado'] = localizado
                rec['causa'] = causa_probable(label, dif, localizado, calc, tipo)
                rows_chk.append(rec)

        tablas.append({
            'n_tabla': i_tabla,
            'seccion': sec[:80],
            'tabla_idx': 0,
            'n_cols':  len(cols),
            'n_sumas': len(checks),
            'ok':      nok,
            'dif':     nz,
        })

    # Post-proceso: diferencias que se compensan entre columnas de la misma fila
    # (matrices de segmento: col_A diff = +X, col_B diff = -X => error real de desglose)
    grp = defaultdict(list)
    for rec in rows_chk:
        grp[(rec['n_tabla'], rec['fila'])].append(rec)
    for key, recs in grp.items():
        if (len(recs) >= 2
                and sum(r['dif'] for r in recs) == 0
                and all(r['dif'] != 0 for r in recs)):
            for r in recs:
                r['localizado'] = True
                r['causa'] = ('Columnas de segmento NO cuadran (el consolidado si): '
                              'el desglose difiere en +-igual monto que se compensa — REVISAR')

    # Hallazgos = revisar con diferencia pequena o localizada
    hallazgos = [r for r in rows_chk
                 if r.get('localizado') or abs(r['dif']) <= UMBRAL]

    return {
        'ok':        rows_ok,
        'hallazgos': hallazgos,
        'revisar':   rows_chk,
        'indice':    tablas,
    }

# ---------------------------------------------------------------------------
# Escribir resumen en la hoja propia de la sociedad (ej. "E514")
# ---------------------------------------------------------------------------
def escribir_resumen(ss_id, codigo, nombre_doc, resultado):
    """Escribe un bloque de resumen en la hoja de la sociedad (nombre = codigo).
    Nunca toca la fila 1 (encabezados del usuario). Siempre escribe desde fila 2
    o desde la primera fila libre si ya hay datos previos."""
    sheet_id, es_nueva = obtener_o_crear_hoja(ss_id, codigo)
    if not es_nueva:
        _limpiar_desde_fila2(ss_id, sheet_id, 1)

    n_ok   = len(resultado['ok'])
    n_hall = len(resultado['hallazgos'])
    n_rev  = len(resultado['revisar'])
    n_cuad = len(resultado['indice'])

    filas = [
        [f"Documento: {nombre_doc}"],
        [f"Sumas verificadas que cuadran exacto: {n_ok}"],
        [f"Hallazgos prioritarios (dif. pequena o localizada): {n_hall}"],
        [f"A revisar manualmente: {n_rev}"],
        [f"Cuadros con sumas detectados: {n_cuad}"],
    ]
    put_range(ss_id, sheet_id, f"A2:A{1 + len(filas)}", filas)

# ---------------------------------------------------------------------------
# Escribir las 4 sub-hojas en Workiva
# ---------------------------------------------------------------------------
# Cabeceras identicas al xlsx de referencia (verificar_sumas.py output),
# con "Sociedad" como primera columna para identificar la empresa.
HDR_HALL = ["Sociedad", "N tabla", "Cuadro / Nota", "Tabla",
            "Fila", "Columna", "Impreso", "Calculado", "Diferencia",
            "Regla", "Causa probable"]
HDR_OK   = ["Sociedad", "N tabla", "Cuadro / Nota", "Tabla",
            "Fila (subtotal/total)", "Columna", "Valor impreso", "Regla"]
HDR_IDX  = ["Sociedad", "N tabla", "Cuadro / Nota", "Tabla",
            "Cols. monto", "Sumas", "Cuadran", "A revisar"]

NOMBRE_HOJAS = {
    "hallazgos": "Hallazgos",
    "revisar":   "Revisar_manual",
    "ok":        "Verificadas_OK",
    "indice":    "Indice_cuadros",
}

def _limpiar_desde_fila2(ss_id, sheet_id, n_cols):
    """Borra todo el contenido desde fila 2 hacia abajo (deja fila 1 intacta)."""
    ultima = contar_filas(ss_id, sheet_id)
    if ultima < 2:
        return
    fila_vacia = [""] * n_cols
    filas_vacias = [fila_vacia for _ in range(ultima - 1)]
    col_fin = chr(64 + n_cols)
    put_range(ss_id, sheet_id, f"A2:{col_fin}{ultima}", filas_vacias)

def _escribir_hoja(ss_id, nombre_hoja, encabezados, filas):
    sheet_id, es_nueva = obtener_o_crear_hoja(ss_id, nombre_hoja)
    n = len(encabezados)
    if es_nueva:
        put_range(ss_id, sheet_id, f"A1:{chr(64 + n)}1", [encabezados])
    else:
        _limpiar_desde_fila2(ss_id, sheet_id, n)
    if filas:
        put_range(ss_id, sheet_id, f"A2:{chr(64 + n)}{1 + len(filas)}", filas)

def escribir_4_hojas(ss_id, codigo, resultado):
    def nombre(clave):
        return f"{codigo}.- {NOMBRE_HOJAS[clave]}"

    # Hallazgos (diferencias pequenas + localizadas)
    filas_h = [
        [codigo, r['n_tabla'], r['seccion'], r['tabla_idx'],
         r['fila'], r['columna'], r['impreso'], r['calc'], r['dif'],
         r['metodo'], r['causa']]
        for r in resultado['hallazgos']
    ]
    _escribir_hoja(ss_id, nombre("hallazgos"), HDR_HALL, filas_h)

    # Revisar_manual (todas las diferencias)
    filas_r = [
        [codigo, r['n_tabla'], r['seccion'], r['tabla_idx'],
         r['fila'], r['columna'], r['impreso'], r['calc'], r['dif'],
         r['metodo'], r['causa']]
        for r in resultado['revisar']
    ]
    _escribir_hoja(ss_id, nombre("revisar"), HDR_HALL, filas_r)

    # Verificadas_OK
    filas_ok = [
        [codigo, r['n_tabla'], r['seccion'], r['tabla_idx'],
         r['fila'], r['columna'], r['impreso'], r['metodo']]
        for r in resultado['ok']
    ]
    _escribir_hoja(ss_id, nombre("ok"), HDR_OK, filas_ok)

    # Indice_cuadros
    filas_i = [
        [codigo, t['n_tabla'], t['seccion'], t['tabla_idx'],
         t['n_cols'], t['n_sumas'], t['ok'], t['dif']]
        for t in resultado['indice']
    ]
    _escribir_hoja(ss_id, nombre("indice"), HDR_IDX, filas_i)

# ---------------------------------------------------------------------------
# UI helpers
# ---------------------------------------------------------------------------
def hr(c="-"):
    print(c * 64)

def ask(prompt, opts=None, default=None):
    if opts:
        txt = f"{prompt} [{'/'.join(opts)}]"
        if default:
            txt += f" (default {default})"
        print(f"  {txt}: ", end="")
        v = input().strip().upper() or (default or "")
        return v if not opts or v in opts else (default or opts[0])
    print(f"  {prompt}: ", end="")
    return input().strip()

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    hr("=")
    print("  VERIFICADOR DE SUMAS - EE.FF. WORKIVA")
    print("  (sin instalacion de librerias adicionales)")
    hr("=")

    print("\n  PERIODO\n")
    mes_raw = ask("  Mes (numero o nombre, ej: 6 / junio)")
    mes = MESES.get(mes_raw.lower())
    while not mes:
        print(f"  Mes '{mes_raw}' no reconocido.")
        mes_raw = ask("  Mes")
        mes = MESES.get(mes_raw.lower())

    anio = ask("  Ano (ej: 2026)")
    while not re.fullmatch(r"\d{4}", anio):
        print("  Ano invalido.")
        anio = ask("  Ano")

    print("\n  IDIOMA\n")
    idioma = ask("  Idioma", opts=["ESP", "ENG", "AMBOS"], default="AMBOS")

    print(f"\n  Conectando a Workiva [{mes}-{anio} / {idioma}]...\n")
    docs = buscar_documentos(mes, anio, idioma)

    if not docs:
        print(f"  No hay documentos {mes}-{anio} [{idioma}].")
        input("\n  Enter para salir...")
        return

    seleccionados = seleccionar_docs(docs)
    if not seleccionados:
        print("  Ninguno seleccionado.")
        input("\n  Enter para salir...")
        return

    print()
    ss_id = buscar_spreadsheet_verif()
    if not ss_id:
        print(f"  No se encontro el spreadsheet '{SS_VERIF_NAME}'.")
        input("\n  Enter para salir...")
        return

    DOCX_DIR.mkdir(exist_ok=True)
    hr()
    total_hall = 0

    for i, doc in enumerate(seleccionados, 1):
        m = re.match(r"^([A-Z]\d+)", doc["nombre"].strip())
        codigo = m.group(1) if m else doc["nombre"][:20]

        print(f"\n  [{i}/{len(seleccionados)}] {doc['nombre']}")
        print(f"    Codigo sociedad: '{codigo}'")
        print("    Exportando  ...", end=" ", flush=True)
        try:
            ruta = exportar_docx(doc)
            print(f"OK ({ruta.stat().st_size // 1024} KB)")
        except Exception as e:
            print(f"ERROR: {e}")
            continue

        print("    Verificando ...", end=" ", flush=True)
        try:
            resultado = verificar_docx(ruta)
        except Exception as e:
            print(f"ERROR al leer: {e}")
            continue

        n_rev  = len(resultado["revisar"])
        n_ok   = len(resultado["ok"])
        n_hall = len(resultado["hallazgos"])
        total_hall += n_hall
        print(f"OK:{n_ok}  Revisar:{n_rev}  Hallazgos:{n_hall}")

        print("    Escribiendo resumen ...", end=" ", flush=True)
        try:
            escribir_resumen(ss_id, codigo, doc["nombre"], resultado)
            print("OK")
        except Exception as e:
            print(f"ERROR: {e}")

        print("    Escribiendo subhojas ...", end=" ", flush=True)
        try:
            escribir_4_hojas(ss_id, codigo, resultado)
            print("OK")
        except Exception as e:
            print(f"ERROR: {e}")

    hr("=")
    print(f"\n  RESUMEN FINAL")
    print(f"  Documentos procesados : {len(seleccionados)}")
    print(f"  Hallazgos prioritarios: {total_hall}")
    print(f"\n  Workiva -> '{SS_VERIF_NAME}'")
    print(f"  Hojas: Hallazgos / Revisar_manual / Verificadas_OK / Indice_cuadros")
    hr("=")
    input("\n  Presiona Enter para salir...")

if __name__ == "__main__":
    main()
