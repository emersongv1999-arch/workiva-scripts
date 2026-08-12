"""
verificar_workiva_GUI.py
Verificador de Sumas - EE.FF. Workiva
Interfaz grafica con tkinter — colores corporativos CGE
"""
import base64, io, json, math, os, re, shutil, ssl, struct, sys, time, urllib.request, urllib.error, wave, zipfile
import xml.etree.ElementTree as ET
from pathlib import Path
from collections import defaultdict
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import threading

# Import a nivel de modulo (no dentro de la funcion) para que PyInstaller lo
# detecte en el analisis estatico y lo empaquete en el .exe.
try:
    import winsound
except Exception:
    winsound = None

# ── CREDENCIALES ──────────────────────────────────────────────────────────────
CLIENT_ID     = "db2c551e-e18a-417e-8e52-d182716b8ef2"
CLIENT_SECRET = "wk_secret:oa2c:DzlUCmBQDv6raPxG09me"
WORKSPACE_ID  = "w_34913aadaa38420eabd7e4d341b78a1a"
AUDITOR_NAME  = "Emerson Garrido"

TOKEN_URL  = "https://api.app.wdesk.com/iam/v1/oauth2/token"
WDESK_BASE = "https://api.app.wdesk.com"
UMBRAL     = 1000

MESES = {
    "1":"01","01":"01","enero":"01","2":"02","02":"02","febrero":"02",
    "3":"03","03":"03","marzo":"03","4":"04","04":"04","abril":"04",
    "5":"05","05":"05","mayo":"05","6":"06","06":"06","junio":"06",
    "7":"07","07":"07","julio":"07","8":"08","08":"08","agosto":"08",
    "9":"09","09":"09","septiembre":"09","10":"10","octubre":"10",
    "11":"11","noviembre":"11","12":"12","diciembre":"12",
}


# ── LOGO CGE (base64 JPEG) ───────────────────────────────────────────────────
LOGO_B64 = (
    "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"
)
# ── SSL ───────────────────────────────────────────────────────────────────────
CTX = ssl.create_default_context()
CTX.check_hostname = False
CTX.verify_mode    = ssl.CERT_NONE

# ── HTTP ──────────────────────────────────────────────────────────────────────
def http(method, url, headers=None, body=None, timeout=60):
    data = json.dumps(body).encode() if body is not None else None
    h = {"Content-Type": "application/json",
         "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Python/3.13",
         **(headers or {})}
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

# ── AUTH ──────────────────────────────────────────────────────────────────────
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
            headers={"Authorization": f"Bearer {token}",
                     "Content-Type": "application/json",
                     "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Python/3.13",
                     "X-Version": "2022-01-01"},
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
            headers={"Authorization": f"Bearer {token}",
                     "Content-Type": "application/json",
                     "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Python/3.13",
                     "X-Version": "2022-01-01"},
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

# ── WORKIVA ───────────────────────────────────────────────────────────────────
def buscar_documentos(mes, anio, idioma):
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
    return docs

def buscar_spreadsheet_verif(ss_name, ss_cache):
    if ss_cache.exists():
        cached = ss_cache.read_text().strip()
        if cached:
            return cached
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
            if ss_name.lower() in ss.get("name", "").lower():
                sid = ss["id"]
                ss_cache.write_text(sid)
                return sid
        url = data.get("@nextLink") or data.get("nextLink") or None
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

def put_range(ss_id, sheet_id, rango, values):
    status, _, location = api_put(
        f"/platform/v1/spreadsheets/{ss_id}/sheets/{sheet_id}/values/{rango}",
        {"values": values}
    )
    if status == 202 and location:
        poll_operation(location, wait=2)

def exportar_docx(doc, docx_dir):
    nombre = re.sub(r'[\\/:*?"<>|]', "-", doc["nombre"]) + ".docx"
    ruta = docx_dir / nombre
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

# ── PARSEAR DOCX ──────────────────────────────────────────────────────────────
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
                celdas = []
                for tc in tr.findall(_wtag("tc")):
                    text = get_cell_text(tc)
                    tcPr = tc.find(_wtag("tcPr"))
                    span = 1
                    if tcPr is not None:
                        gs = tcPr.find(_wtag("gridSpan"))
                        if gs is not None:
                            try:
                                span = int(gs.get(_wtag("val")) or gs.get("val") or 1)
                            except (ValueError, TypeError):
                                span = 1
                    celdas.append(text)
                    for _ in range(span - 1):
                        celdas.append("")
                filas.append({"cells": celdas, "blue": _row_is_blue(tr)})
            if filas:
                elementos.append({"tipo": "tabla", "filas": filas})
    return elementos

# ── LOGICA DE VERIFICACION ────────────────────────────────────────────────────
KW = re.compile(
    r'(total|totales|subtotal|sub-total|saldo\s+final|saldos?\s+al|'
    r'patrimonio\s+(total|al\s+final)|ganancia\s+bruta|'
    r'ganancia\s*\(p[eé]rdida\)\s*(bruta|antes|del|\b)|'
    r'resultado\s+integral\s+total|incremento\s*\(disminuci[oó]n\)|'
    # English equivalents
    r'net\s+cash\s+(flows?|generated|used)|'
    r'gross\s+profit|profit\s*(before|after|for)|'
    r'total\s+comprehensive\s+income|'
    r'net\s+(increase|decrease)\s+in\s+cash|'
    r'equity\s+(total|at\s+end)|increase\s*\(decrease\))', re.I)

KW_FLAG = re.compile(
    r'(\b(total(?:es)?|sub-?total)\b|saldo\s+(final|al\b)|total\s+d[eo]l?\b|patrimonio\s+total|'
    # English equivalents
    r'net\s+cash\s+(flows?|generated|used)|'
    r'net\s+(increase|decrease)\s+in\s+cash|'
    r'total\s+equity)', re.I)

BAL    = re.compile(r'(saldo\b|patrimonio\s+al\b)', re.I)
TOTMOV = re.compile(r'(total.*(increment|movimiento|disminuci|cambios|'
                    r'resultado\s+integral|del\s+per[ií]odo|patrimonio)'
                    r'|^cambios[,\s]+total)', re.I)
REF_NOTA = re.compile(r'\((nota|note)\s+\d+[\.\d]*\)', re.I)

# Filas cuyo total NO es una suma lineal de lo inmediatamente anterior:
# ratios/conteos por accion, o reconciliaciones (EBITDA) que combinan
# lineas separadas por varios subtotales intermedios. Verificarlas como
# si fueran un bloque-suma simple genera falsos hallazgos.
NOLINEAL = re.compile(
    r'(ebitda|'
    r'n[uú]mero\s+de\s+acciones|number\s+of\s+shares|'
    r'promedio\s+ponderado|weighted\s+average|'
    r'por\s+acci[oó]n|per\s+share)', re.I)

def parse_num(s):
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
    # Separador de miles: coma (ENG) o punto (ESP) — ambos se eliminan
    t = t.replace(',', '')
    core = t.replace('.', '')
    if not re.fullmatch(r'\d+', core):
        return None
    v = int(core)
    return -v if neg else v

def cell(r, j):
    return r['cells'][j] if j < len(r['cells']) else ''

def _row_label(r):
    for c in r.get('cells', []):
        t = c.strip()
        if t:
            return t
    return ''

def amount_cols(rows):
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
    h = re.sub(r'\s+', ' ', htxt[j]).strip() if j < len(htxt) else ''
    return h[:40] if h else f'col{j}'

def is_movement_table(rows, cols):
    nbal = sum(1 for r in rows
               if BAL.search(_row_label(r))
               and any(parse_num(cell(r, j)) is not None for j in cols))
    ntot = sum(1 for r in rows if TOTMOV.search(_row_label(r)))
    return nbal >= 1 and (nbal >= 2 or ntot >= 1)

def verify(rows, cols):
    contrast = any(
        (not r['blue']) and any(parse_num(cell(r, j)) is not None for j in cols)
        for r in rows
    )

    def numeric(r):
        return any(parse_num(cell(r, j)) is not None for j in cols)

    def is_ckpt(r):
        if not numeric(r):
            return False
        lab = _row_label(r)
        if REF_NOTA.search(lab):
            return False
        if KW.search(lab):
            return True
        if r['blue'] and contrast:
            return True
        return False

    def klass_of(r):
        lab = _row_label(r)
        if NOLINEAL.search(lab):
            return 'none'  # no es suma lineal: se ignora, ni suma ni se verifica
        if is_ckpt(r):
            return 'ckpt'
        return 'add' if numeric(r) else 'none'

    klass = [klass_of(r) for r in rows]
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
                if prev is not None and block:
                    # Solo tiene sentido si hay detalle real entre el ckpt
                    # anterior y este; si block esta vacio, esto degenera en
                    # "prev" a secas — comparar contra una fila anterior sin
                    # relacion (ej. filas consecutivas "operating/investing/
                    # financing" sin detalle entre medio) da falsos positivos.
                    cands['B_acumulativo'] = prev + sum(block)
                cands['E_acum_total'] = cum
                if len(subs) >= 2:
                    # Con un solo subtotal previo, "sum(subs)" es literalmente
                    # ese mismo valor — comparar contra el ckpt anterior sin
                    # relacion (filas consecutivas sin detalle entre medio,
                    # ej. operating/investing/financing) da falsos positivos.
                    cands['C_subtotales'] = sum(subs)
                if stack_ok.get(i):
                    cands['S_jerarquia'] = P
                if not block and prev is not None and len(subs) >= 2:
                    for s in subs[:-1]:
                        if s + prev == P:
                            cands['D_seccion_anterior'] = P
                            break
                avail = {n: c for n, c in cands.items() if c is not None}
                lab = _row_label(r)
                difs = {n: (P - c) for n, c in avail.items()}
                best = min(difs, key=lambda n: abs(difs[n])) if difs else None
                if best is not None and difs[best] == 0:
                    res.append({'col': j, 'label': lab, 'printed': P, 'dif': 0,
                                'metodo': best, 'clase': 'check'})
                    if best in ('E_acum_total', 'C_subtotales'):
                        cum = 0
                        subs = [P]
                elif (KW_FLAG.search(lab) or (r['blue'] and 'A_bloque' in cands)) and best is not None:
                    # Para filas azules con detalle arriba, usar siempre A_bloque
                    # (evita que otro candidato coincidente enmascare un error real)
                    if r['blue'] and 'A_bloque' in cands and not KW_FLAG.search(lab):
                        best = 'A_bloque'
                    bd = difs[best]
                    if best == 'E_acum_total' and cum == 0:
                        res.append({'col': j, 'label': lab, 'printed': P,
                                    'dif': None, 'clase': 'linea'})
                    elif best == 'C_subtotales' and not subs:
                        res.append({'col': j, 'label': lab, 'printed': P,
                                    'dif': None, 'clase': 'linea'})
                    elif P == 0 and abs(bd) > 1000:
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
    res = []
    for j in cols:
        opening = None
        summov = 0
        have_open = False
        for r in rows:
            lab = _row_label(r)
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
                _is_close_candidate = (BAL.search(lab) or TOTMOV.search(lab)
                                       or bool(re.fullmatch(r'total\.?', lab.strip(), re.I)))
                if d_close == 0 and _is_close_candidate:
                    res.append({'col': j, 'label': lab, 'printed': v, 'dif': 0,
                                'metodo': 'Movimiento: saldo final = inicial + movimientos',
                                'clase': 'check'})
                    opening = v
                    summov = 0
                elif d_sub == 0:
                    res.append({'col': j, 'label': lab, 'printed': v, 'dif': 0,
                                'metodo': 'Suma de movimientos', 'clase': 'check'})
                elif d_close is not None and abs(d_close) < abs(d_sub) and _is_close_candidate:
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
    """Devuelve (texto_causa, es_estructural). es_estructural=True marca
    patrones donde la fila NO es una suma lineal comparable (desagregacion,
    esquema de saldo) o no hay detalle que sumar (calc==0) — esos casos se
    excluyen de Hallazgos porque no representan un error de cuadre real."""
    lab = (label or '').lower()
    if localizado:
        return ('Diferencia LOCALIZADA: otras columnas del mismo cuadro cuadran '
                '— probable error real, REVISAR'), False
    if tipo_tabla == 'movimiento':
        return ('Movimiento NO cuadra: saldo final != saldo inicial + '
                'suma movimientos — REVISAR'), False
    if calc == 0:
        return ('Fila rotulada "total" sin detalle sumable arriba '
                '(posible cifra derivada/conciliacion) — revisar'), True
    if 'atribuible a' in lab:
        return 'Desagregacion (propietarios / no controladoras): no es suma lineal', True
    if 'comienzo' in lab or 'al final' in lab or lab.startswith('saldo'):
        return 'Esquema de movimiento (saldo inicial + movimientos = saldo final)', True
    if abs(dif) <= UMBRAL:
        return 'DIFERENCIA PEQUENA: posible redondeo o error real — REVISAR', False
    return ('Total que combina secciones, estado matricial o estructura no estandar '
            '— revisar'), False

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
        _saldo_en_header = any(
            re.search(r'saldo', h, re.I) and re.search(r'\d{2}-\d{2}-\d{4}', h)
            for h in htxt
        )
        _row_labels_have_saldo = any(BAL.search(_row_label(r)) for r in filas if not r['blue'])
        if _saldo_en_header and not _row_labels_have_saldo:
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
                causa, estructural = causa_probable(label, dif, localizado, calc, tipo)
                rec['causa'] = causa
                rec['estructural'] = estructural
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

    # Va a Hallazgos cualquier diferencia real de cuadre (>UMBRAL incluido),
    # salvo los patrones estructuralmente no-lineales (desagregacion, esquema
    # de saldo, fila sin detalle) que no dependen de si hay o no una "columna
    # testigo" limpia en el mismo cuadro.
    hallazgos = [r for r in rows_chk if not r.get('estructural')]

    return {'ok': rows_ok, 'hallazgos': hallazgos, 'revisar': rows_chk, 'indice': tablas}

# ── ESCRIBIR EN WORKIVA ───────────────────────────────────────────────────────
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
    fila_vacia = [""] * n_cols
    filas_vacias = [fila_vacia for _ in range(2999)]
    col_fin = chr(64 + n_cols)
    put_range(ss_id, sheet_id, f"A2:{col_fin}3000", filas_vacias)

def _escribir_hoja(ss_id, nombre_hoja, encabezados, filas):
    sheet_id, es_nueva = obtener_o_crear_hoja(ss_id, nombre_hoja)
    n = len(encabezados)
    if es_nueva:
        put_range(ss_id, sheet_id, f"A1:{chr(64 + n)}1", [encabezados])
    else:
        _limpiar_desde_fila2(ss_id, sheet_id, n)
    if filas:
        put_range(ss_id, sheet_id, f"A2:{chr(64 + n)}{1 + len(filas)}", filas)

def escribir_resumen(ss_id, codigo, nombre_doc, resultado):
    sheet_id, _ = obtener_o_crear_hoja(ss_id, codigo)
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

def escribir_4_hojas(ss_id, codigo, resultado):
    def nombre(clave):
        return f"{codigo}.- {NOMBRE_HOJAS[clave]}"

    filas_h = [
        [codigo, r['n_tabla'], r['seccion'], r['tabla_idx'],
         r['fila'], r['columna'], r['impreso'], r['calc'], r['dif'],
         r['metodo'], r['causa']]
        for r in resultado['hallazgos']
    ]
    _escribir_hoja(ss_id, nombre("hallazgos"), HDR_HALL, filas_h)

    filas_r = [
        [codigo, r['n_tabla'], r['seccion'], r['tabla_idx'],
         r['fila'], r['columna'], r['impreso'], r['calc'], r['dif'],
         r['metodo'], r['causa']]
        for r in resultado['revisar']
    ]
    _escribir_hoja(ss_id, nombre("revisar"), HDR_HALL, filas_r)

    filas_ok = [
        [codigo, r['n_tabla'], r['seccion'], r['tabla_idx'],
         r['fila'], r['columna'], r['impreso'], r['metodo']]
        for r in resultado['ok']
    ]
    _escribir_hoja(ss_id, nombre("ok"), HDR_OK, filas_ok)

    filas_i = [
        [codigo, t['n_tabla'], t['seccion'], t['tabla_idx'],
         t['n_cols'], t['n_sumas'], t['ok'], t['dif']]
        for t in resultado['indice']
    ]
    _escribir_hoja(ss_id, nombre("indice"), HDR_IDX, filas_i)

# ── COLORES CGE ───────────────────────────────────────────────────────────────
CGE_BLUE    = "#011689"
CGE_BLUE2   = "#0a2abf"   # hover / variante
CGE_SIDEBAR = "#010e5a"   # sidebar más oscuro que el header
CGE_WHITE   = "#ffffff"
CGE_LIGHT   = "#f0f3fc"   # fondo general
CGE_CARD    = "#ffffff"
CGE_BORDER  = "#c8d0e8"
CGE_TEXT    = "#0d1a4a"
CGE_MUTED   = "#6b7aab"
CGE_GREEN   = "#0a8f5c"
CGE_RED     = "#c0001a"
CGE_YELLOW  = "#e8a000"
CGE_ROWALT  = "#eef1fb"   # fila alternada en lista docs

FONT_HEAD   = ("Segoe UI", 18, "bold")
FONT_SUB    = ("Segoe UI", 10)
FONT_LABEL  = ("Segoe UI", 10)
FONT_BOLD   = ("Segoe UI", 10, "bold")
FONT_SMALL  = ("Segoe UI", 9)
FONT_MONO   = ("Consolas", 9)


_LLENAR_COMP_SRC = base64.b64decode(
    b"IiIiCmxsZW5hcl9jb21wYXJhdGl2b3MucHkKPT09PT09PT09PT09PT09PT09PT09PQpTY3JpcHQgZ2Vuw6lyaWNvIHBhcmEgY29tcGxldGFyIGNvbHVtbmFzIGRlIHBlcsOtb2RvcyBlbiBhcmNoaXZvcwoiQmFzZSBOb3RhcyIgaW5kaXZpZHVhbGVzIGRlIFRPREFTIGxhcyBzb2NpZWRhZGVzIGRlIHVuIHBlcsOtb2RvLgoKVVNPOgogICAgcHl0aG9uIGxsZW5hcl9jb21wYXJhdGl2b3MucHkKCkVsIHNjcmlwdCBwcmVndW50YSBlbCBhw7FvIHkgbWVzIHkgcHJvY2VzYSB0b2RvcyBsb3MgYXJjaGl2b3MgZGUgbGEKY2FycGV0YSBJbmRpdmlkdWFsZXMgZGUgZXNlIHBlcsOtb2RvIGF1dG9tw6F0aWNhbWVudGUuCiIiIgoKaW1wb3J0IHdhcm5pbmdzLCB0aW1lLCByZSwgc3NsLCB1cmxsaWIucmVxdWVzdCwgdXJsbGliLnBhcnNlLCBqc29uCmltcG9ydCByZXF1ZXN0cwpmcm9tIHVybGxpYjMuZXhjZXB0aW9ucyBpbXBvcnQgSW5zZWN1cmVSZXF1ZXN0V2FybmluZwp3YXJuaW5ncy5maWx0ZXJ3YXJuaW5ncygiaWdub3JlIiwgY2F0ZWdvcnk9SW5zZWN1cmVSZXF1ZXN0V2FybmluZykKCiMg4pSA4pSAIENSRURFTkNJQUxFUyDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIAKQ0xJRU5UX0lEICAgICA9ICJkYjJjNTUxZS1lMThhLTQxN2UtOGU1Mi1kMTgyNzE2YjhlZjIiCkNMSUVOVF9TRUNSRVQgPSAid2tfc2VjcmV0Om9hMmM6RHpsVUNtQlFEdjZyYVB4RzA5bWUiClRPS0VOX1VSTCAgICAgPSAiaHR0cHM6Ly9hcGkuYXBwLndkZXNrLmNvbS9pYW0vdjEvb2F1dGgyL3Rva2VuIgojIOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgAoKZGVmIGdldF9zZXNzaW9uKCk6CiAgICByZXNwID0gcmVxdWVzdHMucG9zdChUT0tFTl9VUkwsIGRhdGE9ewogICAgICAgICJncmFudF90eXBlIjogICAgImNsaWVudF9jcmVkZW50aWFscyIsCiAgICAgICAgImNsaWVudF9pZCI6ICAgICBDTElFTlRfSUQsCiAgICAgICAgImNsaWVudF9zZWNyZXQiOiBDTElFTlRfU0VDUkVULAogICAgfSwgdmVyaWZ5PUZhbHNlLCB0aW1lb3V0PTMwKQogICAgdG9rZW4gPSByZXNwLmpzb24oKVsiYWNjZXNzX3Rva2VuIl0KICAgIHMgPSByZXF1ZXN0cy5TZXNzaW9uKCkKICAgIHMuaGVhZGVycy51cGRhdGUoeyJBdXRob3JpemF0aW9uIjogZiJCZWFyZXIge3Rva2VufSJ9KQogICAgcy52ZXJpZnkgPSBGYWxzZQogICAgcmV0dXJuIHMKCmRlZiBfdW5sb2NrX3NoZWV0KHNzX2lkLCBzaWQsIHNuYW1lKToKICAgICIiIkVsaW1pbmEgdG9kb3MgbG9zIGxvY2tzIGRlIHVuYSBob2phIHZpYSBERUxFVEUgL2xvY2tzL3tsb2NrSWR9LiIiIgogICAgdXJsID0gV0RFU0tfQkFTRSArICIvcGxhdGZvcm0vdjEvc3ByZWFkc2hlZXRzLyIgKyBzc19pZCArICIvc2hlZXRzLyIgKyBzaWQgKyAiL2xvY2tzIgogICAgdHJ5OgogICAgICAgIHIgICAgPSBzZXNzaW9uLmdldCh1cmwsIHRpbWVvdXQ9MzApCiAgICAgICAgZGF0YSA9IHIuanNvbigpCiAgICAgICAgbG9ja3MgPSBkYXRhLmdldCgiZGF0YSIsIFtdKQogICAgICAgIGlmIG5vdCBsb2NrczoKICAgICAgICAgICAgcmV0dXJuCiAgICAgICAgZm9yIGxrIGluIGxvY2tzOgogICAgICAgICAgICBsaWQgPSBsay5nZXQoImlkIikgb3IgbGsuZ2V0KCJsb2NrSWQiKQogICAgICAgICAgICBpZiBub3QgbGlkOgogICAgICAgICAgICAgICAgY29udGludWUKICAgICAgICAgICAgZHIgPSBzZXNzaW9uLmRlbGV0ZShXREVTS19CQVNFICsgIi9wbGF0Zm9ybS92MS9zcHJlYWRzaGVldHMvIiArIHNzX2lkCiAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgKyAiL3NoZWV0cy8iICsgc2lkICsgIi9sb2Nrcy8iICsgbGlkLCB0aW1lb3V0PTMwKQogICAgICAgICAgICBpZiBkci5zdGF0dXNfY29kZSA9PSAyMDI6CiAgICAgICAgICAgICAgICBwb2xsKGRyLmhlYWRlcnMuZ2V0KCJMb2NhdGlvbiIsICIiKSkKICAgICAgICBwcmludChmIiAgICBbdW5sb2NrXSB7c25hbWV9OiB7bGVuKGxvY2tzKX0gbG9jayhzKSBlbGltaW5hZG8ocykiKQogICAgZXhjZXB0IEV4Y2VwdGlvbiBhcyBlOgogICAgICAgIHByaW50KGYiICAgIFt1bmxvY2tdIHtzbmFtZX06IGVycm9yIHtlfSIpCgpkZWYgY2xlYW5fZmlsZShmaWQsIG5hbWUpOgogICAgIiIiRWxpbWluYSBsb2NrcyBkZSB0b2RhcyBsYXMgaG9qYXMgY29tcGFyYXRpdmFzIGRlbCBhcmNoaXZvLiIiIgogICAgc2hlZXRzID0gZ2V0X3NoZWV0cyhmaWQpCiAgICBza2lwICAgPSBTS0lQX1NIRUVUUyB8IHsiQmFzZXMifQogICAgZm9yIHNuYW1lLCBzaWQgaW4gc2hlZXRzLml0ZW1zKCk6CiAgICAgICAgaWYgc25hbWUgaW4gc2tpcDoKICAgICAgICAgICAgY29udGludWUKICAgICAgICBfdW5sb2NrX3NoZWV0KGZpZCwgc2lkLCBzbmFtZSkKCiMg4pSA4pSA4pSAIENPTkZJR1VSQUNJw5NOIOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgApXT1JLU1BBQ0VfSUQgPSAid18zNDkxM2FhZGFhMzg0MjBlYWJkN2U0ZDM0MWI3OGExYSIKV0RFU0tfQkFTRSAgID0gImh0dHBzOi8vYXBpLmFwcC53ZGVzay5jb20iCgojIOKUgOKUgCBNT0RPIFBSVUVCQSDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIAKIyBQYXJhIHByb2JhciBjb24gdW4gYXJjaGl2byBkZSBub21icmUgbm8gZXN0w6FuZGFyLgojIEVuIHByb2R1Y2Npw7NuIGRlamFyIFRFU1RfTU9ERSA9IEZhbHNlLgpURVNUX01PREUgICAgICA9IEZhbHNlClRFU1RfRklMRV9JRCAgID0gIjE0ZDlmNDRmODc5NjQwY2E5ZWZkMWQxNGQ3ZmQ5MzkzIiAgIyBFMjE1X0lORF8wOS0yMDI2X0Jhc2UgTm90YXMgQ0dFQ3gKVEVTVF9DT0RFICAgICAgPSAiRTIxNSIKVEVTVF9NTSAgICAgICAgPSAiMDkiClRFU1RfWVlZWSAgICAgID0gIjIwMjYiClRFU1RfU1VGRklYICAgID0gIkJhc2UgTm90YXMgQ0dFQ3giCiMg4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSACgojIOKUgOKUgCBFWENFUENJw5NOIERFIFBSVUVCQSDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIAKIyBDdWFuZG8gU09VUkNFX0NPREVfT1ZFUlJJREUgZXN0w6EgZGVmaW5pZG8sIGFsIHByb2Nlc2FyIGVsIGFyY2hpdm8gaW5kaWNhZG8KIyBlbiBPVkVSUklERV9UQVJHRVQsIGxhcyBmdWVudGVzIHNlIGJ1c2NhbiB1c2FuZG8gU09VUkNFX0NPREVfT1ZFUlJJREUgZW4KIyBsdWdhciBkZWwgY8OzZGlnbyByZWFsIGRlbCBhcmNoaXZvIGRlc3Rpbm8uCiMgU09MTyBQQVJBIFBSVUVCQVMg4oCUIGRlamFyIGVuIE5vbmUgZW4gcHJvZHVjY2nDs24uCk9WRVJSSURFX1RBUkdFVCAgICAgID0gKCJFMzAwIiwgIjAzIiwgIjIwMjYiKSAgICMgKGNvZGUsIG1tLCB5eXl5KSBkZWwgYXJjaGl2byBkZXN0aW5vClNPVVJDRV9DT0RFX09WRVJSSURFID0gIkUyMDAiICAgICAgICAgICAgICAgICAgICAjIGPDs2RpZ28gYSB1c2FyIGFsIGJ1c2NhciBmdWVudGVzCiMg4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSACgpGVUxMX0NPUFlfUEFJUlMgPSB7CiAgICAiNzkuLSBQcsOpc3RhbW9zIGJhbmNhcmlvcyAtIGRlc2dsb3NlIGRlIG1vbmVkYXMgKGIpIjoKICAgICI3OC4tIFByw6lzdGFtb3MgYmFuY2FyaW9zIC0gZGVzZ2xvc2UgZGUgbW9uZWRhcyAoYikiLAp9CgojIEFsaWFzIGRlIGhvamFzOiBub21icmUgZW4gdGFyZ2V0IOKGkiBub21icmUgZW4gZnVlbnRlIChjdWFuZG8gZGlmaWVyZW4gZW50cmUgcGVyw61vZG9zKQpTSEVFVF9BTElBU0VTID0gewogICAgIjIwLi0gUmVzdW1lbiBkZSBlc3RyYXRpZmljYWNpw7NuIGRlIGxhIGNhcnRlcmEgYnJ1dGEiOgogICAgIjIwLi0gQ3VlbnRhcyBwb3IgY29icmFyIGEgZW50aWRhZGVzIHJlbGFjaW9uYWRhcyIsCn0KCiMgSG9qYXMgY29uIGJsb3F1ZSBjb21wYXJhdGl2byBlbiBmaWxhcyBmaWphcyAobm8gZGV0ZWN0YWJsZXMgcG9yIGZlY2hhIGVuIGNvbCBCKS4KIyBGb3JtYXRvOiBub21icmVfaG9qYSDihpIgKHNyY19yb3dfc3RhcnQsIHNyY19yb3dfZW5kLCB0Z3Rfcm93X3N0YXJ0LCB0Z3Rfcm93X2VuZCkKIyBUb2RvcyBsb3Mgw61uZGljZXMgc29uIGJhc2UtMCB5IGVsIHJhbmdvIGVzIFtzdGFydCwgZW5kKSBleGNsdXNpdm8uCiMgTGEgZnVlbnRlIHNpZW1wcmUgZXMgImJhbGFuY2UiIChwZXLDrW9kbyBwcmlvcl9lbmQpLgpCTE9DS19DT1BZX1NIRUVUUyA9IHsKICAgICI2MC4tIEN1YWRybyBtb3ZpbWllbnRvIGFjdGl2byBmaWpvIjogICAgICAgICAgICAgICAgICAgICAgICAgICgxMSwgMzYsIDUxLCA3NiksCiAgICAiNjIuLSBQcm9waWVkYWRlcywgcGxhbnRhIHkgZXF1aXBvcyBlbiBhcnJlbmRhbWllbnRvLCBuZXRvIjogICAoMzEsIDQ0LCA0NiwgNTkpLAp9CgpTS0lQX1NIRUVUUyA9IHsKICAgICJDUCIsIkJhc2VzIiwiUXVlcnkgQlBDIiwiUXVlcnkgSEFOQSBBRiIsIlJlcG9ydGUgZW4gJCIsCiAgICAiUXVlcnkgLSBIQU5BIC0gRGV1ZG9yZXMiLCJBLi0gQWN0aXZvcyBQUFQiLAogICAgIkIuLSBQYXRyaW1vbmlvIHkgUGFzaXZvcyBQUFQiLCJDLi0gRXN0YWRvIGRlIHJlc3VsdGFkbyBwb3IgZnVuY2nDs24gUFBUIiwKICAgICJFMSBSZXMgQWN1bXVsYWRvIiwiRjEgQ3VhZHJhamUgSG9qYSBBLi0gU2FsZG8gSW5pY2lhbCBkZSBDYWphIiwKfQojIOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgAoKc2Vzc2lvbiA9IGdldF9zZXNzaW9uKCkKc2Vzc2lvbi5oZWFkZXJzLnVwZGF0ZSh7IlgtVmVyc2lvbiI6ICIyMDIyLTAxLTAxIn0pCgpfbGFzdF90b2tlbiA9IFt0aW1lLnRpbWUoKV0KZGVmIHJlZnJlc2hfdG9rZW4oKToKICAgIGlmIHRpbWUudGltZSgpIC0gX2xhc3RfdG9rZW5bMF0gPiA0ODA6CiAgICAgICAgbnMgPSBnZXRfc2Vzc2lvbigpCiAgICAgICAgbnMuaGVhZGVycy51cGRhdGUoeyJYLVZlcnNpb24iOiAiMjAyMi0wMS0wMSJ9KQogICAgICAgIHNlc3Npb24uaGVhZGVycy51cGRhdGUobnMuaGVhZGVycykKICAgICAgICBfbGFzdF90b2tlblswXSA9IHRpbWUudGltZSgpCiAgICAgICAgcHJpbnQoIiAgW1Rva2VuIHJlbm92YWRvXSIpCgojIOKUgOKUgOKUgCBIRUxQRVJTIOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgApkZWYgY29sX2xldHRlcihpZHgpOgogICAgaWYgaWR4IDwgMjY6IHJldHVybiBjaHIoNjUraWR4KQogICAgcmV0dXJuIGNocig2NCtpZHgvLzI2KStjaHIoNjUraWR4JTI2KQoKZGVmIGdldF9zaGVldHMoc3NfaWQpOgogICAgcmVzdWx0ID0ge30KICAgIHVybCA9IFdERVNLX0JBU0UrIi9wbGF0Zm9ybS92MS9zcHJlYWRzaGVldHMvIitzc19pZCsiL3NoZWV0cyIKICAgIGZvciBfIGluIHJhbmdlKDIwKToKICAgICAgICB0cnk6CiAgICAgICAgICAgIHIgICAgPSBzZXNzaW9uLmdldCh1cmwsIHRpbWVvdXQ9OTApCiAgICAgICAgICAgIGRhdGEgPSByLmpzb24oKQogICAgICAgICAgICBmb3IgcyBpbiBkYXRhLmdldCgiZGF0YSIsIFtdKToKICAgICAgICAgICAgICAgIHJlc3VsdFtzWyJuYW1lIl1dID0gc1siaWQiXQogICAgICAgICAgICB1cmwgPSBkYXRhLmdldCgiQG5leHRMaW5rIikKICAgICAgICAgICAgaWYgbm90IHVybDoKICAgICAgICAgICAgICAgIHJldHVybiByZXN1bHQKICAgICAgICBleGNlcHQgRXhjZXB0aW9uOgogICAgICAgICAgICB0aW1lLnNsZWVwKDUpCiAgICByZXR1cm4gcmVzdWx0CgpkZWYgcmVhZF9zaGVldChzc19pZCwgc2hlZXRfaWQpOgogICAgdXJsID0gKFdERVNLX0JBU0UrIi9wbGF0Zm9ybS92MS9zcHJlYWRzaGVldHMvIitzc19pZCsiL3NoZWV0cy8iK3NoZWV0X2lkCiAgICAgICAgICAgKyIvc2hlZXRkYXRhPyRmaWVsZHM9Y2VsbHMuY2FsY3VsYXRlZFZhbHVlLGNlbGxzLnZhbHVlJiRtYXhjZWxsc3BlcnBhZ2U9NTAwMDAiKQogICAgZm9yIF8gaW4gcmFuZ2UoNSk6CiAgICAgICAgdHJ5OgogICAgICAgICAgICByZXR1cm4gc2Vzc2lvbi5nZXQodXJsLCB0aW1lb3V0PTEyMCkuanNvbigpLmdldCgiZGF0YSIse30pLmdldCgiY2VsbHMiLFtdKQogICAgICAgIGV4Y2VwdCBFeGNlcHRpb246IHRpbWUuc2xlZXAoNSkKICAgIHJldHVybiBbXQoKZGVmIHBvbGwobG9jYXRpb24pOgogICAgdXJsID0gbG9jYXRpb24gaWYgbG9jYXRpb24uc3RhcnRzd2l0aCgiaHR0cCIpIGVsc2UgV0RFU0tfQkFTRStsb2NhdGlvbgogICAgZm9yIGF0dGVtcHQgaW4gcmFuZ2UoMTIwKToKICAgICAgICB0aW1lLnNsZWVwKDMpCiAgICAgICAgdHJ5OgogICAgICAgICAgICBib2R5ID0gc2Vzc2lvbi5nZXQodXJsLCB0aW1lb3V0PTYwKS5qc29uKCkKICAgICAgICAgICAgZGF0YSA9IGJvZHkuZ2V0KCJkYXRhIiwgYm9keSkKICAgICAgICAgICAgc3QgICA9IGRhdGEuZ2V0KCJzdGF0dXMiLCBib2R5LmdldCgic3RhdHVzIiwgIiIpKQogICAgICAgICAgICBpZiBzdCA9PSAiY29tcGxldGVkIjoKICAgICAgICAgICAgICAgIHJldHVybiBUcnVlCiAgICAgICAgICAgIGlmIHN0IGluICgiZmFpbGVkIiwgImVycm9yIik6CiAgICAgICAgICAgICAgICBtc2cgPSAoZGF0YS5nZXQoImVycm9yIikgb3IgZGF0YS5nZXQoIm1lc3NhZ2UiKSBvcgogICAgICAgICAgICAgICAgICAgICAgIGJvZHkuZ2V0KCJlcnJvciIpIG9yIGJvZHkuZ2V0KCJtZXNzYWdlIikgb3IgIiIpCiAgICAgICAgICAgICAgICBpZiBtc2c6CiAgICAgICAgICAgICAgICAgICAgcHJpbnQoZiIgICAgICBbV29ya2l2YSBlcnJvcl0ge3N0cihtc2cpWzoxMjBdfSIpCiAgICAgICAgICAgICAgICByZXR1cm4gRmFsc2UKICAgICAgICBleGNlcHQgRXhjZXB0aW9uIGFzIGU6CiAgICAgICAgICAgIGlmIGF0dGVtcHQgPT0gMzk6CiAgICAgICAgICAgICAgICBwcmludChmIiAgICAgIFtwb2xsIGV4Y2VwdGlvbl0ge2V9IikKICAgIHJldHVybiBGYWxzZQoKZGVmIHB1dF9jb2woc3NfaWQsIHNpZCwgY29sX2lkeCwgdmFsdWVzLCBsYWJlbD0iIik6CiAgICByZWZyZXNoX3Rva2VuKCkKICAgIGNsID0gY29sX2xldHRlcihjb2xfaWR4KQoKICAgICMgQ29uc3RydWlyIGNodW5rcyBjb250aWd1b3MgZGUgdmFsb3JlcyBuby1Ob25lIHBhcmEgZXZpdGFyIGVudmlhciBOb25lIGEgbGEgQVBJCiAgICBjaHVua3MgPSBbXQogICAgaSA9IDAKICAgIHdoaWxlIGkgPCBsZW4odmFsdWVzKToKICAgICAgICBpZiB2YWx1ZXNbaV0gaXMgbm90IE5vbmU6CiAgICAgICAgICAgIGogPSBpCiAgICAgICAgICAgIHdoaWxlIGogPCBsZW4odmFsdWVzKSBhbmQgdmFsdWVzW2pdIGlzIG5vdCBOb25lOgogICAgICAgICAgICAgICAgaiArPSAxCiAgICAgICAgICAgIGNodW5rcy5hcHBlbmQoKGksIHZhbHVlc1tpOmpdKSkKICAgICAgICAgICAgaSA9IGoKICAgICAgICBlbHNlOgogICAgICAgICAgICBpICs9IDEKCiAgICBuID0gc3VtKDEgZm9yIHYgaW4gdmFsdWVzIGlmIHYgaXMgbm90IE5vbmUpCiAgICBpZiBub3QgY2h1bmtzOgogICAgICAgIHJldHVybiBUcnVlCgogICAgb2tfYWxsID0gVHJ1ZQogICAgZm9yIHN0YXJ0LCBjaHVuayBpbiBjaHVua3M6CiAgICAgICAgcjEgID0gc3RhcnQgKyAxCiAgICAgICAgcjIgID0gcjEgKyBsZW4oY2h1bmspIC0gMQogICAgICAgIHJuZyA9IGYie2NsfXtyMX06e2NsfXtyMn0iCiAgICAgICAgcnAgID0gc2Vzc2lvbi5wdXQoV0RFU0tfQkFTRSsiL3BsYXRmb3JtL3YxL3NwcmVhZHNoZWV0cy8iK3NzX2lkKyIvc2hlZXRzLyIrc2lkCiAgICAgICAgICAgICAgICAgICAgICAgICAgKyIvdmFsdWVzLyIrcm5nLAogICAgICAgICAgICAgICAgICAgICAgICAgIGpzb249eyJ2YWx1ZXMiOiBbW3ZdIGZvciB2IGluIGNodW5rXX0sIHRpbWVvdXQ9MTIwKQogICAgICAgIGlmIHJwLnN0YXR1c19jb2RlID09IDIwMjoKICAgICAgICAgICAgb2sgPSBwb2xsKHJwLmhlYWRlcnMuZ2V0KCJMb2NhdGlvbiIsICIiKSkKICAgICAgICAgICAgaWYgbm90IG9rOgogICAgICAgICAgICAgICAgb2tfYWxsID0gRmFsc2UKICAgICAgICBlbHNlOgogICAgICAgICAgICBwcmludChmIiAgICBFUlIgSFRUUCB7cnAuc3RhdHVzX2NvZGV9OiB7cnAudGV4dFs6NjBdfSIpCiAgICAgICAgICAgIG9rX2FsbCA9IEZhbHNlCgogICAgcHJpbnQoZiIgICAgeydPSycgaWYgb2tfYWxsIGVsc2UgJ0VSUid9IGNvbCB7Y2x9OiB7bn0gdmFscyBbe2xhYmVsfV0iKQogICAgcmV0dXJuIG9rX2FsbAoKZGVmIHB1dF9jb2xfcmFuZ2Uoc3NfaWQsIHNpZCwgY29sX2lkeCwgc3RhcnRfcm93LCB2YWx1ZXMsIGxhYmVsPSIiKToKICAgICIiIkVzY3JpYmUgdW4gc2xpY2UgZGUgY29sdW1uYSBjb21lbnphbmRvIGVuIHN0YXJ0X3JvdyAoYmFzZS0wKS4iIiIKICAgIHJlZnJlc2hfdG9rZW4oKQogICAgY2wgPSBjb2xfbGV0dGVyKGNvbF9pZHgpCiAgICByMSA9IHN0YXJ0X3JvdyArIDEgICAgICAgICAgIyBiYXNlLTEKICAgIHIyID0gcjEgKyBsZW4odmFsdWVzKSAtIDEKICAgIHJuZyA9IGYie2NsfXtyMX06e2NsfXtyMn0iCiAgICBycCAgPSBzZXNzaW9uLnB1dChXREVTS19CQVNFKyIvcGxhdGZvcm0vdjEvc3ByZWFkc2hlZXRzLyIrc3NfaWQrIi9zaGVldHMvIitzaWQKICAgICAgICAgICAgICAgICAgICAgICsiL3ZhbHVlcy8iK3JuZywKICAgICAgICAgICAgICAgICAgICAgIGpzb249eyJ2YWx1ZXMiOltbdl0gZm9yIHYgaW4gdmFsdWVzXX0sIHRpbWVvdXQ9MTIwKQogICAgaWYgcnAuc3RhdHVzX2NvZGUgPT0gMjAyOgogICAgICAgIG9rID0gcG9sbChycC5oZWFkZXJzLmdldCgiTG9jYXRpb24iLCIiKSkKICAgICAgICBuICA9IHN1bSgxIGZvciB2IGluIHZhbHVlcyBpZiB2IGlzIG5vdCBOb25lKQogICAgICAgIHByaW50KGYiICAgIHsnT0snIGlmIG9rIGVsc2UgJ0VSUid9IGNvbCB7Y2x9W3tyMX06e3IyfV06IHtufSB2YWxzIFt7bGFiZWx9XSIpCiAgICAgICAgcmV0dXJuIG9rCiAgICBwcmludChmIiAgICBFUlIgSFRUUCB7cnAuc3RhdHVzX2NvZGV9OiB7cnAudGV4dFs6NjBdfSIpCiAgICByZXR1cm4gRmFsc2UKCmRlZiBpc19mb3JtdWxhKHJvdywgY29sKToKICAgIGMgPSByb3dbY29sXSBpZiBjb2wgPCBsZW4ocm93KSBlbHNlIHt9CiAgICByZXR1cm4gc3RyKGMuZ2V0KCJ2YWx1ZSIsIiIpIGlmIGlzaW5zdGFuY2UoYyxkaWN0KSBlbHNlICIiKS5zdGFydHN3aXRoKCI9IikKCmRlZiBnZXRfY3Yocm93LCBjb2wpOgogICAgYyA9IHJvd1tjb2xdIGlmIGNvbCA8IGxlbihyb3cpIGVsc2Uge30KICAgIHJldHVybiBjLmdldCgiY2FsY3VsYXRlZFZhbHVlIikgaWYgaXNpbnN0YW5jZShjLGRpY3QpIGVsc2UgTm9uZQoKIyDilIDilIDilIAgUEFTTyAxOiBDYXJnYXIgdG9kb3MgbG9zIGFyY2hpdm9zIGRlbCB3b3Jrc3BhY2Ug4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSACmRlZiBsb2FkX2FsbF9maWxlcygpOgogICAgYWxsX2ZpbGVzID0ge30KICAgIHVybCA9IFdERVNLX0JBU0UrIi9wbGF0Zm9ybS92MS9maWxlcz93b3Jrc3BhY2VJZD0iK1dPUktTUEFDRV9JRCsiJmxpbWl0PTEwMCIKICAgIHdoaWxlIHVybDoKICAgICAgICByICAgID0gc2Vzc2lvbi5nZXQodXJsLCB0aW1lb3V0PTkwKQogICAgICAgIGRhdGEgPSByLmpzb24oKQogICAgICAgIGZvciBmIGluIGRhdGEuZ2V0KCJkYXRhIixbXSk6CiAgICAgICAgICAgIGFsbF9maWxlc1tmWyJuYW1lIl1dID0gZlsiaWQiXQogICAgICAgIHVybCA9IGRhdGEuZ2V0KCJAbmV4dExpbmsiKQogICAgcmV0dXJuIGFsbF9maWxlcwoKIyDilIDilIDilIAgUEFTTyAyOiBFbmNvbnRyYXIgYXJjaGl2b3MgZGVzdGlubyBkZWwgcGVyw61vZG8g4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSACmRlZiBmaW5kX3RhcmdldF9maWxlcyhtbSwgeXl5eSwgdGlwbywgYWxsX2ZpbGVzKToKICAgICIiIgogICAgQnVzY2EgdG9kb3MgbG9zIGFyY2hpdm9zIGRlbCBwZXLDrW9kbyB5IHRpcG8gaW5kaWNhZG8gKElORCBvIENPTlNPKS4KICAgIFBhdHLDs246IEV7Y29kZX1fe3RpcG99X3tNTX0te1lZWVl9X0Jhc2UgTm90YXMge3N1ZmZpeH0KICAgIFNpbiBwcmVmaWpvcyAoQ0hOKSwgKExDKSwgZXRjLiBBY2VwdGEgJy0nIG8gJ18nIGNvbW8gc2VwYXJhZG9yIGRlIGZlY2hhLgogICAgIiIiCiAgICBwYXR0ZXJuID0gcmUuY29tcGlsZShyZiJeRVxkK197dGlwb31fe21tfVstX117eXl5eX1fQmFzZSBOb3RhcyAuKyQiKQogICAgdGFyZ2V0cyA9IFtdCiAgICBmb3IgbmFtZSwgZmlkIGluIGFsbF9maWxlcy5pdGVtcygpOgogICAgICAgIGlmIHBhdHRlcm4ubWF0Y2gobmFtZSk6CiAgICAgICAgICAgIHBhcnNlZCA9IHJlLm1hdGNoKHJmIihFXGQrKV8oe3RpcG99KV8oXGR7ezJ9fSlbLV9dKFxke3s0fX0pXyguKikiLCBuYW1lKQogICAgICAgICAgICBpZiBwYXJzZWQ6CiAgICAgICAgICAgICAgICB0YXJnZXRzLmFwcGVuZCh7CiAgICAgICAgICAgICAgICAgICAgImlkIjogICAgIGZpZCwKICAgICAgICAgICAgICAgICAgICAibmFtZSI6ICAgbmFtZSwKICAgICAgICAgICAgICAgICAgICAiY29kZSI6ICAgcGFyc2VkLmdyb3VwKDEpLAogICAgICAgICAgICAgICAgICAgICJ0aXBvIjogICBwYXJzZWQuZ3JvdXAoMiksCiAgICAgICAgICAgICAgICAgICAgIm1tIjogICAgIHBhcnNlZC5ncm91cCgzKSwKICAgICAgICAgICAgICAgICAgICAieXl5eSI6ICAgcGFyc2VkLmdyb3VwKDQpLAogICAgICAgICAgICAgICAgICAgICJzdWZmaXgiOiBwYXJzZWQuZ3JvdXAoNSksCiAgICAgICAgICAgICAgICB9KQogICAgcmV0dXJuIHNvcnRlZCh0YXJnZXRzLCBrZXk9bGFtYmRhIHg6IHhbImNvZGUiXSkKCiMg4pSA4pSA4pSAIFBBU08gMzogTGVlciBCYXNlcyBkZWwgYXJjaGl2byBkZXN0aW5vIOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgApkZWYgcmVhZF9iYXNlcyh0YXJnZXRfaWQsIHNoZWV0cyk6CiAgICBjZWxscyA9IHJlYWRfc2hlZXQodGFyZ2V0X2lkLCBzaGVldHNbIkJhc2VzIl0pCiAgICByZXN1bHQgPSB7fQogICAgcm93X21hcCA9IHsKICAgICAgICAxMzogKCJjdXJyZW50X2VuZCIsInByaW9yX2VuZCIpLAogICAgICAgIDE0OiAoImVlcnJfc3RhcnQiLCJwcmlvcl9lZXJyX3N0YXJ0IiksCiAgICAgICAgMTU6ICgiZWVycl9lbmQiLCJwcmlvcl9lZXJyX2VuZCIpLAogICAgICAgIDE2OiAoInF1YXJ0ZXJfc3RhcnQiLCJwcmlvcl9xdWFydGVyX3N0YXJ0IiksCiAgICAgICAgMTc6ICgicHJldl9wZXJpb2RfZW5kIiwicHJpb3JfcHJldl9wZXJpb2RfZW5kIiksCiAgICB9CiAgICBmb3Igcm93X2lkeCwoa2V5X2Msa2V5X3ApIGluIHJvd19tYXAuaXRlbXMoKToKICAgICAgICBpZiByb3dfaWR4ID49IGxlbihjZWxscyk6IGNvbnRpbnVlCiAgICAgICAgcm93ID0gY2VsbHNbcm93X2lkeF0KICAgICAgICBmb3IgY29sX2lkeCxrZXkgaW4gWygzLGtleV9jKSwoNSxrZXlfcCldOgogICAgICAgICAgICBpZiBjb2xfaWR4IDwgbGVuKHJvdyk6CiAgICAgICAgICAgICAgICBjICA9IHJvd1tjb2xfaWR4XQogICAgICAgICAgICAgICAgY3YgPSBjLmdldCgiY2FsY3VsYXRlZFZhbHVlIiwiIikgaWYgaXNpbnN0YW5jZShjLGRpY3QpIGVsc2UgIiIKICAgICAgICAgICAgICAgIGlmIGN2OiByZXN1bHRba2V5XSA9IHN0cihjdikKICAgIHJldHVybiByZXN1bHQKCiMg4pSA4pSA4pSAIFBBU08gNDogQnVzY2FyIGFyY2hpdm9zIGZ1ZW50ZSDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIAKZGVmIGRhdGVfdG9fbW1feXl5eShkYXRlX3N0cik6CiAgICBwYXJ0cyA9IHN0cihkYXRlX3N0cikuc3BsaXQoIi0iKQogICAgcmV0dXJuIChwYXJ0c1sxXSwgcGFydHNbMF0pIGlmIGxlbihwYXJ0cykgPj0gMiBlbHNlIChOb25lLCBOb25lKQoKZGVmIGZpbmRfc291cmNlX2ZpbGVzKHBhcnNlZCwgYmFzZXMsIGFsbF9maWxlcyk6CiAgICBjb2RlLCBzdWZmaXggPSBwYXJzZWRbImNvZGUiXSwgcGFyc2VkWyJzdWZmaXgiXQogICAgdGlwbyA9IHBhcnNlZC5nZXQoInRpcG8iLCAiSU5EIikKICAgIG1tX2N1cnIsIHl5eXlfY3VyciA9IHBhcnNlZFsibW0iXSwgcGFyc2VkWyJ5eXl5Il0KCiAgICAjIEV4Y2VwY2nDs24gZGUgcHJ1ZWJhOiBzdXN0aXR1aXIgY8OzZGlnbyBkZSBmdWVudGUgc2kgYXBsaWNhCiAgICBpZiAoU09VUkNFX0NPREVfT1ZFUlJJREUgYW5kCiAgICAgICAgICAgIChjb2RlLCBtbV9jdXJyLCB5eXl5X2N1cnIpID09IE9WRVJSSURFX1RBUkdFVCk6CiAgICAgICAgcHJpbnQoZiIgIFtFWENFUENJw5NOIFBSVUVCQV0gRnVlbnRlcyBidXNjYWRhcyBjb21vIHtTT1VSQ0VfQ09ERV9PVkVSUklERX0gZW4gdmV6IGRlIHtjb2RlfSIpCiAgICAgICAgY29kZSA9IFNPVVJDRV9DT0RFX09WRVJSSURFCgogICAgZGVmIGZpbmQobW0sIHl5eXksIGxhYmVsKToKICAgICAgICAjIE1pc21vIHRpcG8gKElORC9DT05TTykgcXVlIGVsIGRlc3Rpbm8uIEludGVudGEgYW1ib3Mgc2VwYXJhZG9yZXMuCiAgICAgICAgZm9yIHNlcCBpbiBbIi0iLCAiXyJdOgogICAgICAgICAgICBuYW1lID0gZiJ7Y29kZX1fe3RpcG99X3ttbX17c2VwfXt5eXl5fV97c3VmZml4fSIKICAgICAgICAgICAgZmlkICA9IGFsbF9maWxlcy5nZXQobmFtZSkKICAgICAgICAgICAgaWYgZmlkOgogICAgICAgICAgICAgICAgcHJpbnQoZiIgICAg4pyTOiB7bmFtZX0iKQogICAgICAgICAgICAgICAgcmV0dXJuIGZpZAogICAgICAgIHByaW50KGYiICAgIOKclyBubyBlbmNvbnRyYWRvOiB7Y29kZX1fe3RpcG99X3ttbX0te3l5eXl9X3tzdWZmaXh9IikKICAgICAgICByZXR1cm4gTm9uZQoKICAgIHNvdXJjZXMgPSB7fQogICAgbW1fYiwgIHl5X2IgID0gZGF0ZV90b19tbV95eXl5KGJhc2VzLmdldCgicHJpb3JfZW5kIiwiIikpCiAgICBtbV9lLCAgeXlfZSAgPSBkYXRlX3RvX21tX3l5eXkoYmFzZXMuZ2V0KCJwcmlvcl9lZXJyX2VuZCIsIiIpKQogICAgbW1fcSwgIHl5X3EgID0gZGF0ZV90b19tbV95eXl5KGJhc2VzLmdldCgicHJpb3JfcHJldl9wZXJpb2RfZW5kIiwiIikpCiAgICBtbV9wcCwgeXlfcHAgPSBkYXRlX3RvX21tX3l5eXkoYmFzZXMuZ2V0KCJwcmV2X3BlcmlvZF9lbmQiLCIiKSkKCiAgICBpZiBtbV9iOgogICAgICAgIHNvdXJjZXNbImJhbGFuY2UiXSA9IGZpbmQobW1fYiwgeXlfYiwgZiJCYWxhbmNlIERJQy17eXlfYn0iKQogICAgaWYgbW1fZSBhbmQgKG1tX2UseXlfZSkgIT0gKG1tX2IseXlfYik6CiAgICAgICAgc291cmNlc1siZWVyciJdID0gZmluZChtbV9lLCB5eV9lLCBmIkVFUlIge21tX2V9LXt5eV9lfSIpCiAgICBlbHNlOgogICAgICAgIHNvdXJjZXNbImVlcnIiXSA9IHNvdXJjZXMuZ2V0KCJiYWxhbmNlIikKICAgIGlmIG1tX3EgYW5kIChtbV9xLHl5X3EpIG5vdCBpbiBbKG1tX2IseXlfYiksKG1tX2UseXlfZSldOgogICAgICAgIHNvdXJjZXNbInF1YXJ0ZXJfcHJldiJdID0gZmluZChtbV9xLCB5eV9xLCBmIlExLXByZXYge21tX3F9LXt5eV9xfSIpCiAgICBpZiBtbV9wcCBhbmQgeXlfcHAgPT0geXl5eV9jdXJyIGFuZCBtbV9wcCAhPSBtbV9jdXJyOgogICAgICAgIHNvdXJjZXNbImN1cnJfc3VicGVyaW9kIl0gPSBmaW5kKG1tX3BwLCB5eV9wcCwgZiJTdWItcGVyw61vZG8gYWN0dWFsIHttbV9wcH0te3l5X3BwfSIpCgogICAgcmV0dXJuIHNvdXJjZXMKCiMg4pSA4pSA4pSAIFBBU08gNTogQ2FyZ2FyIGRhdG9zIGRlIGZ1ZW50ZXMg4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSACmRlZiBsb2FkX3NvdXJjZXMoc291cmNlcyk6CiAgICBsb2FkZWQgPSB7fQogICAgZm9yIGtleSwgZmlkIGluIHNvdXJjZXMuaXRlbXMoKToKICAgICAgICBpZiBub3QgZmlkIG9yIGZpZCBpbiBsb2FkZWQ6IGNvbnRpbnVlCiAgICAgICAgc2hlZXRzID0gZ2V0X3NoZWV0cyhmaWQpCiAgICAgICAgbG9hZGVkW2ZpZF0gPSB7InNoZWV0cyI6IHNoZWV0cywgImNlbGxzIjoge319CiAgICAgICAgZm9yIHNuYW1lLCBzaWQgaW4gc2hlZXRzLml0ZW1zKCk6CiAgICAgICAgICAgIGxvYWRlZFtmaWRdWyJjZWxscyJdW3NuYW1lXSA9IHJlYWRfc2hlZXQoZmlkLCBzaWQpCiAgICAgICAgcHJpbnQoZiIgICAgQ2FyZ2FkbyAoe2tleX0pOiB7bGVuKHNoZWV0cyl9IGhvamFzIikKICAgIHJldHVybiBsb2FkZWQKCiMg4pSA4pSA4pSAIFBBU08gNjogRGV0ZWN0YXIgY29sdW1uYXMgYSBsbGVuYXIg4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSAClBFUklPRF9QQVRURVJOUyA9IFsKICAgICgicHJpb3JfZWVycl9zdGFydCIsICAgICJwcmlvcl9lZXJyX2VuZCIsICAgICAgICAiZWVyciIpLAogICAgKCJwcmlvcl9lZXJyX3N0YXJ0IiwgICAgInByaW9yX3ByZXZfcGVyaW9kX2VuZCIsICJxdWFydGVyX3ByZXYiKSwKICAgICgiIiwgICAgICAgICAgICAgICAgICAgICJwcmlvcl9lbmQiLCAgICAgICAgICAgICAiYmFsYW5jZSIpLAogICAgKCJlZXJyX3N0YXJ0IiwgICAgICAgICAgInByZXZfcGVyaW9kX2VuZCIsICAgICAgICJjdXJyX3N1YnBlcmlvZCIpLApdCgpkZWYgZGV0ZWN0X2NvbXBfY29scyhjZWxscywgYmFzZXMpOgogICAgY29sX3RleHRzID0ge30KICAgIGZvciByb3cgaW4gY2VsbHNbOjhdOgogICAgICAgIGZvciBqLCBjIGluIGVudW1lcmF0ZShyb3cpOgogICAgICAgICAgICBpZiBpc2luc3RhbmNlKGMsZGljdCk6CiAgICAgICAgICAgICAgICBmb3IgdmFsIGluIFtzdHIoYy5nZXQoImNhbGN1bGF0ZWRWYWx1ZSIsIiIpKSwgc3RyKGMuZ2V0KCJ2YWx1ZSIsIiIpKV06CiAgICAgICAgICAgICAgICAgICAgaWYgdmFsIGFuZCB2YWwgbm90IGluICgiTm9uZSIsIiIpOgogICAgICAgICAgICAgICAgICAgICAgICBjb2xfdGV4dHMuc2V0ZGVmYXVsdChqLFtdKS5hcHBlbmQodmFsLmxvd2VyKCkpCgogICAgZGF0ZV9maWVsZHMgPSB7CiAgICAgICAgInByaW9yX2VuZCI6ICAgICAgICAgICAgIGJhc2VzLmdldCgicHJpb3JfZW5kIiwiIiksCiAgICAgICAgInByaW9yX2VlcnJfZW5kIjogICAgICAgIGJhc2VzLmdldCgicHJpb3JfZWVycl9lbmQiLCIiKSwKICAgICAgICAicHJpb3JfZWVycl9zdGFydCI6ICAgICAgYmFzZXMuZ2V0KCJwcmlvcl9lZXJyX3N0YXJ0IiwiIiksCiAgICAgICAgInByaW9yX3ByZXZfcGVyaW9kX2VuZCI6IGJhc2VzLmdldCgicHJpb3JfcHJldl9wZXJpb2RfZW5kIiwiIiksCiAgICAgICAgInByZXZfcGVyaW9kX2VuZCI6ICAgICAgIGJhc2VzLmdldCgicHJldl9wZXJpb2RfZW5kIiwiIiksCiAgICAgICAgImVlcnJfc3RhcnQiOiAgICAgICAgICAgIGJhc2VzLmdldCgiZWVycl9zdGFydCIsIiIpLAogICAgfQoKICAgIHJlc3VsdCA9IHt9CiAgICBjdXJyX2VuZCA9IGJhc2VzLmdldCgiY3VycmVudF9lbmQiLCJfX1hfXyIpCiAgICBlZXJyX2VuZCA9IGJhc2VzLmdldCgiZWVycl9lbmQiLCJfX1hfXyIpCgogICAgZm9yIGNvbF9pZHgsIHRleHRzIGluIGNvbF90ZXh0cy5pdGVtcygpOgogICAgICAgIGNvbWJpbmVkID0gIiAiLmpvaW4odGV4dHMpCiAgICAgICAgaWYgYW55KGsgaW4gY29tYmluZWQgZm9yIGsgaW4gW2N1cnJfZW5kLCBlZXJyX2VuZCwgInF1ZXJ5Iiwic3VtaWYiLCJicGMiLCJhY3R1YWwiXSk6CiAgICAgICAgICAgIGNvbnRpbnVlCiAgICAgICAgZm9yIHNrdywgZWt3LCBwZXJpb2Rfa2V5IGluIFBFUklPRF9QQVRURVJOUzoKICAgICAgICAgICAgc2QgPSBkYXRlX2ZpZWxkcy5nZXQoc2t3LCBza3cpLmxvd2VyKCkKICAgICAgICAgICAgZWQgPSBkYXRlX2ZpZWxkcy5nZXQoZWt3LCBla3cpLmxvd2VyKCkKICAgICAgICAgICAgaWYgKG5vdCBzZCBvciBzZCBpbiBjb21iaW5lZCkgYW5kIChlZCBhbmQgZWQgaW4gY29tYmluZWQpOgogICAgICAgICAgICAgICAgcmVzdWx0W2NvbF9pZHhdID0gcGVyaW9kX2tleQogICAgICAgICAgICAgICAgYnJlYWsKICAgIHJldHVybiByZXN1bHQKCiMg4pSA4pSA4pSAIFBBU08gNmI6IERldGVjY2nDs24gZGUgYmxvcXVlcyB2ZXJ0aWNhbGVzIOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgApkZWYgZGV0ZWN0X3ZlcnRpY2FsX2Jsb2NrcyhjZWxscywgYmFzZXMpOgogICAgIiIiCiAgICBEZXRlY3RhIGhvamFzIGNvbiBibG9xdWVzIGFwaWxhZG9zIHZlcnRpY2FsbWVudGUgKGVqLiBob2phcyAxOSwgMjApLgogICAgQnVzY2EgZW4gY29sIEIgKGlkeCAxKSBUT0RBUyBsYXMgb2N1cnJlbmNpYXMgZGUgY3VycmVudF9lbmQgeSBwcmlvcl9lbmQuCiAgICBSZXRvcm5hIGRpY3QgY29uIGxpc3RhcyBkZSBvY3VycmVuY2lhcywgbyBOb25lIHNpIG5vIGhheSBibG9xdWVzIHbDoWxpZG9zLgogICAgIiIiCiAgICBjdXJyICA9IGJhc2VzLmdldCgiY3VycmVudF9lbmQiLCAiIikKICAgIHByaW9yID0gYmFzZXMuZ2V0KCJwcmlvcl9lbmQiLCAiIikKICAgIGlmIG5vdCBjdXJyIG9yIG5vdCBwcmlvcjoKICAgICAgICByZXR1cm4gTm9uZQogICAgYWN0dWFsX3Jvd3MgPSBbXQogICAgY29tcF9yb3dzICAgPSBbXQogICAgZm9yIGksIHJvdyBpbiBlbnVtZXJhdGUoY2VsbHMpOgogICAgICAgIGN2ID0gc3RyKGdldF9jdihyb3csIDEpIG9yICIiKS5zdHJpcCgpCiAgICAgICAgaWYgY3VyciBpbiBjdjoKICAgICAgICAgICAgYWN0dWFsX3Jvd3MuYXBwZW5kKGkpCiAgICAgICAgaWYgcHJpb3IgaW4gY3Y6CiAgICAgICAgICAgIGNvbXBfcm93cy5hcHBlbmQoaSkKICAgIGlmIG5vdCBhY3R1YWxfcm93cyBvciBub3QgY29tcF9yb3dzOgogICAgICAgIHJldHVybiBOb25lCiAgICBpZiBjb21wX3Jvd3NbMF0gPD0gYWN0dWFsX3Jvd3NbMF06CiAgICAgICAgcmV0dXJuIE5vbmUKICAgIHJldHVybiB7CiAgICAgICAgImFjdHVhbF9zdGFydCI6IGFjdHVhbF9yb3dzWzBdLAogICAgICAgICJjb21wX3N0YXJ0IjogICBjb21wX3Jvd3NbMF0sCiAgICAgICAgImFjdHVhbF9yb3dzIjogIGFjdHVhbF9yb3dzLAogICAgICAgICJjb21wX3Jvd3MiOiAgICBjb21wX3Jvd3MsCiAgICB9CgpkZWYgZmlsbF92ZXJ0aWNhbF9zaGVldCh0YXJnZXRfaWQsIHNpZF90LCB0Z3RfY2VsbHMsIHNyY19jZWxscywgYmxvY2tzLCBiYXNlcyk6CiAgICAiIiIKICAgIENvcGlhIGJsb3F1ZXMgYWN0dWFsZXMgZGVsIGZ1ZW50ZSDihpIgYmxvcXVlcyBjb21wYXJhdGl2b3MgZGVsIHRhcmdldC4KICAgIFBhcmVhciBzdWItYmxvcXVlcyBwb3Igb3JkZW4gZGUgYXBhcmljacOzbiBkZSBwcmlvcl9lbmQgZW4gY29sIEI6CiAgICAgIHNyY19hY3R1YWxfcm93c1tpXSDihpIgdGd0X2NvbXBfcm93c1tpXQogICAgRXN0byBtYW5lamEgaG9qYXMgY29uIG3Dumx0aXBsZXMgc3ViLWJsb3F1ZXMgKGVqLiBob2phIDIwIGNvbiBzZWdtZW50b3MpLgogICAgU29sbyBlc2NyaWJlIGNlbGRhcyBudW3DqXJpY2FzIG5vLWbDs3JtdWxhIGRlbCB0YXJnZXQuCiAgICAiIiIKICAgIHByaW9yID0gYmFzZXMuZ2V0KCJwcmlvcl9lbmQiLCAiIikKCiAgICAjIFRvZGFzIGxhcyBvY3VycmVuY2lhcyBkZSBwcmlvcl9lbmQgZW4gY29sIEIgZGVsIGZ1ZW50ZQogICAgc3JjX2FjdHVhbF9yb3dzID0gW2kgZm9yIGksIHJvdyBpbiBlbnVtZXJhdGUoc3JjX2NlbGxzKQogICAgICAgICAgICAgICAgICAgICAgIGlmIHByaW9yIGluIHN0cihnZXRfY3Yocm93LCAxKSBvciAiIikuc3RyaXAoKV0KICAgIGlmIG5vdCBzcmNfYWN0dWFsX3Jvd3M6CiAgICAgICAgcHJpbnQoIiAgICDihpIgQmxvcXVlIGFjdHVhbCBubyBlbmNvbnRyYWRvIGVuIGZ1ZW50ZSIpCiAgICAgICAgcmV0dXJuIDAKCiAgICB0Z3RfY29tcF9yb3dzID0gYmxvY2tzLmdldCgiY29tcF9yb3dzIiwgW2Jsb2Nrc1siY29tcF9zdGFydCJdXSkKICAgIG5fYmxvY2tzID0gbWluKGxlbihzcmNfYWN0dWFsX3Jvd3MpLCBsZW4odGd0X2NvbXBfcm93cykpCgogICAgIyBDb25zdHJ1aXIgbWFwYSBjb2wg4oaSIHt0Z3Rfcm93OiB2YWx1ZX0gcGFyYSB0b2RvcyBsb3Mgc3ViLWJsb3F1ZXMKICAgIHdyaXRlX21hcCA9IHt9ICAgIyBjb2xfaWR4IOKGkiB7dGd0X3Jvd19pZHg6IHZhbHVlfQogICAgZm9yIGIgaW4gcmFuZ2Uobl9ibG9ja3MpOgogICAgICAgIHNyY19zdGFydCA9IHNyY19hY3R1YWxfcm93c1tiXQogICAgICAgIHRndF9zdGFydCA9IHRndF9jb21wX3Jvd3NbYl0KICAgICAgICBzcmNfZW5kICAgPSBzcmNfYWN0dWFsX3Jvd3NbYisxXSBpZiBiKzEgPCBsZW4oc3JjX2FjdHVhbF9yb3dzKSBlbHNlIGxlbihzcmNfY2VsbHMpCiAgICAgICAgdGd0X2VuZCAgID0gdGd0X2NvbXBfcm93c1tiKzFdICAgaWYgYisxIDwgbGVuKHRndF9jb21wX3Jvd3MpICAgZWxzZSBsZW4odGd0X2NlbGxzKQogICAgICAgIGJsb2NrX2ggICA9IG1pbihzcmNfZW5kIC0gc3JjX3N0YXJ0LCB0Z3RfZW5kIC0gdGd0X3N0YXJ0KQoKICAgICAgICBmb3Igb2Zmc2V0IGluIHJhbmdlKGJsb2NrX2gpOgogICAgICAgICAgICBzaSA9IHNyY19zdGFydCArIG9mZnNldAogICAgICAgICAgICB0aSA9IHRndF9zdGFydCArIG9mZnNldAogICAgICAgICAgICBpZiBzaSA+PSBsZW4oc3JjX2NlbGxzKSBvciB0aSA+PSBsZW4odGd0X2NlbGxzKToKICAgICAgICAgICAgICAgIGJyZWFrCiAgICAgICAgICAgIHJvd19zcmMgPSBzcmNfY2VsbHNbc2ldCiAgICAgICAgICAgIHJvd190Z3QgPSB0Z3RfY2VsbHNbdGldCiAgICAgICAgICAgIGZvciBjb2wgaW4gcmFuZ2UobWF4KGxlbihyb3dfc3JjKSwgbGVuKHJvd190Z3QpKSk6CiAgICAgICAgICAgICAgICBpZiBpc19mb3JtdWxhKHJvd190Z3QsIGNvbCk6CiAgICAgICAgICAgICAgICAgICAgY29udGludWUKICAgICAgICAgICAgICAgIHZhbCA9IGdldF9jdihyb3dfc3JjLCBjb2wpCiAgICAgICAgICAgICAgICBpZiBub3QgaXNpbnN0YW5jZSh2YWwsIChpbnQsIGZsb2F0KSk6CiAgICAgICAgICAgICAgICAgICAgY29udGludWUKICAgICAgICAgICAgICAgIHdyaXRlX21hcC5zZXRkZWZhdWx0KGNvbCwge30pW3RpXSA9IHZhbAoKICAgICMgRXNjcmliaXIgY29sdW1uYSBhIGNvbHVtbmEgY29uIHVuIHNvbG8gcHV0X2NvbF9yYW5nZSBwb3IgY29sdW1uYQogICAgd3JpdHRlbiA9IDAKICAgIGZvciBjb2xfaWR4LCByb3dfdmFscyBpbiBzb3J0ZWQod3JpdGVfbWFwLml0ZW1zKCkpOgogICAgICAgIGlmIG5vdCByb3dfdmFsczoKICAgICAgICAgICAgY29udGludWUKICAgICAgICBtaW5fcm93ID0gbWluKHJvd192YWxzKQogICAgICAgIG1heF9yb3cgPSBtYXgocm93X3ZhbHMpCiAgICAgICAgdmFsdWVzICA9IFtyb3dfdmFscy5nZXQoaSkgZm9yIGkgaW4gcmFuZ2UobWluX3JvdywgbWF4X3JvdyArIDEpXQogICAgICAgIGlmIGFsbCh2IGlzIE5vbmUgZm9yIHYgaW4gdmFsdWVzKToKICAgICAgICAgICAgY29udGludWUKICAgICAgICBvayA9IHB1dF9jb2xfcmFuZ2UodGFyZ2V0X2lkLCBzaWRfdCwgY29sX2lkeCwgbWluX3JvdywgdmFsdWVzLCAidmVydGljYWwiKQogICAgICAgIGlmIG9rOgogICAgICAgICAgICB3cml0dGVuICs9IDEKICAgICAgICB0aW1lLnNsZWVwKDAuMikKICAgIHJldHVybiB3cml0dGVuCgojIOKUgOKUgOKUgCBQQVNPIDc6IE9mZnNldCB5IG1hcGVvIGRlIGZpbGFzIOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgApkZWYgZmluZF9vZmZzZXQodGd0X2NlbGxzLCBzcmNfY2VsbHMsIGRhdGVfa3cpOgogICAgdGd0X2NvbCA9IHNyY19jb2wgPSBOb25lCiAgICBrdyA9IHN0cihkYXRlX2t3KS5sb3dlcigpIGlmIGRhdGVfa3cgZWxzZSAiIgogICAgZm9yIHJvdyBpbiB0Z3RfY2VsbHNbOjhdOgogICAgICAgIGZvciBqLCBjIGluIGVudW1lcmF0ZShyb3cpOgogICAgICAgICAgICBpZiBpc2luc3RhbmNlKGMsZGljdCkgYW5kIGt3IGFuZCBrdyBpbiBzdHIoYy5nZXQoImNhbGN1bGF0ZWRWYWx1ZSIsIiIpKS5sb3dlcigpOgogICAgICAgICAgICAgICAgaWYgdGd0X2NvbCBpcyBOb25lOiB0Z3RfY29sID0gagogICAgZm9yIHJvdyBpbiBzcmNfY2VsbHNbOjhdOgogICAgICAgIGZvciBqLCBjIGluIGVudW1lcmF0ZShyb3cpOgogICAgICAgICAgICBpZiBpc2luc3RhbmNlKGMsZGljdCkgYW5kIGt3IGFuZCBrdyBpbiBzdHIoYy5nZXQoImNhbGN1bGF0ZWRWYWx1ZSIsIiIpKS5sb3dlcigpOgogICAgICAgICAgICAgICAgaWYgc3JjX2NvbCBpcyBOb25lOiBzcmNfY29sID0gagogICAgaWYgdGd0X2NvbCBpcyBub3QgTm9uZSBhbmQgc3JjX2NvbCBpcyBub3QgTm9uZTogcmV0dXJuIHRndF9jb2wgLSBzcmNfY29sCiAgICByZXR1cm4gMgoKZGVmIGZpbmRfYnBjX2NvbChzcmNfY2VsbHMsIHRndF9jZWxscyk6CiAgICAiIiIKICAgIERldGVjdGEgbGEgY29sdW1uYSBxdWUgY29udGllbmUgZWwgY8OzZGlnbyBCUEMgKCdBZ3J1cGFkb3IgQlBDJyAvICdBZ3J1cGFkb3InKS4KICAgIEJ1c2NhIGVuIGxhcyBwcmltZXJhcyA4IGZpbGFzIHVuIGhlYWRlciBxdWUgZGlnYSAnYWdydXBhZG9yJy4KICAgIFJldG9ybmEgZWwgw61uZGljZSBkZSBjb2x1bW5hLCBvIE5vbmUgc2kgbm8gZXhpc3RlLgogICAgIiIiCiAgICBmb3IgY2VsbHMgaW4gKHNyY19jZWxscywgdGd0X2NlbGxzKToKICAgICAgICBmb3Igcm93IGluIGNlbGxzWzo4XToKICAgICAgICAgICAgZm9yIGosIGMgaW4gZW51bWVyYXRlKHJvdyk6CiAgICAgICAgICAgICAgICBpZiBpc2luc3RhbmNlKGMsIGRpY3QpOgogICAgICAgICAgICAgICAgICAgIGN2ID0gc3RyKGMuZ2V0KCJjYWxjdWxhdGVkVmFsdWUiLCIiKSkubG93ZXIoKQogICAgICAgICAgICAgICAgICAgIGlmICJhZ3J1cGFkb3IiIGluIGN2OgogICAgICAgICAgICAgICAgICAgICAgICByZXR1cm4gagogICAgcmV0dXJuIE5vbmUKCmRlZiBidWlsZF9yb3dfbWFwcGluZyh0Z3RfY2VsbHMsIHNyY19jZWxscyk6CiAgICAiIiIKICAgIE1hcGVvIGRlIGZpbGFzIHRhcmdldCDihpIgc291cmNlIGJhc2FkbyBlbiBBTkNMQVMuCiAgICBGdW5jaW9uYSBjb24gZGlmZiBlbiBjdWFscXVpZXIgc2VudGlkbyAodGFyZ2V0IGNvbiBtw6FzIG8gbWVub3MgZmlsYXMpLgoKICAgIEVzdHJhdGVnaWE6CiAgICAgIDEuIFNpIGRpZmY9PTA6IG1hcGVvIGRpcmVjdG8gMToxIChjYXNvIG3DoXMgY29tw7puIHkgc2VndXJvKS4KICAgICAgMi4gU2kgZGlmZiE9MDoKICAgICAgICAgYS4gQW5jbGFzID0gZmlsYXMgY29uIEJQQyBjb2luY2lkZW50ZSBvIGV0aXF1ZXRhIChjb2wgQikgaWTDqW50aWNhLAogICAgICAgICAgICBjb24gw61uZGljZSBkZSBzb3VyY2UgZXN0cmljdGFtZW50ZSBjcmVjaWVudGUuCiAgICAgICAgIGIuIEZpbGFzIGFuY2xhZGFzIOKGkiBzdSBhbmNsYS4KICAgICAgICAgYy4gRmlsYXMgTk8gdmFjw61hcyBlbnRyZSBhbmNsYXMg4oaSIGludGVycG9sYWNpw7NuIHBvc2ljaW9uYWwuCiAgICAgICAgIGQuIEZpbGFzIFZBQ8ONQVMgKHNpbiBldGlxdWV0YSBuaSBCUEMpIOKGkiBOb25lIFNJRU1QUkUgKG5vIHJlY2liZW4gdmFsb3IpLgogICAgIiIiCiAgICBkaWZmID0gbGVuKHRndF9jZWxscykgLSBsZW4oc3JjX2NlbGxzKQogICAgaWYgZGlmZiA9PSAwOgogICAgICAgIHJldHVybiBsaXN0KHJhbmdlKGxlbih0Z3RfY2VsbHMpKSkKCiAgICBicGNfY29sID0gZmluZF9icGNfY29sKHNyY19jZWxscywgdGd0X2NlbGxzKQoKICAgIGRlZiBsYmwocm93KTogcmV0dXJuIHN0cihnZXRfY3Yocm93LCAxKSBvciAiIikuc3RyaXAoKQogICAgZGVmIGJwYyhyb3cpOgogICAgICAgIGlmIGJwY19jb2wgaXMgTm9uZTogcmV0dXJuIE5vbmUKICAgICAgICBiID0gZ2V0X2N2KHJvdywgYnBjX2NvbCkKICAgICAgICByZXR1cm4gc3RyKGIpIGlmIGIgaXMgbm90IE5vbmUgYW5kIHN0cihiKS5zdHJpcCgpIGVsc2UgTm9uZQoKICAgICMgTG9va3VwcyBkZWwgc291cmNlCiAgICBzcmNfYnBjID0ge30KICAgIGZvciBpLCByIGluIGVudW1lcmF0ZShzcmNfY2VsbHMpOgogICAgICAgIGIgPSBicGMocikKICAgICAgICBpZiBiOiBzcmNfYnBjLnNldGRlZmF1bHQoYiwgaSkKICAgIHNyY19sYmwgPSB7fQogICAgZm9yIGksIHIgaW4gZW51bWVyYXRlKHNyY19jZWxscyk6CiAgICAgICAgbCA9IGxibChyKQogICAgICAgIGlmIGw6IHNyY19sYmwuc2V0ZGVmYXVsdChsLCBbXSkuYXBwZW5kKGkpCgogICAgIyAxLiBEZXRlY3RhciBhbmNsYXMgKHNyY19pZHggZXN0cmljdGFtZW50ZSBjcmVjaWVudGUpCiAgICBhbmNob3JzID0gW10KICAgIHVzZWQgPSBzZXQoKQogICAgbGFzdF9zcmMgPSAtMQogICAgZm9yIHRpLCBydCBpbiBlbnVtZXJhdGUodGd0X2NlbGxzKToKICAgICAgICBzaSA9IE5vbmUKICAgICAgICBiID0gYnBjKHJ0KQogICAgICAgIGlmIGIgYW5kIGIgaW4gc3JjX2JwYyBhbmQgc3JjX2JwY1tiXSA+IGxhc3Rfc3JjIGFuZCBzcmNfYnBjW2JdIG5vdCBpbiB1c2VkOgogICAgICAgICAgICBzaSA9IHNyY19icGNbYl0KICAgICAgICBlbHNlOgogICAgICAgICAgICBsID0gbGJsKHJ0KQogICAgICAgICAgICBpZiBsIGFuZCBsIGluIHNyY19sYmw6CiAgICAgICAgICAgICAgICBmb3IgY2FuZCBpbiBzcmNfbGJsW2xdOgogICAgICAgICAgICAgICAgICAgIGlmIGNhbmQgPiBsYXN0X3NyYyBhbmQgY2FuZCBub3QgaW4gdXNlZDoKICAgICAgICAgICAgICAgICAgICAgICAgc2kgPSBjYW5kOyBicmVhawogICAgICAgIGlmIHNpIGlzIG5vdCBOb25lOgogICAgICAgICAgICBhbmNob3JzLmFwcGVuZCgodGksIHNpKSkKICAgICAgICAgICAgdXNlZC5hZGQoc2kpOyBsYXN0X3NyYyA9IHNpCgogICAgbWFwcGluZyA9IFtOb25lXSAqIGxlbih0Z3RfY2VsbHMpCiAgICBmb3IgdGksIHNpIGluIGFuY2hvcnM6CiAgICAgICAgbWFwcGluZ1t0aV0gPSBzaQoKICAgICMgMi4gSW50ZXJwb2xhY2nDs24gcG9zaWNpb25hbCBlbnRyZSBhbmNsYXMg4oCUIHNvbG8gZmlsYXMgTk8gdmFjw61hcwogICAgZm9yIGsgaW4gcmFuZ2UobGVuKGFuY2hvcnMpIC0gMSk6CiAgICAgICAgdDAsIHMwID0gYW5jaG9yc1trXQogICAgICAgIHQxLCBzMSA9IGFuY2hvcnNbayArIDFdCiAgICAgICAgZm9yIHRpIGluIHJhbmdlKHQwICsgMSwgdDEpOgogICAgICAgICAgICBpZiBub3QgbGJsKHRndF9jZWxsc1t0aV0pOgogICAgICAgICAgICAgICAgY29udGludWUgICMgZmlsYSB2YWPDrWEg4oaSIE5vbmUKICAgICAgICAgICAgc2kgPSBzMCArICh0aSAtIHQwKQogICAgICAgICAgICBpZiBzMCA8IHNpIDwgczE6CiAgICAgICAgICAgICAgICBtYXBwaW5nW3RpXSA9IHNpCgogICAgcmV0dXJuIG1hcHBpbmcKCmRlZiBidWlsZF93cml0ZV92YWx1ZXModGd0X2NlbGxzLCBzcmNfY2VsbHMsIGRlc3RfY29sLCBzcmNfY29sKToKICAgIHJvd19tYXAgPSBidWlsZF9yb3dfbWFwcGluZyh0Z3RfY2VsbHMsIHNyY19jZWxscykKICAgIGJwY19jb2wgPSBmaW5kX2JwY19jb2woc3JjX2NlbGxzLCB0Z3RfY2VsbHMpCgogICAgZGVmIGlzX2RhdGFfcm93KHJvdyk6CiAgICAgICAgIiIiVW5hIGZpbGEgcmVjaWJlIHZhbG9yIHNvbG8gc2kgdGllbmUgZXRpcXVldGEgKGNvbCBCKSBvIGPDs2RpZ28gQlBDLgogICAgICAgIExhcyBmaWxhcyBlc3RydWN0dXJhbG1lbnRlIHZhY8OtYXMgKGhlbHBlcnMvY3VhZHJhamVzIHNpbiBsYWJlbCkgc2Ugc2FsdGFuLiIiIgogICAgICAgIGlmIHN0cihnZXRfY3Yocm93LCAxKSBvciAiIikuc3RyaXAoKToKICAgICAgICAgICAgcmV0dXJuIFRydWUKICAgICAgICBpZiBicGNfY29sIGlzIG5vdCBOb25lIGFuZCBnZXRfY3Yocm93LCBicGNfY29sKSBub3QgaW4gKE5vbmUsICIiKToKICAgICAgICAgICAgcmV0dXJuIFRydWUKICAgICAgICByZXR1cm4gRmFsc2UKCiAgICB2YWxzID0gW10KICAgIHVubWFwcGVkID0gW10KICAgIGZvciBpIGluIHJhbmdlKGxlbih0Z3RfY2VsbHMpKToKICAgICAgICByb3dfdCA9IHRndF9jZWxsc1tpXSBpZiBpIDwgbGVuKHRndF9jZWxscykgZWxzZSBbXQogICAgICAgIGlmIGlzX2Zvcm11bGEocm93X3QsIGRlc3RfY29sKToKICAgICAgICAgICAgdmFscy5hcHBlbmQoTm9uZSk7IGNvbnRpbnVlCiAgICAgICAgIyBTaSBsYSBjZWxkYSBkZXN0aW5vIHlhIGNvbnRpZW5lIHRleHRvIChlbmNhYmV6YWRvLCB1bmlkYWQsIGV0Yy4pIG5vIHRvY2FyCiAgICAgICAgZXhpc3RpbmcgPSBnZXRfY3Yocm93X3QsIGRlc3RfY29sKQogICAgICAgIGlmIGlzaW5zdGFuY2UoZXhpc3RpbmcsIHN0cikgYW5kIGV4aXN0aW5nLnN0cmlwKCk6CiAgICAgICAgICAgIHZhbHMuYXBwZW5kKE5vbmUpOyBjb250aW51ZQogICAgICAgIGlmIG5vdCBpc19kYXRhX3Jvdyhyb3dfdCk6CiAgICAgICAgICAgIHZhbHMuYXBwZW5kKE5vbmUpOyBjb250aW51ZQogICAgICAgIHNyY19yb3cgPSByb3dfbWFwW2ldCiAgICAgICAgaWYgc3JjX3JvdyBpcyBOb25lOgogICAgICAgICAgICAjIExvZ2dlYXIgYWdydXBhZG9yZXMvZXRpcXVldGFzIHF1ZSBubyBtYXBlYXJvbgogICAgICAgICAgICBiID0gZ2V0X2N2KHJvd190LCBicGNfY29sKSBpZiBicGNfY29sIGlzIG5vdCBOb25lIGVsc2UgTm9uZQogICAgICAgICAgICBsYiA9IHN0cihnZXRfY3Yocm93X3QsIDEpIG9yICIiKS5zdHJpcCgpCiAgICAgICAgICAgIHRhZyA9IHN0cihiKSBpZiBiIGlzIG5vdCBOb25lIGVsc2UgbGJbOjMwXQogICAgICAgICAgICBpZiB0YWc6CiAgICAgICAgICAgICAgICB1bm1hcHBlZC5hcHBlbmQoZiJmaWxhIHtpKzF9Ont0YWd9IikKICAgICAgICAgICAgdmFscy5hcHBlbmQoTm9uZSk7IGNvbnRpbnVlCiAgICAgICAgc3YgPSBnZXRfY3Yoc3JjX2NlbGxzW3NyY19yb3ddLCBzcmNfY29sKQogICAgICAgIHZhbHMuYXBwZW5kKHN2IGlmIGlzaW5zdGFuY2Uoc3YsIChpbnQsIGZsb2F0KSkgZWxzZSBOb25lKQogICAgaWYgdW5tYXBwZWQ6CiAgICAgICAgcHJpbnQoZiIgICAgICBbc2luIG1hcGVvXSB7JywgJy5qb2luKHVubWFwcGVkWzo4XSl9IgogICAgICAgICAgICAgICsgKCIgLi4uIiBpZiBsZW4odW5tYXBwZWQpID4gOCBlbHNlICIiKSkKICAgIHJldHVybiB2YWxzCgojIOKUgOKUgOKUgCBQQVNPIDg6IENvcGlhIGRlIGhvamEgdGlwbyA3OSDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIAKZGVmIGNvcHlfZGV0YWlsX3NoZWV0KHRhcmdldF9pZCwgdGd0X3NpZCwgc3JjX2NlbGxzLCB0Z3RfY2VsbHMpOgogICAgY29scyA9IHtqIGZvciByb3cgaW4gc3JjX2NlbGxzIGZvciBqLGMgaW4gZW51bWVyYXRlKHJvdykKICAgICAgICAgICAgaWYgaXNpbnN0YW5jZShjLGRpY3QpIGFuZCBub3QgaXNfZm9ybXVsYShyb3csaikKICAgICAgICAgICAgYW5kIGMuZ2V0KCJjYWxjdWxhdGVkVmFsdWUiKSBub3QgaW4gKE5vbmUsIiIsMCl9CiAgICBvayA9IDAKICAgIGZvciBjb2xfaWR4IGluIHNvcnRlZChjb2xzKToKICAgICAgICB3ICAgPSBbXQogICAgICAgIGhhcyA9IEZhbHNlCiAgICAgICAgZm9yIGkgaW4gcmFuZ2UobGVuKHRndF9jZWxscykpOgogICAgICAgICAgICBycyA9IHNyY19jZWxsc1tpXSBpZiBpIDwgbGVuKHNyY19jZWxscykgZWxzZSBbXQogICAgICAgICAgICBydCA9IHRndF9jZWxsc1tpXSBpZiBpIDwgbGVuKHRndF9jZWxscykgZWxzZSBbXQogICAgICAgICAgICBpZiBpc19mb3JtdWxhKHJ0LCBjb2xfaWR4KSBvciBpc19mb3JtdWxhKHJzLCBjb2xfaWR4KToKICAgICAgICAgICAgICAgIHcuYXBwZW5kKE5vbmUpOyBjb250aW51ZQogICAgICAgICAgICBjdiA9IChyc1tjb2xfaWR4XSBpZiBjb2xfaWR4IDwgbGVuKHJzKSBlbHNlIHt9KQogICAgICAgICAgICBjdiA9IGN2LmdldCgiY2FsY3VsYXRlZFZhbHVlIikgaWYgaXNpbnN0YW5jZShjdixkaWN0KSBlbHNlIE5vbmUKICAgICAgICAgICAgdy5hcHBlbmQoY3YgaWYgY3Ygbm90IGluIChOb25lLCIiKSBlbHNlIE5vbmUpCiAgICAgICAgICAgIGlmIGN2IG5vdCBpbiAoTm9uZSwiIiwwKTogaGFzID0gVHJ1ZQogICAgICAgIGlmIG5vdCBoYXM6IGNvbnRpbnVlCiAgICAgICAgd2hpbGUgbGVuKHcpIDwgbGVuKHRndF9jZWxscyk6IHcuYXBwZW5kKE5vbmUpCiAgICAgICAgY2wgPSBjb2xfbGV0dGVyKGNvbF9pZHgpCiAgICAgICAgcnAgPSBzZXNzaW9uLnB1dChXREVTS19CQVNFKyIvcGxhdGZvcm0vdjEvc3ByZWFkc2hlZXRzLyIrdGFyZ2V0X2lkKyIvc2hlZXRzLyIrdGd0X3NpZAogICAgICAgICAgICAgICAgICAgICAgICAgKyIvdmFsdWVzLyIrZiJ7Y2x9MTp7Y2x9e2xlbih3KX0iLAogICAgICAgICAgICAgICAgICAgICAgICAganNvbj17InZhbHVlcyI6W1t2XSBmb3IgdiBpbiB3XX0sIHRpbWVvdXQ9MTIwKQogICAgICAgIGlmIHJwLnN0YXR1c19jb2RlID09IDIwMiBhbmQgcG9sbChycC5oZWFkZXJzLmdldCgiTG9jYXRpb24iLCIiKSk6IG9rICs9IDEKICAgICAgICB0aW1lLnNsZWVwKDAuMikKICAgIHByaW50KGYiICAgIHtva30gY29sdW1uYXMgY29waWFkYXMiKQoKZGVmIGNvcHlfYmxvY2tfc2hlZXQodGFyZ2V0X2lkLCB0Z3Rfc2lkLCBzcmNfY2VsbHMsIHRndF9jZWxscywgc3JjX3N0YXJ0LCBzcmNfZW5kLCB0Z3Rfc3RhcnQsIHRndF9lbmQpOgogICAgIiIiCiAgICBDb3BpYSB1biByYW5nbyBkZSBmaWxhcyBkZWwgZnVlbnRlIGFsIHRhcmdldCAoYmxvcXVlIGEgYmxvcXVlLCDDrW5kaWNlcyBiYXNlLTApLgogICAgU29sbyBlc2NyaWJlIGNlbGRhcyBudW3DqXJpY2FzIG5vLWbDs3JtdWxhIGVuIGVsIHRhcmdldC4KICAgIEFncnVwYSBwb3IgY29sdW1uYSB5IHVzYSBwdXRfY29sX3JhbmdlIHBhcmEgbWluaW1pemFyIGxsYW1hZGFzIGEgbGEgQVBJLgogICAgIiIiCiAgICBibG9ja19oID0gbWluKHNyY19lbmQgLSBzcmNfc3RhcnQsIHRndF9lbmQgLSB0Z3Rfc3RhcnQpCiAgICB3cml0ZV9tYXAgPSB7fSAgICMgY29sX2lkeCDihpIge3RndF9yb3dfaWR4OiB2YWx1ZX0KCiAgICBmb3Igb2Zmc2V0IGluIHJhbmdlKGJsb2NrX2gpOgogICAgICAgIHNpID0gc3JjX3N0YXJ0ICsgb2Zmc2V0CiAgICAgICAgdGkgPSB0Z3Rfc3RhcnQgKyBvZmZzZXQKICAgICAgICBpZiBzaSA+PSBsZW4oc3JjX2NlbGxzKSBvciB0aSA+PSBsZW4odGd0X2NlbGxzKToKICAgICAgICAgICAgYnJlYWsKICAgICAgICByb3dfc3JjID0gc3JjX2NlbGxzW3NpXQogICAgICAgIHJvd190Z3QgPSB0Z3RfY2VsbHNbdGldCiAgICAgICAgZm9yIGNvbCBpbiByYW5nZShtYXgobGVuKHJvd19zcmMpLCBsZW4ocm93X3RndCkpKToKICAgICAgICAgICAgaWYgaXNfZm9ybXVsYShyb3dfdGd0LCBjb2wpOgogICAgICAgICAgICAgICAgY29udGludWUKICAgICAgICAgICAgdmFsID0gZ2V0X2N2KHJvd19zcmMsIGNvbCkKICAgICAgICAgICAgaWYgbm90IGlzaW5zdGFuY2UodmFsLCAoaW50LCBmbG9hdCkpOgogICAgICAgICAgICAgICAgY29udGludWUKICAgICAgICAgICAgd3JpdGVfbWFwLnNldGRlZmF1bHQoY29sLCB7fSlbdGldID0gdmFsCgogICAgd3JpdHRlbiA9IDAKICAgIGZvciBjb2xfaWR4LCByb3dfdmFscyBpbiBzb3J0ZWQod3JpdGVfbWFwLml0ZW1zKCkpOgogICAgICAgIGlmIG5vdCByb3dfdmFsczoKICAgICAgICAgICAgY29udGludWUKICAgICAgICBtaW5fcm93ID0gbWluKHJvd192YWxzKQogICAgICAgIG1heF9yb3cgPSBtYXgocm93X3ZhbHMpCiAgICAgICAgdmFsdWVzICA9IFtyb3dfdmFscy5nZXQoaSkgZm9yIGkgaW4gcmFuZ2UobWluX3JvdywgbWF4X3JvdyArIDEpXQogICAgICAgIGlmIGFsbCh2IGlzIE5vbmUgZm9yIHYgaW4gdmFsdWVzKToKICAgICAgICAgICAgY29udGludWUKICAgICAgICBvayA9IHB1dF9jb2xfcmFuZ2UodGFyZ2V0X2lkLCB0Z3Rfc2lkLCBjb2xfaWR4LCBtaW5fcm93LCB2YWx1ZXMsICJibG9jayIpCiAgICAgICAgaWYgb2s6CiAgICAgICAgICAgIHdyaXR0ZW4gKz0gMQogICAgICAgIHRpbWUuc2xlZXAoMC4yKQogICAgcHJpbnQoZiIgICAge3dyaXR0ZW59IGNvbHVtbmFzIGVzY3JpdGFzIikKCiMg4pSA4pSA4pSAIFBST0NFU0FSIFVOIEFSQ0hJVk8g4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSACmRlZiBwcm9jZXNzX2ZpbGUodGFyZ2V0X2luZm8sIGFsbF9maWxlcyk6CiAgICBmaWQgICAgPSB0YXJnZXRfaW5mb1siaWQiXQogICAgbmFtZSAgID0gdGFyZ2V0X2luZm9bIm5hbWUiXQogICAgcGFyc2VkID0gdGFyZ2V0X2luZm8KCiAgICBwcmludChmIlxueyfilIAnKjYwfSIpCiAgICBwcmludChmIlByb2Nlc2FuZG86IHtuYW1lfSIpCiAgICBwcmludChmInsn4pSAJyo2MH0iKQoKICAgICMgSG9qYXMgZGVsIHRhcmdldAogICAgdGd0X3NoZWV0cyA9IGdldF9zaGVldHMoZmlkKQogICAgaWYgIkJhc2VzIiBub3QgaW4gdGd0X3NoZWV0czoKICAgICAgICBwcmludCgiICDinJcgU2luIGhvamEgQmFzZXMg4oCUIHNhbHRhbmRvIikKICAgICAgICByZXR1cm4gMCwgMAoKICAgICMgQmFzZXMKICAgIGJhc2VzID0gcmVhZF9iYXNlcyhmaWQsIHRndF9zaGVldHMpCiAgICBwcmludChmIiAgUGVyw61vZG86IHtiYXNlcy5nZXQoJ2N1cnJlbnRfZW5kJywnPycpfSB8IENvbXBhcjoge2Jhc2VzLmdldCgncHJpb3JfZW5kJywnPycpfSIpCgogICAgIyBGdWVudGVzCiAgICBzb3VyY2VzID0gZmluZF9zb3VyY2VfZmlsZXMocGFyc2VkLCBiYXNlcywgYWxsX2ZpbGVzKQoKICAgICMgQ2FyZ2FyIGZ1ZW50ZXMKICAgIHByaW50KCIgIENhcmdhbmRvIGZ1ZW50ZXMuLi4iKQogICAgbG9hZGVkID0gbG9hZF9zb3VyY2VzKHNvdXJjZXMpCgogICAgcGVyaW9kX3JlZiA9IHsKICAgICAgICAiYmFsYW5jZSI6ICAgICAgICBiYXNlcy5nZXQoInByaW9yX2VuZCIsIiIpLAogICAgICAgICJlZXJyIjogICAgICAgICAgIGJhc2VzLmdldCgicHJpb3JfZWVycl9lbmQiLCIiKSwKICAgICAgICAicXVhcnRlcl9wcmV2IjogICBiYXNlcy5nZXQoInByaW9yX3ByZXZfcGVyaW9kX2VuZCIsIiIpLAogICAgICAgICJjdXJyX3N1YnBlcmlvZCI6IGJhc2VzLmdldCgicHJldl9wZXJpb2RfZW5kIiwiIiksCiAgICB9CgogICAgZGVmIGdldF9zcmMoa2V5KToKICAgICAgICBmaWQyID0gc291cmNlcy5nZXQoa2V5KQogICAgICAgIGlmIG5vdCBmaWQyIG9yIGZpZDIgbm90IGluIGxvYWRlZDogcmV0dXJuIE5vbmUsIHt9CiAgICAgICAgcmV0dXJuIGZpZDIsIGxvYWRlZFtmaWQyXVsiY2VsbHMiXQoKICAgIHRvX3Byb2Nlc3MgPSB7bjpzaWQgZm9yIG4sc2lkIGluIHRndF9zaGVldHMuaXRlbXMoKSBpZiBuIG5vdCBpbiBTS0lQX1NIRUVUU30KICAgIG9rX3RvdGFsID0gZXJyX3RvdGFsID0gMAoKICAgIGZvciBzbmFtZSwgc2lkX3QgaW4gdG9fcHJvY2Vzcy5pdGVtcygpOgogICAgICAgIHJlZnJlc2hfdG9rZW4oKQoKICAgICAgICAjIENvcGlhIGRlIGhvamEgdGlwbyA3OQogICAgICAgIGlmIHNuYW1lIGluIEZVTExfQ09QWV9QQUlSUzoKICAgICAgICAgICAgc3JjX25hbWUgPSBGVUxMX0NPUFlfUEFJUlNbc25hbWVdCiAgICAgICAgICAgIF8sIGNtYXAgID0gZ2V0X3NyYygiYmFsYW5jZSIpCiAgICAgICAgICAgIHNyY19jICAgID0gY21hcC5nZXQoc3JjX25hbWUsIFtdKQogICAgICAgICAgICB0Z3RfYyAgICA9IHJlYWRfc2hlZXQoZmlkLCBzaWRfdCkKICAgICAgICAgICAgcHJpbnQoZiIgIFtDT1BJQV0ge3NuYW1lfSIpCiAgICAgICAgICAgIGlmIHNyY19jOiBjb3B5X2RldGFpbF9zaGVldChmaWQsIHNpZF90LCBzcmNfYywgdGd0X2MpCiAgICAgICAgICAgIGVsc2U6ICAgICBwcmludCgiICAgIOKGkiBGdWVudGUgbm8gZW5jb250cmFkYSIpCiAgICAgICAgICAgIGNvbnRpbnVlCgogICAgICAgICMgQ29waWEgZGUgYmxvcXVlIGZpam8gKGVqLiBob2phIDYwKQogICAgICAgIGlmIHNuYW1lIGluIEJMT0NLX0NPUFlfU0hFRVRTOgogICAgICAgICAgICBzcywgc2UsIHRzLCB0ZSA9IEJMT0NLX0NPUFlfU0hFRVRTW3NuYW1lXQogICAgICAgICAgICBfLCBjbWFwID0gZ2V0X3NyYygiYmFsYW5jZSIpCiAgICAgICAgICAgIHNyY19jICAgPSBjbWFwLmdldChzbmFtZSwgW10pCiAgICAgICAgICAgIHRndF9jICAgPSByZWFkX3NoZWV0KGZpZCwgc2lkX3QpCiAgICAgICAgICAgIHByaW50KGYiICBbQkxPUVVFXSB7c25hbWV9IChzcmMge3NzKzF9OntzZX0g4oaSIHRndCB7dHMrMX06e3RlfSkiKQogICAgICAgICAgICBpZiBzcmNfYzogY29weV9ibG9ja19zaGVldChmaWQsIHNpZF90LCBzcmNfYywgdGd0X2MsIHNzLCBzZSwgdHMsIHRlKQogICAgICAgICAgICBlbHNlOiAgICAgcHJpbnQoIiAgICDihpIgRnVlbnRlIG5vIGVuY29udHJhZGEiKQogICAgICAgICAgICBjb250aW51ZQoKICAgICAgICB0Z3RfY2VsbHMgPSByZWFkX3NoZWV0KGZpZCwgc2lkX3QpCiAgICAgICAgaWYgbm90IHRndF9jZWxsczogY29udGludWUKCiAgICAgICAgY29tcF9jb2xzID0gZGV0ZWN0X2NvbXBfY29scyh0Z3RfY2VsbHMsIGJhc2VzKQoKICAgICAgICBpZiBub3QgY29tcF9jb2xzOgogICAgICAgICAgICAjIEludGVudGFyIHBhdHLDs24gZGUgYmxvcXVlcyB2ZXJ0aWNhbGVzIChlai4gaG9qYSAxOSkKICAgICAgICAgICAgYmxvY2tzID0gZGV0ZWN0X3ZlcnRpY2FsX2Jsb2Nrcyh0Z3RfY2VsbHMsIGJhc2VzKQogICAgICAgICAgICBpZiBibG9ja3M6CiAgICAgICAgICAgICAgICBfLCBjbWFwICAgPSBnZXRfc3JjKCJiYWxhbmNlIikKICAgICAgICAgICAgICAgIHNyY19jZWxscyA9IGNtYXAuZ2V0KHNuYW1lKSBvciBjbWFwLmdldChTSEVFVF9BTElBU0VTLmdldChzbmFtZSwgIiIpLCBbXSkKICAgICAgICAgICAgICAgIGlmIHNyY19jZWxsczoKICAgICAgICAgICAgICAgICAgICBwcmludChmIiAgW1ZFUlRJQ0FMXSB7c25hbWV9IikKICAgICAgICAgICAgICAgICAgICBuID0gZmlsbF92ZXJ0aWNhbF9zaGVldChmaWQsIHNpZF90LCB0Z3RfY2VsbHMsIHNyY19jZWxscywgYmxvY2tzLCBiYXNlcykKICAgICAgICAgICAgICAgICAgICBpZiBuOiBva190b3RhbCArPSBuCiAgICAgICAgICAgICAgICAgICAgZWxzZTogcHJpbnQoIiAgICDihpIgU2luIHZhbG9yZXMgZXNjcml0b3MiKQogICAgICAgICAgICBjb250aW51ZQoKICAgICAgICBwcmludChmIiAgW3tzbmFtZX1dIOKAlCB7bGVuKGNvbXBfY29scyl9IGNvbChzKSIpCgogICAgICAgIGZvciBkZXN0X2NvbCwgcGVyaW9kX2tleSBpbiBjb21wX2NvbHMuaXRlbXMoKToKICAgICAgICAgICAgIyBSZWdsYSAxMTogZWwgY29tcGFyYXRpdm8gYmFsYW5jZSAoMzEtMTIpIHNvbG8gc2UgbGxlbmEgY3VhbmRvIGVsCiAgICAgICAgICAgICMgcGVyw61vZG8gYWN0dWFsIGVzIG1hcnpvICgwMykuIEVuIDA2LzA5LzEyIGVzYSBjb2x1bW5hIHlhIHF1ZWTDswogICAgICAgICAgICAjIHBvYmxhZGEgZW4gZWwgY2llcnJlIGRlIG1hcnpvIHkgbm8gc2UgdnVlbHZlIGEgdG9jYXIuCiAgICAgICAgICAgIGlmIHBlcmlvZF9rZXkgPT0gImJhbGFuY2UiIGFuZCBwYXJzZWRbIm1tIl0gIT0gIjAzIjoKICAgICAgICAgICAgICAgIGNvbnRpbnVlCgogICAgICAgICAgICBfLCBjbWFwICAgPSBnZXRfc3JjKHBlcmlvZF9rZXkpCiAgICAgICAgICAgIHNyY19jZWxscyA9IGNtYXAuZ2V0KHNuYW1lLCBbXSkKICAgICAgICAgICAgaWYgbm90IHNyY19jZWxsczogY29udGludWUKCiAgICAgICAgICAgIG9mZnNldCAgPSBmaW5kX29mZnNldCh0Z3RfY2VsbHMsIHNyY19jZWxscywgcGVyaW9kX3JlZi5nZXQocGVyaW9kX2tleSwiIikpCiAgICAgICAgICAgIHNyY19jb2wgPSBkZXN0X2NvbCAtIG9mZnNldAogICAgICAgICAgICBpZiBzcmNfY29sIDwgMDogY29udGludWUKCiAgICAgICAgICAgIHdyaXRlX3ZhbHMgPSBidWlsZF93cml0ZV92YWx1ZXModGd0X2NlbGxzLCBzcmNfY2VsbHMsIGRlc3RfY29sLCBzcmNfY29sKQogICAgICAgICAgICBuID0gc3VtKDEgZm9yIHYgaW4gd3JpdGVfdmFscyBpZiB2IGlzIG5vdCBOb25lKQogICAgICAgICAgICBpZiBuID09IDA6IGNvbnRpbnVlCgogICAgICAgICAgICBvayA9IHB1dF9jb2woZmlkLCBzaWRfdCwgZGVzdF9jb2wsIHdyaXRlX3ZhbHMsIHBlcmlvZF9rZXkpCiAgICAgICAgICAgIGlmIG9rOiBva190b3RhbCArPSAxCiAgICAgICAgICAgIGVsc2U6ICBlcnJfdG90YWwgKz0gMQogICAgICAgICAgICB0aW1lLnNsZWVwKDAuMykKCiAgICBwcmludChmIiAgUmVzdWx0YWRvOiBPSz17b2tfdG90YWx9ICBFUlI9e2Vycl90b3RhbH0iKQogICAgcmV0dXJuIG9rX3RvdGFsLCBlcnJfdG90YWwKCiMg4pSA4pSA4pSAIE1BSU4g4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSACmRlZiBtYWluKCk6CiAgICBfdDAgPSB0aW1lLnRpbWUoKQogICAgcHJpbnQoIj0iKjYwKQogICAgcHJpbnQoIkxMRU5BRE8gREUgQ09NUEFSQVRJVk9TIHYyIikKICAgIHByaW50KCI9Iio2MCkKCiAgICAjIE1vZG8gcHJ1ZWJhOiB1c2FyIGFyY2hpdm8gZGUgcHJ1ZWJhIGRpcmVjdGFtZW50ZQogICAgaWYgVEVTVF9NT0RFOgogICAgICAgIHByaW50KGYiXG5bTU9ETyBQUlVFQkFdIEFyY2hpdm86IHtURVNUX0ZJTEVfSUR9IikKICAgICAgICBwcmludChmIiAgRW1wcmVzYToge1RFU1RfQ09ERX0gfCBQZXLDrW9kbzoge1RFU1RfTU19LXtURVNUX1lZWVl9IikKICAgICAgICByZWZyZXNoX3Rva2VuKCkKICAgICAgICBhbGxfZmlsZXMgICAgPSBsb2FkX2FsbF9maWxlcygpCiAgICAgICAgdGFyZ2V0X2ZpbGVzID0gW3sKICAgICAgICAgICAgImlkIjogVEVTVF9GSUxFX0lELCAibmFtZSI6IGYiKHBydWViYSkge1RFU1RfQ09ERX1fe1RFU1RfTU19LXtURVNUX1lZWVl9IiwKICAgICAgICAgICAgImNvZGUiOiBURVNUX0NPREUsICJ0aXBvIjogIklORCIsICJtbSI6IFRFU1RfTU0sICJ5eXl5IjogVEVTVF9ZWVlZLCAic3VmZml4IjogVEVTVF9TVUZGSVgsCiAgICAgICAgfV0KICAgIGVsc2U6CiAgICAgICAgIyBTb2xvIElORCDigJQgQ09OU08gZXhjbHVpZG8KICAgICAgICBwcmludCgpCiAgICAgICAgeXl5eSA9IGlucHV0KCJBw7FvIGRlbCBwZXLDrW9kbyAoZWo6IDIwMjYpOiAiKS5zdHJpcCgpCiAgICAgICAgbW0gICA9IGlucHV0KCJNZXMgZGVsIHBlcsOtb2RvIChlajogMDYpOiAiKS5zdHJpcCgpLnpmaWxsKDIpCiAgICAgICAgdGlwbyA9ICJJTkQiCgogICAgICAgIGlmIG5vdCB5eXl5LmlzZGlnaXQoKSBvciBub3QgbW0uaXNkaWdpdCgpIG9yIG5vdCAoMSA8PSBpbnQobW0pIDw9IDEyKToKICAgICAgICAgICAgcHJpbnQoIkHDsW8gbyBtZXMgaW52w6FsaWRvLiIpCiAgICAgICAgICAgIHJldHVybgoKICAgICAgICBwcmludChmIlxuQnVzY2FuZG8gYXJjaGl2b3MgSU5EIHBhcmEge21tfS17eXl5eX0uLi4iKQogICAgICAgIHJlZnJlc2hfdG9rZW4oKQoKICAgICAgICBhbGxfZmlsZXMgICAgPSBsb2FkX2FsbF9maWxlcygpCiAgICAgICAgdGFyZ2V0X2ZpbGVzID0gZmluZF90YXJnZXRfZmlsZXMobW0sIHl5eXksIHRpcG8sIGFsbF9maWxlcykKCiAgICBpZiBub3QgdGFyZ2V0X2ZpbGVzOgogICAgICAgIHByaW50KGYiTm8gc2UgZW5jb250cmFyb24gYXJjaGl2b3MgRXt7Y29kZX19X0lORF97bW19LXt5eXl5fV9CYXNlIE5vdGFzIHt7c3VmZml4fX0iKQogICAgICAgIHJldHVybgoKICAgIHByaW50KGYiXG5BcmNoaXZvcyBlbmNvbnRyYWRvcyAoe2xlbih0YXJnZXRfZmlsZXMpfSk6IikKICAgIGZvciBpLCB0IGluIGVudW1lcmF0ZSh0YXJnZXRfZmlsZXMsIDEpOgogICAgICAgIHByaW50KGYiICB7aX0uIHt0WyduYW1lJ119IikKCiAgICBpZiBub3QgVEVTVF9NT0RFOgogICAgICAgIGNvbmZpcm0gPSBpbnB1dChmIlxuwr9Qcm9jZXNhciB0b2RvcyAocyksIGVsZWdpciB1bm8gcG9yIHVubyAoZSksIG8gY2FuY2VsYXIgKG4pPyAiKS5zdHJpcCgpLmxvd2VyKCkKICAgICAgICBpZiBjb25maXJtID09ICJuIjoKICAgICAgICAgICAgcHJpbnQoIkNhbmNlbGFkby4iKQogICAgICAgICAgICByZXR1cm4KICAgICAgICBlbGlmIGNvbmZpcm0gPT0gImUiOgogICAgICAgICAgICBzZWxlY2Npb25hZG9zID0gW10KICAgICAgICAgICAgZm9yIHQgaW4gdGFyZ2V0X2ZpbGVzOgogICAgICAgICAgICAgICAgcmVzcCA9IGlucHV0KGYiICDCv1Byb2Nlc2FyIHt0WyduYW1lJ119PyAocy9uKTogIikuc3RyaXAoKS5sb3dlcigpCiAgICAgICAgICAgICAgICBpZiByZXNwID09ICJzIjoKICAgICAgICAgICAgICAgICAgICBzZWxlY2Npb25hZG9zLmFwcGVuZCh0KQogICAgICAgICAgICBpZiBub3Qgc2VsZWNjaW9uYWRvczoKICAgICAgICAgICAgICAgIHByaW50KCJObyBzZSBzZWxlY2Npb27DsyBuaW5nw7puIGFyY2hpdm8uIENhbmNlbGFkby4iKQogICAgICAgICAgICAgICAgcmV0dXJuCiAgICAgICAgICAgIHRhcmdldF9maWxlcyA9IHNlbGVjY2lvbmFkb3MKICAgICAgICAgICAgcHJpbnQoZiJcblByb2Nlc2FuZG8ge2xlbih0YXJnZXRfZmlsZXMpfSBhcmNoaXZvKHMpIHNlbGVjY2lvbmFkbyhzKS4iKQoKICAgICMgUHJvY2VzYXIgY2FkYSBhcmNoaXZvOiBsaW1waWFyIHByaW1lcm8sIGx1ZWdvIGxsZW5hcgogICAgdG90YWxfb2sgPSB0b3RhbF9lcnIgPSAwCiAgICBmb3IgdCBpbiB0YXJnZXRfZmlsZXM6CiAgICAgICAgcHJpbnQoZiJcbiAg4oaSIExpbXBpYW5kbyBjb21wYXJhdGl2b3M6IHt0WyduYW1lJ119IikKICAgICAgICBjbGVhbl9maWxlKHRbImlkIl0sIHRbIm5hbWUiXSkKICAgICAgICBvaywgZXJyID0gcHJvY2Vzc19maWxlKHQsIGFsbF9maWxlcykKICAgICAgICB0b3RhbF9vayAgKz0gb2sKICAgICAgICB0b3RhbF9lcnIgKz0gZXJyCgogICAgZWxhcHNlZCA9IHRpbWUudGltZSgpIC0gX3QwCiAgICBtaW5zLCBzZWNzID0gZGl2bW9kKGludChlbGFwc2VkKSwgNjApCiAgICBwcmludChmIlxueyc9Jyo2MH0iKQogICAgcHJpbnQoZiJSRVNVTUVOIEZJTkFMOiB7bGVuKHRhcmdldF9maWxlcyl9IGFyY2hpdm9zIHByb2Nlc2Fkb3MiKQogICAgcHJpbnQoZiIgIE9wZXJhY2lvbmVzIE9LOiAge3RvdGFsX29rfSIpCiAgICBwcmludChmIiAgRXJyb3JlczogICAgICAgICB7dG90YWxfZXJyfSIpCiAgICBwcmludChmIiAgVGllbXBvIHRvdGFsOiAgICB7bWluc31tIHtzZWNzfXMiKQogICAgcHJpbnQoIj0iKjYwKQoKaWYgX19uYW1lX18gPT0gIl9fbWFpbl9fIjoKICAgIG1haW4oKQo="
).decode("utf-8")

_FLUJO_SRC = base64.b64decode(
    b"IyAtKi0gY29kaW5nOiB1dGYtOCAtKi0KIiIiCkdlbmVyYSBGbHVqb19FZmVjdGl2b188TU0tQUFBQT4ueGxzeCBkZXNkZSBsYSBiYXNlIFNRTCBTZXJ2ZXIgZGUgZUZsdWpvLgoKQWwgZWplY3V0YXJsbyBwcmVndW50YSBxdWUgcGVyaW9kbyBxdWllcmVzIChtdWVzdHJhIGxvcyBkaXNwb25pYmxlcyBlbiBsYQpiYXNlKSB5IGFybWEgZWwgZmx1am8gZGUgbGFzIHNvY2llZGFkZXMgcXVlIHRlbmdhbiBpbmZvcm1lIHBhcmEgZXNlIGNpZXJyZS4KCkhvamFzOgogIDEuIENvbnNvbGlkYWRvICAgICAgICAgICAgIC0gRXN0YWRvIGRlIGZsdWpvIElGMSBwb3Igc29jaWVkYWQKICAyLiBEZXRhbGxlIEN1ZW50YSBDb250YWJsZSAtIEN1ZW50YXMgY29udGFibGVzIGNvbiBEZWJlL0hhYmVyL05ldG8gY29uIHNpZ25vCiAgMy4gVGFibGEgRGluYW1pY2EgICAgICAgICAgLSBQaXZvdGUgc29icmUgZWwgZGV0YWxsZSAocmVxdWllcmUgRXhjZWwgaW5zdGFsYWRvKQoKUmVxdWlzaXRvczoKICBwaXAgaW5zdGFsbCBweW9kYmMgb3BlbnB5eGwgcHl3aW4zMgogIChweXdpbjMyIHNvbG8gZXMgbmVjZXNhcmlvIHBhcmEgbGEgdGFibGEgZGluYW1pY2E7IHNpbiBlbCwgZWwgc2NyaXB0CiAgIGdlbmVyYSBpZ3VhbCBsYXMgZG9zIHByaW1lcmFzIGhvamFzKQoKUmVnbGEgZGUgc2lnbm8gKHZhbGlkYWRhIGNvbnRyYSBsb3MgaW5mb3JtZXMgb2ZpY2lhbGVzIGRlIGVGbHVqbyk6CiAgLSBDdWVudGEgbm9ybWFsOiAgICAgICAgICAgIG5ldG8gPSBIYWJlciAtIERlYmUgIC0+IGxpbmVhIEZJRlJTMQogIC0gQ3VlbnRhIG1peHRhIChGTFVNSVg9U0kpOiBEZWJlIC0+IEZJRlJTMSBjb21vIC1EZWJlCiAgICAgICAgICAgICAgICAgICAgICAgICAgICAgIEhhYmVyIC0+IEZJRlJTMiBjb21vICtIYWJlcgogIC0gRXhjZXBjaW9uOiBsYSBsaW5lYSA0MDEwMTAwIChkaWYuIGRlIGNhbWJpbyBzb2JyZSBlbCBlZmVjdGl2bykgbGEKICAgIGNhbGN1bGEgZUZsdWpvIHBvciByZXZhbG9yaXphY2lvbiBkZWwgc2FsZG8sIG5vIGVzdGEgZW4gX01PVklFLgoiIiIKCmltcG9ydCBvcwppbXBvcnQgcmUKaW1wb3J0IHB5b2RiYwpmcm9tIG9wZW5weXhsIGltcG9ydCBXb3JrYm9vawpmcm9tIG9wZW5weXhsLnN0eWxlcyBpbXBvcnQgRm9udCwgUGF0dGVybkZpbGwsIEJvcmRlciwgU2lkZQpmcm9tIG9wZW5weXhsLnV0aWxzIGltcG9ydCBnZXRfY29sdW1uX2xldHRlcgoKIyAtLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tCiMgQ29uZmlndXJhY2lvbgojIC0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0KU0VSVkVSICAgPSByIlNRTC1XLUZFLVNQUC0wMVxGTFVKRUZFQyIgICAjIGxhIGluc3RhbmNpYSBlcyBGTFVKRUZFQyAoY29uIEMgZmluYWwpCkRBVEFCQVNFID0gImZsdWpvX2VmZWN0aXZvMDIiClVTRVIgICAgID0gInVzZXJmamVmZWMiClBBU1NXT1JEID0gb3MuZW52aXJvbi5nZXQoIkVGTFVKT19QV0QiLCAidXNjZWZlY3QyMDE0IikgICMgbWVqb3IgdmlhIHZhcmlhYmxlIGRlIGVudG9ybm8KClRJUE8gPSAiSUYxIgoKVE9EQVNfRU1QUkVTQVMgPSBbCiAgICAiQUdFTkNJQSIsICJBVExBTlRJQ08iLCAiQklOQVJJQSIsICJDQUJPTEVPTkVTIiwgIkNHRUEiLCAiQ0dFQyIsICJDR0VEIiwKICAgICJDR0VHIiwgIkNHRUgiLCAiQ0dFTSIsICJDR0VOIiwgIkNMRyIsICJDT05BRkUiLCAiRTExMSIsICJFMjA1IiwKICAgICJFREVMTUFHIiwgIkVMRUNEQSIsICJFTElRU0EiLCAiRU1FTEFSSSIsICJFTUVMQVQiLCAiRU1FTEFUSU5WIiwKICAgICJFTUVMTk9SVEUiLCAiRU5FUlBMVVMiLCAiR0FTTkFUVVJBTCIsICJHTkhPTERJTkciLCAiR1BHIiwgIkdQR1NPTEFSIiwKICAgICJHUzAwIiwgIklHU0EiLCAiSU5DQV9JIiwgIklOQ0FfSUkiLCAiTk9WQU5FVCIsICJTR0NFIiwgIlRFQ05FVCIsCiAgICAiVFJBTlNFTUVMIiwgIlRSQU5TTkVUIiwgIlZQQUMiLApdCgojIC0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0KIyBDb25leGlvbgojIC0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0KZGVmIGNvbmVjdGFyKCk6CiAgICBkcml2ZXJzID0gWyJPREJDIERyaXZlciAxOCBmb3IgU1FMIFNlcnZlciIsCiAgICAgICAgICAgICAgICJPREJDIERyaXZlciAxNyBmb3IgU1FMIFNlcnZlciIsCiAgICAgICAgICAgICAgICJTUUwgU2VydmVyIl0KICAgIHVsdGltb19lcnJvciA9IE5vbmUKICAgIGZvciBkcnYgaW4gZHJpdmVyczoKICAgICAgICB0cnk6CiAgICAgICAgICAgIGNzID0gKGYiRFJJVkVSPXt7e2Rydn19fTtTRVJWRVI9e1NFUlZFUn07REFUQUJBU0U9e0RBVEFCQVNFfTsiCiAgICAgICAgICAgICAgICAgIGYiVUlEPXtVU0VSfTtQV0Q9e1BBU1NXT1JEfTtUcnVzdFNlcnZlckNlcnRpZmljYXRlPXllcyIpCiAgICAgICAgICAgIHJldHVybiBweW9kYmMuY29ubmVjdChjcywgdGltZW91dD0xNSkKICAgICAgICBleGNlcHQgcHlvZGJjLkVycm9yIGFzIGU6CiAgICAgICAgICAgIHVsdGltb19lcnJvciA9IGUKICAgIHJhaXNlIFN5c3RlbUV4aXQoZiJObyBzZSBwdWRvIGNvbmVjdGFyIGNvbiBuaW5ndW4gZHJpdmVyIE9EQkM6IHt1bHRpbW9fZXJyb3J9IikKCgojIC0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0KIyBTZWxlY2Npb24gZGUgcGVyaW9kbwojIC0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0KZGVmIHBlZGlyX21lc19jaWVycmUoKToKICAgICIiIlBpZGUgZWwgbWVzIGRlIGNpZXJyZSAoTU0vQUFBQSkuIEVsIHBlcmlvZG8gc2llbXByZSBlcyBlbCBhY3VtdWxhZG8KICAgIGRlc2RlIGVuZXJvIGRlIGVzZSBhw7FvIGhhc3RhIGVsIG1lcyBpbmRpY2Fkby4iIiIKICAgIHdoaWxlIFRydWU6CiAgICAgICAgdGV4dG8gPSBpbnB1dCgiXG5NZXMgZGUgY2llcnJlIChNTS9BQUFBLCBlai4gMDYvMjAyNik6ICIpLnN0cmlwKCkKICAgICAgICBtID0gcmUubWF0Y2gociJeKFxkezEsMn0pXHMqWy9cLV1ccyooXGR7NH0pJCIsIHRleHRvKQogICAgICAgIGlmIG06CiAgICAgICAgICAgIG1lcywgYW5vID0gaW50KG0uZ3JvdXAoMSkpLCBpbnQobS5ncm91cCgyKSkKICAgICAgICAgICAgaWYgMSA8PSBtZXMgPD0gMTI6CiAgICAgICAgICAgICAgICByZXR1cm4gZiIwMS97YW5vfSIsIGYie21lczowMmR9L3thbm99IgogICAgICAgIHByaW50KCJGb3JtYXRvIG5vIHZhbGlkby4gVXNhIE1NL0FBQUEsIHBvciBlamVtcGxvIDA2LzIwMjYuIikKCgpkZWYgYnVzY2FyX3NvY2llZGFkZXMoY3VyLCBmZWNoYV9pbmksIGZlY2hhX2Zpbik6CiAgICAiIiJEZXZ1ZWx2ZSBsYXMgc29jaWVkYWRlcyBxdWUgdGllbmVuIGluZm9ybWUgSUYxIHBhcmEgZXNlIHBlcmlvZG8uIiIiCiAgICBlbmNvbnRyYWRhcyA9IFtdCiAgICBmb3IgZW1wIGluIFRPREFTX0VNUFJFU0FTOgogICAgICAgIHRyeToKICAgICAgICAgICAgY3VyLmV4ZWN1dGUoCiAgICAgICAgICAgICAgICBmIlNFTEVDVCBDT1VOVCgqKSBGUk9NIHtlbXB9X0ZMVUpPUyAiCiAgICAgICAgICAgICAgICBmIldIRVJFIFRJUE9GTFVKTz0/IEFORCBGRUNIQUlOST0/IEFORCBGRUNIQUZJTj0/IiwKICAgICAgICAgICAgICAgIFRJUE8sIGZlY2hhX2luaSwgZmVjaGFfZmluKQogICAgICAgICAgICBpZiBjdXIuZmV0Y2hvbmUoKVswXSA+IDA6CiAgICAgICAgICAgICAgICBlbmNvbnRyYWRhcy5hcHBlbmQoZW1wKQogICAgICAgIGV4Y2VwdCBweW9kYmMuRXJyb3I6CiAgICAgICAgICAgIGNvbnRpbnVlICAjIHRhYmxhIGluZXhpc3RlbnRlIG8gc2luIHBlcm1pc28KICAgIHJldHVybiBlbmNvbnRyYWRhcwoKCmRlZiBidXNjYXJfcHJlbGltaW5hcmVzKGN1ciwgZmVjaGFfZmluLCBleGNsdWlyKToKICAgICIiIlNvY2llZGFkZXMgU0lOIGluZm9ybWUgZ3VhcmRhZG8gcGVybyBDT04gbW92aW1pZW50b3MgY2FyZ2Fkb3MgZW4KICAgIF9NT1ZJRSBwYXJhIGVsIHBlcmlvZG8gKGVsIGZsdWpvIHNlIHB1ZWRlIGNhbGN1bGFyIGVuIGZvcm1hIHByZWxpbWluYXIpLiIiIgogICAgbWVzX2ZpbiwgYW5vID0gKGludCh4KSBmb3IgeCBpbiBmZWNoYV9maW4uc3BsaXQoIi8iKSkKICAgIGVuY29udHJhZGFzID0gW10KICAgIGZvciBlbXAgaW4gVE9EQVNfRU1QUkVTQVM6CiAgICAgICAgaWYgZW1wIGluIGV4Y2x1aXI6CiAgICAgICAgICAgIGNvbnRpbnVlCiAgICAgICAgdHJ5OgogICAgICAgICAgICBjdXIuZXhlY3V0ZSgKICAgICAgICAgICAgICAgIGYiU0VMRUNUIENPVU5UKCopIEZST00ge2VtcH1fTU9WSUUgIgogICAgICAgICAgICAgICAgZiJXSEVSRSBBTk89PyBBTkQgTUVTIEJFVFdFRU4gMSBBTkQgPyIsIGFubywgbWVzX2ZpbikKICAgICAgICAgICAgaWYgY3VyLmZldGNob25lKClbMF0gPiAwOgogICAgICAgICAgICAgICAgZW5jb250cmFkYXMuYXBwZW5kKGVtcCkKICAgICAgICBleGNlcHQgcHlvZGJjLkVycm9yOgogICAgICAgICAgICBjb250aW51ZQogICAgcmV0dXJuIGVuY29udHJhZGFzCgoKZGVmIGVsZWdpcl9wZXJpb2RvKGN1cik6CiAgICAiIiJQaWRlIGVsIG1lcyBkZSBjaWVycmUgeSBtdWVzdHJhIGxhcyBzb2NpZWRhZGVzIGVuY29udHJhZGFzLgogICAgRGV2dWVsdmUgKGZlY2hhX2luaSwgZmVjaGFfZmluLCBbZW1wcmVzYXMgY29uIGluZm9ybWVdLAogICAgW2VtcHJlc2FzIHByZWxpbWluYXJlcyBkZXNkZSBtb3ZpbWllbnRvc10pLiIiIgogICAgd2hpbGUgVHJ1ZToKICAgICAgICBmZWNoYV9pbmksIGZlY2hhX2ZpbiA9IHBlZGlyX21lc19jaWVycmUoKQogICAgICAgIHByaW50KGYiQnVzY2FuZG8gaW5mb3JtZXMgSUYxIGRlbCBwZXJpb2RvIHtmZWNoYV9pbml9IC0+IHtmZWNoYV9maW59Li4uIikKICAgICAgICBvZmljaWFsZXMgPSBidXNjYXJfc29jaWVkYWRlcyhjdXIsIGZlY2hhX2luaSwgZmVjaGFfZmluKQogICAgICAgIHByZWxpbWluYXJlcyA9IGJ1c2Nhcl9wcmVsaW1pbmFyZXMoY3VyLCBmZWNoYV9maW4sIHNldChvZmljaWFsZXMpKQoKICAgICAgICBpZiBub3Qgb2ZpY2lhbGVzIGFuZCBub3QgcHJlbGltaW5hcmVzOgogICAgICAgICAgICBwcmludCgiTmluZ3VuYSBzb2NpZWRhZCB0aWVuZSBpbmZvcm1lIG5pIG1vdmltaWVudG9zIHBhcmEgZXNlICIKICAgICAgICAgICAgICAgICAgImNpZXJyZS4gUHJ1ZWJhIGNvbiBvdHJvIG1lcy4iKQogICAgICAgICAgICBjb250aW51ZQoKICAgICAgICBpZiBvZmljaWFsZXM6CiAgICAgICAgICAgIHByaW50KGYiXG5Tb2NpZWRhZGVzIGNvbiBpbmZvcm1lIG9maWNpYWwgKHtsZW4ob2ZpY2lhbGVzKX0pOiIpCiAgICAgICAgICAgIGZvciBlbXAgaW4gb2ZpY2lhbGVzOgogICAgICAgICAgICAgICAgcHJpbnQoZiIgIC0ge2VtcH0iKQogICAgICAgIGVsc2U6CiAgICAgICAgICAgIHByaW50KCJcbk5pbmd1bmEgc29jaWVkYWQgdGllbmUgaW5mb3JtZSBvZmljaWFsIGd1YXJkYWRvICIKICAgICAgICAgICAgICAgICAgInBhcmEgZXNlIGNpZXJyZS4iKQoKICAgICAgICBpbmNsdWlkYXMgPSBbXQogICAgICAgIGlmIHByZWxpbWluYXJlczoKICAgICAgICAgICAgcHJpbnQoZiJcblNvY2llZGFkZXMgU0lOIGluZm9ybWUgZ3VhcmRhZG8gcGVybyBDT04gbW92aW1pZW50b3MgIgogICAgICAgICAgICAgICAgICBmImNhcmdhZG9zICh7bGVuKHByZWxpbWluYXJlcyl9KToiKQogICAgICAgICAgICBmb3IgZW1wIGluIHByZWxpbWluYXJlczoKICAgICAgICAgICAgICAgIHByaW50KGYiICAtIHtlbXB9IikKICAgICAgICAgICAgcmVzcCA9IGlucHV0KCJcbsK/SW5jbHVpcmxhcyBjb24gZmx1am8gUFJFTElNSU5BUiBjYWxjdWxhZG8gZGVzZGUgIgogICAgICAgICAgICAgICAgICAgICAgICAgImxvcyBtb3ZpbWllbnRvcz8gKHMvbik6ICIpLnN0cmlwKCkubG93ZXIoKQogICAgICAgICAgICBpZiByZXNwIGluICgicyIsICJzaSIsICJzw60iLCAieSIpOgogICAgICAgICAgICAgICAgaW5jbHVpZGFzID0gcHJlbGltaW5hcmVzCgogICAgICAgIGlmIG9maWNpYWxlcyBvciBpbmNsdWlkYXM6CiAgICAgICAgICAgIHJldHVybiBmZWNoYV9pbmksIGZlY2hhX2Zpbiwgb2ZpY2lhbGVzLCBpbmNsdWlkYXMKICAgICAgICBwcmludCgiTm8gcXVlZG8gbmluZ3VuYSBzb2NpZWRhZCBzZWxlY2Npb25hZGEuIFBydWViYSBkZSBudWV2by4iKQoKCiMgLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLQojIEV4dHJhY2Npb24KIyAtLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tClJFX0NVRU5UQV9GTFVKTyA9IHJlLmNvbXBpbGUociJeWzEyM11cZHs2fSQiKQoKUEFUUk9ORVNfU1VCVE9UQUwgPSBbCiAgICAoIk9QRVIiLCAgICByZS5jb21waWxlKHIiTmV0b3MuKk9wZXJhY2kiLCAgICAgICAgICAgICAgcmUuSSkpLAogICAgKCJJTlYiLCAgICAgcmUuY29tcGlsZShyIk5ldG9zLipJbnZlcnNpIiwgICAgICAgICAgICAgIHJlLkkpKSwKICAgICgiRklOIiwgICAgIHJlLmNvbXBpbGUociJOZXRvcy4qRmluYW5jaWFjaSIsICAgICAgICAgICByZS5JKSksCiAgICAoIkRJRkMiLCAgICByZS5jb21waWxlKHIiVmFyaWFjaW9uZXMgZW4gbGFzIFRhc2FzIiwgICAgcmUuSSkpLAogICAgKCJWQVJTVEMiLCAgcmUuY29tcGlsZShyImFudGVzIGRlbCBlZmVjdG8iLCAgICAgICAgICAgIHJlLkkpKSwKICAgICgiVkFSTkVUQSIsIHJlLmNvbXBpbGUociJJbmNyZW1lbnRvIFwoRGlzbWludWNpLm5cKSBkZSBlZmVjdGl2byIsIHJlLkkpKSwKICAgICgiU0lOSSIsICAgIHJlLmNvbXBpbGUociJTYWxkbyBJbmljaWFsIiwgICAgICAgICAgICAgICByZS5JKSksCiAgICAoIlNGSU4iLCAgICByZS5jb21waWxlKHIiU2FsZG8gRmluYWwiLCAgICAgICAgICAgICAgICAgcmUuSSkpLApdCgoKZGVmIGV4dHJhZXJfaW5mb3JtZShjdXIsIGVtcCwgZmVjaGFfaW5pLCBmZWNoYV9maW4pOgogICAgIiIiTGVlIGVsIGluZm9ybWUgSUYxIHJlbmRlcml6YWRvOiB2YWxvcmVzIHBvciBsaW5lYSB5IHN1YnRvdGFsZXMuIiIiCiAgICBsaW5lYXMsIHN1YnRvdGFsZXMgPSB7fSwge30KICAgIGN1ci5leGVjdXRlKAogICAgICAgIGYiU0VMRUNUIExUUklNKFJUUklNKENPTFVNTkExKSksIExUUklNKFJUUklNKENPTFVNTkEyKSksICIKICAgICAgICBmIkxUUklNKFJUUklNKENPTFVNTkE0KSkgRlJPTSB7ZW1wfV9GTFVKT1MgIgogICAgICAgIGYiV0hFUkUgVElQT0ZMVUpPPT8gQU5EIEZFQ0hBSU5JPT8gQU5EIEZFQ0hBRklOPT8gT1JERVIgQlkgRlBPU0lDSU9OIiwKICAgICAgICBUSVBPLCBmZWNoYV9pbmksIGZlY2hhX2ZpbikKICAgIGZvciBjMSwgYzIsIGM0IGluIGN1ci5mZXRjaGFsbCgpOgogICAgICAgIGlmIG5vdCBjNDoKICAgICAgICAgICAgY29udGludWUKICAgICAgICB0cnk6CiAgICAgICAgICAgIHZhbCA9IGZsb2F0KGM0KQogICAgICAgIGV4Y2VwdCBWYWx1ZUVycm9yOgogICAgICAgICAgICBjb250aW51ZQogICAgICAgIGlmIFJFX0NVRU5UQV9GTFVKTy5tYXRjaChjMSBvciAiIik6CiAgICAgICAgICAgIGxpbmVhc1tjMV0gPSBsaW5lYXMuZ2V0KGMxLCAwLjApICsgdmFsCiAgICAgICAgZWxzZToKICAgICAgICAgICAgZm9yIGNsYXZlLCBwYXRyb24gaW4gUEFUUk9ORVNfU1VCVE9UQUw6CiAgICAgICAgICAgICAgICBpZiBwYXRyb24uc2VhcmNoKGMyIG9yICIiKToKICAgICAgICAgICAgICAgICAgICBzdWJ0b3RhbGVzW2NsYXZlXSA9IHZhbAogICAgICAgICAgICAgICAgICAgIGJyZWFrCiAgICByZXR1cm4gbGluZWFzLCBzdWJ0b3RhbGVzCgoKZGVmIGV4dHJhZXJfbm9tYnJlc19saW5lYXMoY3VyLCBlbXByZXNhcywgZmVjaGFfaW5pLCBmZWNoYV9maW4pOgogICAgIiIiTm9tYnJlcyBJRlJTIGRlIGNhZGEgbGluZWEsIHRvbWFkb3MgZGUgbG9zIGluZm9ybWVzIElGMSByZWFsZXMKICAgIChsYSB0YWJsYSBFU1RGTFVKTyB0aWVuZSBsYSBwbGFudGlsbGEgYW50aWd1YSBTVlMgeSBhbGd1bm9zIGNvZGlnb3MKICAgIHNlIHJldXRpbGl6YW4gY29uIG90cm8gc2lnbmlmaWNhZG8pLiBTaSBlbCBwZXJpb2RvIGVsZWdpZG8gbm8gdGllbmUKICAgIGluZm9ybWVzLCBzZSBjb21wbGVtZW50YSBjb24gaW5mb3JtZXMgSUYxIGRlIGN1YWxxdWllciBwZXJpb2RvLiIiIgogICAgbm9tYnJlcyA9IHt9CgogICAgZGVmIHJlY29sZWN0YXIoZW1wLCBjb25fcGVyaW9kbyk6CiAgICAgICAgaWYgY29uX3BlcmlvZG86CiAgICAgICAgICAgIGN1ci5leGVjdXRlKAogICAgICAgICAgICAgICAgZiJTRUxFQ1QgTFRSSU0oUlRSSU0oQ09MVU1OQTEpKSwgTFRSSU0oUlRSSU0oQ09MVU1OQTIpKSAiCiAgICAgICAgICAgICAgICBmIkZST00ge2VtcH1fRkxVSk9TIFdIRVJFIFRJUE9GTFVKTz0/IEFORCBGRUNIQUlOST0/IEFORCBGRUNIQUZJTj0/IiwKICAgICAgICAgICAgICAgIFRJUE8sIGZlY2hhX2luaSwgZmVjaGFfZmluKQogICAgICAgIGVsc2U6CiAgICAgICAgICAgIGN1ci5leGVjdXRlKAogICAgICAgICAgICAgICAgZiJTRUxFQ1QgTFRSSU0oUlRSSU0oQ09MVU1OQTEpKSwgTFRSSU0oUlRSSU0oQ09MVU1OQTIpKSAiCiAgICAgICAgICAgICAgICBmIkZST00ge2VtcH1fRkxVSk9TIFdIRVJFIFRJUE9GTFVKTz0/IiwgVElQTykKICAgICAgICBmb3IgYzEsIGMyIGluIGN1ci5mZXRjaGFsbCgpOgogICAgICAgICAgICBpZiBSRV9DVUVOVEFfRkxVSk8ubWF0Y2goYzEgb3IgIiIpIGFuZCBjMSBub3QgaW4gbm9tYnJlczoKICAgICAgICAgICAgICAgIG5vbWJyZSA9IHJlLnNwbGl0KHIiXHN7Myx9IiwgYzIgb3IgIiIpWzBdLnN0cmlwKCkKICAgICAgICAgICAgICAgIGlmIG5vbWJyZToKICAgICAgICAgICAgICAgICAgICBub21icmVzW2MxXSA9IG5vbWJyZQoKICAgIGZvciBlbXAgaW4gZW1wcmVzYXM6CiAgICAgICAgcmVjb2xlY3RhcihlbXAsIFRydWUpCiAgICAjIGNvbXBsZW1lbnRvIGdsb2JhbDogY29kaWdvcyBxdWUgYXVuIG5vIHRlbmdhbiBub21icmUKICAgIGZvciBlbXAgaW4gVE9EQVNfRU1QUkVTQVM6CiAgICAgICAgdHJ5OgogICAgICAgICAgICByZWNvbGVjdGFyKGVtcCwgRmFsc2UpCiAgICAgICAgZXhjZXB0IHB5b2RiYy5FcnJvcjoKICAgICAgICAgICAgY29udGludWUKICAgIHJldHVybiBub21icmVzCgoKZGVmIGZsdWpvX3ByZWxpbWluYXIoZGV0YWxsZV9lbXApOgogICAgIiIiQ2FsY3VsYSBsaW5lYXMgeSBzdWJ0b3RhbGVzIGRlc2RlIGVsIGRldGFsbGUgZGUgbW92aW1pZW50b3MKICAgIChwYXJhIHNvY2llZGFkZXMgc2luIGluZm9ybWUgb2ZpY2lhbCkuIE5vIGluY2x1eWUgc2FsZG9zIGRlIGNhamE7CiAgICBsYSBkaWYuIGRlIGNhbWJpbyBzb2xvIHJlY29nZSBsbyBjb250YWJpbGl6YWRvIGVuIGN1ZW50YXMgbWFwZWFkYXMuIiIiCiAgICBsaW5lYXMsIHN1YnRvdGFsZXMgPSB7fSwge30KICAgIGZvciAoX2VtcCwgY29kLCBfbm9tZiwgX2N0YSwgX25vbSwgX21vdnMsIF9kLCBfaCwgbmV0bykgaW4gZGV0YWxsZV9lbXA6CiAgICAgICAgaWYgbm90IFJFX0NVRU5UQV9GTFVKTy5tYXRjaChjb2QpIGFuZCBub3QgY29kLnN0YXJ0c3dpdGgoIjQiKToKICAgICAgICAgICAgY29udGludWUKICAgICAgICBsaW5lYXNbY29kXSA9IGxpbmVhcy5nZXQoY29kLCAwLjApICsgbmV0bwogICAgb3BlciA9IHN1bSh2IGZvciBrLCB2IGluIGxpbmVhcy5pdGVtcygpIGlmIGsuc3RhcnRzd2l0aCgiMSIpKQogICAgaW52ICA9IHN1bSh2IGZvciBrLCB2IGluIGxpbmVhcy5pdGVtcygpIGlmIGsuc3RhcnRzd2l0aCgiMiIpKQogICAgZmluICA9IHN1bSh2IGZvciBrLCB2IGluIGxpbmVhcy5pdGVtcygpIGlmIGsuc3RhcnRzd2l0aCgiMyIpKQogICAgZGlmYyA9IHN1bSh2IGZvciBrLCB2IGluIGxpbmVhcy5pdGVtcygpIGlmIGsuc3RhcnRzd2l0aCgiNCIpKQogICAgc3VidG90YWxlc1siT1BFUiJdID0gb3BlcgogICAgc3VidG90YWxlc1siSU5WIl0gPSBpbnYKICAgIHN1YnRvdGFsZXNbIkZJTiJdID0gZmluCiAgICBzdWJ0b3RhbGVzWyJWQVJTVEMiXSA9IG9wZXIgKyBpbnYgKyBmaW4KICAgIGlmIGRpZmM6CiAgICAgICAgc3VidG90YWxlc1siRElGQyJdID0gZGlmYwogICAgc3VidG90YWxlc1siVkFSTkVUQSJdID0gb3BlciArIGludiArIGZpbiArIGRpZmMKICAgICMgc2luIFNJTkkvU0ZJTjogbG9zIHNhbGRvcyBkZSBjYWphIG5vIGVzdGFuIGVuIF9NT1ZJRQogICAgbGluZWFzID0ge2s6IHYgZm9yIGssIHYgaW4gbGluZWFzLml0ZW1zKCkgaWYgbm90IGsuc3RhcnRzd2l0aCgiNCIpfQogICAgcmV0dXJuIGxpbmVhcywgc3VidG90YWxlcwoKCmRlZiBleHRyYWVyX2RldGFsbGUoY3VyLCBlbXAsIG5vbWJyZXNfbGluZWFzLCBmZWNoYV9pbmksIGZlY2hhX2Zpbik6CiAgICAiIiJBZ3JlZ2EgX01PVklFIHBvciBjdWVudGEgKG1lc2VzIGRlbCBwZXJpb2RvKSB5IGFwbGljYSBsYSByZWdsYSBkZSBzaWduby4iIiIKICAgIG1lc19pbmksIGFub19pbmkgPSAoaW50KHgpIGZvciB4IGluIGZlY2hhX2luaS5zcGxpdCgiLyIpKQogICAgbWVzX2ZpbiwgYW5vX2ZpbiA9IChpbnQoeCkgZm9yIHggaW4gZmVjaGFfZmluLnNwbGl0KCIvIikpCiAgICBpZiBhbm9faW5pICE9IGFub19maW46CiAgICAgICAgIyBwZXJpb2RvIGNydXphIGVsIGHDsW86IGZpbHRyYXIgcG9yIHJhbmdvIGRlIGZlY2hhcyBjb21wbGV0bwogICAgICAgIGNvbmRpY2lvbiA9ICgiKChtLkFOTyA9ID8gQU5EIG0uTUVTID49ID8pIE9SIChtLkFOTyA9ID8gQU5EIG0uTUVTIDw9ID8pICIKICAgICAgICAgICAgICAgICAgICAgIk9SIChtLkFOTyA+ID8gQU5EIG0uQU5PIDwgPykpIikKICAgICAgICBwYXJhbXMgPSAoYW5vX2luaSwgbWVzX2luaSwgYW5vX2ZpbiwgbWVzX2ZpbiwgYW5vX2luaSwgYW5vX2ZpbikKICAgIGVsc2U6CiAgICAgICAgY29uZGljaW9uID0gIm0uQU5PID0gPyBBTkQgbS5NRVMgQkVUV0VFTiA/IEFORCA/IgogICAgICAgIHBhcmFtcyA9IChhbm9faW5pLCBtZXNfaW5pLCBtZXNfZmluKQoKICAgIGZpbGFzID0gW10KICAgIGN1ci5leGVjdXRlKGYiIiIKICAgICAgICBTRUxFQ1QgYy5DT0RDVEEsIExUUklNKFJUUklNKGMuTk9NQ1RBKSksCiAgICAgICAgICAgICAgIExUUklNKFJUUklNKElTTlVMTChjLkZJRlJTMSwnJykpKSwgTFRSSU0oUlRSSU0oSVNOVUxMKGMuRklGUlMyLCcnKSkpLAogICAgICAgICAgICAgICBMVFJJTShSVFJJTShJU05VTEwoYy5GTFVNSVgsJycpKSksCiAgICAgICAgICAgICAgIFNVTShDQVNFIFdIRU4gbS5USVBPTU9WPSdEJyBUSEVOIG0uTU9OVE8gRUxTRSAwIEVORCksCiAgICAgICAgICAgICAgIFNVTShDQVNFIFdIRU4gbS5USVBPTU9WPSdIJyBUSEVOIG0uTU9OVE8gRUxTRSAwIEVORCksCiAgICAgICAgICAgICAgIFNVTShDQVNFIFdIRU4gbS5USVBPTU9WPSdEJyBUSEVOIDEgRUxTRSAwIEVORCksCiAgICAgICAgICAgICAgIFNVTShDQVNFIFdIRU4gbS5USVBPTU9WPSdIJyBUSEVOIDEgRUxTRSAwIEVORCkKICAgICAgICBGUk9NIHtlbXB9X01PVklFIG0KICAgICAgICBKT0lOIHtlbXB9X0NVRU5UQVMgYyBPTiBjLkNPRENUQSA9IG0uQ1VFTlRBCiAgICAgICAgV0hFUkUge2NvbmRpY2lvbn0KICAgICAgICBHUk9VUCBCWSBjLkNPRENUQSwgTFRSSU0oUlRSSU0oYy5OT01DVEEpKSwgYy5GSUZSUzEsIGMuRklGUlMyLCBjLkZMVU1JWAogICAgICAgICIiIiwgKnBhcmFtcykKICAgIGZvciBjb2QsIG5vbSwgZjEsIGYyLCBtaXgsIGRlYmUsIGhhYmVyLCBuZCwgbmggaW4gY3VyLmZldGNoYWxsKCk6CiAgICAgICAgY29kID0gY29kLnN0cmlwKCkKICAgICAgICBpZiBtaXggPT0gIlNJIiBhbmQgZjI6CiAgICAgICAgICAgIGZpbGFzLmFwcGVuZCgoZW1wLCBmMSwgbm9tYnJlc19saW5lYXMuZ2V0KGYxLCAiIiksIGNvZCwgbm9tLAogICAgICAgICAgICAgICAgICAgICAgICAgIG5kLCBkZWJlLCAwLjAsIC1kZWJlKSkKICAgICAgICAgICAgZmlsYXMuYXBwZW5kKChlbXAsIGYyLCBub21icmVzX2xpbmVhcy5nZXQoZjIsICIiKSwgY29kLCBub20sCiAgICAgICAgICAgICAgICAgICAgICAgICAgbmgsIDAuMCwgaGFiZXIsIGhhYmVyKSkKICAgICAgICBlbHNlOgogICAgICAgICAgICBsaW5lYSA9IGYxIGlmIGYxIGVsc2UgIihzaW4gbWFwZW8pIgogICAgICAgICAgICBmaWxhcy5hcHBlbmQoKGVtcCwgbGluZWEsIG5vbWJyZXNfbGluZWFzLmdldChsaW5lYSwgIiIpLCBjb2QsIG5vbSwKICAgICAgICAgICAgICAgICAgICAgICAgICBuZCArIG5oLCBkZWJlLCBoYWJlciwgaGFiZXIgLSBkZWJlKSkKICAgIHJldHVybiBmaWxhcwoKCiMgLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLQojIEVzY3JpdHVyYSBFeGNlbCAob3BlbnB5eGwpCiMgLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLQpGTVRfTlVNICAgPSAiIywjIzA7KCMsIyMwKSIKRl9USVRVTE8gID0gRm9udChib2xkPVRydWUsIHNpemU9MTMpCkZfTkVHUklUQSA9IEZvbnQoYm9sZD1UcnVlKQpGX0hEUiAgICAgPSBGb250KGJvbGQ9VHJ1ZSwgY29sb3I9IkZGRkZGRiIpCkZJTExfSERSICA9IFBhdHRlcm5GaWxsKCJzb2xpZCIsIGZnQ29sb3I9IjMzMzMzMyIpCkZJTExfU0VDICA9IFBhdHRlcm5GaWxsKCJzb2xpZCIsIGZnQ29sb3I9IkU2RTZFNiIpCkJPUkRFX1RPVCA9IEJvcmRlcih0b3A9U2lkZShzdHlsZT0idGhpbiIpLCBib3R0b209U2lkZShzdHlsZT0idGhpbiIpKQoKTUVTRVMgPSB7MTogImVuZXJvIiwgMjogImZlYnJlcm8iLCAzOiAibWFyem8iLCA0OiAiYWJyaWwiLCA1OiAibWF5byIsCiAgICAgICAgIDY6ICJqdW5pbyIsIDc6ICJqdWxpbyIsIDg6ICJhZ29zdG8iLCA5OiAic2VwdGllbWJyZSIsCiAgICAgICAgIDEwOiAib2N0dWJyZSIsIDExOiAibm92aWVtYnJlIiwgMTI6ICJkaWNpZW1icmUifQoKCmRlZiBob2phX2NvbnNvbGlkYWRvKHdiLCBlbXByZXNhcywgbGluZWFzX2VtcCwgc3VidF9lbXAsIG5vbWJyZXMsCiAgICAgICAgICAgICAgICAgICAgIGZlY2hhX2luaSwgZmVjaGFfZmluLCBwcmVsaW1pbmFyZXM9KCkpOgogICAgd3MgPSB3Yi5hY3RpdmUKICAgIHdzLnRpdGxlID0gIkNvbnNvbGlkYWRvIgogICAgbmNvbCA9IDIgKyBsZW4oZW1wcmVzYXMpCiAgICBwcmVsaW1pbmFyZXMgPSBzZXQocHJlbGltaW5hcmVzKQoKICAgIG1pLCBhaSA9IChpbnQoeCkgZm9yIHggaW4gZmVjaGFfaW5pLnNwbGl0KCIvIikpCiAgICBtZiwgYWYgPSAoaW50KHgpIGZvciB4IGluIGZlY2hhX2Zpbi5zcGxpdCgiLyIpKQogICAgc3VidGl0dWxvID0gKGYiQWN1bXVsYWRvIGRlbCAxIGRlIHtNRVNFU1ttaV19IGRlIHthaX0gYWwgdWx0aW1vIGRpYSBkZSAiCiAgICAgICAgICAgICAgICAgZiJ7TUVTRVNbbWZdfSBkZSB7YWZ9IChjaWZyYXMgZW4gQ0xQKSIpCgogICAgd3MuY2VsbCgxLCAxLCAiRVNUQURPIERFIEZMVUpPIERFIEVGRUNUSVZPIElGUlMgLSBNZXRvZG8gRGlyZWN0byIpLmZvbnQgPSBGX1RJVFVMTwogICAgd3MuY2VsbCgyLCAxLCBzdWJ0aXR1bG8pLmZvbnQgPSBGb250KGl0YWxpYz1UcnVlKQogICAgaWYgcHJlbGltaW5hcmVzOgogICAgICAgIHdzLmNlbGwoMywgMSwgIigqKSBQUkVMSU1JTkFSOiBjYWxjdWxhZG8gZGVzZGUgbG9zIG1vdmltaWVudG9zICIKICAgICAgICAgICAgICAgICAgICAgICJjYXJnYWRvczsgc2luIGluZm9ybWUgb2ZpY2lhbCBlbiBlRmx1am8sIHNpbiBzYWxkb3MgIgogICAgICAgICAgICAgICAgICAgICAgImluaWNpYWwvZmluYWwgbmkgZGlmLiBkZSBjYW1iaW8gcG9yIHJldmFsb3JpemFjaW9uLiIKICAgICAgICAgICAgICAgICkuZm9udCA9IEZvbnQoaXRhbGljPVRydWUsIHNpemU9OSwgY29sb3I9IkIwMDAwMCIpCgogICAgZmlsYSA9IDQKICAgIHdzLmNlbGwoZmlsYSwgMSwgIkNvZGlnbyIpCiAgICB3cy5jZWxsKGZpbGEsIDIsICJDb25jZXB0byIpCiAgICBmb3IgaSwgZW1wIGluIGVudW1lcmF0ZShlbXByZXNhcyk6CiAgICAgICAgZXRpcXVldGEgPSBlbXAgKyAiICgqKSIgaWYgZW1wIGluIHByZWxpbWluYXJlcyBlbHNlIGVtcAogICAgICAgIHdzLmNlbGwoZmlsYSwgMyArIGksIGV0aXF1ZXRhKQogICAgZm9yIGMgaW4gcmFuZ2UoMSwgbmNvbCArIDEpOgogICAgICAgIHdzLmNlbGwoZmlsYSwgYykuZm9udCA9IEZfSERSCiAgICAgICAgd3MuY2VsbChmaWxhLCBjKS5maWxsID0gRklMTF9IRFIKICAgIGZpbGEgKz0gMQoKICAgIGNvZGlnb3MgPSBzb3J0ZWQoe2MgZm9yIGQgaW4gbGluZWFzX2VtcC52YWx1ZXMoKSBmb3IgYyBpbiBkfSkKICAgIHNlY2Npb25lcyA9IFsoIjEiLCAiRkxVSk8gREUgT1BFUkFDSU9OIiwgICAgIk9QRVIiLCAiRmx1am8gbmV0byBkZSBhY3RpdmlkYWRlcyBkZSBPcGVyYWNpb24iKSwKICAgICAgICAgICAgICAgICAoIjIiLCAiRkxVSk8gREUgSU5WRVJTSU9OIiwgICAgIklOViIsICAiRmx1am8gbmV0byBkZSBhY3RpdmlkYWRlcyBkZSBJbnZlcnNpb24iKSwKICAgICAgICAgICAgICAgICAoIjMiLCAiRkxVSk8gREUgRklOQU5DSUFDSU9OIiwgIkZJTiIsICAiRmx1am8gbmV0byBkZSBhY3RpdmlkYWRlcyBkZSBGaW5hbmNpYWNpb24iKV0KCiAgICBmb3IgcHJlZmlqbywgdGl0dWxvLCBjbGF2ZSwgZXRpcXVldGEgaW4gc2VjY2lvbmVzOgogICAgICAgIHdzLmNlbGwoZmlsYSwgMiwgdGl0dWxvKS5mb250ID0gRl9ORUdSSVRBCiAgICAgICAgZm9yIGMgaW4gcmFuZ2UoMSwgbmNvbCArIDEpOgogICAgICAgICAgICB3cy5jZWxsKGZpbGEsIGMpLmZpbGwgPSBGSUxMX1NFQwogICAgICAgIGZpbGEgKz0gMQogICAgICAgIGZvciBjb2QgaW4gY29kaWdvczoKICAgICAgICAgICAgaWYgbm90IGNvZC5zdGFydHN3aXRoKHByZWZpam8pOgogICAgICAgICAgICAgICAgY29udGludWUKICAgICAgICAgICAgd3MuY2VsbChmaWxhLCAxLCBjb2QpCiAgICAgICAgICAgIHdzLmNlbGwoZmlsYSwgMiwgbm9tYnJlcy5nZXQoY29kLCAiIikpCiAgICAgICAgICAgIGZvciBpLCBlbXAgaW4gZW51bWVyYXRlKGVtcHJlc2FzKToKICAgICAgICAgICAgICAgIGlmIGNvZCBpbiBsaW5lYXNfZW1wW2VtcF06CiAgICAgICAgICAgICAgICAgICAgY2VsID0gd3MuY2VsbChmaWxhLCAzICsgaSwgbGluZWFzX2VtcFtlbXBdW2NvZF0pCiAgICAgICAgICAgICAgICAgICAgY2VsLm51bWJlcl9mb3JtYXQgPSBGTVRfTlVNCiAgICAgICAgICAgIGZpbGEgKz0gMQogICAgICAgIHdzLmNlbGwoZmlsYSwgMiwgZXRpcXVldGEpLmZvbnQgPSBGX05FR1JJVEEKICAgICAgICBmb3IgaSwgZW1wIGluIGVudW1lcmF0ZShlbXByZXNhcyk6CiAgICAgICAgICAgIGlmIGNsYXZlIGluIHN1YnRfZW1wW2VtcF06CiAgICAgICAgICAgICAgICBjZWwgPSB3cy5jZWxsKGZpbGEsIDMgKyBpLCBzdWJ0X2VtcFtlbXBdW2NsYXZlXSkKICAgICAgICAgICAgICAgIGNlbC5udW1iZXJfZm9ybWF0ID0gRk1UX05VTQogICAgICAgICAgICAgICAgY2VsLmZvbnQgPSBGX05FR1JJVEEKICAgICAgICBmb3IgYyBpbiByYW5nZSgxLCBuY29sICsgMSk6CiAgICAgICAgICAgIHdzLmNlbGwoZmlsYSwgYykuYm9yZGVyID0gQk9SREVfVE9UCiAgICAgICAgZmlsYSArPSAyCgogICAgcmVzdW1lbiA9IFsoIlZBUlNUQyIsICAiSW5jcmVtZW50byAoZGlzbWludWNpb24pIGFudGVzIGRlIGRpZi4gZGUgY2FtYmlvIiwgRmFsc2UpLAogICAgICAgICAgICAgICAoIkRJRkMiLCAgICAiRWZlY3RvIHZhcmlhY2lvbmVzIHRhc2EgZGUgY2FtYmlvIiwgICAgICAgICAgICAgICAgRmFsc2UpLAogICAgICAgICAgICAgICAoIlZBUk5FVEEiLCAiSW5jcmVtZW50byAoZGlzbWludWNpb24pIG5ldG8gZGUgZWZlY3Rpdm8iLCAgICAgICAgVHJ1ZSksCiAgICAgICAgICAgICAgICgiU0lOSSIsICAgICJFZmVjdGl2bywgc2FsZG8gaW5pY2lhbCIsICAgICAgICAgICAgICAgICAgICAgICAgICBGYWxzZSksCiAgICAgICAgICAgICAgICgiU0ZJTiIsICAgICJFZmVjdGl2bywgc2FsZG8gZmluYWwiLCAgICAgICAgICAgICAgICAgICAgICAgICAgICBUcnVlKV0KICAgIGZvciBjbGF2ZSwgZXRpcXVldGEsIGRlc3RhY2FyIGluIHJlc3VtZW46CiAgICAgICAgd3MuY2VsbChmaWxhLCAyLCBldGlxdWV0YSkuZm9udCA9IEZfTkVHUklUQSBpZiBkZXN0YWNhciBlbHNlIEZvbnQoKQogICAgICAgIGZvciBpLCBlbXAgaW4gZW51bWVyYXRlKGVtcHJlc2FzKToKICAgICAgICAgICAgaWYgY2xhdmUgaW4gc3VidF9lbXBbZW1wXToKICAgICAgICAgICAgICAgIGNlbCA9IHdzLmNlbGwoZmlsYSwgMyArIGksIHN1YnRfZW1wW2VtcF1bY2xhdmVdKQogICAgICAgICAgICAgICAgY2VsLm51bWJlcl9mb3JtYXQgPSBGTVRfTlVNCiAgICAgICAgICAgICAgICBpZiBkZXN0YWNhcjoKICAgICAgICAgICAgICAgICAgICBjZWwuZm9udCA9IEZfTkVHUklUQQogICAgICAgIGZpbGEgKz0gMQoKICAgIHdzLmNvbHVtbl9kaW1lbnNpb25zWyJBIl0ud2lkdGggPSAxMAogICAgd3MuY29sdW1uX2RpbWVuc2lvbnNbIkIiXS53aWR0aCA9IDUyCiAgICBmb3IgaSBpbiByYW5nZShsZW4oZW1wcmVzYXMpKToKICAgICAgICB3cy5jb2x1bW5fZGltZW5zaW9uc1tnZXRfY29sdW1uX2xldHRlcigzICsgaSldLndpZHRoID0gMTgKICAgIHdzLmZyZWV6ZV9wYW5lcyA9ICJBNSIKCgpkZWYgaG9qYV9kZXRhbGxlKHdiLCBkZXRhbGxlLCBmZWNoYV9pbmksIGZlY2hhX2Zpbik6CiAgICB3cyA9IHdiLmNyZWF0ZV9zaGVldCgiRGV0YWxsZSBDdWVudGEgQ29udGFibGUiKQogICAgd3MuY2VsbCgxLCAxLCBmIkRFVEFMTEUgUE9SIENVRU5UQSBDT05UQUJMRSBDT04gU0lHTk8gLSBNb3ZpbWllbnRvcyAiCiAgICAgICAgICAgICAgICAgIGYie2ZlY2hhX2luaX0gYSB7ZmVjaGFfZmlufSIpLmZvbnQgPSBGb250KGJvbGQ9VHJ1ZSwgc2l6ZT0xMikKICAgIHdzLmNlbGwoMiwgMSwgIk5ldG8gPSBIYWJlciAtIERlYmUgKGN1ZW50YXMgbm9ybWFsZXMpIHwgbWl4dGFzOiBEZWJlLT5GSUZSUzEoLSksICIKICAgICAgICAgICAgICAgICAgIkhhYmVyLT5GSUZSUzIoKykuIEN1YWRyYSBjb24gZWwgZmx1am8gb2ZpY2lhbCBzYWx2byBkaWYuIGRlIGNhbWJpby4iCiAgICAgICAgICAgICkuZm9udCA9IEZvbnQoaXRhbGljPVRydWUsIHNpemU9OSkKCiAgICBlbmNhYmV6YWRvcyA9IFsiU29jaWVkYWQiLCAiQ29kLiBMaW5lYSBGbHVqbyIsICJMaW5lYSBkZSBGbHVqbyAoSUZSUykiLAogICAgICAgICAgICAgICAgICAgIkN1ZW50YSBDb250YWJsZSIsICJOb21icmUgQ3VlbnRhIENvbnRhYmxlIiwgIk4gTW92cyIsCiAgICAgICAgICAgICAgICAgICAiRGViZSIsICJIYWJlciIsICJOZXRvIGNvbiBzaWdubyAoQ0xQKSJdCiAgICBmaWxhID0gNAogICAgZm9yIGosIGggaW4gZW51bWVyYXRlKGVuY2FiZXphZG9zLCBzdGFydD0xKToKICAgICAgICBjZWwgPSB3cy5jZWxsKGZpbGEsIGosIGgpCiAgICAgICAgY2VsLmZvbnQgPSBGX0hEUgogICAgICAgIGNlbC5maWxsID0gRklMTF9IRFIKCiAgICBmb3IgeCBpbiBzb3J0ZWQoZGV0YWxsZSwga2V5PWxhbWJkYSByOiAoclswXSwgclsxXSwgclszXSkpOgogICAgICAgIGZpbGEgKz0gMQogICAgICAgIGZvciBqLCB2IGluIGVudW1lcmF0ZSh4LCBzdGFydD0xKToKICAgICAgICAgICAgY2VsID0gd3MuY2VsbChmaWxhLCBqLCB2KQogICAgICAgICAgICBpZiBqIGluICg3LCA4LCA5KToKICAgICAgICAgICAgICAgIGNlbC5udW1iZXJfZm9ybWF0ID0gRk1UX05VTQogICAgICAgIHdzLmNlbGwoZmlsYSwgMikubnVtYmVyX2Zvcm1hdCA9ICJAIgogICAgICAgIHdzLmNlbGwoZmlsYSwgNCkubnVtYmVyX2Zvcm1hdCA9ICJAIgoKICAgIGFuY2hvcyA9IFsxMSwgMTQsIDQ2LCAxMywgNDQsIDgsIDE4LCAxOCwgMjBdCiAgICBmb3IgaiwgdyBpbiBlbnVtZXJhdGUoYW5jaG9zLCBzdGFydD0xKToKICAgICAgICB3cy5jb2x1bW5fZGltZW5zaW9uc1tnZXRfY29sdW1uX2xldHRlcihqKV0ud2lkdGggPSB3CiAgICB3cy5mcmVlemVfcGFuZXMgPSAiQTUiCiAgICB3cy5hdXRvX2ZpbHRlci5yZWYgPSBmIkE0Okl7ZmlsYX0iCiAgICByZXR1cm4gZmlsYQoKCmRlZiB0YWJsYV9kaW5hbWljYShydXRhX3hsc3gsIHVsdGltYV9maWxhLCBmZWNoYV9pbmksIGZlY2hhX2Zpbik6CiAgICAiIiJDcmVhIGxhIHRhYmxhIGRpbmFtaWNhIGNvbiBFeGNlbCBDT00gKG9wZW5weXhsIG5vIHNvcG9ydGEgcGl2b3RlcyBuYXRpdm9zKS4iIiIKICAgIHRyeToKICAgICAgICBpbXBvcnQgd2luMzJjb20uY2xpZW50CiAgICBleGNlcHQgSW1wb3J0RXJyb3I6CiAgICAgICAgcHJpbnQoIkFWSVNPOiBweXdpbjMyIG5vIGluc3RhbGFkbzsgc2Ugb21pdGUgbGEgdGFibGEgZGluYW1pY2EuIikKICAgICAgICByZXR1cm4KICAgIHhsID0gd2luMzJjb20uY2xpZW50LkRpc3BhdGNoRXgoIkV4Y2VsLkFwcGxpY2F0aW9uIikKICAgIHhsLlZpc2libGUgPSBGYWxzZQogICAgeGwuRGlzcGxheUFsZXJ0cyA9IEZhbHNlCiAgICB0cnk6CiAgICAgICAgd2IgPSB4bC5Xb3JrYm9va3MuT3BlbihydXRhX3hsc3gpCiAgICAgICAgZGV0ID0gd2IuV29ya3NoZWV0cygiRGV0YWxsZSBDdWVudGEgQ29udGFibGUiKQogICAgICAgIG9yaWdlbiA9IGRldC5SYW5nZShkZXQuQ2VsbHMoNCwgMSksIGRldC5DZWxscyh1bHRpbWFfZmlsYSwgOSkpCiAgICAgICAgcHYgPSB3Yi5Xb3Jrc2hlZXRzLkFkZChBZnRlcj13Yi5Xb3Jrc2hlZXRzKHdiLldvcmtzaGVldHMuQ291bnQpKQogICAgICAgIHB2Lk5hbWUgPSAiVGFibGEgRGluYW1pY2EiCiAgICAgICAgY2FjaGUgPSB3Yi5QaXZvdENhY2hlcygpLkNyZWF0ZSgxLCBvcmlnZW4pICAgICAgICAgICMgMSA9IHhsRGF0YWJhc2UKICAgICAgICBwdCA9IGNhY2hlLkNyZWF0ZVBpdm90VGFibGUocHYuUmFuZ2UoIkEzIiksICJQVF9GbHVqbyIpCiAgICAgICAgcHQuUGl2b3RGaWVsZHMoIlNvY2llZGFkIikuT3JpZW50YXRpb24gPSAyICAgICAgICAgICMgY29sdW1uYQogICAgICAgIGYxID0gcHQuUGl2b3RGaWVsZHMoIkNvZC4gTGluZWEgRmx1am8iKTsgICAgICAgIGYxLk9yaWVudGF0aW9uID0gMTsgZjEuUG9zaXRpb24gPSAxCiAgICAgICAgZjIgPSBwdC5QaXZvdEZpZWxkcygiTGluZWEgZGUgRmx1am8gKElGUlMpIik7ICAgZjIuT3JpZW50YXRpb24gPSAxOyBmMi5Qb3NpdGlvbiA9IDIKICAgICAgICBmMyA9IHB0LlBpdm90RmllbGRzKCJOb21icmUgQ3VlbnRhIENvbnRhYmxlIik7ICBmMy5PcmllbnRhdGlvbiA9IDE7IGYzLlBvc2l0aW9uID0gMwogICAgICAgIGRmID0gcHQuQWRkRGF0YUZpZWxkKHB0LlBpdm90RmllbGRzKCJOZXRvIGNvbiBzaWdubyAoQ0xQKSIpLCAiTmV0byBDTFAiLCAtNDE1NykKICAgICAgICBkZi5OdW1iZXJGb3JtYXQgPSBGTVRfTlVNCiAgICAgICAgcHQuUm93QXhpc0xheW91dCgxKSAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICMgdGFidWxhcgogICAgICAgIHB0LlJlcGVhdEFsbExhYmVscygyKQogICAgICAgIHRyeToKICAgICAgICAgICAgZjMuU2hvd0RldGFpbCA9IEZhbHNlCiAgICAgICAgZXhjZXB0IEV4Y2VwdGlvbjoKICAgICAgICAgICAgcGFzcwogICAgICAgIHB2LkNlbGxzKDEsIDEpLlZhbHVlID0gKGYiVEFCTEEgRElOQU1JQ0EgLSBGbHVqbyBuZXRvIGNvbiBzaWdubyBwb3IgbGluZWEgIgogICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgIGYieSBzb2NpZWRhZCAoe2ZlY2hhX2luaX0gYSB7ZmVjaGFfZmlufSkiKQogICAgICAgIHB2LlJhbmdlKCJBMSIpLkZvbnQuQm9sZCA9IFRydWUKICAgICAgICBwdi5Db2x1bW5zKDEpLkNvbHVtbldpZHRoID0gMTYKICAgICAgICBwdi5Db2x1bW5zKDIpLkNvbHVtbldpZHRoID0gNDYKICAgICAgICBwdi5Db2x1bW5zKDMpLkNvbHVtbldpZHRoID0gNDQKICAgICAgICB3Yi5TYXZlKCkKICAgICAgICB3Yi5DbG9zZShGYWxzZSkKICAgIGZpbmFsbHk6CiAgICAgICAgeGwuUXVpdCgpCgoKIyAtLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tCiMgTWFpbgojIC0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0KZGVmIG1haW4oKToKICAgIGNuID0gY29uZWN0YXIoKQogICAgY3VyID0gY24uY3Vyc29yKCkKICAgIHByaW50KGYiQ29uZWN0YWRvIGEge1NFUlZFUn0ve0RBVEFCQVNFfSIpCgogICAgZmVjaGFfaW5pLCBmZWNoYV9maW4sIG9maWNpYWxlcywgcHJlbGltaW5hcmVzID0gZWxlZ2lyX3BlcmlvZG8oY3VyKQogICAgZW1wcmVzYXMgPSBvZmljaWFsZXMgKyBbZSBmb3IgZSBpbiBwcmVsaW1pbmFyZXMgaWYgZSBub3QgaW4gb2ZpY2lhbGVzXQogICAgcHJpbnQoZiJcblBlcmlvZG8gZWxlZ2lkbzoge2ZlY2hhX2luaX0gLT4ge2ZlY2hhX2Zpbn0iKQogICAgcHJpbnQoZiJDb24gaW5mb3JtZSBvZmljaWFsIDogeycsICcuam9pbihvZmljaWFsZXMpIGlmIG9maWNpYWxlcyBlbHNlICctJ30iKQogICAgcHJpbnQoZiJQcmVsaW1pbmFyZXMgICAgICAgIDogeycsICcuam9pbihwcmVsaW1pbmFyZXMpIGlmIHByZWxpbWluYXJlcyBlbHNlICctJ30iKQoKICAgIHNhbGlkYSA9IG9zLnBhdGguam9pbigKICAgICAgICBvcy5wYXRoLmRpcm5hbWUob3MucGF0aC5hYnNwYXRoKF9fZmlsZV9fKSksCiAgICAgICAgZiJGbHVqb19FZmVjdGl2b197ZmVjaGFfZmluLnJlcGxhY2UoJy8nLCAnLScpfS54bHN4IikKCiAgICBub21icmVzID0gZXh0cmFlcl9ub21icmVzX2xpbmVhcyhjdXIsIG9maWNpYWxlcywgZmVjaGFfaW5pLCBmZWNoYV9maW4pCiAgICBwcmludChmIkxpbmVhcyBkZSBmbHVqbyBpZGVudGlmaWNhZGFzOiB7bGVuKG5vbWJyZXMpfSIpCgogICAgbGluZWFzX2VtcCwgc3VidF9lbXAsIGRldGFsbGUgPSB7fSwge30sIFtdCiAgICBmb3IgZW1wIGluIGVtcHJlc2FzOgogICAgICAgIGRldCA9IGV4dHJhZXJfZGV0YWxsZShjdXIsIGVtcCwgbm9tYnJlcywgZmVjaGFfaW5pLCBmZWNoYV9maW4pCiAgICAgICAgZGV0YWxsZS5leHRlbmQoZGV0KQogICAgICAgIGlmIGVtcCBpbiBvZmljaWFsZXM6CiAgICAgICAgICAgIGxpbmVhc19lbXBbZW1wXSwgc3VidF9lbXBbZW1wXSA9IGV4dHJhZXJfaW5mb3JtZSgKICAgICAgICAgICAgICAgIGN1ciwgZW1wLCBmZWNoYV9pbmksIGZlY2hhX2ZpbikKICAgICAgICAgICAgb3JpZ2VuID0gImluZm9ybWUgb2ZpY2lhbCIKICAgICAgICBlbHNlOgogICAgICAgICAgICBsaW5lYXNfZW1wW2VtcF0sIHN1YnRfZW1wW2VtcF0gPSBmbHVqb19wcmVsaW1pbmFyKGRldCkKICAgICAgICAgICAgb3JpZ2VuID0gIlBSRUxJTUlOQVIgZGVzZGUgbW92aW1pZW50b3MiCiAgICAgICAgcHJpbnQoZiIgIHtlbXA6MTBzfToge2xlbihsaW5lYXNfZW1wW2VtcF0pfSBsaW5lYXMgKHtvcmlnZW59KSwgIgogICAgICAgICAgICAgIGYie2xlbihkZXQpfSBmaWxhcyBkZSBkZXRhbGxlIikKICAgIGNuLmNsb3NlKCkKCiAgICB3YiA9IFdvcmtib29rKCkKICAgIGhvamFfY29uc29saWRhZG8od2IsIGVtcHJlc2FzLCBsaW5lYXNfZW1wLCBzdWJ0X2VtcCwgbm9tYnJlcywKICAgICAgICAgICAgICAgICAgICAgZmVjaGFfaW5pLCBmZWNoYV9maW4sIHByZWxpbWluYXJlcykKICAgIHVsdGltYSA9IGhvamFfZGV0YWxsZSh3YiwgZGV0YWxsZSwgZmVjaGFfaW5pLCBmZWNoYV9maW4pCiAgICB3Yi5zYXZlKHNhbGlkYSkKICAgIHByaW50KGYiR3VhcmRhZG86IHtzYWxpZGF9IikKCiAgICB0YWJsYV9kaW5hbWljYShzYWxpZGEsIHVsdGltYSwgZmVjaGFfaW5pLCBmZWNoYV9maW4pCiAgICBwcmludCgiTGlzdG8uIikKCgppZiBfX25hbWVfXyA9PSAiX19tYWluX18iOgogICAgbWFpbigpCg=="
).decode("utf-8")

_MCP_V2_SRC = base64.b64decode(
    b"IyEvdXNyL2Jpbi9lbnYgcHl0aG9uMwoiIiIKd29ya2l2YV9tY3BfdjIucHkgIOKGkCAgRVNQRUpPIGNvbiBzb3BvcnRlIEVFUlIgcGFyYSBRMi9RMy9RNAo9PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09CklndWFsIHF1ZSB3b3JraXZhX21jcC5weSBjb24gZXN0b3MgY2FtYmlvcyBlbiB3b3JraXZhX2ZpbGxfY29tcGFyYXRpdmVzOgoKICAxLiBCdXNjYSB1biBzZWd1bmRvIGFyY2hpdm8gZnVlbnRlIHBhcmEgRUVSUiAocHJpb3JfZWVycl9lbmQpLgogIDIuIERldGVjdGEgY29sdW1uYXMgY29tcGFyYXRpdmFzIGRlIEJBTEFOQ0UgKHByaW9yX2VuZCkgWSBkZSBFRVJSCiAgICAgKHByaW9yX2VlcnJfZW5kKSBlbiBsb3MgZW5jYWJlemFkb3MgZGUgY2FkYSBob2phLgogIDMuIExhIHJlc3RyaWNjacOzbiAic29sbyBtZXMgMDMgZXNjcmliZSIgc2UgYXBsaWNhIMO6bmljYW1lbnRlIGEgbGFzCiAgICAgY29sdW1uYXMgZGUgQkFMQU5DRTsgbGFzIGNvbHVtbmFzIEVFUlIgc2UgZXNjcmliZW4gZW4gY3VhbHF1aWVyIG1lcy4KClRvZG8gbG8gZGVtw6FzIGVzIGlkw6ludGljbyBhbCBvcmlnaW5hbC4KIiIiCgpmcm9tIF9fZnV0dXJlX18gaW1wb3J0IGFubm90YXRpb25zCgppbXBvcnQgYXN5bmNpbwppbXBvcnQgY3N2CmltcG9ydCBpbwppbXBvcnQganNvbgppbXBvcnQgb3MKaW1wb3J0IHJlCmltcG9ydCB0aW1lCmltcG9ydCB1bmljb2RlZGF0YQppbXBvcnQgd2FybmluZ3MKZnJvbSBjb250ZXh0bGliIGltcG9ydCBhc3luY2NvbnRleHRtYW5hZ2VyCmZyb20gdHlwaW5nIGltcG9ydCBBbnksIE9wdGlvbmFsCgppbXBvcnQgaHR0cHgKZnJvbSBkb3RlbnYgaW1wb3J0IGxvYWRfZG90ZW52CmZyb20gbWNwLnNlcnZlci5mYXN0bWNwIGltcG9ydCBGYXN0TUNQCmZyb20gcHlkYW50aWMgaW1wb3J0IEJhc2VNb2RlbCwgQ29uZmlnRGljdCwgRmllbGQKCiMg4pSA4pSAIENyZWRlbmNpYWxlcyDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIAKbG9hZF9kb3RlbnYoZG90ZW52X3BhdGg9b3MucGF0aC5qb2luKG9zLnBhdGguZGlybmFtZShfX2ZpbGVfXyksICIuZW52IikpCgpDTElFTlRfSUQgICAgID0gb3MuZ2V0ZW52KCJXT1JLSVZBX0NMSUVOVF9JRCIsICIiKQpDTElFTlRfU0VDUkVUID0gb3MuZ2V0ZW52KCJXT1JLSVZBX0NMSUVOVF9TRUNSRVQiLCAiIikKV09SS1NQQUNFX0lEICA9IG9zLmdldGVudigiV09SS0lWQV9XT1JLU1BBQ0VfSUQiLCAiIikKCiMg4pSA4pSAIEVuZHBvaW50cyDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIAKVE9LRU5fVVJMICAgID0gImh0dHBzOi8vYXBpLmFwcC53ZGVzay5jb20vaWFtL3YxL29hdXRoMi90b2tlbiIKUExBVEZPUk1fVVJMID0gImh0dHBzOi8vYXBpLmFwcC53ZGVzay5jb20vcGxhdGZvcm0vdjEiCldEQVRBX1VSTCAgICA9ICJodHRwczovL2guYXBwLndkZXNrLmNvbS9zL3dkYXRhL3ByZXAvYXBpL3YxIgoKVkVSSUZZX1NTTCA9IEZhbHNlCndhcm5pbmdzLmZpbHRlcndhcm5pbmdzKCJpZ25vcmUiKQoKCiMg4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQCiMgQ0xJRU5URSBDT01QQVJUSURPIENPTiBSRUZSRVNIIERFIFRPS0VOCiMg4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQCgpjbGFzcyBXb3JraXZhQ2xpZW50OgogICAgZGVmIF9faW5pdF9fKHNlbGYpIC0+IE5vbmU6CiAgICAgICAgc2VsZi5fdG9rZW46IHN0ciA9ICIiCiAgICAgICAgc2VsZi5fdG9rZW5fdHM6IGZsb2F0ID0gMC4wCiAgICAgICAgc2VsZi5fY2xpZW50OiBodHRweC5Bc3luY0NsaWVudCB8IE5vbmUgPSBOb25lCgogICAgYXN5bmMgZGVmIF9lbnN1cmVfY2xpZW50KHNlbGYpIC0+IGh0dHB4LkFzeW5jQ2xpZW50OgogICAgICAgIGlmIHNlbGYuX2NsaWVudCBpcyBOb25lIG9yIHNlbGYuX2NsaWVudC5pc19jbG9zZWQ6CiAgICAgICAgICAgIHNlbGYuX2NsaWVudCA9IGh0dHB4LkFzeW5jQ2xpZW50KHZlcmlmeT1WRVJJRllfU1NMLCB0aW1lb3V0PTEyMC4wKQogICAgICAgIHJldHVybiBzZWxmLl9jbGllbnQKCiAgICBhc3luYyBkZWYgX2dldF90b2tlbihzZWxmKSAtPiBzdHI6CiAgICAgICAgaWYgdGltZS50aW1lKCkgLSBzZWxmLl90b2tlbl90cyA8IDU0MCBhbmQgc2VsZi5fdG9rZW46CiAgICAgICAgICAgIHJldHVybiBzZWxmLl90b2tlbgogICAgICAgIGNsaWVudCA9IGF3YWl0IHNlbGYuX2Vuc3VyZV9jbGllbnQoKQogICAgICAgIHJlc3AgPSBhd2FpdCBjbGllbnQucG9zdCgKICAgICAgICAgICAgVE9LRU5fVVJMLAogICAgICAgICAgICBqc29uPXsKICAgICAgICAgICAgICAgICJncmFudF90eXBlIjogICAgImNsaWVudF9jcmVkZW50aWFscyIsCiAgICAgICAgICAgICAgICAiY2xpZW50X2lkIjogICAgIENMSUVOVF9JRCwKICAgICAgICAgICAgICAgICJjbGllbnRfc2VjcmV0IjogQ0xJRU5UX1NFQ1JFVCwKICAgICAgICAgICAgfSwKICAgICAgICAgICAgaGVhZGVycz17IkNvbnRlbnQtVHlwZSI6ICJhcHBsaWNhdGlvbi9qc29uIn0sCiAgICAgICAgKQogICAgICAgIHJlc3AucmFpc2VfZm9yX3N0YXR1cygpCiAgICAgICAgc2VsZi5fdG9rZW4gICAgPSByZXNwLmpzb24oKVsiYWNjZXNzX3Rva2VuIl0KICAgICAgICBzZWxmLl90b2tlbl90cyA9IHRpbWUudGltZSgpCiAgICAgICAgcmV0dXJuIHNlbGYuX3Rva2VuCgogICAgYXN5bmMgZGVmIF9oZWFkZXJzKHNlbGYpIC0+IGRpY3Rbc3RyLCBzdHJdOgogICAgICAgIHRva2VuID0gYXdhaXQgc2VsZi5fZ2V0X3Rva2VuKCkKICAgICAgICByZXR1cm4gewogICAgICAgICAgICAiQXV0aG9yaXphdGlvbiI6IGYiQmVhcmVyIHt0b2tlbn0iLAogICAgICAgICAgICAiQ29udGVudC1UeXBlIjogICJhcHBsaWNhdGlvbi9qc29uIiwKICAgICAgICAgICAgIlgtVmVyc2lvbiI6ICAgICAiMjAyMi0wMS0wMSIsCiAgICAgICAgfQoKICAgIGFzeW5jIGRlZiBnZXQoc2VsZiwgdXJsOiBzdHIsICoqa3dhcmdzKSAtPiBodHRweC5SZXNwb25zZToKICAgICAgICBjbGllbnQgPSBhd2FpdCBzZWxmLl9lbnN1cmVfY2xpZW50KCkKICAgICAgICBsYXN0OiBodHRweC5SZXNwb25zZSB8IE5vbmUgPSBOb25lCiAgICAgICAgZm9yIGF0dGVtcHQgaW4gcmFuZ2UoMyk6CiAgICAgICAgICAgIHRyeToKICAgICAgICAgICAgICAgIHIgPSBhd2FpdCBjbGllbnQuZ2V0KHVybCwgaGVhZGVycz1hd2FpdCBzZWxmLl9oZWFkZXJzKCksICoqa3dhcmdzKQogICAgICAgICAgICBleGNlcHQgaHR0cHguVHJhbnNwb3J0RXJyb3I6CiAgICAgICAgICAgICAgICBpZiBhdHRlbXB0ID09IDI6CiAgICAgICAgICAgICAgICAgICAgcmFpc2UKICAgICAgICAgICAgICAgIGF3YWl0IGFzeW5jaW8uc2xlZXAoMSArIDIgKiBhdHRlbXB0KQogICAgICAgICAgICAgICAgY29udGludWUKICAgICAgICAgICAgdHJhbnNpZW50ID0gKAogICAgICAgICAgICAgICAgci5zdGF0dXNfY29kZSBpbiAoNDI5LCA1MDAsIDUwMiwgNTAzLCA1MDQpCiAgICAgICAgICAgICAgICBvciAoci5zdGF0dXNfY29kZSA9PSAyMDAgYW5kIG5vdCByLmNvbnRlbnQpCiAgICAgICAgICAgICkKICAgICAgICAgICAgaWYgbm90IHRyYW5zaWVudDoKICAgICAgICAgICAgICAgIHJldHVybiByCiAgICAgICAgICAgIGxhc3QgPSByCiAgICAgICAgICAgIGlmIGF0dGVtcHQgPCAyOgogICAgICAgICAgICAgICAgcmV0cnlfYWZ0ZXIgPSByLmhlYWRlcnMuZ2V0KCJSZXRyeS1BZnRlciIsICIiKQogICAgICAgICAgICAgICAgZGVsYXkgPSBmbG9hdChyZXRyeV9hZnRlcikgaWYgcmV0cnlfYWZ0ZXIuaXNkaWdpdCgpIGVsc2UgMSArIDIgKiBhdHRlbXB0CiAgICAgICAgICAgICAgICBhd2FpdCBhc3luY2lvLnNsZWVwKGRlbGF5KQogICAgICAgIHJldHVybiBsYXN0CgogICAgYXN5bmMgZGVmIHB1dChzZWxmLCB1cmw6IHN0ciwgKiprd2FyZ3MpIC0+IGh0dHB4LlJlc3BvbnNlOgogICAgICAgIGNsaWVudCA9IGF3YWl0IHNlbGYuX2Vuc3VyZV9jbGllbnQoKQogICAgICAgIHJldHVybiBhd2FpdCBjbGllbnQucHV0KHVybCwgaGVhZGVycz1hd2FpdCBzZWxmLl9oZWFkZXJzKCksICoqa3dhcmdzKQoKICAgIGFzeW5jIGRlZiBwb3N0KHNlbGYsIHVybDogc3RyLCAqKmt3YXJncykgLT4gaHR0cHguUmVzcG9uc2U6CiAgICAgICAgY2xpZW50ID0gYXdhaXQgc2VsZi5fZW5zdXJlX2NsaWVudCgpCiAgICAgICAgcmV0dXJuIGF3YWl0IGNsaWVudC5wb3N0KHVybCwgaGVhZGVycz1hd2FpdCBzZWxmLl9oZWFkZXJzKCksICoqa3dhcmdzKQoKICAgIGFzeW5jIGRlZiBjbG9zZShzZWxmKSAtPiBOb25lOgogICAgICAgIGlmIHNlbGYuX2NsaWVudCBhbmQgbm90IHNlbGYuX2NsaWVudC5pc19jbG9zZWQ6CiAgICAgICAgICAgIGF3YWl0IHNlbGYuX2NsaWVudC5hY2xvc2UoKQoKCl93ayA9IFdvcmtpdmFDbGllbnQoKQoKCiMg4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQCiMgSEVMUEVSUyBJTlRFUk5PUwojIOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkAoKZGVmIF9jb2xfbGV0dGVyKGlkeDogaW50KSAtPiBzdHI6CiAgICBpZiBpZHggPCAyNjoKICAgICAgICByZXR1cm4gY2hyKDY1ICsgaWR4KQogICAgcmV0dXJuIGNocig2NCArIGlkeCAvLyAyNikgKyBjaHIoNjUgKyBpZHggJSAyNikKCgpkZWYgX2N2KGNlbGw6IEFueSkgLT4gQW55OgogICAgaWYgaXNpbnN0YW5jZShjZWxsLCBkaWN0KToKICAgICAgICByZXR1cm4gY2VsbC5nZXQoImNhbGN1bGF0ZWRWYWx1ZSIpCiAgICByZXR1cm4gTm9uZQoKCmRlZiBfaXNfZm9ybXVsYShyb3c6IGxpc3QsIGNvbDogaW50KSAtPiBib29sOgogICAgaWYgY29sID49IGxlbihyb3cpOgogICAgICAgIHJldHVybiBGYWxzZQogICAgYyA9IHJvd1tjb2xdCiAgICByZXR1cm4gc3RyKGMuZ2V0KCJ2YWx1ZSIsICIiKSBpZiBpc2luc3RhbmNlKGMsIGRpY3QpIGVsc2UgIiIpLnN0YXJ0c3dpdGgoIj0iKQoKCmRlZiBfZXRpcXVldGFfZmlsYShyb3dfZTogbGlzdCkgLT4gc3RyOgogICAgIiIiUsOzdHVsbyBkZXNjcmlwdGl2byBkZSBsYSBmaWxhIChjb2x1bW5hIEIsIGNvbiBmYWxsYmFjayBhIEEgeSBDKS4iIiIKICAgIGZvciBqIGluICgxLCAwLCAyKToKICAgICAgICBpZiBqIDwgbGVuKHJvd19lKToKICAgICAgICAgICAgdCA9IF9jdihyb3dfZVtqXSkKICAgICAgICAgICAgaWYgaXNpbnN0YW5jZSh0LCBzdHIpIGFuZCB0LnN0cmlwKCk6CiAgICAgICAgICAgICAgICByZXR1cm4gdC5zdHJpcCgpCiAgICByZXR1cm4gIiIKCgpkZWYgX25vcm1fbGJsKHM6IHN0cikgLT4gc3RyOgogICAgcyA9IHVuaWNvZGVkYXRhLm5vcm1hbGl6ZSgiTkZLRCIsIHMgb3IgIiIpCiAgICBzID0gIiIuam9pbihjaCBmb3IgY2ggaW4gcyBpZiBub3QgdW5pY29kZWRhdGEuY29tYmluaW5nKGNoKSkKICAgIHJldHVybiByZS5zdWIociJccysiLCAiICIsIHMuc3RyaXAoKS5sb3dlcigpLnJzdHJpcCgiLjo7ICIpKQoKCl9TVE9QV09SRFNfRVRJUVVFVEEgPSB7CiAgICAiZGUiLCAiZGVsIiwgImxhIiwgImVsIiwgImxvcyIsICJsYXMiLCAieSIsICJvIiwgInUiLCAicG9yIiwgImVuIiwgImEiLAogICAgImFsIiwgImNvbiIsICJwYXJhIiwgInF1ZSIsICJzZSIsICJzdSIsICJzdXMiLCAidW4iLCAidW5hIiwKfQoKIyAibm8iLyJub24iLyJzaW4iIE5VTkNBIHNlIHRyYXRhbiBjb21vIGNvbmVjdG9yZXMgaWdub3JhYmxlczogaW52aWVydGVuIGVsCiMgc2VudGlkbyBkZSBsYSBldGlxdWV0YSAoIkNvcnJpZW50ZXMiIHZzICJObyBjb3JyaWVudGVzIiBzb24gb3B1ZXN0b3MsIG5vCiMgbGEgbWlzbWEgZmlsYSBjb24gb3RybyB0ZXh0bykuIERlYmVuIGNvaW5jaWRpciBleGFjdGFtZW50ZSBhIGFtYm9zIGxhZG9zLgpfTkVHQUNJT05FU19FVElRVUVUQSA9IHsibm8iLCAibm9uIiwgInNpbiJ9CgojIFBhcmVzIGRlIHBhbGFicmFzIG9wdWVzdGFzIENPTkZJUk1BREFTOiBzaSB1bmEgZXRpcXVldGEgdGllbmUgdW5hIHBhbGFicmEKIyBkZSB1biBwYXIgeSBsYSBvdHJhIGV0aXF1ZXRhIHRpZW5lIHN1IG9wdWVzdG8sIE5VTkNBIHNlIGNvbnNpZGVyYW4gbGEKIyBtaXNtYSBmaWxhLCBzaW4gaW1wb3J0YXIgY3XDoW50YXMgb3RyYXMgcGFsYWJyYXMgY29tcGFydGFuLiBOZWNlc2FyaW8KIyBwb3JxdWUgIkltcG9ydGVzLi4uIGRlIGxhcmdvIHBsYXpvIiB5ICIuLi5kZSBjb3J0byBwbGF6byIgY29tcGFydGVuIGVsCiMgODAlIGRlIHN1cyBwYWxhYnJhcyAoY2FsemFiYW4gY29uIGVsIHVtYnJhbCBwZW5zYWRvIHBhcmEgcmVvcmRlbmFtaWVudG9zCiMgY29tbyBlbCBkZSAiRGV0ZXJpb3JvLi4uIiksIHBlcm8gc29uIGzDrW5lYXMgb3B1ZXN0YXMuCl9BTlRPTklNT1NfRVRJUVVFVEEgPSBbCiAgICB7ImxhcmdvIiwgImNvcnRvIn0sCiAgICB7ImNvYnJhciIsICJwYWdhciJ9LAogICAgeyJhY3Rpdm8iLCAiYWN0aXZvcyIsICJwYXNpdm8iLCAicGFzaXZvcyJ9LAogICAgeyJpbmdyZXNvIiwgImluZ3Jlc29zIiwgImdhc3RvIiwgImdhc3RvcyJ9LApdCgojIFNpbsOzbmltb3MgY29ub2NpZG9zIHkgVkVSSUZJQ0FET1MgZW50cmUgcGxhbnRpbGxhcyBkZSBkaXN0aW50b3MgcGVyw61vZG9zCiMgKGVqLiAiQ29zdG8gZGUgYWRtaW5pc3RyYWNpw7NuIiBwYXPDsyBhIGxsYW1hcnNlICJHYXN0byBkZSBhZG1pbmlzdHJhY2nDs24iKS4KIyBFcyB1bmEgbGlzdGEgYmxhbmNhIGEgcHJvcMOzc2l0bzogc29sbyBzZSBhZ3JlZ2FuIHBhcmVzIGNvbmZpcm1hZG9zLiBDb24KIyBlc3RvIHNlIGV2aXRhIGFkaXZpbmFyIHBvciBwb3JjZW50YWplIGRlIHBhbGFicmFzIGVuIGNvbcO6biwgcXVlIHB1ZWRlCiMgY29uZnVuZGlyIGNvbmNlcHRvcyBvcHVlc3RvcyBjb24gcG9jYXMgcGFsYWJyYXMgKGVqLiAiY3VlbnRhcyBwb3IgY29icmFyIgojIHZzICJjdWVudGFzIHBvciBwYWdhciIgY29tcGFydGVuIG3DoXMgcGFsYWJyYXMgcXVlICJjb3N0byIvImdhc3RvIiBwZXJvCiMgc2lnbmlmaWNhbiBsbyBjb250cmFyaW8pLgpfU0lOT05JTU9TX0VUSVFVRVRBID0gewogICAgImNvc3RvIjogImdhc3RvIiwKICAgICJyZWVtYm9sc29zIjogInBhZ29zIiwKfQoKIyBJZ3VhbCBxdWUgX1NJTk9OSU1PU19FVElRVUVUQSBwZXJvIGEgbml2ZWwgZGUgRlJBU0UgY29tcGxldGE6IHBhcmEgY2FtYmlvcwojIGRlIG5vbWJyZSBxdWUgbm8gc29uIHVuYSBzb2xhIHBhbGFicmEgZGlzdGludGEsIHNpbm8gdW5hIHJlZGFjY2nDs24KIyBkaXN0aW50YSBwYXJhIGVsIG1pc21vIGNvbmNlcHRvIChlai4gbm90YSAxMTE6ICJ0ZXNvcmVyw61hIGNlbnRyYWxpemFkYSIKIyBwYXPDsyBhIGxsYW1hcnNlICJjdWVudGEgY29ycmllbnRlIG1lcmNhbnRpbCIg4oCUIGNhc2kgbm8gY29tcGFydGVuCiMgcGFsYWJyYXMsIGFzw60gcXVlIGxhIGNvbXBhcmFjacOzbiBwb3IgcGFsYWJyYXMgbm8gYWxjYW56YSkuIFNlIHJlZW1wbGF6YQojIEFOVEVTIGRlIHBhcnRpciBlbiBwYWxhYnJhcywgYXPDrSBxdWUgc29sbyBzZSBhZ3JlZ2FuIHBhcmVzIENPTkZJUk1BRE9TLgpfRlJBU0VTX1NJTk9OSU1BUyA9IFsKICAgICgiY3VlbnRhIGNvcnJpZW50ZSBtZXJjYW50aWwiLCAidGVzb3JlcmlhIGNlbnRyYWxpemFkYSIpLAogICAgKCJiZW5lZmljaW8gKGdhc3RvKSIsICJnYXN0byIpLApdCgoKZGVmIF9hcGxpY2FyX2ZyYXNlc19zaW5vbmltYXMobGJsOiBzdHIpIC0+IHN0cjoKICAgIGZvciB2YXJpYW50ZSwgY2Fub25pY2EgaW4gX0ZSQVNFU19TSU5PTklNQVM6CiAgICAgICAgbGJsID0gbGJsLnJlcGxhY2UodmFyaWFudGUsIGNhbm9uaWNhKQogICAgcmV0dXJuIGxibAoKCiMgQ29sZXRhcyBkZXNjcmlwdGl2YXMgcXVlIGEgdmVjZXMgc2UgYWdyZWdhbi9xdWl0YW4gZW50cmUgcGxhbnRpbGxhcyBzaW4KIyBjYW1iaWFyIGVsIGNvbmNlcHRvIGRlIGxhIGZpbGEgKGVqLiAiT3Ryb3MgaW5ncmVzb3MuIiBwYXPDsyBhIGxsYW1hcnNlCiMgIk90cm9zIGluZ3Jlc29zLCBwb3IgZnVuY2nDs24uIikuIFNlIHF1aXRhbiBBTlRFUyBkZSBjb21wYXJhciwgdGFudG8gc2kKIyBlc3TDoW4gY29tbyBzaSBubyDigJQgYXPDrSAiT3Ryb3MgaW5ncmVzb3MiIHkgIk90cm9zIGluZ3Jlc29zLCBwb3IgZnVuY2nDs24iCiMgcXVlZGFuIGlkw6ludGljYXMuIExpc3RhIGJsYW5jYSBhIHByb3DDs3NpdG8sIGlndWFsIHF1ZSBsb3Mgc2luw7NuaW1vcy4KX0NPTEVUQVNfSUdOT1JBQkxFUyA9IFsKICAgICJwb3IgZnVuY2lvbiIsCl0KCgpkZWYgX3F1aXRhcl9jb2xldGFzX2lnbm9yYWJsZXMobGJsOiBzdHIpIC0+IHN0cjoKICAgIGZvciBjb2xldGEgaW4gX0NPTEVUQVNfSUdOT1JBQkxFUzoKICAgICAgICBsYmwgPSByZS5zdWIocmYiXHMqLD9ccyp7cmUuZXNjYXBlKGNvbGV0YSl9XHMqJCIsICIiLCBsYmwpCiAgICByZXR1cm4gbGJsCgoKZGVmIF9wYWxhYnJhc19zaWduaWZpY2F0aXZhcyhsYmw6IHN0cikgLT4gc2V0W3N0cl06CiAgICAiIiJQYWxhYnJhcyBkZSB1bmEgZXRpcXVldGEgeWEgbm9ybWFsaXphZGEsIHNpbiBjb25lY3RvcmVzLCBzw61tYm9sb3MKICAgIHN1ZWx0b3MgKCgqKSwgZ3Vpb25lcywgZXRjLikgbmkgcGFsYWJyYXMgY29ydGFzIOKAlCBwYXJhIGNvbXBhcmFyIHBvcgogICAgY29udGVuaWRvIGVuIHZleiBkZSBwb3IgdGV4dG8gZXhhY3RvLiIiIgogICAgbGJsID0gX3F1aXRhcl9jb2xldGFzX2lnbm9yYWJsZXMoX2FwbGljYXJfZnJhc2VzX3Npbm9uaW1hcyhsYmwpKQogICAgcGFsYWJyYXMgPSAocmUuc3ViKHIiW15hLXrDsTAtOV0rIiwgIiIsIHcpIGZvciB3IGluIGxibC5zcGxpdCgpKQogICAgcmV0dXJuIHt3IGZvciB3IGluIHBhbGFicmFzIGlmIGxlbih3KSA+PSAzIGFuZCB3IG5vdCBpbiBfU1RPUFdPUkRTX0VUSVFVRVRBfQoKCmRlZiBfcGFsYWJyYXNfY2Fub25pY2FzKGxibDogc3RyKSAtPiBzZXRbc3RyXToKICAgICIiIlBhbGFicmFzIHNpZ25pZmljYXRpdmFzIG5vcm1hbGl6YWRhcyBhIHN1IGZvcm1hIGNhbsOzbmljYSBzZWfDum4KICAgIF9TSU5PTklNT1NfRVRJUVVFVEEgKGVqLiAnY29zdG8nIHkgJ2dhc3RvJyBxdWVkYW4gY29tbyBsYSBtaXNtYQogICAgcGFsYWJyYSkuIiIiCiAgICByZXR1cm4ge19TSU5PTklNT1NfRVRJUVVFVEEuZ2V0KHcsIHcpIGZvciB3IGluIF9wYWxhYnJhc19zaWduaWZpY2F0aXZhcyhsYmwpfQoKCmRlZiBfZXRpcXVldGFzX3NpbWlsYXJlcyhhOiBzdHIsIGI6IHN0cikgLT4gYm9vbDoKICAgICIiIlRydWUgc2kgZG9zIGV0aXF1ZXRhcyBkZXNjcmliZW4gbGEgbWlzbWEgZmlsYSBwZXNlIGEgdW4gY2FtYmlvIGRlCiAgICBwbGFudGlsbGEgZW50cmUgcGVyw61vZG9zLiBEb3MgbWVjYW5pc21vcywgZGVsaWJlcmFkYW1lbnRlIGVzdHJpY3RvczoKCiAgICAxKSBFdGlxdWV0YXMgQ09SVEFTIChwb2NhcyBwYWxhYnJhcyBzaWduaWZpY2F0aXZhcyk6IGRlYmVuIGNhbHphcgogICAgICAgRVhBQ1RPIHRyYXMgYXBsaWNhciBsYSBsaXN0YSBibGFuY2EgZGUgc2luw7NuaW1vcyB2ZXJpZmljYWRvcy4gTm8gc2UKICAgICAgIGFkaXZpbmEgcG9yIHBvcmNlbnRhamUg4oCUIGNvbiBwb2NhcyBwYWxhYnJhcyB1biBzb2xvIHTDqXJtaW5vCiAgICAgICBvcHVlc3RvIChjb2JyYXIvcGFnYXIsIGFjdGl2by9wYXNpdm8pIHB1ZWRlIHBhcmVjZXIgInBhcmVjaWRvIiBzaW4KICAgICAgIHNlcmxvLgogICAgMikgRXRpcXVldGFzIExBUkdBUyAobXVjaGFzIHBhbGFicmFzIHNpZ25pZmljYXRpdmFzKTogc2UgYWNlcHRhIHF1ZQogICAgICAgbGFzIG1pc21hcyBwYWxhYnJhcyBlc3TDqW4gZW4gb3RybyBvcmRlbiAoZWouIHVuYSByZWRhY2Npw7NuIGxlZ2FsCiAgICAgICByZW9yZGVuYWRhKSwgdG9sZXJhbmRvIHVuYSBkaWZlcmVuY2lhIG3DrW5pbWEg4oCUIGNvbiB0YW50YXMgcGFsYWJyYXMKICAgICAgIGVuIGNvbcO6biBsYSBwcm9iYWJpbGlkYWQgZGUgcXVlIHNlYW4gY29uY2VwdG9zIGRpc3RpbnRvcyBwb3IKICAgICAgIGNhc3VhbGlkYWQgZXMgcHLDoWN0aWNhbWVudGUgbnVsYS4KICAgICIiIgogICAgcGFsYWJyYXNfYSwgcGFsYWJyYXNfYiA9IHNldChhLnNwbGl0KCkpLCBzZXQoYi5zcGxpdCgpKQogICAgaWYgKHBhbGFicmFzX2EgJiBfTkVHQUNJT05FU19FVElRVUVUQSkgIT0gKHBhbGFicmFzX2IgJiBfTkVHQUNJT05FU19FVElRVUVUQSk6CiAgICAgICAgcmV0dXJuIEZhbHNlICAgIyB1bmEgdGllbmUgIm5vIi8ic2luIiB5IGxhIG90cmEgbm86IHNvbiBvcHVlc3RhcwoKICAgIGZvciBwYXIgaW4gX0FOVE9OSU1PU19FVElRVUVUQToKICAgICAgICBlbl9hLCBlbl9iID0gcGFsYWJyYXNfYSAmIHBhciwgcGFsYWJyYXNfYiAmIHBhcgogICAgICAgIGlmIGVuX2EgYW5kIGVuX2IgYW5kIGVuX2EgIT0gZW5fYjoKICAgICAgICAgICAgcmV0dXJuIEZhbHNlICAgIyB1bmEgdGllbmUgImxhcmdvIi8iY29icmFyIi8uLi4geSBsYSBvdHJhIHN1IG9wdWVzdG8KCiAgICBwYSwgcGIgPSBfcGFsYWJyYXNfY2Fub25pY2FzKGEpLCBfcGFsYWJyYXNfY2Fub25pY2FzKGIpCiAgICBpZiBub3QgcGEgb3Igbm90IHBiOgogICAgICAgIHJldHVybiBGYWxzZQogICAgaWYgcGEgPT0gcGI6CiAgICAgICAgcmV0dXJuIFRydWUKCiAgICAjIFNvbG8gcGFyYSBldGlxdWV0YXMgbGFyZ2FzOiB0b2xlcmFyIHBhbGFicmFzIHN1ZWx0YXMgcXVlIGNhbWJpYXJvbgogICAgIyAoZWouICJkZXRlcm1pbmFkbyIgdnMgImRldGVybWluYWRhcyIpIHNpIGNhc2kgdG9kbyBlbCByZXN0byBjYWx6YS4KICAgIGlmIGxlbihwYSkgPj0gNSBhbmQgbGVuKHBiKSA+PSA1OgogICAgICAgIGludGVyc2VjY2lvbiA9IGxlbihwYSAmIHBiKQogICAgICAgIHJldHVybiBpbnRlcnNlY2Npb24gLyBtYXgobGVuKHBhKSwgbGVuKHBiKSkgPj0gMC44CiAgICByZXR1cm4gRmFsc2UKCgpfUkVfUFJFRklKT19IT0pBID0gcmUuY29tcGlsZShyIl5ccyooW0EtWmEtesORw7EwLTldezEsNH0pXHMqXC5ccyotP1xzKlxTIikKCgpkZWYgX3ByZWZpam9faG9qYShub21icmU6IHN0cikgLT4gc3RyOgogICAgIiIiJzIzLi0gU2VnbWVudG9zIGRlIHZlbnRhcycg4oaSICcyMyciIiIKICAgIG0gPSBfUkVfUFJFRklKT19IT0pBLm1hdGNoKG5vbWJyZSBvciAiIikKICAgIHJldHVybiBtLmdyb3VwKDEpLnVwcGVyKCkgaWYgbSBlbHNlICIiCgoKIyBIb2phcyBhcm1hZGFzIGNvbW8gRE9TIFRBQkxBUyBDT01QTEVUQVMgQVBJTEFEQVMgZGUgYcOxb3MgZGlzdGludG9zOgojIGFycmliYSBlbCBwZXLDrW9kbyBhY3R1YWwgKDIwMjYpIHkgYWJham8gbG9zIG1pc21vcyBwZXLDrW9kb3MgZGVsIGHDsW8KIyBhbnRlcmlvciAoMjAyNSkuIEVuIGVzdGFzIG5vdGFzIGxhIHRhYmxhIGRlIGFiYWpvIGRlbCBkZXN0aW5vIGNvcnJlc3BvbmRlCiMgYSBsYSB0YWJsYSBkZSBBUlJJQkEgZGVsIGFyY2hpdm8gZnVlbnRlIChxdWUgZXMgZWwgY29tcGFyYXRpdm8gZGVsIGHDsW8KIyBhbnRlcmlvciksIHkgbGEgdGFibGEgZGUgYXJyaWJhIGRlbCBkZXN0aW5vIG5vIHRpZW5lIGNvbnRyYSBxdcOpIHZhbGlkYXJzZS4KSE9KQVNfVEFCTEFfQU5VQUxfQVBJTEFEQSA9IHsiMjMifQoKCmRlZiBfZmlsYV9rd19lbl9jb2woY2VsbHM6IGxpc3RbbGlzdF0sIGt3OiBzdHIsIGNvbDogaW50KSAtPiBpbnQgfCBOb25lOgogICAgIiIiw41uZGljZSBkZSBsYSBmaWxhIGRvbmRlIGFwYXJlY2Uga3cgZGVudHJvIGRlIGxhIGNvbHVtbmEgY29sLiIiIgogICAgaWYgbm90IGt3IG9yIGNvbCBpcyBOb25lOgogICAgICAgIHJldHVybiBOb25lCiAgICBmb3IgcmksIHJvdyBpbiBlbnVtZXJhdGUoY2VsbHMpOgogICAgICAgIGlmIGNvbCA8IGxlbihyb3cpIGFuZCBpc2luc3RhbmNlKHJvd1tjb2xdLCBkaWN0KToKICAgICAgICAgICAgZm9yIHZrIGluICgiY2FsY3VsYXRlZFZhbHVlIiwgInZhbHVlIik6CiAgICAgICAgICAgICAgICBpZiBrdyBpbiBzdHIocm93W2NvbF0uZ2V0KHZrLCAiIikgb3IgIiIpLmxvd2VyKCk6CiAgICAgICAgICAgICAgICAgICAgcmV0dXJuIHJpCiAgICByZXR1cm4gTm9uZQoKCmFzeW5jIGRlZiBfZ2V0X3NoZWV0cyhzc19pZDogc3RyKSAtPiBkaWN0W3N0ciwgc3RyXToKICAgIHJlc3VsdDogZGljdFtzdHIsIHN0cl0gPSB7fQogICAgdXJsID0gZiJ7UExBVEZPUk1fVVJMfS9zcHJlYWRzaGVldHMve3NzX2lkfS9zaGVldHMiCiAgICB3aGlsZSB1cmw6CiAgICAgICAgciAgICA9IGF3YWl0IF93ay5nZXQodXJsKQogICAgICAgIGRhdGEgPSByLmpzb24oKQogICAgICAgIGZvciBzIGluIGRhdGEuZ2V0KCJkYXRhIiwgW10pOgogICAgICAgICAgICByZXN1bHRbc1sibmFtZSJdXSA9IHNbImlkIl0KICAgICAgICB1cmwgPSBkYXRhLmdldCgiQG5leHRMaW5rIikKICAgIHJldHVybiByZXN1bHQKCgphc3luYyBkZWYgX3JlYWRfc2hlZXRfY2VsbHMoc3NfaWQ6IHN0ciwgc2hlZXRfaWQ6IHN0cikgLT4gbGlzdFtsaXN0XToKICAgIHVybCA9ICgKICAgICAgICBmIntQTEFURk9STV9VUkx9L3NwcmVhZHNoZWV0cy97c3NfaWR9L3NoZWV0cy97c2hlZXRfaWR9IgogICAgICAgICIvc2hlZXRkYXRhPyRmaWVsZHM9Y2VsbHMuY2FsY3VsYXRlZFZhbHVlLGNlbGxzLnZhbHVlJiRtYXhjZWxsc3BlcnBhZ2U9NTAwMDAiCiAgICApCiAgICByID0gYXdhaXQgX3drLmdldCh1cmwpCiAgICBpZiByLnN0YXR1c19jb2RlICE9IDIwMDoKICAgICAgICByZXR1cm4gW10KICAgIHJldHVybiByLmpzb24oKS5nZXQoImRhdGEiLCB7fSkuZ2V0KCJjZWxscyIsIFtdKQoKCmFzeW5jIGRlZiBfcG9sbF9vcGVyYXRpb24obG9jYXRpb246IHN0ciwgbWF4X2F0dGVtcHRzOiBpbnQgPSA0MCkgLT4gYm9vbDoKICAgIGlmIG5vdCBsb2NhdGlvbi5zdGFydHN3aXRoKCJodHRwIik6CiAgICAgICAgbG9jYXRpb24gPSAiaHR0cHM6Ly9hcGkuYXBwLndkZXNrLmNvbSIgKyBsb2NhdGlvbgogICAgZm9yIF8gaW4gcmFuZ2UobWF4X2F0dGVtcHRzKToKICAgICAgICBhd2FpdCBhc3luY2lvLnNsZWVwKDMpCiAgICAgICAgdHJ5OgogICAgICAgICAgICBib2R5ID0gKGF3YWl0IF93ay5nZXQobG9jYXRpb24pKS5qc29uKCkKICAgICAgICAgICAgc3QgICA9IGJvZHkuZ2V0KCJzdGF0dXMiLCBib2R5LmdldCgiZGF0YSIsIHt9KS5nZXQoInN0YXR1cyIsICIiKSkKICAgICAgICAgICAgaWYgc3QgPT0gImNvbXBsZXRlZCI6CiAgICAgICAgICAgICAgICByZXR1cm4gVHJ1ZQogICAgICAgICAgICBpZiBzdCBpbiAoImZhaWxlZCIsICJlcnJvciIpOgogICAgICAgICAgICAgICAgcmV0dXJuIEZhbHNlCiAgICAgICAgZXhjZXB0IEV4Y2VwdGlvbjoKICAgICAgICAgICAgcGFzcwogICAgcmV0dXJuIEZhbHNlCgoKYXN5bmMgZGVmIF92ZXJpZnlfd3JpdGUoc3NfaWQ6IHN0ciwgc2lkOiBzdHIsIGNvbF9pZHg6IGludCwgc3RhcnRfcm93OiBpbnQsCiAgICAgICAgICAgICAgICAgICAgICAgICB2YWx1ZXM6IGxpc3QsIGNsOiBzdHIpIC0+IGxpc3Rbc3RyXToKICAgICIiIlJlbGVlIGxhIGhvamEgY29tcGxldGEgKG1pc21vIGNhbWlubyB5YSBwcm9iYWRvIHF1ZSB1c2EgZWwgcmVzdG8gZGUKICAgIGxhIGFwcCBwYXJhIGxlZXIgY2VsZGFzOiBfcmVhZF9zaGVldF9jZWxscyArIGNhbGN1bGF0ZWRWYWx1ZSkgeSBkZXZ1ZWx2ZQogICAgbGFzIGNlbGRhcyBjdXlvIHZhbG9yIE5PIGNvaW5jaWRlIGNvbiBsbyBxdWUgc2UgaW50ZW50w7MgZXNjcmliaXIKICAgIChpbmRpY2lvIGRlIGNlbGRhIGJsb3F1ZWFkYS9wcm90ZWdpZGEgcXVlIFdvcmtpdmEgaWdub3LDsyBlbiBzaWxlbmNpbwogICAgYWwgY29tcGxldGFyIGVsIFBVVCkuCgogICAgUmVpbnRlbnRhIGNvbiBlc3BlcmEgcG9ycXVlIFdvcmtpdmEgcHVlZGUgdGFyZGFyIGVuIHByb3BhZ2FyIGxhCiAgICBlc2NyaXR1cmEgYSBsYSBsZWN0dXJhIChjb25zaXN0ZW5jaWEgZXZlbnR1YWwpLgogICAgIiIiCiAgICBtaXNtYXRjaGVzOiBsaXN0W3N0cl0gPSBbXQogICAgZm9yIGludGVudG8gaW4gcmFuZ2UoMyk6CiAgICAgICAgaWYgaW50ZW50byA+IDA6CiAgICAgICAgICAgIGF3YWl0IGFzeW5jaW8uc2xlZXAoMiAqIGludGVudG8pCiAgICAgICAgdHJ5OgogICAgICAgICAgICBjZWxscyA9IGF3YWl0IF9yZWFkX3NoZWV0X2NlbGxzKHNzX2lkLCBzaWQpCiAgICAgICAgZXhjZXB0IEV4Y2VwdGlvbjoKICAgICAgICAgICAgcmV0dXJuIFtdCgogICAgICAgIG1pc21hdGNoZXMgPSBbXQogICAgICAgIGZvciBpLCB3YW50IGluIGVudW1lcmF0ZSh2YWx1ZXMpOgogICAgICAgICAgICBpZiB3YW50IGlzIE5vbmU6CiAgICAgICAgICAgICAgICBjb250aW51ZQogICAgICAgICAgICByb3dfaSA9IHN0YXJ0X3JvdyArIGkKICAgICAgICAgICAgcm93ICAgPSBjZWxsc1tyb3dfaV0gaWYgcm93X2kgPCBsZW4oY2VsbHMpIGVsc2UgW10KICAgICAgICAgICAgZ290ICAgPSBfY3Yocm93W2NvbF9pZHhdKSBpZiBjb2xfaWR4IDwgbGVuKHJvdykgZWxzZSBOb25lCiAgICAgICAgICAgIGdvdF9udW0gPSBnb3QgaWYgaXNpbnN0YW5jZShnb3QsIChpbnQsIGZsb2F0KSkgZWxzZSBOb25lCiAgICAgICAgICAgIGlmIGdvdF9udW0gaXMgTm9uZSBvciBhYnMoZ290X251bSAtIGZsb2F0KHdhbnQpKSA+IDAuNToKICAgICAgICAgICAgICAgIG1pc21hdGNoZXMuYXBwZW5kKGYie2NsfXtzdGFydF9yb3cgKyBpICsgMX0iKQoKICAgICAgICBpZiBub3QgbWlzbWF0Y2hlczoKICAgICAgICAgICAgcmV0dXJuIFtdCiAgICByZXR1cm4gbWlzbWF0Y2hlcwoKCmFzeW5jIGRlZiBfd3JpdGVfY29sdW1uKHNzX2lkOiBzdHIsIHNpZDogc3RyLCBjb2xfaWR4OiBpbnQsCiAgICAgICAgICAgICAgICAgICAgICAgICB2YWx1ZXM6IGxpc3QsIHN0YXJ0X3JvdzogaW50ID0gMCkgLT4gdHVwbGVbYm9vbCwgc3RyIHwgTm9uZV06CiAgICAiIiJFc2NyaWJlIHVuYSBjb2x1bW5hLiBSZXRvcm5hIChvaywgbW90aXZvX2Vycm9yKSDigJQgbW90aXZvX2Vycm9yIGVzIE5vbmUgc2kgb2suIiIiCiAgICBjbCA9IF9jb2xfbGV0dGVyKGNvbF9pZHgpCiAgICByMSA9IHN0YXJ0X3JvdyArIDEKICAgIHIyID0gcjEgKyBsZW4odmFsdWVzKSAtIDEKICAgIHJuZyA9IGYie2NsfXtyMX06e2NsfXtyMn0iCiAgICBycCA9IGF3YWl0IF93ay5wdXQoCiAgICAgICAgZiJ7UExBVEZPUk1fVVJMfS9zcHJlYWRzaGVldHMve3NzX2lkfS9zaGVldHMve3NpZH0vdmFsdWVzL3tybmd9IiwKICAgICAgICBqc29uPXsidmFsdWVzIjogW1t2XSBmb3IgdiBpbiB2YWx1ZXNdfSwKICAgICkKICAgIGlmIHJwLnN0YXR1c19jb2RlID09IDIwMjoKICAgICAgICBvayA9IGF3YWl0IF9wb2xsX29wZXJhdGlvbihycC5oZWFkZXJzLmdldCgiTG9jYXRpb24iLCAiIikpCiAgICAgICAgaWYgbm90IG9rOgogICAgICAgICAgICByZXR1cm4gRmFsc2UsIGYiTGEgb3BlcmFjacOzbiBkZSBlc2NyaXR1cmEgZW4ge3JuZ30gZmFsbMOzICh0aW1lb3V0IHUgb3BlcmFjacOzbiBjYW5jZWxhZGEpLiIKCiAgICAgICAgIyBXb3JraXZhIHB1ZWRlIHJlc3BvbmRlciAiY29tcGxldGVkIiBlIGlnbm9yYXIgZW4gc2lsZW5jaW8gbGFzCiAgICAgICAgIyBjZWxkYXMgYmxvcXVlYWRhcy9wcm90ZWdpZGFzIGRlbnRybyBkZWwgcmFuZ28g4oCUIHNlIHZlcmlmaWNhIHJlbGV5ZW5kby4KICAgICAgICBtaXNtYXRjaGVzID0gYXdhaXQgX3ZlcmlmeV93cml0ZShzc19pZCwgc2lkLCBjb2xfaWR4LCBzdGFydF9yb3csIHZhbHVlcywgY2wpCiAgICAgICAgaWYgbWlzbWF0Y2hlczoKICAgICAgICAgICAgbW90aXZvID0gKAogICAgICAgICAgICAgICAgZiJDZWxkYShzKSB7JywgJy5qb2luKG1pc21hdGNoZXNbOjEwXSl9IG5vIHNlIGFjdHVhbGl6YXJvbiB0cmFzIGVzY3JpYmlyICIKICAgICAgICAgICAgICAgIGYiKHByb2JhYmxlbWVudGUgQkxPUVVFQURBKFMpL1BST1RFR0lEQShTKSBlbiBXb3JraXZhKSIKICAgICAgICAgICAgKQogICAgICAgICAgICByZXR1cm4gRmFsc2UsIG1vdGl2bwogICAgICAgIHJldHVybiBUcnVlLCBOb25lCgogICAgdHJ5OgogICAgICAgIGJvZHkgPSBycC5qc29uKCkKICAgICAgICBtc2cgID0gYm9keS5nZXQoIm1lc3NhZ2UiKSBvciBib2R5LmdldCgiZXJyb3IiKSBvciBzdHIoYm9keSkKICAgIGV4Y2VwdCBFeGNlcHRpb246CiAgICAgICAgbXNnID0gcnAudGV4dFs6MzAwXQoKICAgIGlmIHJwLnN0YXR1c19jb2RlIGluICg0MDAsIDQwMywgNDA5LCA0MjIpIGFuZCByZS5zZWFyY2gocidsb2NrfHByb3RlY3R8YmxvcXVlJywgbXNnLCByZS5JKToKICAgICAgICBtb3Rpdm8gPSBmIkNlbGRhKHMpIHtybmd9IEJMT1FVRUFEQShTKS9QUk9URUdJREEoUykgZW4gV29ya2l2YToge21zZ1s6MjAwXX0iCiAgICBlbHNlOgogICAgICAgIG1vdGl2byA9IGYiRXJyb3IgSFRUUCB7cnAuc3RhdHVzX2NvZGV9IGFsIGVzY3JpYmlyIHtybmd9OiB7bXNnWzoyMDBdfSIKICAgIHJldHVybiBGYWxzZSwgbW90aXZvCgoKYXN5bmMgZGVmIF9sb2FkX2FsbF9maWxlcygpIC0+IGRpY3Rbc3RyLCBzdHJdOgogICAgcmVzdWx0OiBkaWN0W3N0ciwgc3RyXSA9IHt9CiAgICB1cmwgPSBmIntQTEFURk9STV9VUkx9L2ZpbGVzP3dvcmtzcGFjZUlkPXtXT1JLU1BBQ0VfSUR9JmxpbWl0PTEwMCIKICAgIHdoaWxlIHVybDoKICAgICAgICByICAgID0gYXdhaXQgX3drLmdldCh1cmwpCiAgICAgICAgZGF0YSA9IHIuanNvbigpCiAgICAgICAgZm9yIGYgaW4gZGF0YS5nZXQoImRhdGEiLCBbXSk6CiAgICAgICAgICAgIHJlc3VsdFtmWyJuYW1lIl1dID0gZlsiaWQiXQogICAgICAgIHVybCA9IGRhdGEuZ2V0KCJAbmV4dExpbmsiKQogICAgcmV0dXJuIHJlc3VsdAoKCmRlZiBfaGFuZGxlX2Vycm9yKGU6IEV4Y2VwdGlvbikgLT4gc3RyOgogICAgaWYgaXNpbnN0YW5jZShlLCBodHRweC5IVFRQU3RhdHVzRXJyb3IpOgogICAgICAgIGNvZGUgPSBlLnJlc3BvbnNlLnN0YXR1c19jb2RlCiAgICAgICAgaWYgY29kZSA9PSA0MDE6CiAgICAgICAgICAgIHJldHVybiAiRXJyb3I6IE5vIGF1dGVudGljYWRvLiBWZXJpZmljYSBDTElFTlRfSUQgeSBDTElFTlRfU0VDUkVUIGVuIC5lbnYiCiAgICAgICAgaWYgY29kZSA9PSA0MDM6CiAgICAgICAgICAgIHJldHVybiAiRXJyb3I6IFNpbiBwZXJtaXNvcyBwYXJhIGVzdGUgcmVjdXJzby4iCiAgICAgICAgaWYgY29kZSA9PSA0MDQ6CiAgICAgICAgICAgIHJldHVybiAiRXJyb3I6IFJlY3Vyc28gbm8gZW5jb250cmFkby4gVmVyaWZpY2EgZWwgSUQuIgogICAgICAgIGlmIGNvZGUgPT0gNDI5OgogICAgICAgICAgICByZXR1cm4gIkVycm9yOiBSYXRlIGxpbWl0IGFsY2FuemFkby4gRXNwZXJhIHVuIG1vbWVudG8uIgogICAgICAgIHJldHVybiBmIkVycm9yIEhUVFAge2NvZGV9OiB7ZS5yZXNwb25zZS50ZXh0WzoyMDBdfSIKICAgIGlmIGlzaW5zdGFuY2UoZSwgaHR0cHguVGltZW91dEV4Y2VwdGlvbik6CiAgICAgICAgcmV0dXJuICJFcnJvcjogVGltZW91dC4gTGEgb3BlcmFjacOzbiB0YXJkw7MgZGVtYXNpYWRvLiIKICAgIHJldHVybiBmIkVycm9yIGluZXNwZXJhZG86IHt0eXBlKGUpLl9fbmFtZV9ffToge2V9IgoKCiMg4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQCiMgU0VSVklET1IgTUNQCiMg4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQCgpAYXN5bmNjb250ZXh0bWFuYWdlcgphc3luYyBkZWYgbGlmZXNwYW4oc2VydmVyKTogICMgdHlwZTogaWdub3JlW3R5cGUtYXJnXQogICAgeWllbGQKICAgIGF3YWl0IF93ay5jbG9zZSgpCgoKbWNwID0gRmFzdE1DUCgid29ya2l2YV9tY3BfdjIiLCBsaWZlc3Bhbj1saWZlc3BhbikKCgojIOKUgOKUgOKUgCAxLiBMSVNUQVIgQVJDSElWT1Mg4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSACgpjbGFzcyBMaXN0RmlsZXNJbnB1dChCYXNlTW9kZWwpOgogICAgbW9kZWxfY29uZmlnID0gQ29uZmlnRGljdChzdHJfc3RyaXBfd2hpdGVzcGFjZT1UcnVlKQogICAgcGF0dGVybjogIE9wdGlvbmFsW3N0cl0gPSBGaWVsZChkZWZhdWx0PU5vbmUpCiAgICBsaW1pdDogICAgaW50ICAgICAgICAgICAgPSBGaWVsZChkZWZhdWx0PTUwLCBnZT0xLCBsZT01MDApCiAgICBvZmZzZXQ6ICAgaW50ICAgICAgICAgICAgPSBGaWVsZChkZWZhdWx0PTAsIGdlPTApCgoKQG1jcC50b29sKG5hbWU9IndvcmtpdmFfbGlzdF9maWxlcyIsCiAgICAgICAgICBhbm5vdGF0aW9ucz17InJlYWRPbmx5SGludCI6IFRydWUsICJkZXN0cnVjdGl2ZUhpbnQiOiBGYWxzZSwKICAgICAgICAgICAgICAgICAgICAgICAiaWRlbXBvdGVudEhpbnQiOiBUcnVlLCAib3BlbldvcmxkSGludCI6IFRydWV9KQphc3luYyBkZWYgd29ya2l2YV9saXN0X2ZpbGVzKHBhcmFtczogTGlzdEZpbGVzSW5wdXQpIC0+IHN0cjoKICAgICIiIkxpc3RhIGFyY2hpdm9zIGRlbCB3b3Jrc3BhY2UgZGUgV29ya2l2YS4iIiIKICAgIHRyeToKICAgICAgICBhbGxfZmlsZXMgPSBhd2FpdCBfbG9hZF9hbGxfZmlsZXMoKQogICAgICAgIGl0ZW1zID0gbGlzdChhbGxfZmlsZXMuaXRlbXMoKSkKICAgICAgICBpZiBwYXJhbXMucGF0dGVybjoKICAgICAgICAgICAgcnggICAgPSByZS5jb21waWxlKHBhcmFtcy5wYXR0ZXJuLCByZS5JR05PUkVDQVNFKQogICAgICAgICAgICBpdGVtcyA9IFsobiwgaSkgZm9yIG4sIGkgaW4gaXRlbXMgaWYgcnguc2VhcmNoKG4pXQogICAgICAgIHRvdGFsICAgID0gbGVuKGl0ZW1zKQogICAgICAgIHBhZ2UgICAgID0gaXRlbXNbcGFyYW1zLm9mZnNldDogcGFyYW1zLm9mZnNldCArIHBhcmFtcy5saW1pdF0KICAgICAgICBoYXNfbW9yZSA9IHRvdGFsID4gcGFyYW1zLm9mZnNldCArIGxlbihwYWdlKQogICAgICAgIHJldHVybiBqc29uLmR1bXBzKHsKICAgICAgICAgICAgInRvdGFsIjogdG90YWwsICJjb3VudCI6IGxlbihwYWdlKSwgIm9mZnNldCI6IHBhcmFtcy5vZmZzZXQsCiAgICAgICAgICAgICJoYXNfbW9yZSI6IGhhc19tb3JlLAogICAgICAgICAgICAibmV4dF9vZmZzZXQiOiBwYXJhbXMub2Zmc2V0ICsgbGVuKHBhZ2UpIGlmIGhhc19tb3JlIGVsc2UgTm9uZSwKICAgICAgICAgICAgImZpbGVzIjogW3sibmFtZSI6IG4sICJpZCI6IGl9IGZvciBuLCBpIGluIHBhZ2VdLAogICAgICAgIH0sIGluZGVudD0yLCBlbnN1cmVfYXNjaWk9RmFsc2UpCiAgICBleGNlcHQgRXhjZXB0aW9uIGFzIGU6CiAgICAgICAgcmV0dXJuIF9oYW5kbGVfZXJyb3IoZSkKCgojIOKUgOKUgOKUgCAyLiBMSVNUQVIgSE9KQVMg4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSACgpjbGFzcyBHZXRTaGVldHNJbnB1dChCYXNlTW9kZWwpOgogICAgbW9kZWxfY29uZmlnID0gQ29uZmlnRGljdChzdHJfc3RyaXBfd2hpdGVzcGFjZT1UcnVlKQogICAgc3ByZWFkc2hlZXRfaWQ6IHN0ciA9IEZpZWxkKC4uLikKCgpAbWNwLnRvb2wobmFtZT0id29ya2l2YV9nZXRfc2hlZXRzIiwKICAgICAgICAgIGFubm90YXRpb25zPXsicmVhZE9ubHlIaW50IjogVHJ1ZSwgImRlc3RydWN0aXZlSGludCI6IEZhbHNlLAogICAgICAgICAgICAgICAgICAgICAgICJpZGVtcG90ZW50SGludCI6IFRydWUsICJvcGVuV29ybGRIaW50IjogVHJ1ZX0pCmFzeW5jIGRlZiB3b3JraXZhX2dldF9zaGVldHMocGFyYW1zOiBHZXRTaGVldHNJbnB1dCkgLT4gc3RyOgogICAgIiIiTGlzdGEgdG9kYXMgbGFzIGhvamFzIGRlIHVuIHNwcmVhZHNoZWV0LiIiIgogICAgdHJ5OgogICAgICAgIHNoZWV0cyA9IGF3YWl0IF9nZXRfc2hlZXRzKHBhcmFtcy5zcHJlYWRzaGVldF9pZCkKICAgICAgICByZXR1cm4ganNvbi5kdW1wcyh7CiAgICAgICAgICAgICJzcHJlYWRzaGVldF9pZCI6IHBhcmFtcy5zcHJlYWRzaGVldF9pZCwKICAgICAgICAgICAgImNvdW50IjogbGVuKHNoZWV0cyksCiAgICAgICAgICAgICJzaGVldHMiOiBbeyJuYW1lIjogbiwgImlkIjogaX0gZm9yIG4sIGkgaW4gc2hlZXRzLml0ZW1zKCldLAogICAgICAgIH0sIGluZGVudD0yLCBlbnN1cmVfYXNjaWk9RmFsc2UpCiAgICBleGNlcHQgRXhjZXB0aW9uIGFzIGU6CiAgICAgICAgcmV0dXJuIF9oYW5kbGVfZXJyb3IoZSkKCgojIOKUgOKUgOKUgCAzLiBMRUVSIEhPSkEg4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSACgpjbGFzcyBSZWFkU2hlZXRJbnB1dChCYXNlTW9kZWwpOgogICAgbW9kZWxfY29uZmlnID0gQ29uZmlnRGljdChzdHJfc3RyaXBfd2hpdGVzcGFjZT1UcnVlKQogICAgc3ByZWFkc2hlZXRfaWQ6IHN0ciAgICAgID0gRmllbGQoLi4uKQogICAgc2hlZXRfbmFtZTogICAgIHN0ciAgICAgID0gRmllbGQoLi4uKQogICAgbWF4X3Jvd3M6ICAgICAgIGludCAgICAgID0gRmllbGQoZGVmYXVsdD0yMDAsIGdlPTEsIGxlPTIwMDApCiAgICBza2lwX2VtcHR5OiAgICAgYm9vbCAgICAgPSBGaWVsZChkZWZhdWx0PVRydWUpCiAgICBjb2xfc3RhcnQ6ICAgICAgaW50ICAgICAgPSBGaWVsZChkZWZhdWx0PTAsIGdlPTApCiAgICBjb2xfZW5kOiAgICAgICAgT3B0aW9uYWxbaW50XSA9IEZpZWxkKGRlZmF1bHQ9Tm9uZSkKCgpAbWNwLnRvb2wobmFtZT0id29ya2l2YV9yZWFkX3NoZWV0IiwKICAgICAgICAgIGFubm90YXRpb25zPXsicmVhZE9ubHlIaW50IjogVHJ1ZSwgImRlc3RydWN0aXZlSGludCI6IEZhbHNlLAogICAgICAgICAgICAgICAgICAgICAgICJpZGVtcG90ZW50SGludCI6IFRydWUsICJvcGVuV29ybGRIaW50IjogVHJ1ZX0pCmFzeW5jIGRlZiB3b3JraXZhX3JlYWRfc2hlZXQocGFyYW1zOiBSZWFkU2hlZXRJbnB1dCkgLT4gc3RyOgogICAgIiIiTGVlIGVsIGNvbnRlbmlkbyBkZSB1bmEgaG9qYSBkZSBXb3JraXZhLiIiIgogICAgdHJ5OgogICAgICAgIHNoZWV0cyA9IGF3YWl0IF9nZXRfc2hlZXRzKHBhcmFtcy5zcHJlYWRzaGVldF9pZCkKICAgICAgICBzaWQgICAgPSBzaGVldHMuZ2V0KHBhcmFtcy5zaGVldF9uYW1lKQogICAgICAgIGlmIG5vdCBzaWQ6CiAgICAgICAgICAgIGF2YWlsYWJsZSA9ICIsICIuam9pbihzaGVldHMua2V5cygpKQogICAgICAgICAgICByZXR1cm4gZiJFcnJvcjogSG9qYSAne3BhcmFtcy5zaGVldF9uYW1lfScgbm8gZW5jb250cmFkYS4gRGlzcG9uaWJsZXM6IHthdmFpbGFibGV9IgogICAgICAgIGNlbGxzID0gYXdhaXQgX3JlYWRfc2hlZXRfY2VsbHMocGFyYW1zLnNwcmVhZHNoZWV0X2lkLCBzaWQpCiAgICAgICAgcm93cyAgPSBbXQogICAgICAgIGZvciBpLCByb3cgaW4gZW51bWVyYXRlKGNlbGxzWzogcGFyYW1zLm1heF9yb3dzXSk6CiAgICAgICAgICAgIGNvbF9lbmQgPSBwYXJhbXMuY29sX2VuZCBpZiBwYXJhbXMuY29sX2VuZCBpcyBub3QgTm9uZSBlbHNlIGxlbihyb3cpCiAgICAgICAgICAgIHZhbHMgICAgPSBbX2N2KHJvd1tqXSkgaWYgaiA8IGxlbihyb3cpIGVsc2UgTm9uZQogICAgICAgICAgICAgICAgICAgICAgIGZvciBqIGluIHJhbmdlKHBhcmFtcy5jb2xfc3RhcnQsIGNvbF9lbmQpXQogICAgICAgICAgICBzdHJfdmFscyA9IFtzdHIodikgaWYgdiBpcyBub3QgTm9uZSBlbHNlICIiIGZvciB2IGluIHZhbHNdCiAgICAgICAgICAgIGlmIHBhcmFtcy5za2lwX2VtcHR5IGFuZCBub3QgYW55KHYgZm9yIHYgaW4gc3RyX3ZhbHMpOgogICAgICAgICAgICAgICAgY29udGludWUKICAgICAgICAgICAgcm93cy5hcHBlbmQoeyJyb3dfaWR4IjogaSwgInZhbHVlcyI6IHZhbHN9KQogICAgICAgIHJldHVybiBqc29uLmR1bXBzKHsKICAgICAgICAgICAgInNwcmVhZHNoZWV0X2lkIjogcGFyYW1zLnNwcmVhZHNoZWV0X2lkLAogICAgICAgICAgICAic2hlZXRfbmFtZSI6IHBhcmFtcy5zaGVldF9uYW1lLAogICAgICAgICAgICAidG90YWxfcm93cyI6IGxlbihjZWxscyksCiAgICAgICAgICAgICJyZXR1cm5lZF9yb3dzIjogbGVuKHJvd3MpLAogICAgICAgICAgICAiY29sX3N0YXJ0IjogcGFyYW1zLmNvbF9zdGFydCwKICAgICAgICAgICAgInJvd3MiOiByb3dzLAogICAgICAgIH0sIGluZGVudD0yLCBlbnN1cmVfYXNjaWk9RmFsc2UpCiAgICBleGNlcHQgRXhjZXB0aW9uIGFzIGU6CiAgICAgICAgcmV0dXJuIF9oYW5kbGVfZXJyb3IoZSkKCgojIOKUgOKUgOKUgCA0LiBFU0NSSUJJUiBDT0xVTU5BIOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgAoKY2xhc3MgV3JpdGVDb2x1bW5JbnB1dChCYXNlTW9kZWwpOgogICAgbW9kZWxfY29uZmlnID0gQ29uZmlnRGljdChzdHJfc3RyaXBfd2hpdGVzcGFjZT1UcnVlKQogICAgc3ByZWFkc2hlZXRfaWQ6IHN0ciAgICAgICA9IEZpZWxkKC4uLikKICAgIHNoZWV0X25hbWU6ICAgICBzdHIgICAgICAgPSBGaWVsZCguLi4pCiAgICBjb2xfaW5kZXg6ICAgICAgaW50ICAgICAgID0gRmllbGQoLi4uLCBnZT0wKQogICAgdmFsdWVzOiAgICAgICAgIGxpc3RbQW55XSA9IEZpZWxkKC4uLikKICAgIHN0YXJ0X3JvdzogICAgICBpbnQgICAgICAgPSBGaWVsZChkZWZhdWx0PTAsIGdlPTApCgoKQG1jcC50b29sKG5hbWU9IndvcmtpdmFfd3JpdGVfY29sdW1uIiwKICAgICAgICAgIGFubm90YXRpb25zPXsicmVhZE9ubHlIaW50IjogRmFsc2UsICJkZXN0cnVjdGl2ZUhpbnQiOiBGYWxzZSwKICAgICAgICAgICAgICAgICAgICAgICAiaWRlbXBvdGVudEhpbnQiOiBUcnVlLCAib3BlbldvcmxkSGludCI6IFRydWV9KQphc3luYyBkZWYgd29ya2l2YV93cml0ZV9jb2x1bW4ocGFyYW1zOiBXcml0ZUNvbHVtbklucHV0KSAtPiBzdHI6CiAgICAiIiJFc2NyaWJlIHVuYSBjb2x1bW5hIGRlIHZhbG9yZXMgZW4gdW5hIGhvamEgZGUgV29ya2l2YS4iIiIKICAgIHRyeToKICAgICAgICBzaGVldHMgPSBhd2FpdCBfZ2V0X3NoZWV0cyhwYXJhbXMuc3ByZWFkc2hlZXRfaWQpCiAgICAgICAgc2lkICAgID0gc2hlZXRzLmdldChwYXJhbXMuc2hlZXRfbmFtZSkKICAgICAgICBpZiBub3Qgc2lkOgogICAgICAgICAgICByZXR1cm4gZiJFcnJvcjogSG9qYSAne3BhcmFtcy5zaGVldF9uYW1lfScgbm8gZW5jb250cmFkYS4iCiAgICAgICAgb2ssIG1vdGl2byA9IGF3YWl0IF93cml0ZV9jb2x1bW4oCiAgICAgICAgICAgIHBhcmFtcy5zcHJlYWRzaGVldF9pZCwgc2lkLAogICAgICAgICAgICBwYXJhbXMuY29sX2luZGV4LCBwYXJhbXMudmFsdWVzLCBwYXJhbXMuc3RhcnRfcm93CiAgICAgICAgKQogICAgICAgIG5fd3JpdHRlbiA9IHN1bSgxIGZvciB2IGluIHBhcmFtcy52YWx1ZXMgaWYgdiBpcyBub3QgTm9uZSkKICAgICAgICByZXR1cm4ganNvbi5kdW1wcyh7CiAgICAgICAgICAgICJzdWNjZXNzIjogb2ssICJzaGVldF9uYW1lIjogcGFyYW1zLnNoZWV0X25hbWUsCiAgICAgICAgICAgICJjb2xfbGV0dGVyIjogX2NvbF9sZXR0ZXIocGFyYW1zLmNvbF9pbmRleCksCiAgICAgICAgICAgICJzdGFydF9yb3ciOiBwYXJhbXMuc3RhcnRfcm93ICsgMSwKICAgICAgICAgICAgImVuZF9yb3ciOiAgIHBhcmFtcy5zdGFydF9yb3cgKyBsZW4ocGFyYW1zLnZhbHVlcyksCiAgICAgICAgICAgICJuX3ZhbHVlcyI6ICBuX3dyaXR0ZW4sCiAgICAgICAgICAgICJlcnJvciI6ICAgICBtb3Rpdm8sCiAgICAgICAgfSwgaW5kZW50PTIsIGVuc3VyZV9hc2NpaT1GYWxzZSkKICAgIGV4Y2VwdCBFeGNlcHRpb24gYXMgZToKICAgICAgICByZXR1cm4gX2hhbmRsZV9lcnJvcihlKQoKCiMg4pSA4pSA4pSAIDUuIExJU1RBUiBUQUJMQVMgV0RBVEEg4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSACgpjbGFzcyBMaXN0VGFibGVzSW5wdXQoQmFzZU1vZGVsKToKICAgIG1vZGVsX2NvbmZpZyA9IENvbmZpZ0RpY3Qoc3RyX3N0cmlwX3doaXRlc3BhY2U9VHJ1ZSkKICAgIHBhdHRlcm46IE9wdGlvbmFsW3N0cl0gPSBGaWVsZChkZWZhdWx0PU5vbmUpCiAgICBsaW1pdDogICBpbnQgICAgICAgICAgICA9IEZpZWxkKGRlZmF1bHQ9NTAsIGdlPTEsIGxlPTIwMCkKICAgIG9mZnNldDogIGludCAgICAgICAgICAgID0gRmllbGQoZGVmYXVsdD0wLCBnZT0wKQoKCkBtY3AudG9vbChuYW1lPSJ3b3JraXZhX2xpc3RfdGFibGVzIiwKICAgICAgICAgIGFubm90YXRpb25zPXsicmVhZE9ubHlIaW50IjogVHJ1ZSwgImRlc3RydWN0aXZlSGludCI6IEZhbHNlLAogICAgICAgICAgICAgICAgICAgICAgICJpZGVtcG90ZW50SGludCI6IFRydWUsICJvcGVuV29ybGRIaW50IjogVHJ1ZX0pCmFzeW5jIGRlZiB3b3JraXZhX2xpc3RfdGFibGVzKHBhcmFtczogTGlzdFRhYmxlc0lucHV0KSAtPiBzdHI6CiAgICAiIiJMaXN0YSB0YWJsYXMgV0RhdGEuIiIiCiAgICB0cnk6CiAgICAgICAgdXJsICAgPSBmIntXREFUQV9VUkx9L3RhYmxlP3dvcmtzcGFjZUlkPXtXT1JLU1BBQ0VfSUR9IgogICAgICAgIHIgICAgID0gYXdhaXQgX3drLmdldCh1cmwpCiAgICAgICAgaXRlbXMgPSByLmpzb24oKS5nZXQoImRhdGEiLCBbXSkKICAgICAgICBpZiBwYXJhbXMucGF0dGVybjoKICAgICAgICAgICAgcnggICAgPSByZS5jb21waWxlKHBhcmFtcy5wYXR0ZXJuLCByZS5JR05PUkVDQVNFKQogICAgICAgICAgICBpdGVtcyA9IFt0IGZvciB0IGluIGl0ZW1zIGlmIHJ4LnNlYXJjaCh0LmdldCgibmFtZSIsICIiKSldCiAgICAgICAgdG90YWwgPSBsZW4oaXRlbXMpCiAgICAgICAgcGFnZSAgPSBpdGVtc1twYXJhbXMub2Zmc2V0OiBwYXJhbXMub2Zmc2V0ICsgcGFyYW1zLmxpbWl0XQogICAgICAgIHJldHVybiBqc29uLmR1bXBzKHsKICAgICAgICAgICAgInRvdGFsIjogdG90YWwsICJjb3VudCI6IGxlbihwYWdlKSwgIm9mZnNldCI6IHBhcmFtcy5vZmZzZXQsCiAgICAgICAgICAgICJoYXNfbW9yZSI6IHRvdGFsID4gcGFyYW1zLm9mZnNldCArIGxlbihwYWdlKSwKICAgICAgICAgICAgInRhYmxlcyI6IFt7ImlkIjogdC5nZXQoImlkIiksICJuYW1lIjogdC5nZXQoIm5hbWUiKSwKICAgICAgICAgICAgICAgICAgICAgICAgImRlc2MiOiB0LmdldCgiZGVzY3JpcHRpb24iLCAiIil9IGZvciB0IGluIHBhZ2VdLAogICAgICAgIH0sIGluZGVudD0yLCBlbnN1cmVfYXNjaWk9RmFsc2UpCiAgICBleGNlcHQgRXhjZXB0aW9uIGFzIGU6CiAgICAgICAgcmV0dXJuIF9oYW5kbGVfZXJyb3IoZSkKCgojIOKUgOKUgOKUgCA2LiBMSVNUQVIgUVVFUklFUyBXREFUQSDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIAKCmNsYXNzIExpc3RRdWVyaWVzSW5wdXQoQmFzZU1vZGVsKToKICAgIG1vZGVsX2NvbmZpZyA9IENvbmZpZ0RpY3Qoc3RyX3N0cmlwX3doaXRlc3BhY2U9VHJ1ZSkKICAgIHBhdHRlcm46IE9wdGlvbmFsW3N0cl0gPSBGaWVsZChkZWZhdWx0PU5vbmUpCiAgICBsaW1pdDogICBpbnQgICAgICAgICAgICA9IEZpZWxkKGRlZmF1bHQ9NTAsIGdlPTEsIGxlPTIwMCkKICAgIG9mZnNldDogIGludCAgICAgICAgICAgID0gRmllbGQoZGVmYXVsdD0wLCBnZT0wKQoKCkBtY3AudG9vbChuYW1lPSJ3b3JraXZhX2xpc3RfcXVlcmllcyIsCiAgICAgICAgICBhbm5vdGF0aW9ucz17InJlYWRPbmx5SGludCI6IFRydWUsICJkZXN0cnVjdGl2ZUhpbnQiOiBGYWxzZSwKICAgICAgICAgICAgICAgICAgICAgICAiaWRlbXBvdGVudEhpbnQiOiBUcnVlLCAib3BlbldvcmxkSGludCI6IFRydWV9KQphc3luYyBkZWYgd29ya2l2YV9saXN0X3F1ZXJpZXMocGFyYW1zOiBMaXN0UXVlcmllc0lucHV0KSAtPiBzdHI6CiAgICAiIiJMaXN0YSBxdWVyaWVzIFdEYXRhLiIiIgogICAgdHJ5OgogICAgICAgIHVybCAgID0gZiJ7V0RBVEFfVVJMfS9xdWVyeT93b3Jrc3BhY2VJZD17V09SS1NQQUNFX0lEfSIKICAgICAgICByICAgICA9IGF3YWl0IF93ay5nZXQodXJsKQogICAgICAgIGl0ZW1zID0gci5qc29uKCkuZ2V0KCJkYXRhIiwgW10pCiAgICAgICAgaWYgcGFyYW1zLnBhdHRlcm46CiAgICAgICAgICAgIHJ4ICAgID0gcmUuY29tcGlsZShwYXJhbXMucGF0dGVybiwgcmUuSUdOT1JFQ0FTRSkKICAgICAgICAgICAgaXRlbXMgPSBbcSBmb3IgcSBpbiBpdGVtcyBpZiByeC5zZWFyY2gocS5nZXQoIm5hbWUiLCAiIikpXQogICAgICAgIHRvdGFsID0gbGVuKGl0ZW1zKQogICAgICAgIHBhZ2UgID0gaXRlbXNbcGFyYW1zLm9mZnNldDogcGFyYW1zLm9mZnNldCArIHBhcmFtcy5saW1pdF0KICAgICAgICByZXR1cm4ganNvbi5kdW1wcyh7CiAgICAgICAgICAgICJ0b3RhbCI6IHRvdGFsLCAiY291bnQiOiBsZW4ocGFnZSksICJvZmZzZXQiOiBwYXJhbXMub2Zmc2V0LAogICAgICAgICAgICAiaGFzX21vcmUiOiB0b3RhbCA+IHBhcmFtcy5vZmZzZXQgKyBsZW4ocGFnZSksCiAgICAgICAgICAgICJxdWVyaWVzIjogW3siaWQiOiBxLmdldCgiaWQiKSwgIm5hbWUiOiBxLmdldCgibmFtZSIpLAogICAgICAgICAgICAgICAgICAgICAgICAgInN0YXRlbWVudCI6IChxLmdldCgic3RhdGVtZW50Iikgb3IgIiIpWzoyMDBdfSBmb3IgcSBpbiBwYWdlXSwKICAgICAgICB9LCBpbmRlbnQ9MiwgZW5zdXJlX2FzY2lpPUZhbHNlKQogICAgZXhjZXB0IEV4Y2VwdGlvbiBhcyBlOgogICAgICAgIHJldHVybiBfaGFuZGxlX2Vycm9yKGUpCgoKIyDilIDilIDilIAgNy4gRUpFQ1VUQVIgUVVFUlkgV0RBVEEg4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSACgpjbGFzcyBSdW5RdWVyeUlucHV0KEJhc2VNb2RlbCk6CiAgICBtb2RlbF9jb25maWcgPSBDb25maWdEaWN0KHN0cl9zdHJpcF93aGl0ZXNwYWNlPVRydWUpCiAgICBxdWVyeV9pZDogICBzdHIgICAgICAgICAgICAgICAgICAgICAgID0gRmllbGQoLi4uKQogICAgcGFyYW1ldGVyczogT3B0aW9uYWxbZGljdFtzdHIsIHN0cl1dICA9IEZpZWxkKGRlZmF1bHQ9Tm9uZSkKICAgIG1heF9yb3dzOiAgIGludCAgICAgICAgICAgICAgICAgICAgICAgPSBGaWVsZChkZWZhdWx0PTUwMCwgZ2U9MSwgbGU9NTAwMCkKCgpAbWNwLnRvb2wobmFtZT0id29ya2l2YV9ydW5fcXVlcnkiLAogICAgICAgICAgYW5ub3RhdGlvbnM9eyJyZWFkT25seUhpbnQiOiBUcnVlLCAiZGVzdHJ1Y3RpdmVIaW50IjogRmFsc2UsCiAgICAgICAgICAgICAgICAgICAgICAgImlkZW1wb3RlbnRIaW50IjogRmFsc2UsICJvcGVuV29ybGRIaW50IjogVHJ1ZX0pCmFzeW5jIGRlZiB3b3JraXZhX3J1bl9xdWVyeShwYXJhbXM6IFJ1blF1ZXJ5SW5wdXQpIC0+IHN0cjoKICAgICIiIkVqZWN1dGEgdW5hIHF1ZXJ5IFdEYXRhIHkgcmV0b3JuYSByZXN1bHRhZG9zLiIiIgogICAgdHJ5OgogICAgICAgIGJvZHk6IGRpY3Rbc3RyLCBBbnldID0ge30KICAgICAgICBpZiBwYXJhbXMucGFyYW1ldGVyczoKICAgICAgICAgICAgYm9keVsicGFyYW1ldGVycyJdID0gW3sibmFtZSI6IGssICJ2YWx1ZSI6IHZ9CiAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgZm9yIGssIHYgaW4gcGFyYW1zLnBhcmFtZXRlcnMuaXRlbXMoKV0KICAgICAgICByID0gYXdhaXQgX3drLnBvc3QoZiJ7V0RBVEFfVVJMfS9xdWVyeS97cGFyYW1zLnF1ZXJ5X2lkfS9yZXN1bHQiLAogICAgICAgICAgICAgICAgICAgICAgICAgICBqc29uPWJvZHkgb3IgTm9uZSkKICAgICAgICBpZiByLnN0YXR1c19jb2RlIG5vdCBpbiAoMjAwLCAyMDEsIDIwMik6CiAgICAgICAgICAgIHJldHVybiBmIkVycm9yIGFsIGxhbnphciBxdWVyeTogSFRUUCB7ci5zdGF0dXNfY29kZX0g4oCUIHtyLnRleHRbOjIwMF19IgogICAgICAgIHJlc3VsdF9pZCA9IHIuanNvbigpLmdldCgiZGF0YSIsIHt9KS5nZXQoImlkIikgb3Igci5qc29uKCkuZ2V0KCJpZCIpCiAgICAgICAgaWYgbm90IHJlc3VsdF9pZDoKICAgICAgICAgICAgcmV0dXJuICJFcnJvcjogTm8gc2Ugb2J0dXZvIElEIGRlIHJlc3VsdGFkby4iCiAgICAgICAgZm9yIF8gaW4gcmFuZ2UoNjApOgogICAgICAgICAgICBhd2FpdCBhc3luY2lvLnNsZWVwKDMpCiAgICAgICAgICAgIHBvbGwgICA9IGF3YWl0IF93ay5nZXQoZiJ7V0RBVEFfVVJMfS9xdWVyeS97cGFyYW1zLnF1ZXJ5X2lkfS9yZXN1bHQve3Jlc3VsdF9pZH0iKQogICAgICAgICAgICBzdGF0dXMgPSBwb2xsLmpzb24oKS5nZXQoImRhdGEiLCB7fSkuZ2V0KCJzdGF0dXMiLCAiIikKICAgICAgICAgICAgaWYgc3RhdHVzID09ICJDT01QTEVURSI6CiAgICAgICAgICAgICAgICBicmVhawogICAgICAgICAgICBpZiBzdGF0dXMgPT0gIkVSUk9SIjoKICAgICAgICAgICAgICAgIHJldHVybiBmIkVycm9yIGVuIGxhIHF1ZXJ5OiB7cG9sbC5qc29uKCkuZ2V0KCdkYXRhJywge30pLmdldCgnZXJyb3InLCAnJyl9IgogICAgICAgIGRsID0gYXdhaXQgX3drLmdldCgKICAgICAgICAgICAgZiJ7V0RBVEFfVVJMfS9xdWVyeS97cGFyYW1zLnF1ZXJ5X2lkfS9yZXN1bHQve3Jlc3VsdF9pZH0vZG93bmxvYWQiKQogICAgICAgIGlmIGRsLnN0YXR1c19jb2RlICE9IDIwMDoKICAgICAgICAgICAgcmV0dXJuIGYiRXJyb3IgYWwgZGVzY2FyZ2FyIHJlc3VsdGFkbzogSFRUUCB7ZGwuc3RhdHVzX2NvZGV9IgogICAgICAgIHJlYWRlciAgPSBjc3YuRGljdFJlYWRlcihpby5TdHJpbmdJTyhkbC50ZXh0KSkKICAgICAgICBjb2x1bW5zID0gcmVhZGVyLmZpZWxkbmFtZXMgb3IgW10KICAgICAgICByb3dzICAgID0gW2xpc3Qocm93LnZhbHVlcygpKSBmb3Igcm93IGluIHJlYWRlcl0KICAgICAgICB0cnVuY2F0ZWQgPSBsZW4ocm93cykgPiBwYXJhbXMubWF4X3Jvd3MKICAgICAgICByb3dzICAgICAgPSByb3dzWzogcGFyYW1zLm1heF9yb3dzXQogICAgICAgIHJldHVybiBqc29uLmR1bXBzKHsKICAgICAgICAgICAgInF1ZXJ5X2lkIjogcGFyYW1zLnF1ZXJ5X2lkLCAicmVzdWx0X2lkIjogcmVzdWx0X2lkLAogICAgICAgICAgICAiY29sdW1ucyI6IGxpc3QoY29sdW1ucyksICJ0b3RhbF9yb3dzIjogbGVuKHJvd3MpLAogICAgICAgICAgICAidHJ1bmNhdGVkIjogdHJ1bmNhdGVkLCAicm93cyI6IHJvd3MsCiAgICAgICAgfSwgaW5kZW50PTIsIGVuc3VyZV9hc2NpaT1GYWxzZSkKICAgIGV4Y2VwdCBFeGNlcHRpb24gYXMgZToKICAgICAgICByZXR1cm4gX2hhbmRsZV9lcnJvcihlKQoKCiMg4pSA4pSA4pSAIDguIExMRU5BUiBDT01QQVJBVElWT1MgKFYyIOKAlCBjb24gc29wb3J0ZSBFRVJSKSDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIAKCmNsYXNzIEZpbGxDb21wYXJhdGl2ZXNJbnB1dChCYXNlTW9kZWwpOgogICAgbW9kZWxfY29uZmlnID0gQ29uZmlnRGljdChzdHJfc3RyaXBfd2hpdGVzcGFjZT1UcnVlKQogICAgc3ByZWFkc2hlZXRfaWQ6ICAgICAgICAgIHN0ciAgICAgICA9IEZpZWxkKC4uLikKICAgIGRyeV9ydW46ICAgICAgICAgICAgICAgICBib29sICAgICAgPSBGaWVsZChkZWZhdWx0PVRydWUpCiAgICBzaGVldF9vZmZzZXQ6ICAgICAgICAgICAgaW50ICAgICAgID0gRmllbGQoZGVmYXVsdD0wLCBnZT0wKQogICAgbWF4X3NoZWV0czogICAgICAgICAgICAgIGludCAgICAgICA9IEZpZWxkKGRlZmF1bHQ9MjAsIGdlPTEsIGxlPTEwMCkKICAgIGV4Y2x1ZGVfc2hlZXRzOiAgICAgICAgICBsaXN0W3N0cl0gPSBGaWVsZChkZWZhdWx0X2ZhY3Rvcnk9bGlzdCkKICAgIGluY2x1ZGVfc2hlZXRzOiAgICAgICAgICBsaXN0W3N0cl0gPSBGaWVsZChkZWZhdWx0X2ZhY3Rvcnk9bGlzdCkKICAgIGFwcGx5X2RlZmF1bHRfZXhjbHVkZXM6ICBib29sICAgICAgPSBGaWVsZChkZWZhdWx0PVRydWUpCiAgICBtYXhfZWplbXBsb3M6ICAgICAgICAgICAgaW50ICAgICAgID0gRmllbGQoZGVmYXVsdD0zLCBnZT0xLCBsZT0xMDAwKQogICAgZGV0YWxsZV9maWxhczogICAgICAgICAgIGJvb2wgICAgICA9IEZpZWxkKGRlZmF1bHQ9RmFsc2UpCgoKQG1jcC50b29sKAogICAgbmFtZT0id29ya2l2YV9maWxsX2NvbXBhcmF0aXZlcyIsCiAgICBhbm5vdGF0aW9ucz17InJlYWRPbmx5SGludCI6IEZhbHNlLCAiZGVzdHJ1Y3RpdmVIaW50IjogRmFsc2UsCiAgICAgICAgICAgICAgICAgImlkZW1wb3RlbnRIaW50IjogVHJ1ZSwgIm9wZW5Xb3JsZEhpbnQiOiBUcnVlfQopCmFzeW5jIGRlZiB3b3JraXZhX2ZpbGxfY29tcGFyYXRpdmVzKHBhcmFtczogRmlsbENvbXBhcmF0aXZlc0lucHV0KSAtPiBzdHI6CiAgICAiIiIKICAgIExsZW5hIGNvbHVtbmFzIGNvbXBhcmF0aXZhcyBkZSB1biBhcmNoaXZvIEJhc2UgTm90YXMuCgogICAgQ0FNQklPUyB2cyB2ZXJzacOzbiBvcmlnaW5hbDoKICAgIC0gRGV0ZWN0YSB5IHByb2Nlc2EgY29sdW1uYXMgRUVSUiAocHJpb3JfZWVycl9lbmQpIGFkZW3DoXMgZGUgYmFsYW5jZSAocHJpb3JfZW5kKS4KICAgIC0gTGEgcmVzdHJpY2Npw7NuIGRlIG1lcyAwMyBhcGxpY2Egc29sbyBhIGNvbHVtbmFzIGRlIEJBTEFOQ0U7IGxhcyBjb2x1bW5hcwogICAgICBFRVJSIHNlIGVzY3JpYmVuIGVuIGN1YWxxdWllciBtZXMuCiAgICAtIFJlcG9ydGEgc291cmNlX2VlcnIgYWRlbcOhcyBkZSBzb3VyY2VfYmFsYW5jZS4KICAgICIiIgogICAgU0tJUF9TSEVFVFMgPSB7CiAgICAgICAgIkNQIiwgIkJhc2VzIiwgIlF1ZXJ5IEJQQyIsICJRdWVyeSBIQU5BIEFGIiwgIlJlcG9ydGUgZW4gJCIsCiAgICAgICAgIlF1ZXJ5IC0gSEFOQSAtIERldWRvcmVzIiwgIkEuLSBBY3Rpdm9zIFBQVCIsCiAgICAgICAgIkIuLSBQYXRyaW1vbmlvIHkgUGFzaXZvcyBQUFQiLCAiQy4tIEVzdGFkbyBkZSByZXN1bHRhZG8gcG9yIGZ1bmNpw7NuIFBQVCIsCiAgICAgICAgIkUxIFJlcyBBY3VtdWxhZG8iLCAiRjEgQ3VhZHJhamUgSG9qYSBBLi0gU2FsZG8gSW5pY2lhbCBkZSBDYWphIiwKICAgICAgICAiMjYuLSIsICAjIFRyYW5zYWNjaW9uZXMgY29uIHJlbGFjaW9uYWRhcyDigJQgZXN0cnVjdHVyYSBlc3BlY2lhbCwgbGxlbmFkbyBtYW51YWwKICAgIH0KICAgIEFVWF9TS0lQX1NIRUVUUyA9IHsKICAgICAgICAiUXVlcnkgSEFOQSIsICJSZXBvcnRlIGNvbnNvbGlkYWRvIGVuICQiLCAiUGxhbnRpbGxhIGNvbnNvbGlkYWNpw7NuIiwKICAgICAgICAiVlAiLCAiU29jaWVkYWRlcyIsICJQYXJ0aWNpcGFjacOzbiBhY2Npb25hcmlhIiwgIkNvbnZlcnNpb25lcyBtb25lZGFzIiwKICAgICAgICAiVHJhZHVjY2nDs24gTm90YXMiLCAiUmVsYWNpb25hZGFzIiwgImRldGFsbGUgZWZlIHR4IEdOLUdMIiwKICAgIH0KICAgIFNPQ0lFREFEX1JFID0gcmUuY29tcGlsZShyIihDR0VNfEVkZWxtYWd8RWRlbGFtZylccyokIiwgcmUuSUdOT1JFQ0FTRSkKCiAgICB0cnk6CiAgICAgICAgIyAxLiBMZWVyIGhvamFzIGRlbCBkZXN0aW5vCiAgICAgICAgdGd0X3NoZWV0cyA9IGF3YWl0IF9nZXRfc2hlZXRzKHBhcmFtcy5zcHJlYWRzaGVldF9pZCkKICAgICAgICBpZiAiQmFzZXMiIG5vdCBpbiB0Z3Rfc2hlZXRzOgogICAgICAgICAgICByZXR1cm4gIkVycm9yOiBFbCBhcmNoaXZvIG5vIHRpZW5lIGhvamEgJ0Jhc2VzJy4iCgogICAgICAgICMgMi4gTGVlciBob2phIEJhc2VzCiAgICAgICAgYmFzZXNfY2VsbHMgPSBhd2FpdCBfcmVhZF9zaGVldF9jZWxscyhwYXJhbXMuc3ByZWFkc2hlZXRfaWQsIHRndF9zaGVldHNbIkJhc2VzIl0pCiAgICAgICAgYmFzZXM6IGRpY3Rbc3RyLCBzdHJdID0ge30KICAgICAgICBsYWJlbF9tYXAgPSB7CiAgICAgICAgICAgICJlc3RhZG9zIGZpbmFuY2llcm9zIjogICAgICAgICAgICAoImN1cnJlbnRfZW5kIiwgICAgICAgICAicHJpb3JfZW5kIiksCiAgICAgICAgICAgICJlc3RhZG8gZGUgcmVzdWx0YWRvcyAtIGluaWNpYWwiOiAoImVlcnJfc3RhcnQiLCAgICAgICAgICAicHJpb3JfZWVycl9zdGFydCIpLAogICAgICAgICAgICAiZXN0YWRvIGRlIHJlc3VsdGFkb3MgLSBmaW5hbCI6ICAgKCJlZXJyX2VuZCIsICAgICAgICAgICAgInByaW9yX2VlcnJfZW5kIiksCiAgICAgICAgICAgICJlc3RhZG8gZGUgcmVzdWx0YWRvcyAtIHF1YXJ0ZXJzIjooInF1YXJ0ZXJfc3RhcnQiLCAgICAgICAicHJpb3JfcXVhcnRlcl9zdGFydCIpLAogICAgICAgICAgICAiZXN0YWRvcyBmaW5hbmNpZXJvcyBhbnRlcmlvcmVzIjogKCJwcmV2X3BlcmlvZF9lbmQiLCAgICAgInByaW9yX3ByZXZfcGVyaW9kX2VuZCIpLAogICAgICAgIH0KICAgICAgICBmb3Igcm93IGluIGJhc2VzX2NlbGxzOgogICAgICAgICAgICBsYWJlbCA9IHN0cihfY3Yocm93WzFdKSBvciAiIikuc3RyaXAoKS5sb3dlcigpIGlmIGxlbihyb3cpID4gMSBlbHNlICIiCiAgICAgICAgICAgIGtleXMgID0gbGFiZWxfbWFwLmdldChsYWJlbCkKICAgICAgICAgICAgaWYgbm90IGtleXM6CiAgICAgICAgICAgICAgICBjb250aW51ZQogICAgICAgICAgICBmb3IgY29sX2lkeCwga2V5IGluIFsoMywga2V5c1swXSksICg1LCBrZXlzWzFdKV06CiAgICAgICAgICAgICAgICBjdiA9IF9jdihyb3dbY29sX2lkeF0pIGlmIGNvbF9pZHggPCBsZW4ocm93KSBlbHNlIE5vbmUKICAgICAgICAgICAgICAgIGlmIGN2OgogICAgICAgICAgICAgICAgICAgIGJhc2VzW2tleV0gPSBzdHIoY3YpCgogICAgICAgIGN1cnJfZW5kICA9IGJhc2VzLmdldCgiY3VycmVudF9lbmQiLCAiPyIpCiAgICAgICAgcHJpb3JfZW5kID0gYmFzZXMuZ2V0KCJwcmlvcl9lbmQiLCAiPyIpCgogICAgICAgIHJlcG9ydDogZGljdFtzdHIsIEFueV0gPSB7CiAgICAgICAgICAgICJzcHJlYWRzaGVldF9pZCI6ICAgcGFyYW1zLnNwcmVhZHNoZWV0X2lkLAogICAgICAgICAgICAiZHJ5X3J1biI6ICAgICAgICAgIHBhcmFtcy5kcnlfcnVuLAogICAgICAgICAgICAiY3VycmVudF9lbmQiOiAgICAgIGN1cnJfZW5kLAogICAgICAgICAgICAicHJpb3JfZW5kIjogICAgICAgIHByaW9yX2VuZCwKICAgICAgICAgICAgImJhc2VzIjogICAgICAgICAgICBiYXNlcywKICAgICAgICAgICAgInNoZWV0c19wcm9jZXNzZWQiOiBbXSwKICAgICAgICAgICAgInNoZWV0c19za2lwcGVkIjogICBbXSwKICAgICAgICAgICAgInNoZWV0c19mYWlsZWQiOiAgICBbXSwKICAgICAgICAgICAgInRvdGFsX2NvbHNfd3JpdHRlbiI6IDAsCiAgICAgICAgICAgICJ0b3RhbF9jb2xzX2ZhaWxlZCI6ICAwLAogICAgICAgIH0KCiAgICAgICAgIyAzLiBCdXNjYXIgYXJjaGl2b3MgZnVlbnRlCiAgICAgICAgYWxsX2ZpbGVzICA9IGF3YWl0IF9sb2FkX2FsbF9maWxlcygpCiAgICAgICAgaWRfdG9fbmFtZSA9IHt2OiBrIGZvciBrLCB2IGluIGFsbF9maWxlcy5pdGVtcygpfQogICAgICAgIHRhcmdldF9uYW1lID0gaWRfdG9fbmFtZS5nZXQocGFyYW1zLnNwcmVhZHNoZWV0X2lkLCAiIikKCiAgICAgICAgbSA9IHJlLm1hdGNoKHIiKFwoKD86Q0hOfExDKVwpXHMqKT8oRVxkKylfKElORHxDT05TTylfKFxkezJ9KVstX10oXGR7NH0pXyguKikiLAogICAgICAgICAgICAgICAgICAgICB0YXJnZXRfbmFtZSkKICAgICAgICBpZiBub3QgbToKICAgICAgICAgICAgcmVwb3J0WyJ3YXJuaW5nIl0gPSAoCiAgICAgICAgICAgICAgICBmIk5vbWJyZSAne3RhcmdldF9uYW1lfScgbm8gc2lndWUgZWwgcGF0csOzbiBlc3BlcmFkby4iCiAgICAgICAgICAgICkKICAgICAgICAgICAgcmV0dXJuIGpzb24uZHVtcHMocmVwb3J0LCBpbmRlbnQ9MiwgZW5zdXJlX2FzY2lpPUZhbHNlKQoKICAgICAgICBwcmVmaXgsIGNvZGUsIHRpcG8sIG1tLCB5eXl5LCBzdWZmaXggPSBtLmdyb3VwcygpCiAgICAgICAgcHJlZml4ID0gcHJlZml4IG9yICIiCgogICAgICAgIGRlZiBfZGF0ZV9wYXJ0cyhkOiBzdHIpIC0+IHR1cGxlW3N0ciwgc3RyXToKICAgICAgICAgICAgcGFydHMgPSBzdHIoZCkuc3BsaXQoIi0iKQogICAgICAgICAgICByZXR1cm4gKHBhcnRzWzFdLCBwYXJ0c1swXSkgaWYgbGVuKHBhcnRzKSA+PSAyIGVsc2UgKCIiLCAiIikKCiAgICAgICAgIyDDjW5kaWNlIGRlIGFsbF9maWxlcyBub3JtYWxpemFkbyAoZXNwYWNpb3MgbcO6bHRpcGxlcyDihpIgdW5vKQogICAgICAgIF9hbGxfZmlsZXNfbm9ybTogZGljdFtzdHIsIHN0cl0gPSB7CiAgICAgICAgICAgIHJlLnN1YihyIlxzKyIsICIgIiwgayk6IHYgZm9yIGssIHYgaW4gYWxsX2ZpbGVzLml0ZW1zKCkKICAgICAgICB9CgogICAgICAgIGRlZiBfZmluZF9maWxlKG5hbWU6IHN0cikgLT4gc3RyIHwgTm9uZToKICAgICAgICAgICAgIiIiQnVzY2EgZW4gYWxsX2ZpbGVzIG5vcm1hbGl6YW5kbyBlc3BhY2lvcyBtw7psdGlwbGVzLiIiIgogICAgICAgICAgICBub3JtID0gcmUuc3ViKHIiXHMrIiwgIiAiLCBuYW1lKQogICAgICAgICAgICByZXR1cm4gX2FsbF9maWxlc19ub3JtLmdldChub3JtKQoKICAgICAgICAjIEZ1ZW50ZSBCQUxBTkNFIChwcmlvcl9lbmQgPSBkaWMgYcOxbyBhbnRlcmlvcikKICAgICAgICBzcmNfYmFsYW5jZV9pZDogc3RyIHwgTm9uZSA9IE5vbmUKICAgICAgICBpZiBiYXNlcy5nZXQoInByaW9yX2VuZCIpOgogICAgICAgICAgICBtbV9iLCB5eV9iID0gX2RhdGVfcGFydHMoYmFzZXNbInByaW9yX2VuZCJdKQogICAgICAgICAgICBmb3Igc2VwIGluIFsiLSIsICJfIl06CiAgICAgICAgICAgICAgICBuYW1lID0gZiJ7cHJlZml4fXtjb2RlfV97dGlwb31fe21tX2J9e3NlcH17eXlfYn1fe3N1ZmZpeH0iCiAgICAgICAgICAgICAgICBmaWQgID0gX2ZpbmRfZmlsZShuYW1lKQogICAgICAgICAgICAgICAgaWYgZmlkOgogICAgICAgICAgICAgICAgICAgIHNyY19iYWxhbmNlX2lkID0gZmlkCiAgICAgICAgICAgICAgICAgICAgcmVwb3J0WyJzb3VyY2VfYmFsYW5jZSJdID0gbmFtZQogICAgICAgICAgICAgICAgICAgIGJyZWFrCgogICAgICAgIGlmIG5vdCBzcmNfYmFsYW5jZV9pZDoKICAgICAgICAgICAgcmVwb3J0WyJ3YXJuaW5nIl0gPSAiTm8gc2UgZW5jb250csOzIGVsIGFyY2hpdm8gZnVlbnRlIGRlIGJhbGFuY2UgY29tcGFyYXRpdm8uIgogICAgICAgICAgICByZXR1cm4ganNvbi5kdW1wcyhyZXBvcnQsIGluZGVudD0yLCBlbnN1cmVfYXNjaWk9RmFsc2UpCgogICAgICAgICMgRnVlbnRlIEVFUlIvUVVBUlRFUiAocHJpb3JfZWVycl9lbmQgPSBtaXNtbyBwZXLDrW9kbyBhw7FvIGFudGVyaW9yLCBlai4gMDktMjAyNSkKICAgICAgICBzcmNfZWVycl9pZDogc3RyIHwgTm9uZSA9IE5vbmUKICAgICAgICBpZiBiYXNlcy5nZXQoInByaW9yX2VlcnJfZW5kIik6CiAgICAgICAgICAgIG1tX2UsIHl5X2UgPSBfZGF0ZV9wYXJ0cyhiYXNlc1sicHJpb3JfZWVycl9lbmQiXSkKICAgICAgICAgICAgZm9yIHNlcCBpbiBbIi0iLCAiXyJdOgogICAgICAgICAgICAgICAgbmFtZSA9IGYie3ByZWZpeH17Y29kZX1fe3RpcG99X3ttbV9lfXtzZXB9e3l5X2V9X3tzdWZmaXh9IgogICAgICAgICAgICAgICAgZmlkICA9IF9maW5kX2ZpbGUobmFtZSkKICAgICAgICAgICAgICAgIGlmIGZpZDoKICAgICAgICAgICAgICAgICAgICBzcmNfZWVycl9pZCA9IGZpZAogICAgICAgICAgICAgICAgICAgIHJlcG9ydFsic291cmNlX2VlcnIiXSA9IG5hbWUKICAgICAgICAgICAgICAgICAgICBicmVhawogICAgICAgIGlmIG5vdCBzcmNfZWVycl9pZDoKICAgICAgICAgICAgcmVwb3J0WyJzb3VyY2VfZWVyciJdID0gIk5vIGVuY29udHJhZG8iCgogICAgICAgICMgRnVlbnRlIFBFUsONT0RPIEFOVEVSSU9SIGNvbXBhcmF0aXZvIChwcmlvcl9wcmV2X3BlcmlvZF9lbmQgPSBlai4gMDYtMjAyNSBwYXJhIFEzKQogICAgICAgIHNyY19wcmV2X2lkOiBzdHIgfCBOb25lID0gTm9uZQogICAgICAgIGlmIGJhc2VzLmdldCgicHJpb3JfcHJldl9wZXJpb2RfZW5kIik6CiAgICAgICAgICAgIG1tX3AsIHl5X3AgPSBfZGF0ZV9wYXJ0cyhiYXNlc1sicHJpb3JfcHJldl9wZXJpb2RfZW5kIl0pCiAgICAgICAgICAgIGZvciBzZXAgaW4gWyItIiwgIl8iXToKICAgICAgICAgICAgICAgIG5hbWUgPSBmIntwcmVmaXh9e2NvZGV9X3t0aXBvfV97bW1fcH17c2VwfXt5eV9wfV97c3VmZml4fSIKICAgICAgICAgICAgICAgIGZpZCAgPSBfZmluZF9maWxlKG5hbWUpCiAgICAgICAgICAgICAgICBpZiBmaWQ6CiAgICAgICAgICAgICAgICAgICAgc3JjX3ByZXZfaWQgPSBmaWQKICAgICAgICAgICAgICAgICAgICByZXBvcnRbInNvdXJjZV9wcmV2X3BlcmlvZCJdID0gbmFtZQogICAgICAgICAgICAgICAgICAgIGJyZWFrCiAgICAgICAgaWYgbm90IHNyY19wcmV2X2lkOgogICAgICAgICAgICByZXBvcnRbInNvdXJjZV9wcmV2X3BlcmlvZCJdID0gIk5vIGVuY29udHJhZG8iCgogICAgICAgICMgRnVlbnRlIFBFUsONT0RPIEFOVEVSSU9SIGFjdHVhbCAocHJldl9wZXJpb2RfZW5kID0gZWouIDA2LTIwMjYgcGFyYSBRMykKICAgICAgICBzcmNfY3Vycl9wcmV2X2lkOiBzdHIgfCBOb25lID0gTm9uZQogICAgICAgIGlmIGJhc2VzLmdldCgicHJldl9wZXJpb2RfZW5kIik6CiAgICAgICAgICAgIG1tX2NwLCB5eV9jcCA9IF9kYXRlX3BhcnRzKGJhc2VzWyJwcmV2X3BlcmlvZF9lbmQiXSkKICAgICAgICAgICAgZm9yIHNlcCBpbiBbIi0iLCAiXyJdOgogICAgICAgICAgICAgICAgbmFtZSA9IGYie3ByZWZpeH17Y29kZX1fe3RpcG99X3ttbV9jcH17c2VwfXt5eV9jcH1fe3N1ZmZpeH0iCiAgICAgICAgICAgICAgICBmaWQgID0gX2ZpbmRfZmlsZShuYW1lKQogICAgICAgICAgICAgICAgaWYgZmlkOgogICAgICAgICAgICAgICAgICAgIHNyY19jdXJyX3ByZXZfaWQgPSBmaWQKICAgICAgICAgICAgICAgICAgICByZXBvcnRbInNvdXJjZV9jdXJyX3ByZXYiXSA9IG5hbWUKICAgICAgICAgICAgICAgICAgICBicmVhawogICAgICAgIGlmIG5vdCBzcmNfY3Vycl9wcmV2X2lkOgogICAgICAgICAgICByZXBvcnRbInNvdXJjZV9jdXJyX3ByZXYiXSA9ICJObyBlbmNvbnRyYWRvIgoKICAgICAgICBzcmNfc2hlZXRzX2JhbCAgICAgICA9IGF3YWl0IF9nZXRfc2hlZXRzKHNyY19iYWxhbmNlX2lkKQogICAgICAgIHNyY19zaGVldHNfZWVyciAgICAgID0gYXdhaXQgX2dldF9zaGVldHMoc3JjX2VlcnJfaWQpICAgICAgIGlmIHNyY19lZXJyX2lkICAgICAgIGVsc2Uge30KICAgICAgICBzcmNfc2hlZXRzX3ByZXYgICAgICA9IGF3YWl0IF9nZXRfc2hlZXRzKHNyY19wcmV2X2lkKSAgICAgICBpZiBzcmNfcHJldl9pZCAgICAgICBlbHNlIHt9CiAgICAgICAgc3JjX3NoZWV0c19jdXJyX3ByZXYgPSBhd2FpdCBfZ2V0X3NoZWV0cyhzcmNfY3Vycl9wcmV2X2lkKSAgaWYgc3JjX2N1cnJfcHJldl9pZCAgZWxzZSB7fQoKICAgICAgICAjIDQuIENhbmRpZGF0YXMKICAgICAgICBleHRyYV9leGNsdWRlcyAgPSBzZXQocGFyYW1zLmV4Y2x1ZGVfc2hlZXRzKQogICAgICAgIGluY2x1ZGVfbG93ZXIgICA9IFtzLmxvd2VyKCkgZm9yIHMgaW4gcGFyYW1zLmluY2x1ZGVfc2hlZXRzXSBpZiBwYXJhbXMuaW5jbHVkZV9zaGVldHMgZWxzZSBOb25lCiAgICAgICAgY2FuZGlkYXRlczogbGlzdFtzdHJdID0gW10KICAgICAgICBza2lwcGVkX3NvY2llZGFkID0gMAogICAgICAgIGZvciBzbmFtZSBpbiB0Z3Rfc2hlZXRzOgogICAgICAgICAgICBpZiBpbmNsdWRlX2xvd2VyIGlzIG5vdCBOb25lIGFuZCBub3QgYW55KGt3IGluIHNuYW1lLmxvd2VyKCkgZm9yIGt3IGluIGluY2x1ZGVfbG93ZXIpOgogICAgICAgICAgICAgICAgY29udGludWUKICAgICAgICAgICAgaWYgc25hbWUgaW4gU0tJUF9TSEVFVFMgb3IgYW55KHNuYW1lLnN0YXJ0c3dpdGgocCkgZm9yIHAgaW4gU0tJUF9TSEVFVFMpIG9yIHNuYW1lIGluIGV4dHJhX2V4Y2x1ZGVzOgogICAgICAgICAgICAgICAgaWYgcGFyYW1zLnNoZWV0X29mZnNldCA9PSAwOgogICAgICAgICAgICAgICAgICAgIHJlcG9ydFsic2hlZXRzX3NraXBwZWQiXS5hcHBlbmQoc25hbWUpCiAgICAgICAgICAgIGVsaWYgcGFyYW1zLmFwcGx5X2RlZmF1bHRfZXhjbHVkZXMgYW5kIHNuYW1lIGluIEFVWF9TS0lQX1NIRUVUUzoKICAgICAgICAgICAgICAgIGlmIHBhcmFtcy5zaGVldF9vZmZzZXQgPT0gMDoKICAgICAgICAgICAgICAgICAgICByZXBvcnRbInNoZWV0c19za2lwcGVkIl0uYXBwZW5kKGYie3NuYW1lfSAoYXV4aWxpYXIpIikKICAgICAgICAgICAgZWxpZiBwYXJhbXMuYXBwbHlfZGVmYXVsdF9leGNsdWRlcyBhbmQgU09DSUVEQURfUkUuc2VhcmNoKHNuYW1lKToKICAgICAgICAgICAgICAgIHNraXBwZWRfc29jaWVkYWQgKz0gMQogICAgICAgICAgICBlbGlmIHNuYW1lIG5vdCBpbiBzcmNfc2hlZXRzX2JhbCBhbmQgc25hbWUgbm90IGluIHNyY19zaGVldHNfZWVyciBhbmQgc25hbWUgbm90IGluIHNyY19zaGVldHNfcHJldiBhbmQgc25hbWUgbm90IGluIHNyY19zaGVldHNfY3Vycl9wcmV2OgogICAgICAgICAgICAgICAgaWYgcGFyYW1zLnNoZWV0X29mZnNldCA9PSAwOgogICAgICAgICAgICAgICAgICAgIHJlcG9ydFsic2hlZXRzX3NraXBwZWQiXS5hcHBlbmQoZiJ7c25hbWV9IChubyBlbiBmdWVudGUpIikKICAgICAgICAgICAgZWxzZToKICAgICAgICAgICAgICAgIGNhbmRpZGF0ZXMuYXBwZW5kKHNuYW1lKQogICAgICAgIGlmIHBhcmFtcy5hcHBseV9kZWZhdWx0X2V4Y2x1ZGVzOgogICAgICAgICAgICByZXBvcnRbInNraXBwZWRfZGVzZ2xvc2Vfc29jaWVkYWQiXSA9IHNraXBwZWRfc29jaWVkYWQKCiAgICAgICAgYmF0Y2ggICAgICA9IGNhbmRpZGF0ZXNbcGFyYW1zLnNoZWV0X29mZnNldDogcGFyYW1zLnNoZWV0X29mZnNldCArIHBhcmFtcy5tYXhfc2hlZXRzXQogICAgICAgIG5leHRfb2Zmc2V0ID0gcGFyYW1zLnNoZWV0X29mZnNldCArIGxlbihiYXRjaCkKICAgICAgICByZXBvcnRbInRvdGFsX2NhbmRpZGF0ZV9zaGVldHMiXSA9IGxlbihjYW5kaWRhdGVzKQogICAgICAgIHJlcG9ydFsic2hlZXRfb2Zmc2V0Il0gICAgICAgICAgID0gcGFyYW1zLnNoZWV0X29mZnNldAogICAgICAgIHJlcG9ydFsiYmF0Y2hfc2l6ZSJdICAgICAgICAgICAgID0gbGVuKGJhdGNoKQogICAgICAgIHJlcG9ydFsiaGFzX21vcmUiXSAgICAgICAgICAgICAgID0gbmV4dF9vZmZzZXQgPCBsZW4oY2FuZGlkYXRlcykKICAgICAgICBpZiByZXBvcnRbImhhc19tb3JlIl06CiAgICAgICAgICAgIHJlcG9ydFsibmV4dF9vZmZzZXQiXSA9IG5leHRfb2Zmc2V0CgogICAgICAgICMgNS4gTGVlciBjZWxkYXMgZGVsIGxvdGUgZW4gcGFyYWxlbG8KICAgICAgICBzZW0gPSBhc3luY2lvLlNlbWFwaG9yZSg2KQoKICAgICAgICBhc3luYyBkZWYgX3JlYWRfbGltKHNzX2lkOiBzdHIsIHNpZDogc3RyKSAtPiBsaXN0W2xpc3RdOgogICAgICAgICAgICBhc3luYyB3aXRoIHNlbToKICAgICAgICAgICAgICAgIHJldHVybiBhd2FpdCBfcmVhZF9zaGVldF9jZWxscyhzc19pZCwgc2lkKQoKICAgICAgICB0Z3RfY2VsbHNfYnlfbmFtZSA9IGRpY3QoemlwKAogICAgICAgICAgICBiYXRjaCwKICAgICAgICAgICAgYXdhaXQgYXN5bmNpby5nYXRoZXIoCiAgICAgICAgICAgICAgICAqKF9yZWFkX2xpbShwYXJhbXMuc3ByZWFkc2hlZXRfaWQsIHRndF9zaGVldHNbc10pIGZvciBzIGluIGJhdGNoKQogICAgICAgICAgICApLAogICAgICAgICkpCgogICAgICAgICMgNi4gRGV0ZWN0YXIgY29sdW1uYXMgY29tcGFyYXRpdmFzIHBvciBmZWNoYSBlbiBlbmNhYmV6YWRvLgogICAgICAgICMgICAgVGlwb3MgeSBrZXl3b3JkcyBkZSBkZXRlY2Npw7NuIChlbiBvcmRlbiBkZSBwcmlvcmlkYWQgcGFyYSBldml0YXIgYW1iaWfDvGVkYWRlcyk6CiAgICAgICAgIyAgICAgICJxdWFydGVyIiAgICDihpIgcHJpb3JfcXVhcnRlcl9zdGFydCAgKGVqLiAyMDI1LTA3LTAxLCDDum5pY2EgcGFyYSBlbCBxdWFydGVyKQogICAgICAgICMgICAgICAiZWVyciIgICAgICAg4oaSIHByaW9yX2VlcnJfZW5kICAgICAgIChlai4gMjAyNS0wOS0zMCwgYWN1bXVsYWRvIGFudWFsKQogICAgICAgICMgICAgICAicHJldl9wZXJpb2Qi4oaSIHByaW9yX3ByZXZfcGVyaW9kX2VuZCAoZWouIDIwMjUtMDYtMzAsIHNlbWVzdHJlIGFudGVyaW9yKQogICAgICAgICMgICAgICAiYmFsIiAgICAgICAg4oaSIHByaW9yX2VuZCAgICAgICAgICAgIChlai4gMjAyNS0xMi0zMSwgYmFsYW5jZSkKICAgICAgICAjCiAgICAgICAgIyAgICBQYXJhIGVuY29udHJhciBsYSBjb2x1bW5hIGZ1ZW50ZSBzZSBidXNjYSBlbiBlbCBhcmNoaXZvIGZ1ZW50ZSBsYSBjb2x1bW5hCiAgICAgICAgIyAgICBxdWUgY29udGVuZ2EgbGEga2V5d29yZCBjYXJhY3RlcsOtc3RpY2EgZGUgY2FkYSB0aXBvIChkYXRlLWRyaXZlbiwgc2luIG9mZnNldCBmaWpvKS4KICAgICAgICAjICAgIExhIGtleXdvcmQgZGUgYsO6c3F1ZWRhIGVuIGVsIGZ1ZW50ZToKICAgICAgICAjICAgICAgInF1YXJ0ZXIiICAgIOKGkiBwcmlvcl9xdWFydGVyX3N0YXJ0ICAoY29sIGRlbCBxdWFydGVyIGVuIGZ1ZW50ZSAwOS1hYWFhKQogICAgICAgICMgICAgICAiZWVyciIgICAgICAg4oaSIHByaW9yX2VlcnJfc3RhcnQgICAgIChpbmljaW8gRUVSUiwgZGlzdGluZ3VlIGRlIHF1YXJ0ZXIpCiAgICAgICAgIyAgICAgICJwcmV2X3BlcmlvZCLihpIgcHJpb3JfcHJldl9wZXJpb2RfZW5kIChjb2wgYWN0dWFsIGVuIGZ1ZW50ZSAwNi1hYWFhKQogICAgICAgICMgICAgICAiYmFsIiAgICAgICAg4oaSIHByaW9yX2VuZCAgICAgICAgICAgIChjb2wgYWN0dWFsIGVuIGZ1ZW50ZSAxMi1hYWFhKQoKICAgICAgICBrd19iYWwgICAgICAgPSBzdHIoYmFzZXMuZ2V0KCJwcmlvcl9lbmQiLCAgICAgICAgICAgICAiIikpLmxvd2VyKCkKICAgICAgICBrd19lZXJyICAgICAgPSBzdHIoYmFzZXMuZ2V0KCJwcmlvcl9lZXJyX2VuZCIsICAgICAgICAiIikpLmxvd2VyKCkKICAgICAgICBrd19xdWFydGVyICAgPSBzdHIoYmFzZXMuZ2V0KCJwcmlvcl9xdWFydGVyX3N0YXJ0IiwgICAiIikpLmxvd2VyKCkKICAgICAgICBrd19wcmV2ICAgICAgPSBzdHIoYmFzZXMuZ2V0KCJwcmlvcl9wcmV2X3BlcmlvZF9lbmQiLCAiIikpLmxvd2VyKCkKICAgICAgICBrd19jdXJyX3ByZXYgPSBzdHIoYmFzZXMuZ2V0KCJwcmV2X3BlcmlvZF9lbmQiLCAgICAgICAiIikpLmxvd2VyKCkKICAgICAgICAjIFBhcmEgYnVzY2FyIGVuIGZ1ZW50ZTogdXNhciBzdGFydCBkZWwgRUVSUiAoZGlzdGluZ3VlIEVFUlIgdnMgcXVhcnRlcikKICAgICAgICBrd19lZXJyX3NyYyA9IHN0cihiYXNlcy5nZXQoInByaW9yX2VlcnJfc3RhcnQiLCAiIikpLmxvd2VyKCkgb3Iga3dfZWVycgoKICAgICAgICBkZWYgX3llYXJfc3RhcnQoZGF0ZV9zdHI6IHN0cikgLT4gc3RyOgogICAgICAgICAgICAiIiInMjAyNi0wNi0zMCcg4oaSICcyMDI2LTAxLTAxJyAgKGluaWNpbyBkZSBhw7FvIHBhcmEgZmlsdHJhciBjb2x1bW5hIFlURCkiIiIKICAgICAgICAgICAgcmV0dXJuIChkYXRlX3N0cls6NF0gKyAiLTAxLTAxIikgaWYgZGF0ZV9zdHIgYW5kIGxlbihkYXRlX3N0cikgPj0gNCBlbHNlIGRhdGVfc3RyCgogICAgICAgICMgUGFyYSBjdXJyX3ByZXYgeSBwcmV2X3BlcmlvZCBlbiBsYSBGVUVOVEUsIGJ1c2NhciBwb3IgZWwgaW5pY2lvIGRlIGHDsW8gKCdZWVlZLTAxLTAxJykKICAgICAgICAjIGVuIGx1Z2FyIGRlbCBmaW4gZGVsIHBlcsOtb2RvICgnWVlZWS0wNi0zMCcpLiBBc8OtIHNlIGRpc3Rpbmd1ZSBsYSBjb2x1bW5hIGFjdW11bGFkYSBZVEQKICAgICAgICAjICgiMDEtMDEtMjAyNi8zMC0wNi0yMDI2IikgZGUgbGEgdHJpbWVzdHJhbCAoIjAxLTA0LTIwMjYvMzAtMDYtMjAyNiIpLCBxdWUgZW4gZWwKICAgICAgICAjIGFyY2hpdm8gZnVlbnRlIGFtYmFzIHRlcm1pbmFuIGVuIGxhIG1pc21hIGZlY2hhIHBlcm8gc29sbyBsYSBZVEQgY29udGllbmUgJzAxLTAxJy4KICAgICAgICBrd19jdXJyX3ByZXZfc3JjID0gX3llYXJfc3RhcnQoa3dfY3Vycl9wcmV2KQogICAgICAgIGt3X3ByZXZfc3JjICAgICAgPSBfeWVhcl9zdGFydChrd19wcmV2KQoKICAgICAgICAjIE1hcGVvIHRpcG8g4oaSIChrZXl3b3JkIGRldGVjY2nDs24gZW4gZGVzdGlubywgYXJjaGl2byBmdWVudGUsIGtleXdvcmQgYsO6c3F1ZWRhIGVuIGZ1ZW50ZSkKICAgICAgICAjIE9yZGVuIGRlIHByaW9yaWRhZDogcXVhcnRlciBwcmltZXJvIChtw6FzIGVzcGVjw61maWNvKSwgbHVlZ28gZWVyciwgcHJldl9wZXJpb2QsIGJhbAogICAgICAgIFRZUEVfTUFQID0gWwogICAgICAgICAgICAoInF1YXJ0ZXIiLCAgICAga3dfcXVhcnRlciwgICBzcmNfZWVycl9pZCwgICAgICAgc3JjX3NoZWV0c19lZXJyLCAgICAgIGt3X3F1YXJ0ZXIpLAogICAgICAgICAgICAoImVlcnIiLCAgICAgICAga3dfZWVyciwgICAgICBzcmNfZWVycl9pZCwgICAgICAgc3JjX3NoZWV0c19lZXJyLCAgICAgIGt3X2VlcnJfc3JjKSwKICAgICAgICAgICAgKCJjdXJyX3ByZXYiLCAgIGt3X2N1cnJfcHJldiwgc3JjX2N1cnJfcHJldl9pZCwgIHNyY19zaGVldHNfY3Vycl9wcmV2LCBrd19jdXJyX3ByZXZfc3JjKSwKICAgICAgICAgICAgIyBiYWwgYW50ZXMgcXVlIHByZXZfcGVyaW9kOiBhbWJvcyB1c2FuICIyMDI1LTEyLTMxIiBjb21vIGtleXdvcmQ7CiAgICAgICAgICAgICMgc2kgcHJldl9wZXJpb2QgdmEgcHJpbWVybywgcmVjbGFtYSBsYSBjb2x1bW5hIERpYyB5IGJhbCBudW5jYSBzZSBwcm9jZXNhLgogICAgICAgICAgICAjIENvbiBiYWwgcHJpbWVybywgdG9tYSBsYSBjb2x1bW5hIHkgbGVlIGRlbCBwZXLDrW9kbyBhbnRlcmlvciAoUTEgcGFyYSBRMiwgZXRjLikuCiAgICAgICAgICAgICgiYmFsIiwgICAgICAgICBrd19iYWwsCiAgICAgICAgICAgICBzcmNfY3Vycl9wcmV2X2lkICBvciBzcmNfYmFsYW5jZV9pZCwKICAgICAgICAgICAgIHNyY19zaGVldHNfY3Vycl9wcmV2IGlmIHNyY19jdXJyX3ByZXZfaWQgZWxzZSBzcmNfc2hlZXRzX2JhbCwKICAgICAgICAgICAgIGt3X2JhbCksCiAgICAgICAgICAgICgicHJldl9wZXJpb2QiLCBrd19wcmV2LCAgICAgIHNyY19wcmV2X2lkLCAgICAgICBzcmNfc2hlZXRzX3ByZXYsICAgICAga3dfcHJldl9zcmMpLAogICAgICAgIF0KCiAgICAgICAgZGVmIF9maW5kX3NyY19jb2woc3JjX2NlbGxzOiBsaXN0W2xpc3RdLCBrdzogc3RyKSAtPiBpbnQgfCBOb25lOgogICAgICAgICAgICAiIiJCdXNjYSBlbiBsYXMgcHJpbWVyYXMgOCBmaWxhcyBsYSBwcmltZXJhIGNvbHVtbmEgY3V5byBoZWFkZXIgY29udGVuZ2Ega3cuIiIiCiAgICAgICAgICAgIGlmIG5vdCBrdzoKICAgICAgICAgICAgICAgIHJldHVybiBOb25lCiAgICAgICAgICAgIGZvciByb3cgaW4gc3JjX2NlbGxzWzo4XToKICAgICAgICAgICAgICAgIGZvciBqLCBjZWxsIGluIGVudW1lcmF0ZShyb3cpOgogICAgICAgICAgICAgICAgICAgIGlmIG5vdCBpc2luc3RhbmNlKGNlbGwsIGRpY3QpOgogICAgICAgICAgICAgICAgICAgICAgICBjb250aW51ZQogICAgICAgICAgICAgICAgICAgIGZvciB2YWxfa2V5IGluICgiY2FsY3VsYXRlZFZhbHVlIiwgInZhbHVlIik6CiAgICAgICAgICAgICAgICAgICAgICAgIHYgPSBzdHIoY2VsbC5nZXQodmFsX2tleSwgIiIpIG9yICIiKS5sb3dlcigpCiAgICAgICAgICAgICAgICAgICAgICAgIGlmIGt3IGluIHY6CiAgICAgICAgICAgICAgICAgICAgICAgICAgICByZXR1cm4gagogICAgICAgICAgICByZXR1cm4gTm9uZQoKICAgICAgICBkZWYgX2ZpbmRfc3JjX2NvbF9udGgoc3JjX2NlbGxzOiBsaXN0W2xpc3RdLCBrdzogc3RyLCBuOiBpbnQpIC0+IGludCB8IE5vbmU6CiAgICAgICAgICAgICIiIkJ1c2NhIGxhIE4tw6lzaW1hIGNvbHVtbmEgKDAtYmFzZWQpIGN1eW8gaGVhZGVyIGNvbnRlbmdhIGt3IGVuIGxhcyBwcmltZXJhcyA4IGZpbGFzLiIiIgogICAgICAgICAgICBpZiBub3Qga3c6CiAgICAgICAgICAgICAgICByZXR1cm4gTm9uZQogICAgICAgICAgICBzZWVuX2NvbHM6IGxpc3RbaW50XSA9IFtdCiAgICAgICAgICAgIHNlZW5fc2V0OiBzZXRbaW50XSA9IHNldCgpCiAgICAgICAgICAgIGZvciByb3cgaW4gc3JjX2NlbGxzWzo4XToKICAgICAgICAgICAgICAgIGZvciBqLCBjZWxsIGluIGVudW1lcmF0ZShyb3cpOgogICAgICAgICAgICAgICAgICAgIGlmIGogaW4gc2Vlbl9zZXQgb3Igbm90IGlzaW5zdGFuY2UoY2VsbCwgZGljdCk6CiAgICAgICAgICAgICAgICAgICAgICAgIGNvbnRpbnVlCiAgICAgICAgICAgICAgICAgICAgZm9yIHZhbF9rZXkgaW4gKCJjYWxjdWxhdGVkVmFsdWUiLCAidmFsdWUiKToKICAgICAgICAgICAgICAgICAgICAgICAgdiA9IHN0cihjZWxsLmdldCh2YWxfa2V5LCAiIikgb3IgIiIpLmxvd2VyKCkKICAgICAgICAgICAgICAgICAgICAgICAgaWYga3cgaW4gdjoKICAgICAgICAgICAgICAgICAgICAgICAgICAgIHNlZW5fY29scy5hcHBlbmQoaikKICAgICAgICAgICAgICAgICAgICAgICAgICAgIHNlZW5fc2V0LmFkZChqKQogICAgICAgICAgICAgICAgICAgICAgICAgICAgYnJlYWsKICAgICAgICAgICAgcmV0dXJuIHNlZW5fY29sc1tuXSBpZiBuIDwgbGVuKHNlZW5fY29scykgZWxzZSAoc2Vlbl9jb2xzWy0xXSBpZiBzZWVuX2NvbHMgZWxzZSBOb25lKQoKICAgICAgICBkZWYgX2ZpbmRfc2VnbWVudF9sYWJlbChhbGxfcm93czogbGlzdCwgY29sX2o6IGludCwgaGVhZGVyX3JvdzogaW50KSAtPiBzdHI6CiAgICAgICAgICAgICIiIgogICAgICAgICAgICBEZXRlY3RhIGVsIG5vbWJyZSBkZSBzZWdtZW50byBxdWUgInBvc2VlIiBsYSBjb2x1bW5hIGNvbF9qLgogICAgICAgICAgICBCdXNjYSBlbiBsYXMgZmlsYXMgYW50ZXJpb3JlcyBhbCBoZWFkZXIgZGUgZmVjaGEgKGhlYWRlcl9yb3cpCiAgICAgICAgICAgIGVzY2FuZWFuZG8gaGFjaWEgbGEgaXpxdWllcmRhIGRlc2RlIGNvbF9qIGhhc3RhIGVuY29udHJhciB1bmEKICAgICAgICAgICAgY2VsZGEgY29uIHRleHRvIG5vLXZhY8OtbyBxdWUgbm8gc2VhIHVuYSBmZWNoYSBuaSBNJC4KICAgICAgICAgICAgIiIiCiAgICAgICAgICAgIF9za2lwID0geyJtJCIsICIlIiwgIiJ9CiAgICAgICAgICAgIF9kYXRlX3JlID0gcmUuY29tcGlsZShyIlxkezR9LVxkezJ9LVxkezJ9fFxkezJ9LVxkezR9fFxkezR9L1xkezJ9L1xkezJ9IikKICAgICAgICAgICAgZm9yIHJpIGluIHJhbmdlKGhlYWRlcl9yb3cgLSAxLCAtMSwgLTEpOgogICAgICAgICAgICAgICAgcm93ID0gYWxsX3Jvd3NbcmldCiAgICAgICAgICAgICAgICBmb3IgamogaW4gcmFuZ2UoY29sX2osIC0xLCAtMSk6CiAgICAgICAgICAgICAgICAgICAgaWYgamogPj0gbGVuKHJvdyk6CiAgICAgICAgICAgICAgICAgICAgICAgIGNvbnRpbnVlCiAgICAgICAgICAgICAgICAgICAgY2VsbCA9IHJvd1tqal0KICAgICAgICAgICAgICAgICAgICBpZiBub3QgaXNpbnN0YW5jZShjZWxsLCBkaWN0KToKICAgICAgICAgICAgICAgICAgICAgICAgY29udGludWUKICAgICAgICAgICAgICAgICAgICBmb3IgdmsgaW4gKCJjYWxjdWxhdGVkVmFsdWUiLCAidmFsdWUiKToKICAgICAgICAgICAgICAgICAgICAgICAgcmF3ID0gc3RyKGNlbGwuZ2V0KHZrLCAiIikgb3IgIiIpLnN0cmlwKCkKICAgICAgICAgICAgICAgICAgICAgICAgbG8gID0gcmF3Lmxvd2VyKCkKICAgICAgICAgICAgICAgICAgICAgICAgIyAidmFsdWUiIGVzIGxhIGbDs3JtdWxhIGNydWRhIChlai4gIj0nQmFzZXMnIUYxNiIpOiBudW5jYQogICAgICAgICAgICAgICAgICAgICAgICAjIHNpcnZlIGNvbW8gbm9tYnJlIGRlIHNlZ21lbnRvLCBhdW5xdWUgY2FsY3VsYXRlZFZhbHVlCiAgICAgICAgICAgICAgICAgICAgICAgICMgZXN0w6kgdmFjw61vLiBVc2FybGEgcm9tcMOtYSBsYSBkZXRlY2Npw7NuIChjYcOtYSBhCiAgICAgICAgICAgICAgICAgICAgICAgICMgYnVzY2FyIHBvciBwb3NpY2nDs24geSBhZ2FycmFiYSBsYSBjb2x1bW5hIHZlY2luYSkuCiAgICAgICAgICAgICAgICAgICAgICAgIGlmIHZrID09ICJ2YWx1ZSIgYW5kIGxvLnN0YXJ0c3dpdGgoIj0iKToKICAgICAgICAgICAgICAgICAgICAgICAgICAgIGNvbnRpbnVlCiAgICAgICAgICAgICAgICAgICAgICAgIGlmIGxvIGluIF9za2lwIG9yIF9kYXRlX3JlLnNlYXJjaChsbyk6CiAgICAgICAgICAgICAgICAgICAgICAgICAgICBjb250aW51ZQogICAgICAgICAgICAgICAgICAgICAgICAjIE5vbWJyZXMgZGUgc2VnbWVudG8gcmVhbGVzIHNvbiBjb3J0b3MgKHNvY2llZGFkLAogICAgICAgICAgICAgICAgICAgICAgICAjIGNhdGVnb3LDrWE6ICJQYXRlbnRlcywgbWFyY2FzIHJlZ2lzdHJhZGFzIHkgb3Ryb3MKICAgICAgICAgICAgICAgICAgICAgICAgIyBkZXJlY2hvcyIgfjcgcGFsYWJyYXMpLiBMYXMgZGVzY3JpcGNpb25lcyBvZmljaWFsZXMKICAgICAgICAgICAgICAgICAgICAgICAgIyBkZSBub3RhIChlai4gImzDrW5lYSBkZSBwYXJ0aWRhIGVuIGVsIGVzdGFkbyBkZQogICAgICAgICAgICAgICAgICAgICAgICAjIHJlc3VsdGFkb3MgcXVlIGluY2x1eWUgYW1vcnRpemFjacOzbi4uLiIpIHNvbgogICAgICAgICAgICAgICAgICAgICAgICAjIG9yYWNpb25lcyBsYXJnYXMgcXVlIE5PIHNvbiBzZWdtZW50b3Mg4oCUIHNpIHNlCiAgICAgICAgICAgICAgICAgICAgICAgICMgYWNlcHRhbiwgc2UgY29uZnVuZGVuIGNvbiBub21icmVzIGRlIHNlZ21lbnRvIHkKICAgICAgICAgICAgICAgICAgICAgICAgIyByb21wZW4gbGEgYsO6c3F1ZWRhIGVuIGVsIGFyY2hpdm8gZnVlbnRlLgogICAgICAgICAgICAgICAgICAgICAgICBpZiBsZW4ocmF3KSA+PSAzIGFuZCBsZW4obG8uc3BsaXQoKSkgPD0gODoKICAgICAgICAgICAgICAgICAgICAgICAgICAgIHJldHVybiBsbwogICAgICAgICAgICByZXR1cm4gIiIKCiAgICAgICAgZGVmIF9uZXh0X2NvbXBhbmlvbl9jb2xfaW5fc3JjKHNyY19jZWxsczogbGlzdFtsaXN0XSwgcGFyZW50X2NvbDogaW50LCBuOiBpbnQgPSAxKSAtPiBpbnQgfCBOb25lOgogICAgICAgICAgICAiIiJDb21wYW5pb24gZW4gZnVlbnRlOiBzaWd1aWVudGUgY29sIGJham8gZWwgbWlzbW8gcGVyw61vZG8gZGUgZmVjaGEgcXVlIHBhcmVudF9jb2wuCiAgICAgICAgICAgIEFjZXB0YSBjb2xzIHNpbiBmZWNoYSAobWVyZ2UpIE8gY29uIGxhIG1pc21hIGZlY2hhIHF1ZSBlbCBwYWRyZSAobm8gbWVyZ2UpLgogICAgICAgICAgICBQYXJhIHNpIGhheSB1bmEgZmVjaGEgRElGRVJFTlRFIChudWV2byBwZXLDrW9kbykuIiIiCiAgICAgICAgICAgIF9kcCA9IHJlLmNvbXBpbGUociJcZHs0fS1cZHsyfS1cZHsyfXxcZHsyfS1cZHs0fSIpCiAgICAgICAgICAgIGRlZiBfY29sX2RhdGVzKGNvbCk6CiAgICAgICAgICAgICAgICBkYXRlcyA9IHNldCgpCiAgICAgICAgICAgICAgICBmb3Igcm93IGluIHNyY19jZWxsc1s6OF06CiAgICAgICAgICAgICAgICAgICAgaWYgY29sIDwgbGVuKHJvdyk6CiAgICAgICAgICAgICAgICAgICAgICAgIGN2ID0gc3RyKHJvd1tjb2xdLmdldCgiY2FsY3VsYXRlZFZhbHVlIikgb3Igcm93W2NvbF0uZ2V0KCJ2YWx1ZSIpIG9yICIiKSBpZiBpc2luc3RhbmNlKHJvd1tjb2xdLCBkaWN0KSBlbHNlICIiCiAgICAgICAgICAgICAgICAgICAgICAgIGZvciBtIGluIF9kcC5maW5kYWxsKGN2KToKICAgICAgICAgICAgICAgICAgICAgICAgICAgIGRhdGVzLmFkZChtKQogICAgICAgICAgICAgICAgcmV0dXJuIGRhdGVzCiAgICAgICAgICAgIHBhcmVudF9kYXRlcyA9IF9jb2xfZGF0ZXMocGFyZW50X2NvbCkKICAgICAgICAgICAgZm91bmQgPSAwCiAgICAgICAgICAgIGNvbCA9IHBhcmVudF9jb2wgKyAxCiAgICAgICAgICAgIHdoaWxlIGNvbCA8IHBhcmVudF9jb2wgKyAyMDoKICAgICAgICAgICAgICAgIGNvbF9kYXRlcyA9IF9jb2xfZGF0ZXMoY29sKQogICAgICAgICAgICAgICAgIyBTaSB0aWVuZSBmZWNoYXMgZGlzdGludGFzIGFsIHBhZHJlIOKGkiBudWV2byBwZXLDrW9kbywgcGFyYXIKICAgICAgICAgICAgICAgIGlmIGNvbF9kYXRlcyBhbmQgbm90IGNvbF9kYXRlcy5pc3N1YnNldChwYXJlbnRfZGF0ZXMpOgogICAgICAgICAgICAgICAgICAgIGJyZWFrCiAgICAgICAgICAgICAgICAjIENvbXBhbmlvbjogdGllbmUgTSQgKG8gImVmZWN0byIgZW4gc3ViLWVuY2FiZXphZG8pCiAgICAgICAgICAgICAgICBoYXNfbXMgPSBhbnkoCiAgICAgICAgICAgICAgICAgICAgc3RyKHJvd1tjb2xdLmdldCgiY2FsY3VsYXRlZFZhbHVlIikgb3Igcm93W2NvbF0uZ2V0KCJ2YWx1ZSIpIG9yICIiKS5zdHJpcCgpLmxvd2VyKCkgaW4gKCJtJCIsICIkIikgaWYgaXNpbnN0YW5jZShyb3dbY29sXSwgZGljdCkgZWxzZSBGYWxzZQogICAgICAgICAgICAgICAgICAgIGZvciByb3cgaW4gc3JjX2NlbGxzWzoxMl0gaWYgY29sIDwgbGVuKHJvdykKICAgICAgICAgICAgICAgICkKICAgICAgICAgICAgICAgIGhhc19lZmVjdG8gPSBhbnkoCiAgICAgICAgICAgICAgICAgICAgImVmZWN0byIgaW4gc3RyKHJvd1tjb2xdLmdldCgiY2FsY3VsYXRlZFZhbHVlIikgb3Igcm93W2NvbF0uZ2V0KCJ2YWx1ZSIpIG9yICIiKS5sb3dlcigpIGlmIGlzaW5zdGFuY2Uocm93W2NvbF0sIGRpY3QpIGVsc2UgRmFsc2UKICAgICAgICAgICAgICAgICAgICBmb3Igcm93IGluIHNyY19jZWxsc1s1OjEzXSBpZiBjb2wgPCBsZW4ocm93KQogICAgICAgICAgICAgICAgKQogICAgICAgICAgICAgICAgaWYgaGFzX21zIG9yIGhhc19lZmVjdG86CiAgICAgICAgICAgICAgICAgICAgZm91bmQgKz0gMQogICAgICAgICAgICAgICAgICAgIGlmIGZvdW5kID49IG46CiAgICAgICAgICAgICAgICAgICAgICAgIHJldHVybiBjb2wKICAgICAgICAgICAgICAgIGNvbCArPSAxCiAgICAgICAgICAgIHJldHVybiBOb25lCgogICAgICAgICMgUGFsYWJyYXMgcXVlIGludmllcnRlbiBlbCBzZW50aWRvIGRlIHVuIHNlZ21lbnRvLiBTaSBsYSBkaWZlcmVuY2lhCiAgICAgICAgIyBlbnRyZSBkb3MgZXRpcXVldGFzIHNlIHJlZHVjZSBhIHVuYSBkZSBlc3RhcywgTk8gc29uIGVsIG1pc21vCiAgICAgICAgIyBzZWdtZW50byBwb3IgbcOhcyBxdWUgdW5hIGNvbnRlbmdhIGEgbGEgb3RyYS4KICAgICAgICBfTkVHQUNJT05FUyA9IHsibm8iLCAibm9uIiwgInNpbiJ9CgogICAgICAgIGRlZiBfZmluZF9zcmNfY29sX2J5X3NlZ21lbnQoCiAgICAgICAgICAgIHNyY19jZWxsczogbGlzdFtsaXN0XSwga3dfc3JjOiBzdHIsIHNlZ21lbnRfbGFiZWw6IHN0ciwKICAgICAgICAgICAgb2NjdXJyZW5jZV9pbmRleDogaW50ID0gMAogICAgICAgICkgLT4gaW50IHwgTm9uZToKICAgICAgICAgICAgIiIiCiAgICAgICAgICAgIEJ1c2NhIGVuIGVsIGZ1ZW50ZSBsYSBjb2x1bW5hIHF1ZSAoYSkgZXN0w6EgYmFqbyBlbCBtaXNtbyBzZWdtZW50bwogICAgICAgICAgICB5IChiKSBjb250aWVuZSBrd19zcmMgZW4gZWwgZW5jYWJlemFkby4KICAgICAgICAgICAgU2kgbm8gaGF5IHNlZ21lbnRvIG8gbm8gc2UgZW5jdWVudHJhLCB1c2Egw61uZGljZSBkZSBvY3VycmVuY2lhIChOdGggbWF0Y2gpLgogICAgICAgICAgICAiIiIKICAgICAgICAgICAgaWYgbm90IGt3X3NyYzoKICAgICAgICAgICAgICAgIHJldHVybiBOb25lCiAgICAgICAgICAgIGlmIG5vdCBzZWdtZW50X2xhYmVsOgogICAgICAgICAgICAgICAgIyBVc2FyIMOtbmRpY2UgZGUgb2N1cnJlbmNpYSAobm8gaWdub3JhcmxvIGNvbW8gaGFjw61hIF9maW5kX3NyY19jb2wpCiAgICAgICAgICAgICAgICByZXN1bHQgPSBfZmluZF9zcmNfY29sX250aChzcmNfY2VsbHMsIGt3X3NyYywgb2NjdXJyZW5jZV9pbmRleCkKICAgICAgICAgICAgICAgIGlmIHJlc3VsdCBpcyBOb25lIGFuZCBvY2N1cnJlbmNlX2luZGV4ID4gMDoKICAgICAgICAgICAgICAgICAgICBiYXNlX2NvbCA9IF9maW5kX3NyY19jb2xfbnRoKHNyY19jZWxscywga3dfc3JjLCAwKQogICAgICAgICAgICAgICAgICAgIGlmIGJhc2VfY29sIGlzIG5vdCBOb25lOgogICAgICAgICAgICAgICAgICAgICAgICByZXN1bHQgPSBiYXNlX2NvbCArIG9jY3VycmVuY2VfaW5kZXgKICAgICAgICAgICAgICAgIHJldHVybiByZXN1bHQKCiAgICAgICAgICAgIF9kYXRlX3JlID0gcmUuY29tcGlsZShyIlxkezR9LVxkezJ9LVxkezJ9fFxkezJ9LVxkezR9fFxkezR9L1xkezJ9L1xkezJ9IikKICAgICAgICAgICAgX3NraXAgPSB7Im0kIiwgIiUiLCAiIn0KCiAgICAgICAgICAgICMgUGFzbyAxOiBlbmNvbnRyYXIgdG9kYXMgbGFzIGNvbHVtbmFzIGRlIGluaWNpbyBkZSBzZWdtZW50byBlbiBlbCBmdWVudGUKICAgICAgICAgICAgIyBVbiAiaW5pY2lvIGRlIHNlZ21lbnRvIiBlcyB1bmEgY2VsZGEgY29uIHRleHRvIG5vLWZlY2hhIGVuIGxhcyBwcmltZXJhcyA4IGZpbGFzCiAgICAgICAgICAgIHNlZ19zdGFydHM6IGxpc3RbdHVwbGVbaW50LCBpbnQsIHN0cl1dID0gW10gICMgKGZpbGEsIGNvbCwgbGFiZWwpCiAgICAgICAgICAgIGZvciByaSwgcm93IGluIGVudW1lcmF0ZShzcmNfY2VsbHNbOjhdKToKICAgICAgICAgICAgICAgIGZvciBqaiwgY2VsbCBpbiBlbnVtZXJhdGUocm93KToKICAgICAgICAgICAgICAgICAgICBpZiBub3QgaXNpbnN0YW5jZShjZWxsLCBkaWN0KToKICAgICAgICAgICAgICAgICAgICAgICAgY29udGludWUKICAgICAgICAgICAgICAgICAgICBmb3IgdmsgaW4gKCJjYWxjdWxhdGVkVmFsdWUiLCAidmFsdWUiKToKICAgICAgICAgICAgICAgICAgICAgICAgcmF3ID0gc3RyKGNlbGwuZ2V0KHZrLCAiIikgb3IgIiIpLnN0cmlwKCkKICAgICAgICAgICAgICAgICAgICAgICAgbG8gID0gcmF3Lmxvd2VyKCkKICAgICAgICAgICAgICAgICAgICAgICAgaWYgbG8gaW4gX3NraXAgb3IgX2RhdGVfcmUuc2VhcmNoKGxvKSBvciBsZW4ocmF3KSA8IDM6CiAgICAgICAgICAgICAgICAgICAgICAgICAgICBjb250aW51ZQogICAgICAgICAgICAgICAgICAgICAgICBzZWdfc3RhcnRzLmFwcGVuZCgocmksIGpqLCBsbykpCgogICAgICAgICAgICAjIFBhc28gMjogZW5jb250cmFyIGN1w6FsIHNlZ21lbnRvIGRlbCBmdWVudGUgY29pbmNpZGUgY29uIHNlZ21lbnRfbGFiZWwKICAgICAgICAgICAgIyBTb2xvIHVzYXIgc2VnX3N0YXJ0cyBzaSBsb3MgdmFsb3JlcyBzb24gdGV4dG8gcmVhbCAobm8gZsOzcm11bGFzKQogICAgICAgICAgICByZWFsX3NlZ3MgPSBbKHJpLCBqaiwgbGJsKSBmb3IgcmksIGpqLCBsYmwgaW4gc2VnX3N0YXJ0cwogICAgICAgICAgICAgICAgICAgICAgICAgaWYgbm90IGxibC5zdGFydHN3aXRoKCI9IildCgogICAgICAgICAgICAjIENhbmRpZGF0b3MgZGUgY29sdW1uYSBkZSBpbmljaW8gZGUgc2VnbWVudG8gcXVlIGNhbHphbiBjb24KICAgICAgICAgICAgIyBzZWdtZW50X2xhYmVsLCBlbiBvcmRlbiAocHVlZGUgaGFiZXIgdmFyaW9zOiBsYSBtaXNtYSBldGlxdWV0YQogICAgICAgICAgICAjIGRlIHNlZ21lbnRvIHNlIHJlcGl0ZSB1bmEgdmV6IHBvciBjYWRhIGJsb3F1ZSBkZSBmZWNoYSwgZWouCiAgICAgICAgICAgICMgIlByb2dyYW1hcyBpbmZvcm3DoXRpY29zIiBiYWpvIEQsIGJham8gSCwgYmFqbyBMLi4uKS4KICAgICAgICAgICAgZXhhY3RfY2FuZGlkYXRlczogbGlzdFtpbnRdID0gW2pqIGZvciBfLCBqaiwgbGJsIGluIHJlYWxfc2VncyBpZiBsYmwgPT0gc2VnbWVudF9sYWJlbF0KICAgICAgICAgICAgc3ViX2NhbmRpZGF0ZXM6IGxpc3RbaW50XSA9IFtdCiAgICAgICAgICAgIGlmIG5vdCBleGFjdF9jYW5kaWRhdGVzOgogICAgICAgICAgICAgICAgZm9yIF8sIGpqLCBsYmwgaW4gcmVhbF9zZWdzOgogICAgICAgICAgICAgICAgICAgIGlmIHNlZ21lbnRfbGFiZWwgbm90IGluIGxibCBhbmQgbGJsIG5vdCBpbiBzZWdtZW50X2xhYmVsOgogICAgICAgICAgICAgICAgICAgICAgICBjb250aW51ZQogICAgICAgICAgICAgICAgICAgIGlmIF9ORUdBQ0lPTkVTICYgKHNldChsYmwuc3BsaXQoKSkgXiBzZXQoc2VnbWVudF9sYWJlbC5zcGxpdCgpKSk6CiAgICAgICAgICAgICAgICAgICAgICAgIGNvbnRpbnVlCiAgICAgICAgICAgICAgICAgICAgc3ViX2NhbmRpZGF0ZXMuYXBwZW5kKGpqKQoKICAgICAgICAgICAgZGVmIF9rd19zcmNfY29sX2luX3JhbmdlKHN0YXJ0OiBpbnQsIGVuZDogaW50KSAtPiBpbnQgfCBOb25lOgogICAgICAgICAgICAgICAgZm9yIHJvdyBpbiBzcmNfY2VsbHNbOjhdOgogICAgICAgICAgICAgICAgICAgIGZvciBqaiBpbiByYW5nZShzdGFydCwgbWluKGVuZCwgbGVuKHJvdykpKToKICAgICAgICAgICAgICAgICAgICAgICAgY2VsbCA9IHJvd1tqal0KICAgICAgICAgICAgICAgICAgICAgICAgaWYgbm90IGlzaW5zdGFuY2UoY2VsbCwgZGljdCk6CiAgICAgICAgICAgICAgICAgICAgICAgICAgICBjb250aW51ZQogICAgICAgICAgICAgICAgICAgICAgICBmb3IgdmsgaW4gKCJjYWxjdWxhdGVkVmFsdWUiLCAidmFsdWUiKToKICAgICAgICAgICAgICAgICAgICAgICAgICAgIHYgPSBzdHIoY2VsbC5nZXQodmssICIiKSBvciAiIikubG93ZXIoKQogICAgICAgICAgICAgICAgICAgICAgICAgICAgaWYga3dfc3JjIGluIHY6CiAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgcmV0dXJuIGpqCiAgICAgICAgICAgICAgICByZXR1cm4gTm9uZQoKICAgICAgICAgICAgZm9yIGNhbmRpZGF0ZXMgaW4gKGV4YWN0X2NhbmRpZGF0ZXMsIHN1Yl9jYW5kaWRhdGVzKToKICAgICAgICAgICAgICAgIGlmIG5vdCBjYW5kaWRhdGVzOgogICAgICAgICAgICAgICAgICAgIGNvbnRpbnVlCiAgICAgICAgICAgICAgICAjIFBhc28gMzogZGVudHJvIGRlIENBREEgY2FuZGlkYXRvIGRlIHNlZ21lbnRvICh1bm8gcG9yIGJsb3F1ZQogICAgICAgICAgICAgICAgIyBkZSBmZWNoYSksIGJ1c2NhciBrd19zcmMgKGZlY2hhKS4gU29sbyB1biBibG9xdWUgZGUgZmVjaGEKICAgICAgICAgICAgICAgICMgdGVuZHLDoSBlc2EgZmVjaGEgZW4gc3UgcmFuZ28gZGUgY29sdW1uYXMg4oCUIGFzw60gc2UgZXZpdGEKICAgICAgICAgICAgICAgICMgbWV6Y2xhciBibG9xdWVzIHF1ZSBjb21wYXJ0ZW4gZWwgbWlzbW8gbm9tYnJlIGRlIHNlZ21lbnRvLgogICAgICAgICAgICAgICAgZm9yIG1hdGNoZWRfY29sIGluIGNhbmRpZGF0ZXM6CiAgICAgICAgICAgICAgICAgICAgbmV4dF9zZWdfY29sID0gbWluKAogICAgICAgICAgICAgICAgICAgICAgICAoamogZm9yIF8sIGpqLCBfIGluIHJlYWxfc2VncyBpZiBqaiA+IG1hdGNoZWRfY29sKSwKICAgICAgICAgICAgICAgICAgICAgICAgZGVmYXVsdD05OTk5CiAgICAgICAgICAgICAgICAgICAgKQogICAgICAgICAgICAgICAgICAgIGZvdW5kID0gX2t3X3NyY19jb2xfaW5fcmFuZ2UobWF0Y2hlZF9jb2wsIG5leHRfc2VnX2NvbCkKICAgICAgICAgICAgICAgICAgICBpZiBmb3VuZCBpcyBub3QgTm9uZToKICAgICAgICAgICAgICAgICAgICAgICAgcmV0dXJuIGZvdW5kCgogICAgICAgICAgICAjIFNlZ21lbnRvIG5vIGVuY29udHJhZG8gbyBzaW4gdGV4dG8gcmVhbCDihpIgdXNhciDDrW5kaWNlIGRlIG9jdXJyZW5jaWEuCiAgICAgICAgICAgICMgU2kgbGEgTnRoIG9jdXJyZW5jaWEgbm8gZXhpc3RlIChjZWxkYXMgZnVzaW9uYWRhczogc29sbyBsYSAxcmEgdGllbmUgZmVjaGEpLAogICAgICAgICAgICAjIGZhbGxiYWNrOiBjb2wgZGUgb2NjPTAgKyBvZmZzZXQgKGNvbHVtbmFzIGNvbnRpZ3VhcyBkZW50cm8gZGVsIG1pc21vIG1lcmdlKS4KICAgICAgICAgICAgcmVzdWx0ID0gX2ZpbmRfc3JjX2NvbF9udGgoc3JjX2NlbGxzLCBrd19zcmMsIG9jY3VycmVuY2VfaW5kZXgpCiAgICAgICAgICAgIGlmIHJlc3VsdCBpcyBOb25lIGFuZCBvY2N1cnJlbmNlX2luZGV4ID4gMDoKICAgICAgICAgICAgICAgIGJhc2VfY29sID0gX2ZpbmRfc3JjX2NvbF9udGgoc3JjX2NlbGxzLCBrd19zcmMsIDApCiAgICAgICAgICAgICAgICBpZiBiYXNlX2NvbCBpcyBub3QgTm9uZToKICAgICAgICAgICAgICAgICAgICByZXN1bHQgPSBiYXNlX2NvbCArIG9jY3VycmVuY2VfaW5kZXgKICAgICAgICAgICAgcmV0dXJuIHJlc3VsdAoKICAgICAgICBjb21wX2NvbHNfYnlfbmFtZTogZGljdFtzdHIsIGxpc3RbZGljdF1dID0ge30KICAgICAgICBmb3Igc25hbWUgaW4gYmF0Y2g6CiAgICAgICAgICAgIGNvbXBfY29sczogbGlzdFtkaWN0XSA9IFtdCiAgICAgICAgICAgICMgY29sIC0+IGZpbGEgZG9uZGUgcXVlZMOzIHJlY2xhbWFkYS4gVW5hIGhvamEgcHVlZGUgdGVuZXIgdmFyaWFzCiAgICAgICAgICAgICMgc3ViLXRhYmxhcyBpbmRlcGVuZGllbnRlcyBxdWUgcmV1c2FuIGxhIG1pc21hIGxldHJhIGRlIGNvbHVtbmEKICAgICAgICAgICAgIyBjb24gdW4gc2lnbmlmaWNhZG8gZGlzdGludG8gKGVqLiBub3RhIDExNTogbGEgY29sdW1uYSBGIGVzCiAgICAgICAgICAgICMgImNvbXBhcmF0aXZvIEVFUlIiIGVuIGxhIHRhYmxhIGRlIGFycmliYSB5ICJzYWxkbyBwdW50dWFsCiAgICAgICAgICAgICMgMzEtMTItMjAyNSIgZW4gbGEgc3ViLXRhYmxhIGRlIGFiYWpvKS4gUG9yIGVzbyBOTyBlcyB1biBzZXQKICAgICAgICAgICAgIyBmaWpvOiB1bmEgY29sdW1uYSBzZSBwdWVkZSByZWNsYW1hciBkZSBudWV2byBzaSBlbCBudWV2byB1c28KICAgICAgICAgICAgIyBlc3TDoSBjbGFyYW1lbnRlIGVuIG90cm8gYmxvcXVlIChzZXBhcmFkbyBwb3IgMisgZmlsYXMgZW4gYmxhbmNvKS4KICAgICAgICAgICAgc2VlbjogZGljdFtpbnQsIGludF0gPSB7fQogICAgICAgICAgICBvY2N1cnJlbmNlX2NvdW50czogZGljdFt0dXBsZSwgaW50XSA9IHt9CiAgICAgICAgICAgIGRlZiBfZmlsYV9lbl9ibGFuY28ocm93OiBsaXN0KSAtPiBib29sOgogICAgICAgICAgICAgICAgIiIiVHJ1ZSBzaSBsYSBmaWxhIG5vIHRpZW5lIG5pbmfDum4gdGV4dG8gKHNlcGFyYWRvciBlbnRyZSB0YWJsYXMpLiIiIgogICAgICAgICAgICAgICAgZm9yIGNlbGwgaW4gcm93WzozMF06CiAgICAgICAgICAgICAgICAgICAgaWYgbm90IGlzaW5zdGFuY2UoY2VsbCwgZGljdCk6CiAgICAgICAgICAgICAgICAgICAgICAgIGNvbnRpbnVlCiAgICAgICAgICAgICAgICAgICAgdiA9IHN0cihjZWxsLmdldCgiY2FsY3VsYXRlZFZhbHVlIikgb3IgY2VsbC5nZXQoInZhbHVlIikgb3IgIiIpLnN0cmlwKCkKICAgICAgICAgICAgICAgICAgICBpZiB2OgogICAgICAgICAgICAgICAgICAgICAgICByZXR1cm4gRmFsc2UKICAgICAgICAgICAgICAgIHJldHVybiBUcnVlCgogICAgICAgICAgICBkZWYgX2Jsb3F1ZXNfZGlzdGludG9zKGZpbGFfYTogaW50LCBmaWxhX2I6IGludCkgLT4gYm9vbDoKICAgICAgICAgICAgICAgICIiIlRydWUgc2kgZW50cmUgZmlsYV9hIHkgZmlsYV9iIGhheSAyKyBmaWxhcyBlbiBibGFuY28gc2VndWlkYXMKICAgICAgICAgICAgICAgIChzZXBhcmFkb3IgcmVhbCBkZSB0YWJsYSwgbm8gc29sbyB1biBlc3BhY2lhZG9yKS4iIiIKICAgICAgICAgICAgICAgIGFsbF9yb3dzID0gdGd0X2NlbGxzX2J5X25hbWVbc25hbWVdCiAgICAgICAgICAgICAgICBpbmksIGZpbiA9IHNvcnRlZCgoZmlsYV9hLCBmaWxhX2IpKQogICAgICAgICAgICAgICAgYmxhbmNvcyA9IDAKICAgICAgICAgICAgICAgIGZvciBpIGluIHJhbmdlKGluaSArIDEsIGZpbik6CiAgICAgICAgICAgICAgICAgICAgaWYgX2ZpbGFfZW5fYmxhbmNvKGFsbF9yb3dzW2ldKToKICAgICAgICAgICAgICAgICAgICAgICAgYmxhbmNvcyArPSAxCiAgICAgICAgICAgICAgICAgICAgICAgIGlmIGJsYW5jb3MgPj0gMjoKICAgICAgICAgICAgICAgICAgICAgICAgICAgIHJldHVybiBUcnVlCiAgICAgICAgICAgICAgICAgICAgZWxzZToKICAgICAgICAgICAgICAgICAgICAgICAgYmxhbmNvcyA9IDAKICAgICAgICAgICAgICAgIHJldHVybiBGYWxzZQoKICAgICAgICAgICAgZm9yIGNvbF90eXBlLCBrd19kZXRlY3QsIHNyY19pZCwgc3JjX3NoLCBrd19zcmMgaW4gVFlQRV9NQVA6CiAgICAgICAgICAgICAgICBpZiBub3Qga3dfZGV0ZWN0IG9yIG5vdCBzcmNfaWQ6CiAgICAgICAgICAgICAgICAgICAgY29udGludWUKICAgICAgICAgICAgICAgIGFsbF9yb3dzID0gdGd0X2NlbGxzX2J5X25hbWVbc25hbWVdCiAgICAgICAgICAgICAgICAjIE5vdGFzIGNvbiBkb3MgdGFibGFzIGFwaWxhZGFzIHkgZXN0cnVjdHVyYSBOTyByZWxhY2lvbmFkYSAoZWouIHRhYmxhIGRlCiAgICAgICAgICAgICAgICAjIGVzdGUgcGVyw61vZG8gYXJyaWJhLCB0YWJsYSBkZWwgcGVyw61vZG8gYW50ZXJpb3IgInRhbCBjdWFsIHNlIHJlcG9ydMOzIgogICAgICAgICAgICAgICAgIyBhYmFqbykgcHVlZGVuIHJlcGV0aXIgcG9yIGNvaW5jaWRlbmNpYSBsYSBtaXNtYSBmZWNoYSBxdWUgYnVzY2EgZXN0ZQogICAgICAgICAgICAgICAgIyBjb2xfdHlwZSwgcGVybyBlbiB1bmEgY29sdW1uYSBkZSBsYSB0YWJsYSBkZSBhYmFqbyBxdWUgbm8gdGllbmUgbmFkYQogICAgICAgICAgICAgICAgIyBxdWUgdmVyLiBQYXJhIG5vIG1lemNsYXJsYXM6IHVuYSB2ZXogZW5jb250cmFkYSBsYSBwcmltZXJhIGNvaW5jaWRlbmNpYSwKICAgICAgICAgICAgICAgICMgZGVqYXIgZGUgYnVzY2FyIGNvbHVtbmFzIE5VRVZBUyBtw6FzIGFsbMOhIGRlIGxhIHByaW1lcmEgZmlsYSBlbiBibGFuY28KICAgICAgICAgICAgICAgICMgKHNlcGFyYWRvciBkZSB0YWJsYSkuIEVsIG1lY2FuaXNtbyBkZSAiZG9ibGUgc3ViLXRhYmxhIiAoc3ViMl9oZWFkZXJfcm93LAogICAgICAgICAgICAgICAgIyBtw6FzIGFiYWpvKSBzaWd1ZSBmdW5jaW9uYW5kbyBpZ3VhbDogYnVzY2EgZGVudHJvIGRlIGxhIE1JU01BIGNvbHVtbmEsCiAgICAgICAgICAgICAgICAjIG5vIHNlIHZlIGFmZWN0YWRvIHBvciBlc3RlIGzDrW1pdGUuCiAgICAgICAgICAgICAgICBkZWYgX2NvbF90aWVuZV9tc19jZXJjYShjb2w6IGludCwgZGVzZGVfZmlsYTogaW50KSAtPiBib29sOgogICAgICAgICAgICAgICAgICAgICIiIk0kIChvICQpIGVuIGFsZ3VuYSBkZSBsYXMgZmlsYXMgc2lndWllbnRlcyBkZSBlc2EgY29sdW1uYToKICAgICAgICAgICAgICAgICAgICBjb25maXJtYSBxdWUgZXMgdW5hIGNvbHVtbmEgZGUgZGF0b3MgcmVhbCwgbm8gdW5hIG1lbmNpw7NuCiAgICAgICAgICAgICAgICAgICAgc3VlbHRhIGRlIHVuYSBmZWNoYSBlbiBjdWFscXVpZXIgcGFydGUgZGUgbGEgaG9qYS4iIiIKICAgICAgICAgICAgICAgICAgICBmb3IgcnIgaW4gYWxsX3Jvd3NbZGVzZGVfZmlsYTpkZXNkZV9maWxhICsgOF06CiAgICAgICAgICAgICAgICAgICAgICAgIGlmIGNvbCA+PSBsZW4ocnIpIG9yIG5vdCBpc2luc3RhbmNlKHJyW2NvbF0sIGRpY3QpOgogICAgICAgICAgICAgICAgICAgICAgICAgICAgY29udGludWUKICAgICAgICAgICAgICAgICAgICAgICAgdiA9IHN0cihycltjb2xdLmdldCgiY2FsY3VsYXRlZFZhbHVlIikgb3IgcnJbY29sXS5nZXQoInZhbHVlIikgb3IgIiIpLnN0cmlwKCkubG93ZXIoKQogICAgICAgICAgICAgICAgICAgICAgICBpZiB2IGluICgibSQiLCAiJCIpOgogICAgICAgICAgICAgICAgICAgICAgICAgICAgcmV0dXJuIFRydWUKICAgICAgICAgICAgICAgICAgICByZXR1cm4gRmFsc2UKCiAgICAgICAgICAgICAgICBwcmltZXJfbWF0Y2hfcm93OiBpbnQgfCBOb25lID0gTm9uZQogICAgICAgICAgICAgICAgX2JsYW5jb3Nfc2VndWlkb3Nfc2NhbiA9IDAKICAgICAgICAgICAgICAgIGZpbl9ibG9xdWVfYWN0dWFsID0gbGVuKGFsbF9yb3dzKQogICAgICAgICAgICAgICAgaWR4X2luaWNpb19ibG9xdWUgPSBsZW4oY29tcF9jb2xzKQogICAgICAgICAgICAgICAgZm9yIGksIHJvdyBpbiBlbnVtZXJhdGUoYWxsX3Jvd3MpOgogICAgICAgICAgICAgICAgICAgIGlmIHByaW1lcl9tYXRjaF9yb3cgaXMgbm90IE5vbmUgYW5kIGkgPiBwcmltZXJfbWF0Y2hfcm93OgogICAgICAgICAgICAgICAgICAgICAgICBpZiBfZmlsYV9lbl9ibGFuY28ocm93KToKICAgICAgICAgICAgICAgICAgICAgICAgICAgIF9ibGFuY29zX3NlZ3VpZG9zX3NjYW4gKz0gMQogICAgICAgICAgICAgICAgICAgICAgICAgICAgaWYgX2JsYW5jb3Nfc2VndWlkb3Nfc2NhbiA+PSAyOgogICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgIGZpbl9ibG9xdWVfYWN0dWFsID0gaSAtIDEgICAjIG5vIGluY2x1aXIgZWwgMmRvIGJsYW5jbwogICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgIGJyZWFrCiAgICAgICAgICAgICAgICAgICAgICAgIGVsc2U6CiAgICAgICAgICAgICAgICAgICAgICAgICAgICBfYmxhbmNvc19zZWd1aWRvc19zY2FuID0gMAogICAgICAgICAgICAgICAgICAgICMgTcOhcyBhbGzDoSBkZSBmaWxhIDc6IHNvbG8gcHJvY2VzYXIgc2kgbGEga2V5d29yZCBhcGFyZWNlIGVuCiAgICAgICAgICAgICAgICAgICAgIyDiiaUyIGNlbGRhcyBkZSBlc3RhIGZpbGEgKGluZGljYSBjZWxkYSBmdXNpb25hZGEgPSBlbmNhYmV6YWRvIHJlYWwpCiAgICAgICAgICAgICAgICAgICAgIyBPIHNpLCBhdW5xdWUgYXBhcmV6Y2EgdW5hIHNvbGEgdmV6LCBlc2EgY29sdW1uYSB0aWVuZSAiTSQiIGNlcmNhCiAgICAgICAgICAgICAgICAgICAgIyAoY29uZmlybWEgZW5jYWJlemFkbyByZWFsIGF1bnF1ZSBsYSBmZWNoYSBzZWEgw7puaWNhIGVuIGxhIGZpbGEg4oCUCiAgICAgICAgICAgICAgICAgICAgIyBlai4gbGEgZmVjaGEgZGUgSU5JQ0lPIGRlIHVuIHRyaW1lc3RyZSBzb2xvIGFwYXJlY2UgZW4gc3UgcHJvcGlhCiAgICAgICAgICAgICAgICAgICAgIyBjb2x1bW5hLCBubyBzZSByZXBpdGUpLiBGaWxhcyAwLTc6IGFjZXB0YXIgaW5jbHVzbyBtYXRjaCDDum5pY28uCiAgICAgICAgICAgICAgICAgICAgaWYgaSA+PSA4OgogICAgICAgICAgICAgICAgICAgICAgICBtYXRjaGVzX2luX3JvdyA9IHN1bSgKICAgICAgICAgICAgICAgICAgICAgICAgICAgIDEgZm9yIGMgaW4gcm93CiAgICAgICAgICAgICAgICAgICAgICAgICAgICBpZiBpc2luc3RhbmNlKGMsIGRpY3QpIGFuZCBrd19kZXRlY3QgaW4gc3RyKAogICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgIGMuZ2V0KCJjYWxjdWxhdGVkVmFsdWUiKSBvciBjLmdldCgidmFsdWUiKSBvciAiIgogICAgICAgICAgICAgICAgICAgICAgICAgICAgKS5sb3dlcigpCiAgICAgICAgICAgICAgICAgICAgICAgICkKICAgICAgICAgICAgICAgICAgICAgICAgaWYgbWF0Y2hlc19pbl9yb3cgPCAyOgogICAgICAgICAgICAgICAgICAgICAgICAgICAgY29sc19jb25fbXMgPSBbCiAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgaiBmb3IgaiwgYyBpbiBlbnVtZXJhdGUocm93KQogICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgIGlmIGlzaW5zdGFuY2UoYywgZGljdCkKICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICBhbmQga3dfZGV0ZWN0IGluIHN0cihjLmdldCgiY2FsY3VsYXRlZFZhbHVlIikgb3IgYy5nZXQoInZhbHVlIikgb3IgIiIpLmxvd2VyKCkKICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICBhbmQgX2NvbF90aWVuZV9tc19jZXJjYShqLCBpKQogICAgICAgICAgICAgICAgICAgICAgICAgICAgXQogICAgICAgICAgICAgICAgICAgICAgICAgICAgaWYgbm90IGNvbHNfY29uX21zOgogICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgIGNvbnRpbnVlCiAgICAgICAgICAgICAgICAgICAgZm9yIGosIGNlbGwgaW4gZW51bWVyYXRlKHJvdyk6CiAgICAgICAgICAgICAgICAgICAgICAgIGlmIG5vdCBpc2luc3RhbmNlKGNlbGwsIGRpY3QpOgogICAgICAgICAgICAgICAgICAgICAgICAgICAgY29udGludWUKICAgICAgICAgICAgICAgICAgICAgICAgaWYgaiBpbiBzZWVuIGFuZCBub3QgX2Jsb3F1ZXNfZGlzdGludG9zKHNlZW5bal0sIGkpOgogICAgICAgICAgICAgICAgICAgICAgICAgICAgY29udGludWUKICAgICAgICAgICAgICAgICAgICAgICAgZm9yIHZhbF9rZXkgaW4gKCJjYWxjdWxhdGVkVmFsdWUiLCAidmFsdWUiKToKICAgICAgICAgICAgICAgICAgICAgICAgICAgIHYgPSBzdHIoY2VsbC5nZXQodmFsX2tleSwgIiIpIG9yICIiKS5sb3dlcigpCiAgICAgICAgICAgICAgICAgICAgICAgICAgICBpZiBrd19kZXRlY3QgaW4gdjoKICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICBpZiBwcmltZXJfbWF0Y2hfcm93IGlzIE5vbmU6CiAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgIHByaW1lcl9tYXRjaF9yb3cgPSBpCiAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgIyBTa2lwICUgY29sdW1uczogY2hlY2sgc3Vycm91bmRpbmcgcm93cyAowrE0KSBmb3IgIiUiIGxhYmVsCiAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgd2luX3MgPSBtYXgoMCwgaSAtIDQpCiAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgd2luX2UgPSBtaW4obGVuKGFsbF9yb3dzKSwgaSArIDUpCiAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgZGVmIF9jZWxsX3N0cihjZWxsX2QpOgogICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICBpZiBub3QgaXNpbnN0YW5jZShjZWxsX2QsIGRpY3QpOgogICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgcmV0dXJuICIiCiAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgIHJldHVybiBzdHIoCiAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICBjZWxsX2QuZ2V0KCJjYWxjdWxhdGVkVmFsdWUiKSBvcgogICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgY2VsbF9kLmdldCgidmFsdWUiKSBvciAiIgogICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICApLnN0cmlwKCkKICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAjIEJ1c2NhciAiJSIgc2llbXByZSBlbiBsYXMgcHJpbWVyYXMgMTAgZmlsYXMKICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAjIChkb25kZSBlc3TDoW4gbG9zIGVuY2FiZXphZG9zIE0kLyUpLAogICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICMgaW5kZXBlbmRpZW50ZW1lbnRlIGRlIGVuIHF1w6kgZmlsYSBzZSBkZXRlY3TDsyBsYSBmZWNoYS4KICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICBpc19wY3QgPSBhbnkoCiAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgIF9jZWxsX3N0cihyW2pdKSA9PSAiJSIKICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgZm9yIHIgaW4gYWxsX3Jvd3NbOjEwXQogICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICBpZiBqIDwgbGVuKHIpCiAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgKQogICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICMgRGV0ZWN0YXIgc2VnbWVudG8gaG9yaXpvbnRhbCAodGFibGFzIG11bHRpLXNlZ21lbnRvKQogICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgIHNlZ19sYWJlbCA9IF9maW5kX3NlZ21lbnRfbGFiZWwoYWxsX3Jvd3MsIGosIGkpCiAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgIyBDb2x1bW5hcyAiQ29udHJvbCI6IHZlcmlmaWNhY2nDs24gaW50ZXJuYSBkZSBjdWFkcmUsCiAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgIyBubyB1biBtb250byByZWFsIGRlIG5lZ29jaW8uIE5vIHNlIGNvbXBhcmFuL2VzY3JpYmVuLAogICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICMgaWd1YWwgcXVlIGxhcyBjb2x1bW5hcyAiJSIuCiAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgaXNfY29udHJvbCA9IF9ub3JtX2xibChzZWdfbGFiZWwpID09ICJjb250cm9sIgogICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgIGlmIG5vdCBpc19wY3QgYW5kIG5vdCBpc19jb250cm9sOgoKICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgIyBEZXRlY3RhciBkb2JsZSBzdWItdGFibGE6IGJ1c2NhciBzaSBsYSBtaXNtYQogICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAjIGtleXdvcmQgYXBhcmVjZSBkZSBudWV2byBlbiBsYSBtaXNtYSBjb2x1bW5hIGoKICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgIyBlbiBmaWxhcyBwb3N0ZXJpb3JlcyAoc3ViLXRhYmxhIGluZmVyaW9yKS4KICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgc3ViMl9oZWFkZXJfcm93ID0gTm9uZQogICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICBzdWIyX2RhdGFfc3RhcnQgPSBOb25lCiAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgIGZvciBpMiwgcm93MiBpbiBlbnVtZXJhdGUoYWxsX3Jvd3NbaSArIDE6XSwgc3RhcnQ9aSArIDEpOgogICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgY2VsbDIgPSByb3cyW2pdIGlmIGogPCBsZW4ocm93MikgZWxzZSBOb25lCiAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICBpZiBub3QgaXNpbnN0YW5jZShjZWxsMiwgZGljdCk6CiAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgY29udGludWUKICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgIGZvciB2azIgaW4gKCJjYWxjdWxhdGVkVmFsdWUiLCAidmFsdWUiKToKICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICB2MiA9IHN0cihjZWxsMi5nZXQodmsyLCAiIikgb3IgIiIpLmxvd2VyKCkKICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICBpZiBrd19kZXRlY3QgaW4gdjI6CiAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgIHN1YjJfaGVhZGVyX3JvdyA9IGkyCiAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgIGJyZWFrCiAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICBpZiBzdWIyX2hlYWRlcl9yb3cgaXMgbm90IE5vbmU6CiAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgYnJlYWsKICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgaWYgc3ViMl9oZWFkZXJfcm93IGlzIG5vdCBOb25lOgogICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgIyBFbmNvbnRyYXIgcHJpbWVyYSBmaWxhIGRlIGRhdG9zIHRyYXMgZWwgZW5jYWJlemFkbyBpbmZlcmlvcgogICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgZm9yIGkzIGluIHJhbmdlKHN1YjJfaGVhZGVyX3JvdyArIDEsIGxlbihhbGxfcm93cykpOgogICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgIGNlbGwzID0gYWxsX3Jvd3NbaTNdW2pdIGlmIGogPCBsZW4oYWxsX3Jvd3NbaTNdKSBlbHNlIE5vbmUKICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICBoYXNfa3czID0gaXNpbnN0YW5jZShjZWxsMywgZGljdCkgYW5kIGFueSgKICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAga3dfZGV0ZWN0IGluIHN0cihjZWxsMy5nZXQodmszLCAiIikgb3IgIiIpLmxvd2VyKCkKICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgZm9yIHZrMyBpbiAoImNhbGN1bGF0ZWRWYWx1ZSIsICJ2YWx1ZSIpCiAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgKQogICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgIGlmIG5vdCBoYXNfa3czOgogICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICBzdWIyX2RhdGFfc3RhcnQgPSBpMwogICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICBicmVhawogICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICBvY2Nfa2V5ID0gKGNvbF90eXBlLCBrd19kZXRlY3QpCiAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgIG9jY19pZHggPSBvY2N1cnJlbmNlX2NvdW50cy5nZXQob2NjX2tleSwgMCkKICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgb2NjdXJyZW5jZV9jb3VudHNbb2NjX2tleV0gPSBvY2NfaWR4ICsgMQogICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICBjb21wX2NvbHMuYXBwZW5kKHsKICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICJjb2wiOiAgICAgICAgICAgICAgaiwKICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICJ0eXBlIjogICAgICAgICAgICAgY29sX3R5cGUsCiAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAic3JjX2lkIjogICAgICAgICAgIHNyY19pZCwKICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICJzcmNfc2giOiAgICAgICAgICAgc3JjX3NoLAogICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgImt3X3NyYyI6ICAgICAgICAgICBrd19zcmMsCiAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAiZmlyc3RfaGVhZGVyX3JvdyI6IGksCiAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAic2VnbWVudF9sYWJlbCI6ICAgIHNlZ19sYWJlbCwKICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICJvY2N1cnJlbmNlX2luZGV4Ijogb2NjX2lkeCwKICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICJzdWIyX2hlYWRlcl9yb3ciOiAgc3ViMl9oZWFkZXJfcm93LAogICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgInN1YjJfZGF0YV9zdGFydCI6ICBzdWIyX2RhdGFfc3RhcnQsCiAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAic3ViX3RhYmxlX29mZnNldCI6IChzdWIyX2hlYWRlcl9yb3cgLSBpKSBpZiBzdWIyX2hlYWRlcl9yb3cgZWxzZSBOb25lLAogICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICB9KQogICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICBzZWVuW2pdID0gaQogICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAjIENvbHVtbmFzIGNvbXBhw7FlcmFzIGJham8gZWwgbWlzbW8gbWVyZ2UgZGUgZmVjaGE6CiAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICMgbGEgY2VsZGEgZGUgZmVjaGEgc29sbyBleGlzdGUgZW4gbGEgMXJhIGNvbCBkZWwgbWVyZ2U7CiAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICMgbGFzIHNpZ3VpZW50ZXMgKGVqLiAiRWZlY3RvIGVuIHJlc3VsdGFkb3MiKSB0aWVuZW4gZmVjaGEgdmFjw61hLgogICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICBfZGF0ZV9wYXQgPSByZS5jb21waWxlKHIiXGR7NH0tXGR7Mn0tXGR7Mn18XGR7Mn0tXGR7NH0iKQogICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICBqaiA9IGogKyAxCiAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgIF9za2lwcGVkX3NlcCA9IDAKICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgX2NvbXBhbmlvbl9pZHggPSAwICAjIGN1w6FudGFzIGNvbXBhbmlvbnMgeWEgYcOxYWRpbW9zCiAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgIHdoaWxlIGpqIDwgNTAwIGFuZCAoamogbm90IGluIHNlZW4gb3IgX2Jsb3F1ZXNfZGlzdGludG9zKHNlZW5bampdLCBpKSk6CiAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAjIFBhcmFyIHNpIGxhIGNvbCB0aWVuZSBjdWFscXVpZXIgZmVjaGEgZW4gZW5jYWJlemFkbwogICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgZGVmIF9jb2xfaGFzX2RhdGUoY29sKToKICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICBmb3IgcnIgaW4gYWxsX3Jvd3NbOjhdOgogICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICBpZiBjb2wgPj0gbGVuKHJyKTogY29udGludWUKICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgY3YgPSBzdHIocnJbY29sXS5nZXQoImNhbGN1bGF0ZWRWYWx1ZSIpIG9yIHJyW2NvbF0uZ2V0KCJ2YWx1ZSIpIG9yICIiKSBpZiBpc2luc3RhbmNlKHJyW2NvbF0sIGRpY3QpIGVsc2UgIiIKICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgaWYgX2RhdGVfcGF0LnNlYXJjaChjdik6CiAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICByZXR1cm4gVHJ1ZQogICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgIHJldHVybiBGYWxzZQogICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgaWYgX2NvbF9oYXNfZGF0ZShqaik6CiAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgYnJlYWsKICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICMgRGViZSB0ZW5lciBNJCBlbiBhbGd1bmEgZmlsYSBkZSBlbmNhYmV6YWRvIChjb2wgZGUgZGF0b3MpCiAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICBkZWYgX2NvbF9oYXNfbXMoY29sKToKICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICBmb3IgcnIgaW4gYWxsX3Jvd3NbOjEyXToKICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgaWYgY29sID49IGxlbihycik6IGNvbnRpbnVlCiAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgIGN2ID0gc3RyKHJyW2NvbF0uZ2V0KCJjYWxjdWxhdGVkVmFsdWUiKSBvciBycltjb2xdLmdldCgidmFsdWUiKSBvciAiIikuc3RyaXAoKSBpZiBpc2luc3RhbmNlKHJyW2NvbF0sIGRpY3QpIGVsc2UgIiIKICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgaWYgY3YubG93ZXIoKSBpbiAoIm0kIiwgIiQiKToKICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgIHJldHVybiBUcnVlCiAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgcmV0dXJuIEZhbHNlCiAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICBpZiBub3QgX2NvbF9oYXNfbXMoamopOgogICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICMgUGVybWl0aXIgaGFzdGEgMiBjb2xzIHNlcGFyYWRvcmFzIHZhY8OtYXMgYW50ZXMgZGUgcmVuZGlyc2UKICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICBfc2tpcHBlZF9zZXAgKz0gMQogICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgIGlmIF9za2lwcGVkX3NlcCA+IDI6CiAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgIGJyZWFrCiAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgamogKz0gMQogICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgIGNvbnRpbnVlCiAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICBfc2tpcHBlZF9zZXAgPSAwCiAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAjIFNhbHRhciBjb2x1bW5hcyAlCiAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICBpZiBhbnkoX2NlbGxfc3RyKHJbampdKSA9PSAiJSIgZm9yIHIgaW4gYWxsX3Jvd3NbOjEwXSBpZiBqaiA8IGxlbihyKSk6CiAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgamogKz0gMQogICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgIGNvbnRpbnVlCiAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICBfY29tcGFuaW9uX2lkeCArPSAxCiAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICBvY2Nfa2V5X2MgPSAoY29sX3R5cGUsIGt3X2RldGVjdCkKICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgIG9jY19pZHhfYyA9IG9jY3VycmVuY2VfY291bnRzLmdldChvY2Nfa2V5X2MsIDApCiAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICBvY2N1cnJlbmNlX2NvdW50c1tvY2Nfa2V5X2NdID0gb2NjX2lkeF9jICsgMQogICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgY29tcF9jb2xzLmFwcGVuZCh7CiAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgImNvbCI6ICAgICAgICAgICAgICAgICAgamosCiAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgInR5cGUiOiAgICAgICAgICAgICAgICAgY29sX3R5cGUsCiAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgInNyY19pZCI6ICAgICAgICAgICAgICAgc3JjX2lkLAogICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICJzcmNfc2giOiAgICAgICAgICAgICAgIHNyY19zaCwKICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAia3dfc3JjIjogICAgICAgICAgICAgICBrd19zcmMsCiAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgImZpcnN0X2hlYWRlcl9yb3ciOiAgICAgaSwKICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAic2VnbWVudF9sYWJlbCI6ICAgICAgICBzZWdfbGFiZWwsCiAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgIm9jY3VycmVuY2VfaW5kZXgiOiAgICAgb2NjX2lkeF9jLAogICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICJzdWIyX2hlYWRlcl9yb3ciOiAgICAgIHN1YjJfaGVhZGVyX3JvdywKICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAic3ViMl9kYXRhX3N0YXJ0IjogICAgICBzdWIyX2RhdGFfc3RhcnQsCiAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgInN1Yl90YWJsZV9vZmZzZXQiOiAgICAgKHN1YjJfaGVhZGVyX3JvdyAtIGkpIGlmIHN1YjJfaGVhZGVyX3JvdyBlbHNlIE5vbmUsCiAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgImlzX2NvbXBhbmlvbiI6ICAgICAgICAgVHJ1ZSwKICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAiY29tcGFuaW9uX3NyY19vZmZzZXQiOiBfY29tcGFuaW9uX2lkeCwgICMgc2FsdGFyIE4gY29scyBNJCBlbiBmdWVudGUgZGVzZGUgc3JjX2NvbAogICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgfSkKICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgIHNlZW5bampdID0gaQogICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgamogKz0gMQogICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgIGJyZWFrCiAgICAgICAgICAgICAgICAjIFRvZGFzIGxhcyBjb2x1bW5hcyBkZXRlY3RhZGFzIGVuIGVzdGEgcGFzYWRhIHF1ZWRhbiBhY290YWRhcyBhbAogICAgICAgICAgICAgICAgIyBibG9xdWUgZG9uZGUgc2UgZW5jb250cmFyb246IGZpbGFzIGZ1ZXJhIGRlIGVzZSByYW5nbyAob3RyYQogICAgICAgICAgICAgICAgIyBzdWItdGFibGEsIHNpIGxhIGhheSkgTk8gc2UgY29tcGFyYW4vZXNjcmliZW4gY29uIGVzdGUgY29sX2luZm8sCiAgICAgICAgICAgICAgICAjIGRlamFuZG8gcXVlIG90cmEgcGFzYWRhIGxhcyByZWNsYW1lIGNvbiBlbCB0aXBvIHF1ZSBjb3JyZXNwb25kYS4KICAgICAgICAgICAgICAgIGZvciBlbnRyeSBpbiBjb21wX2NvbHNbaWR4X2luaWNpb19ibG9xdWU6XToKICAgICAgICAgICAgICAgICAgICBlbnRyeVsiZmlsYV9ibG9xdWVfaW5pY2lvIl0gPSBwcmltZXJfbWF0Y2hfcm93IG9yIDAKICAgICAgICAgICAgICAgICAgICBlbnRyeVsiZmlsYV9ibG9xdWVfZmluIl0gPSBmaW5fYmxvcXVlX2FjdHVhbAogICAgICAgICAgICBpZiBjb21wX2NvbHM6CiAgICAgICAgICAgICAgICBjb21wX2NvbHNfYnlfbmFtZVtzbmFtZV0gPSBjb21wX2NvbHMKCiAgICAgICAgd2l0aF9jb2xzID0gbGlzdChjb21wX2NvbHNfYnlfbmFtZSkKCiAgICAgICAgIyA3LiBMZWVyIGNlbGRhcyBmdWVudGUgYWdydXBhZGFzIHBvciAoc3JjX2lkLCBzaGVldCkgcGFyYSBldml0YXIgbGVjdHVyYXMgZHVwbGljYWRhcwogICAgICAgICMgICAgQ2xhdmU6IChzcmNfaWQsIHNuYW1lKSDihpIgY2VsbHMKICAgICAgICBzcmNfcmVhZF9rZXlzOiBsaXN0W3R1cGxlW3N0ciwgc3RyLCBzdHJdXSA9IFtdICAjIChzcmNfaWQsIHNoZWV0X2lkLCBzbmFtZSkKICAgICAgICBzZWVuX3JlYWRzOiBzZXRbdHVwbGVbc3RyLCBzdHJdXSA9IHNldCgpCiAgICAgICAgZm9yIHNuYW1lIGluIHdpdGhfY29sczoKICAgICAgICAgICAgZm9yIGNvbF9pbmZvIGluIGNvbXBfY29sc19ieV9uYW1lW3NuYW1lXToKICAgICAgICAgICAgICAgIHNpZF9zcmMgPSBjb2xfaW5mb1sic3JjX2lkIl0KICAgICAgICAgICAgICAgIHNyY19zaCAgPSBjb2xfaW5mb1sic3JjX3NoIl0KICAgICAgICAgICAgICAgIGlmIG5vdCBzaWRfc3JjIG9yIHNuYW1lIG5vdCBpbiBzcmNfc2g6CiAgICAgICAgICAgICAgICAgICAgY29udGludWUKICAgICAgICAgICAgICAgIGtleSA9IChzaWRfc3JjLCBzbmFtZSkKICAgICAgICAgICAgICAgIGlmIGtleSBub3QgaW4gc2Vlbl9yZWFkczoKICAgICAgICAgICAgICAgICAgICBzZWVuX3JlYWRzLmFkZChrZXkpCiAgICAgICAgICAgICAgICAgICAgc3JjX3JlYWRfa2V5cy5hcHBlbmQoKHNpZF9zcmMsIHNyY19zaFtzbmFtZV0sIHNuYW1lKSkKCiAgICAgICAgc3JjX2NlbGxzX2NhY2hlOiBkaWN0W3R1cGxlW3N0ciwgc3RyXSwgbGlzdFtsaXN0XV0gPSB7fQogICAgICAgIGlmIHNyY19yZWFkX2tleXM6CiAgICAgICAgICAgIHJlc3VsdHMgPSBhd2FpdCBhc3luY2lvLmdhdGhlcigKICAgICAgICAgICAgICAgICooX3JlYWRfbGltKHNpZCwgc2hlZXRfaWQpIGZvciBzaWQsIHNoZWV0X2lkLCBfIGluIHNyY19yZWFkX2tleXMpCiAgICAgICAgICAgICkKICAgICAgICAgICAgZm9yIChzaWQsIF8sIHNuYW1lKSwgY2VsbHMgaW4gemlwKHNyY19yZWFkX2tleXMsIHJlc3VsdHMpOgogICAgICAgICAgICAgICAgc3JjX2NlbGxzX2NhY2hlWyhzaWQsIHNuYW1lKV0gPSBjZWxscwoKICAgICAgICAjIDguIFByb2Nlc2FyIGNhZGEgaG9qYQogICAgICAgIGZvciBzbmFtZSBpbiB3aXRoX2NvbHM6CiAgICAgICAgICAgIHNpZF90ICAgICA9IHRndF9zaGVldHNbc25hbWVdCiAgICAgICAgICAgIHRndF9jZWxscyA9IHRndF9jZWxsc19ieV9uYW1lW3NuYW1lXQoKICAgICAgICAgICAgc2hlZXRfcmVwb3J0OiBkaWN0W3N0ciwgQW55XSA9IHsKICAgICAgICAgICAgICAgICJzaGVldCI6IHNuYW1lLAogICAgICAgICAgICAgICAgImNvbXBfY29scyI6IFsKICAgICAgICAgICAgICAgICAgICBmIntfY29sX2xldHRlcihjWydjb2wnXSl9KHtjWyd0eXBlJ119LHNlZz17Yy5nZXQoJ3NlZ21lbnRfbGFiZWwnLCcnKSFyfSkiCiAgICAgICAgICAgICAgICAgICAgZm9yIGMgaW4gY29tcF9jb2xzX2J5X25hbWVbc25hbWVdCiAgICAgICAgICAgICAgICBdLAogICAgICAgICAgICAgICAgImNvbHNfd3JpdHRlbiI6IDAsCiAgICAgICAgICAgIH0KCiAgICAgICAgICAgIGZvciBjb2xfaW5mbyBpbiBjb21wX2NvbHNfYnlfbmFtZVtzbmFtZV06CiAgICAgICAgICAgICAgICBkZXN0X2NvbCA9IGNvbF9pbmZvWyJjb2wiXQogICAgICAgICAgICAgICAgY29sX3R5cGUgPSBjb2xfaW5mb1sidHlwZSJdCiAgICAgICAgICAgICAgICBzcmNfaWQgICA9IGNvbF9pbmZvWyJzcmNfaWQiXQogICAgICAgICAgICAgICAga3dfc3JjICAgPSBjb2xfaW5mb1sia3dfc3JjIl0KCiAgICAgICAgICAgICAgICAjIE9idGVuZXIgY2VsZGFzIGZ1ZW50ZSBkZXNkZSBjYWNoZQogICAgICAgICAgICAgICAgc3JjX2NlbGxzID0gc3JjX2NlbGxzX2NhY2hlLmdldCgoc3JjX2lkLCBzbmFtZSksIFtdKQogICAgICAgICAgICAgICAgaWYgbm90IHNyY19jZWxsczoKICAgICAgICAgICAgICAgICAgICBjb250aW51ZQoKICAgICAgICAgICAgICAgICMgQnVzY2FyIGNvbHVtbmEgZnVlbnRlIHBvciBzZWdtZW50byArIGtleXdvcmQgKHBhcmEgdGFibGFzIG11bHRpLXNlZ21lbnRvKQogICAgICAgICAgICAgICAgc2VnX2xhYmVsICAgICAgID0gY29sX2luZm8uZ2V0KCJzZWdtZW50X2xhYmVsIiwgIiIpCiAgICAgICAgICAgICAgICBvY2N1cnJlbmNlX2luZGV4ID0gY29sX2luZm8uZ2V0KCJvY2N1cnJlbmNlX2luZGV4IiwgMCkKICAgICAgICAgICAgICAgIGNvbXBhbmlvbl9vZmZzZXQgPSBjb2xfaW5mby5nZXQoImNvbXBhbmlvbl9zcmNfb2Zmc2V0IiwgMCkKICAgICAgICAgICAgICAgICMgb2NjdXJyZW5jZV9pbmRleCB5IGNvbXBhbmlvbl9zcmNfb2Zmc2V0IHNlIGxsZW5hbiBjb24gZWwgTUlTTU8KICAgICAgICAgICAgICAgICMgY29udGFkb3IgKHBvc2ljacOzbiBkZW50cm8gZGVsIGJsb3F1ZTogMD1jb2wgYmFzZSwgMT1jb21wYW5pb24gMSwKICAgICAgICAgICAgICAgICMgMj1jb21wYW5pb24gMi4uLikuIFNpIGVzdGEgY29sdW1uYSBlcyB1biBjb21wYW5pb24sIGVsIHBhc28gZGUKICAgICAgICAgICAgICAgICMgY29tcGFuaW9uIChfbmV4dF9jb21wYW5pb25fY29sX2luX3NyYywgbcOhcyBhYmFqbykgWUEgaGFjZSBlc2UKICAgICAgICAgICAgICAgICMgZGVzcGxhemFtaWVudG8gYnVzY2FuZG8gTSQvZWZlY3RvIHJlYWwgZW4gZWwgZnVlbnRlLiBVc2FyCiAgICAgICAgICAgICAgICAjIG9jY3VycmVuY2VfaW5kZXggdGFtYmnDqW4gYXF1w60gcGFyYSBlbGVnaXIgbGEgTnRoIGNvaW5jaWRlbmNpYSBkZQogICAgICAgICAgICAgICAgIyBrd19zcmMgZHVwbGljYSBlbCBkZXNwbGF6YW1pZW50byAtLSB5IHNpIGt3X3NyYyAodW5hIGZlY2hhKSBzZQogICAgICAgICAgICAgICAgIyByZXBpdGUgZW4gZWwgZnVlbnRlIHBvciBjb2luY2lkZW5jaWEgZW4gdW4gYmxvcXVlIG5vIHJlbGFjaW9uYWRvCiAgICAgICAgICAgICAgICAjIChlai4gImN1cnJfcHJldiIgcXVlIHRhbWJpw6luIGFycmFuY2EgMS1lbmVybyksIHRlcm1pbmEgc2FsdGFuZG8KICAgICAgICAgICAgICAgICMgYWwgYmxvcXVlIGVxdWl2b2NhZG8gYW50ZXMgZGUgYXBsaWNhciBlbCBjb21wYW5pb24uIFBvciBlc28gYWPDoQogICAgICAgICAgICAgICAgIyBzaWVtcHJlIHNlIGJ1c2NhIGxhIFBSSU1FUkEgY29pbmNpZGVuY2lhIGRlIGt3X3NyYyBjb21vIGJhc2UuCiAgICAgICAgICAgICAgICBfb2NjX3BhcmFfa3dfc3JjID0gMCBpZiBjb21wYW5pb25fb2Zmc2V0IGVsc2Ugb2NjdXJyZW5jZV9pbmRleAogICAgICAgICAgICAgICAgc3JjX2NvbCA9IF9maW5kX3NyY19jb2xfYnlfc2VnbWVudChzcmNfY2VsbHMsIGt3X3NyYywgc2VnX2xhYmVsLCBfb2NjX3BhcmFfa3dfc3JjKQogICAgICAgICAgICAgICAgaWYgY29tcGFuaW9uX29mZnNldCBhbmQgc3JjX2NvbCBpcyBub3QgTm9uZToKICAgICAgICAgICAgICAgICAgICBzcmNfY29sID0gX25leHRfY29tcGFuaW9uX2NvbF9pbl9zcmMoc3JjX2NlbGxzLCBzcmNfY29sLCBjb21wYW5pb25fb2Zmc2V0KQogICAgICAgICAgICAgICAgaWYgc3JjX2NvbCBpcyBOb25lOgogICAgICAgICAgICAgICAgICAgIGNvbnRpbnVlCgogICAgICAgICAgICAgICAgZmlsYV9ibG9xdWVfaW5pY2lvID0gY29sX2luZm8uZ2V0KCJmaWxhX2Jsb3F1ZV9pbmljaW8iLCAwKQogICAgICAgICAgICAgICAgZmlsYV9ibG9xdWVfZmluICAgID0gY29sX2luZm8uZ2V0KCJmaWxhX2Jsb3F1ZV9maW4iKQoKICAgICAgICAgICAgICAgIHN1YjJfZGF0YV9zdGFydCAgPSBjb2xfaW5mby5nZXQoInN1YjJfZGF0YV9zdGFydCIpCiAgICAgICAgICAgICAgICBzdWJfdGFibGVfb2Zmc2V0ID0gY29sX2luZm8uZ2V0KCJzdWJfdGFibGVfb2Zmc2V0IikKCiAgICAgICAgICAgICAgICAjIOKUgOKUgCBSZWdsYSBlc3BlY8OtZmljYTogaG9qYXMgY29uIGRvcyB0YWJsYXMgYW51YWxlcyBhcGlsYWRhcyDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIAKICAgICAgICAgICAgICAgICMgKGVqLiAiMjMuLSBTZWdtZW50b3MgZGUgdmVudGFzIikuIExhIHRhYmxhIGRlIGFycmliYSBkZWwgZGVzdGlubyBlcwogICAgICAgICAgICAgICAgIyBlbCBwZXLDrW9kbyBhY3R1YWwgeSBOTyBzZSB2YWxpZGEuIExhIGRlIGFiYWpvIHNvbiBsb3MgcGVyw61vZG9zIGRlbAogICAgICAgICAgICAgICAgIyBhw7FvIGFudGVyaW9yLCB5IGNvcnJlc3BvbmRlIGEgbGEgdGFibGEgZGUgQVJSSUJBIGRlbCBhcmNoaXZvIGZ1ZW50ZS4KICAgICAgICAgICAgICAgICMgRWwgZGVzZmFzZSBlbnRyZSBibG9xdWVzIHNlIGNhbGN1bGEgY29tcGFyYW5kbyBlbiBxdcOpIGZpbGEgZXN0w6EgZWwKICAgICAgICAgICAgICAgICMgZW5jYWJlemFkbyBkZSBmZWNoYSBlbiBjYWRhIGFyY2hpdm8sIGFzw60gbm8gZGVwZW5kZSBkZSBmaWxhcyBmaWphcy4KICAgICAgICAgICAgICAgIHRhYmxhX2FwaWxhZGEgICA9IF9wcmVmaWpvX2hvamEoc25hbWUpIGluIEhPSkFTX1RBQkxBX0FOVUFMX0FQSUxBREEKICAgICAgICAgICAgICAgIGZpbGFfaGRyX2Rlc3QgICA9IGNvbF9pbmZvLmdldCgiZmlyc3RfaGVhZGVyX3JvdyIpCiAgICAgICAgICAgICAgICBvZmZzZXRfYXBpbGFkYSAgPSBOb25lCiAgICAgICAgICAgICAgICBpZiB0YWJsYV9hcGlsYWRhIGFuZCBmaWxhX2hkcl9kZXN0IGlzIG5vdCBOb25lOgogICAgICAgICAgICAgICAgICAgIGZpbGFfaGRyX3NyYyA9IF9maWxhX2t3X2VuX2NvbChzcmNfY2VsbHMsIGt3X3NyYywgc3JjX2NvbCkKICAgICAgICAgICAgICAgICAgICBpZiBmaWxhX2hkcl9zcmMgaXMgbm90IE5vbmU6CiAgICAgICAgICAgICAgICAgICAgICAgIG9mZnNldF9hcGlsYWRhID0gZmlsYV9oZHJfZGVzdCAtIGZpbGFfaGRyX3NyYwoKICAgICAgICAgICAgICAgICMgUmVhbGluZWFjacOzbiBwb3IgZXRpcXVldGE6IGN1YW5kbyBsYSBwbGFudGlsbGEgZGVsIGFyY2hpdm8gZnVlbnRlCiAgICAgICAgICAgICAgICAjIHRpZW5lIGZpbGFzIGRlIG3DoXMgbyBkZSBtZW5vcyByZXNwZWN0byBhbCBkZXN0aW5vLCBsYSBmaWxhIGkgZGVsCiAgICAgICAgICAgICAgICAjIGRlc3Rpbm8gTk8gY29ycmVzcG9uZGUgYSBsYSBmaWxhIGkgZGVsIGZ1ZW50ZS4gU2UgYnVzY2EgZW4gZWwKICAgICAgICAgICAgICAgICMgZnVlbnRlIGxhIGZpbGEgY29uIGxhIG1pc21hIGV0aXF1ZXRhIGRlbnRybyBkZSB1bmEgdmVudGFuYSBjZXJjYW5hCiAgICAgICAgICAgICAgICAjIHkgc2UgdXNhIGVzYS4gU2kgbGFzIHBsYW50aWxsYXMgZXN0w6FuIGFsaW5lYWRhcyAoY2FzbyBub3JtYWwpIGxhCiAgICAgICAgICAgICAgICAjIGV0aXF1ZXRhIGNhbHphIGVuIGxhIG1pc21hIGZpbGEgeSBlbCBjb21wb3J0YW1pZW50byBubyBjYW1iaWEuCiAgICAgICAgICAgICAgICBfVkVOVEFOQV9BTElORUFDSU9OID0gOAoKICAgICAgICAgICAgICAgIHNyY192YWxzOiBsaXN0W0FueV0gPSBbXQogICAgICAgICAgICAgICAgc3JjX2NvcnI6IGxpc3RbYm9vbF0gPSBbXSAgICMgRmFsc2UgPSBsYSBmaWxhIG5vIGV4aXN0ZSBlbiBlbCBmdWVudGUKICAgICAgICAgICAgICAgIHNyY19za2lwOiBsaXN0W2Jvb2xdID0gW10gICAjIFRydWUgID0gZmlsYSBmdWVyYSBkZSBhbGNhbmNlOiBuaSB2YWxpZGFyIG5pIGVzY3JpYmlyCiAgICAgICAgICAgICAgICBzcmNfdmlhX2J1c3F1ZWRhOiBsaXN0W2Jvb2xdID0gW10gICMgVHJ1ZSA9IG5vIGNhbHrDsyBkaXJlY3RvLCBzZSBidXNjw7MgY2VyY2EKICAgICAgICAgICAgICAgIGZvciBpIGluIHJhbmdlKGxlbih0Z3RfY2VsbHMpKToKICAgICAgICAgICAgICAgICAgICBpZiBmaWxhX2Jsb3F1ZV9maW4gaXMgbm90IE5vbmUgYW5kIG5vdCAoZmlsYV9ibG9xdWVfaW5pY2lvIDw9IGkgPCBmaWxhX2Jsb3F1ZV9maW4pOgogICAgICAgICAgICAgICAgICAgICAgICAjIEVzdGEgZmlsYSBxdWVkYSBmdWVyYSBkZWwgYmxvcXVlIGRvbmRlIHNlIGRldGVjdMOzIGVzdGEKICAgICAgICAgICAgICAgICAgICAgICAgIyBjb2x1bW5hIChlai4gb3RyYSBzdWItdGFibGEgZGVudHJvIGRlIGxhIG1pc21hIGhvamEgcXVlCiAgICAgICAgICAgICAgICAgICAgICAgICMgcmV1c2EgbGEgbWlzbWEgbGV0cmEgZGUgY29sdW1uYSBjb24gb3RybyBzaWduaWZpY2FkbykuCiAgICAgICAgICAgICAgICAgICAgICAgICMgU2UgZGVqYSBwYXJhIHF1ZSBPVFJBIGVudHJhZGEgZGUgY29tcF9jb2xzIChkZXRlY3RhZGEgZW4KICAgICAgICAgICAgICAgICAgICAgICAgIyBlc2Ugb3RybyBibG9xdWUpIHNlIGhhZ2EgY2FyZ28sIHNpIGNvcnJlc3BvbmRlLgogICAgICAgICAgICAgICAgICAgICAgICBzcmNfdmFscy5hcHBlbmQoTm9uZSkKICAgICAgICAgICAgICAgICAgICAgICAgc3JjX2NvcnIuYXBwZW5kKFRydWUpCiAgICAgICAgICAgICAgICAgICAgICAgIHNyY19za2lwLmFwcGVuZChUcnVlKQogICAgICAgICAgICAgICAgICAgICAgICBzcmNfdmlhX2J1c3F1ZWRhLmFwcGVuZChGYWxzZSkKICAgICAgICAgICAgICAgICAgICAgICAgY29udGludWUKICAgICAgICAgICAgICAgICAgICBpZiB0YWJsYV9hcGlsYWRhOgogICAgICAgICAgICAgICAgICAgICAgICAjIFNvbG8gc2UgdmFsaWRhIGxhIHRhYmxhIGluZmVyaW9yIChhw7FvIGFudGVyaW9yKS4gVG9kbyBsbyBxdWUKICAgICAgICAgICAgICAgICAgICAgICAgIyBlc3TDoSBzb2JyZSBzdSBlbmNhYmV6YWRvIGVzIGVsIHBlcsOtb2RvIGFjdHVhbDogc2luIGNvbXBhcmF0aXZvLgogICAgICAgICAgICAgICAgICAgICAgICAjIFkgdW5hIHZleiBxdWUgZWwgZGVzdGlubyBzZSBxdWVkYSBzaW4gZXRpcXVldGEgKGZpbiBkZSBsYQogICAgICAgICAgICAgICAgICAgICAgICAjIHRhYmxhIGluZmVyaW9yLCBlai4gdHJhcyBlbCAiVG90YWwiKSwgdGFtcG9jbyBzZSBjb21wYXJhOgogICAgICAgICAgICAgICAgICAgICAgICAjIGRlIGxvIGNvbnRyYXJpbyBlbCBvZmZzZXQgc2lndWUgYXBsaWPDoW5kb3NlIHNpbiBsw61taXRlIGhhY2lhCiAgICAgICAgICAgICAgICAgICAgICAgICMgYWJham8geSB0ZXJtaW5hIGxleWVuZG8gY29udGVuaWRvIGRlIGxhIGZ1ZW50ZSBxdWUgbm8gdGllbmUKICAgICAgICAgICAgICAgICAgICAgICAgIyBuYWRhIHF1ZSB2ZXIgKG90cmEgdGFibGEsIHVuIHBpZSBkZSBww6FnaW5hLCBldGMuKS4KICAgICAgICAgICAgICAgICAgICAgICAgX2xibF9hcGlsYWRhID0gX25vcm1fbGJsKF9ldGlxdWV0YV9maWxhKHRndF9jZWxsc1tpXSkpCiAgICAgICAgICAgICAgICAgICAgICAgIGlmIG9mZnNldF9hcGlsYWRhIGlzIE5vbmUgb3IgaSA8PSBmaWxhX2hkcl9kZXN0IG9yIG5vdCBfbGJsX2FwaWxhZGE6CiAgICAgICAgICAgICAgICAgICAgICAgICAgICBzcmNfdmFscy5hcHBlbmQoTm9uZSkKICAgICAgICAgICAgICAgICAgICAgICAgICAgIHNyY19jb3JyLmFwcGVuZChUcnVlKQogICAgICAgICAgICAgICAgICAgICAgICAgICAgc3JjX3NraXAuYXBwZW5kKFRydWUpCiAgICAgICAgICAgICAgICAgICAgICAgICAgICBzcmNfdmlhX2J1c3F1ZWRhLmFwcGVuZChGYWxzZSkKICAgICAgICAgICAgICAgICAgICAgICAgICAgIGNvbnRpbnVlCiAgICAgICAgICAgICAgICAgICAgICAgIHNyY19yb3dfaSA9IGkgLSBvZmZzZXRfYXBpbGFkYQogICAgICAgICAgICAgICAgICAgICMgRG9ibGUgc3ViLXRhYmxhOiBmaWxhcyBkZSBsYSBzdWItdGFibGEgaW5mZXJpb3IgZGVsIGRlc3Rpbm8KICAgICAgICAgICAgICAgICAgICAjIHNlIHJlbWFwZWFuIGEgbGFzIGZpbGFzIGRlIGxhIHN1Yi10YWJsYSBzdXBlcmlvciBkZWwgZnVlbnRlLAogICAgICAgICAgICAgICAgICAgICMgUEVSTyBzb2xvIHNpIGxhIGZ1ZW50ZSBubyB0aWVuZSB5YSBkYXRvcyBlbiBsYSBtaXNtYSBmaWxhLgogICAgICAgICAgICAgICAgICAgICMgQ3VhbmRvIGFtYmFzIHN1Yi10YWJsYXMgZXN0w6FuIGVuIGxhcyBtaXNtYXMgZmlsYXMgKGVqLiBub3RhIDg1KSwKICAgICAgICAgICAgICAgICAgICAjIGVsIG9mZnNldCBubyBoYWNlIGZhbHRhIHkgYXBsaWNhcmxvIHJlbWFwZWEgYWwgbHVnYXIgaW5jb3JyZWN0by4KICAgICAgICAgICAgICAgICAgICBlbGlmIHN1YjJfZGF0YV9zdGFydCBhbmQgc3ViX3RhYmxlX29mZnNldCBhbmQgaSA+PSBzdWIyX2RhdGFfc3RhcnQ6CiAgICAgICAgICAgICAgICAgICAgICAgIHJvd19vcmlnID0gc3JjX2NlbGxzW2ldIGlmIDAgPD0gaSA8IGxlbihzcmNfY2VsbHMpIGVsc2UgW10KICAgICAgICAgICAgICAgICAgICAgICAgc3Zfb3JpZyAgPSBfY3Yocm93X29yaWdbc3JjX2NvbF0pIGlmIHNyY19jb2wgPCBsZW4ocm93X29yaWcpIGVsc2UgTm9uZQogICAgICAgICAgICAgICAgICAgICAgICBpZiBzdl9vcmlnIGlzIG5vdCBOb25lOgogICAgICAgICAgICAgICAgICAgICAgICAgICAgc3JjX3Jvd19pID0gaSAgICAgICAgICAjIGZ1ZW50ZSB0aWVuZSBkYXRvcyBhcXXDrTogbm8gYXBsaWNhciBvZmZzZXQKICAgICAgICAgICAgICAgICAgICAgICAgZWxzZToKICAgICAgICAgICAgICAgICAgICAgICAgICAgIHNyY19yb3dfaSA9IGkgLSBzdWJfdGFibGVfb2Zmc2V0CiAgICAgICAgICAgICAgICAgICAgZWxzZToKICAgICAgICAgICAgICAgICAgICAgICAgc3JjX3Jvd19pID0gaQoKICAgICAgICAgICAgICAgICAgICBsYmxfdCA9IF9ub3JtX2xibChfZXRpcXVldGFfZmlsYSh0Z3RfY2VsbHNbaV0pKQogICAgICAgICAgICAgICAgICAgIHJvd19iID0gc3JjX2NlbGxzW3NyY19yb3dfaV0gaWYgMCA8PSBzcmNfcm93X2kgPCBsZW4oc3JjX2NlbGxzKSBlbHNlIFtdCiAgICAgICAgICAgICAgICAgICAgbGJsX2IgPSBfbm9ybV9sYmwoX2V0aXF1ZXRhX2ZpbGEocm93X2IpKQogICAgICAgICAgICAgICAgICAgIHZpYV9idXNxdWVkYSA9IEZhbHNlCiAgICAgICAgICAgICAgICAgICAgaWYgbGJsX3QgYW5kIGxibF9iICE9IGxibF90OgogICAgICAgICAgICAgICAgICAgICAgICB2aWFfYnVzcXVlZGEgPSBUcnVlCiAgICAgICAgICAgICAgICAgICAgICAgICMgTWlzbWEgZmlsYSwgcGVybyBsYSBldGlxdWV0YSBjYW1iacOzIGRlIHVuYSBwbGFudGlsbGEgYSBvdHJhCiAgICAgICAgICAgICAgICAgICAgICAgICMgKGVqLiAiQ29zdG8gZGUgYWRtaW5pc3RyYWNpw7NuIiBwYXPDsyBhIGxsYW1hcnNlICJHYXN0byBkZQogICAgICAgICAgICAgICAgICAgICAgICAjIGFkbWluaXN0cmFjacOzbiIsIG8gZWwgbWlzbW8gdGV4dG8gcXVlZMOzIHJlb3JkZW5hZG8pLiBTaSBsYXMKICAgICAgICAgICAgICAgICAgICAgICAgIyBldGlxdWV0YXMgY29tcGFydGVuIGxhIG1heW9yw61hIGRlIHN1cyBwYWxhYnJhcywgc2UgYWNlcHRhCiAgICAgICAgICAgICAgICAgICAgICAgICMgY29tbyBsYSBtaXNtYSBmaWxhIHNpbiBuZWNlc2lkYWQgZGUgYnVzY2FyIGVuIG90cmEgcG9zaWNpw7NuCiAgICAgICAgICAgICAgICAgICAgICAgICMg4oCUIGVzIG3DoXMgcm9idXN0byBlbnRyZSBzb2NpZWRhZGVzIHF1ZSBhc3VtaXIgZXN0cnVjdHVyYXMgZGUKICAgICAgICAgICAgICAgICAgICAgICAgIyB0YWJsYSBpZMOpbnRpY2FzLgogICAgICAgICAgICAgICAgICAgICAgICBpZiBsYmxfYiBhbmQgX2V0aXF1ZXRhc19zaW1pbGFyZXMobGJsX3QsIGxibF9iKToKICAgICAgICAgICAgICAgICAgICAgICAgICAgIGhhbGxhZGEgPSBzcmNfcm93X2kKICAgICAgICAgICAgICAgICAgICAgICAgZWxzZToKICAgICAgICAgICAgICAgICAgICAgICAgICAgICMgRGVzZmFzZSByZWFsIGRlIGZpbGE6IGJ1c2NhciBsYSBldGlxdWV0YSBjZXJjYSwgZGUgbGEgbcOhcwogICAgICAgICAgICAgICAgICAgICAgICAgICAgIyBwcsOzeGltYSBhIGxhIG3DoXMgbGVqYW5hLiBMYSBiw7pzcXVlZGEgdG9sZXJhIFVOQSBmaWxhIGVuCiAgICAgICAgICAgICAgICAgICAgICAgICAgICAjIGJsYW5jbyBkZSBwb3IgbWVkaW8gKGVzcGFjaWFkb3Igbm9ybWFsIGFudGVzIGRlIHVuCiAgICAgICAgICAgICAgICAgICAgICAgICAgICAjICJUb3RhbCIsIHBvciBlamVtcGxvKSwgcGVybyBzZSBkZXRpZW5lIHNpIGVuY3VlbnRyYSBET1MKICAgICAgICAgICAgICAgICAgICAgICAgICAgICMgYmxhbmNvcyBzZWd1aWRvczogZXNhIGVzIGxhIHNlw7FhbCByZWFsIGRlICJlc3RvIGVzIG90cmEKICAgICAgICAgICAgICAgICAgICAgICAgICAgICMgdGFibGEiIChub3RhcyBjb24gZG9zIHRhYmxhcyBhcGlsYWRhcyByZXBpdGVuIGxhcyBtaXNtYXMKICAgICAgICAgICAgICAgICAgICAgICAgICAgICMgZXRpcXVldGFzIOKAlCBjcnV6YXIgZXNlIGJvcmRlIG1lemNsYXLDrWEgYW1ib3MgYmxvcXVlcykuCiAgICAgICAgICAgICAgICAgICAgICAgICAgICBoYWxsYWRhID0gTm9uZQogICAgICAgICAgICAgICAgICAgICAgICAgICAgZm9yIHNpZ25vIGluICgtMSwgMSk6CiAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgYmxhbmNvc19zZWd1aWRvcyA9IDAKICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICBmb3IgZCBpbiByYW5nZSgxLCBfVkVOVEFOQV9BTElORUFDSU9OICsgMSk6CiAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgIGNhbmQgPSBzcmNfcm93X2kgKyBzaWdubyAqIGQKICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgaWYgbm90ICgwIDw9IGNhbmQgPCBsZW4oc3JjX2NlbGxzKSk6CiAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICBicmVhawogICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICBsYmxfY2FuZCA9IF9ub3JtX2xibChfZXRpcXVldGFfZmlsYShzcmNfY2VsbHNbY2FuZF0pKQogICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICBpZiBub3QgbGJsX2NhbmQ6CiAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICBibGFuY29zX3NlZ3VpZG9zICs9IDEKICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgIGlmIGJsYW5jb3Nfc2VndWlkb3MgPj0gMjoKICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICBicmVhayAgICMgZG9zIGJsYW5jb3Mgc2VndWlkb3M6IGJvcmRlIHJlYWwgZGUgdGFibGEKICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgIGNvbnRpbnVlCiAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgIGJsYW5jb3Nfc2VndWlkb3MgPSAwCiAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgIGlmIGxibF9jYW5kID09IGxibF90IG9yIF9ldGlxdWV0YXNfc2ltaWxhcmVzKGxibF90LCBsYmxfY2FuZCk6CiAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICBoYWxsYWRhID0gY2FuZAogICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgYnJlYWsKICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICBpZiBoYWxsYWRhIGlzIG5vdCBOb25lOgogICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICBicmVhawogICAgICAgICAgICAgICAgICAgICAgICBpZiBoYWxsYWRhIGlzIE5vbmU6CiAgICAgICAgICAgICAgICAgICAgICAgICAgICBzcmNfdmFscy5hcHBlbmQoTm9uZSkKICAgICAgICAgICAgICAgICAgICAgICAgICAgIHNyY19jb3JyLmFwcGVuZChGYWxzZSkKICAgICAgICAgICAgICAgICAgICAgICAgICAgIHNyY19za2lwLmFwcGVuZChGYWxzZSkKICAgICAgICAgICAgICAgICAgICAgICAgICAgIHNyY192aWFfYnVzcXVlZGEuYXBwZW5kKFRydWUpCiAgICAgICAgICAgICAgICAgICAgICAgICAgICBjb250aW51ZQogICAgICAgICAgICAgICAgICAgICAgICBzcmNfcm93X2kgPSBoYWxsYWRhCgogICAgICAgICAgICAgICAgICAgIHJvd19zID0gc3JjX2NlbGxzW3NyY19yb3dfaV0gaWYgMCA8PSBzcmNfcm93X2kgPCBsZW4oc3JjX2NlbGxzKSBlbHNlIFtdCiAgICAgICAgICAgICAgICAgICAgc3YgICAgPSBfY3Yocm93X3Nbc3JjX2NvbF0pIGlmIHNyY19jb2wgPCBsZW4ocm93X3MpIGVsc2UgTm9uZQogICAgICAgICAgICAgICAgICAgIHNyY192YWxzLmFwcGVuZChzdiBpZiBpc2luc3RhbmNlKHN2LCAoaW50LCBmbG9hdCkpIGVsc2UgTm9uZSkKICAgICAgICAgICAgICAgICAgICBzcmNfY29yci5hcHBlbmQoVHJ1ZSkKICAgICAgICAgICAgICAgICAgICBzcmNfc2tpcC5hcHBlbmQoRmFsc2UpCiAgICAgICAgICAgICAgICAgICAgc3JjX3ZpYV9idXNxdWVkYS5hcHBlbmQodmlhX2J1c3F1ZWRhKQoKICAgICAgICAgICAgICAgIHdyaXRlX3ZhbHM6IGxpc3RbQW55XSA9IFtdCiAgICAgICAgICAgICAgICBmb3IgaSwgdiBpbiBlbnVtZXJhdGUoc3JjX3ZhbHMpOgogICAgICAgICAgICAgICAgICAgIGlmIHNyY19za2lwW2ldOgogICAgICAgICAgICAgICAgICAgICAgICAjIEZ1ZXJhIGRlbCBhbGNhbmNlIGRlIGxhIG5vdGE6IG5vIHNlIHRvY2EgbGEgY2VsZGEuCiAgICAgICAgICAgICAgICAgICAgICAgIHdyaXRlX3ZhbHMuYXBwZW5kKE5vbmUpCiAgICAgICAgICAgICAgICAgICAgZWxpZiBfaXNfZm9ybXVsYSh0Z3RfY2VsbHNbaV0sIGRlc3RfY29sKToKICAgICAgICAgICAgICAgICAgICAgICAgd3JpdGVfdmFscy5hcHBlbmQoTm9uZSkKICAgICAgICAgICAgICAgICAgICBlbGlmIG5vdCBzcmNfY29ycltpXToKICAgICAgICAgICAgICAgICAgICAgICAgIyBMYSBmaWxhIG5vIGV4aXN0ZSBlbiBlbCBhcmNoaXZvIGZ1ZW50ZTogbm8gc2UgaW52ZW50YSB1bgogICAgICAgICAgICAgICAgICAgICAgICAjIHZhbG9yIG5pIHNlIHBpc2EgZWwgcXVlIHlhIGVzdMOhLiBRdWVkYSBwYXJhIHJldmlzacOzbiBtYW51YWwuCiAgICAgICAgICAgICAgICAgICAgICAgIHdyaXRlX3ZhbHMuYXBwZW5kKE5vbmUpCiAgICAgICAgICAgICAgICAgICAgZWxpZiB2IGlzIE5vbmU6CiAgICAgICAgICAgICAgICAgICAgICAgICMgU2kgbGEgZnVlbnRlIGVzIE5vbmUgcGVybyBlbCBkZXN0aW5vIHRpZW5lIHZhbG9yIG51bcOpcmljbywgZXNjcmliaXIgMAogICAgICAgICAgICAgICAgICAgICAgICAjIHBhcmEgbGltcGlhciB2YWxvcmVzIGVycsOzbmVvcyBwcmV2aW9zIGVuIFdvcmtpdmEKICAgICAgICAgICAgICAgICAgICAgICAgZGVzdF9jdiA9IF9jdih0Z3RfY2VsbHNbaV1bZGVzdF9jb2xdKSBpZiBkZXN0X2NvbCA8IGxlbih0Z3RfY2VsbHNbaV0pIGVsc2UgTm9uZQogICAgICAgICAgICAgICAgICAgICAgICB3cml0ZV92YWxzLmFwcGVuZCgwIGlmIGlzaW5zdGFuY2UoZGVzdF9jdiwgKGludCwgZmxvYXQpKSBhbmQgZGVzdF9jdiAhPSAwIGVsc2UgTm9uZSkKICAgICAgICAgICAgICAgICAgICBlbHNlOgogICAgICAgICAgICAgICAgICAgICAgICBkZXN0X2N2ID0gX2N2KHRndF9jZWxsc1tpXVtkZXN0X2NvbF0pIGlmIGRlc3RfY29sIDwgbGVuKHRndF9jZWxsc1tpXSkgZWxzZSBOb25lCiAgICAgICAgICAgICAgICAgICAgICAgIF9kZXN0X3ZhY2lvID0gZGVzdF9jdiBpcyBOb25lIG9yIChpc2luc3RhbmNlKGRlc3RfY3YsIHN0cikgYW5kIG5vdCBkZXN0X2N2LnN0cmlwKCkpCiAgICAgICAgICAgICAgICAgICAgICAgIGlmIF9kZXN0X3ZhY2lvOgogICAgICAgICAgICAgICAgICAgICAgICAgICAgIyBFbCBkZXN0aW5vIGVzdMOhIFJFQUxNRU5URSBlbiBibGFuY28gKGZpbGEgdMOtdHVsby9zdWJ0w610dWxvLAogICAgICAgICAgICAgICAgICAgICAgICAgICAgIyBzaW4gZGF0byBwcm9waW8sIGVqLiAiRGV1ZG9yZXMgdmFyaW9zIiBhbnRlcyBkZSAiRGV1ZG9yZXMKICAgICAgICAgICAgICAgICAgICAgICAgICAgICMgdmFyaW9zICgqKS4iKTogbm8gc2UgZXNjcmliZSBuYWRhLCBwYXJhIG5vIHJlbGxlbmFyIGFsZ28KICAgICAgICAgICAgICAgICAgICAgICAgICAgICMgcXVlIG5vIGNvcnJlc3BvbmRlLgogICAgICAgICAgICAgICAgICAgICAgICAgICAgd3JpdGVfdmFscy5hcHBlbmQoTm9uZSkKICAgICAgICAgICAgICAgICAgICAgICAgZWxzZToKICAgICAgICAgICAgICAgICAgICAgICAgICAgIHdyaXRlX3ZhbHMuYXBwZW5kKHYpCgogICAgICAgICAgICAgICAgbiA9IHN1bSgxIGZvciB2IGluIChzcmNfdmFscyBpZiBwYXJhbXMuZHJ5X3J1biBlbHNlIHdyaXRlX3ZhbHMpCiAgICAgICAgICAgICAgICAgICAgICAgIGlmIHYgaXMgbm90IE5vbmUpCiAgICAgICAgICAgICAgICBpZiBuID09IDA6CiAgICAgICAgICAgICAgICAgICAgY29udGludWUKCiAgICAgICAgICAgICAgICBpZiBub3QgcGFyYW1zLmRyeV9ydW46CiAgICAgICAgICAgICAgICAgICAgIyBDb2x1bW5hcyBkZSBCQUxBTkNFOiBzb2xvIGVzY3JpYmlyIGVuIG1lcyAwMyAocmVzdHJpY2Npw7NuIGNvbnRhYmxlKQogICAgICAgICAgICAgICAgICAgICMgRUVSUiwgcXVhcnRlciB5IHByZXZfcGVyaW9kIHNlIGVzY3JpYmVuIGVuIGN1YWxxdWllciBtZXMKICAgICAgICAgICAgICAgICAgICBpZiBjb2xfdHlwZSA9PSAiYmFsIiBhbmQgbW0gIT0gIjAzIjoKICAgICAgICAgICAgICAgICAgICAgICAgc2hlZXRfcmVwb3J0LnNldGRlZmF1bHQoImNvbHNfc2tpcHBlZF9iYWxfcmVzdHJpY3Rpb24iLCBbXSkuYXBwZW5kKAogICAgICAgICAgICAgICAgICAgICAgICAgICAgX2NvbF9sZXR0ZXIoZGVzdF9jb2wpCiAgICAgICAgICAgICAgICAgICAgICAgICkKICAgICAgICAgICAgICAgICAgICAgICAgY29udGludWUKICAgICAgICAgICAgICAgICAgICBvaywgbW90aXZvID0gYXdhaXQgX3dyaXRlX2NvbHVtbigKICAgICAgICAgICAgICAgICAgICAgICAgcGFyYW1zLnNwcmVhZHNoZWV0X2lkLCBzaWRfdCwgZGVzdF9jb2wsIHdyaXRlX3ZhbHMKICAgICAgICAgICAgICAgICAgICApCiAgICAgICAgICAgICAgICAgICAgaWYgb2s6CiAgICAgICAgICAgICAgICAgICAgICAgIHNoZWV0X3JlcG9ydFsiY29sc193cml0dGVuIl0gKz0gMQogICAgICAgICAgICAgICAgICAgICAgICByZXBvcnRbInRvdGFsX2NvbHNfd3JpdHRlbiJdICs9IDEKICAgICAgICAgICAgICAgICAgICBlbHNlOgogICAgICAgICAgICAgICAgICAgICAgICBzaGVldF9yZXBvcnQuc2V0ZGVmYXVsdCgiY29sc19mYWlsZWQiLCBbXSkuYXBwZW5kKHsKICAgICAgICAgICAgICAgICAgICAgICAgICAgICJjb2wiOiBfY29sX2xldHRlcihkZXN0X2NvbCksICJtb3Rpdm8iOiBtb3Rpdm8sCiAgICAgICAgICAgICAgICAgICAgICAgIH0pCiAgICAgICAgICAgICAgICAgICAgICAgIHJlcG9ydFsic2hlZXRzX2ZhaWxlZCJdLmFwcGVuZCh7CiAgICAgICAgICAgICAgICAgICAgICAgICAgICAic2hlZXQiOiBzbmFtZSwKICAgICAgICAgICAgICAgICAgICAgICAgICAgICJlcnJvciI6IGYiQ29sIHtfY29sX2xldHRlcihkZXN0X2NvbCl9OiB7bW90aXZvfSIsCiAgICAgICAgICAgICAgICAgICAgICAgIH0pCiAgICAgICAgICAgICAgICAgICAgICAgIHJlcG9ydFsidG90YWxfY29sc19mYWlsZWQiXSArPSAxCiAgICAgICAgICAgICAgICAgICAgY29udGludWUKICAgICAgICAgICAgICAgIGVsc2U6CiAgICAgICAgICAgICAgICAgICAgIyBNb2RvIHZhbGlkYWNpw7NuCiAgICAgICAgICAgICAgICAgICAgZXF1YWwsIGRpZmYsIHNpbl9jb3JyLCBzYW1wbGVzLCBmaWxhc19kZXQgPSAwLCAwLCAwLCBbXSwgW10KICAgICAgICAgICAgICAgICAgICBmb3IgaSBpbiByYW5nZShsZW4oc3JjX3ZhbHMpKToKICAgICAgICAgICAgICAgICAgICAgICAgcm93X3QgPSB0Z3RfY2VsbHNbaV0KICAgICAgICAgICAgICAgICAgICAgICAgaWYgc3JjX3NraXBbaV06CiAgICAgICAgICAgICAgICAgICAgICAgICAgICBjb250aW51ZQogICAgICAgICAgICAgICAgICAgICAgICBpZiBub3Qgc3JjX2NvcnJbaV06CiAgICAgICAgICAgICAgICAgICAgICAgICAgICAjIExhIGZpbGEgbm8gZXhpc3RlIGVuIGVsIGFyY2hpdm8gZnVlbnRlLiBTZSByZXBvcnRhIHBhcmEKICAgICAgICAgICAgICAgICAgICAgICAgICAgICMgcmV2aXNpw7NuIG1hbnVhbCBlbiBsdWdhciBkZSBkZXNjYXJ0YXJsYSBlbiBzaWxlbmNpby4KICAgICAgICAgICAgICAgICAgICAgICAgICAgIF9jID0gX2N2KHJvd190W2Rlc3RfY29sXSkgaWYgZGVzdF9jb2wgPCBsZW4ocm93X3QpIGVsc2UgTm9uZQogICAgICAgICAgICAgICAgICAgICAgICAgICAgaWYgbm90IGlzaW5zdGFuY2UoX2MsIChpbnQsIGZsb2F0KSkgb3IgX2MgPT0gMDoKICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAjIEVuY2FiZXphZG9zIChmZWNoYXMsICJNJCIpLCB0ZXh0byB5IGNlbGRhcyB2YWPDrWFzIG8gZW4KICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAjIGNlcm8gbm8gc29uIGNhbmRpZGF0b3MgYSBjb21wYXJhY2nDs246IG5vIHNvbiBoYWxsYXpnby4KICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICBjb250aW51ZQogICAgICAgICAgICAgICAgICAgICAgICAgICAgc2luX2NvcnIgKz0gMQogICAgICAgICAgICAgICAgICAgICAgICAgICAgaWYgcGFyYW1zLmRldGFsbGVfZmlsYXM6CiAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgZmlsYXNfZGV0LmFwcGVuZCh7CiAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICJmaWxhIjogICAgIGkgKyAxLAogICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAiZXRpcXVldGEiOiBfZXRpcXVldGFfZmlsYShyb3dfdCksCiAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICJkZXN0aW5vIjogIF9jLAogICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAiZnVlbnRlIjogICBOb25lLAogICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAiZXN0YWRvIjogICAiU0lOIENPUlJFU1BPTkRFTkNJQSIsCiAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgfSkKICAgICAgICAgICAgICAgICAgICAgICAgICAgIGNvbnRpbnVlCiAgICAgICAgICAgICAgICAgICAgICAgIHYgPSBzcmNfdmFsc1tpXQogICAgICAgICAgICAgICAgICAgICAgICBpZiB2IGlzIE5vbmU6CiAgICAgICAgICAgICAgICAgICAgICAgICAgICBjb250aW51ZQogICAgICAgICAgICAgICAgICAgICAgICBjdXIgPSBfY3Yocm93X3RbZGVzdF9jb2xdKSBpZiBkZXN0X2NvbCA8IGxlbihyb3dfdCkgZWxzZSBOb25lCiAgICAgICAgICAgICAgICAgICAgICAgIF9jdXJfdmFjaW8gPSBjdXIgaXMgTm9uZSBvciAoaXNpbnN0YW5jZShjdXIsIHN0cikgYW5kIG5vdCBjdXIuc3RyaXAoKSkKICAgICAgICAgICAgICAgICAgICAgICAgaWYgX2N1cl92YWNpbzoKICAgICAgICAgICAgICAgICAgICAgICAgICAgICMgRWwgZGVzdGlubyBlc3TDoSBSRUFMTUVOVEUgZW4gYmxhbmNvIChubyAiMCIsIG5hZGEgZXNjcml0bykuCiAgICAgICAgICAgICAgICAgICAgICAgICAgICAjIEVuIHRvZGFzIGxhcyBub3RhcywgdW5hIGZpbGEgY29uIGRhdG8gcmVhbCBzaWVtcHJlIHRyYWUgdW4KICAgICAgICAgICAgICAgICAgICAgICAgICAgICMgIjAiIGV4cGzDrWNpdG8gY3VhbmRvIG5vIHRpZW5lIG1vbnRvIOKAlCBudW5jYSBxdWVkYSB2YWPDrWEuCiAgICAgICAgICAgICAgICAgICAgICAgICAgICAjIFVuYSBjZWxkYSB2YWPDrWEgZXMgbGEgc2XDsWFsIGRlIHF1ZSBsYSBmaWxhIGVzIHVuIHTDrXR1bG8gbwogICAgICAgICAgICAgICAgICAgICAgICAgICAgIyBzdWJ0w610dWxvIChlai4gIkRldWRvcmVzIHZhcmlvcyIgYW50ZXMgZGUgIkRldWRvcmVzIHZhcmlvcwogICAgICAgICAgICAgICAgICAgICAgICAgICAgIyAoKikuIiksIHF1ZSBubyB0aWVuZSBuYWRhIHByb3BpbyBxdWUgY29tcGFyYXIuIEZvcnphcmxhIGEKICAgICAgICAgICAgICAgICAgICAgICAgICAgICMgMCB5IGNvbXBhcmFybGEgY29udHJhIGxhIGZ1ZW50ZSBnZW5lcmEgZmFsc29zIGhhbGxhemdvcy4KICAgICAgICAgICAgICAgICAgICAgICAgICAgIGNvbnRpbnVlCiAgICAgICAgICAgICAgICAgICAgICAgIGN1cl9udW0gPSBmbG9hdChjdXIpIGlmIGlzaW5zdGFuY2UoY3VyLCAoaW50LCBmbG9hdCkpIGVsc2UgTm9uZQogICAgICAgICAgICAgICAgICAgICAgICAjIFRvbGVyYW5jaWEgMS4wMDAgcGVzb3M6IG1vbnRvcyBzZSBwcmVzZW50YW4gZW4gTSQsCiAgICAgICAgICAgICAgICAgICAgICAgICMgZGlmZXJlbmNpYXMgbWVub3JlcyBhIDEuMDAwIHNvbiBpbnNpZ25pZmljYW50ZXMgKHJlZG9uZGVvKQogICAgICAgICAgICAgICAgICAgICAgICBpZiBjdXJfbnVtIGlzIG5vdCBOb25lIGFuZCBhYnMoY3VyX251bSAtIGZsb2F0KHYpKSA8IDEwMDA6CiAgICAgICAgICAgICAgICAgICAgICAgICAgICBlcXVhbCArPSAxCiAgICAgICAgICAgICAgICAgICAgICAgICAgICBlc3RhZG8gPSAiT0siCiAgICAgICAgICAgICAgICAgICAgICAgIGVsc2U6CiAgICAgICAgICAgICAgICAgICAgICAgICAgICBkaWZmICArPSAxCiAgICAgICAgICAgICAgICAgICAgICAgICAgICBlc3RhZG8gPSAiSEFMTEFaR08iIGlmIGN1cl9udW0gaXMgbm90IE5vbmUgZWxzZSAiTk8gUFJPQ0VTQURPIgogICAgICAgICAgICAgICAgICAgICAgICAgICAgaWYgbGVuKHNhbXBsZXMpIDwgcGFyYW1zLm1heF9lamVtcGxvczoKICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICBzYW1wbGVzLmFwcGVuZCh7ImZpbGEiOiBpICsgMSwgImRlc3Rpbm8iOiBjdXIsICJmdWVudGUiOiB2fSkKICAgICAgICAgICAgICAgICAgICAgICAgaWYgcGFyYW1zLmRldGFsbGVfZmlsYXM6CiAgICAgICAgICAgICAgICAgICAgICAgICAgICBmaWxhc19kZXQuYXBwZW5kKHsKICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAiZmlsYSI6ICAgICBpICsgMSwKICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAiZXRpcXVldGEiOiBfZXRpcXVldGFfZmlsYShyb3dfdCksCiAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgImRlc3Rpbm8iOiAgY3VyLAogICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICJmdWVudGUiOiAgIHYsCiAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgImVzdGFkbyI6ICAgZXN0YWRvLAogICAgICAgICAgICAgICAgICAgICAgICAgICAgfSkKCiAgICAgICAgICAgICAgICAgICAgY29tcDogZGljdFtzdHIsIEFueV0gPSB7CiAgICAgICAgICAgICAgICAgICAgICAgICJjb2wiOiAgICAgICAgICAgIF9jb2xfbGV0dGVyKGRlc3RfY29sKSwKICAgICAgICAgICAgICAgICAgICAgICAgInRpcG8iOiAgICAgICAgICAgY29sX3R5cGUsCiAgICAgICAgICAgICAgICAgICAgICAgICJ2YWxvcmVzX2Z1ZW50ZSI6IG4sCiAgICAgICAgICAgICAgICAgICAgICAgICJpZ3VhbGVzIjogICAgICAgIGVxdWFsLAogICAgICAgICAgICAgICAgICAgICAgICAiZGlzdGludG9zIjogICAgICBkaWZmLAogICAgICAgICAgICAgICAgICAgIH0KICAgICAgICAgICAgICAgICAgICBpZiBzaW5fY29ycjoKICAgICAgICAgICAgICAgICAgICAgICAgY29tcFsic2luX2NvcnJlc3BvbmRlbmNpYSJdID0gc2luX2NvcnIKICAgICAgICAgICAgICAgICAgICBpZiBzYW1wbGVzOgogICAgICAgICAgICAgICAgICAgICAgICBjb21wWyJlamVtcGxvc19kaXN0aW50b3MiXSA9IHNhbXBsZXMKICAgICAgICAgICAgICAgICAgICBpZiBwYXJhbXMuZGV0YWxsZV9maWxhczoKICAgICAgICAgICAgICAgICAgICAgICAga3dfYWN0aXZlID0gewogICAgICAgICAgICAgICAgICAgICAgICAgICAgImJhbCI6IGt3X2JhbCwgImVlcnIiOiBrd19lZXJyLAogICAgICAgICAgICAgICAgICAgICAgICAgICAgInF1YXJ0ZXIiOiBrd19xdWFydGVyLCAicHJldl9wZXJpb2QiOiBrd19wcmV2LAogICAgICAgICAgICAgICAgICAgICAgICB9LmdldChjb2xfdHlwZSwgIiIpCiAgICAgICAgICAgICAgICAgICAgICAgIHRleHRvczogbGlzdFtzdHJdID0gW10KICAgICAgICAgICAgICAgICAgICAgICAgZm9yIHJvd19oIGluIHRndF9jZWxsc1s6OF06CiAgICAgICAgICAgICAgICAgICAgICAgICAgICBmb3IgY19oIGluIChkZXN0X2NvbCwgZGVzdF9jb2wgLSAxLCBkZXN0X2NvbCAtIDIpOgogICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgIGlmIDAgPD0gY19oIDwgbGVuKHJvd19oKToKICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgdCA9IF9jdihyb3dfaFtjX2hdKQogICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICBzID0gc3RyKHQpLnN0cmlwKCkgaWYgdCBpcyBub3QgTm9uZSBlbHNlICIiCiAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgIGlmIChzIGFuZCBzIG5vdCBpbiAoIk0kIiwgIkFncnVwYWRvciIpCiAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgYW5kIG5vdCByZS5mdWxsbWF0Y2gociJcZHs0fS1cZHsyfS1cZHsyfSIsIHMpCiAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgYW5kIChub3Qga3dfYWN0aXZlIG9yIGt3X2FjdGl2ZSBub3QgaW4gcy5sb3dlcigpKQogICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgIGFuZCBzIG5vdCBpbiB0ZXh0b3MpOgogICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgdGV4dG9zLmFwcGVuZChzKQogICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgYnJlYWsKICAgICAgICAgICAgICAgICAgICAgICAgY29tcFsiY29udGV4dG8iXSA9ICIgIi5qb2luKHRleHRvcykKICAgICAgICAgICAgICAgICAgICAgICAgY29tcFsiZmlsYXMiXSAgICA9IGZpbGFzX2RldAoKICAgICAgICAgICAgICAgICAgICBzaGVldF9yZXBvcnQuc2V0ZGVmYXVsdCgiY29tcGFyYWNpb24iLCBbXSkuYXBwZW5kKGNvbXApCiAgICAgICAgICAgICAgICAgICAgc2hlZXRfcmVwb3J0WyJjb2xzX3dyaXR0ZW4iXSArPSAxCiAgICAgICAgICAgICAgICAgICAgcmVwb3J0WyJ0b3RhbF9jZWxsc19lcXVhbCJdID0gcmVwb3J0LmdldCgidG90YWxfY2VsbHNfZXF1YWwiLCAwKSArIGVxdWFsCiAgICAgICAgICAgICAgICAgICAgcmVwb3J0WyJ0b3RhbF9jZWxsc19kaWZmIl0gID0gcmVwb3J0LmdldCgidG90YWxfY2VsbHNfZGlmZiIsIDApICsgZGlmZgogICAgICAgICAgICAgICAgICAgIHJlcG9ydFsidG90YWxfY29sc193cml0dGVuIl0gKz0gMQoKICAgICAgICAgICAgcmVwb3J0WyJzaGVldHNfcHJvY2Vzc2VkIl0uYXBwZW5kKHNoZWV0X3JlcG9ydCkKCiAgICAgICAgaWYgcGFyYW1zLmRyeV9ydW46CiAgICAgICAgICAgIHJlcG9ydFsibWVzc2FnZSJdID0gKAogICAgICAgICAgICAgICAgIk1PRE8gRFJZLVJVTjogTm8gc2UgZXNjcmliacOzIG5hZGEuICIKICAgICAgICAgICAgICAgICJMbGFtYSBjb24gZHJ5X3J1bj1GYWxzZSBwYXJhIGFwbGljYXIgbG9zIGNhbWJpb3MuIgogICAgICAgICAgICApCgogICAgICAgIHJldHVybiBqc29uLmR1bXBzKHJlcG9ydCwgaW5kZW50PTIsIGVuc3VyZV9hc2NpaT1GYWxzZSkKICAgIGV4Y2VwdCBFeGNlcHRpb24gYXMgZToKICAgICAgICByZXR1cm4gX2hhbmRsZV9lcnJvcihlKQoKCiMg4pSA4pSA4pSAIDkuIFZFUklGSUNBUiBTVU1BUyDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIAKCmNsYXNzIFZlcmlmeVN1bXNJbnB1dChCYXNlTW9kZWwpOgogICAgbW9kZWxfY29uZmlnID0gQ29uZmlnRGljdChzdHJfc3RyaXBfd2hpdGVzcGFjZT1UcnVlKQogICAgc3ByZWFkc2hlZXRfaWQ6IHN0ciAgICAgICA9IEZpZWxkKC4uLikKICAgIHNoZWV0X25hbWU6ICAgICBzdHIgICAgICAgPSBGaWVsZCguLi4pCiAgICBzdW1fY29sOiAgICAgICAgaW50ICAgICAgID0gRmllbGQoLi4uLCBnZT0wKQogICAgZGV0YWlsX2NvbHM6ICAgIGxpc3RbaW50XSA9IEZpZWxkKC4uLikKICAgIHRvbGVyYW5jZTogICAgICBmbG9hdCAgICAgPSBGaWVsZChkZWZhdWx0PTEuMCwgZ2U9MCkKICAgIGhlYWRlcl9yb3dzOiAgICBpbnQgICAgICAgPSBGaWVsZChkZWZhdWx0PTUsIGdlPTApCgoKQG1jcC50b29sKG5hbWU9IndvcmtpdmFfdmVyaWZ5X3N1bXMiLAogICAgICAgICAgYW5ub3RhdGlvbnM9eyJyZWFkT25seUhpbnQiOiBUcnVlLCAiZGVzdHJ1Y3RpdmVIaW50IjogRmFsc2UsCiAgICAgICAgICAgICAgICAgICAgICAgImlkZW1wb3RlbnRIaW50IjogVHJ1ZSwgIm9wZW5Xb3JsZEhpbnQiOiBUcnVlfSkKYXN5bmMgZGVmIHdvcmtpdmFfdmVyaWZ5X3N1bXMocGFyYW1zOiBWZXJpZnlTdW1zSW5wdXQpIC0+IHN0cjoKICAgICIiIlZlcmlmaWNhIGFyaXRtw6l0aWNhbWVudGUgc3VidG90YWxlcyB5IHRvdGFsZXMgZGUgdW5hIGhvamEuIiIiCiAgICB0cnk6CiAgICAgICAgc2hlZXRzID0gYXdhaXQgX2dldF9zaGVldHMocGFyYW1zLnNwcmVhZHNoZWV0X2lkKQogICAgICAgIHNpZCAgICA9IHNoZWV0cy5nZXQocGFyYW1zLnNoZWV0X25hbWUpCiAgICAgICAgaWYgbm90IHNpZDoKICAgICAgICAgICAgcmV0dXJuIGYiRXJyb3I6IEhvamEgJ3twYXJhbXMuc2hlZXRfbmFtZX0nIG5vIGVuY29udHJhZGEuIgogICAgICAgIGNlbGxzICAgID0gYXdhaXQgX3JlYWRfc2hlZXRfY2VsbHMocGFyYW1zLnNwcmVhZHNoZWV0X2lkLCBzaWQpCiAgICAgICAgcGFzc19jbnQgPSBmYWlsX2NudCA9IDAKICAgICAgICBmYWlsdXJlczogbGlzdFtkaWN0XSA9IFtdCiAgICAgICAgZm9yIGksIHJvdyBpbiBlbnVtZXJhdGUoY2VsbHNbcGFyYW1zLmhlYWRlcl9yb3dzOl0sIHN0YXJ0PXBhcmFtcy5oZWFkZXJfcm93cyk6CiAgICAgICAgICAgIHRvdGFsX3ZhbCA9IF9jdihyb3dbcGFyYW1zLnN1bV9jb2xdKSBpZiBwYXJhbXMuc3VtX2NvbCA8IGxlbihyb3cpIGVsc2UgTm9uZQogICAgICAgICAgICBpZiBub3QgaXNpbnN0YW5jZSh0b3RhbF92YWwsIChpbnQsIGZsb2F0KSk6CiAgICAgICAgICAgICAgICBjb250aW51ZQogICAgICAgICAgICBkZXRhaWxfc3VtID0gc3VtKAogICAgICAgICAgICAgICAgKF9jdihyb3dbZGNdKSBvciAwKSBmb3IgZGMgaW4gcGFyYW1zLmRldGFpbF9jb2xzCiAgICAgICAgICAgICAgICBpZiBkYyA8IGxlbihyb3cpIGFuZCBpc2luc3RhbmNlKF9jdihyb3dbZGNdKSwgKGludCwgZmxvYXQpKQogICAgICAgICAgICApCiAgICAgICAgICAgIGxhYmVsID0gc3RyKF9jdihyb3dbMV0pIGlmIGxlbihyb3cpID4gMSBlbHNlIGYiZmlsYSB7aSsxfSIpIG9yIGYiZmlsYSB7aSsxfSIKICAgICAgICAgICAgZGlmZiAgPSBhYnModG90YWxfdmFsIC0gZGV0YWlsX3N1bSkKICAgICAgICAgICAgaWYgZGlmZiA8PSBwYXJhbXMudG9sZXJhbmNlOgogICAgICAgICAgICAgICAgcGFzc19jbnQgKz0gMQogICAgICAgICAgICBlbHNlOgogICAgICAgICAgICAgICAgZmFpbF9jbnQgKz0gMQogICAgICAgICAgICAgICAgZmFpbHVyZXMuYXBwZW5kKHsKICAgICAgICAgICAgICAgICAgICAicm93IjogaSArIDEsICJsYWJlbCI6IGxhYmVsLAogICAgICAgICAgICAgICAgICAgICJleHBlY3RlZCI6IHJvdW5kKGRldGFpbF9zdW0sIDIpLAogICAgICAgICAgICAgICAgICAgICJhY3R1YWwiOiAgIHJvdW5kKHRvdGFsX3ZhbCwgMiksCiAgICAgICAgICAgICAgICAgICAgImRpZmYiOiAgICAgcm91bmQoZGlmZiwgMiksCiAgICAgICAgICAgICAgICB9KQogICAgICAgIHJldHVybiBqc29uLmR1bXBzKHsKICAgICAgICAgICAgInNwcmVhZHNoZWV0X2lkIjogcGFyYW1zLnNwcmVhZHNoZWV0X2lkLAogICAgICAgICAgICAic2hlZXRfbmFtZSI6ICAgICBwYXJhbXMuc2hlZXRfbmFtZSwKICAgICAgICAgICAgInN0YXR1cyI6ICAgICAgICAgIk9LIiBpZiBmYWlsX2NudCA9PSAwIGVsc2UgIkRJRkVSRU5DSUFTIEVOQ09OVFJBREFTIiwKICAgICAgICAgICAgInBhc3NfY291bnQiOiAgICAgcGFzc19jbnQsICJmYWlsX2NvdW50IjogZmFpbF9jbnQsCiAgICAgICAgICAgICJ0b2xlcmFuY2UiOiAgICAgIHBhcmFtcy50b2xlcmFuY2UsICJmYWlsdXJlcyI6IGZhaWx1cmVzLAogICAgICAgIH0sIGluZGVudD0yLCBlbnN1cmVfYXNjaWk9RmFsc2UpCiAgICBleGNlcHQgRXhjZXB0aW9uIGFzIGU6CiAgICAgICAgcmV0dXJuIF9oYW5kbGVfZXJyb3IoZSkKCgojIOKUgOKUgOKUgCAxMC4gQ1JVWkFSIE5PVEFTIENPTiBFU1RBRE8gUFJJTUFSSU8g4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSACgpjbGFzcyBDaGVja05vdGVDb25zaXN0ZW5jeUlucHV0KEJhc2VNb2RlbCk6CiAgICBtb2RlbF9jb25maWcgPSBDb25maWdEaWN0KHN0cl9zdHJpcF93aGl0ZXNwYWNlPVRydWUpCiAgICBzcHJlYWRzaGVldF9pZDogc3RyICAgPSBGaWVsZCguLi4pCiAgICBwcmltYXJ5X3NoZWV0OiAgc3RyICAgPSBGaWVsZCguLi4pCiAgICBub3RlX3NoZWV0OiAgICAgc3RyICAgPSBGaWVsZCguLi4pCiAgICBwcmltYXJ5X2NvbDogICAgaW50ICAgPSBGaWVsZCguLi4sIGdlPTApCiAgICBub3RlX2NvbDogICAgICAgaW50ICAgPSBGaWVsZCguLi4sIGdlPTApCiAgICBwcmltYXJ5X3JvdzogICAgaW50ICAgPSBGaWVsZCguLi4sIGdlPTApCiAgICBub3RlX3RvdGFsX3JvdzogaW50ICAgPSBGaWVsZCguLi4sIGdlPTApCiAgICB0b2xlcmFuY2U6ICAgICAgZmxvYXQgPSBGaWVsZChkZWZhdWx0PTEuMCwgZ2U9MCkKICAgIGxhYmVsOiAgICAgICAgICBzdHIgICA9IEZpZWxkKGRlZmF1bHQ9IkNydWNlIikKCgpAbWNwLnRvb2wobmFtZT0id29ya2l2YV9jaGVja19ub3RlX2NvbnNpc3RlbmN5IiwKICAgICAgICAgIGFubm90YXRpb25zPXsicmVhZE9ubHlIaW50IjogVHJ1ZSwgImRlc3RydWN0aXZlSGludCI6IEZhbHNlLAogICAgICAgICAgICAgICAgICAgICAgICJpZGVtcG90ZW50SGludCI6IFRydWUsICJvcGVuV29ybGRIaW50IjogVHJ1ZX0pCmFzeW5jIGRlZiB3b3JraXZhX2NoZWNrX25vdGVfY29uc2lzdGVuY3kocGFyYW1zOiBDaGVja05vdGVDb25zaXN0ZW5jeUlucHV0KSAtPiBzdHI6CiAgICAiIiJDcnV6YSB1biB2YWxvciBlbnRyZSBlc3RhZG8gcHJpbWFyaW8geSBub3RhLiIiIgogICAgdHJ5OgogICAgICAgIHNoZWV0cyA9IGF3YWl0IF9nZXRfc2hlZXRzKHBhcmFtcy5zcHJlYWRzaGVldF9pZCkKCiAgICAgICAgYXN5bmMgZGVmIF9nZXRfdmFsKHNoZWV0X25hbWU6IHN0ciwgcm93OiBpbnQsIGNvbDogaW50KSAtPiBmbG9hdCB8IE5vbmU6CiAgICAgICAgICAgIHNpZCA9IHNoZWV0cy5nZXQoc2hlZXRfbmFtZSkKICAgICAgICAgICAgaWYgbm90IHNpZDoKICAgICAgICAgICAgICAgIHJldHVybiBOb25lCiAgICAgICAgICAgIGNlbGxzID0gYXdhaXQgX3JlYWRfc2hlZXRfY2VsbHMocGFyYW1zLnNwcmVhZHNoZWV0X2lkLCBzaWQpCiAgICAgICAgICAgIGlmIHJvdyA+PSBsZW4oY2VsbHMpOgogICAgICAgICAgICAgICAgcmV0dXJuIE5vbmUKICAgICAgICAgICAgcm93X2RhdGEgPSBjZWxsc1tyb3ddCiAgICAgICAgICAgIHYgPSBfY3Yocm93X2RhdGFbY29sXSkgaWYgY29sIDwgbGVuKHJvd19kYXRhKSBlbHNlIE5vbmUKICAgICAgICAgICAgcmV0dXJuIGZsb2F0KHYpIGlmIGlzaW5zdGFuY2UodiwgKGludCwgZmxvYXQpKSBlbHNlIE5vbmUKCiAgICAgICAgcHJpbWFyeV92YWwgPSBhd2FpdCBfZ2V0X3ZhbChwYXJhbXMucHJpbWFyeV9zaGVldCwgcGFyYW1zLnByaW1hcnlfcm93LCBwYXJhbXMucHJpbWFyeV9jb2wpCiAgICAgICAgbm90ZV92YWwgICAgPSBhd2FpdCBfZ2V0X3ZhbChwYXJhbXMubm90ZV9zaGVldCwgcGFyYW1zLm5vdGVfdG90YWxfcm93LCBwYXJhbXMubm90ZV9jb2wpCgogICAgICAgIGlmIHByaW1hcnlfdmFsIGlzIE5vbmU6CiAgICAgICAgICAgIHJldHVybiBmIkVycm9yOiBObyBzZSBwdWRvIGxlZXIge3BhcmFtcy5wcmltYXJ5X3NoZWV0fSBmaWxhIHtwYXJhbXMucHJpbWFyeV9yb3crMX0iCiAgICAgICAgaWYgbm90ZV92YWwgaXMgTm9uZToKICAgICAgICAgICAgcmV0dXJuIGYiRXJyb3I6IE5vIHNlIHB1ZG8gbGVlciB7cGFyYW1zLm5vdGVfc2hlZXR9IGZpbGEge3BhcmFtcy5ub3RlX3RvdGFsX3JvdysxfSIKCiAgICAgICAgZGlmZiAgID0gYWJzKHByaW1hcnlfdmFsIC0gbm90ZV92YWwpCiAgICAgICAgcGFzc2VkID0gZGlmZiA8PSBwYXJhbXMudG9sZXJhbmNlCiAgICAgICAgcmV0dXJuIGpzb24uZHVtcHMoewogICAgICAgICAgICAibGFiZWwiOiBwYXJhbXMubGFiZWwsICJzdGF0dXMiOiAiUEFTUyIgaWYgcGFzc2VkIGVsc2UgIkZBSUwiLAogICAgICAgICAgICAicHJpbWFyeV9zaGVldCI6IHBhcmFtcy5wcmltYXJ5X3NoZWV0LCAibm90ZV9zaGVldCI6IHBhcmFtcy5ub3RlX3NoZWV0LAogICAgICAgICAgICAicHJpbWFyeV92YWx1ZSI6IHJvdW5kKHByaW1hcnlfdmFsLCAyKSwgIm5vdGVfdmFsdWUiOiByb3VuZChub3RlX3ZhbCwgMiksCiAgICAgICAgICAgICJkaWZmIjogcm91bmQoZGlmZiwgMiksICJ0b2xlcmFuY2UiOiBwYXJhbXMudG9sZXJhbmNlLAogICAgICAgIH0sIGluZGVudD0yLCBlbnN1cmVfYXNjaWk9RmFsc2UpCiAgICBleGNlcHQgRXhjZXB0aW9uIGFzIGU6CiAgICAgICAgcmV0dXJuIF9oYW5kbGVfZXJyb3IoZSkKCgojIOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkAojIEVOVFJZIFBPSU5UCiMg4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQ4pWQCgppZiBfX25hbWVfXyA9PSAiX19tYWluX18iOgogICAgaWYgbm90IENMSUVOVF9JRCBvciBub3QgQ0xJRU5UX1NFQ1JFVDoKICAgICAgICBpbXBvcnQgc3lzCiAgICAgICAgcHJpbnQoIkVSUk9SOiBGYWx0YSBXT1JLSVZBX0NMSUVOVF9JRCBvIFdPUktJVkFfQ0xJRU5UX1NFQ1JFVCBlbiAuZW52IiwKICAgICAgICAgICAgICBmaWxlPXN5cy5zdGRlcnIpCiAgICAgICAgc3lzLmV4aXQoMSkKICAgIG1jcC5ydW4oKQo="
).decode("utf-8")

_LLENAR_V2_SRC = base64.b64decode(
    b"IyEvdXNyL2Jpbi9lbnYgcHl0aG9uMwoiIiIKbGxlbmFkb19jb21wYXJhdGl2b3NWMl9lc3Blam8ucHkgIOKGkCAgRVNQRUpPIHF1ZSB1c2Egd29ya2l2YV9tY3BfdjIucHkKPT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PQpJZMOpbnRpY28gYSBsbGVuYWRvX2NvbXBhcmF0aXZvc1YyLnB5IHBlcm8gY2FyZ2Egd29ya2l2YV9tY3BfdjIucHkKZW4gbHVnYXIgZGUgd29ya2l2YV9tY3AucHkgcGFyYToKICAtIERldGVjdGFyIHkgbGxlbmFyIGNvbHVtbmFzIEVFUlIgKGhvamEgQyB5IGVxdWl2YWxlbnRlcykgZW4gUTIvUTMvUTQuCiAgLSBSZXN0cmljY2nDs24gbWVzIDAzIGFwbGljYSBzb2xvIGEgY29sdW1uYXMgZGUgQkFMQU5DRS4KClVTTzoKICAgIHB5dGhvbiBsbGVuYWRvX2NvbXBhcmF0aXZvc1YyX2VzcGVqby5weSAtLW1lcyAwOSAtLWFuaW8gMjAyNgogICAgcHl0aG9uIGxsZW5hZG9fY29tcGFyYXRpdm9zVjJfZXNwZWpvLnB5IC0tbWVzIDA5IC0tYW5pbyAyMDI2IC0tZHJ5LXJ1bgogICAgcHl0aG9uIGxsZW5hZG9fY29tcGFyYXRpdm9zVjJfZXNwZWpvLnB5IC0tbWVzIDA5IC0tYW5pbyAyMDI2IC0tc29sbyBFMjAwCgpSRVFVSVNJVE9TOgogICAgLSB3b3JraXZhX21jcF92Mi5weSBlbiBsYSBtaXNtYSBjYXJwZXRhCiAgICAtIC5lbnYgY29uIGxhcyBjcmVkZW5jaWFsZXMgZW4gbGEgbWlzbWEgY2FycGV0YQoiIiIKCmZyb20gX19mdXR1cmVfXyBpbXBvcnQgYW5ub3RhdGlvbnMKCmltcG9ydCBhcmdwYXJzZQppbXBvcnQgYXN5bmNpbwppbXBvcnQgaW1wb3J0bGliLnV0aWwKaW1wb3J0IGpzb24KaW1wb3J0IHJlCmltcG9ydCBzeXMKaW1wb3J0IHRpbWUKZnJvbSBwYXRobGliIGltcG9ydCBQYXRoCgoKIyDilIDilIAgQ2FyZ2FyIHdvcmtpdmFfbWNwX3YyIGRlc2RlIGxhIG1pc21hIGNhcnBldGEg4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSACgpkZWYgX2xvYWRfbWNwKCk6CiAgICBoZXJlICAgICA9IFBhdGgoX19maWxlX18pLnBhcmVudAogICAgbWNwX3BhdGggPSBoZXJlIC8gIndvcmtpdmFfbWNwX3YyLnB5IgogICAgaWYgbm90IG1jcF9wYXRoLmV4aXN0cygpOgogICAgICAgIHByaW50KGYiRVJST1I6IE5vIHNlIGVuY3VlbnRyYSB7bWNwX3BhdGh9IikKICAgICAgICBzeXMuZXhpdCgxKQogICAgc3BlYyA9IGltcG9ydGxpYi51dGlsLnNwZWNfZnJvbV9maWxlX2xvY2F0aW9uKCJ3b3JraXZhX21jcF92MiIsIG1jcF9wYXRoKQogICAgbW9kICA9IGltcG9ydGxpYi51dGlsLm1vZHVsZV9mcm9tX3NwZWMoc3BlYykKICAgIHN5cy5tb2R1bGVzWyJ3b3JraXZhX21jcF92MiJdID0gbW9kCiAgICBzcGVjLmxvYWRlci5leGVjX21vZHVsZShtb2QpCiAgICByZXR1cm4gbW9kCgoKX1BSRUZJWF9SRSA9IHJlLmNvbXBpbGUociJeXHMqXChbXildKlwpXHMqIikKCgpkZWYgX3N0cmlwX3ByZWZpeChuYW1lOiBzdHIpIC0+IHN0cjoKICAgIHJldHVybiBfUFJFRklYX1JFLnN1YigiIiwgbmFtZSBvciAiIikuc3RyaXAoKQoKCk1FU19QT1JfVFJJTUVTVFJFID0gewogICAgIlExIjogIjAzIiwgIlEyIjogIjA2IiwgIlEzIjogIjA5IiwgIlE0IjogIjEyIiwKICAgICIxIjogIjAzIiwgIjIiOiAiMDYiLCAiMyI6ICIwOSIsICI0IjogIjEyIiwKICAgICIwMyI6ICIwMyIsICIwNiI6ICIwNiIsICIwOSI6ICIwOSIsICIxMiI6ICIxMiIsCn0KCgojIOKUgOKUgCBNb2RvIGludGVyYWN0aXZvIOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgAoKZGVmIF9wZWRpcih0ZXh0bzogc3RyLCB2YWxpZGFyLCBkZWZhdWx0OiBzdHIgfCBOb25lID0gTm9uZSkgLT4gc3RyOgogICAgd2hpbGUgVHJ1ZToKICAgICAgICB2ID0gaW5wdXQodGV4dG8pCiAgICAgICAgZm9yIGJvbSBpbiAoY2hyKDB4RkVGRiksIGNocigweEVGKSArIGNocigweEJCKSArIGNocigweEJGKSk6CiAgICAgICAgICAgIHYgPSB2LnJlbW92ZXByZWZpeChib20pCiAgICAgICAgdiA9IHYuc3RyaXAoKQogICAgICAgIGlmIG5vdCB2IGFuZCBkZWZhdWx0IGlzIG5vdCBOb25lOgogICAgICAgICAgICByZXR1cm4gZGVmYXVsdAogICAgICAgIGlmIHZhbGlkYXIodik6CiAgICAgICAgICAgIHJldHVybiB2CiAgICAgICAgcHJpbnQoIiAgIFZhbG9yIG5vIHbDoWxpZG8sIGludGVudGEgZGUgbnVldm8uIikKCgpkZWYgcGVkaXJfb3BjaW9uZXMoKSAtPiB0dXBsZVtzdHIsIHN0ciwgYm9vbCwgc3RyIHwgTm9uZSwgaW50XToKICAgIHByaW50KCI9PT0gTGxlbmFkbyBkZSBDb21wYXJhdGl2b3MgVjIgRXNwZWpvIChFRVJSKSDigJQgbW9kbyBpbnRlcmFjdGl2byA9PT1cbiIpCiAgICBtZXNfcmF3ID0gX3BlZGlyKAogICAgICAgICJUcmltZXN0cmUgbyBtZXMgIChRMS9RMi9RMy9RNCAgbyAgMDMvMDYvMDkvMTIpOiAiLAogICAgICAgIGxhbWJkYSB2OiB2LnVwcGVyKCkgaW4gTUVTX1BPUl9UUklNRVNUUkUsCiAgICApCiAgICBtZXMgID0gTUVTX1BPUl9UUklNRVNUUkVbbWVzX3Jhdy51cHBlcigpXQogICAgYW5pbyA9IF9wZWRpcigiQcOxbyAoZWogMjAyNik6ICIsCiAgICAgICAgICAgICAgICAgIGxhbWJkYSB2OiByZS5mdWxsbWF0Y2gociJcZHs0fSIsIHYpIGlzIG5vdCBOb25lKQogICAgbW9kbyA9IF9wZWRpcigKICAgICAgICAiTW9kbyAgWzFdIERSWS1SVU4gKHNpbXVsYWNpw7NuKSAgWzJdIEVTQ1JJVFVSQSBSRUFMICAoRW50ZXIgPSBEUlktUlVOKTogIiwKICAgICAgICBsYW1iZGEgdjogdiBpbiAoIjEiLCAiMiIpLAogICAgICAgIGRlZmF1bHQ9IjEiLAogICAgKQogICAgZHJ5X3J1biAgPSAobW9kbyA9PSAiMSIpCiAgICBzb2xvX3JhdyA9IF9wZWRpcigiU29jaWVkYWQgZXNwZWPDrWZpY2EgKGVqIEUyMTUpIG8gRW50ZXIgcGFyYSBUT0RBUzogIiwKICAgICAgICAgICAgICAgICAgICAgIGxhbWJkYSB2OiBUcnVlLCBkZWZhdWx0PSIiKQogICAgc29sbyAgICAgPSBzb2xvX3Jhdy5zdHJpcCgpIG9yIE5vbmUKICAgIGxvdGVfcmF3ID0gX3BlZGlyKCJIb2phcyBwb3IgbG90ZSAoRW50ZXIgPSA1MCk6ICIsCiAgICAgICAgICAgICAgICAgICAgICBsYW1iZGEgdjogdi5pc2RpZ2l0KCkgYW5kIDEgPD0gaW50KHYpIDw9IDEwMCwgZGVmYXVsdD0iNTAiKQogICAgbG90ZSAgICAgPSBpbnQobG90ZV9yYXcpCiAgICBwcmludCgpCiAgICByZXR1cm4gbWVzLCBhbmlvLCBkcnlfcnVuLCBzb2xvLCBsb3RlCgoKIyDilIDilIAgUHJvY2VzYXIgdW4gYXJjaGl2byBjb21wbGV0byAoY29uIHBhZ2luYWNpw7NuKSDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIAKCmFzeW5jIGRlZiBfcHJvY2VzYXJfYXJjaGl2byhtY3AsIGZpZDogc3RyLCBub21icmU6IHN0ciwKICAgICAgICAgICAgICAgICAgICAgICAgICAgICBkcnlfcnVuOiBib29sLCBsb3RlOiBpbnQsCiAgICAgICAgICAgICAgICAgICAgICAgICAgICAgaG9qYTogc3RyIHwgTm9uZSA9IE5vbmUsCiAgICAgICAgICAgICAgICAgICAgICAgICAgICAgc2hvdWxkX3N0b3A9Tm9uZSkgLT4gZGljdDoKICAgIG9mZnNldCAgICAgICA9IDAKICAgIHRvdGFsX2NvbHMgICA9IDAKICAgIHRvdGFsX2hvamFzICA9IDAKICAgIGVuY2FiZXphZG8gICA9IEZhbHNlCiAgICBibG9xdWVhZGFzX2FsbDogbGlzdFtkaWN0XSA9IFtdCgogICAgd2hpbGUgVHJ1ZToKICAgICAgICAjIENvcnRlIHNvbGljaXRhZG8gcG9yIGVsIHVzdWFyaW8uIFNlIGV2YWx1YSBlbnRyZSBsb3RlcyAobm8gYSBtaXRhZAogICAgICAgICMgZGUgdW5vKSBwYXJhIG5vIGRlamFyIHVuYSBlc2NyaXR1cmEgcGFyY2lhbCBlbiBXb3JraXZhLgogICAgICAgIGlmIHNob3VsZF9zdG9wIGlzIG5vdCBOb25lIGFuZCBzaG91bGRfc3RvcCgpOgogICAgICAgICAgICBwcmludCgiICDij7kgRGV0ZW5pZG8gcG9yIGVsIHVzdWFyaW8uIikKICAgICAgICAgICAgcmV0dXJuIHsKICAgICAgICAgICAgICAgICJlc3RhZG8iOiAgICJkZXRlbmlkbyIsCiAgICAgICAgICAgICAgICAiZGV0YWxsZSI6ICBmIkRldGVuaWRvIHBvciBlbCB1c3VhcmlvIHRyYXMge3RvdGFsX2NvbHN9IGNvbHVtbmEocykgZXNjcml0YShzKS4iLAogICAgICAgICAgICAgICAgImhvamFzIjogICAgdG90YWxfaG9qYXMsCiAgICAgICAgICAgICAgICAiY29sdW1uYXMiOiB0b3RhbF9jb2xzLAogICAgICAgICAgICB9CgogICAgICAgIG1jcC5fd2suX2NsaWVudCA9IE5vbmUKICAgICAgICBwYXJhbXMgPSBtY3AuRmlsbENvbXBhcmF0aXZlc0lucHV0KAogICAgICAgICAgICBzcHJlYWRzaGVldF9pZD1maWQsCiAgICAgICAgICAgIGRyeV9ydW49ZHJ5X3J1biwKICAgICAgICAgICAgc2hlZXRfb2Zmc2V0PW9mZnNldCwKICAgICAgICAgICAgbWF4X3NoZWV0cz1sb3RlLAogICAgICAgICAgICBpbmNsdWRlX3NoZWV0cz1baG9qYV0gaWYgaG9qYSBlbHNlIFtdLAogICAgICAgICkKICAgICAgICByYXcgPSBhd2FpdCBtY3Aud29ya2l2YV9maWxsX2NvbXBhcmF0aXZlcyhwYXJhbXMpCgogICAgICAgIHRyeToKICAgICAgICAgICAgciA9IGpzb24ubG9hZHMocmF3KQogICAgICAgIGV4Y2VwdCBqc29uLkpTT05EZWNvZGVFcnJvcjoKICAgICAgICAgICAgcmV0dXJuIHsiZXN0YWRvIjogImVycm9yIiwgImRldGFsbGUiOiBmIlJlc3B1ZXN0YSBuby1KU09OOiB7cmF3WzoyMDBdfSJ9CgogICAgICAgIGlmICJ3YXJuaW5nIiBpbiByOgogICAgICAgICAgICByZXR1cm4geyJlc3RhZG8iOiAid2FybmluZyIsICJkZXRhbGxlIjogclsid2FybmluZyJdfQoKICAgICAgICBpZiAibWVzc2FnZSIgaW4gciBhbmQgInNoZWV0X29mZnNldCIgbm90IGluIHI6CiAgICAgICAgICAgIHJldHVybiB7ImVzdGFkbyI6ICJ3YXJuaW5nIiwgImRldGFsbGUiOiByWyJtZXNzYWdlIl19CgogICAgICAgIGlmIG5vdCBlbmNhYmV6YWRvOgogICAgICAgICAgICBjYW5kaWRhdGFzID0gci5nZXQoInRvdGFsX2NhbmRpZGF0ZV9zaGVldHMiLCAiPyIpCiAgICAgICAgICAgIHByaW50KGYiICBQZXLDrW9kbyBhY3R1YWwgIDoge3IuZ2V0KCdjdXJyZW50X2VuZCcsICc/Jyl9IikKICAgICAgICAgICAgcHJpbnQoZiIgIFBlcsOtb2RvIGNvbXAuICAgOiB7ci5nZXQoJ3ByaW9yX2VuZCcsICc/Jyl9IikKICAgICAgICAgICAgcHJpbnQoZiIgIEZ1ZW50ZSBiYWxhbmNlICA6IHtyLmdldCgnc291cmNlX2JhbGFuY2UnLCAnPycpfSIpCiAgICAgICAgICAgIHByaW50KGYiICBGdWVudGUgRUVSUiAgICAgOiB7ci5nZXQoJ3NvdXJjZV9lZXJyJywgJ05vIGVuY29udHJhZG8nKX0iKQogICAgICAgICAgICBwcmludChmIiAgRnVlbnRlIHByZXYgcGVyLjoge3IuZ2V0KCdzb3VyY2VfcHJldl9wZXJpb2QnLCAnTm8gZW5jb250cmFkbycpfSIpCiAgICAgICAgICAgIHByaW50KGYiICBGdWVudGUgY3VyciBwcmV2OiB7ci5nZXQoJ3NvdXJjZV9jdXJyX3ByZXYnLCAnTm8gZW5jb250cmFkbycpfSIpCiAgICAgICAgICAgIHByaW50KGYiICBIb2phcyBjYW5kaWRhdGFzOiB7Y2FuZGlkYXRhc30iCiAgICAgICAgICAgICAgICAgIGYiIChleGNsdWlkb3Mge3IuZ2V0KCdza2lwcGVkX2Rlc2dsb3NlX3NvY2llZGFkJywgMCl9IGRlc2dsb3NlcykiKQogICAgICAgICAgICBlbmNhYmV6YWRvID0gVHJ1ZQoKICAgICAgICBob2phc19sb3RlICA9IGxlbihyLmdldCgic2hlZXRzX3Byb2Nlc3NlZCIsIFtdKSkKICAgICAgICBjb2xzX2xvdGUgICA9IHIuZ2V0KCJ0b3RhbF9jb2xzX3dyaXR0ZW4iLCAwKQogICAgICAgIHRvdGFsX2hvamFzICs9IGhvamFzX2xvdGUKICAgICAgICB0b3RhbF9jb2xzICArPSBjb2xzX2xvdGUKCiAgICAgICAgYWNjaW9uID0gInNpbXVsYWRhcyIgaWYgZHJ5X3J1biBlbHNlICJlc2NyaXRhcyIKICAgICAgICBwcmludChmIiAgbG90ZSBvZmZzZXQge3IuZ2V0KCdzaGVldF9vZmZzZXQnLCBvZmZzZXQpOj4zfTogIgogICAgICAgICAgICAgIGYie3IuZ2V0KCdiYXRjaF9zaXplJywgaG9qYXNfbG90ZSl9IGhvamFzIHwge2NvbHNfbG90ZX0gY29sdW1uYXMge2FjY2lvbn0iKQoKICAgICAgICBmYWxsaWRhcyAgPSByLmdldCgic2hlZXRzX2ZhaWxlZCIsIFtdKQogICAgICAgIGNvbHNfZmFpbCA9IHIuZ2V0KCJ0b3RhbF9jb2xzX2ZhaWxlZCIsIDApCiAgICAgICAgaWYgZmFsbGlkYXMgb3IgY29sc19mYWlsOgogICAgICAgICAgICBibG9xdWVhZGFzICAgID0gW2YgZm9yIGYgaW4gZmFsbGlkYXMgaWYgIkJMT1FVRUFEQSIgaW4gKGYuZ2V0KCJlcnJvciIpIG9yICIiKV0KICAgICAgICAgICAgbm9fYmxvcXVlYWRhcyA9IFtmIGZvciBmIGluIGZhbGxpZGFzIGlmIGYgbm90IGluIGJsb3F1ZWFkYXNdCiAgICAgICAgICAgIHByaW50KGYiICDinJcgRXJyb3JlcyBlbiBsb3RlOiB7bGVuKGZhbGxpZGFzKX0gaG9qYXMsIHtjb2xzX2ZhaWx9IGNvbHMgZmFsbGlkYXMiKQogICAgICAgICAgICBmb3IgZiBpbiBmYWxsaWRhc1s6OF06CiAgICAgICAgICAgICAgICBwcmludChmIiAgICAgIMK3IHtmLmdldCgnc2hlZXQnKX06IHtmLmdldCgnZXJyb3InKX0iKQoKICAgICAgICAgICAgaWYgbm9fYmxvcXVlYWRhczoKICAgICAgICAgICAgICAgICMgRmFsbGEgbm8gcmVsYWNpb25hZGEgYSBibG9xdWVvIChwb3NpYmxlIHRyYW5zaXRvcmlhKSDigJQKICAgICAgICAgICAgICAgICMgc2UgcmVpbnRlbnRhIGVsIGFyY2hpdm8gY29tcGxldG8sIGNvbW8gYW50ZXMuCiAgICAgICAgICAgICAgICByZXR1cm4gewogICAgICAgICAgICAgICAgICAgICJlc3RhZG8iOiAgICJpbmNvbXBsZXRvIiwKICAgICAgICAgICAgICAgICAgICAiZGV0YWxsZSI6ICAoCiAgICAgICAgICAgICAgICAgICAgICAgIGYie3RvdGFsX2NvbHN9IGNvbHVtbmFzIHthY2Npb259OyAiCiAgICAgICAgICAgICAgICAgICAgICAgIGYie2xlbihmYWxsaWRhcyl9IGhvamEocykgY29uIGVycm9yIGVuIGxvdGUgb2Zmc2V0IHtvZmZzZXR9OiAiCiAgICAgICAgICAgICAgICAgICAgICAgICsgIiwgIi5qb2luKGYuZ2V0KCJzaGVldCIsICI/IikgZm9yIGYgaW4gZmFsbGlkYXNbOjVdKQogICAgICAgICAgICAgICAgICAgICksCiAgICAgICAgICAgICAgICAgICAgImhvamFzIjogICAgdG90YWxfaG9qYXMsCiAgICAgICAgICAgICAgICAgICAgImNvbHVtbmFzIjogdG90YWxfY29scywKICAgICAgICAgICAgICAgIH0KCiAgICAgICAgICAgICMgQ2VsZGEocykgYmxvcXVlYWRhL3Byb3RlZ2lkYTogbm8gZXMgdHJhbnNpdG9yaW8sIHJlaW50ZW50YXIgbm8KICAgICAgICAgICAgIyBzaXJ2ZSDigJQgc2UgcmVnaXN0cmEgeSBzZSBzaWd1ZSBjb24gZWwgcmVzdG8gZGUgaG9qYXMgZGVsIGFyY2hpdm8uCiAgICAgICAgICAgIGJsb3F1ZWFkYXNfYWxsLmV4dGVuZChibG9xdWVhZGFzKQoKICAgICAgICBpZiBub3Qgci5nZXQoImhhc19tb3JlIik6CiAgICAgICAgICAgIGJyZWFrCiAgICAgICAgb2Zmc2V0ID0gclsibmV4dF9vZmZzZXQiXQoKICAgIGlmIGJsb3F1ZWFkYXNfYWxsOgogICAgICAgIG5fY2VsZGFzID0gMAogICAgICAgIGZvciBmIGluIGJsb3F1ZWFkYXNfYWxsOgogICAgICAgICAgICBtID0gcmUuc2VhcmNoKHIiQ2VsZGFcKHNcKVxzKyguKz8pXHMrbm8gc2UgYWN0dWFsaXphcm9uIiwgZi5nZXQoImVycm9yIikgb3IgIiIpCiAgICAgICAgICAgIG5fY2VsZGFzICs9IGxlbihtLmdyb3VwKDEpLnNwbGl0KCIsIikpIGlmIG0gZWxzZSAxCiAgICAgICAgcmV0dXJuIHsKICAgICAgICAgICAgImVzdGFkbyI6ICAgImVycm9yIiwKICAgICAgICAgICAgImRldGFsbGUiOiAgKAogICAgICAgICAgICAgICAgZiJ7bl9jZWxkYXN9IGNlbGRhKHMpIGVuIHtsZW4oYmxvcXVlYWRhc19hbGwpfSBjb2x1bW5hKHMpICIKICAgICAgICAgICAgICAgIGYiQkxPUVVFQURBKFMpL1BST1RFR0lEQShTKSBlbiBXb3JraXZhOiAiCiAgICAgICAgICAgICAgICArICIgfCAiLmpvaW4oZiJ7Zi5nZXQoJ3NoZWV0Jyl9IC0+IHtmLmdldCgnZXJyb3InKX0iIGZvciBmIGluIGJsb3F1ZWFkYXNfYWxsKQogICAgICAgICAgICApLAogICAgICAgICAgICAiaG9qYXMiOiAgICB0b3RhbF9ob2phcywKICAgICAgICAgICAgImNvbHVtbmFzIjogdG90YWxfY29scywKICAgICAgICB9CgogICAgZXN0YWRvID0gIm9rIiBpZiB0b3RhbF9jb2xzID4gMCBlbHNlICJzaW5fY2FtYmlvcyIKICAgIHJldHVybiB7ImVzdGFkbyI6IGVzdGFkbywgImhvamFzIjogdG90YWxfaG9qYXMsICJjb2x1bW5hcyI6IHRvdGFsX2NvbHN9CgoKIyDilIDilIAgUnVubmVyIHByaW5jaXBhbCDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIAKCmFzeW5jIGRlZiBydW4obWVzOiBzdHIsIGFuaW86IHN0ciwgZHJ5X3J1bjogYm9vbCwgc29sbzogc3RyIHwgTm9uZSwgbG90ZTogaW50LAogICAgICAgICAgICAgIGhvamE6IHN0ciB8IE5vbmUgPSBOb25lKSAtPiBpbnQ6CiAgICBtY3AgPSBfbG9hZF9tY3AoKQoKICAgIHByaW50KCI9IiAqIDY1KQogICAgcHJpbnQoZiIgIExsZW5hZG8gQ29tcGFyYXRpdm9zIFYyIEVzcGVqbyAoRUVSUikg4oCUIHttZXN9LXthbmlvfSIpCiAgICBwcmludChmIiAgTW9kbyAgOiB7J0RSWS1SVU4gKHNpbXVsYWNpw7NuKScgaWYgZHJ5X3J1biBlbHNlICdFU0NSSVRVUkEgUkVBTCd9IikKICAgIHByaW50KGYiICBMb3RlICA6IHtsb3RlfSBob2phcyBwb3IgbGxhbWFkYSIpCiAgICBpZiBzb2xvOgogICAgICAgIHByaW50KGYiICBGaWx0cm86IHNvbG8ge3NvbG99IikKICAgIGlmIGhvamE6CiAgICAgICAgcHJpbnQoZiIgIEhvamEgIDogc29sbyAne2hvamF9JyIpCiAgICBwcmludCgiPSIgKiA2NSkKCiAgICBwcmludCgiXG5CdXNjYW5kbyBhcmNoaXZvcyBJTkQuLi4iKQogICAgbWNwLl93ay5fY2xpZW50ID0gTm9uZQogICAgYWxsX2ZpbGVzID0gYXdhaXQgbWNwLl9sb2FkX2FsbF9maWxlcygpCgogICAgcGF0cm9uICAgID0gcmUuY29tcGlsZShyZiJeRVxkK19JTkRfe21lc31bLV9de2FuaW99X0Jhc2UgTm90YXMgLiskIiwgcmUuSUdOT1JFQ0FTRSkKICAgIHNvbG9fY29kZSA9IGYiRXtzb2xvLnVwcGVyKCkubHN0cmlwKCdFJyl9XyIgaWYgc29sbyBlbHNlIE5vbmUKCiAgICBhcmNoaXZvcyA9IFtdCiAgICBmb3IgbmFtZSwgZmlkIGluIGFsbF9maWxlcy5pdGVtcygpOgogICAgICAgIGNsZWFuID0gX3N0cmlwX3ByZWZpeChuYW1lKQogICAgICAgIGlmIG5vdCBwYXRyb24ubWF0Y2goY2xlYW4pOgogICAgICAgICAgICBjb250aW51ZQogICAgICAgIGlmIHNvbG9fY29kZSBhbmQgbm90IGNsZWFuLnVwcGVyKCkuc3RhcnRzd2l0aChzb2xvX2NvZGUpOgogICAgICAgICAgICBjb250aW51ZQogICAgICAgIGFyY2hpdm9zLmFwcGVuZCh7Im5hbWUiOiBuYW1lLCAiaWQiOiBmaWR9KQogICAgYXJjaGl2b3Muc29ydChrZXk9bGFtYmRhIHg6IF9zdHJpcF9wcmVmaXgoeFsibmFtZSJdKS51cHBlcigpKQoKICAgIGlmIG5vdCBhcmNoaXZvczoKICAgICAgICBwcmludCgiICBObyBzZSBlbmNvbnRyYXJvbiBhcmNoaXZvcyBwYXJhIGVzZSBwZXLDrW9kby4iKQogICAgICAgIHJldHVybiAxCgogICAgcHJpbnQoZiIgIHtsZW4oYXJjaGl2b3MpfSBhcmNoaXZvKHMpIGVuY29udHJhZG8ocyk6XG4iKQogICAgZm9yIGEgaW4gYXJjaGl2b3M6CiAgICAgICAgcHJpbnQoZiIgICAgwrcge2FbJ25hbWUnXX0iKQoKICAgIE1BWF9JTlRFTlRPUyA9IDUKICAgIHJlc3VtZW4gICAgICA9IFtdCiAgICB0X2luaWNpbyAgICAgPSB0aW1lLnRpbWUoKQoKICAgIGZvciBpLCBhcmNoaXZvIGluIGVudW1lcmF0ZShhcmNoaXZvcywgMSk6CiAgICAgICAgbm9tYnJlID0gYXJjaGl2b1sibmFtZSJdCiAgICAgICAgZmlkICAgID0gYXJjaGl2b1siaWQiXQogICAgICAgIHByaW50KGYiXG57J+KUgCcgKiA2NX0iKQogICAgICAgIHByaW50KGYiW3tpfS97bGVuKGFyY2hpdm9zKX1dIHtub21icmV9IikKICAgICAgICBwcmludChmInsn4pSAJyAqIDY1fSIpCgogICAgICAgIGNvbXBsZXRhZG8gICAgICAgPSBGYWxzZQogICAgICAgIHVsdGltb19yZXN1bHRhZG8gPSBOb25lCgogICAgICAgIGZvciBpbnRlbnRvIGluIHJhbmdlKDEsIE1BWF9JTlRFTlRPUyArIDEpOgogICAgICAgICAgICBpZiBpbnRlbnRvID4gMToKICAgICAgICAgICAgICAgIGVzcGVyYSA9IG1pbig1ICogMiAqKiAoaW50ZW50byAtIDIpLCA2MCkKICAgICAgICAgICAgICAgIHByaW50KGYiICBSZWludGVudG8ge2ludGVudG99L3tNQVhfSU5URU5UT1N9IChlc3BlcmEge2VzcGVyYX1zKS4uLiIpCiAgICAgICAgICAgICAgICBhd2FpdCBhc3luY2lvLnNsZWVwKGVzcGVyYSkKCiAgICAgICAgICAgIHRyeToKICAgICAgICAgICAgICAgIHJlc3VsdGFkbyA9IGF3YWl0IF9wcm9jZXNhcl9hcmNoaXZvKG1jcCwgZmlkLCBub21icmUsIGRyeV9ydW4sIGxvdGUsIGhvamEpCiAgICAgICAgICAgIGV4Y2VwdCBFeGNlcHRpb24gYXMgZToKICAgICAgICAgICAgICAgIHByaW50KGYiICBFUlJPUiBpbnRlbnRvIHtpbnRlbnRvfToge2V9IikKICAgICAgICAgICAgICAgIGNvbnRpbnVlCgogICAgICAgICAgICB1bHRpbW9fcmVzdWx0YWRvID0gcmVzdWx0YWRvCgogICAgICAgICAgICBpZiByZXN1bHRhZG9bImVzdGFkbyJdID09ICJ3YXJuaW5nIjoKICAgICAgICAgICAgICAgIHByaW50KGYiICDimqAgIHtyZXN1bHRhZG9bJ2RldGFsbGUnXX0iKQogICAgICAgICAgICAgICAgcmVzdW1lbi5hcHBlbmQoeyJhcmNoaXZvIjogbm9tYnJlLCAqKnJlc3VsdGFkb30pCiAgICAgICAgICAgICAgICBjb21wbGV0YWRvID0gVHJ1ZQogICAgICAgICAgICAgICAgYnJlYWsKCiAgICAgICAgICAgIGlmIHJlc3VsdGFkb1siZXN0YWRvIl0gPT0gImluY29tcGxldG8iOgogICAgICAgICAgICAgICAgcHJpbnQoIiAgTG90ZSBjb24gZXJyb3JlcyDigJQgc2UgcmVpbnRlbnRhcsOhIGVsIGFyY2hpdm8gY29tcGxldG8uIikKICAgICAgICAgICAgICAgIGNvbnRpbnVlCgogICAgICAgICAgICBpZiByZXN1bHRhZG9bImVzdGFkbyJdID09ICJlcnJvciI6CiAgICAgICAgICAgICAgICBwcmludChmIiAg4pyXIEVSUk9SOiB7cmVzdWx0YWRvLmdldCgnZGV0YWxsZScsICcnKX0iKQogICAgICAgICAgICAgICAgcmVzdW1lbi5hcHBlbmQoeyJhcmNoaXZvIjogbm9tYnJlLCAqKnJlc3VsdGFkb30pCiAgICAgICAgICAgICAgICBjb21wbGV0YWRvID0gVHJ1ZQogICAgICAgICAgICAgICAgYnJlYWsKCiAgICAgICAgICAgIGFjY2lvbiA9ICJzaW11bGFkYXMiIGlmIGRyeV9ydW4gZWxzZSAiZXNjcml0YXMiCiAgICAgICAgICAgIHByaW50KGYiICB7J+KckycgaWYgcmVzdWx0YWRvWydlc3RhZG8nXSA9PSAnb2snIGVsc2UgJ34nfSAiCiAgICAgICAgICAgICAgICAgIGYie3Jlc3VsdGFkb1snaG9qYXMnXX0gaG9qYXMgfCB7cmVzdWx0YWRvWydjb2x1bW5hcyddfSBjb2x1bW5hcyB7YWNjaW9ufSIpCiAgICAgICAgICAgIHJlc3VtZW4uYXBwZW5kKHsiYXJjaGl2byI6IG5vbWJyZSwgKipyZXN1bHRhZG99KQogICAgICAgICAgICBjb21wbGV0YWRvID0gVHJ1ZQogICAgICAgICAgICBicmVhawoKICAgICAgICBpZiBub3QgY29tcGxldGFkbzoKICAgICAgICAgICAgaWYgdWx0aW1vX3Jlc3VsdGFkbyBhbmQgdWx0aW1vX3Jlc3VsdGFkby5nZXQoImNvbHVtbmFzIiwgMCkgPiAwOgogICAgICAgICAgICAgICAgcHJpbnQoZiIgIOKaoCBJbmNvbXBsZXRvIHRyYXMge01BWF9JTlRFTlRPU30gaW50ZW50b3MgKHJlLWVqZWN1dGFyIHJldG9tYSkuIikKICAgICAgICAgICAgICAgIHJlc3VtZW4uYXBwZW5kKHsKICAgICAgICAgICAgICAgICAgICAiYXJjaGl2byI6ICBub21icmUsICJlc3RhZG8iOiAiaW5jb21wbGV0byIsCiAgICAgICAgICAgICAgICAgICAgImRldGFsbGUiOiAgdWx0aW1vX3Jlc3VsdGFkby5nZXQoImRldGFsbGUiLCAiIiksCiAgICAgICAgICAgICAgICAgICAgImhvamFzIjogICAgdWx0aW1vX3Jlc3VsdGFkby5nZXQoImhvamFzIiwgMCksCiAgICAgICAgICAgICAgICAgICAgImNvbHVtbmFzIjogdWx0aW1vX3Jlc3VsdGFkby5nZXQoImNvbHVtbmFzIiwgMCksCiAgICAgICAgICAgICAgICB9KQogICAgICAgICAgICBlbHNlOgogICAgICAgICAgICAgICAgcHJpbnQoZiIgIOKclyBObyBzZSBwdWRvIHByb2Nlc2FyIHRyYXMge01BWF9JTlRFTlRPU30gaW50ZW50b3MuIikKICAgICAgICAgICAgICAgIHJlc3VtZW4uYXBwZW5kKHsKICAgICAgICAgICAgICAgICAgICAiYXJjaGl2byI6IG5vbWJyZSwgImVzdGFkbyI6ICJlcnJvciIsCiAgICAgICAgICAgICAgICAgICAgImRldGFsbGUiOiBmIkZhbGzDsyB0cmFzIHtNQVhfSU5URU5UT1N9IGludGVudG9zIiwKICAgICAgICAgICAgICAgIH0pCgogICAgZWxhcHNlZCA9IHRpbWUudGltZSgpIC0gdF9pbmljaW8KICAgIHByaW50KGYiXG57Jz0nICogNjV9IikKICAgIHByaW50KGYiICBSRVNVTUVOIEZJTkFMIOKAlCB7J0RSWS1SVU4nIGlmIGRyeV9ydW4gZWxzZSAnRVNDUklUVVJBIFJFQUwnfSIpCiAgICBwcmludChmIiAgVGllbXBvIHRvdGFsOiB7ZWxhcHNlZCAvIDYwOi4xZn0gbWluIikKICAgIHByaW50KGYieyc9JyAqIDY1fSIpCgogICAgb2sgICAgICAgPSBbciBmb3IgciBpbiByZXN1bWVuIGlmIHJbImVzdGFkbyJdID09ICJvayJdCiAgICBzaW5fY2FtYiA9IFtyIGZvciByIGluIHJlc3VtZW4gaWYgclsiZXN0YWRvIl0gPT0gInNpbl9jYW1iaW9zIl0KICAgIHdhcm5pbmdzID0gW3IgZm9yIHIgaW4gcmVzdW1lbiBpZiByWyJlc3RhZG8iXSA9PSAid2FybmluZyJdCiAgICBpbmNvbXBsICA9IFtyIGZvciByIGluIHJlc3VtZW4gaWYgclsiZXN0YWRvIl0gPT0gImluY29tcGxldG8iXQogICAgZXJyb3JlcyAgPSBbciBmb3IgciBpbiByZXN1bWVuIGlmIHJbImVzdGFkbyJdID09ICJlcnJvciJdCgogICAgYWNjaW9uID0gInNpbXVsYWRhcyIgaWYgZHJ5X3J1biBlbHNlICJlc2NyaXRhcyIKCiAgICBwcmludChmIlxuICDinJMgT0sgICAgICAgICAgIDoge2xlbihvayl9IikKICAgIGZvciByIGluIG9rOgogICAgICAgIHByaW50KGYiICAgIMK3IHtyWydhcmNoaXZvJ119IOKGkiB7clsnaG9qYXMnXX0gaG9qYXMsIHtyWydjb2x1bW5hcyddfSBjb2x1bW5hcyB7YWNjaW9ufSIpCiAgICBpZiBzaW5fY2FtYjoKICAgICAgICBwcmludChmIlxuICB+IFNpbiBjYW1iaW9zICA6IHtsZW4oc2luX2NhbWIpfSIpCiAgICAgICAgZm9yIHIgaW4gc2luX2NhbWI6CiAgICAgICAgICAgIHByaW50KGYiICAgIMK3IHtyWydhcmNoaXZvJ119IikKICAgIGlmIHdhcm5pbmdzOgogICAgICAgIHByaW50KGYiXG4gIOKaoCBXYXJuaW5ncyAgICAgOiB7bGVuKHdhcm5pbmdzKX0iKQogICAgICAgIGZvciByIGluIHdhcm5pbmdzOgogICAgICAgICAgICBwcmludChmIiAgICDCtyB7clsnYXJjaGl2byddfToge3JbJ2RldGFsbGUnXX0iKQogICAgaWYgaW5jb21wbDoKICAgICAgICBwcmludChmIlxuICDimqAgSW5jb21wbGV0b3MgIDoge2xlbihpbmNvbXBsKX0gKHJlLWVqZWN1dGFyIHBhcmEgcmV0b21hcikiKQogICAgICAgIGZvciByIGluIGluY29tcGw6CiAgICAgICAgICAgIHByaW50KGYiICAgIMK3IHtyWydhcmNoaXZvJ119OiB7clsnZGV0YWxsZSddfSIpCiAgICBpZiBlcnJvcmVzOgogICAgICAgIHByaW50KGYiXG4gIOKclyBFcnJvcmVzICAgICAgOiB7bGVuKGVycm9yZXMpfSIpCiAgICAgICAgZm9yIHIgaW4gZXJyb3JlczoKICAgICAgICAgICAgcHJpbnQoZiIgICAgwrcge3JbJ2FyY2hpdm8nXX06IHtyWydkZXRhbGxlJ119IikKCiAgICBpZiBkcnlfcnVuOgogICAgICAgIHByaW50KCJcbiAgW0RSWS1SVU5dIE5vIHNlIGVzY3JpYmnDsyBuYWRhIGVuIFdvcmtpdmEuIikKCiAgICByZXR1cm4gMiBpZiAoaW5jb21wbCBvciBlcnJvcmVzKSBlbHNlIDAKCgojIOKUgOKUgCBFbnRyeSBwb2ludCDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIAKCmRlZiBtYWluKCk6CiAgICBpZiBsZW4oc3lzLmFyZ3YpID09IDE6CiAgICAgICAgdHJ5OgogICAgICAgICAgICBtZXMsIGFuaW8sIGRyeV9ydW4sIHNvbG8sIGxvdGUgPSBwZWRpcl9vcGNpb25lcygpCiAgICAgICAgZXhjZXB0IEtleWJvYXJkSW50ZXJydXB0OgogICAgICAgICAgICBwcmludCgiXG5DYW5jZWxhZG8uIikKICAgICAgICAgICAgaW5wdXQoIlxuUHJlc2lvbmEgRW50ZXIgcGFyYSBjZXJyYXIuLi4iKQogICAgICAgICAgICBzeXMuZXhpdCgxKQogICAgICAgIGNvZGlnbyA9IGFzeW5jaW8ucnVuKHJ1bihtZXM9bWVzLCBhbmlvPWFuaW8sIGRyeV9ydW49ZHJ5X3J1biwgc29sbz1zb2xvLCBsb3RlPWxvdGUpKQogICAgICAgIGlucHV0KCJcblByZXNpb25hIEVudGVyIHBhcmEgY2VycmFyLi4uIikKICAgICAgICBzeXMuZXhpdChjb2RpZ28pCgogICAgcGFyc2VyID0gYXJncGFyc2UuQXJndW1lbnRQYXJzZXIoCiAgICAgICAgZGVzY3JpcHRpb249IkxsZW5hIGNvbXBhcmF0aXZvcyAoYmFsYW5jZSArIEVFUlIpIGRlIHRvZG9zIGxvcyBJTkQgZGUgdW4gcGVyw61vZG8iLAogICAgKQogICAgcGFyc2VyLmFkZF9hcmd1bWVudCgiLS1tZXMiLCAgICAgcmVxdWlyZWQ9VHJ1ZSkKICAgIHBhcnNlci5hZGRfYXJndW1lbnQoIi0tYW5pbyIsICAgIHJlcXVpcmVkPVRydWUpCiAgICBwYXJzZXIuYWRkX2FyZ3VtZW50KCItLWRyeS1ydW4iLCBhY3Rpb249InN0b3JlX3RydWUiKQogICAgcGFyc2VyLmFkZF9hcmd1bWVudCgiLS1zb2xvIiwgICAgZGVmYXVsdD1Ob25lKQogICAgcGFyc2VyLmFkZF9hcmd1bWVudCgiLS1ob2phIiwgICAgZGVmYXVsdD1Ob25lLAogICAgICAgICAgICAgICAgICAgICAgICBoZWxwPSJOb21icmUgZXhhY3RvIGRlIGxhIGhvamEgYSBwcm9jZXNhciAoZWo6ICdDLi0gRXN0YWRvIGRlIHJlc3VsdGFkbycpIikKICAgIHBhcnNlci5hZGRfYXJndW1lbnQoIi0tbG90ZSIsICAgIHR5cGU9aW50LCBkZWZhdWx0PTUwKQogICAgYXJncyA9IHBhcnNlci5wYXJzZV9hcmdzKCkKCiAgICBhbmlvID0gYXJncy5hbmlvLnN0cmlwKCkKICAgIGlmIGxlbihhbmlvKSA9PSAyOgogICAgICAgIGFuaW8gPSAiMjAiICsgYW5pbwoKICAgIHRyeToKICAgICAgICBjb2RpZ28gPSBhc3luY2lvLnJ1bihydW4oCiAgICAgICAgICAgIG1lcyAgICAgPSBhcmdzLm1lcy5zdHJpcCgpLnpmaWxsKDIpLAogICAgICAgICAgICBhbmlvICAgID0gYW5pbywKICAgICAgICAgICAgZHJ5X3J1biA9IGFyZ3MuZHJ5X3J1biwKICAgICAgICAgICAgc29sbyAgICA9IGFyZ3Muc29sbywKICAgICAgICAgICAgbG90ZSAgICA9IG1heCgxLCBtaW4oYXJncy5sb3RlLCAxMDApKSwKICAgICAgICAgICAgaG9qYSAgICA9IGFyZ3MuaG9qYSwKICAgICAgICApKQogICAgZXhjZXB0IEtleWJvYXJkSW50ZXJydXB0OgogICAgICAgIHByaW50KCJcbkNhbmNlbGFkby4iKQogICAgICAgIHN5cy5leGl0KDEpCiAgICBzeXMuZXhpdChjb2RpZ28pCgoKaWYgX19uYW1lX18gPT0gIl9fbWFpbl9fIjoKICAgIG1haW4oKQo="
).decode("utf-8")

_VALIDAR_V2_SRC = base64.b64decode(
    b"IyEvdXNyL2Jpbi9lbnYgcHl0aG9uMwoiIiIKdmFsaWRhcl9jb21wYXJhdGl2b3NfdjIucHkgIOKGkCAgRVNQRUpPIHF1ZSB1c2Egd29ya2l2YV9tY3BfdjIucHkKPT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PQpJZMOpbnRpY28gYSB2YWxpZGFyX2NvbXBhcmF0aXZvcy5weSBwZXJvIGNhcmdhIHdvcmtpdmFfbWNwX3YyLnB5CmVuIGx1Z2FyIGRlIHdvcmtpdmFfbWNwLnB5IHBhcmEgYXByb3ZlY2hhciBsYSBkZXRlY2Npw7NuIGRlCmNvbHVtbmFzIEVFUlIgKGhvamEgQyB5IGVxdWl2YWxlbnRlcyBlbiBRMi9RMy9RNCkuCgpVU086CiAgcHl0aG9uIHZhbGlkYXJfY29tcGFyYXRpdm9zX3YyLnB5CiAgICAgIOKGkiBwaWRlIGludGVyYWN0aXZhbWVudGUgc29jaWVkYWQsIGHDsW8gYmFzZSwgSU5EL0NPTlNPIHkgdHJpbWVzdHJlLgoKICBweXRob24gdmFsaWRhcl9jb21wYXJhdGl2b3NfdjIucHkgRTExMCAyMDI2IFEyCiAgcHl0aG9uIHZhbGlkYXJfY29tcGFyYXRpdm9zX3YyLnB5IEUyMDAgMjAyNiBRMSAtLXRpcG8gSU5ECiAgcHl0aG9uIHZhbGlkYXJfY29tcGFyYXRpdm9zX3YyLnB5IC0taWQgPHNwcmVhZHNoZWV0X2lkPgoKU0FMSURBOiBleGl0IGNvZGUgMCA9IHRvZG8gY2FsemEsIDIgPSBoYXkgaGFsbGF6Z29zLCAxID0gZXJyb3IuCiIiIgoKaW1wb3J0IGFyZ3BhcnNlCmltcG9ydCBhc3luY2lvCmltcG9ydCBpbXBvcnRsaWIudXRpbAppbXBvcnQganNvbgppbXBvcnQgbG9nZ2luZwppbXBvcnQgb3MKaW1wb3J0IHJlCmltcG9ydCBzeXMKZnJvbSBkYXRldGltZSBpbXBvcnQgZGF0ZXRpbWUKZnJvbSBwYXRobGliIGltcG9ydCBQYXRoCgpsb2dnaW5nLmdldExvZ2dlcigiaHR0cHgiKS5zZXRMZXZlbChsb2dnaW5nLldBUk5JTkcpCgoKIyDilIDilIAgQ2FyZ2FyIHdvcmtpdmFfbWNwX3YyIGRlc2RlIGxhIG1pc21hIGNhcnBldGEg4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSACgpkZWYgX2xvYWRfdygpOgogICAgaGVyZSAgICAgPSBQYXRoKF9fZmlsZV9fKS5wYXJlbnQKICAgIG1jcF9wYXRoID0gaGVyZSAvICJ3b3JraXZhX21jcF92Mi5weSIKICAgIGlmIG5vdCBtY3BfcGF0aC5leGlzdHMoKToKICAgICAgICBwcmludChmIkVSUk9SOiBObyBzZSBlbmN1ZW50cmEge21jcF9wYXRofSIpCiAgICAgICAgc3lzLmV4aXQoMSkKICAgIHNwZWMgPSBpbXBvcnRsaWIudXRpbC5zcGVjX2Zyb21fZmlsZV9sb2NhdGlvbigid29ya2l2YV9tY3BfdjIiLCBtY3BfcGF0aCkKICAgIG1vZCAgPSBpbXBvcnRsaWIudXRpbC5tb2R1bGVfZnJvbV9zcGVjKHNwZWMpCiAgICBzeXMubW9kdWxlc1sid29ya2l2YV9tY3BfdjIiXSA9IG1vZAogICAgc3BlYy5sb2FkZXIuZXhlY19tb2R1bGUobW9kKQogICAgcmV0dXJuIG1vZAoKCncgPSBfbG9hZF93KCkKCk1FU19QT1JfVFJJTUVTVFJFID0gewogICAgIlExIjogIjAzIiwgIlEyIjogIjA2IiwgIlEzIjogIjA5IiwgIlE0IjogIjEyIiwKICAgICIxIjogIjAzIiwgIjIiOiAiMDYiLCAiMyI6ICIwOSIsICI0IjogIjEyIiwKICAgICIwMyI6ICIwMyIsICIwNiI6ICIwNiIsICIwOSI6ICIwOSIsICIxMiI6ICIxMiIsCn0KCgpkZWYgX3BlZGlyKHRleHRvOiBzdHIsIHZhbGlkYXIsIGRlZmF1bHQ6IHN0ciB8IE5vbmUgPSBOb25lKSAtPiBzdHI6CiAgICB3aGlsZSBUcnVlOgogICAgICAgIHYgPSBpbnB1dCh0ZXh0bykKICAgICAgICBmb3IgYm9tIGluIChjaHIoMHhGRUZGKSwgY2hyKDB4RUYpICsgY2hyKDB4QkIpICsgY2hyKDB4QkYpKToKICAgICAgICAgICAgdiA9IHYucmVtb3ZlcHJlZml4KGJvbSkKICAgICAgICB2ID0gdi5zdHJpcCgpCiAgICAgICAgaWYgbm90IHYgYW5kIGRlZmF1bHQgaXMgbm90IE5vbmU6CiAgICAgICAgICAgIHJldHVybiBkZWZhdWx0CiAgICAgICAgaWYgdmFsaWRhcih2KToKICAgICAgICAgICAgcmV0dXJuIHYKICAgICAgICBwcmludCgiICAgdmFsb3Igbm8gdsOhbGlkbywgaW50ZW50YSBkZSBudWV2byIpCgoKZGVmIHBlZGlyX29wY2lvbmVzKCkgLT4gdHVwbGVbc3RyLCBzdHIsIHN0ciwgc3RyXToKICAgIHByaW50KCI9PT0gVmFsaWRhZG9yIGRlIGNvbXBhcmF0aXZvcyBXb3JraXZhIFYyIChjaWVycmUgbm9ybWFsKSA9PT1cbiIpCiAgICBzb2NpZWRhZCA9IF9wZWRpcigiU29jaWVkYWQgKGVqIEUxMTAsIEUyMDApOiAiLAogICAgICAgICAgICAgICAgICAgICAgbGFtYmRhIHY6IHJlLmZ1bGxtYXRjaChyIltFZV1cZCsiLCB2KSBpcyBub3QgTm9uZSkudXBwZXIoKQogICAgYW5pbyA9IF9wZWRpcigiQcOxbyBiYXNlIChlaiAyMDI2KTogIiwKICAgICAgICAgICAgICAgICAgbGFtYmRhIHY6IHJlLmZ1bGxtYXRjaChyIlxkezR9IiwgdikgaXMgbm90IE5vbmUpCiAgICB0aXBvX2luID0gX3BlZGlyKCJUaXBvIGRlIGNpZXJyZSBbMV0gQ09OU08gIFsyXSBJTkQgIChFbnRlciA9IENPTlNPKTogIiwKICAgICAgICAgICAgICAgICAgICAgbGFtYmRhIHY6IHYudXBwZXIoKSBpbiAoIjEiLCAiMiIsICJDT05TTyIsICJJTkQiKSwKICAgICAgICAgICAgICAgICAgICAgZGVmYXVsdD0iQ09OU08iKQogICAgdGlwbyA9ICJJTkQiIGlmIHRpcG9faW4udXBwZXIoKSBpbiAoIjIiLCAiSU5EIikgZWxzZSAiQ09OU08iCiAgICB0cmltZXN0cmUgPSBfcGVkaXIoIlRyaW1lc3RyZSAoUTEvUTIvUTMvUTQsIDEtNCBvIG1lcyAwMy8wNi8wOS8xMik6ICIsCiAgICAgICAgICAgICAgICAgICAgICAgbGFtYmRhIHY6IHYudXBwZXIoKSBpbiBNRVNfUE9SX1RSSU1FU1RSRSkKICAgIHByaW50KCkKICAgIHJldHVybiBzb2NpZWRhZCwgYW5pbywgdGlwbywgdHJpbWVzdHJlCgoKYXN5bmMgZGVmIHJlc29sdmVyX3NwcmVhZHNoZWV0KHNvY2llZGFkOiBzdHIsIGFuaW86IHN0ciwgdHJpbWVzdHJlOiBzdHIsCiAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICB0aXBvOiBzdHIpIC0+IHR1cGxlW3N0ciwgc3RyXSB8IE5vbmU6CiAgICBtbSA9IE1FU19QT1JfVFJJTUVTVFJFW3RyaW1lc3RyZS51cHBlcigpXQogICAgYWxsX2ZpbGVzID0gYXdhaXQgdy5fbG9hZF9hbGxfZmlsZXMoKQogICAgcGF0cm9uICAgID0gcmUuY29tcGlsZShyZiJee3JlLmVzY2FwZShzb2NpZWRhZCl9X3t0aXBvfV97bW19Wy1fXXthbmlvfV8iKQogICAgbWF0Y2hlcyAgID0ge246IGkgZm9yIG4sIGkgaW4gYWxsX2ZpbGVzLml0ZW1zKCkgaWYgcGF0cm9uLm1hdGNoKG4pfQoKICAgIGlmIGxlbihtYXRjaGVzKSA9PSAxOgogICAgICAgIG5hbWUsIHNzX2lkID0gbmV4dChpdGVyKG1hdGNoZXMuaXRlbXMoKSkpCiAgICAgICAgcHJpbnQoZiJBcmNoaXZvIGVuY29udHJhZG86IHtuYW1lfSIpCiAgICAgICAgcmV0dXJuIHNzX2lkLCBuYW1lCgogICAgaWYgbGVuKG1hdGNoZXMpID4gMToKICAgICAgICBwcmludCgiRVJST1I6IG3DoXMgZGUgdW4gYXJjaGl2byBjYWx6YTsgdXNhIC0taWQgcGFyYSBlbGVnaXIgdW5vOiIpCiAgICAgICAgZm9yIG4sIGkgaW4gc29ydGVkKG1hdGNoZXMuaXRlbXMoKSk6CiAgICAgICAgICAgIHByaW50KGYiICB7bn0gIChpZCB7aX0pIikKICAgICAgICByZXR1cm4gTm9uZQoKICAgIHByaW50KGYiRVJST1I6IG5vIHNlIGVuY29udHLDsyBhcmNoaXZvIHBhcmEge3NvY2llZGFkfSB7dGlwb30ge21tfS17YW5pb30uIikKICAgIGRpc3BvbmlibGVzID0gc29ydGVkKAogICAgICAgIG4gZm9yIG4gaW4gYWxsX2ZpbGVzCiAgICAgICAgaWYgbi5zdGFydHN3aXRoKGYie3NvY2llZGFkfV8iKSBhbmQgIkJhc2UgTm90YXMiIGluIG4KICAgICkKICAgIGlmIGRpc3BvbmlibGVzOgogICAgICAgIHByaW50KCJBcmNoaXZvcyBCYXNlIE5vdGFzIGRpc3BvbmlibGVzIHBhcmEgZXNhIHNvY2llZGFkOiIpCiAgICAgICAgZm9yIG4gaW4gZGlzcG9uaWJsZXM6CiAgICAgICAgICAgIHByaW50KGYiICB7bn0iKQogICAgcmV0dXJuIE5vbmUKCgojIOKUgOKUgCBSZWdsYXMgZGUgYWxjYW5jZSBwb3IgaG9qYSDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIAKIwojIDEpIExJTUlURV9GSUxBUzogw7psdGltYSBmaWxhIHbDoWxpZGEgZGUgY2FkYSBub3RhLiBNw6FzIGFiYWpvIGRlIGVzYSBmaWxhIGxhcwojICAgIGhvamFzIHRyYWVuIGJsb3F1ZXMgYXV4aWxpYXJlcyAoUFBULCBjdWFkcm9zIGRlIGFwb3lvLCBldGMuKSBxdWUgbm8gc29uCiMgICAgY29tcGFyYXRpdm8geSBnZW5lcmFiYW4gaGFsbGF6Z29zIGZhbHNvcy4KIwojIDIpIFN1YmhvamFzOiBlbiBsb3MgYXJjaGl2b3MgQ09OU09MSURBRE9TIGNhZGEgbm90YSBzZSByZXBpdGUgdW5hIG8gbcOhcwojICAgIHZlY2VzIGNvbW8gaG9qYSBkZSBhcG95byAoIjI3Li0gQ0dFTSBDb25zbyIsICI3My4tIFBQQSIsIGV0Yy4pLiBTb24KIyAgICBhcG95byBkZSBsYSBub3RhIHJlYWwgeSBOTyBkZWJlbiB2YWxpZGFyc2UuCiMKIyAgICBMYSBkZXRlY2Npw7NuIE5PIHVzYSB1bmEgbGlzdGEgZGUgbm9tYnJlczogZXNvcyBub21icmVzIGNhbWJpYW4gZGUgdW5hCiMgICAgc29jaWVkYWQgYSBvdHJhLiBTZSB1c2EgZWwgcHJlZmlqbyBkZSBsYSBub3RhICgiMjciLCAiRiIsICJBIiksIHF1ZSBlcwojICAgIHN1IGlkZW50aWZpY2Fkb3I6IGxhIG5vdGEgcmVhbCBlcyBsYSBQUklNRVJBIGhvamEgZGVsIGFyY2hpdm8gY29uIGVzZQojICAgIHByZWZpam8geSBjdWFscXVpZXIgaG9qYSBwb3N0ZXJpb3IgcXVlIHJlcGl0YSBlbCBwcmVmaWpvIGVzIHN1YmhvamEuCiMKIyAgICBDb25zZWN1ZW5jaWEgaW1wb3J0YW50ZTogdW5hIGhvamEgY29uIHByZWZpam8gw7puaWNvIGphbcOhcyBzZSBkZXNjYXJ0YS4KCiMgTm90YXMgZXhjbHVpZGFzIGRlIGxhIFZBTElEQUNJw5NOIChubyBkZWwgbGxlbmFkbykuCiMgLSAiRCI6IG1pZW50cmFzIHNlIGludmVzdGlnYSB1biBwcm9ibGVtYSBwdW50dWFsLiBDYWRhIGNvbHVtbmEgY29tcGFyYXRpdmEKIyAgIGRlIGVzdGEgbm90YSBwdWVkZSBsZWVyIGRlIHVuIGFyY2hpdm8gZnVlbnRlIGRpc3RpbnRvLCB5IGFsZ3VubyBkZSBlc29zCiMgICBhcmNoaXZvcyB0aWVuZSB1bmEgZXN0cnVjdHVyYSBkaXN0aW50YSBjZXJjYSBkZSBsb3MgdG90YWxlcyBxdWUgZ2VuZXJhCiMgICBTSU4gQ09SUkVTUE9OREVOQ0lBIGVuIGNhc2NhZGEgKDMgZGUgNCBjb2x1bW5hcyBmYWxsYW4ganVzdG8gZW4gbGFzCiMgICBmaWxhcyAiVG90YWwiKS4KIyAtICIxMzkiLCAiMTQwIiAoTklJRiA1IC0gT3BlcmFjaW9uZXMgZGlzY29udGludWFkYXMpOiBubyBzZSB1c2FuLgpOT1RBU19FWENMVUlEQVNfVkFMSURBQ0lPTiA9IHsiRCIsICIxMzkiLCAiMTQwIn0KClJBTkdPX0ZJTEFTOiBkaWN0W3N0ciwgdHVwbGVbaW50IHwgTm9uZSwgaW50IHwgTm9uZV1dID0gewogICAgIkEiOiAgIChOb25lLCA0MyksCiAgICAiQiI6ICAgKE5vbmUsIDU1KSwKICAgICJDIjogICAoTm9uZSwgNDUpLAogICAgIkQiOiAgIChOb25lLCA3NyksCiAgICAiSyI6ICAgKE5vbmUsIDE0KSwKICAgICIxMyI6ICAoTm9uZSwgMTQpLAogICAgIjE0IjogIChOb25lLCA0NSksCiAgICAiMTUiOiAgKE5vbmUsIDE0KSwKICAgICIxNyI6ICAoTm9uZSwgMTUpLAogICAgIjIyIjogICg3LCAgICAxMSksCiAgICAiMjMiOiAgKE5vbmUsIDI2KSwKICAgICI1MyI6ICAoTm9uZSwgMjUpLAogICAgIjU1IjogICg3LCAgICAxOCksCiAgICAiNTciOiAgKE5vbmUsIDQxKSwKICAgICI3NCI6ICAoTm9uZSwgMjIpLAogICAgIjc3IjogIChOb25lLCA0MCksCiAgICAiODUiOiAgKE5vbmUsIDM3KSwKICAgICI5MCI6ICAoTm9uZSwgMjUpLAogICAgIjk1IjogIChOb25lLCAxNiksCiAgICAiMTA0IjogKE5vbmUsIDIyKSwKICAgICIxMDUiOiAoTm9uZSwgMTEpLAogICAgIjEwNiI6IChOb25lLCAxMiksCiAgICAiMTA3IjogKE5vbmUsIDIwKSwKICAgICIxMDgiOiAoTm9uZSwgMTMpLAogICAgIjEwOSI6IChOb25lLCAxOSksCiAgICAiMTEwIjogKE5vbmUsIDI0KSwKICAgICIxMTEiOiAoTm9uZSwgMzcpLAogICAgIjExMyI6IChOb25lLCA0NCksCiAgICAiMTE0IjogKE5vbmUsIDI5KSwKICAgICIxMTgiOiAoTm9uZSwgMjEpLAogICAgIjEyMCI6IChOb25lLCA0MyksCiAgICAiMTIxIjogKE5vbmUsIDUzKSwKICAgICIxMjMiOiAoMTMsICAgTm9uZSksCn0KCiMgRmlsYXMgcHVudHVhbGVzIGV4Y2x1aWRhcyBkZW50cm8gZGUgdW5hIG5vdGEgKG5vIGVzIHVuIHRlbWEgZGUgcmFuZ286CiMgbGEgZmlsYSBlc3TDoSBlbiBtZWRpbyBkZSBvdHJhcyBxdWUgc8OtIHNlIHZhbGlkYW4pLiBFai4gbm90YSAxNDogbGEgZmlsYQojIDI4ICJEZXVkb3JlcyB2YXJpb3MiIGVzIHVuIHN1YnRvdGFsIHF1ZSBubyBkZWJlIGNvbXBhcmFyc2UuCkZJTEFTX0VYQ0xVSURBU19QT1JfTk9UQTogZGljdFtzdHIsIHNldFtpbnRdXSA9IHsKICAgICIxNCI6IHsyOH0sCn0KCiMgIkEuLSBBY3Rpdm9zIiAtPiAiQSIgOyAiMjcuIENHRU0gQ29uc28iIC0+ICIyNyIgOyAiNTUuLUNHRSIgLT4gIjU1IgpfUkVfUFJFRklKTyA9IHJlLmNvbXBpbGUociJeXHMqKFtBLVphLXrDkcOxMC05XXsxLDR9KVxzKlwuXHMqLT9ccypcUyIpCgoKZGVmIHByZWZpam9faG9qYShub21icmU6IHN0cikgLT4gc3RyOgogICAgIiIiUHJlZmlqbyBkZSBsYSBub3RhICgiQSIsICIyNyIpLCBvICIiIHNpIGVsIG5vbWJyZSBubyBsbyBsbGV2YS4iIiIKICAgIG0gPSBfUkVfUFJFRklKTy5tYXRjaChub21icmUgb3IgIiIpCiAgICByZXR1cm4gbS5ncm91cCgxKS51cHBlcigpIGlmIG0gZWxzZSAiIgoKCmNsYXNzIERldGVjdG9yU3ViaG9qYXM6CiAgICAiIiJNYXJjYSBjb21vIHN1YmhvamEgdG9kYSBob2phIHF1ZSByZXBpdGEgZWwgcHJlZmlqbyBkZSB1bmEgYW50ZXJpb3IuCgogICAgU2UgYWxpbWVudGEgZW4gZWwgbWlzbW8gb3JkZW4gZW4gcXVlIFdvcmtpdmEgZGV2dWVsdmUgbGFzIGhvamFzLCBxdWUgZXMKICAgIGVsIG9yZGVuIGRlbCBhcmNoaXZvOiBsYSBub3RhIHJlYWwgdmEgcHJpbWVybyB5IHN1cyBob2phcyBkZSBhcG95byBsYQogICAgc2lndWVuLiBVbmEgaG9qYSBzaW4gcHJlZmlqbywgbyBjb24gdW4gcHJlZmlqbyBxdWUgYXBhcmVjZSB1bmEgc29sYSB2ZXosCiAgICBudW5jYSBzZSBtYXJjYS4KICAgICIiIgoKICAgIGRlZiBfX2luaXRfXyhzZWxmKSAtPiBOb25lOgogICAgICAgIHNlbGYuX3Zpc3RvczogZGljdFtzdHIsIHN0cl0gPSB7fQoKICAgIGRlZiBlc19zdWJob2phKHNlbGYsIG5vbWJyZTogc3RyKSAtPiBzdHIgfCBOb25lOgogICAgICAgICIiIkRldnVlbHZlIGVsIG5vbWJyZSBkZSBsYSBub3RhIHJlYWwgc2kgYG5vbWJyZWAgZXMgc3ViaG9qYSBzdXlhLiIiIgogICAgICAgIHByZWZpam8gPSBwcmVmaWpvX2hvamEobm9tYnJlKQogICAgICAgIGlmIG5vdCBwcmVmaWpvOgogICAgICAgICAgICByZXR1cm4gTm9uZQogICAgICAgIHBhZHJlID0gc2VsZi5fdmlzdG9zLmdldChwcmVmaWpvKQogICAgICAgIGlmIHBhZHJlIGlzIE5vbmU6CiAgICAgICAgICAgIHNlbGYuX3Zpc3Rvc1twcmVmaWpvXSA9IG5vbWJyZQogICAgICAgICAgICByZXR1cm4gTm9uZQogICAgICAgIHJldHVybiBwYWRyZQoKCmRlZiByYW5nb19maWxhcyhub21icmU6IHN0cikgLT4gdHVwbGVbaW50IHwgTm9uZSwgaW50IHwgTm9uZV06CiAgICAiIiJEZXZ1ZWx2ZSAoZGVzZGUsIGhhc3RhKSBwYXJhIGVzYSBob2phLiBOb25lID0gc2luIGzDrW1pdGUgZW4gZXNlIGV4dHJlbW8uIiIiCiAgICByZXR1cm4gUkFOR09fRklMQVMuZ2V0KHByZWZpam9faG9qYShub21icmUpLCAoTm9uZSwgTm9uZSkpCgoKZGVmIF9ub21icmVfcGVzdGFuYShub21icmU6IHN0ciwgdXNhZG9zOiBzZXRbc3RyXSkgLT4gc3RyOgogICAgbGltcGlvID0gcmUuc3ViKHIiW1xbXF06Kj8vXFxdIiwgIiAiLCBub21icmUpWzozMV0ucnN0cmlwKCkKICAgIGJhc2UsIG4gPSBsaW1waW8sIDIKICAgIHdoaWxlIGxpbXBpbyBpbiB1c2Fkb3M6CiAgICAgICAgc3VmaWpvID0gZiIgKHtufSkiCiAgICAgICAgbGltcGlvID0gYmFzZVs6IDMxIC0gbGVuKHN1ZmlqbyldICsgc3VmaWpvCiAgICAgICAgbiArPSAxCiAgICB1c2Fkb3MuYWRkKGxpbXBpbykKICAgIHJldHVybiBsaW1waW8KCgpkZWYgZXhwb3J0YXJfZXhjZWwocnV0YTogc3RyLCB0aXR1bG86IHN0ciwgc3VidGl0dWxvOiBzdHIsCiAgICAgICAgICAgICAgICAgICBob2phczogbGlzdFtkaWN0XSkgLT4gTm9uZToKICAgIGZyb20gb3BlbnB5eGwgaW1wb3J0IFdvcmtib29rCiAgICBmcm9tIG9wZW5weXhsLnN0eWxlcyBpbXBvcnQgRm9udAoKICAgIGJvbGQgPSBGb250KGJvbGQ9VHJ1ZSkKICAgIHdiICAgPSBXb3JrYm9vaygpCgogICAgd3MgPSB3Yi5hY3RpdmUKICAgIHdzLnRpdGxlID0gIlJlc3VtZW4iCiAgICB3cy5jZWxsKHJvdz0xLCBjb2x1bW49MSwgdmFsdWU9dGl0dWxvKS5mb250ID0gYm9sZAogICAgd3MuY2VsbChyb3c9MiwgY29sdW1uPTEsIHZhbHVlPXN1YnRpdHVsbykuZm9udCA9IGJvbGQKICAgIGVuY2FiZXphZG9zID0gWyJOb3RhIiwgIkhvamEgRXhjZWwiLCAiRmlsYXMiLCAiT0siLCAiSGFsbGF6Z28iLCAiTm8gcHJvY2VzYWRvIiwKICAgICAgICAgICAgICAgICAgICJTaW4gY29ycmVzcG9uZGVuY2lhIl0KICAgIGZvciBqLCBoIGluIGVudW1lcmF0ZShlbmNhYmV6YWRvcywgc3RhcnQ9MSk6CiAgICAgICAgd3MuY2VsbChyb3c9NCwgY29sdW1uPWosIHZhbHVlPWgpLmZvbnQgPSBib2xkCiAgICB3cy5jb2x1bW5fZGltZW5zaW9uc1siQSJdLndpZHRoID0gNzAKICAgIHdzLmNvbHVtbl9kaW1lbnNpb25zWyJCIl0ud2lkdGggPSAzNAogICAgd3MuZnJlZXplX3BhbmVzID0gIkE1IgoKICAgIHVzYWRvczogc2V0W3N0cl0gPSB7IlJlc3VtZW4ifQogICAgZm9yIGksIGhvamEgaW4gZW51bWVyYXRlKGhvamFzLCBzdGFydD01KToKICAgICAgICBmaWxhcyA9IGhvamFbImZpbGFzIl0KICAgICAgICB0YWIgICA9IF9ub21icmVfcGVzdGFuYShob2phWyJub21icmUiXSwgdXNhZG9zKSBpZiBmaWxhcyBlbHNlICItIgogICAgICAgIHdzLmNlbGwocm93PWksIGNvbHVtbj0xLCB2YWx1ZT1ob2phWyJub21icmUiXSkKICAgICAgICB3cy5jZWxsKHJvdz1pLCBjb2x1bW49MiwgdmFsdWU9dGFiKQogICAgICAgIHdzLmNlbGwocm93PWksIGNvbHVtbj0zLCB2YWx1ZT1sZW4oZmlsYXMpKQogICAgICAgIHdzLmNlbGwocm93PWksIGNvbHVtbj00LCB2YWx1ZT1zdW0oMSBmb3IgZiBpbiBmaWxhcyBpZiBmWyJlc3RhZG8iXSA9PSAiT0siKSkKICAgICAgICB3cy5jZWxsKHJvdz1pLCBjb2x1bW49NSwgdmFsdWU9c3VtKDEgZm9yIGYgaW4gZmlsYXMgaWYgZlsiZXN0YWRvIl0gPT0gIkhBTExBWkdPIikpCiAgICAgICAgd3MuY2VsbChyb3c9aSwgY29sdW1uPTYsIHZhbHVlPXN1bSgxIGZvciBmIGluIGZpbGFzIGlmIGZbImVzdGFkbyJdID09ICJOTyBQUk9DRVNBRE8iKSkKICAgICAgICB3cy5jZWxsKHJvdz1pLCBjb2x1bW49NywKICAgICAgICAgICAgICAgIHZhbHVlPXN1bSgxIGZvciBmIGluIGZpbGFzIGlmIGZbImVzdGFkbyJdID09ICJTSU4gQ09SUkVTUE9OREVOQ0lBIikpCgogICAgICAgIGlmIG5vdCBmaWxhczoKICAgICAgICAgICAgY29udGludWUKICAgICAgICB3c19uID0gd2IuY3JlYXRlX3NoZWV0KHRhYikKICAgICAgICB3c19uLmNlbGwocm93PTEsIGNvbHVtbj0xLCB2YWx1ZT1ob2phWyJub21icmUiXSkuZm9udCA9IGJvbGQKICAgICAgICBjb2xzID0gWyJGaWxhIiwgIkV0aXF1ZXRhIiwgIlZhbG9yIGRlY2xhcmFkbyAoY29tcGFyYXRpdm8pIiwKICAgICAgICAgICAgICAgICJWYWxvciByZWFsIChmdWVudGUpIiwgIkVzdGFkbyIsICJOb3RhIl0KICAgICAgICBmb3IgaiwgaCBpbiBlbnVtZXJhdGUoY29scywgc3RhcnQ9MSk6CiAgICAgICAgICAgIHdzX24uY2VsbChyb3c9MiwgY29sdW1uPWosIHZhbHVlPWgpLmZvbnQgPSBib2xkCiAgICAgICAgZm9yIHIsIGYgaW4gZW51bWVyYXRlKHNvcnRlZChmaWxhcywga2V5PWxhbWJkYSB4OiAoeFsiZmlsYSJdLCB4WyJldGlxdWV0YSJdKSksCiAgICAgICAgICAgICAgICAgICAgICAgICAgICAgIHN0YXJ0PTMpOgogICAgICAgICAgICB3c19uLmNlbGwocm93PXIsIGNvbHVtbj0xLCB2YWx1ZT1mWyJmaWxhIl0pCiAgICAgICAgICAgIHdzX24uY2VsbChyb3c9ciwgY29sdW1uPTIsIHZhbHVlPWZbImV0aXF1ZXRhIl0pCiAgICAgICAgICAgIGMzID0gd3Nfbi5jZWxsKHJvdz1yLCBjb2x1bW49MywgdmFsdWU9ZlsiZGVzdGlubyJdKQogICAgICAgICAgICBjNCA9IHdzX24uY2VsbChyb3c9ciwgY29sdW1uPTQsIHZhbHVlPWZbImZ1ZW50ZSJdKQogICAgICAgICAgICBjMy5udW1iZXJfZm9ybWF0ID0gIiMsIyMwIgogICAgICAgICAgICBjNC5udW1iZXJfZm9ybWF0ID0gIiMsIyMwIgogICAgICAgICAgICB3c19uLmNlbGwocm93PXIsIGNvbHVtbj01LCB2YWx1ZT1mWyJlc3RhZG8iXSkKICAgICAgICAgICAgd3Nfbi5jZWxsKHJvdz1yLCBjb2x1bW49NiwgdmFsdWU9Zlsibm90YSJdKQogICAgICAgIHdzX24uY29sdW1uX2RpbWVuc2lvbnNbIkIiXS53aWR0aCA9IDYwCiAgICAgICAgd3Nfbi5jb2x1bW5fZGltZW5zaW9uc1siQyJdLndpZHRoID0gMjIKICAgICAgICB3c19uLmNvbHVtbl9kaW1lbnNpb25zWyJEIl0ud2lkdGggPSAyMgogICAgICAgIHdzX24uY29sdW1uX2RpbWVuc2lvbnNbIkUiXS53aWR0aCA9IDE0CiAgICAgICAgd3Nfbi5jb2x1bW5fZGltZW5zaW9uc1siRiJdLndpZHRoID0gMzAKICAgICAgICB3c19uLmZyZWV6ZV9wYW5lcyA9ICJBMyIKCiAgICB3Yi5zYXZlKHJ1dGEpCgoKYXN5bmMgZGVmIHZhbGlkYXIoc3ByZWFkc2hlZXRfaWQ6IHN0ciwgZXRpcXVldGE6IHN0ciwgbWF4X3NoZWV0czogaW50ID0gNTApIC0+IGludDoKICAgIG9mZnNldCA9IDAKICAgIHRvdGFsX2VxdWFsID0gdG90YWxfZGlmZiA9IHRvdGFsX3Npbl9jb3JyID0gMAogICAgY2FuZGlkYXRhcyA9ICI/IgogICAgaW5mbzogZGljdCA9IHt9CiAgICBob2phczogbGlzdFtkaWN0XSA9IFtdCiAgICBlbmNhYmV6YWRvX2ltcHJlc28gPSBGYWxzZQogICAgb21pdGlkYXNfc3ViaG9qYSAgPSAwCiAgICBvbWl0aWRhc19leGNsdWlkYXMgPSAwCiAgICBmaWxhc19mdWVyYSAgICAgICA9IDAKICAgIGRldGVjdG9yICAgICAgICAgID0gRGV0ZWN0b3JTdWJob2phcygpCgogICAgd2hpbGUgVHJ1ZToKICAgICAgICByYXcgPSBhd2FpdCB3LndvcmtpdmFfZmlsbF9jb21wYXJhdGl2ZXMoCiAgICAgICAgICAgIHcuRmlsbENvbXBhcmF0aXZlc0lucHV0KAogICAgICAgICAgICAgICAgc3ByZWFkc2hlZXRfaWQ9c3ByZWFkc2hlZXRfaWQsCiAgICAgICAgICAgICAgICBkcnlfcnVuPVRydWUsCiAgICAgICAgICAgICAgICBzaGVldF9vZmZzZXQ9b2Zmc2V0LAogICAgICAgICAgICAgICAgbWF4X3NoZWV0cz1tYXhfc2hlZXRzLAogICAgICAgICAgICAgICAgZGV0YWxsZV9maWxhcz1UcnVlLAogICAgICAgICAgICApCiAgICAgICAgKQogICAgICAgIHRyeToKICAgICAgICAgICAgciA9IGpzb24ubG9hZHMocmF3KQogICAgICAgIGV4Y2VwdCBqc29uLkpTT05EZWNvZGVFcnJvcjoKICAgICAgICAgICAgcHJpbnQoZiJFUlJPUiBkZWwgY29uZWN0b3I6IHtyYXd9IikKICAgICAgICAgICAgcmV0dXJuIDEKCiAgICAgICAgaWYgIndhcm5pbmciIGluIHI6CiAgICAgICAgICAgIHByaW50KGYiQURWRVJURU5DSUE6IHtyWyd3YXJuaW5nJ119IikKICAgICAgICAgICAgcmV0dXJuIDEKCiAgICAgICAgaWYgbm90IGVuY2FiZXphZG9faW1wcmVzbzoKICAgICAgICAgICAgY2FuZGlkYXRhcyA9IHIuZ2V0KCJ0b3RhbF9jYW5kaWRhdGVfc2hlZXRzIiwgIj8iKQogICAgICAgICAgICBpbmZvID0gewogICAgICAgICAgICAgICAgImN1cnJlbnRfZW5kIjogICAgICAgclsiY3VycmVudF9lbmQiXSwKICAgICAgICAgICAgICAgICJwcmlvcl9lbmQiOiAgICAgICAgIHJbInByaW9yX2VuZCJdLAogICAgICAgICAgICAgICAgInNvdXJjZV9iYWxhbmNlIjogICAgci5nZXQoInNvdXJjZV9iYWxhbmNlIiwgIj8iKSwKICAgICAgICAgICAgICAgICJzb3VyY2VfZWVyciI6ICAgICAgIHIuZ2V0KCJzb3VyY2VfZWVyciIsICJObyBlbmNvbnRyYWRvIiksCiAgICAgICAgICAgICAgICAic291cmNlX3ByZXZfcGVyaW9kIjpyLmdldCgic291cmNlX3ByZXZfcGVyaW9kIiwgIk5vIGVuY29udHJhZG8iKSwKICAgICAgICAgICAgICAgICJzb3VyY2VfY3Vycl9wcmV2IjogIHIuZ2V0KCJzb3VyY2VfY3Vycl9wcmV2IiwgIk5vIGVuY29udHJhZG8iKSwKICAgICAgICAgICAgfQogICAgICAgICAgICBwcmludChmIkFyY2hpdm8gZGVzdGlubyAgIDoge2V0aXF1ZXRhfSIpCiAgICAgICAgICAgIHByaW50KGYiUGVyw61vZG8gYWN0dWFsICAgIDoge3JbJ2N1cnJlbnRfZW5kJ119IikKICAgICAgICAgICAgcHJpbnQoZiJDb21wYXJhdGl2byBiYWwuICA6IHtyWydwcmlvcl9lbmQnXX0iKQogICAgICAgICAgICBwcmludChmIkZ1ZW50ZSBiYWxhbmNlICAgIDoge2luZm9bJ3NvdXJjZV9iYWxhbmNlJ119IikKICAgICAgICAgICAgcHJpbnQoZiJGdWVudGUgRUVSUiAgICAgICA6IHtpbmZvWydzb3VyY2VfZWVyciddfSIpCiAgICAgICAgICAgIHByaW50KGYiRnVlbnRlIHByZXYucGVyaW9kOiB7aW5mb1snc291cmNlX3ByZXZfcGVyaW9kJ119IikKICAgICAgICAgICAgcHJpbnQoZiJGdWVudGUgY3Vyci5wcmV2ICA6IHtpbmZvWydzb3VyY2VfY3Vycl9wcmV2J119IikKICAgICAgICAgICAgcHJpbnQoZiJIb2phcyBhIHZhbGlkYXIgICA6IHtjYW5kaWRhdGFzfSIKICAgICAgICAgICAgICAgICAgZiIgKGV4Y2x1aWRvcyB7ci5nZXQoJ3NraXBwZWRfZGVzZ2xvc2Vfc29jaWVkYWQnLCAwKX0gZGVzZ2xvc2VzIHBvciBzb2NpZWRhZCkiKQogICAgICAgICAgICBwcmludCgiLSIgKiA3MCkKICAgICAgICAgICAgZW5jYWJlemFkb19pbXByZXNvID0gVHJ1ZQoKICAgICAgICBmb3Igc2ggaW4gci5nZXQoInNoZWV0c19wcm9jZXNzZWQiLCBbXSk6CiAgICAgICAgICAgIG5vbWJyZV9ob2phID0gc2hbInNoZWV0Il0KCiAgICAgICAgICAgICMgU3ViaG9qYSBkZSBhcG95byBkZSB1biBjb25zb2xpZGFkbzogbm8gc2UgdmFsaWRhLgogICAgICAgICAgICBwYWRyZSA9IGRldGVjdG9yLmVzX3N1YmhvamEobm9tYnJlX2hvamEpCiAgICAgICAgICAgIGlmIHBhZHJlIGlzIG5vdCBOb25lOgogICAgICAgICAgICAgICAgb21pdGlkYXNfc3ViaG9qYSArPSAxCiAgICAgICAgICAgICAgICBjb250aW51ZQoKICAgICAgICAgICAgaWYgcHJlZmlqb19ob2phKG5vbWJyZV9ob2phKSBpbiBOT1RBU19FWENMVUlEQVNfVkFMSURBQ0lPTjoKICAgICAgICAgICAgICAgIG9taXRpZGFzX2V4Y2x1aWRhcyArPSAxCiAgICAgICAgICAgICAgICBjb250aW51ZQoKICAgICAgICAgICAgZGVzZGUsIGhhc3RhID0gcmFuZ29fZmlsYXMobm9tYnJlX2hvamEpCiAgICAgICAgICAgIGZpbGFzX2V4Y2x1aWRhcyA9IEZJTEFTX0VYQ0xVSURBU19QT1JfTk9UQS5nZXQocHJlZmlqb19ob2phKG5vbWJyZV9ob2phKSwgc2V0KCkpCiAgICAgICAgICAgIGZpbGFzX2hvamE6IGxpc3RbZGljdF0gPSBbXQogICAgICAgICAgICBjb21wcyA9IHNoLmdldCgiY29tcGFyYWNpb24iLCBbXSkKICAgICAgICAgICAgZm9yIGNvbXAgaW4gY29tcHM6CiAgICAgICAgICAgICAgICBjb250ZXh0byA9IChjb21wLmdldCgiY29udGV4dG8iKSBvciAiIikuc3RyaXAoKQogICAgICAgICAgICAgICAgdGlwb19jb2wgPSBjb21wLmdldCgidGlwbyIsICJiYWwiKQogICAgICAgICAgICAgICAgZm9yIGYgaW4gY29tcC5nZXQoImZpbGFzIiwgW10pOgogICAgICAgICAgICAgICAgICAgICMgRnVlcmEgZGVsIGFsY2FuY2UgZGUgbGEgbm90YSAoYmxvcXVlcyBhdXhpbGlhcmVzIGFsIHBpZSkuCiAgICAgICAgICAgICAgICAgICAgaWYgKGRlc2RlIGlzIG5vdCBOb25lIGFuZCBmWyJmaWxhIl0gPCBkZXNkZSkgb3IgKGhhc3RhIGlzIG5vdCBOb25lIGFuZCBmWyJmaWxhIl0gPiBoYXN0YSk6CiAgICAgICAgICAgICAgICAgICAgICAgIGZpbGFzX2Z1ZXJhICs9IDEKICAgICAgICAgICAgICAgICAgICAgICAgY29udGludWUKICAgICAgICAgICAgICAgICAgICBpZiBmWyJmaWxhIl0gaW4gZmlsYXNfZXhjbHVpZGFzOgogICAgICAgICAgICAgICAgICAgICAgICBmaWxhc19mdWVyYSArPSAxCiAgICAgICAgICAgICAgICAgICAgICAgIGNvbnRpbnVlCiAgICAgICAgICAgICAgICAgICAgaWYgZlsiZXN0YWRvIl0gPT0gIk9LIjoKICAgICAgICAgICAgICAgICAgICAgICAgdG90YWxfZXF1YWwgKz0gMQogICAgICAgICAgICAgICAgICAgIGVsaWYgZlsiZXN0YWRvIl0gPT0gIlNJTiBDT1JSRVNQT05ERU5DSUEiOgogICAgICAgICAgICAgICAgICAgICAgICB0b3RhbF9zaW5fY29yciArPSAxCiAgICAgICAgICAgICAgICAgICAgZWxzZToKICAgICAgICAgICAgICAgICAgICAgICAgdG90YWxfZGlmZiArPSAxCiAgICAgICAgICAgICAgICAgICAgYmFzZSA9IGZbImV0aXF1ZXRhIl0gb3IgZiIoZmlsYSB7ZlsnZmlsYSddfSkiCiAgICAgICAgICAgICAgICAgICAgaWYgY29udGV4dG86CiAgICAgICAgICAgICAgICAgICAgICAgIGV0aXEgPSBmIntiYXNlfSAtIHtjb250ZXh0b30iCiAgICAgICAgICAgICAgICAgICAgZWxpZiBsZW4oY29tcHMpID4gMToKICAgICAgICAgICAgICAgICAgICAgICAgZXRpcSA9IGYie2Jhc2V9IChjb2wge2NvbXBbJ2NvbCddfSB7dGlwb19jb2x9KSIKICAgICAgICAgICAgICAgICAgICBlbHNlOgogICAgICAgICAgICAgICAgICAgICAgICBldGlxID0gYmFzZQogICAgICAgICAgICAgICAgICAgIGlmIGZbImVzdGFkbyJdID09ICJIQUxMQVpHTyI6CiAgICAgICAgICAgICAgICAgICAgICAgIHRyeToKICAgICAgICAgICAgICAgICAgICAgICAgICAgIG5vdGEgPSBmImRpZmllcmUgZW4ge2Zsb2F0KGZbJ2Rlc3Rpbm8nXSkgLSBmbG9hdChmWydmdWVudGUnXSk6LC4wZn0iCiAgICAgICAgICAgICAgICAgICAgICAgIGV4Y2VwdCAoVHlwZUVycm9yLCBWYWx1ZUVycm9yKToKICAgICAgICAgICAgICAgICAgICAgICAgICAgIG5vdGEgPSAiZGlmaWVyZSIKICAgICAgICAgICAgICAgICAgICBlbGlmIGZbImVzdGFkbyJdID09ICJOTyBQUk9DRVNBRE8iOgogICAgICAgICAgICAgICAgICAgICAgICBub3RhID0gInZhbG9yIGRlc3Rpbm8gbm8gbnVtw6lyaWNvIgogICAgICAgICAgICAgICAgICAgIGVsaWYgZlsiZXN0YWRvIl0gPT0gIlNJTiBDT1JSRVNQT05ERU5DSUEiOgogICAgICAgICAgICAgICAgICAgICAgICBub3RhID0gImxhIGZpbGEgbm8gZXhpc3RlIGVuIGVsIGFyY2hpdm8gZnVlbnRlOiByZXZpc2FyIG1hbnVhbG1lbnRlIgogICAgICAgICAgICAgICAgICAgIGVsc2U6CiAgICAgICAgICAgICAgICAgICAgICAgIG5vdGEgPSBOb25lCiAgICAgICAgICAgICAgICAgICAgZmlsYXNfaG9qYS5hcHBlbmQoewogICAgICAgICAgICAgICAgICAgICAgICAiZmlsYSI6IGZbImZpbGEiXSwgImV0aXF1ZXRhIjogZXRpcSwKICAgICAgICAgICAgICAgICAgICAgICAgImRlc3Rpbm8iOiBmWyJkZXN0aW5vIl0sICJmdWVudGUiOiBmWyJmdWVudGUiXSwKICAgICAgICAgICAgICAgICAgICAgICAgImVzdGFkbyI6IGZbImVzdGFkbyJdLCAibm90YSI6IG5vdGEsCiAgICAgICAgICAgICAgICAgICAgfSkKICAgICAgICAgICAgaG9qYXMuYXBwZW5kKHsibm9tYnJlIjogbm9tYnJlX2hvamEsICJmaWxhcyI6IGZpbGFzX2hvamF9KQoKICAgICAgICBwcmludChmIiAgbG90ZSBvZmZzZXQge3JbJ3NoZWV0X29mZnNldCddOj4zfToge3JbJ2JhdGNoX3NpemUnXX0gaG9qYXMgcmV2aXNhZGFzIikKCiAgICAgICAgaWYgbm90IHIuZ2V0KCJoYXNfbW9yZSIpOgogICAgICAgICAgICBicmVhawogICAgICAgIG9mZnNldCA9IHJbIm5leHRfb2Zmc2V0Il0KCiAgICBwcmludCgiLSIgKiA3MCkKICAgIHByaW50KGYiUkVTVU1FTjoge2xlbihob2phcyl9IGhvamFzIHwgIgogICAgICAgICAgZiJ7dG90YWxfZXF1YWx9IHZhbG9yZXMgaWd1YWxlcyB8IHt0b3RhbF9kaWZmfSBjb24gaGFsbGF6Z28vbm8gcHJvY2VzYWRvIikKICAgIGlmIG9taXRpZGFzX3N1YmhvamE6CiAgICAgICAgcHJpbnQoZiIgICh7b21pdGlkYXNfc3ViaG9qYX0gc3ViaG9qYShzKSBkZSBhcG95byBvbWl0aWRhcywgdmVyIGRldGFsbGUgYXJyaWJhKSIpCiAgICBpZiBvbWl0aWRhc19leGNsdWlkYXM6CiAgICAgICAgcHJpbnQoZiIgICh7b21pdGlkYXNfZXhjbHVpZGFzfSBob2phKHMpIGV4Y2x1aWRhcyB0ZW1wb3JhbG1lbnRlIGRlIGxhIHZhbGlkYWNpw7NuOiAiCiAgICAgICAgICAgICAgZiJ7c29ydGVkKE5PVEFTX0VYQ0xVSURBU19WQUxJREFDSU9OKX0pIikKICAgIGlmIGZpbGFzX2Z1ZXJhOgogICAgICAgIHByaW50KGYiICAoe2ZpbGFzX2Z1ZXJhfSBmaWxhKHMpIGZ1ZXJhIGRlbCBhbGNhbmNlIGRlIHN1IG5vdGEsIG9taXRpZGFzKSIpCiAgICBpZiB0b3RhbF9zaW5fY29ycjoKICAgICAgICBwcmludChmIiAgKHt0b3RhbF9zaW5fY29ycn0gZmlsYShzKSBzaW4gY29ycmVzcG9uZGVuY2lhIGVuIGVsIGFyY2hpdm8gZnVlbnRlLCAiCiAgICAgICAgICAgICAgZiJyZXZpc2FyIG1hbnVhbG1lbnRlIGVuIGVsIEV4Y2VsKSIpCgogICAgbSA9IHJlLm1hdGNoKHIiKEVcZCspXyhJTkR8Q09OU08pXyhcZHsyfSlbLV9dKFxkezR9KSIsIGV0aXF1ZXRhKQogICAgaWYgbToKICAgICAgICBiYXNlICAgICAgPSBmInttLmdyb3VwKDEpfV97bS5ncm91cCgyKX1fe20uZ3JvdXAoMyl9LXttLmdyb3VwKDQpfSIKICAgICAgICBzdWJ0aXR1bG8gPSBmInttLmdyb3VwKDEpfSB7bS5ncm91cCgyKX0ge20uZ3JvdXAoMyl9LXttLmdyb3VwKDQpfSIKICAgIGVsc2U6CiAgICAgICAgYmFzZSAgICAgID0gcmUuc3ViKHInW1xcLzoqPyI8Pnxcc10rJywgIl8iLCBldGlxdWV0YSkKICAgICAgICBzdWJ0aXR1bG8gPSBldGlxdWV0YQogICAgc3VidGl0dWxvICs9IChmIiDigJQgYmFsIHtpbmZvLmdldCgncHJpb3JfZW5kJywnPycpfSIKICAgICAgICAgICAgICAgICAgZiIgLyBFRVJSIHtpbmZvLmdldCgnc291cmNlX2VlcnInLCc/Jyl9IgogICAgICAgICAgICAgICAgICBmIiDigJQgcmV2aXNhZG8ge2RhdGV0aW1lLm5vdygpLnN0cmZ0aW1lKCclWS0lbS0lZCAlSDolTScpfSIpCgogICAgcnV0YSA9IG9zLnBhdGguYWJzcGF0aChmImRldGFsbGVfZmlsYXNfe2Jhc2V9Lnhsc3giKQogICAgZXhwb3J0YXJfZXhjZWwoCiAgICAgICAgcnV0YSwKICAgICAgICAiRGV0YWxsZSBmaWxhIHBvciBmaWxhIOKAlCBjb21wYXJhdGl2byBkZWNsYXJhZG8gdnMuIGFyY2hpdm8gZnVlbnRlIChWMikiLAogICAgICAgIHN1YnRpdHVsbywKICAgICAgICBob2phcywKICAgICkKICAgIHByaW50KGYiXG5FeGNlbCBnZW5lcmFkbzoge3J1dGF9IikKCiAgICByZXR1cm4gMiBpZiB0b3RhbF9kaWZmIGVsc2UgMAoKCmFzeW5jIGRlZiBtYWluKCkgLT4gaW50OgogICAgcGFyc2VyID0gYXJncGFyc2UuQXJndW1lbnRQYXJzZXIoCiAgICAgICAgZGVzY3JpcHRpb249IlZhbGlkYSBjb21wYXJhdGl2b3MgKGJhbGFuY2UgKyBFRVJSKSBkZSB1biBCYXNlIE5vdGFzIGRlIFdvcmtpdmEuIiwKICAgICAgICBmb3JtYXR0ZXJfY2xhc3M9YXJncGFyc2UuUmF3RGVzY3JpcHRpb25IZWxwRm9ybWF0dGVyLAogICAgKQogICAgcGFyc2VyLmFkZF9hcmd1bWVudCgic29jaWVkYWQiLCAgIG5hcmdzPSI/IikKICAgIHBhcnNlci5hZGRfYXJndW1lbnQoImFuaW8iLCAgICAgICBuYXJncz0iPyIpCiAgICBwYXJzZXIuYWRkX2FyZ3VtZW50KCJ0cmltZXN0cmUiLCAgbmFyZ3M9Ij8iKQogICAgcGFyc2VyLmFkZF9hcmd1bWVudCgiLS10aXBvIiwgICAgIGNob2ljZXM9WyJDT05TTyIsICJJTkQiXSwgZGVmYXVsdD0iQ09OU08iKQogICAgcGFyc2VyLmFkZF9hcmd1bWVudCgiLS1pZCIsICAgICAgIGRlc3Q9InNwcmVhZHNoZWV0X2lkIikKICAgIHBhcnNlci5hZGRfYXJndW1lbnQoIi0tbG90ZSIsICAgICB0eXBlPWludCwgZGVmYXVsdD01MCkKICAgIGFyZ3MgPSBwYXJzZXIucGFyc2VfYXJncygpCgogICAgaWYgYXJncy5zcHJlYWRzaGVldF9pZDoKICAgICAgICBzc19pZCwgZXRpcXVldGEgPSBhcmdzLnNwcmVhZHNoZWV0X2lkLCBhcmdzLnNwcmVhZHNoZWV0X2lkCiAgICBlbHNlOgogICAgICAgIGlmIGFyZ3Muc29jaWVkYWQgYW5kIGFyZ3MuYW5pbyBhbmQgYXJncy50cmltZXN0cmU6CiAgICAgICAgICAgIHNvY2llZGFkLCBhbmlvLCB0aXBvLCB0cmltZXN0cmUgPSAoCiAgICAgICAgICAgICAgICBhcmdzLnNvY2llZGFkLnVwcGVyKCksIGFyZ3MuYW5pbywgYXJncy50aXBvLCBhcmdzLnRyaW1lc3RyZQogICAgICAgICAgICApCiAgICAgICAgICAgIGlmIHRyaW1lc3RyZS51cHBlcigpIG5vdCBpbiBNRVNfUE9SX1RSSU1FU1RSRToKICAgICAgICAgICAgICAgIHByaW50KGYiRVJST1I6IHRyaW1lc3RyZSAne3RyaW1lc3RyZX0nIG5vIHbDoWxpZG8uIikKICAgICAgICAgICAgICAgIHJldHVybiAxCiAgICAgICAgZWxzZToKICAgICAgICAgICAgc29jaWVkYWQsIGFuaW8sIHRpcG8sIHRyaW1lc3RyZSA9IHBlZGlyX29wY2lvbmVzKCkKCiAgICAgICAgZW5jb250cmFkbyA9IGF3YWl0IHJlc29sdmVyX3NwcmVhZHNoZWV0KHNvY2llZGFkLCBhbmlvLCB0cmltZXN0cmUsIHRpcG8pCiAgICAgICAgaWYgbm90IGVuY29udHJhZG86CiAgICAgICAgICAgIHJldHVybiAxCiAgICAgICAgc3NfaWQsIGV0aXF1ZXRhID0gZW5jb250cmFkbwoKICAgIHJldHVybiBhd2FpdCB2YWxpZGFyKHNzX2lkLCBldGlxdWV0YSwgYXJncy5sb3RlKQoKCmlmIF9fbmFtZV9fID09ICJfX21haW5fXyI6CiAgICB0cnk6CiAgICAgICAgc3lzLmV4aXQoYXN5bmNpby5ydW4obWFpbigpKSkKICAgIGV4Y2VwdCBLZXlib2FyZEludGVycnVwdDoKICAgICAgICBwcmludCgiXG5DYW5jZWxhZG8uIikKICAgICAgICBzeXMuZXhpdCgxKQo="
).decode("utf-8")


# Módulos con acceso restringido: key → contraseña
RESTRICTED_MODULES = {}

NAV_ITEMS = [
    ("Verificador de Sumas",   "verif"),
    ("Llenar Comparativos",    "mod2"),
    ("Flujo de Efectivo",      "mod5"),
    ("Validar Comparativos",   "mod6"),
]

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Auditor — CGE Workiva")
        self.configure(bg=CGE_LIGHT)
        self.resizable(True, True)
        self.minsize(980, 680)

        self._docs      = []
        self._doc_vars  = []
        self._running   = False
        self._stop_flag = False
        self._ss_id     = None
        self._ss_name   = None
        self._ss_cache  = None
        self._docx_dir  = None
        self._active_view = None

        self._build_ui()
        self._center(1080, 720)

    def _center(self, w, h):
        self.update_idletasks()
        x = (self.winfo_screenwidth()  - w) // 2
        y = (self.winfo_screenheight() - h) // 2
        self.geometry(f"{w}x{h}+{x}+{y}")

    # ── UI ────────────────────────────────────────────────────────────────────
    def _build_ui(self):
        # Grid layout en la ventana principal: header fila 0, contenido fila 1, footer fila 2
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)

        # Header
        hdr_frame = tk.Frame(self)
        hdr_frame.grid(row=0, column=0, sticky="ew")
        self._build_header(hdr_frame)

        # Contenido principal
        main = tk.Frame(self, bg=CGE_LIGHT)
        main.grid(row=1, column=0, sticky="nsew")

        self._build_sidebar(main)

        right_col = tk.Frame(main, bg=CGE_LIGHT)
        right_col.pack(side="left", fill="both", expand=True)

        self._content = tk.Frame(right_col, bg=CGE_LIGHT)
        self._content.pack(fill="both", expand=True)

        # Footer — siempre en fila 2, ancho completo
        footer = tk.Frame(self, bg=CGE_BLUE, pady=6)
        footer.grid(row=2, column=0, sticky="ew")

        # Construir vistas
        self._views = {}
        self._build_view_verif()
        self._build_view_comparativos()
        self._build_view_flujo_efectivo()
        self._build_view_validar_comparativos()

        # Mostrar primera vista
        self._show_view("verif")

    def _build_sidebar(self, parent):
        sidebar = tk.Frame(parent, bg=CGE_SIDEBAR, width=210)
        sidebar.pack(side="left", fill="y")
        sidebar.pack_propagate(False)

        # Línea separadora derecha
        tk.Frame(parent, bg=CGE_BLUE2, width=2).pack(side="left", fill="y")

        tk.Label(sidebar, text="HERRAMIENTAS", font=("Segoe UI", 7, "bold"),
                 bg=CGE_SIDEBAR, fg="#4a6ab5").pack(anchor="w", padx=18, pady=(16, 4))

        self._nav_btns = {}
        for label, key in NAV_ITEMS:
            btn = tk.Button(
                sidebar, text=label,
                font=FONT_SMALL, anchor="w",
                bg=CGE_SIDEBAR, fg=CGE_WHITE,
                activebackground=CGE_BLUE, activeforeground=CGE_WHITE,
                relief="flat", bd=0, padx=18, pady=12,
                cursor="hand2",
                command=lambda k=key: self._show_view(k)
            )
            btn.pack(fill="x")
            self._nav_btns[key] = btn

    def _show_view(self, key):
        # Verificar acceso restringido
        if key in RESTRICTED_MODULES:
            if not self._pedir_clave(key):
                return

        # Resaltar botón activo
        for k, btn in self._nav_btns.items():
            btn.configure(bg=CGE_BLUE if k == key else CGE_SIDEBAR)

        # Ocultar todas las vistas y mostrar la seleccionada
        for k, frame in self._views.items():
            frame.pack_forget()
        self._views[key].pack(fill="both", expand=True, padx=18, pady=14)
        self._active_view = key

        # Actualizar subtítulo del header
        label = next(l for l, k in NAV_ITEMS if k == key)
        self._header_subtitle.configure(text=label)

    def _pedir_clave(self, key):
        popup = tk.Toplevel(self)
        popup.transient(self)
        popup.title("Acceso restringido")
        popup.resizable(False, False)
        popup.grab_set()
        popup.configure(bg=CGE_CARD)

        # Centrar popup
        popup.update_idletasks()
        pw, ph = 340, 200
        x = self.winfo_x() + (self.winfo_width()  - pw) // 2
        y = self.winfo_y() + (self.winfo_height() - ph) // 2
        popup.geometry(f"{pw}x{ph}+{x}+{y}")

        tk.Label(popup, text="Módulo restringido",
                 font=("Segoe UI", 11, "bold"),
                 bg=CGE_CARD, fg=CGE_BLUE).pack(pady=(18, 4))
        tk.Label(popup, text="Ingresa la contraseña para continuar:",
                 font=FONT_SMALL, bg=CGE_CARD, fg=CGE_MUTED).pack()

        var = tk.StringVar()
        entry = tk.Entry(popup, textvariable=var, show="•",
                         font=FONT_LABEL, bg=CGE_LIGHT, fg=CGE_TEXT,
                         relief="flat", bd=4, width=20,
                         highlightbackground=CGE_BORDER, highlightthickness=1)
        entry.pack(pady=10)
        entry.focus_set()

        result = [False]

        error_lbl = tk.Label(popup, text="", font=FONT_SMALL,
                             bg=CGE_CARD, fg=CGE_RED)
        error_lbl.pack()

        def confirmar(e=None):
            if var.get() == RESTRICTED_MODULES[key]:
                result[0] = True
                popup.destroy()
            else:
                entry.configure(highlightbackground=CGE_RED, highlightthickness=2)
                error_lbl.configure(text="Contraseña incorrecta.")
                var.set("")
                entry.focus_set()

        btn_frame = tk.Frame(popup, bg=CGE_CARD)
        btn_frame.pack()
        tk.Button(btn_frame, text="Cancelar", font=FONT_SMALL,
                  bg=CGE_BORDER, fg=CGE_TEXT, relief="flat", bd=0,
                  padx=12, pady=5, cursor="hand2",
                  command=popup.destroy).pack(side="left", padx=(0, 6))
        tk.Button(btn_frame, text="Entrar", font=FONT_SMALL,
                  bg=CGE_BLUE, fg=CGE_WHITE, relief="flat", bd=0,
                  padx=12, pady=5, cursor="hand2",
                  command=confirmar).pack(side="left")

        entry.bind("<Return>", confirmar)
        popup.wait_window()
        return result[0]


    # ── LLENAR COMPARATIVOS ───────────────────────────────────────────────────
    def _build_view_comparativos(self):
        frame = tk.Frame(self._content, bg=CGE_LIGHT)
        self._views["mod2"] = frame

        body = tk.Frame(frame, bg=CGE_LIGHT)
        body.pack(fill="both", expand=True)

        # Panel izquierdo
        left = tk.Frame(body, bg=CGE_LIGHT, width=230)
        left.pack(side="left", fill="y", padx=(0, 14))
        left.pack_propagate(False)

        # Card periodo
        tk.Label(left, text="PERIODO", font=("Segoe UI", 8, "bold"),
                 bg=CGE_LIGHT, fg=CGE_MUTED).pack(anchor="w", pady=(6, 2))
        pf = tk.Frame(left, bg=CGE_CARD,
                      highlightbackground=CGE_BORDER, highlightthickness=1)
        pf.pack(fill="x", pady=(0, 10))
        inner = tk.Frame(pf, bg=CGE_CARD, padx=12, pady=10)
        inner.pack(fill="x")

        tk.Label(inner, text="Mes", font=FONT_SMALL,
                 bg=CGE_CARD, fg=CGE_MUTED).grid(row=0, column=0, sticky="w", pady=4)
        self._cmp_mes = tk.StringVar()
        _e_cmp_mes = tk.Entry(inner, textvariable=self._cmp_mes, font=FONT_LABEL,
                 bg=CGE_LIGHT, fg=CGE_TEXT, relief="flat", bd=4, width=12,
                 highlightbackground=CGE_BORDER, highlightthickness=1)
        _e_cmp_mes.grid(row=0, column=1, sticky="ew", padx=(8,0), pady=4)
        _e_cmp_mes.bind("<Return>", lambda e: self._cmp_on_buscar())

        tk.Label(inner, text="Año", font=FONT_SMALL,
                 bg=CGE_CARD, fg=CGE_MUTED).grid(row=1, column=0, sticky="w", pady=4)
        self._cmp_anio = tk.StringVar()
        _e_cmp_anio = tk.Entry(inner, textvariable=self._cmp_anio, font=FONT_LABEL,
                 bg=CGE_LIGHT, fg=CGE_TEXT, relief="flat", bd=4, width=12,
                 highlightbackground=CGE_BORDER, highlightthickness=1)
        _e_cmp_anio.grid(row=1, column=1, sticky="ew", padx=(8,0), pady=4)
        _e_cmp_anio.bind("<Return>", lambda e: self._cmp_on_buscar())
        inner.columnconfigure(1, weight=1)

        # Botones
        tk.Frame(left, bg=CGE_LIGHT, height=4).pack()
        self._cmp_btn_buscar = tk.Button(left, text="Buscar archivos",
                  font=FONT_BOLD, bg=CGE_BLUE, fg=CGE_WHITE,
                  activebackground=CGE_BLUE2, activeforeground=CGE_WHITE,
                  relief="flat", bd=0, padx=10, pady=9,
                  cursor="hand2", command=self._cmp_on_buscar)
        self._cmp_btn_buscar.pack(fill="x")
        self._cmp_btn_buscar.bind("<Return>", lambda e: self._cmp_on_buscar())
        tk.Frame(left, bg=CGE_LIGHT, height=6).pack()
        self._cmp_btn_procesar = tk.Button(left, text="Procesar seleccionados",
                  font=FONT_BOLD, bg=CGE_GREEN, fg=CGE_WHITE, disabledforeground="#E4E9F5",
                  activebackground="#076b45", activeforeground=CGE_WHITE,
                  relief="flat", bd=0, padx=10, pady=9,
                  cursor="hand2", command=self._cmp_on_procesar, state="disabled")
        self._cmp_btn_procesar.pack(fill="x")
        self._cmp_btn_procesar.bind("<Return>", lambda e: self._cmp_on_procesar())
        tk.Frame(left, bg=CGE_LIGHT, height=4).pack()
        self._cmp_btn_reintentar = tk.Button(left, text="Reintentar fallidos",
                  font=FONT_BOLD, bg=CGE_YELLOW, fg="#1a1a1a",
                  activebackground="#c88a00", activeforeground="#1a1a1a",
                  relief="flat", bd=0, padx=10, pady=9,
                  cursor="hand2", command=self._cmp_on_reintentar)
        # starts hidden — only shown after a run that has failures
        self._cmp_failed = []

        # Panel derecho
        right = tk.Frame(body, bg=CGE_LIGHT)
        right.pack(side="left", fill="both", expand=True)

        # Archivos encontrados
        arch_hdr = tk.Frame(right, bg=CGE_LIGHT)
        arch_hdr.pack(fill="x", pady=(0, 4))
        tk.Label(arch_hdr, text="ARCHIVOS ENCONTRADOS", font=("Segoe UI", 8, "bold"),
                 bg=CGE_LIGHT, fg=CGE_MUTED).pack(side="left")
        tk.Button(arch_hdr, text="Desmarcar todas", font=FONT_SMALL,
                  bg=CGE_BORDER, fg=CGE_TEXT, relief="flat", bd=0,
                  padx=8, pady=2, cursor="hand2",
                  command=lambda: [v.set(False) for v in self._cmp_vars]
                  ).pack(side="right", padx=(4,0))
        tk.Button(arch_hdr, text="Marcar todas", font=FONT_SMALL,
                  bg=CGE_BLUE, fg=CGE_WHITE, relief="flat", bd=0,
                  padx=8, pady=2, cursor="hand2",
                  command=lambda: [v.set(True) for v in self._cmp_vars]
                  ).pack(side="right")
        self._cmp_sel_count_lbl = tk.Label(arch_hdr, text="", font=FONT_SMALL,
                                           bg=CGE_LIGHT, fg=CGE_MUTED)
        self._cmp_sel_count_lbl.pack(side="right", padx=(0, 8))
        doc_box = tk.Frame(right, bg=CGE_CARD,
                           highlightbackground=CGE_BORDER, highlightthickness=1)
        doc_box.pack(fill="x", pady=(0, 12))
        self._cmp_canvas = tk.Canvas(doc_box, bg=CGE_CARD, highlightthickness=0, height=200)
        sb = tk.Scrollbar(doc_box, orient="vertical", command=self._cmp_canvas.yview)
        self._cmp_canvas.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        self._cmp_canvas.pack(side="left", fill="both", expand=True)
        self._cmp_inner = tk.Frame(self._cmp_canvas, bg=CGE_CARD)
        cmp_win = self._cmp_canvas.create_window((0,0), window=self._cmp_inner, anchor="nw")
        self._cmp_inner.bind("<Configure>",
            lambda e: self._cmp_canvas.configure(scrollregion=self._cmp_canvas.bbox("all")))
        self._cmp_canvas.bind("<Configure>",
            lambda e: self._cmp_canvas.itemconfig(cmp_win, width=e.width))
        self._cmp_canvas.bind("<MouseWheel>",
            lambda e: self._cmp_canvas.yview_scroll(int(-1*(e.delta/120)), "units"))
        self._cmp_files  = []
        self._cmp_vars   = []
        self._cmp_lbl_empty = tk.Label(self._cmp_inner,
            text="Ingresa el periodo y presiona 'Buscar archivos'",
            font=FONT_SMALL, bg=CGE_CARD, fg=CGE_MUTED, pady=20)
        self._cmp_lbl_empty.pack()

        # Log actividad
        act_hdr = tk.Frame(right, bg=CGE_LIGHT)
        act_hdr.pack(fill="x", pady=(0, 4))
        tk.Label(act_hdr, text="ACTIVIDAD", font=("Segoe UI", 8, "bold"),
                 bg=CGE_LIGHT, fg=CGE_MUTED).pack(side="left")
        tk.Button(act_hdr, text="Limpiar", font=FONT_SMALL,
                  bg=CGE_BORDER, fg=CGE_TEXT, relief="flat", bd=0,
                  padx=8, pady=2, cursor="hand2",
                  command=lambda: self._cmp_clear_log()).pack(side="right")
        self._cmp_stop_flag = False
        self._cmp_btn_detener = tk.Button(act_hdr, text="Detener", font=FONT_SMALL,
                  bg=CGE_RED, fg=CGE_WHITE, relief="flat", bd=0,
                  padx=8, pady=2, cursor="hand2",
                  command=self._cmp_detener)
        # se muestra solo cuando hay proceso activo
        log_box = tk.Frame(right, bg=CGE_CARD,
                           highlightbackground=CGE_BORDER, highlightthickness=1)
        log_box.pack(fill="both", expand=True)
        self._cmp_log = scrolledtext.ScrolledText(
            log_box, font=FONT_MONO, bg=CGE_CARD, fg=CGE_TEXT,
            relief="flat", bd=8, state="disabled", wrap="word", height=8)
        self._cmp_log.pack(fill="both", expand=True)
        self._cmp_log.tag_config("ok",   foreground=CGE_GREEN)
        self._cmp_log.tag_config("err",  foreground=CGE_RED)
        self._cmp_log.tag_config("warn", foreground=CGE_YELLOW)
        self._cmp_log.tag_config("blue", foreground=CGE_BLUE)
        self._cmp_log.tag_config("bold", font=("Consolas", 9, "bold"))
        self._cmp_log.tag_config("muted",foreground=CGE_MUTED)

    def _cmp_detener(self):
        self._cmp_stop_flag = True
        self._cmp_btn_detener.pack_forget()
        self._cmp_log_write(
            "\n⏹ Deteniendo... se completara el lote en curso para no dejar "
            "una escritura parcial en Workiva.", "warn")

    @staticmethod
    def _wav_aviso(tonos=((880, 0.16), (1175, 0.24)), fr=44100, vol=0.45):
        """Genera en memoria un WAV con un par de tonos. Se reproduce por la
        ruta de audio normal (waveOut), que es la unica que no depende ni del
        esquema de sonidos de Windows ni de la API Beep — ambas pueden quedar
        mudas en equipos corporativos y en sesiones RDP/VDI."""
        buf = io.BytesIO()
        with wave.open(buf, "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(fr)
            frames = bytearray()
            for freq, dur in tonos:
                n = int(fr * dur)
                for i in range(n):
                    # Envolvente de ataque/caida para que no suene un "clic".
                    env = min(1.0, i / 400.0, (n - i) / 400.0)
                    frames += struct.pack(
                        "<h", int(32767 * vol * env * math.sin(2 * math.pi * freq * i / fr)))
            w.writeframes(bytes(frames))
        return buf.getvalue()

    def _flash_taskbar(self):
        """Hace parpadear el boton de la app en la barra de tareas hasta que
        el usuario la mira. No depende del stack de audio, asi que sirve de
        aviso aunque el sonido no funcione (RDP/VDI, esquema sin sonidos)."""
        try:
            import ctypes

            class FLASHWINFO(ctypes.Structure):
                _fields_ = [("cbSize",    ctypes.c_uint),
                            ("hwnd",      ctypes.c_void_p),
                            ("dwFlags",   ctypes.c_uint),
                            ("uCount",    ctypes.c_uint),
                            ("dwTimeout", ctypes.c_uint)]

            user32 = ctypes.windll.user32
            GA_ROOT          = 2
            FLASHW_ALL       = 0x00000003   # titulo + boton de la barra
            FLASHW_TIMERNOFG = 0x0000000C   # parpadea hasta que pase a primer plano

            hwnd = user32.GetAncestor(self.winfo_id(), GA_ROOT)
            if not hwnd:
                return
            info = FLASHWINFO(ctypes.sizeof(FLASHWINFO), hwnd,
                              FLASHW_ALL | FLASHW_TIMERNOFG, 0, 0)
            user32.FlashWindowEx(ctypes.byref(info))
        except Exception:
            pass

    def _avisar_fin(self):
        """Aviso de proceso terminado: visual (barra de tareas) + sonoro."""
        self._flash_taskbar()
        self._beep()

    def _beep(self):
        """Aviso sonoro al terminar un proceso largo."""
        if winsound is None:
            try:
                self.bell()
            except Exception:
                pass
            return

        if not hasattr(self, "_wav_cache"):
            try:
                self._wav_cache = self._wav_aviso()
            except Exception:
                self._wav_cache = None

        def _play():
            # Se prueban de mas a menos confiable. PlaySound con SND_MEMORY es
            # sincronico a proposito (sin SND_ASYNC): asi el buffer sigue vivo
            # durante toda la reproduccion.
            if self._wav_cache:
                try:
                    winsound.PlaySound(self._wav_cache, winsound.SND_MEMORY)
                    return
                except Exception:
                    pass
            try:
                winsound.Beep(880, 180)
                winsound.Beep(1175, 260)
                return
            except Exception:
                pass
            try:
                winsound.MessageBeep(winsound.MB_ICONASTERISK)
            except Exception:
                pass

        threading.Thread(target=_play, daemon=True).start()

    def _cmp_on_reintentar(self):
        if not self._cmp_failed:
            return
        failed_ids = {f["id"] for f in self._cmp_failed}
        for f, v in zip(self._cmp_files, self._cmp_vars):
            v.set(f["id"] in failed_ids)
        self._cmp_on_procesar()

    def _cmp_show_result_popup(self, resultados, total_ok, total_err, dur_str):
        hay_err = total_err > 0
        # Track which files failed for the retry button
        failed_names = {r["name"] for r in resultados if r["err"] > 0}
        self._cmp_failed = [f for f in self._cmp_files if f["name"] in failed_names]
        if self._cmp_failed:
            self._cmp_btn_reintentar.pack(fill="x")
        else:
            self._cmp_btn_reintentar.pack_forget()
        # Si la ventana principal estaba minimizada, restaurarla — si no, el
        # popup se crea "detrás" y queda invisible hasta restaurar a mano.
        # OJO: solo tocar el estado si estaba "iconic" (minimizada); si no,
        # esto pisaría una ventana maximizada ("zoomed") y la achicaría sola.
        try:
            if self.state() == "iconic":
                self.deiconify()
        except Exception:
            pass

        top = tk.Toplevel(self)
        top.transient(self)
        top.title("Completado sin errores" if not hay_err else f"Completado con {total_err} ERR")
        top.resizable(False, False)
        top.configure(bg="white")

        # ── Zona de icono + contenido ──────────────────────────────────────
        msg_frame = tk.Frame(top, bg="white", padx=16, pady=16)
        msg_frame.pack(fill="both", expand=True)

        icon = "⚠" if hay_err else "✓"
        icon_color = "#E6A817" if hay_err else "#1A7A4A"
        tk.Label(msg_frame, text=icon, font=("Segoe UI", 32),
                 bg="white", fg=icon_color).pack(side="left", anchor="n", padx=(4, 16))

        right = tk.Frame(msg_frame, bg="white")
        right.pack(side="left", anchor="n")

        # Tabla de sociedades
        tk.Label(right, text="Archivos procesados:", font=("Segoe UI", 10, "bold"),
                 bg="white", fg="#1a1a1a").grid(row=0, column=0, columnspan=4, sticky="w", pady=(0,6))

        # Cabecera de tabla
        for col, (txt, ancho) in enumerate([("Sociedad", 35), ("OK", 6), ("ERR", 6), ("Tiempo", 10)]):
            tk.Label(right, text=txt, font=("Segoe UI", 9, "bold"),
                     bg="white", fg="#555", width=ancho, anchor="w").grid(row=1, column=col, padx=(0,8))

        tk.Frame(right, bg="#D0D0D0", height=1).grid(row=2, column=0, columnspan=4, sticky="ew", pady=2)

        for i, r in enumerate(resultados):
            err_color = CGE_RED if r["err"] > 0 else "#1a1a1a"
            tk.Label(right, text=r["name"], font=("Consolas", 9),
                     bg="white", fg="#1a1a1a", anchor="w", width=35).grid(row=3+i, column=0, padx=(0,8), pady=1)
            tk.Label(right, text=str(r["ok"]), font=("Segoe UI", 9, "bold"),
                     bg="white", fg="#1A7A4A", anchor="w", width=6).grid(row=3+i, column=1, padx=(0,8))
            tk.Label(right, text=str(r["err"]), font=("Segoe UI", 9, "bold"),
                     bg="white", fg=err_color, anchor="w", width=6).grid(row=3+i, column=2, padx=(0,8))
            tk.Label(right, text=r.get("dur","–"), font=("Segoe UI", 9),
                     bg="white", fg="#555", anchor="w", width=10).grid(row=3+i, column=3)

        tk.Frame(right, bg="#D0D0D0", height=1).grid(row=3+len(resultados), column=0, columnspan=4, sticky="ew", pady=4)

        # Totales
        n = len(resultados)
        tk.Label(right, text="TOTAL", font=("Segoe UI", 9, "bold"),
                 bg="white", fg="#1a1a1a", anchor="w").grid(row=4+n, column=0, sticky="w")
        tk.Label(right, text=str(total_ok), font=("Segoe UI", 9, "bold"),
                 bg="white", fg="#1A7A4A", anchor="w").grid(row=4+n, column=1)
        tk.Label(right, text=str(total_err), font=("Segoe UI", 9, "bold"),
                 bg="white", fg=CGE_RED if hay_err else "#1a1a1a", anchor="w").grid(row=4+n, column=2)
        tk.Label(right, text=dur_str, font=("Segoe UI", 9, "bold"),
                 bg="white", fg=CGE_BLUE, anchor="w").grid(row=4+n, column=3)

        # ── Separador + botones ────────────────────────────────────────────
        tk.Frame(top, bg="#D0D0D0", height=1).pack(fill="x")
        btn_row = tk.Frame(top, bg="#F0F0F0", padx=12, pady=8)
        btn_row.pack(fill="x")

        if hay_err:
            def ver_errores():
                err_top = tk.Toplevel(top)
                err_top.transient(top)
                err_top.title("Detalle de errores")
                err_top.configure(bg="white")
                err_top.minsize(560, 320)

                hdr = tk.Frame(err_top, bg="white", padx=14, pady=10)
                hdr.pack(fill="x")
                tk.Label(hdr, text="⚠  Sociedades con errores", font=("Segoe UI", 11, "bold"),
                         bg="white", fg="#1a1a1a").pack(anchor="w")

                box_frame = tk.Frame(err_top, bg="white")
                box_frame.pack(fill="both", expand=True, padx=14, pady=(0, 8))
                box = scrolledtext.ScrolledText(
                    box_frame, font=("Consolas", 9), wrap="word",
                    relief="flat", bd=0, padx=8, pady=4, height=16)
                box.pack(fill="both", expand=True)
                box.tag_config("code", font=("Segoe UI", 10, "bold"), foreground=CGE_BLUE)
                box.tag_config("bloq", foreground=CGE_RED)
                box.tag_config("cell", font=("Consolas", 9, "bold"))
                box.tag_config("normal", foreground="#333")

                for r in resultados:
                    if r["err"] <= 0:
                        continue
                    box.insert("end", f"{r['code']}\n", "code")
                    detalle = r.get("detalle", "")
                    if "BLOQUEADA" in detalle or "PROTEGIDA" in detalle:
                        # detalle = "N celda(s) en M columna(s) BLOQUEADA(S)... en Workiva: hoja1 -> Col X: Celda(s) A1, A2 no se ... | hoja2 -> ..."
                        resumen, _, resto = detalle.partition(": ")
                        box.insert("end", f"  ⚠ {resumen}\n", "bloq")
                        for parte in resto.split(" | "):
                            hoja_nom, _, err_txt = parte.partition(" -> ")
                            box.insert("end", f"    · {hoja_nom}\n", "normal")
                            m = re.match(r"(Col \w+): Celda\(s\) (.+?) no se actualizaron", err_txt)
                            if m:
                                box.insert("end", f"        {m.group(1)} — celdas: ", "normal")
                                box.insert("end", f"{m.group(2)}\n", "cell")
                            else:
                                box.insert("end", f"        {err_txt}\n", "normal")
                    elif detalle:
                        box.insert("end", f"  {detalle}\n", "normal")
                    else:
                        box.insert("end", f"  {r['err']} ERR (sin detalle)\n", "normal")
                    box.insert("end", "\n")
                box.configure(state="disabled")

                tk.Frame(err_top, bg="#D0D0D0", height=1).pack(fill="x")
                btn_frame = tk.Frame(err_top, bg="white", pady=10)
                btn_frame.pack(fill="x")
                tk.Button(btn_frame, text="Cerrar", font=("Segoe UI", 9),
                          relief="solid", bd=1, padx=18, pady=5, cursor="hand2",
                          command=err_top.destroy).pack()

                err_top.update_idletasks()
                w, h = err_top.winfo_width(), err_top.winfo_height()
                x = top.winfo_rootx() + (top.winfo_width()  - w) // 2
                y = top.winfo_rooty() + (top.winfo_height() - h) // 2
                err_top.geometry(f"+{max(x,0)}+{max(y,0)}")
                err_top.grab_set()
                err_top.lift()
                err_top.focus_force()
            tk.Button(btn_row, text=f"Ver errores ({total_err})",
                      font=("Segoe UI", 9, "bold"), bg=CGE_RED, fg=CGE_WHITE,
                      relief="flat", padx=14, pady=4, cursor="hand2",
                      command=ver_errores).pack(side="left")
            def _reintentar():
                top.destroy()
                self._cmp_on_reintentar()
            tk.Button(btn_row, text=f"Reintentar fallidos ({total_err})",
                      font=("Segoe UI", 9, "bold"), bg=CGE_YELLOW, fg="#1a1a1a",
                      relief="flat", padx=14, pady=4, cursor="hand2",
                      command=_reintentar).pack(side="left", padx=(8, 0))

        tk.Button(btn_row, text="Aceptar", font=("Segoe UI", 9),
                  relief="solid", bd=1, padx=14, pady=4,
                  cursor="hand2", command=top.destroy).pack(side="right")

        top.update_idletasks()
        w, h = top.winfo_width(), top.winfo_height()
        x = self.winfo_rootx() + (self.winfo_width()  - w) // 2
        y = self.winfo_rooty() + (self.winfo_height() - h) // 2
        top.geometry(f"+{x}+{y}")

        # Forzar que el popup pase al frente aunque la app estuviera minimizada
        # o con otra ventana encima (Excel, navegador, etc.).
        top.grab_set()
        top.lift()
        top.attributes("-topmost", True)
        top.after(300, lambda: top.attributes("-topmost", False))
        top.focus_force()

    def _cmp_log_write(self, msg, tag=None):
        def _do():
            self._cmp_log.configure(state="normal")
            self._cmp_log.insert("end", msg + "\n", tag or "")
            self._cmp_log.see("end")
            self._cmp_log.configure(state="disabled")
        self.after(0, _do)

    def _cmp_clear_log(self):
        self._cmp_log.configure(state="normal")
        self._cmp_log.delete("1.0", "end")
        self._cmp_log.configure(state="disabled")

    def _cmp_render_files(self, files):
        self._cmp_failed = []
        self._cmp_btn_reintentar.pack_forget()
        for w in self._cmp_inner.winfo_children():
            w.destroy()
        self._cmp_vars = []
        if not files:
            tk.Label(self._cmp_inner, text="No se encontraron archivos.",
                     font=FONT_SMALL, bg=CGE_CARD, fg=CGE_RED, pady=14).pack()
            self._cmp_sel_count_lbl.configure(text="")
            return
        for i, f in enumerate(files):
            var = tk.BooleanVar(value=True)
            var.trace_add("write", lambda *a: self._cmp_update_sel_count())
            self._cmp_vars.append(var)
            bg = CGE_ROWALT if i % 2 == 0 else CGE_CARD
            row = tk.Frame(self._cmp_inner, bg=bg)
            row.pack(fill="x")
            cb = tk.Checkbutton(row, text=f["name"], variable=var,
                                font=FONT_SMALL, bg=bg, fg=CGE_TEXT,
                                selectcolor=CGE_LIGHT, activebackground=bg,
                                anchor="w", padx=10, pady=5)
            cb.pack(fill="x")
            for w in (row, cb):
                w.bind("<MouseWheel>",
                    lambda e: self._cmp_canvas.yview_scroll(int(-1*(e.delta/120)), "units"))
        self._cmp_update_sel_count()

    def _cmp_update_sel_count(self):
        marcados = sum(1 for v in self._cmp_vars if v.get())
        self._cmp_sel_count_lbl.configure(text=f"{marcados} de {len(self._cmp_vars)} marcados")

    def _cmp_on_buscar(self):
        mes  = self._cmp_mes.get().strip().zfill(2)
        anio = self._cmp_anio.get().strip()
        if not re.fullmatch(r"\d{2}", mes) or not re.fullmatch(r"\d{4}", anio):
            messagebox.showerror("Error", "Ingresa mes (01-12) y año válidos.")
            return
        self._cmp_clear_log()
        self._cmp_btn_buscar.configure(state="disabled")
        self._cmp_btn_procesar.configure(state="disabled")
        self._progress.configure(mode="indeterminate")
        self._progress.start(10)
        self._cmp_log_write(f"Buscando archivos IND para {mes}-{anio}...", "blue")
        threading.Thread(target=self._cmp_thread_buscar,
                         args=(mes, anio), daemon=True).start()

    def _cmp_thread_buscar(self, mes, anio):
        try:
            import asyncio as _aio_b, os as _os_b, re as _re_b
            _os_b.environ["WORKIVA_CLIENT_ID"]     = CLIENT_ID
            _os_b.environ["WORKIVA_CLIENT_SECRET"] = CLIENT_SECRET
            _os_b.environ["WORKIVA_WORKSPACE_ID"]  = WORKSPACE_ID
            tmpdir   = self._get_mcp_tmpdir()
            mcp_mod  = self._load_mcp_v2_mod(tmpdir)
            mcp_mod._wk._client = None
            all_files = _aio_b.run(mcp_mod._load_all_files())

            pattern = _re_b.compile(rf"^E\d+_IND_{mes}[-_]{anio}_Base Notas .+$")
            files = []
            for name, fid in all_files.items():
                if pattern.match(name):
                    parsed = _re_b.match(rf"(E\d+)_(IND)_(\d{{2}})[-_](\d{{4}})_(.*)", name)
                    if parsed:
                        files.append({
                            "id": fid, "name": name,
                            "code": parsed.group(1), "tipo": "IND",
                            "mm": parsed.group(3), "yyyy": parsed.group(4),
                            "suffix": parsed.group(5),
                        })
            files.sort(key=lambda x: x["code"])
            self._cmp_files    = files
            self._cmp_allfiles = all_files
            self.after(0, lambda: self._cmp_render_files(files))
            self._cmp_log_write(f"  {len(files)} archivo(s) encontrado(s).", "ok" if files else "err")
            if files:
                self.after(0, lambda: self._cmp_btn_procesar.configure(state="normal"))
        except Exception as e:
            self._cmp_log_write(f"ERROR: {e}", "err")
        finally:
            self.after(0, lambda: self._cmp_btn_buscar.configure(state="normal"))
            self.after(0, self._progress.stop)

    def _cmp_on_procesar(self):
        seleccionados = [f for f, v in zip(self._cmp_files, self._cmp_vars) if v.get()]
        if not seleccionados:
            messagebox.showwarning("Aviso", "Selecciona al menos un archivo.")
            return
        nombres = "\n".join(f"  • {t.get('name', t.get('code',''))}" for t in seleccionados)
        confirmado = messagebox.askyesno(
            "Confirmar procesamiento",
            f"Esto va a ESCRIBIR datos directamente en Workiva para "
            f"{len(seleccionados)} archivo(s):\n\n{nombres}\n\n"
            "Esta acción no se puede deshacer automáticamente. "
            "¿Confirmas que quieres continuar?",
            icon="warning",
        )
        if not confirmado:
            return
        self._cmp_stop_flag = False
        self._cmp_btn_detener.pack(side="right", padx=(0, 4))
        self._cmp_btn_buscar.configure(state="disabled")
        self._cmp_btn_procesar.configure(state="disabled")
        self._progress.configure(mode="indeterminate")
        self._progress.start(10)
        self._cmp_log_write(f"\nProcesando {len(seleccionados)} archivo(s)...", "blue")
        threading.Thread(target=self._cmp_thread_procesar,
                         args=(seleccionados,), daemon=True).start()

    def _cmp_set_label(self, label):
        # Solo actualiza el texto del subtitulo — la barra de progreso queda
        # en modo indeterminado (animandose) durante todo el proceso, ya que
        # el llenado real no reporta avance por hoja de forma confiable
        # (puede tardar 15-20 min sin ninguna señal intermedia).
        self.after(0, lambda: self._header_subtitle.configure(text=label))

    def _cmp_thread_procesar(self, seleccionados):
        try:
            import builtins, types
            _orig_print = builtins.print

            def _gui_print(*args, **kwargs):
                msg = " ".join(str(a) for a in args)
                tag = "err" if "ERR" in msg or "✗" in msg else \
                      "ok"  if "OK" in msg or "✓" in msg else \
                      "bold" if msg.startswith("===") or msg.startswith("───") else None
                self._cmp_log_write(msg, tag)

            builtins.print = _gui_print
            t0 = time.time()
            try:
                import asyncio as _aio, os as _os3
                _os3.environ["WORKIVA_CLIENT_ID"]     = CLIENT_ID
                _os3.environ["WORKIVA_CLIENT_SECRET"] = CLIENT_SECRET
                _os3.environ["WORKIVA_WORKSPACE_ID"]  = WORKSPACE_ID
                tmpdir_p  = self._get_mcp_tmpdir()
                mcp_mod   = self._load_mcp_v2_mod(tmpdir_p)

                llenar_mod = types.ModuleType("llenar_v2")
                llenar_mod.__file__ = str(tmpdir_p / "llenado_comparativosV2_espejo.py")
                exec(compile(_LLENAR_V2_SRC, str(tmpdir_p / "llenado_comparativosV2_espejo.py"), "exec"), llenar_mod.__dict__)
                llenar_mod._load_mcp = lambda: mcp_mod

                total_ok = total_err = 0
                resultados = []
                detenido = False
                for t in seleccionados:
                    if self._cmp_stop_flag:
                        self._cmp_log_write(
                            "\n⏹ Proceso detenido por el usuario — "
                            "los archivos restantes no se procesaron.", "warn")
                        detenido = True
                        break
                    code = t.get("code", t["name"])
                    fid  = t["id"]
                    self._cmp_set_label(f"{code}  —  escribiendo en Workiva... (puede tardar varios minutos)")

                    t_file = time.time()
                    try:
                        mcp_mod._wk._client = None
                        resultado = _aio.run(llenar_mod._procesar_archivo(
                            mcp_mod, fid, t["name"], False, 50,
                            should_stop=lambda: self._cmp_stop_flag))
                        ok      = resultado.get("columnas", 0)
                        err     = 1 if resultado.get("estado") in ("error","incompleto") else 0
                        detalle = resultado.get("detalle", "")
                        if resultado.get("estado") == "detenido":
                            detenido = True
                    except Exception as e_proc:
                        self._cmp_log_write(f"  ERROR {code}: {e_proc}", "err")
                        ok, err, detalle = 0, 1, str(e_proc)
                    elapsed_file = time.time() - t_file
                    mf, sf = divmod(int(elapsed_file), 60)
                    dur_file = f"{mf}m {sf}s" if mf else f"{sf}s"

                    total_ok  += ok
                    total_err += err
                    resultados.append({
                        "name": t["name"], "code": code,
                        "ok": ok, "err": err, "dur": dur_file,
                        "detalle": detalle,
                    })
                    self._cmp_set_label(f"{code}  —  listo ({dur_file})")

                elapsed    = time.time() - t0
                mins, secs = divmod(int(elapsed), 60)
                dur_str    = f"{mins}m {secs}s" if mins else f"{secs}s"
                prefijo    = "DETENIDO — " if detenido else ""
                self._cmp_log_write(
                    f"\n{prefijo}RESUMEN: OK={total_ok}  ERR={total_err}  ({dur_str})",
                    "warn" if (detenido or total_err) else "ok")
                self._cmp_set_label("Llenar Comparativos")
                self.after(0, self._avisar_fin)
                self.after(0, lambda r=resultados, tok=total_ok, terr=total_err, d=dur_str:
                           self._cmp_show_result_popup(r, tok, terr, d))
            finally:
                builtins.print = _orig_print
        except Exception as e:
            self._cmp_log_write(f"ERROR inesperado: {e}", "err")
        finally:
            self.after(0, self._progress.stop)
            self.after(0, self._cmp_btn_detener.pack_forget)
            self.after(0, lambda: self._cmp_btn_buscar.configure(state="normal"))
            self.after(0, lambda: self._cmp_btn_procesar.configure(state="normal"))
            self.after(0, lambda: self._header_subtitle.configure(text="Llenar Comparativos"))


    def _get_mcp_tmpdir(self):
        """Escribe workiva_mcp_v2.py en un dir temporal y retorna su Path."""
        import tempfile, pathlib
        if not hasattr(self, "_mcp_tmpdir"):
            d = pathlib.Path(tempfile.mkdtemp(prefix="auditor_mcp_"))
            (d / "workiva_mcp_v2.py").write_text(_MCP_V2_SRC, encoding="utf-8")
            (d / ".env").write_text(
                f"WORKIVA_CLIENT_ID={CLIENT_ID}\n"
                f"WORKIVA_CLIENT_SECRET={CLIENT_SECRET}\n"
                f"WORKIVA_WORKSPACE_ID={WORKSPACE_ID}\n",
                encoding="utf-8"
            )
            self._mcp_tmpdir = d
        return self._mcp_tmpdir

    def _load_mcp_v2_mod(self, tmpdir):
        """Carga workiva_mcp_v2 desde tmpdir (cacheado en self._mcp_v2_mod)."""
        import importlib.util, sys, os, pathlib
        if not hasattr(self, "_mcp_v2_mod"):
            os.environ["WORKIVA_CLIENT_ID"]     = CLIENT_ID
            os.environ["WORKIVA_CLIENT_SECRET"] = CLIENT_SECRET
            os.environ["WORKIVA_WORKSPACE_ID"]  = WORKSPACE_ID
            mcp_path = pathlib.Path(tmpdir) / "workiva_mcp_v2.py"
            spec = importlib.util.spec_from_file_location("workiva_mcp_v2", mcp_path)
            mod  = importlib.util.module_from_spec(spec)
            sys.modules["workiva_mcp_v2"] = mod
            spec.loader.exec_module(mod)
            self._mcp_v2_mod = mod
        return self._mcp_v2_mod

    # ── CRUCE DE NOTAS ────────────────────────────────────────────────────────
    def _build_view_cruce_notas(self):
        frame = tk.Frame(self._content, bg=CGE_LIGHT)
        self._views["mod3"] = frame

        # Encabezado + botón limpiar
        top = tk.Frame(frame, bg=CGE_LIGHT)
        top.pack(fill="x", pady=(0, 8))
        tk.Label(top, text="Cruce de Notas", font=("Segoe UI", 13, "bold"),
                 bg=CGE_LIGHT, fg=CGE_BLUE).pack(side="left")
        tk.Button(top, text="Limpiar", font=FONT_SMALL,
                  bg=CGE_RED, fg=CGE_WHITE, relief="flat", bd=0,
                  padx=10, pady=4, cursor="hand2",
                  command=self._cruce_limpiar).pack(side="right")

        # Área de texto libre con scroll
        txt_frame = tk.Frame(frame, bg=CGE_BORDER, bd=1, relief="flat")
        txt_frame.pack(fill="both", expand=True)

        self._cruce_text = tk.Text(
            txt_frame,
            font=("Consolas", 11),
            bg=CGE_CARD, fg=CGE_TEXT,
            insertbackground=CGE_BLUE,
            relief="flat", bd=0,
            wrap="none",
            undo=True,
            padx=10, pady=8,
        )
        vsb = ttk.Scrollbar(txt_frame, orient="vertical",
                             command=self._cruce_text.yview)
        hsb = ttk.Scrollbar(txt_frame, orient="horizontal",
                             command=self._cruce_text.xview)
        self._cruce_text.configure(yscrollcommand=vsb.set,
                                   xscrollcommand=hsb.set)
        vsb.pack(side="right", fill="y")
        hsb.pack(side="bottom", fill="x")
        self._cruce_text.pack(fill="both", expand=True)

    def _cruce_limpiar(self):
        if messagebox.askyesno("Confirmar", "¿Limpiar el texto?"):
            self._cruce_text.delete("1.0", "end")


    # ── Módulo 5: Flujo de Efectivo ──────────────────────────────────────────

    def _build_view_flujo_efectivo(self):
        frame = tk.Frame(self._content, bg=CGE_LIGHT)
        self._views["mod5"] = frame

        body = tk.Frame(frame, bg=CGE_LIGHT)
        body.pack(fill="both", expand=True)

        # Panel izquierdo ─────────────────────────────────────────────────────
        left = tk.Frame(body, bg=CGE_LIGHT, width=230)
        left.pack(side="left", fill="y", padx=(0, 14))
        left.pack_propagate(False)

        # Contraseña hardcodeada — no se expone en UI
        self._flujo_pwd = tk.StringVar(value=os.environ.get("EFLUJO_PWD", "uscefect2014"))

        # Período
        tk.Label(left, text="PERÍODO", font=("Segoe UI", 8, "bold"),
                 bg=CGE_LIGHT, fg=CGE_MUTED).pack(anchor="w", pady=(4, 2))
        pf = tk.Frame(left, bg=CGE_CARD, highlightbackground=CGE_BORDER, highlightthickness=1)
        pf.pack(fill="x", pady=(0, 10))
        pi = tk.Frame(pf, bg=CGE_CARD, padx=12, pady=10)
        pi.pack(fill="x")

        tk.Label(pi, text="Mes", font=FONT_SMALL, bg=CGE_CARD, fg=CGE_MUTED).grid(
            row=0, column=0, sticky="w", pady=4)
        self._flujo_mes = tk.StringVar()
        _e_flujo_mes = tk.Entry(pi, textvariable=self._flujo_mes, font=FONT_LABEL,
                 bg=CGE_LIGHT, fg=CGE_TEXT, relief="flat", bd=4, width=12,
                 highlightbackground=CGE_BORDER, highlightthickness=1)
        _e_flujo_mes.grid(row=0, column=1, sticky="ew", padx=(8,0), pady=4)
        _e_flujo_mes.bind("<Return>", lambda e: self._flujo_on_buscar())

        tk.Label(pi, text="Año", font=FONT_SMALL, bg=CGE_CARD, fg=CGE_MUTED).grid(
            row=1, column=0, sticky="w", pady=4)
        self._flujo_anio = tk.StringVar()
        _e_flujo_anio = tk.Entry(pi, textvariable=self._flujo_anio, font=FONT_LABEL,
                 bg=CGE_LIGHT, fg=CGE_TEXT, relief="flat", bd=4, width=12,
                 highlightbackground=CGE_BORDER, highlightthickness=1)
        _e_flujo_anio.grid(row=1, column=1, sticky="ew", padx=(8,0), pady=4)
        _e_flujo_anio.bind("<Return>", lambda e: self._flujo_on_buscar())
        pi.columnconfigure(1, weight=1)

        # Carpeta salida
        tk.Label(left, text="CARPETA DE SALIDA", font=("Segoe UI", 8, "bold"),
                 bg=CGE_LIGHT, fg=CGE_MUTED).pack(anchor="w", pady=(4, 2))
        sf = tk.Frame(left, bg=CGE_CARD, highlightbackground=CGE_BORDER, highlightthickness=1)
        sf.pack(fill="x", pady=(0, 10))
        si = tk.Frame(sf, bg=CGE_CARD, padx=12, pady=10)
        si.pack(fill="x")
        self._flujo_carpeta = tk.StringVar(value=str(Path.home() / "Desktop"))
        tk.Entry(si, textvariable=self._flujo_carpeta, font=("Segoe UI", 8),
                 bg=CGE_LIGHT, fg=CGE_TEXT, relief="flat", bd=4,
                 highlightbackground=CGE_BORDER, highlightthickness=1
                 ).pack(fill="x", pady=(0,4))
        tk.Button(si, text="Examinar...", font=FONT_SMALL,
                  bg=CGE_BORDER, fg=CGE_TEXT, relief="flat", bd=0, padx=8, pady=3,
                  cursor="hand2",
                  command=self._flujo_examinar).pack(anchor="w")

        # Botones
        tk.Frame(left, bg=CGE_LIGHT, height=4).pack()
        self._flujo_btn_buscar = tk.Button(left, text="Buscar sociedades",
                  font=FONT_BOLD, bg=CGE_BLUE, fg=CGE_WHITE,
                  activebackground=CGE_BLUE2, activeforeground=CGE_WHITE,
                  relief="flat", bd=0, padx=10, pady=9,
                  cursor="hand2", command=self._flujo_on_buscar)
        self._flujo_btn_buscar.pack(fill="x")
        self._flujo_btn_buscar.bind("<Return>", lambda e: self._flujo_on_buscar())
        tk.Frame(left, bg=CGE_LIGHT, height=6).pack()
        self._flujo_btn_generar = tk.Button(left, text="Generar Excel",
                  font=FONT_BOLD, bg=CGE_GREEN, fg=CGE_WHITE, disabledforeground="#E4E9F5",
                  activebackground="#076b45", activeforeground=CGE_WHITE,
                  relief="flat", bd=0, padx=10, pady=9,
                  cursor="hand2", command=self._flujo_on_generar, state="disabled")
        self._flujo_btn_generar.pack(fill="x")
        self._flujo_btn_generar.bind("<Return>", lambda e: self._flujo_on_generar())

        # Panel derecho ───────────────────────────────────────────────────────
        right = tk.Frame(body, bg=CGE_LIGHT)
        right.pack(side="left", fill="both", expand=True)

        # Sociedades encontradas — header con botones marcar/desmarcar
        soc_hdr = tk.Frame(right, bg=CGE_LIGHT)
        soc_hdr.pack(fill="x", pady=(0, 4))
        tk.Label(soc_hdr, text="SOCIEDADES ENCONTRADAS", font=("Segoe UI", 8, "bold"),
                 bg=CGE_LIGHT, fg=CGE_MUTED).pack(side="left")
        tk.Button(soc_hdr, text="Desmarcar todas", font=FONT_SMALL,
                  bg=CGE_BORDER, fg=CGE_TEXT, relief="flat", bd=0,
                  padx=8, pady=2, cursor="hand2",
                  command=lambda: [v.set(False) for v in self._flujo_soc_vars]
                  ).pack(side="right", padx=(4,0))
        tk.Button(soc_hdr, text="Marcar todas", font=FONT_SMALL,
                  bg=CGE_BLUE, fg=CGE_WHITE, relief="flat", bd=0,
                  padx=8, pady=2, cursor="hand2",
                  command=lambda: [v.set(True) for v in self._flujo_soc_vars]
                  ).pack(side="right")
        self._flujo_sel_count_lbl = tk.Label(soc_hdr, text="", font=FONT_SMALL,
                                             bg=CGE_LIGHT, fg=CGE_MUTED)
        self._flujo_sel_count_lbl.pack(side="right", padx=(0, 8))

        soc_box = tk.Frame(right, bg=CGE_CARD,
                           highlightbackground=CGE_BORDER, highlightthickness=1)
        soc_box.pack(fill="x", pady=(0, 12))
        self._flujo_soc_canvas = tk.Canvas(soc_box, bg=CGE_CARD,
                                           highlightthickness=0, height=160)
        sb2 = tk.Scrollbar(soc_box, orient="vertical",
                           command=self._flujo_soc_canvas.yview)
        self._flujo_soc_canvas.configure(yscrollcommand=sb2.set)
        sb2.pack(side="right", fill="y")
        self._flujo_soc_canvas.pack(side="left", fill="both", expand=True)
        self._flujo_soc_inner = tk.Frame(self._flujo_soc_canvas, bg=CGE_CARD)
        soc_win = self._flujo_soc_canvas.create_window(
            (0,0), window=self._flujo_soc_inner, anchor="nw")
        self._flujo_soc_inner.bind("<Configure>", lambda e:
            self._flujo_soc_canvas.configure(
                scrollregion=self._flujo_soc_canvas.bbox("all")))
        self._flujo_soc_canvas.bind("<Configure>", lambda e:
            self._flujo_soc_canvas.itemconfig(soc_win, width=e.width))
        # MouseWheel scroll
        def _flujo_scroll(e):
            self._flujo_soc_canvas.yview_scroll(int(-1*(e.delta/120)), "units")
        self._flujo_soc_canvas.bind("<MouseWheel>", _flujo_scroll)
        self._flujo_soc_inner.bind("<MouseWheel>", _flujo_scroll)
        self._flujo_socs      = []
        self._flujo_soc_vars  = []
        self._flujo_lbl_empty = tk.Label(self._flujo_soc_inner,
            text="Ingresa el periodo y presiona 'Buscar sociedades'",
            font=FONT_SMALL, bg=CGE_CARD, fg=CGE_MUTED, pady=20)
        self._flujo_lbl_empty.pack()

        # Log
        act_hdr = tk.Frame(right, bg=CGE_LIGHT)
        act_hdr.pack(fill="x", pady=(0, 4))
        tk.Label(act_hdr, text="ACTIVIDAD", font=("Segoe UI", 8, "bold"),
                 bg=CGE_LIGHT, fg=CGE_MUTED).pack(side="left")
        tk.Button(act_hdr, text="Limpiar", font=FONT_SMALL,
                  bg=CGE_BORDER, fg=CGE_TEXT, relief="flat", bd=0,
                  padx=8, pady=2, cursor="hand2",
                  command=lambda: self._flujo_log_clear()).pack(side="right")
        log_box = tk.Frame(right, bg=CGE_CARD,
                           highlightbackground=CGE_BORDER, highlightthickness=1)
        log_box.pack(fill="both", expand=True)
        self._flujo_log = scrolledtext.ScrolledText(
            log_box, font=FONT_MONO, bg=CGE_CARD, fg=CGE_TEXT,
            relief="flat", bd=8, state="disabled", wrap="word", height=8)
        self._flujo_log.pack(fill="both", expand=True)
        self._flujo_log.tag_config("ok",   foreground=CGE_GREEN)
        self._flujo_log.tag_config("err",  foreground=CGE_RED)
        self._flujo_log.tag_config("warn", foreground=CGE_YELLOW)
        self._flujo_log.tag_config("bold", font=("Consolas", 9, "bold"))

    # ── Flujo helpers ─────────────────────────────────────────────────────────

    def _flujo_log_write(self, msg, tag=None):
        def _do():
            self._flujo_log.configure(state="normal")
            self._flujo_log.insert("end", msg + "\n", tag or "")
            self._flujo_log.see("end")
            self._flujo_log.configure(state="disabled")
        self.after(0, _do)

    def _flujo_log_clear(self):
        self._flujo_log.configure(state="normal")
        self._flujo_log.delete("1.0", "end")
        self._flujo_log.configure(state="disabled")

    def _flujo_examinar(self):
        from tkinter import filedialog
        carpeta = filedialog.askdirectory(title="Seleccionar carpeta de salida")
        if carpeta:
            self._flujo_carpeta.set(carpeta)

    def _flujo_on_buscar(self):
        mes  = self._flujo_mes.get().strip().zfill(2)
        anio = self._flujo_anio.get().strip()
        if not re.fullmatch(r"\d{2}", mes) or not re.fullmatch(r"\d{4}", anio):
            messagebox.showerror("Error", "Ingresa mes (01-12) y año válidos.")
            return
        self._flujo_log_clear()
        self._flujo_btn_buscar.configure(state="disabled")
        self._flujo_btn_generar.configure(state="disabled")
        self._progress.configure(mode="indeterminate")
        self._progress.start(10)
        threading.Thread(target=self._flujo_thread_buscar,
                         args=(mes, anio), daemon=True).start()

    def _flujo_thread_buscar(self, mes, anio):
        try:
            import types
            mod = types.ModuleType("flujo_ef")
            mod.__dict__["os"] = os
            exec(compile(_FLUJO_SRC, "genera_flujo_efectivo.py", "exec"), mod.__dict__)
            pwd = self._flujo_pwd.get().strip()
            mod.PASSWORD = pwd

            self._flujo_log_write("Conectando a SQL Server...")
            cn  = mod.conectar()
            cur = cn.cursor()
            self._flujo_log_write("Conectado. Buscando sociedades...", "ok")

            fecha_ini = f"01/{anio}"
            fecha_fin = f"{mes}/{anio}"
            oficiales    = mod.buscar_sociedades(cur, fecha_ini, fecha_fin)
            preliminares = mod.buscar_preliminares(cur, fecha_fin, set(oficiales))
            cn.close()

            self._flujo_mod      = mod
            self._flujo_oficiales    = oficiales
            self._flujo_preliminares = preliminares
            self._flujo_fecha_ini    = fecha_ini
            self._flujo_fecha_fin    = fecha_fin

            self._flujo_log_write(
                f"Con informe oficial ({len(oficiales)}): " +
                (", ".join(oficiales) if oficiales else "–"), "ok")
            self._flujo_log_write(
                f"Preliminares ({len(preliminares)}): " +
                (", ".join(preliminares) if preliminares else "–"),
                "warn" if preliminares else None)

            self.after(0, self._flujo_build_soc_list)
        except Exception as e:
            self._flujo_log_write(f"ERROR: {e}", "err")
        finally:
            self.after(0, lambda: self._flujo_btn_buscar.configure(state="normal"))
            self.after(0, self._progress.stop)

    def _flujo_build_soc_list(self):
        for w in self._flujo_soc_inner.winfo_children():
            w.destroy()
        self._flujo_socs     = []
        self._flujo_soc_vars = []

        def add_soc(emp, label, default=True):
            var = tk.BooleanVar(value=default)
            var.trace_add("write", lambda *a: self._flujo_update_sel_count())
            row = tk.Frame(self._flujo_soc_inner, bg=CGE_CARD)
            row.pack(fill="x", padx=8, pady=1)
            cb = tk.Checkbutton(row, variable=var, text=label,
                           font=FONT_LABEL, bg=CGE_CARD, fg=CGE_TEXT,
                           activebackground=CGE_CARD,
                           anchor="w", relief="flat")
            cb.pack(side="left")
            # propagar scroll al canvas
            cb.bind("<MouseWheel>", lambda e: self._flujo_soc_canvas.yview_scroll(
                int(-1*(e.delta/120)), "units"))
            row.bind("<MouseWheel>", lambda e: self._flujo_soc_canvas.yview_scroll(
                int(-1*(e.delta/120)), "units"))
            self._flujo_socs.append(emp)
            self._flujo_soc_vars.append(var)

        if self._flujo_oficiales:
            tk.Label(self._flujo_soc_inner, text="— Con informe oficial —",
                     font=("Segoe UI", 8, "bold"), bg=CGE_CARD,
                     fg=CGE_BLUE).pack(anchor="w", padx=8, pady=(6,2))
        for emp in self._flujo_oficiales:
            add_soc(emp, emp, default=True)

        if self._flujo_preliminares:
            tk.Label(self._flujo_soc_inner,
                     text="— Preliminar (desde movimientos) —",
                     font=("Segoe UI", 8, "bold"), bg=CGE_CARD,
                     fg=CGE_YELLOW).pack(anchor="w", padx=8, pady=(8,2))
        for emp in self._flujo_preliminares:
            add_soc(emp, f"{emp}  (*)", default=False)

        self._flujo_btn_generar.configure(
            state="normal" if (self._flujo_oficiales or self._flujo_preliminares)
            else "disabled")
        self._flujo_update_sel_count()

    def _flujo_update_sel_count(self):
        marcados = sum(1 for v in self._flujo_soc_vars if v.get())
        self._flujo_sel_count_lbl.configure(text=f"{marcados} de {len(self._flujo_soc_vars)} marcados")

    def _flujo_on_generar(self):
        seleccionados = [e for e, v in zip(self._flujo_socs, self._flujo_soc_vars)
                         if v.get()]
        if not seleccionados:
            messagebox.showwarning("Aviso", "Selecciona al menos una sociedad.")
            return
        self._flujo_btn_buscar.configure(state="disabled")
        self._flujo_btn_generar.configure(state="disabled")
        self._progress.configure(mode="indeterminate")
        self._progress.start(10)
        threading.Thread(target=self._flujo_thread_generar,
                         args=(seleccionados,), daemon=True).start()

    def _flujo_thread_generar(self, seleccionados):
        try:
            import types
            from openpyxl import Workbook
            mod = self._flujo_mod
            fecha_ini   = self._flujo_fecha_ini
            fecha_fin   = self._flujo_fecha_fin
            oficiales   = set(self._flujo_oficiales)
            preliminares_sel = [e for e in seleccionados if e not in oficiales]

            self._flujo_log_write(
                f"Generando flujo para: {', '.join(seleccionados)}", "bold")

            pwd = self._flujo_pwd.get().strip()
            mod.PASSWORD = pwd
            cn  = mod.conectar()
            cur = cn.cursor()

            nombres = mod.extraer_nombres_lineas(cur, list(oficiales & set(seleccionados)),
                                                 fecha_ini, fecha_fin)
            self._flujo_log_write(f"Líneas de flujo identificadas: {len(nombres)}")

            lineas_emp, subt_emp, detalle = {}, {}, []
            for emp in seleccionados:
                det = mod.extraer_detalle(cur, emp, nombres, fecha_ini, fecha_fin)
                detalle.extend(det)
                if emp in oficiales:
                    lineas_emp[emp], subt_emp[emp] = mod.extraer_informe(
                        cur, emp, fecha_ini, fecha_fin)
                    origen = "oficial"
                else:
                    lineas_emp[emp], subt_emp[emp] = mod.flujo_preliminar(det)
                    origen = "PRELIMINAR"
                self._flujo_log_write(
                    f"  {emp}: {len(lineas_emp[emp])} líneas ({origen})",
                    "warn" if origen == "PRELIMINAR" else "ok")
            cn.close()

            carpeta = self._flujo_carpeta.get().strip()
            mm, aa = fecha_fin.split("/")
            nombre_xlsx = f"Flujo_Efectivo_{mm}-{aa}.xlsx"
            salida = os.path.join(carpeta, nombre_xlsx)

            wb = Workbook()
            mod.hoja_consolidado(wb, seleccionados, lineas_emp, subt_emp,
                                 nombres, fecha_ini, fecha_fin, preliminares_sel)
            ultima = mod.hoja_detalle(wb, detalle, fecha_ini, fecha_fin)
            wb.save(salida)
            self._flujo_log_write(f"Guardado: {salida}", "ok")

            mod.tabla_dinamica(salida, ultima, fecha_ini, fecha_fin)
            self._flujo_log_write("Listo.", "ok")

            self.after(0, lambda s=salida: self._abrir_si_confirma(
                "Flujo generado", f"Archivo generado correctamente:\n\n{s}", s))
        except Exception as e:
            self._flujo_log_write(f"ERROR: {e}", "err")
            self.after(0, lambda err=str(e): messagebox.showerror("Error", err))
        finally:
            self.after(0, self._avisar_fin)
            self.after(0, lambda: self._flujo_btn_buscar.configure(state="normal"))
            self.after(0, lambda: self._flujo_btn_generar.configure(state="normal"))
            self.after(0, self._progress.stop)

    # ── Módulo 4: Extraer EEFF ────────────────────────────────────────────────

    def _build_view_extraer_eeff(self):
        frame = tk.Frame(self._content, bg=CGE_LIGHT)
        self._views["mod4"] = frame

        body = tk.Frame(frame, bg=CGE_LIGHT)
        body.pack(fill="both", expand=True)

        # Panel izquierdo
        left = tk.Frame(body, bg=CGE_LIGHT, width=230)
        left.pack(side="left", fill="y", padx=(0, 14))
        left.pack_propagate(False)

        # ── Sociedad (solo informativo) ───────────────────────────────────────
        tk.Label(left, text="SPREADSHEET", font=("Segoe UI", 8, "bold"),
                 bg=CGE_LIGHT, fg=CGE_MUTED).pack(anchor="w", pady=(6, 2))
        sf = tk.Frame(left, bg=CGE_CARD,
                      highlightbackground=CGE_BORDER, highlightthickness=1)
        sf.pack(fill="x", pady=(0, 10))
        self._eeff_ss_name = tk.StringVar(value="E200_CONSO_12-2025")
        tk.Entry(sf, textvariable=self._eeff_ss_name, font=FONT_BOLD,
                 bg=CGE_CARD, fg=CGE_BLUE, relief="flat", bd=0,
                 insertbackground=CGE_BLUE,
                 highlightbackground=CGE_BORDER, highlightthickness=0
                 ).pack(fill="x", padx=12, pady=10)

        # ── Hojas (checklist) ─────────────────────────────────────────────────
        tk.Label(left, text="HOJAS A EXTRAER", font=("Segoe UI", 8, "bold"),
                 bg=CGE_LIGHT, fg=CGE_MUTED).pack(anchor="w", pady=(4, 2))
        hf = tk.Frame(left, bg=CGE_CARD,
                      highlightbackground=CGE_BORDER, highlightthickness=1)
        hf.pack(fill="x", pady=(0, 10))
        h_inner = tk.Frame(hf, bg=CGE_CARD, padx=12, pady=10)
        h_inner.pack(fill="x")

        hojas = [
            ("A  —  Activos",          "_eeff_chk_a"),
            ("B  —  Pasivos/Pat.",      "_eeff_chk_b"),
            ("C  —  Est. Resultados",   "_eeff_chk_c"),
            ("D  —  Res. Integral",     "_eeff_chk_d"),
            ("F  —  Flujo Efectivo",    "_eeff_chk_f"),
        ]
        for label, attr in hojas:
            var = tk.BooleanVar(value=True)
            setattr(self, attr, var)
            tk.Checkbutton(h_inner, text=label, variable=var,
                           font=FONT_SMALL, bg=CGE_CARD, fg=CGE_TEXT,
                           selectcolor=CGE_LIGHT, activebackground=CGE_CARD,
                           anchor="w", cursor="hand2").pack(fill="x", pady=2)

        tk.Frame(left, bg=CGE_LIGHT, height=6).pack()
        self._eeff_btn = tk.Button(left, text="Extraer EEFF",
                  font=FONT_BOLD, bg=CGE_BLUE, fg=CGE_WHITE,
                  activebackground=CGE_BLUE2, activeforeground=CGE_WHITE,
                  relief="flat", bd=0, padx=10, pady=9,
                  cursor="hand2", command=self._eeff_on_extraer)
        self._eeff_btn.pack(fill="x")
        self._eeff_btn_stop = tk.Button(left, text="Detener",
                  font=FONT_BOLD, bg=CGE_RED, fg=CGE_WHITE,
                  relief="flat", bd=0, padx=10, pady=9,
                  cursor="hand2", command=self._eeff_on_stop)
        # oculto hasta que corra
        self._eeff_running = False

        # Panel derecho: log
        right = tk.Frame(body, bg=CGE_LIGHT)
        right.pack(side="left", fill="both", expand=True)

        act_hdr = tk.Frame(right, bg=CGE_LIGHT)
        act_hdr.pack(fill="x", pady=(0, 4))
        tk.Label(act_hdr, text="RESULTADO", font=("Segoe UI", 8, "bold"),
                 bg=CGE_LIGHT, fg=CGE_MUTED).pack(side="left")
        tk.Button(act_hdr, text="Limpiar", font=FONT_SMALL,
                  bg=CGE_BORDER, fg=CGE_TEXT, relief="flat", bd=0,
                  padx=8, pady=2, cursor="hand2",
                  command=self._eeff_clear_log).pack(side="right")

        log_box = tk.Frame(right, bg=CGE_CARD,
                           highlightbackground=CGE_BORDER, highlightthickness=1)
        log_box.pack(fill="both", expand=True)
        self._eeff_log = scrolledtext.ScrolledText(
            log_box, font=FONT_MONO, bg=CGE_CARD, fg=CGE_TEXT,
            relief="flat", bd=8, state="disabled", wrap="word")
        self._eeff_log.pack(fill="both", expand=True)
        self._eeff_log.tag_config("ok",   foreground=CGE_GREEN)
        self._eeff_log.tag_config("err",  foreground=CGE_RED)
        self._eeff_log.tag_config("warn", foreground=CGE_YELLOW)
        self._eeff_log.tag_config("blue", foreground=CGE_BLUE)
        self._eeff_log.tag_config("bold", font=("Consolas", 9, "bold"))
        self._eeff_log.tag_config("muted",foreground=CGE_MUTED)

    def _eeff_log_write(self, msg, tag=None):
        def _do():
            self._eeff_log.configure(state="normal")
            self._eeff_log.insert("end", msg + "\n", tag or "")
            self._eeff_log.see("end")
            self._eeff_log.configure(state="disabled")
        self.after(0, _do)

    def _eeff_clear_log(self):
        self._eeff_log.configure(state="normal")
        self._eeff_log.delete("1.0", "end")
        self._eeff_log.configure(state="disabled")

    def _eeff_on_stop(self):
        self._eeff_running = False

    def _eeff_on_extraer(self):
        ss_name = self._eeff_ss_name.get().strip()
        if not ss_name:
            messagebox.showerror("Error", "Ingresa el nombre del spreadsheet.")
            return
        self._eeff_clear_log()
        self._eeff_running = True
        self._eeff_btn.pack_forget()
        self._eeff_btn_stop.pack(fill="x")
        self._eeff_log_write(f"Buscando spreadsheet '{ss_name}' en Workiva...", "blue")
        threading.Thread(target=self._eeff_thread,
                         args=(ss_name, 5, 7), daemon=True).start()

    def _eeff_thread(self, ss_name, col_act, col_cmp):
        import builtins
        _orig_print = builtins.print
        def _gui_print(*args, **kwargs):
            if not self._eeff_running:
                return
            msg = " ".join(str(a) for a in args)
            tag = "err"  if ("ERROR" in msg or "✗" in msg) else \
                  "ok"   if ("OK" in msg or "✓" in msg) else \
                  "bold" if (msg.startswith("===") or msg.startswith("───")) else \
                  "muted" if msg.startswith("  ") else None
            self._eeff_log_write(msg, tag)
        builtins.print = _gui_print
        try:
            import requests as _req, warnings as _w
            from urllib3.exceptions import InsecureRequestWarning as _IW
            _w.filterwarnings("ignore", category=_IW)

            s = _req.Session()
            resp = s.post(TOKEN_URL, data={
                "grant_type": "client_credentials",
                "client_id": CLIENT_ID,
                "client_secret": CLIENT_SECRET,
            }, verify=False, timeout=30)
            token = resp.json()["access_token"]
            s.headers.update({"Authorization": f"Bearer {token}",
                               "X-Version": "2022-01-01"})

            # Buscar el spreadsheet: coincidencia parcial con tokens E200, CONSO, 12, 2025
            tokens = [t.lower() for t in ss_name.replace("-", "_").split("_") if t]
            ss_id = None
            ss_found_name = None
            url = f"{WDESK_BASE}/platform/v1/spreadsheets?workspaceId={WORKSPACE_ID}&limit=100"
            while url and not ss_id:
                r    = s.get(url, verify=False, timeout=60)
                data = r.json()
                for item in data.get("data", []):
                    name   = item.get("name", "")
                    name_l = name.lower()
                    if all(t in name_l for t in tokens) and name_l.startswith(tokens[0]):
                        ss_id = item["id"]
                        ss_found_name = name
                        break
                url = data.get("@nextLink")
            if not ss_id:
                self._eeff_log_write(f"✗ No se encontró ningún spreadsheet que contenga: {', '.join(tokens)}", "err")
                return
            self._eeff_log_write(f"✓ Encontrado: {ss_found_name}", "ok")

            def _get_sheets(sid):
                url = f"{WDESK_BASE}/platform/v1/spreadsheets/{sid}/sheets"
                r = s.get(url, verify=False, timeout=60)
                return {sh["name"]: sh["id"] for sh in r.json().get("data", [])}

            def _read_cells(sid, sheet_id):
                url = (f"{WDESK_BASE}/platform/v1/spreadsheets/{sid}/sheets/{sheet_id}"
                       "/sheetdata?$fields=cells.calculatedValue&$maxcellsperpage=50000")
                r = s.get(url, verify=False, timeout=120)
                return r.json().get("data", {}).get("cells", [])

            def _cell(cells, row0, col0):
                try:
                    v = cells[row0][col0]
                    raw = v.get("calculatedValue") if isinstance(v, dict) else None
                    if raw is None or raw == "":
                        return None
                    return float(str(raw).replace(",", "").replace(" ", ""))
                except (IndexError, TypeError, ValueError):
                    return None

            def _find_sheet(sheets, *kws):
                for name, sid in sheets.items():
                    if all(k.lower() in name.lower() for k in kws):
                        return sid
                return None

            def _neg(v):
                return abs(v) if v is not None else None

            # Leer keywords de hojas desde la GUI
            do_a = self._eeff_chk_a.get()
            do_b = self._eeff_chk_b.get()
            do_c = self._eeff_chk_c.get()
            do_d = self._eeff_chk_d.get()
            do_f = self._eeff_chk_f.get()

            def _extraer(col_v):
                if not self._eeff_running:
                    return {}
                sheets = _get_sheets(ss_id)
                if not sheets:
                    self._eeff_log_write("ERROR: no se obtuvieron hojas.", "err")
                    return {}

                sid_a = _find_sheet(sheets, "a.-") if do_a else None
                a = _read_cells(ss_id, sid_a) if sid_a else []
                esf = {
                    "efectivo_equivalentes": _cell(a,  8, col_v),
                    "cuentas_por_cobrar":    _cell(a, 11, col_v),
                    "inventarios":           _cell(a, 13, col_v),
                    "activo_corriente":      _cell(a, 21, col_v),
                    "ppe_neto":              _cell(a, 33, col_v),
                    "activos_ddu":           _cell(a, 36, col_v),
                    "activo_imp_diferido":   _cell(a, 38, col_v),
                    "activo_no_corriente":   _cell(a, 40, col_v),
                    "activo_total":          _cell(a, 42, col_v),
                }
                if not self._eeff_running:
                    return {}

                sid_b = _find_sheet(sheets, "b.-") if do_b else None
                b = _read_cells(ss_id, sid_b) if sid_b else []
                esf.update({
                    "deuda_financiera_corriente":        _cell(b,  8, col_v),
                    "pasivo_arrendamiento_corriente":    _cell(b,  9, col_v),
                    "cuentas_por_pagar":                 _cell(b, 10, col_v),
                    "pasivo_corriente":                  _cell(b, 21, col_v),
                    "deuda_financiera_no_corriente":     _cell(b, 25, col_v),
                    "pasivo_arrendamiento_no_corriente": _cell(b, 26, col_v),
                    "pasivo_imp_diferido":               _cell(b, 30, col_v),
                    "pasivo_no_corriente":               _cell(b, 35, col_v),
                    "pasivo_total":                      _cell(b, 37, col_v),
                    "patrimonio_total":                  _cell(b, 52, col_v),
                })
                if not self._eeff_running:
                    return {}

                sid_c = _find_sheet(sheets, "c.-") if do_c else None
                c = _read_cells(ss_id, sid_c) if sid_c else []
                ga = _cell(c, 14, col_v)
                gd = _cell(c, 15, col_v)
                go = _cell(c, 17, col_v)
                er = {
                    "ingresos":                  _cell(c,  7, col_v),
                    "costo_ventas":              _neg(_cell(c,  8, col_v)),
                    "ganancia_bruta":            _cell(c, 10, col_v),
                    "otros_ingresos_operacion":  _cell(c, 12, col_v),
                    "gastos_operacionales":      (-sum(x for x in [ga, gd, go] if x is not None)
                                                  if any(x is not None for x in [ga, gd, go]) else None),
                    "resultado_operacional":     _cell(c, 19, col_v),
                    "gastos_financieros":        _neg(_cell(c, 23, col_v)),
                    "ganancia_antes_impuesto":   _cell(c, 29, col_v),
                    "gasto_impuesto":            _cell(c, 31, col_v),
                    "ganancia_neta":             _cell(c, 37, col_v),
                }
                if not self._eeff_running:
                    return {}

                sid_d = _find_sheet(sheets, "d.-") if do_d else None
                d = _read_cells(ss_id, sid_d) if sid_d else []
                ori_nc = _cell(d, 18, col_v)
                ori_rc = _cell(d, 53, col_v)
                ori_total = ((ori_nc or 0) + (ori_rc or 0)
                             if (ori_nc is not None or ori_rc is not None) else None)
                er["ori"] = ori_total
                if er.get("ganancia_neta") is not None and ori_total is not None:
                    er["resultado_integral_total"] = er["ganancia_neta"] + ori_total
                if not self._eeff_running:
                    return {}

                sid_f = _find_sheet(sheets, "f.-") if do_f else None
                f = _read_cells(ss_id, sid_f) if sid_f else []
                efe = {
                    "flujo_operacional":       _cell(f, 35, col_v),
                    "flujo_inversion":         _cell(f, 65, col_v),
                    "flujo_financiamiento":    _cell(f, 91, col_v),
                    "efecto_tipo_cambio":      _cell(f, 95, col_v),
                    "variacion_neta_efectivo": _cell(f, 97, col_v),
                    "efectivo_inicio":         _cell(f, 99, col_v),
                    "efectivo_cierre":         _cell(f, 101, col_v),
                    "dividendos_pagados":      _neg(_cell(f, 84, col_v)),
                }
                return {"esf": esf, "er": er, "efe": efe}

            print("  Leyendo columna actual...")
            actual = _extraer(col_act)
            if not self._eeff_running:
                self._eeff_log_write("Detenido por usuario.", "warn")
                return
            print("  Leyendo columna comparativa...")
            comp = _extraer(col_cmp)
            if not self._eeff_running:
                self._eeff_log_write("Detenido por usuario.", "warn")
                return

            def _fmt(v):
                return f"{v:>25,.0f}"

            _LABELS = {
                "efectivo_equivalentes":             "Efectivo y equivalentes",
                "cuentas_por_cobrar":                "Cuentas por cobrar",
                "inventarios":                       "Inventarios",
                "activo_corriente":                  "Activo corriente",
                "ppe_neto":                          "PPE neto",
                "activos_ddu":                       "Activos por derecho de uso",
                "activo_imp_diferido":               "Activo por impuesto diferido",
                "activo_no_corriente":               "Activo no corriente",
                "activo_total":                      "Activo total",
                "deuda_financiera_corriente":        "Deuda financiera corriente",
                "pasivo_arrendamiento_corriente":    "Pasivo arrendamiento corriente",
                "cuentas_por_pagar":                 "Cuentas por pagar",
                "pasivo_corriente":                  "Pasivo corriente",
                "deuda_financiera_no_corriente":     "Deuda financiera no corriente",
                "pasivo_arrendamiento_no_corriente": "Pasivo arrendamiento no corriente",
                "pasivo_imp_diferido":               "Pasivo por impuesto diferido",
                "pasivo_no_corriente":               "Pasivo no corriente",
                "pasivo_total":                      "Pasivo total",
                "patrimonio_total":                  "Patrimonio total",
                "ingresos":                          "Ingresos",
                "costo_ventas":                      "Costo de ventas",
                "ganancia_bruta":                    "Ganancia bruta",
                "otros_ingresos_operacion":          "Otros ingresos de operación",
                "gastos_operacionales":              "Gastos operacionales",
                "resultado_operacional":             "Resultado operacional",
                "gastos_financieros":                "Gastos financieros",
                "ganancia_antes_impuesto":           "Ganancia antes de impuesto",
                "gasto_impuesto":                    "Gasto por impuesto",
                "ganancia_neta":                     "Ganancia neta",
                "ori":                               "Otro resultado integral",
                "resultado_integral_total":          "Resultado integral total",
                "flujo_operacional":                 "Flujo operacional",
                "flujo_inversion":                   "Flujo de inversión",
                "flujo_financiamiento":              "Flujo de financiamiento",
                "efecto_tipo_cambio":                "Efecto tipo de cambio",
                "variacion_neta_efectivo":           "Variación neta efectivo",
                "efectivo_inicio":                   "Efectivo inicio",
                "efectivo_cierre":                   "Efectivo cierre",
                "dividendos_pagados":                "Dividendos pagados",
            }
            def _lbl(k):
                return _LABELS.get(k, k.replace("_", " ").capitalize())

            if do_a or do_b:
                esf_a = actual.get("esf", {})
                esf_c = comp.get("esf", {})
                items = [(k, esf_a[k], esf_c.get(k))
                         for k in esf_a
                         if esf_a[k] is not None and esf_a[k] != 0]
                if items:
                    self._eeff_log_write("\n── A / B  ·  Estado de Situación Financiera ──────────", "bold")
                    self._eeff_log_write(f"  {'Campo':<42} {'Actual':>25}  {'Comparativo':>25}", "bold")
                    for k, va, vc in items:
                        vc_str = _fmt(vc) if (vc is not None and vc != 0) else f"{'—':>25}"
                        self._eeff_log_write(f"  {_lbl(k):<42} {_fmt(va)} {vc_str}", "muted")

            if do_c:
                items = [(k, actual.get("er", {}).get(k), comp.get("er", {}).get(k))
                         for k in actual.get("er", {})
                         if actual.get("er", {}).get(k) is not None and actual.get("er", {}).get(k) != 0]
                if items:
                    self._eeff_log_write("\n── C  ·  Estado de Resultados ────────────────────────", "bold")
                    self._eeff_log_write(f"  {'Campo':<42} {'Actual':>25}  {'Comparativo':>25}", "bold")
                    for k, va, vc in items:
                        vc_str = _fmt(vc) if (vc is not None and vc != 0) else f"{'—':>25}"
                        self._eeff_log_write(f"  {_lbl(k):<42} {_fmt(va)} {vc_str}", "muted")

            if do_d:
                er_a = actual.get("er", {})
                ori = er_a.get("ori")
                rit = er_a.get("resultado_integral_total")
                if ori is not None and ori != 0:
                    self._eeff_log_write("\n── D  ·  Resultado Integral ──────────────────────────", "bold")
                    self._eeff_log_write(f"  {_lbl('ori'):<42} {_fmt(ori)}", "muted")
                if rit is not None and rit != 0:
                    self._eeff_log_write(f"  {_lbl('resultado_integral_total'):<42} {_fmt(rit)}", "muted")

            if do_f:
                items = [(k, actual.get("efe", {}).get(k), comp.get("efe", {}).get(k))
                         for k in actual.get("efe", {})
                         if actual.get("efe", {}).get(k) is not None and actual.get("efe", {}).get(k) != 0]
                if items:
                    self._eeff_log_write("\n── F  ·  Flujo de Efectivo ───────────────────────────", "bold")
                    self._eeff_log_write(f"  {'Campo':<42} {'Actual':>25}  {'Comparativo':>25}", "bold")
                    for k, va, vc in items:
                        vc_str = _fmt(vc) if (vc is not None and vc != 0) else f"{'—':>25}"
                        self._eeff_log_write(f"  {_lbl(k):<42} {_fmt(va)} {vc_str}", "muted")

            self._eeff_log_write("\n✓ Extracción completada.", "ok")

        except Exception as e:
            self._eeff_log_write(f"ERROR: {e}", "err")
        finally:
            builtins.print = _orig_print
            self._eeff_running = False
            self.after(0, self._avisar_fin)
            def _restore():
                self._eeff_btn_stop.pack_forget()
                self._eeff_btn.pack(fill="x")
            self.after(0, _restore)

    def _build_view_placeholder(self, key, name):
        frame = tk.Frame(self._content, bg=CGE_LIGHT)
        tk.Label(frame, text=name, font=("Segoe UI", 16, "bold"),
                 bg=CGE_LIGHT, fg=CGE_BLUE).pack(pady=(60, 10))
        tk.Label(frame, text="En desarrollo", font=("Segoe UI", 11),
                 bg=CGE_LIGHT, fg=CGE_MUTED).pack()
        self._views[key] = frame

    def _build_header(self, container):
        hdr = tk.Frame(container, bg=CGE_BLUE, pady=0)
        hdr.pack(fill="both", expand=True)

        # Logo CGE
        logo_frame = tk.Frame(hdr, bg=CGE_BLUE, padx=18, pady=14)
        logo_frame.pack(side="left")

        try:
            from PIL import Image, ImageTk
            _logo_data = base64.b64decode(LOGO_B64)
            _img = Image.open(io.BytesIO(_logo_data))
            _img = _img.resize((90, 45), Image.LANCZOS)
            self._logo_img = ImageTk.PhotoImage(_img)
            tk.Label(logo_frame, image=self._logo_img, bg=CGE_BLUE).pack(side="left")
        except Exception:
            logo_box = tk.Frame(logo_frame, bg=CGE_WHITE, padx=8, pady=4)
            logo_box.pack(side="left")
            tk.Label(logo_box, text="CGE", font=("Segoe UI", 14, "bold"),
                     bg=CGE_WHITE, fg=CGE_BLUE).pack()

        tk.Frame(logo_frame, bg=CGE_BLUE, width=14).pack(side="left")

        title_frame = tk.Frame(logo_frame, bg=CGE_BLUE)
        title_frame.pack(side="left")
        title_row = tk.Frame(title_frame, bg=CGE_BLUE)
        title_row.pack(anchor="w")
        tk.Label(title_row, text="Auditor",
                 font=("Segoe UI", 15, "bold"),
                 bg=CGE_BLUE, fg=CGE_WHITE).pack(side="left")
        tk.Label(title_row, text=f"  ({AUDITOR_NAME})",
                 font=("Segoe UI", 9),
                 bg=CGE_BLUE, fg="#8aaaf5").pack(side="left", pady=(5, 0))
        self._header_subtitle = tk.Label(title_frame, text="",
                 font=("Segoe UI", 9),
                 bg=CGE_BLUE, fg="#8aaaf5")
        self._header_subtitle.pack(anchor="w")

        # Barra de progreso
        self._progress = ttk.Progressbar(hdr, mode="indeterminate", length=200)
        self._progress.pack(side="right", padx=18, pady=18)
        style = ttk.Style()
        style.theme_use("default")
        style.configure("TProgressbar", troughcolor=CGE_BLUE2,
                        background=CGE_WHITE, thickness=5)

    def _build_view_verif(self):
        frame = tk.Frame(self._content, bg=CGE_LIGHT)
        left = tk.Frame(frame, bg=CGE_LIGHT, width=230)
        left.pack(side="left", fill="y", padx=(0, 14))
        left.pack_propagate(False)
        right = tk.Frame(frame, bg=CGE_LIGHT)
        right.pack(side="left", fill="both", expand=True)
        self._build_controls(left)
        self._build_right(right)
        self._views["verif"] = frame

    def _build_controls(self, parent):
        # ── Card periodo ──
        self._card_title(parent, "Periodo")
        pf = tk.Frame(parent, bg=CGE_CARD,
                      highlightbackground=CGE_BORDER, highlightthickness=1)
        pf.pack(fill="x", pady=(0, 10))
        inner = tk.Frame(pf, bg=CGE_CARD, padx=12, pady=10)
        inner.pack(fill="x")

        self._v_mes  = self._field(inner, "Mes", 0)
        self._v_anio = self._field(inner, "Año", 1)

        # Idioma fijo — este módulo solo procesa documentos en español
        self._v_idioma = tk.StringVar(value="ESP")

        # ── Botones ──
        tk.Frame(parent, bg=CGE_LIGHT, height=4).pack()
        self._btn_buscar = self._make_btn(parent, "Buscar documentos",
                                          self._on_buscar, CGE_BLUE)
        tk.Frame(parent, bg=CGE_LIGHT, height=6).pack()
        self._btn_verificar = self._make_btn(parent, "Verificar seleccionados",
                                             self._on_verificar, CGE_GREEN)
        self._btn_verificar.configure(state="disabled")

    def _card_title(self, parent, text):
        tk.Label(parent, text=text.upper(), font=("Segoe UI", 8, "bold"),
                 bg=CGE_LIGHT, fg=CGE_MUTED).pack(anchor="w", pady=(6, 2))

    def _field(self, parent, label, row, default=""):
        tk.Label(parent, text=label, font=FONT_SMALL,
                 bg=CGE_CARD, fg=CGE_MUTED).grid(row=row, column=0,
                                                  sticky="w", pady=4)
        var = tk.StringVar(value=default)
        e = tk.Entry(parent, textvariable=var, font=FONT_LABEL,
                     bg=CGE_LIGHT, fg=CGE_TEXT, insertbackground=CGE_TEXT,
                     relief="flat", bd=4, width=12,
                     highlightbackground=CGE_BORDER, highlightthickness=1)
        e.grid(row=row, column=1, sticky="ew", padx=(8, 0), pady=4)
        parent.columnconfigure(1, weight=1)
        e.bind("<Return>", lambda ev: self._on_buscar())
        return var

    def _make_btn(self, parent, text, cmd, color):
        b = tk.Button(parent, text=text, font=FONT_BOLD,
                      bg=color, fg=CGE_WHITE, disabledforeground="#E4E9F5",
                      activebackground=CGE_BLUE2, activeforeground=CGE_WHITE,
                      relief="flat", bd=0, padx=10, pady=9,
                      cursor="hand2", command=cmd)
        b.pack(fill="x")
        return b

    def _build_right(self, parent):
        # ── Seccion documentos (arriba) ──
        doc_header = tk.Frame(parent, bg=CGE_LIGHT)
        doc_header.pack(fill="x", pady=(0, 4))
        tk.Label(doc_header, text="DOCUMENTOS ENCONTRADOS",
                 font=("Segoe UI", 8, "bold"),
                 bg=CGE_LIGHT, fg=CGE_MUTED).pack(side="left")

        sel_frame = tk.Frame(doc_header, bg=CGE_LIGHT)
        sel_frame.pack(side="right")
        self._sel_count_lbl = tk.Label(sel_frame, text="", font=FONT_SMALL,
                                       bg=CGE_LIGHT, fg=CGE_MUTED)
        self._sel_count_lbl.pack(side="left", padx=(0, 8))
        tk.Button(sel_frame, text="Todos", font=FONT_SMALL,
                  bg=CGE_BORDER, fg=CGE_TEXT, relief="flat", bd=0,
                  padx=8, pady=2, cursor="hand2",
                  command=self._sel_todos).pack(side="left")
        tk.Button(sel_frame, text="Ninguno", font=FONT_SMALL,
                  bg=CGE_BORDER, fg=CGE_TEXT, relief="flat", bd=0,
                  padx=8, pady=2, cursor="hand2",
                  command=self._sel_ninguno).pack(side="left", padx=(4, 0))

        # Frame para lista de docs
        doc_box = tk.Frame(parent, bg=CGE_CARD,
                           highlightbackground=CGE_BORDER, highlightthickness=1)
        doc_box.pack(fill="x", pady=(0, 12))

        self._doc_canvas = tk.Canvas(doc_box, bg=CGE_CARD,
                                     highlightthickness=0, height=240)
        sb_doc = tk.Scrollbar(doc_box, orient="vertical",
                              command=self._doc_canvas.yview)
        self._doc_canvas.configure(yscrollcommand=sb_doc.set)
        sb_doc.pack(side="right", fill="y")
        self._doc_canvas.pack(side="left", fill="both", expand=True)

        self._doc_inner = tk.Frame(self._doc_canvas, bg=CGE_CARD)
        self._doc_win = self._doc_canvas.create_window(
            (0, 0), window=self._doc_inner, anchor="nw")
        self._doc_inner.bind("<Configure>",
            lambda e: self._doc_canvas.configure(
                scrollregion=self._doc_canvas.bbox("all")))
        self._doc_canvas.bind("<Configure>",
            lambda e: self._doc_canvas.itemconfig(self._doc_win, width=e.width))
        self._doc_canvas.bind("<MouseWheel>",
            lambda e: self._doc_canvas.yview_scroll(int(-1*(e.delta/120)), "units"))
        self._doc_inner.bind("<MouseWheel>",
            lambda e: self._doc_canvas.yview_scroll(int(-1*(e.delta/120)), "units"))

        self._lbl_no_docs = tk.Label(self._doc_inner,
                                     text="Ingresa el periodo y presiona 'Buscar documentos'",
                                     font=FONT_SMALL, bg=CGE_CARD, fg=CGE_MUTED,
                                     pady=20)
        self._lbl_no_docs.pack()

        # ── Seccion actividad (abajo) ──
        act_header = tk.Frame(parent, bg=CGE_LIGHT)
        act_header.pack(fill="x", pady=(0, 4))
        tk.Label(act_header, text="ACTIVIDAD",
                 font=("Segoe UI", 8, "bold"),
                 bg=CGE_LIGHT, fg=CGE_MUTED).pack(side="left")
        tk.Button(act_header, text="Limpiar", font=FONT_SMALL,
                  bg=CGE_BORDER, fg=CGE_TEXT, relief="flat", bd=0,
                  padx=8, pady=2, cursor="hand2",
                  command=self._clear_log).pack(side="right")
        self._btn_detener = tk.Button(act_header, text="Detener", font=FONT_SMALL,
                  bg=CGE_RED, fg=CGE_WHITE, relief="flat", bd=0,
                  padx=8, pady=2, cursor="hand2",
                  command=self._detener)
        # se muestra solo cuando hay proceso activo

        log_box = tk.Frame(parent, bg=CGE_CARD,
                           highlightbackground=CGE_BORDER, highlightthickness=1)
        log_box.pack(fill="both", expand=True)

        self._log = scrolledtext.ScrolledText(
            log_box, font=FONT_MONO, bg=CGE_CARD, fg=CGE_TEXT,
            insertbackground=CGE_TEXT, relief="flat", bd=8,
            state="disabled", wrap="word", height=8)
        self._log.pack(fill="both", expand=True)

        self._log.tag_config("ok",     foreground=CGE_GREEN)
        self._log.tag_config("err",    foreground=CGE_RED)
        self._log.tag_config("warn",   foreground=CGE_YELLOW)
        self._log.tag_config("blue",   foreground=CGE_BLUE)
        self._log.tag_config("muted",  foreground=CGE_MUTED)
        self._log.tag_config("bold",   font=("Consolas", 9, "bold"))

    # ── LOG ───────────────────────────────────────────────────────────────────
    def log(self, msg, tag=None):
        def _do():
            self._log.configure(state="normal")
            self._log.insert("end", msg + "\n", tag or "")
            self._log.see("end")
            self._log.configure(state="disabled")
        self.after(0, _do)

    def _clear_log(self):
        self._log.configure(state="normal")
        self._log.delete("1.0", "end")
        self._log.configure(state="disabled")

    def _detener(self):
        self._stop_flag = True
        self._btn_detener.pack_forget()
        self.log("Deteniendo...", "warn")

    # ── DOCS LIST ─────────────────────────────────────────────────────────────
    def _render_docs(self, docs):
        for w in self._doc_inner.winfo_children():
            w.destroy()
        self._doc_vars = []
        if not docs:
            tk.Label(self._doc_inner,
                     text="No se encontraron documentos para el periodo indicado.",
                     font=FONT_SMALL, bg=CGE_CARD, fg=CGE_RED, pady=14).pack()
            self._sel_count_lbl.configure(text="")
            return
        for i, doc in enumerate(docs):
            var = tk.BooleanVar(value=True)
            var.trace_add("write", lambda *a: self._update_sel_count())
            self._doc_vars.append(var)
            bg = CGE_ROWALT if i % 2 == 0 else CGE_CARD
            row = tk.Frame(self._doc_inner, bg=bg)
            row.pack(fill="x")
            short = doc["nombre"] if len(doc["nombre"]) <= 60 else doc["nombre"][:58] + "…"
            cb = tk.Checkbutton(row, text=short, variable=var,
                                font=FONT_SMALL, bg=bg, fg=CGE_TEXT,
                                selectcolor=CGE_LIGHT,
                                activebackground=bg, activeforeground=CGE_BLUE,
                                anchor="w", padx=10, pady=5)
            cb.pack(fill="x")
            for w in (row, cb):
                w.bind("<MouseWheel>",
                    lambda e: self._doc_canvas.yview_scroll(int(-1*(e.delta/120)), "units"))
        self._update_sel_count()

    def _update_sel_count(self):
        marcados = sum(1 for v in self._doc_vars if v.get())
        self._sel_count_lbl.configure(text=f"{marcados} de {len(self._doc_vars)} marcados")

    def _sel_todos(self):
        for v in self._doc_vars:
            v.set(True)

    def _sel_ninguno(self):
        for v in self._doc_vars:
            v.set(False)

    # ── ACCIONES ──────────────────────────────────────────────────────────────
    def _lock(self):
        self._running   = True
        self._stop_flag = False
        self._btn_buscar.configure(state="disabled")
        self._btn_verificar.configure(state="disabled")
        self._btn_detener.pack(side="right", padx=(0, 4))
        self._progress.configure(mode="indeterminate")
        self._progress.start(10)

    def _unlock(self):
        self._running = False
        self._btn_buscar.configure(state="normal")
        self._btn_detener.pack_forget()
        if self._docs:
            self._btn_verificar.configure(state="normal")
        self._progress.stop()

    def _on_buscar(self):
        mes_raw = self._v_mes.get().strip()
        anio    = self._v_anio.get().strip()
        mes     = MESES.get(mes_raw.lower())
        if not mes:
            messagebox.showerror("Error", f"Mes '{mes_raw}' no reconocido.\nUsa numero (01-12) o nombre.")
            return
        if not re.fullmatch(r"\d{4}", anio):
            messagebox.showerror("Error", "Año invalido. Ej: 2026")
            return
        self._lock()
        self._clear_log()
        threading.Thread(target=self._thread_buscar,
                         args=(mes, anio, self._v_idioma.get()), daemon=True).start()

    def _thread_buscar(self, mes, anio, idioma):
        try:
            self.log(f"Conectando a Workiva — {mes}-{anio} / {idioma}...", "blue")
            docs = buscar_documentos(mes, anio, idioma)
            self._docs = docs
            if not docs:
                self.log("No se encontraron documentos.", "warn")
            else:
                self.log(f"  {len(docs)} documento(s) encontrado(s).", "ok")
            periodo = f"{mes}-{anio}"
            self._ss_name  = f"Verificación de sumas {periodo}"
            self._ss_cache = Path(__file__).parent / f".ss_verif_id_{periodo}"
            self._docx_dir = Path("docx_tmp_verif")
            self.after(0, lambda: self._render_docs(self._docs))
            if self._docs:
                self.after(0, lambda: self._btn_verificar.configure(state="normal"))
        except Exception as e:
            self.log(f"ERROR: {e}", "err")
        finally:
            self.after(0, self._unlock)

    def _on_verificar(self):
        seleccionados = [d for d, v in zip(self._docs, self._doc_vars) if v.get()]
        if not seleccionados:
            messagebox.showwarning("Aviso", "Selecciona al menos un documento.")
            return
        # Limpiar solo si esta es una corrida nueva (no si ya hay una en curso,
        # para no perder resultados de un lote todavia procesandose).
        if not self._running:
            self._clear_log()
        self._lock()
        threading.Thread(target=self._thread_verificar,
                         args=(seleccionados,), daemon=True).start()

    def _thread_verificar(self, seleccionados):
        try:
            self.log(f"\nBuscando spreadsheet '{self._ss_name}'...", "blue")
            ss_id = buscar_spreadsheet_verif(self._ss_name, self._ss_cache)
            if not ss_id:
                self.log(f"No se encontro '{self._ss_name}'.", "err")
                return
            self.log(f"  Spreadsheet encontrado.", "ok")
            self._docx_dir.mkdir(exist_ok=True)

            total_hall = 0
            for i, doc in enumerate(seleccionados, 1):
                if self._stop_flag:
                    self.log("\nProceso detenido por el usuario.", "warn")
                    break
                m = re.match(r"^([A-Z]\d+)", doc["nombre"].strip())
                codigo = m.group(1) if m else doc["nombre"][:20]

                self.log(f"\n[{i}/{len(seleccionados)}] {doc['nombre']}", "bold")
                self.log("  Exportando...", "muted")
                try:
                    ruta = exportar_docx(doc, self._docx_dir)
                    self.log(f"  Exportado ({ruta.stat().st_size // 1024} KB)", "ok")
                except Exception as e:
                    self.log(f"  ERROR: {e}", "err")
                    continue

                self.log("  Verificando sumas...", "muted")
                try:
                    resultado = verificar_docx(ruta)
                except Exception as e:
                    self.log(f"  ERROR: {e}", "err")
                    continue

                n_ok   = len(resultado["ok"])
                n_hall = len(resultado["hallazgos"])
                n_rev  = len(resultado["revisar"])
                total_hall += n_hall
                tag = "ok" if n_hall == 0 else "warn"
                self.log(f"  OK: {n_ok}  |  Hallazgos: {n_hall}  |  Revisar: {n_rev}", tag)

                self.log("  Escribiendo en Workiva...", "muted")
                try:
                    escribir_resumen(ss_id, codigo, doc["nombre"], resultado)
                    escribir_4_hojas(ss_id, codigo, resultado)
                    self.log("  Escrito OK", "ok")
                except Exception as e:
                    self.log(f"  ERROR: {e}", "err")

            self.log(f"\n{'─'*52}", "blue")
            self.log("PROCESO COMPLETADO", "ok")
            self.log(f"Documentos : {len(seleccionados)}", "ok")
            self.log(f"Hallazgos  : {total_hall}",
                     "warn" if total_hall > 0 else "ok")
            self.log(f"Workiva    : '{self._ss_name}'", "muted")
            self.log(f"{'─'*52}", "blue")

        except Exception as e:
            self.log(f"ERROR inesperado: {e}", "err")
        finally:
            if self._docx_dir.exists():
                shutil.rmtree(self._docx_dir, ignore_errors=True)
            self.after(0, self._avisar_fin)
            self.after(0, self._unlock)


    # ── VALIDAR COMPARATIVOS (mod6) ──────────────────────────────────────────

    def _build_view_validar_comparativos(self):
        frame = tk.Frame(self._content, bg=CGE_LIGHT)
        self._views["mod6"] = frame

        body = tk.Frame(frame, bg=CGE_LIGHT)
        body.pack(fill="both", expand=True)

        # Panel izquierdo
        left = tk.Frame(body, bg=CGE_LIGHT, width=230)
        left.pack(side="left", fill="y", padx=(0, 14))
        left.pack_propagate(False)

        tk.Label(left, text="PARÁMETROS", font=("Segoe UI", 8, "bold"),
                 bg=CGE_LIGHT, fg=CGE_MUTED).pack(anchor="w", pady=(6, 2))
        pf = tk.Frame(left, bg=CGE_CARD,
                      highlightbackground=CGE_BORDER, highlightthickness=1)
        pf.pack(fill="x", pady=(0, 10))
        inner = tk.Frame(pf, bg=CGE_CARD, padx=12, pady=10)
        inner.pack(fill="x")

        labels = ["Sociedad", "Año", "Trimestre"]
        vars_  = []
        for i, lbl in enumerate(labels):
            tk.Label(inner, text=lbl, font=FONT_SMALL,
                     bg=CGE_CARD, fg=CGE_MUTED).grid(row=i, column=0, sticky="w", pady=4)
            v = tk.StringVar()
            e = tk.Entry(inner, textvariable=v, font=FONT_LABEL,
                         bg=CGE_LIGHT, fg=CGE_TEXT, relief="flat", bd=4, width=12,
                         highlightbackground=CGE_BORDER, highlightthickness=1)
            e.grid(row=i, column=1, sticky="ew", padx=(8, 0), pady=4)
            e.bind("<Return>", lambda ev: self._val_on_run())
            vars_.append(v)
        # Tipo: dropdown CONSO / IND
        tk.Label(inner, text="Tipo", font=FONT_SMALL,
                 bg=CGE_CARD, fg=CGE_MUTED).grid(row=3, column=0, sticky="w", pady=4)
        self._val_tipo = tk.StringVar(value="CONSO")
        tipo_menu = tk.OptionMenu(inner, self._val_tipo, "CONSO", "IND")
        tipo_menu.configure(font=FONT_LABEL, bg=CGE_LIGHT, fg=CGE_TEXT,
                            activebackground=CGE_BLUE, activeforeground="white",
                            relief="flat", bd=0, highlightthickness=1,
                            highlightbackground=CGE_BORDER, anchor="w")
        tipo_menu["menu"].configure(font=FONT_LABEL, bg=CGE_LIGHT, fg=CGE_TEXT,
                                    activebackground=CGE_BLUE, activeforeground="white")
        tipo_menu.grid(row=3, column=1, sticky="ew", padx=(8, 0), pady=4)
        inner.columnconfigure(1, weight=1)
        self._val_sociedad, self._val_anio, self._val_trim = vars_

        # Carpeta salida
        tk.Label(left, text="CARPETA SALIDA", font=("Segoe UI", 8, "bold"),
                 bg=CGE_LIGHT, fg=CGE_MUTED).pack(anchor="w", pady=(6, 2))
        cf = tk.Frame(left, bg=CGE_CARD,
                      highlightbackground=CGE_BORDER, highlightthickness=1)
        cf.pack(fill="x", pady=(0, 10))
        cinner = tk.Frame(cf, bg=CGE_CARD, padx=8, pady=8)
        cinner.pack(fill="x")
        self._val_carpeta = tk.StringVar(value=str(Path.home()))
        tk.Entry(cinner, textvariable=self._val_carpeta, font=FONT_SMALL,
                 bg=CGE_LIGHT, fg=CGE_TEXT, relief="flat", bd=2, width=20,
                 highlightbackground=CGE_BORDER, highlightthickness=1).pack(fill="x")
        tk.Button(cinner, text="Examinar…", font=FONT_SMALL,
                  bg=CGE_BORDER, fg=CGE_TEXT, relief="flat", bd=0,
                  padx=8, pady=3, cursor="hand2",
                  command=self._val_elegir_carpeta).pack(fill="x", pady=(4, 0))

        self._val_btn_run = tk.Button(
            left, text="Validar", font=("Segoe UI", 10, "bold"),
            bg=CGE_BLUE, fg=CGE_WHITE, relief="flat", bd=0,
            padx=12, pady=8, cursor="hand2",
            command=self._val_on_run)
        self._val_btn_run.pack(fill="x", pady=(4, 0))
        self._val_btn_run.bind("<Return>", lambda e: self._val_on_run())

        # Panel derecho – log
        right = tk.Frame(body, bg=CGE_LIGHT)
        right.pack(side="left", fill="both", expand=True)

        act_hdr = tk.Frame(right, bg=CGE_LIGHT)
        act_hdr.pack(fill="x", pady=(0, 4))
        tk.Label(act_hdr, text="ACTIVIDAD", font=("Segoe UI", 8, "bold"),
                 bg=CGE_LIGHT, fg=CGE_MUTED).pack(side="left")
        tk.Button(act_hdr, text="Limpiar", font=FONT_SMALL,
                  bg=CGE_BORDER, fg=CGE_TEXT, relief="flat", bd=0,
                  padx=8, pady=2, cursor="hand2",
                  command=self._val_clear_log).pack(side="right")
        log_box = tk.Frame(right, bg=CGE_CARD,
                           highlightbackground=CGE_BORDER, highlightthickness=1)
        log_box.pack(fill="both", expand=True)
        self._val_log = scrolledtext.ScrolledText(
            log_box, font=FONT_MONO, bg=CGE_CARD, fg=CGE_TEXT,
            relief="flat", bd=8, state="disabled", wrap="word", height=8)
        self._val_log.pack(fill="both", expand=True)
        self._val_log.tag_config("ok",   foreground=CGE_GREEN)
        self._val_log.tag_config("err",  foreground=CGE_RED)
        self._val_log.tag_config("warn", foreground=CGE_YELLOW)
        self._val_log.tag_config("blue", foreground=CGE_BLUE)
        self._val_log.tag_config("muted", foreground=CGE_MUTED)
        self._val_log_write("Completa los parámetros y presiona 'Validar'.", "muted")

    def _val_log_write(self, msg, tag=None):
        def _do():
            self._val_log.configure(state="normal")
            self._val_log.insert("end", msg + "\n", tag or "")
            self._val_log.see("end")
            self._val_log.configure(state="disabled")
        self.after(0, _do)

    def _val_clear_log(self):
        self._val_log.configure(state="normal")
        self._val_log.delete("1.0", "end")
        self._val_log.configure(state="disabled")

    def _val_elegir_carpeta(self):
        from tkinter import filedialog
        d = filedialog.askdirectory(initialdir=self._val_carpeta.get())
        if d:
            self._val_carpeta.set(d)

    def _val_on_run(self):
        soc  = self._val_sociedad.get().strip().upper()
        anio = self._val_anio.get().strip()
        trim = self._val_trim.get().strip()
        tipo = self._val_tipo.get().strip().upper() or "CONSO"
        if not soc or not anio or not trim:
            messagebox.showwarning("Aviso", "Completa Sociedad, Año y Trimestre.")
            return
        self._val_clear_log()
        self._val_btn_run.configure(state="disabled")
        self._progress.configure(mode="indeterminate")
        self._progress.start(10)
        self._val_log_write(f"Validando {soc} {tipo} {trim}-{anio}...", "blue")
        threading.Thread(
            target=self._val_thread_run,
            args=(soc, anio, trim, tipo),
            daemon=True).start()

    def _val_thread_run(self, soc, anio, trim, tipo):
        try:
            import asyncio as _aio_v, os as _os_v, types as _types_v, builtins as _bi_v
            _os_v.environ["WORKIVA_CLIENT_ID"]     = CLIENT_ID
            _os_v.environ["WORKIVA_CLIENT_SECRET"] = CLIENT_SECRET
            _os_v.environ["WORKIVA_WORKSPACE_ID"]  = WORKSPACE_ID
            tmpdir  = self._get_mcp_tmpdir()
            mcp_mod = self._load_mcp_v2_mod(tmpdir)

            val_mod = _types_v.ModuleType("validar_v2")
            val_mod.__file__ = str(tmpdir / "validar_comparativos_v2.py")
            exec(compile(_VALIDAR_V2_SRC, str(tmpdir / "validar_comparativos_v2.py"), "exec"), val_mod.__dict__)
            val_mod._load_w = lambda: mcp_mod
            val_mod.w = mcp_mod

            carpeta  = self._val_carpeta.get()
            orig_dir = _os_v.getcwd()

            # Un único event loop para todo el thread — evita "bound to a different event loop"
            loop = _aio_v.new_event_loop()
            _aio_v.set_event_loop(loop)
            try:
                mcp_mod._wk._client = None
                encontrado = loop.run_until_complete(val_mod.resolver_spreadsheet(soc, anio, trim, tipo))
                if not encontrado:
                    self._val_log_write("No se encontró el archivo en Workiva.", "err")
                    return
                ss_id, etiqueta = encontrado
                self._val_log_write(f"Archivo: {etiqueta}", "ok")

                _orig_print = _bi_v.print
                def _gui_print(*a, **kw):
                    msg = " ".join(str(x) for x in a)
                    tag = "err" if "ERROR" in msg else "ok" if ("OK" in msg or "Excel" in msg) else None
                    self._val_log_write(msg, tag)
                _bi_v.print = _gui_print
                try:
                    _os_v.chdir(carpeta)
                    mcp_mod._wk._client = None
                    code = loop.run_until_complete(val_mod.validar(ss_id, etiqueta))
                finally:
                    _bi_v.print = _orig_print
                    _os_v.chdir(orig_dir)
            finally:
                loop.close()

            # Mismo patrón de nombre que usa validar_comparativos_v2.py
            m = re.match(r"(E\d+)_(IND|CONSO)_(\d{2})[-_](\d{4})", etiqueta)
            if m:
                base = f"{m.group(1)}_{m.group(2)}_{m.group(3)}-{m.group(4)}"
            else:
                base = re.sub(r'[\\/:*?"<>|\s]+', "_", etiqueta)
            xlsx_path = os.path.join(carpeta, f"detalle_filas_{base}.xlsx")

            if code == 0:
                self._val_log_write("Validación completa: sin hallazgos.", "ok")
                self.after(0, lambda p=xlsx_path: self._abrir_si_confirma(
                    "Validación completa", "Sin hallazgos.\n\n¿Abrir el Excel generado?", p))
            elif code == 2:
                self._val_log_write("Validación completa: hay hallazgos (ver Excel).", "warn")
                self.after(0, lambda p=xlsx_path: self._abrir_si_confirma(
                    "Validación completa", "Hay hallazgos — revisa el Excel.\n\n¿Abrir el Excel generado?", p))
            else:
                self._val_log_write("Validación terminó con advertencias.", "warn")
        except Exception as e:
            self._val_log_write(f"ERROR: {e}", "err")
        finally:
            self.after(0, self._avisar_fin)
            self.after(0, lambda: self._val_btn_run.configure(state="normal"))
            self.after(0, self._progress.stop)

    def _abrir_si_confirma(self, titulo, mensaje, ruta):
        # Restaurar la ventana si estaba minimizada, si no el popup queda invisible.
        # OJO: solo si estaba "iconic" — no pisar una ventana maximizada.
        try:
            if self.state() == "iconic":
                self.deiconify()
            self.lift()
        except Exception:
            pass
        if messagebox.askyesno(titulo, mensaje):
            try:
                os.startfile(ruta)
            except Exception as e:
                messagebox.showerror("Error", f"No se pudo abrir:\n{ruta}\n\n{e}")


if __name__ == "__main__":
    app = App()
    app.mainloop()
