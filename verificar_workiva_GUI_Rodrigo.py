"""
verificar_workiva_GUI.py
Verificador de Sumas - EE.FF. Workiva
Interfaz grafica con tkinter — colores corporativos CGE
"""
import base64, io, json, re, shutil, ssl, sys, time, urllib.request, urllib.error, zipfile
import xml.etree.ElementTree as ET
from pathlib import Path
from collections import defaultdict
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import threading

# ── CREDENCIALES ──────────────────────────────────────────────────────────────
CLIENT_ID     = "8eb96491-aee9-4a94-8ecd-1651efd1c3e5"
CLIENT_SECRET = "wk_secret:oa2c:A2tzB4CsbsKSA2jw4uph"
WORKSPACE_ID  = "w_34913aadaa38420eabd7e4d341b78a1a"

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
    r'resultado\s+integral\s+total|incremento\s*\(disminuci[oó]n\))', re.I)

KW_FLAG = re.compile(
    r'(\b(total(?:es)?|sub-?total)\b|saldo\s+(final|al\b)|total\s+d[eo]l?\b|patrimonio\s+total)', re.I)

BAL    = re.compile(r'(saldo\b|patrimonio\s+al\b)', re.I)
TOTMOV = re.compile(r'(total.*(increment|movimiento|disminuci|cambios|'
                    r'resultado\s+integral|del\s+per[ií]odo|patrimonio)'
                    r'|^cambios[,\s]+total)', re.I)
REF_NOTA = re.compile(r'\(nota\s+\d+[\.\d]*\)', re.I)

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
    if ',' in t:
        return None
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
                elif KW_FLAG.search(lab) and best is not None:
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
                _is_close_candidate = BAL.search(lab) or TOTMOV.search(lab)
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

    hallazgos = [r for r in rows_chk
                 if r.get('localizado') or abs(r['dif']) <= UMBRAL]

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
    "IiIiCmxsZW5hcl9jb21wYXJhdGl2b3MucHkKPT09PT09PT09PT09PT09PT09PT09PQpTY3JpcHQgZ2Vu"
    "w6lyaWNvIHBhcmEgY29tcGxldGFyIGNvbHVtbmFzIGRlIHBlcsOtb2RvcyBlbiBhcmNoaXZvcwoiQmFz"
    "ZSBOb3RhcyIgaW5kaXZpZHVhbGVzIGRlIFRPREFTIGxhcyBzb2NpZWRhZGVzIGRlIHVuIHBlcsOtb2Rv"
    "LgoKVVNPOgogICAgcHl0aG9uIGxsZW5hcl9jb21wYXJhdGl2b3MucHkKCkVsIHNjcmlwdCBwcmVndW50"
    "YSBlbCBhw7FvIHkgbWVzIHkgcHJvY2VzYSB0b2RvcyBsb3MgYXJjaGl2b3MgZGUgbGEKY2FycGV0YSBJ"
    "bmRpdmlkdWFsZXMgZGUgZXNlIHBlcsOtb2RvIGF1dG9tw6F0aWNhbWVudGUuCiIiIgoKaW1wb3J0IHdh"
    "cm5pbmdzLCB0aW1lLCByZSwgc3NsLCB1cmxsaWIucmVxdWVzdCwgdXJsbGliLnBhcnNlLCBqc29uCmlt"
    "cG9ydCByZXF1ZXN0cwpmcm9tIHVybGxpYjMuZXhjZXB0aW9ucyBpbXBvcnQgSW5zZWN1cmVSZXF1ZXN0"
    "V2FybmluZwp3YXJuaW5ncy5maWx0ZXJ3YXJuaW5ncygiaWdub3JlIiwgY2F0ZWdvcnk9SW5zZWN1cmVS"
    "ZXF1ZXN0V2FybmluZykKCiMg4pSA4pSAIENSRURFTkNJQUxFUyDilIDilIDilIDilIDilIDilIDilIDi"
    "lIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDi"
    "lIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDi"
    "lIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIAKQ0xJRU5UX0lEICAgICA9"
    "ICJkYjJjNTUxZS1lMThhLTQxN2UtOGU1Mi1kMTgyNzE2YjhlZjIiCkNMSUVOVF9TRUNSRVQgPSAid2tf"
    "c2VjcmV0Om9hMmM6RHpsVUNtQlFEdjZyYVB4RzA5bWUiClRPS0VOX1VSTCAgICAgPSAiaHR0cHM6Ly9h"
    "cGkuYXBwLndkZXNrLmNvbS9pYW0vdjEvb2F1dGgyL3Rva2VuIgojIOKUgOKUgOKUgOKUgOKUgOKUgOKU"
    "gOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKU"
    "gOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKU"
    "gOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKU"
    "gOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgAoKZGVmIGdldF9zZXNzaW9uKCk6CiAgICByZXNw"
    "ID0gcmVxdWVzdHMucG9zdChUT0tFTl9VUkwsIGRhdGE9ewogICAgICAgICJncmFudF90eXBlIjogICAg"
    "ImNsaWVudF9jcmVkZW50aWFscyIsCiAgICAgICAgImNsaWVudF9pZCI6ICAgICBDTElFTlRfSUQsCiAg"
    "ICAgICAgImNsaWVudF9zZWNyZXQiOiBDTElFTlRfU0VDUkVULAogICAgfSwgdmVyaWZ5PUZhbHNlLCB0"
    "aW1lb3V0PTMwKQogICAgdG9rZW4gPSByZXNwLmpzb24oKVsiYWNjZXNzX3Rva2VuIl0KICAgIHMgPSBy"
    "ZXF1ZXN0cy5TZXNzaW9uKCkKICAgIHMuaGVhZGVycy51cGRhdGUoeyJBdXRob3JpemF0aW9uIjogZiJC"
    "ZWFyZXIge3Rva2VufSJ9KQogICAgcy52ZXJpZnkgPSBGYWxzZQogICAgcmV0dXJuIHMKCiMgSW1wb3J0"
    "YXIgZnVuY2nDs24gZGUgbGltcGllemEgc2kgZXN0w6EgZGlzcG9uaWJsZQpkZWYgY2xlYW5fZmlsZShm"
    "aWQsIG5hbWUpOgogICAgcGFzcyAgIyBuby1vcCBzaSBsaW1waWFyX2NvbXBhcmF0aXZvcy5weSBubyBl"
    "c3TDoSBkaXNwb25pYmxlCnRyeToKICAgIGV4ZWMob3BlbigibGltcGlhcl9jb21wYXJhdGl2b3MucHki"
    "LCBlbmNvZGluZz0idXRmLTgiKS5yZWFkKCkuc3BsaXQoIiMg4pSA4pSAIE1BSU4iKVswXSkKZXhjZXB0"
    "IEZpbGVOb3RGb3VuZEVycm9yOgogICAgcHJpbnQoIiAgW0lORk9dIGxpbXBpYXJfY29tcGFyYXRpdm9z"
    "LnB5IG5vIGVuY29udHJhZG8g4oCUIHNlIG9taXRlIGxpbXBpZXphIikKCiMg4pSA4pSA4pSAIENPTkZJ"
    "R1VSQUNJw5NOIOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKU"
    "gOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKU"
    "gOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKU"
    "gOKUgOKUgOKUgApXT1JLU1BBQ0VfSUQgPSAid18zNDkxM2FhZGFhMzg0MjBlYWJkN2U0ZDM0MWI3OGEx"
    "YSIKV0RFU0tfQkFTRSAgID0gImh0dHBzOi8vYXBpLmFwcC53ZGVzay5jb20iCgojIOKUgOKUgCBNT0RP"
    "IFBSVUVCQSDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDi"
    "lIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDi"
    "lIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDi"
    "lIDilIDilIDilIDilIDilIDilIAKIyBQYXJhIHByb2JhciBjb24gdW4gYXJjaGl2byBkZSBub21icmUg"
    "bm8gZXN0w6FuZGFyLgojIEVuIHByb2R1Y2Npw7NuIGRlamFyIFRFU1RfTU9ERSA9IEZhbHNlLgpURVNU"
    "X01PREUgICAgICA9IEZhbHNlClRFU1RfRklMRV9JRCAgID0gIjE0ZDlmNDRmODc5NjQwY2E5ZWZkMWQx"
    "NGQ3ZmQ5MzkzIiAgIyBFMjE1X0lORF8wOS0yMDI2X0Jhc2UgTm90YXMgQ0dFQ3gKVEVTVF9DT0RFICAg"
    "ICAgPSAiRTIxNSIKVEVTVF9NTSAgICAgICAgPSAiMDkiClRFU1RfWVlZWSAgICAgID0gIjIwMjYiClRF"
    "U1RfU1VGRklYICAgID0gIkJhc2UgTm90YXMgQ0dFQ3giCiMg4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA"
    "4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA"
    "4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA"
    "4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA"
    "4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSACgojIOKUgOKUgCBFWENFUENJw5NOIERFIFBSVUVC"
    "QSDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDi"
    "lIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDi"
    "lIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIAKIyBDdWFuZG8g"
    "U09VUkNFX0NPREVfT1ZFUlJJREUgZXN0w6EgZGVmaW5pZG8sIGFsIHByb2Nlc2FyIGVsIGFyY2hpdm8g"
    "aW5kaWNhZG8KIyBlbiBPVkVSUklERV9UQVJHRVQsIGxhcyBmdWVudGVzIHNlIGJ1c2NhbiB1c2FuZG8g"
    "U09VUkNFX0NPREVfT1ZFUlJJREUgZW4KIyBsdWdhciBkZWwgY8OzZGlnbyByZWFsIGRlbCBhcmNoaXZv"
    "IGRlc3Rpbm8uCiMgU09MTyBQQVJBIFBSVUVCQVMg4oCUIGRlamFyIGVuIE5vbmUgZW4gcHJvZHVjY2nD"
    "s24uCk9WRVJSSURFX1RBUkdFVCAgICAgID0gKCJFMzAwIiwgIjAzIiwgIjIwMjYiKSAgICMgKGNvZGUs"
    "IG1tLCB5eXl5KSBkZWwgYXJjaGl2byBkZXN0aW5vClNPVVJDRV9DT0RFX09WRVJSSURFID0gIkUyMDAi"
    "ICAgICAgICAgICAgICAgICAgICAjIGPDs2RpZ28gYSB1c2FyIGFsIGJ1c2NhciBmdWVudGVzCiMg4pSA"
    "4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA"
    "4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA"
    "4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA"
    "4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSACgpGVUxMX0NP"
    "UFlfUEFJUlMgPSB7CiAgICAiNzkuLSBQcsOpc3RhbW9zIGJhbmNhcmlvcyAtIGRlc2dsb3NlIGRlIG1v"
    "bmVkYXMgKGIpIjoKICAgICI3OC4tIFByw6lzdGFtb3MgYmFuY2FyaW9zIC0gZGVzZ2xvc2UgZGUgbW9u"
    "ZWRhcyAoYikiLAp9CgojIEFsaWFzIGRlIGhvamFzOiBub21icmUgZW4gdGFyZ2V0IOKGkiBub21icmUg"
    "ZW4gZnVlbnRlIChjdWFuZG8gZGlmaWVyZW4gZW50cmUgcGVyw61vZG9zKQpTSEVFVF9BTElBU0VTID0g"
    "ewogICAgIjIwLi0gUmVzdW1lbiBkZSBlc3RyYXRpZmljYWNpw7NuIGRlIGxhIGNhcnRlcmEgYnJ1dGEi"
    "OgogICAgIjIwLi0gQ3VlbnRhcyBwb3IgY29icmFyIGEgZW50aWRhZGVzIHJlbGFjaW9uYWRhcyIsCn0K"
    "CiMgSG9qYXMgY29uIGJsb3F1ZSBjb21wYXJhdGl2byBlbiBmaWxhcyBmaWphcyAobm8gZGV0ZWN0YWJs"
    "ZXMgcG9yIGZlY2hhIGVuIGNvbCBCKS4KIyBGb3JtYXRvOiBub21icmVfaG9qYSDihpIgKHNyY19yb3df"
    "c3RhcnQsIHNyY19yb3dfZW5kLCB0Z3Rfcm93X3N0YXJ0LCB0Z3Rfcm93X2VuZCkKIyBUb2RvcyBsb3Mg"
    "w61uZGljZXMgc29uIGJhc2UtMCB5IGVsIHJhbmdvIGVzIFtzdGFydCwgZW5kKSBleGNsdXNpdm8uCiMg"
    "TGEgZnVlbnRlIHNpZW1wcmUgZXMgImJhbGFuY2UiIChwZXLDrW9kbyBwcmlvcl9lbmQpLgpCTE9DS19D"
    "T1BZX1NIRUVUUyA9IHsKICAgICI2MC4tIEN1YWRybyBtb3ZpbWllbnRvIGFjdGl2byBmaWpvIjogICAg"
    "ICAgICAgICAgICAgICAgICAgICAgICgxMSwgMzYsIDUxLCA3NiksCiAgICAiNjIuLSBQcm9waWVkYWRl"
    "cywgcGxhbnRhIHkgZXF1aXBvcyBlbiBhcnJlbmRhbWllbnRvLCBuZXRvIjogICAoMzEsIDQ0LCA0Niwg"
    "NTkpLAp9CgpTS0lQX1NIRUVUUyA9IHsKICAgICJDUCIsIkJhc2VzIiwiUXVlcnkgQlBDIiwiUXVlcnkg"
    "SEFOQSBBRiIsIlJlcG9ydGUgZW4gJCIsCiAgICAiUXVlcnkgLSBIQU5BIC0gRGV1ZG9yZXMiLCJBLi0g"
    "QWN0aXZvcyBQUFQiLAogICAgIkIuLSBQYXRyaW1vbmlvIHkgUGFzaXZvcyBQUFQiLCJDLi0gRXN0YWRv"
    "IGRlIHJlc3VsdGFkbyBwb3IgZnVuY2nDs24gUFBUIiwKICAgICJFMSBSZXMgQWN1bXVsYWRvIiwiRjEg"
    "Q3VhZHJhamUgSG9qYSBBLi0gU2FsZG8gSW5pY2lhbCBkZSBDYWphIiwKfQojIOKUgOKUgOKUgOKUgOKU"
    "gOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKU"
    "gOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKU"
    "gOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKU"
    "gOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgAoKc2Vzc2lvbiA9IGdldF9zZXNzaW9u"
    "KCkKc2Vzc2lvbi5oZWFkZXJzLnVwZGF0ZSh7IlgtVmVyc2lvbiI6ICIyMDIyLTAxLTAxIn0pCgpfbGFz"
    "dF90b2tlbiA9IFt0aW1lLnRpbWUoKV0KZGVmIHJlZnJlc2hfdG9rZW4oKToKICAgIGlmIHRpbWUudGlt"
    "ZSgpIC0gX2xhc3RfdG9rZW5bMF0gPiA0ODA6CiAgICAgICAgbnMgPSBnZXRfc2Vzc2lvbigpCiAgICAg"
    "ICAgbnMuaGVhZGVycy51cGRhdGUoeyJYLVZlcnNpb24iOiAiMjAyMi0wMS0wMSJ9KQogICAgICAgIHNl"
    "c3Npb24uaGVhZGVycy51cGRhdGUobnMuaGVhZGVycykKICAgICAgICBfbGFzdF90b2tlblswXSA9IHRp"
    "bWUudGltZSgpCiAgICAgICAgcHJpbnQoIiAgW1Rva2VuIHJlbm92YWRvXSIpCgojIOKUgOKUgOKUgCBI"
    "RUxQRVJTIOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKU"
    "gOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKU"
    "gOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKU"
    "gOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgApkZWYgY29sX2xldHRlcihpZHgpOgogICAgaWYgaWR4IDwg"
    "MjY6IHJldHVybiBjaHIoNjUraWR4KQogICAgcmV0dXJuIGNocig2NCtpZHgvLzI2KStjaHIoNjUraWR4"
    "JTI2KQoKZGVmIGdldF9zaGVldHMoc3NfaWQpOgogICAgcmVzdWx0ID0ge30KICAgIHVybCA9IFdERVNL"
    "X0JBU0UrIi9wbGF0Zm9ybS92MS9zcHJlYWRzaGVldHMvIitzc19pZCsiL3NoZWV0cyIKICAgIGZvciBf"
    "IGluIHJhbmdlKDIwKToKICAgICAgICB0cnk6CiAgICAgICAgICAgIHIgICAgPSBzZXNzaW9uLmdldCh1"
    "cmwsIHRpbWVvdXQ9OTApCiAgICAgICAgICAgIGRhdGEgPSByLmpzb24oKQogICAgICAgICAgICBmb3Ig"
    "cyBpbiBkYXRhLmdldCgiZGF0YSIsIFtdKToKICAgICAgICAgICAgICAgIHJlc3VsdFtzWyJuYW1lIl1d"
    "ID0gc1siaWQiXQogICAgICAgICAgICB1cmwgPSBkYXRhLmdldCgiQG5leHRMaW5rIikKICAgICAgICAg"
    "ICAgaWYgbm90IHVybDoKICAgICAgICAgICAgICAgIHJldHVybiByZXN1bHQKICAgICAgICBleGNlcHQg"
    "RXhjZXB0aW9uOgogICAgICAgICAgICB0aW1lLnNsZWVwKDUpCiAgICByZXR1cm4gcmVzdWx0CgpkZWYg"
    "cmVhZF9zaGVldChzc19pZCwgc2hlZXRfaWQpOgogICAgdXJsID0gKFdERVNLX0JBU0UrIi9wbGF0Zm9y"
    "bS92MS9zcHJlYWRzaGVldHMvIitzc19pZCsiL3NoZWV0cy8iK3NoZWV0X2lkCiAgICAgICAgICAgKyIv"
    "c2hlZXRkYXRhPyRmaWVsZHM9Y2VsbHMuY2FsY3VsYXRlZFZhbHVlLGNlbGxzLnZhbHVlJiRtYXhjZWxs"
    "c3BlcnBhZ2U9NTAwMDAiKQogICAgZm9yIF8gaW4gcmFuZ2UoNSk6CiAgICAgICAgdHJ5OgogICAgICAg"
    "ICAgICByZXR1cm4gc2Vzc2lvbi5nZXQodXJsLCB0aW1lb3V0PTEyMCkuanNvbigpLmdldCgiZGF0YSIs"
    "e30pLmdldCgiY2VsbHMiLFtdKQogICAgICAgIGV4Y2VwdCBFeGNlcHRpb246IHRpbWUuc2xlZXAoNSkK"
    "ICAgIHJldHVybiBbXQoKZGVmIHBvbGwobG9jYXRpb24pOgogICAgdXJsID0gbG9jYXRpb24gaWYgbG9j"
    "YXRpb24uc3RhcnRzd2l0aCgiaHR0cCIpIGVsc2UgV0RFU0tfQkFTRStsb2NhdGlvbgogICAgZm9yIF8g"
    "aW4gcmFuZ2UoNDApOgogICAgICAgIHRpbWUuc2xlZXAoMykKICAgICAgICB0cnk6CiAgICAgICAgICAg"
    "IGJvZHkgPSBzZXNzaW9uLmdldCh1cmwsIHRpbWVvdXQ9NjApLmpzb24oKQogICAgICAgICAgICBzdCAg"
    "ID0gYm9keS5nZXQoInN0YXR1cyIsIGJvZHkuZ2V0KCJkYXRhIix7fSkuZ2V0KCJzdGF0dXMiLCIiKSkK"
    "ICAgICAgICAgICAgaWYgc3QgPT0gImNvbXBsZXRlZCI6IHJldHVybiBUcnVlCiAgICAgICAgICAgIGlm"
    "IHN0IGluICgiZmFpbGVkIiwiZXJyb3IiKTogcmV0dXJuIEZhbHNlCiAgICAgICAgZXhjZXB0IEV4Y2Vw"
    "dGlvbjogcGFzcwogICAgcmV0dXJuIEZhbHNlCgpkZWYgcHV0X2NvbChzc19pZCwgc2lkLCBjb2xfaWR4"
    "LCB2YWx1ZXMsIGxhYmVsPSIiKToKICAgIHJlZnJlc2hfdG9rZW4oKQogICAgY2wgID0gY29sX2xldHRl"
    "cihjb2xfaWR4KQogICAgcm5nID0gZiJ7Y2x9MTp7Y2x9e2xlbih2YWx1ZXMpfSIKICAgIHJwICA9IHNl"
    "c3Npb24ucHV0KFdERVNLX0JBU0UrIi9wbGF0Zm9ybS92MS9zcHJlYWRzaGVldHMvIitzc19pZCsiL3No"
    "ZWV0cy8iK3NpZAogICAgICAgICAgICAgICAgICAgICAgKyIvdmFsdWVzLyIrcm5nLAogICAgICAgICAg"
    "ICAgICAgICAgICAganNvbj17InZhbHVlcyI6W1t2XSBmb3IgdiBpbiB2YWx1ZXNdfSwgdGltZW91dD0x"
    "MjApCiAgICBpZiBycC5zdGF0dXNfY29kZSA9PSAyMDI6CiAgICAgICAgb2sgPSBwb2xsKHJwLmhlYWRl"
    "cnMuZ2V0KCJMb2NhdGlvbiIsIiIpKQogICAgICAgIG4gID0gc3VtKDEgZm9yIHYgaW4gdmFsdWVzIGlm"
    "IHYgaXMgbm90IE5vbmUpCiAgICAgICAgcHJpbnQoZiIgICAgeydPSycgaWYgb2sgZWxzZSAnRVJSJ30g"
    "Y29sIHtjbH06IHtufSB2YWxzIFt7bGFiZWx9XSIpCiAgICAgICAgcmV0dXJuIG9rCiAgICBwcmludChm"
    "IiAgICBFUlIgSFRUUCB7cnAuc3RhdHVzX2NvZGV9OiB7cnAudGV4dFs6NjBdfSIpCiAgICByZXR1cm4g"
    "RmFsc2UKCmRlZiBwdXRfY29sX3JhbmdlKHNzX2lkLCBzaWQsIGNvbF9pZHgsIHN0YXJ0X3JvdywgdmFs"
    "dWVzLCBsYWJlbD0iIik6CiAgICAiIiJFc2NyaWJlIHVuIHNsaWNlIGRlIGNvbHVtbmEgY29tZW56YW5k"
    "byBlbiBzdGFydF9yb3cgKGJhc2UtMCkuIiIiCiAgICByZWZyZXNoX3Rva2VuKCkKICAgIGNsID0gY29s"
    "X2xldHRlcihjb2xfaWR4KQogICAgcjEgPSBzdGFydF9yb3cgKyAxICAgICAgICAgICMgYmFzZS0xCiAg"
    "ICByMiA9IHIxICsgbGVuKHZhbHVlcykgLSAxCiAgICBybmcgPSBmIntjbH17cjF9OntjbH17cjJ9Igog"
    "ICAgcnAgID0gc2Vzc2lvbi5wdXQoV0RFU0tfQkFTRSsiL3BsYXRmb3JtL3YxL3NwcmVhZHNoZWV0cy8i"
    "K3NzX2lkKyIvc2hlZXRzLyIrc2lkCiAgICAgICAgICAgICAgICAgICAgICArIi92YWx1ZXMvIitybmcs"
    "CiAgICAgICAgICAgICAgICAgICAgICBqc29uPXsidmFsdWVzIjpbW3ZdIGZvciB2IGluIHZhbHVlc119"
    "LCB0aW1lb3V0PTEyMCkKICAgIGlmIHJwLnN0YXR1c19jb2RlID09IDIwMjoKICAgICAgICBvayA9IHBv"
    "bGwocnAuaGVhZGVycy5nZXQoIkxvY2F0aW9uIiwiIikpCiAgICAgICAgbiAgPSBzdW0oMSBmb3IgdiBp"
    "biB2YWx1ZXMgaWYgdiBpcyBub3QgTm9uZSkKICAgICAgICBwcmludChmIiAgICB7J09LJyBpZiBvayBl"
    "bHNlICdFUlInfSBjb2wge2NsfVt7cjF9OntyMn1dOiB7bn0gdmFscyBbe2xhYmVsfV0iKQogICAgICAg"
    "IHJldHVybiBvawogICAgcHJpbnQoZiIgICAgRVJSIEhUVFAge3JwLnN0YXR1c19jb2RlfToge3JwLnRl"
    "eHRbOjYwXX0iKQogICAgcmV0dXJuIEZhbHNlCgpkZWYgaXNfZm9ybXVsYShyb3csIGNvbCk6CiAgICBj"
    "ID0gcm93W2NvbF0gaWYgY29sIDwgbGVuKHJvdykgZWxzZSB7fQogICAgcmV0dXJuIHN0cihjLmdldCgi"
    "dmFsdWUiLCIiKSBpZiBpc2luc3RhbmNlKGMsZGljdCkgZWxzZSAiIikuc3RhcnRzd2l0aCgiPSIpCgpk"
    "ZWYgZ2V0X2N2KHJvdywgY29sKToKICAgIGMgPSByb3dbY29sXSBpZiBjb2wgPCBsZW4ocm93KSBlbHNl"
    "IHt9CiAgICByZXR1cm4gYy5nZXQoImNhbGN1bGF0ZWRWYWx1ZSIpIGlmIGlzaW5zdGFuY2UoYyxkaWN0"
    "KSBlbHNlIE5vbmUKCiMg4pSA4pSA4pSAIFBBU08gMTogQ2FyZ2FyIHRvZG9zIGxvcyBhcmNoaXZvcyBk"
    "ZWwgd29ya3NwYWNlIOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKU"
    "gOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgApkZWYgbG9hZF9hbGxfZmlsZXMoKToKICAgIGFsbF9m"
    "aWxlcyA9IHt9CiAgICB1cmwgPSBXREVTS19CQVNFKyIvcGxhdGZvcm0vdjEvZmlsZXM/d29ya3NwYWNl"
    "SWQ9IitXT1JLU1BBQ0VfSUQrIiZsaW1pdD0xMDAiCiAgICB3aGlsZSB1cmw6CiAgICAgICAgciAgICA9"
    "IHNlc3Npb24uZ2V0KHVybCwgdGltZW91dD05MCkKICAgICAgICBkYXRhID0gci5qc29uKCkKICAgICAg"
    "ICBmb3IgZiBpbiBkYXRhLmdldCgiZGF0YSIsW10pOgogICAgICAgICAgICBhbGxfZmlsZXNbZlsibmFt"
    "ZSJdXSA9IGZbImlkIl0KICAgICAgICB1cmwgPSBkYXRhLmdldCgiQG5leHRMaW5rIikKICAgIHJldHVy"
    "biBhbGxfZmlsZXMKCiMg4pSA4pSA4pSAIFBBU08gMjogRW5jb250cmFyIGFyY2hpdm9zIGRlc3Rpbm8g"
    "ZGVsIHBlcsOtb2RvIOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKU"
    "gOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgApkZWYgZmluZF90YXJnZXRfZmlsZXMobW0sIHl5"
    "eXksIHRpcG8sIGFsbF9maWxlcyk6CiAgICAiIiIKICAgIEJ1c2NhIHRvZG9zIGxvcyBhcmNoaXZvcyBk"
    "ZWwgcGVyw61vZG8geSB0aXBvIGluZGljYWRvIChJTkQgbyBDT05TTykuCiAgICBQYXRyw7NuOiBFe2Nv"
    "ZGV9X3t0aXBvfV97TU19LXtZWVlZfV9CYXNlIE5vdGFzIHtzdWZmaXh9CiAgICBTaW4gcHJlZmlqb3Mg"
    "KENITiksIChMQyksIGV0Yy4gQWNlcHRhICctJyBvICdfJyBjb21vIHNlcGFyYWRvciBkZSBmZWNoYS4K"
    "ICAgICIiIgogICAgcGF0dGVybiA9IHJlLmNvbXBpbGUocmYiXkVcZCtfe3RpcG99X3ttbX1bLV9de3l5"
    "eXl9X0Jhc2UgTm90YXMgLiskIikKICAgIHRhcmdldHMgPSBbXQogICAgZm9yIG5hbWUsIGZpZCBpbiBh"
    "bGxfZmlsZXMuaXRlbXMoKToKICAgICAgICBpZiBwYXR0ZXJuLm1hdGNoKG5hbWUpOgogICAgICAgICAg"
    "ICBwYXJzZWQgPSByZS5tYXRjaChyZiIoRVxkKylfKHt0aXBvfSlfKFxke3syfX0pWy1fXShcZHt7NH19"
    "KV8oLiopIiwgbmFtZSkKICAgICAgICAgICAgaWYgcGFyc2VkOgogICAgICAgICAgICAgICAgdGFyZ2V0"
    "cy5hcHBlbmQoewogICAgICAgICAgICAgICAgICAgICJpZCI6ICAgICBmaWQsCiAgICAgICAgICAgICAg"
    "ICAgICAgIm5hbWUiOiAgIG5hbWUsCiAgICAgICAgICAgICAgICAgICAgImNvZGUiOiAgIHBhcnNlZC5n"
    "cm91cCgxKSwKICAgICAgICAgICAgICAgICAgICAidGlwbyI6ICAgcGFyc2VkLmdyb3VwKDIpLAogICAg"
    "ICAgICAgICAgICAgICAgICJtbSI6ICAgICBwYXJzZWQuZ3JvdXAoMyksCiAgICAgICAgICAgICAgICAg"
    "ICAgInl5eXkiOiAgIHBhcnNlZC5ncm91cCg0KSwKICAgICAgICAgICAgICAgICAgICAic3VmZml4Ijog"
    "cGFyc2VkLmdyb3VwKDUpLAogICAgICAgICAgICAgICAgfSkKICAgIHJldHVybiBzb3J0ZWQodGFyZ2V0"
    "cywga2V5PWxhbWJkYSB4OiB4WyJjb2RlIl0pCgojIOKUgOKUgOKUgCBQQVNPIDM6IExlZXIgQmFzZXMg"
    "ZGVsIGFyY2hpdm8gZGVzdGlubyDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDi"
    "lIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDi"
    "lIDilIAKZGVmIHJlYWRfYmFzZXModGFyZ2V0X2lkLCBzaGVldHMpOgogICAgY2VsbHMgPSByZWFkX3No"
    "ZWV0KHRhcmdldF9pZCwgc2hlZXRzWyJCYXNlcyJdKQogICAgcmVzdWx0ID0ge30KICAgIHJvd19tYXAg"
    "PSB7CiAgICAgICAgMTM6ICgiY3VycmVudF9lbmQiLCJwcmlvcl9lbmQiKSwKICAgICAgICAxNDogKCJl"
    "ZXJyX3N0YXJ0IiwicHJpb3JfZWVycl9zdGFydCIpLAogICAgICAgIDE1OiAoImVlcnJfZW5kIiwicHJp"
    "b3JfZWVycl9lbmQiKSwKICAgICAgICAxNjogKCJxdWFydGVyX3N0YXJ0IiwicHJpb3JfcXVhcnRlcl9z"
    "dGFydCIpLAogICAgICAgIDE3OiAoInByZXZfcGVyaW9kX2VuZCIsInByaW9yX3ByZXZfcGVyaW9kX2Vu"
    "ZCIpLAogICAgfQogICAgZm9yIHJvd19pZHgsKGtleV9jLGtleV9wKSBpbiByb3dfbWFwLml0ZW1zKCk6"
    "CiAgICAgICAgaWYgcm93X2lkeCA+PSBsZW4oY2VsbHMpOiBjb250aW51ZQogICAgICAgIHJvdyA9IGNl"
    "bGxzW3Jvd19pZHhdCiAgICAgICAgZm9yIGNvbF9pZHgsa2V5IGluIFsoMyxrZXlfYyksKDUsa2V5X3Ap"
    "XToKICAgICAgICAgICAgaWYgY29sX2lkeCA8IGxlbihyb3cpOgogICAgICAgICAgICAgICAgYyAgPSBy"
    "b3dbY29sX2lkeF0KICAgICAgICAgICAgICAgIGN2ID0gYy5nZXQoImNhbGN1bGF0ZWRWYWx1ZSIsIiIp"
    "IGlmIGlzaW5zdGFuY2UoYyxkaWN0KSBlbHNlICIiCiAgICAgICAgICAgICAgICBpZiBjdjogcmVzdWx0"
    "W2tleV0gPSBzdHIoY3YpCiAgICByZXR1cm4gcmVzdWx0CgojIOKUgOKUgOKUgCBQQVNPIDQ6IEJ1c2Nh"
    "ciBhcmNoaXZvcyBmdWVudGUg4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA"
    "4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA"
    "4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSACmRlZiBkYXRlX3RvX21tX3l5eXkoZGF0ZV9zdHIpOgogICAg"
    "cGFydHMgPSBzdHIoZGF0ZV9zdHIpLnNwbGl0KCItIikKICAgIHJldHVybiAocGFydHNbMV0sIHBhcnRz"
    "WzBdKSBpZiBsZW4ocGFydHMpID49IDIgZWxzZSAoTm9uZSwgTm9uZSkKCmRlZiBmaW5kX3NvdXJjZV9m"
    "aWxlcyhwYXJzZWQsIGJhc2VzLCBhbGxfZmlsZXMpOgogICAgY29kZSwgc3VmZml4ID0gcGFyc2VkWyJj"
    "b2RlIl0sIHBhcnNlZFsic3VmZml4Il0KICAgIHRpcG8gPSBwYXJzZWQuZ2V0KCJ0aXBvIiwgIklORCIp"
    "CiAgICBtbV9jdXJyLCB5eXl5X2N1cnIgPSBwYXJzZWRbIm1tIl0sIHBhcnNlZFsieXl5eSJdCgogICAg"
    "IyBFeGNlcGNpw7NuIGRlIHBydWViYTogc3VzdGl0dWlyIGPDs2RpZ28gZGUgZnVlbnRlIHNpIGFwbGlj"
    "YQogICAgaWYgKFNPVVJDRV9DT0RFX09WRVJSSURFIGFuZAogICAgICAgICAgICAoY29kZSwgbW1fY3Vy"
    "ciwgeXl5eV9jdXJyKSA9PSBPVkVSUklERV9UQVJHRVQpOgogICAgICAgIHByaW50KGYiICBbRVhDRVBD"
    "ScOTTiBQUlVFQkFdIEZ1ZW50ZXMgYnVzY2FkYXMgY29tbyB7U09VUkNFX0NPREVfT1ZFUlJJREV9IGVu"
    "IHZleiBkZSB7Y29kZX0iKQogICAgICAgIGNvZGUgPSBTT1VSQ0VfQ09ERV9PVkVSUklERQoKICAgIGRl"
    "ZiBmaW5kKG1tLCB5eXl5LCBsYWJlbCk6CiAgICAgICAgIyBNaXNtbyB0aXBvIChJTkQvQ09OU08pIHF1"
    "ZSBlbCBkZXN0aW5vLiBJbnRlbnRhIGFtYm9zIHNlcGFyYWRvcmVzLgogICAgICAgIGZvciBzZXAgaW4g"
    "WyItIiwgIl8iXToKICAgICAgICAgICAgbmFtZSA9IGYie2NvZGV9X3t0aXBvfV97bW19e3NlcH17eXl5"
    "eX1fe3N1ZmZpeH0iCiAgICAgICAgICAgIGZpZCAgPSBhbGxfZmlsZXMuZ2V0KG5hbWUpCiAgICAgICAg"
    "ICAgIGlmIGZpZDoKICAgICAgICAgICAgICAgIHByaW50KGYiICAgIOKckzoge25hbWV9IikKICAgICAg"
    "ICAgICAgICAgIHJldHVybiBmaWQKICAgICAgICBwcmludChmIiAgICDinJcgbm8gZW5jb250cmFkbzog"
    "e2NvZGV9X3t0aXBvfV97bW19LXt5eXl5fV97c3VmZml4fSIpCiAgICAgICAgcmV0dXJuIE5vbmUKCiAg"
    "ICBzb3VyY2VzID0ge30KICAgIG1tX2IsICB5eV9iICA9IGRhdGVfdG9fbW1feXl5eShiYXNlcy5nZXQo"
    "InByaW9yX2VuZCIsIiIpKQogICAgbW1fZSwgIHl5X2UgID0gZGF0ZV90b19tbV95eXl5KGJhc2VzLmdl"
    "dCgicHJpb3JfZWVycl9lbmQiLCIiKSkKICAgIG1tX3EsICB5eV9xICA9IGRhdGVfdG9fbW1feXl5eShi"
    "YXNlcy5nZXQoInByaW9yX3ByZXZfcGVyaW9kX2VuZCIsIiIpKQogICAgbW1fcHAsIHl5X3BwID0gZGF0"
    "ZV90b19tbV95eXl5KGJhc2VzLmdldCgicHJldl9wZXJpb2RfZW5kIiwiIikpCgogICAgaWYgbW1fYjoK"
    "ICAgICAgICBzb3VyY2VzWyJiYWxhbmNlIl0gPSBmaW5kKG1tX2IsIHl5X2IsIGYiQmFsYW5jZSBESUMt"
    "e3l5X2J9IikKICAgIGlmIG1tX2UgYW5kIChtbV9lLHl5X2UpICE9IChtbV9iLHl5X2IpOgogICAgICAg"
    "IHNvdXJjZXNbImVlcnIiXSA9IGZpbmQobW1fZSwgeXlfZSwgZiJFRVJSIHttbV9lfS17eXlfZX0iKQog"
    "ICAgZWxzZToKICAgICAgICBzb3VyY2VzWyJlZXJyIl0gPSBzb3VyY2VzLmdldCgiYmFsYW5jZSIpCiAg"
    "ICBpZiBtbV9xIGFuZCAobW1fcSx5eV9xKSBub3QgaW4gWyhtbV9iLHl5X2IpLChtbV9lLHl5X2UpXToK"
    "ICAgICAgICBzb3VyY2VzWyJxdWFydGVyX3ByZXYiXSA9IGZpbmQobW1fcSwgeXlfcSwgZiJRMS1wcmV2"
    "IHttbV9xfS17eXlfcX0iKQogICAgaWYgbW1fcHAgYW5kIHl5X3BwID09IHl5eXlfY3VyciBhbmQgbW1f"
    "cHAgIT0gbW1fY3VycjoKICAgICAgICBzb3VyY2VzWyJjdXJyX3N1YnBlcmlvZCJdID0gZmluZChtbV9w"
    "cCwgeXlfcHAsIGYiU3ViLXBlcsOtb2RvIGFjdHVhbCB7bW1fcHB9LXt5eV9wcH0iKQoKICAgIHJldHVy"
    "biBzb3VyY2VzCgojIOKUgOKUgOKUgCBQQVNPIDU6IENhcmdhciBkYXRvcyBkZSBmdWVudGVzIOKUgOKU"
    "gOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKU"
    "gOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgApk"
    "ZWYgbG9hZF9zb3VyY2VzKHNvdXJjZXMpOgogICAgbG9hZGVkID0ge30KICAgIGZvciBrZXksIGZpZCBp"
    "biBzb3VyY2VzLml0ZW1zKCk6CiAgICAgICAgaWYgbm90IGZpZCBvciBmaWQgaW4gbG9hZGVkOiBjb250"
    "aW51ZQogICAgICAgIHNoZWV0cyA9IGdldF9zaGVldHMoZmlkKQogICAgICAgIGxvYWRlZFtmaWRdID0g"
    "eyJzaGVldHMiOiBzaGVldHMsICJjZWxscyI6IHt9fQogICAgICAgIGZvciBzbmFtZSwgc2lkIGluIHNo"
    "ZWV0cy5pdGVtcygpOgogICAgICAgICAgICBsb2FkZWRbZmlkXVsiY2VsbHMiXVtzbmFtZV0gPSByZWFk"
    "X3NoZWV0KGZpZCwgc2lkKQogICAgICAgIHByaW50KGYiICAgIENhcmdhZG8gKHtrZXl9KToge2xlbihz"
    "aGVldHMpfSBob2phcyIpCiAgICByZXR1cm4gbG9hZGVkCgojIOKUgOKUgOKUgCBQQVNPIDY6IERldGVj"
    "dGFyIGNvbHVtbmFzIGEgbGxlbmFyIOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKU"
    "gOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKU"
    "gOKUgOKUgOKUgOKUgOKUgApQRVJJT0RfUEFUVEVSTlMgPSBbCiAgICAoInByaW9yX2VlcnJfc3RhcnQi"
    "LCAgICAicHJpb3JfZWVycl9lbmQiLCAgICAgICAgImVlcnIiKSwKICAgICgicHJpb3JfZWVycl9zdGFy"
    "dCIsICAgICJwcmlvcl9wcmV2X3BlcmlvZF9lbmQiLCAicXVhcnRlcl9wcmV2IiksCiAgICAoIiIsICAg"
    "ICAgICAgICAgICAgICAgICAicHJpb3JfZW5kIiwgICAgICAgICAgICAgImJhbGFuY2UiKSwKICAgICgi"
    "ZWVycl9zdGFydCIsICAgICAgICAgICJwcmV2X3BlcmlvZF9lbmQiLCAgICAgICAiY3Vycl9zdWJwZXJp"
    "b2QiKSwKXQoKZGVmIGRldGVjdF9jb21wX2NvbHMoY2VsbHMsIGJhc2VzKToKICAgIGNvbF90ZXh0cyA9"
    "IHt9CiAgICBmb3Igcm93IGluIGNlbGxzWzo4XToKICAgICAgICBmb3IgaiwgYyBpbiBlbnVtZXJhdGUo"
    "cm93KToKICAgICAgICAgICAgaWYgaXNpbnN0YW5jZShjLGRpY3QpOgogICAgICAgICAgICAgICAgZm9y"
    "IHZhbCBpbiBbc3RyKGMuZ2V0KCJjYWxjdWxhdGVkVmFsdWUiLCIiKSksIHN0cihjLmdldCgidmFsdWUi"
    "LCIiKSldOgogICAgICAgICAgICAgICAgICAgIGlmIHZhbCBhbmQgdmFsIG5vdCBpbiAoIk5vbmUiLCIi"
    "KToKICAgICAgICAgICAgICAgICAgICAgICAgY29sX3RleHRzLnNldGRlZmF1bHQoaixbXSkuYXBwZW5k"
    "KHZhbC5sb3dlcigpKQoKICAgIGRhdGVfZmllbGRzID0gewogICAgICAgICJwcmlvcl9lbmQiOiAgICAg"
    "ICAgICAgICBiYXNlcy5nZXQoInByaW9yX2VuZCIsIiIpLAogICAgICAgICJwcmlvcl9lZXJyX2VuZCI6"
    "ICAgICAgICBiYXNlcy5nZXQoInByaW9yX2VlcnJfZW5kIiwiIiksCiAgICAgICAgInByaW9yX2VlcnJf"
    "c3RhcnQiOiAgICAgIGJhc2VzLmdldCgicHJpb3JfZWVycl9zdGFydCIsIiIpLAogICAgICAgICJwcmlv"
    "cl9wcmV2X3BlcmlvZF9lbmQiOiBiYXNlcy5nZXQoInByaW9yX3ByZXZfcGVyaW9kX2VuZCIsIiIpLAog"
    "ICAgICAgICJwcmV2X3BlcmlvZF9lbmQiOiAgICAgICBiYXNlcy5nZXQoInByZXZfcGVyaW9kX2VuZCIs"
    "IiIpLAogICAgICAgICJlZXJyX3N0YXJ0IjogICAgICAgICAgICBiYXNlcy5nZXQoImVlcnJfc3RhcnQi"
    "LCIiKSwKICAgIH0KCiAgICByZXN1bHQgPSB7fQogICAgY3Vycl9lbmQgPSBiYXNlcy5nZXQoImN1cnJl"
    "bnRfZW5kIiwiX19YX18iKQogICAgZWVycl9lbmQgPSBiYXNlcy5nZXQoImVlcnJfZW5kIiwiX19YX18i"
    "KQoKICAgIGZvciBjb2xfaWR4LCB0ZXh0cyBpbiBjb2xfdGV4dHMuaXRlbXMoKToKICAgICAgICBjb21i"
    "aW5lZCA9ICIgIi5qb2luKHRleHRzKQogICAgICAgIGlmIGFueShrIGluIGNvbWJpbmVkIGZvciBrIGlu"
    "IFtjdXJyX2VuZCwgZWVycl9lbmQsICJxdWVyeSIsInN1bWlmIiwiYnBjIiwiYWN0dWFsIl0pOgogICAg"
    "ICAgICAgICBjb250aW51ZQogICAgICAgIGZvciBza3csIGVrdywgcGVyaW9kX2tleSBpbiBQRVJJT0Rf"
    "UEFUVEVSTlM6CiAgICAgICAgICAgIHNkID0gZGF0ZV9maWVsZHMuZ2V0KHNrdywgc2t3KS5sb3dlcigp"
    "CiAgICAgICAgICAgIGVkID0gZGF0ZV9maWVsZHMuZ2V0KGVrdywgZWt3KS5sb3dlcigpCiAgICAgICAg"
    "ICAgIGlmIChub3Qgc2Qgb3Igc2QgaW4gY29tYmluZWQpIGFuZCAoZWQgYW5kIGVkIGluIGNvbWJpbmVk"
    "KToKICAgICAgICAgICAgICAgIHJlc3VsdFtjb2xfaWR4XSA9IHBlcmlvZF9rZXkKICAgICAgICAgICAg"
    "ICAgIGJyZWFrCiAgICByZXR1cm4gcmVzdWx0CgojIOKUgOKUgOKUgCBQQVNPIDZiOiBEZXRlY2Npw7Nu"
    "IGRlIGJsb3F1ZXMgdmVydGljYWxlcyDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDi"
    "lIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIAK"
    "ZGVmIGRldGVjdF92ZXJ0aWNhbF9ibG9ja3MoY2VsbHMsIGJhc2VzKToKICAgICIiIgogICAgRGV0ZWN0"
    "YSBob2phcyBjb24gYmxvcXVlcyBhcGlsYWRvcyB2ZXJ0aWNhbG1lbnRlIChlai4gaG9qYXMgMTksIDIw"
    "KS4KICAgIEJ1c2NhIGVuIGNvbCBCIChpZHggMSkgVE9EQVMgbGFzIG9jdXJyZW5jaWFzIGRlIGN1cnJl"
    "bnRfZW5kIHkgcHJpb3JfZW5kLgogICAgUmV0b3JuYSBkaWN0IGNvbiBsaXN0YXMgZGUgb2N1cnJlbmNp"
    "YXMsIG8gTm9uZSBzaSBubyBoYXkgYmxvcXVlcyB2w6FsaWRvcy4KICAgICIiIgogICAgY3VyciAgPSBi"
    "YXNlcy5nZXQoImN1cnJlbnRfZW5kIiwgIiIpCiAgICBwcmlvciA9IGJhc2VzLmdldCgicHJpb3JfZW5k"
    "IiwgIiIpCiAgICBpZiBub3QgY3VyciBvciBub3QgcHJpb3I6CiAgICAgICAgcmV0dXJuIE5vbmUKICAg"
    "IGFjdHVhbF9yb3dzID0gW10KICAgIGNvbXBfcm93cyAgID0gW10KICAgIGZvciBpLCByb3cgaW4gZW51"
    "bWVyYXRlKGNlbGxzKToKICAgICAgICBjdiA9IHN0cihnZXRfY3Yocm93LCAxKSBvciAiIikuc3RyaXAo"
    "KQogICAgICAgIGlmIGN1cnIgaW4gY3Y6CiAgICAgICAgICAgIGFjdHVhbF9yb3dzLmFwcGVuZChpKQog"
    "ICAgICAgIGlmIHByaW9yIGluIGN2OgogICAgICAgICAgICBjb21wX3Jvd3MuYXBwZW5kKGkpCiAgICBp"
    "ZiBub3QgYWN0dWFsX3Jvd3Mgb3Igbm90IGNvbXBfcm93czoKICAgICAgICByZXR1cm4gTm9uZQogICAg"
    "aWYgY29tcF9yb3dzWzBdIDw9IGFjdHVhbF9yb3dzWzBdOgogICAgICAgIHJldHVybiBOb25lCiAgICBy"
    "ZXR1cm4gewogICAgICAgICJhY3R1YWxfc3RhcnQiOiBhY3R1YWxfcm93c1swXSwKICAgICAgICAiY29t"
    "cF9zdGFydCI6ICAgY29tcF9yb3dzWzBdLAogICAgICAgICJhY3R1YWxfcm93cyI6ICBhY3R1YWxfcm93"
    "cywKICAgICAgICAiY29tcF9yb3dzIjogICAgY29tcF9yb3dzLAogICAgfQoKZGVmIGZpbGxfdmVydGlj"
    "YWxfc2hlZXQodGFyZ2V0X2lkLCBzaWRfdCwgdGd0X2NlbGxzLCBzcmNfY2VsbHMsIGJsb2NrcywgYmFz"
    "ZXMpOgogICAgIiIiCiAgICBDb3BpYSBibG9xdWVzIGFjdHVhbGVzIGRlbCBmdWVudGUg4oaSIGJsb3F1"
    "ZXMgY29tcGFyYXRpdm9zIGRlbCB0YXJnZXQuCiAgICBQYXJlYXIgc3ViLWJsb3F1ZXMgcG9yIG9yZGVu"
    "IGRlIGFwYXJpY2nDs24gZGUgcHJpb3JfZW5kIGVuIGNvbCBCOgogICAgICBzcmNfYWN0dWFsX3Jvd3Nb"
    "aV0g4oaSIHRndF9jb21wX3Jvd3NbaV0KICAgIEVzdG8gbWFuZWphIGhvamFzIGNvbiBtw7psdGlwbGVz"
    "IHN1Yi1ibG9xdWVzIChlai4gaG9qYSAyMCBjb24gc2VnbWVudG9zKS4KICAgIFNvbG8gZXNjcmliZSBj"
    "ZWxkYXMgbnVtw6lyaWNhcyBuby1mw7NybXVsYSBkZWwgdGFyZ2V0LgogICAgIiIiCiAgICBwcmlvciA9"
    "IGJhc2VzLmdldCgicHJpb3JfZW5kIiwgIiIpCgogICAgIyBUb2RhcyBsYXMgb2N1cnJlbmNpYXMgZGUg"
    "cHJpb3JfZW5kIGVuIGNvbCBCIGRlbCBmdWVudGUKICAgIHNyY19hY3R1YWxfcm93cyA9IFtpIGZvciBp"
    "LCByb3cgaW4gZW51bWVyYXRlKHNyY19jZWxscykKICAgICAgICAgICAgICAgICAgICAgICBpZiBwcmlv"
    "ciBpbiBzdHIoZ2V0X2N2KHJvdywgMSkgb3IgIiIpLnN0cmlwKCldCiAgICBpZiBub3Qgc3JjX2FjdHVh"
    "bF9yb3dzOgogICAgICAgIHByaW50KCIgICAg4oaSIEJsb3F1ZSBhY3R1YWwgbm8gZW5jb250cmFkbyBl"
    "biBmdWVudGUiKQogICAgICAgIHJldHVybiAwCgogICAgdGd0X2NvbXBfcm93cyA9IGJsb2Nrcy5nZXQo"
    "ImNvbXBfcm93cyIsIFtibG9ja3NbImNvbXBfc3RhcnQiXV0pCiAgICBuX2Jsb2NrcyA9IG1pbihsZW4o"
    "c3JjX2FjdHVhbF9yb3dzKSwgbGVuKHRndF9jb21wX3Jvd3MpKQoKICAgICMgQ29uc3RydWlyIG1hcGEg"
    "Y29sIOKGkiB7dGd0X3JvdzogdmFsdWV9IHBhcmEgdG9kb3MgbG9zIHN1Yi1ibG9xdWVzCiAgICB3cml0"
    "ZV9tYXAgPSB7fSAgICMgY29sX2lkeCDihpIge3RndF9yb3dfaWR4OiB2YWx1ZX0KICAgIGZvciBiIGlu"
    "IHJhbmdlKG5fYmxvY2tzKToKICAgICAgICBzcmNfc3RhcnQgPSBzcmNfYWN0dWFsX3Jvd3NbYl0KICAg"
    "ICAgICB0Z3Rfc3RhcnQgPSB0Z3RfY29tcF9yb3dzW2JdCiAgICAgICAgc3JjX2VuZCAgID0gc3JjX2Fj"
    "dHVhbF9yb3dzW2IrMV0gaWYgYisxIDwgbGVuKHNyY19hY3R1YWxfcm93cykgZWxzZSBsZW4oc3JjX2Nl"
    "bGxzKQogICAgICAgIHRndF9lbmQgICA9IHRndF9jb21wX3Jvd3NbYisxXSAgIGlmIGIrMSA8IGxlbih0"
    "Z3RfY29tcF9yb3dzKSAgIGVsc2UgbGVuKHRndF9jZWxscykKICAgICAgICBibG9ja19oICAgPSBtaW4o"
    "c3JjX2VuZCAtIHNyY19zdGFydCwgdGd0X2VuZCAtIHRndF9zdGFydCkKCiAgICAgICAgZm9yIG9mZnNl"
    "dCBpbiByYW5nZShibG9ja19oKToKICAgICAgICAgICAgc2kgPSBzcmNfc3RhcnQgKyBvZmZzZXQKICAg"
    "ICAgICAgICAgdGkgPSB0Z3Rfc3RhcnQgKyBvZmZzZXQKICAgICAgICAgICAgaWYgc2kgPj0gbGVuKHNy"
    "Y19jZWxscykgb3IgdGkgPj0gbGVuKHRndF9jZWxscyk6CiAgICAgICAgICAgICAgICBicmVhawogICAg"
    "ICAgICAgICByb3dfc3JjID0gc3JjX2NlbGxzW3NpXQogICAgICAgICAgICByb3dfdGd0ID0gdGd0X2Nl"
    "bGxzW3RpXQogICAgICAgICAgICBmb3IgY29sIGluIHJhbmdlKG1heChsZW4ocm93X3NyYyksIGxlbihy"
    "b3dfdGd0KSkpOgogICAgICAgICAgICAgICAgaWYgaXNfZm9ybXVsYShyb3dfdGd0LCBjb2wpOgogICAg"
    "ICAgICAgICAgICAgICAgIGNvbnRpbnVlCiAgICAgICAgICAgICAgICB2YWwgPSBnZXRfY3Yocm93X3Ny"
    "YywgY29sKQogICAgICAgICAgICAgICAgaWYgbm90IGlzaW5zdGFuY2UodmFsLCAoaW50LCBmbG9hdCkp"
    "OgogICAgICAgICAgICAgICAgICAgIGNvbnRpbnVlCiAgICAgICAgICAgICAgICB3cml0ZV9tYXAuc2V0"
    "ZGVmYXVsdChjb2wsIHt9KVt0aV0gPSB2YWwKCiAgICAjIEVzY3JpYmlyIGNvbHVtbmEgYSBjb2x1bW5h"
    "IGNvbiB1biBzb2xvIHB1dF9jb2xfcmFuZ2UgcG9yIGNvbHVtbmEKICAgIHdyaXR0ZW4gPSAwCiAgICBm"
    "b3IgY29sX2lkeCwgcm93X3ZhbHMgaW4gc29ydGVkKHdyaXRlX21hcC5pdGVtcygpKToKICAgICAgICBp"
    "ZiBub3Qgcm93X3ZhbHM6CiAgICAgICAgICAgIGNvbnRpbnVlCiAgICAgICAgbWluX3JvdyA9IG1pbihy"
    "b3dfdmFscykKICAgICAgICBtYXhfcm93ID0gbWF4KHJvd192YWxzKQogICAgICAgIHZhbHVlcyAgPSBb"
    "cm93X3ZhbHMuZ2V0KGkpIGZvciBpIGluIHJhbmdlKG1pbl9yb3csIG1heF9yb3cgKyAxKV0KICAgICAg"
    "ICBpZiBhbGwodiBpcyBOb25lIGZvciB2IGluIHZhbHVlcyk6CiAgICAgICAgICAgIGNvbnRpbnVlCiAg"
    "ICAgICAgb2sgPSBwdXRfY29sX3JhbmdlKHRhcmdldF9pZCwgc2lkX3QsIGNvbF9pZHgsIG1pbl9yb3cs"
    "IHZhbHVlcywgInZlcnRpY2FsIikKICAgICAgICBpZiBvazoKICAgICAgICAgICAgd3JpdHRlbiArPSAx"
    "CiAgICAgICAgdGltZS5zbGVlcCgwLjIpCiAgICByZXR1cm4gd3JpdHRlbgoKIyDilIDilIDilIAgUEFT"
    "TyA3OiBPZmZzZXQgeSBtYXBlbyBkZSBmaWxhcyDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDi"
    "lIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDi"
    "lIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIAKZGVmIGZpbmRfb2Zmc2V0KHRndF9jZWxscywg"
    "c3JjX2NlbGxzLCBkYXRlX2t3KToKICAgIHRndF9jb2wgPSBzcmNfY29sID0gTm9uZQogICAga3cgPSBz"
    "dHIoZGF0ZV9rdykubG93ZXIoKSBpZiBkYXRlX2t3IGVsc2UgIiIKICAgIGZvciByb3cgaW4gdGd0X2Nl"
    "bGxzWzo4XToKICAgICAgICBmb3IgaiwgYyBpbiBlbnVtZXJhdGUocm93KToKICAgICAgICAgICAgaWYg"
    "aXNpbnN0YW5jZShjLGRpY3QpIGFuZCBrdyBhbmQga3cgaW4gc3RyKGMuZ2V0KCJjYWxjdWxhdGVkVmFs"
    "dWUiLCIiKSkubG93ZXIoKToKICAgICAgICAgICAgICAgIGlmIHRndF9jb2wgaXMgTm9uZTogdGd0X2Nv"
    "bCA9IGoKICAgIGZvciByb3cgaW4gc3JjX2NlbGxzWzo4XToKICAgICAgICBmb3IgaiwgYyBpbiBlbnVt"
    "ZXJhdGUocm93KToKICAgICAgICAgICAgaWYgaXNpbnN0YW5jZShjLGRpY3QpIGFuZCBrdyBhbmQga3cg"
    "aW4gc3RyKGMuZ2V0KCJjYWxjdWxhdGVkVmFsdWUiLCIiKSkubG93ZXIoKToKICAgICAgICAgICAgICAg"
    "IGlmIHNyY19jb2wgaXMgTm9uZTogc3JjX2NvbCA9IGoKICAgIGlmIHRndF9jb2wgaXMgbm90IE5vbmUg"
    "YW5kIHNyY19jb2wgaXMgbm90IE5vbmU6IHJldHVybiB0Z3RfY29sIC0gc3JjX2NvbAogICAgcmV0dXJu"
    "IDIKCmRlZiBmaW5kX2JwY19jb2woc3JjX2NlbGxzLCB0Z3RfY2VsbHMpOgogICAgIiIiCiAgICBEZXRl"
    "Y3RhIGxhIGNvbHVtbmEgcXVlIGNvbnRpZW5lIGVsIGPDs2RpZ28gQlBDICgnQWdydXBhZG9yIEJQQycg"
    "LyAnQWdydXBhZG9yJykuCiAgICBCdXNjYSBlbiBsYXMgcHJpbWVyYXMgOCBmaWxhcyB1biBoZWFkZXIg"
    "cXVlIGRpZ2EgJ2FncnVwYWRvcicuCiAgICBSZXRvcm5hIGVsIMOtbmRpY2UgZGUgY29sdW1uYSwgbyBO"
    "b25lIHNpIG5vIGV4aXN0ZS4KICAgICIiIgogICAgZm9yIGNlbGxzIGluIChzcmNfY2VsbHMsIHRndF9j"
    "ZWxscyk6CiAgICAgICAgZm9yIHJvdyBpbiBjZWxsc1s6OF06CiAgICAgICAgICAgIGZvciBqLCBjIGlu"
    "IGVudW1lcmF0ZShyb3cpOgogICAgICAgICAgICAgICAgaWYgaXNpbnN0YW5jZShjLCBkaWN0KToKICAg"
    "ICAgICAgICAgICAgICAgICBjdiA9IHN0cihjLmdldCgiY2FsY3VsYXRlZFZhbHVlIiwiIikpLmxvd2Vy"
    "KCkKICAgICAgICAgICAgICAgICAgICBpZiAiYWdydXBhZG9yIiBpbiBjdjoKICAgICAgICAgICAgICAg"
    "ICAgICAgICAgcmV0dXJuIGoKICAgIHJldHVybiBOb25lCgpkZWYgYnVpbGRfcm93X21hcHBpbmcodGd0"
    "X2NlbGxzLCBzcmNfY2VsbHMpOgogICAgIiIiCiAgICBNYXBlbyBkZSBmaWxhcyB0YXJnZXQg4oaSIHNv"
    "dXJjZSBiYXNhZG8gZW4gQU5DTEFTLgogICAgRnVuY2lvbmEgY29uIGRpZmYgZW4gY3VhbHF1aWVyIHNl"
    "bnRpZG8gKHRhcmdldCBjb24gbcOhcyBvIG1lbm9zIGZpbGFzKS4KCiAgICBFc3RyYXRlZ2lhOgogICAg"
    "ICAxLiBTaSBkaWZmPT0wOiBtYXBlbyBkaXJlY3RvIDE6MSAoY2FzbyBtw6FzIGNvbcO6biB5IHNlZ3Vy"
    "bykuCiAgICAgIDIuIFNpIGRpZmYhPTA6CiAgICAgICAgIGEuIEFuY2xhcyA9IGZpbGFzIGNvbiBCUEMg"
    "Y29pbmNpZGVudGUgbyBldGlxdWV0YSAoY29sIEIpIGlkw6ludGljYSwKICAgICAgICAgICAgY29uIMOt"
    "bmRpY2UgZGUgc291cmNlIGVzdHJpY3RhbWVudGUgY3JlY2llbnRlLgogICAgICAgICBiLiBGaWxhcyBh"
    "bmNsYWRhcyDihpIgc3UgYW5jbGEuCiAgICAgICAgIGMuIEZpbGFzIE5PIHZhY8OtYXMgZW50cmUgYW5j"
    "bGFzIOKGkiBpbnRlcnBvbGFjacOzbiBwb3NpY2lvbmFsLgogICAgICAgICBkLiBGaWxhcyBWQUPDjUFT"
    "IChzaW4gZXRpcXVldGEgbmkgQlBDKSDihpIgTm9uZSBTSUVNUFJFIChubyByZWNpYmVuIHZhbG9yKS4K"
    "ICAgICIiIgogICAgZGlmZiA9IGxlbih0Z3RfY2VsbHMpIC0gbGVuKHNyY19jZWxscykKICAgIGlmIGRp"
    "ZmYgPT0gMDoKICAgICAgICByZXR1cm4gbGlzdChyYW5nZShsZW4odGd0X2NlbGxzKSkpCgogICAgYnBj"
    "X2NvbCA9IGZpbmRfYnBjX2NvbChzcmNfY2VsbHMsIHRndF9jZWxscykKCiAgICBkZWYgbGJsKHJvdyk6"
    "IHJldHVybiBzdHIoZ2V0X2N2KHJvdywgMSkgb3IgIiIpLnN0cmlwKCkKICAgIGRlZiBicGMocm93KToK"
    "ICAgICAgICBpZiBicGNfY29sIGlzIE5vbmU6IHJldHVybiBOb25lCiAgICAgICAgYiA9IGdldF9jdihy"
    "b3csIGJwY19jb2wpCiAgICAgICAgcmV0dXJuIHN0cihiKSBpZiBiIGlzIG5vdCBOb25lIGFuZCBzdHIo"
    "Yikuc3RyaXAoKSBlbHNlIE5vbmUKCiAgICAjIExvb2t1cHMgZGVsIHNvdXJjZQogICAgc3JjX2JwYyA9"
    "IHt9CiAgICBmb3IgaSwgciBpbiBlbnVtZXJhdGUoc3JjX2NlbGxzKToKICAgICAgICBiID0gYnBjKHIp"
    "CiAgICAgICAgaWYgYjogc3JjX2JwYy5zZXRkZWZhdWx0KGIsIGkpCiAgICBzcmNfbGJsID0ge30KICAg"
    "IGZvciBpLCByIGluIGVudW1lcmF0ZShzcmNfY2VsbHMpOgogICAgICAgIGwgPSBsYmwocikKICAgICAg"
    "ICBpZiBsOiBzcmNfbGJsLnNldGRlZmF1bHQobCwgW10pLmFwcGVuZChpKQoKICAgICMgMS4gRGV0ZWN0"
    "YXIgYW5jbGFzIChzcmNfaWR4IGVzdHJpY3RhbWVudGUgY3JlY2llbnRlKQogICAgYW5jaG9ycyA9IFtd"
    "CiAgICB1c2VkID0gc2V0KCkKICAgIGxhc3Rfc3JjID0gLTEKICAgIGZvciB0aSwgcnQgaW4gZW51bWVy"
    "YXRlKHRndF9jZWxscyk6CiAgICAgICAgc2kgPSBOb25lCiAgICAgICAgYiA9IGJwYyhydCkKICAgICAg"
    "ICBpZiBiIGFuZCBiIGluIHNyY19icGMgYW5kIHNyY19icGNbYl0gPiBsYXN0X3NyYyBhbmQgc3JjX2Jw"
    "Y1tiXSBub3QgaW4gdXNlZDoKICAgICAgICAgICAgc2kgPSBzcmNfYnBjW2JdCiAgICAgICAgZWxzZToK"
    "ICAgICAgICAgICAgbCA9IGxibChydCkKICAgICAgICAgICAgaWYgbCBhbmQgbCBpbiBzcmNfbGJsOgog"
    "ICAgICAgICAgICAgICAgZm9yIGNhbmQgaW4gc3JjX2xibFtsXToKICAgICAgICAgICAgICAgICAgICBp"
    "ZiBjYW5kID4gbGFzdF9zcmMgYW5kIGNhbmQgbm90IGluIHVzZWQ6CiAgICAgICAgICAgICAgICAgICAg"
    "ICAgIHNpID0gY2FuZDsgYnJlYWsKICAgICAgICBpZiBzaSBpcyBub3QgTm9uZToKICAgICAgICAgICAg"
    "YW5jaG9ycy5hcHBlbmQoKHRpLCBzaSkpCiAgICAgICAgICAgIHVzZWQuYWRkKHNpKTsgbGFzdF9zcmMg"
    "PSBzaQoKICAgIG1hcHBpbmcgPSBbTm9uZV0gKiBsZW4odGd0X2NlbGxzKQogICAgZm9yIHRpLCBzaSBp"
    "biBhbmNob3JzOgogICAgICAgIG1hcHBpbmdbdGldID0gc2kKCiAgICAjIDIuIEludGVycG9sYWNpw7Nu"
    "IHBvc2ljaW9uYWwgZW50cmUgYW5jbGFzIOKAlCBzb2xvIGZpbGFzIE5PIHZhY8OtYXMKICAgIGZvciBr"
    "IGluIHJhbmdlKGxlbihhbmNob3JzKSAtIDEpOgogICAgICAgIHQwLCBzMCA9IGFuY2hvcnNba10KICAg"
    "ICAgICB0MSwgczEgPSBhbmNob3JzW2sgKyAxXQogICAgICAgIGZvciB0aSBpbiByYW5nZSh0MCArIDEs"
    "IHQxKToKICAgICAgICAgICAgaWYgbm90IGxibCh0Z3RfY2VsbHNbdGldKToKICAgICAgICAgICAgICAg"
    "IGNvbnRpbnVlICAjIGZpbGEgdmFjw61hIOKGkiBOb25lCiAgICAgICAgICAgIHNpID0gczAgKyAodGkg"
    "LSB0MCkKICAgICAgICAgICAgaWYgczAgPCBzaSA8IHMxOgogICAgICAgICAgICAgICAgbWFwcGluZ1t0"
    "aV0gPSBzaQoKICAgIHJldHVybiBtYXBwaW5nCgpkZWYgYnVpbGRfd3JpdGVfdmFsdWVzKHRndF9jZWxs"
    "cywgc3JjX2NlbGxzLCBkZXN0X2NvbCwgc3JjX2NvbCk6CiAgICByb3dfbWFwID0gYnVpbGRfcm93X21h"
    "cHBpbmcodGd0X2NlbGxzLCBzcmNfY2VsbHMpCiAgICBicGNfY29sID0gZmluZF9icGNfY29sKHNyY19j"
    "ZWxscywgdGd0X2NlbGxzKQoKICAgIGRlZiBpc19kYXRhX3Jvdyhyb3cpOgogICAgICAgICIiIlVuYSBm"
    "aWxhIHJlY2liZSB2YWxvciBzb2xvIHNpIHRpZW5lIGV0aXF1ZXRhIChjb2wgQikgbyBjw7NkaWdvIEJQ"
    "Qy4KICAgICAgICBMYXMgZmlsYXMgZXN0cnVjdHVyYWxtZW50ZSB2YWPDrWFzIChoZWxwZXJzL2N1YWRy"
    "YWplcyBzaW4gbGFiZWwpIHNlIHNhbHRhbi4iIiIKICAgICAgICBpZiBzdHIoZ2V0X2N2KHJvdywgMSkg"
    "b3IgIiIpLnN0cmlwKCk6CiAgICAgICAgICAgIHJldHVybiBUcnVlCiAgICAgICAgaWYgYnBjX2NvbCBp"
    "cyBub3QgTm9uZSBhbmQgZ2V0X2N2KHJvdywgYnBjX2NvbCkgbm90IGluIChOb25lLCAiIik6CiAgICAg"
    "ICAgICAgIHJldHVybiBUcnVlCiAgICAgICAgcmV0dXJuIEZhbHNlCgogICAgdmFscyA9IFtdCiAgICBm"
    "b3IgaSBpbiByYW5nZShsZW4odGd0X2NlbGxzKSk6CiAgICAgICAgcm93X3QgPSB0Z3RfY2VsbHNbaV0g"
    "aWYgaSA8IGxlbih0Z3RfY2VsbHMpIGVsc2UgW10KICAgICAgICBpZiBpc19mb3JtdWxhKHJvd190LCBk"
    "ZXN0X2NvbCk6CiAgICAgICAgICAgIHZhbHMuYXBwZW5kKE5vbmUpOyBjb250aW51ZQogICAgICAgIGlm"
    "IG5vdCBpc19kYXRhX3Jvdyhyb3dfdCk6ICAgICAgICAgICMgZmlsYSB2YWPDrWEg4oaSIG51bmNhIHJl"
    "Y2liZSB2YWxvcgogICAgICAgICAgICB2YWxzLmFwcGVuZChOb25lKTsgY29udGludWUKICAgICAgICBz"
    "cmNfcm93ID0gcm93X21hcFtpXQogICAgICAgIGlmIHNyY19yb3cgaXMgTm9uZTogdmFscy5hcHBlbmQo"
    "Tm9uZSk7IGNvbnRpbnVlCiAgICAgICAgc3YgPSBnZXRfY3Yoc3JjX2NlbGxzW3NyY19yb3ddLCBzcmNf"
    "Y29sKQogICAgICAgIHZhbHMuYXBwZW5kKHN2IGlmIGlzaW5zdGFuY2Uoc3YsKGludCxmbG9hdCkpIGVs"
    "c2UgTm9uZSkKICAgIHJldHVybiB2YWxzCgojIOKUgOKUgOKUgCBQQVNPIDg6IENvcGlhIGRlIGhvamEg"
    "dGlwbyA3OSDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDi"
    "lIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDi"
    "lIDilIDilIDilIDilIDilIAKZGVmIGNvcHlfZGV0YWlsX3NoZWV0KHRhcmdldF9pZCwgdGd0X3NpZCwg"
    "c3JjX2NlbGxzLCB0Z3RfY2VsbHMpOgogICAgY29scyA9IHtqIGZvciByb3cgaW4gc3JjX2NlbGxzIGZv"
    "ciBqLGMgaW4gZW51bWVyYXRlKHJvdykKICAgICAgICAgICAgaWYgaXNpbnN0YW5jZShjLGRpY3QpIGFu"
    "ZCBub3QgaXNfZm9ybXVsYShyb3csaikKICAgICAgICAgICAgYW5kIGMuZ2V0KCJjYWxjdWxhdGVkVmFs"
    "dWUiKSBub3QgaW4gKE5vbmUsIiIsMCl9CiAgICBvayA9IDAKICAgIGZvciBjb2xfaWR4IGluIHNvcnRl"
    "ZChjb2xzKToKICAgICAgICB3ICAgPSBbXQogICAgICAgIGhhcyA9IEZhbHNlCiAgICAgICAgZm9yIGkg"
    "aW4gcmFuZ2UobGVuKHRndF9jZWxscykpOgogICAgICAgICAgICBycyA9IHNyY19jZWxsc1tpXSBpZiBp"
    "IDwgbGVuKHNyY19jZWxscykgZWxzZSBbXQogICAgICAgICAgICBydCA9IHRndF9jZWxsc1tpXSBpZiBp"
    "IDwgbGVuKHRndF9jZWxscykgZWxzZSBbXQogICAgICAgICAgICBpZiBpc19mb3JtdWxhKHJ0LCBjb2xf"
    "aWR4KSBvciBpc19mb3JtdWxhKHJzLCBjb2xfaWR4KToKICAgICAgICAgICAgICAgIHcuYXBwZW5kKE5v"
    "bmUpOyBjb250aW51ZQogICAgICAgICAgICBjdiA9IChyc1tjb2xfaWR4XSBpZiBjb2xfaWR4IDwgbGVu"
    "KHJzKSBlbHNlIHt9KQogICAgICAgICAgICBjdiA9IGN2LmdldCgiY2FsY3VsYXRlZFZhbHVlIikgaWYg"
    "aXNpbnN0YW5jZShjdixkaWN0KSBlbHNlIE5vbmUKICAgICAgICAgICAgdy5hcHBlbmQoY3YgaWYgY3Yg"
    "bm90IGluIChOb25lLCIiKSBlbHNlIE5vbmUpCiAgICAgICAgICAgIGlmIGN2IG5vdCBpbiAoTm9uZSwi"
    "IiwwKTogaGFzID0gVHJ1ZQogICAgICAgIGlmIG5vdCBoYXM6IGNvbnRpbnVlCiAgICAgICAgd2hpbGUg"
    "bGVuKHcpIDwgbGVuKHRndF9jZWxscyk6IHcuYXBwZW5kKE5vbmUpCiAgICAgICAgY2wgPSBjb2xfbGV0"
    "dGVyKGNvbF9pZHgpCiAgICAgICAgcnAgPSBzZXNzaW9uLnB1dChXREVTS19CQVNFKyIvcGxhdGZvcm0v"
    "djEvc3ByZWFkc2hlZXRzLyIrdGFyZ2V0X2lkKyIvc2hlZXRzLyIrdGd0X3NpZAogICAgICAgICAgICAg"
    "ICAgICAgICAgICAgKyIvdmFsdWVzLyIrZiJ7Y2x9MTp7Y2x9e2xlbih3KX0iLAogICAgICAgICAgICAg"
    "ICAgICAgICAgICAganNvbj17InZhbHVlcyI6W1t2XSBmb3IgdiBpbiB3XX0sIHRpbWVvdXQ9MTIwKQog"
    "ICAgICAgIGlmIHJwLnN0YXR1c19jb2RlID09IDIwMiBhbmQgcG9sbChycC5oZWFkZXJzLmdldCgiTG9j"
    "YXRpb24iLCIiKSk6IG9rICs9IDEKICAgICAgICB0aW1lLnNsZWVwKDAuMikKICAgIHByaW50KGYiICAg"
    "IHtva30gY29sdW1uYXMgY29waWFkYXMiKQoKZGVmIGNvcHlfYmxvY2tfc2hlZXQodGFyZ2V0X2lkLCB0"
    "Z3Rfc2lkLCBzcmNfY2VsbHMsIHRndF9jZWxscywgc3JjX3N0YXJ0LCBzcmNfZW5kLCB0Z3Rfc3RhcnQs"
    "IHRndF9lbmQpOgogICAgIiIiCiAgICBDb3BpYSB1biByYW5nbyBkZSBmaWxhcyBkZWwgZnVlbnRlIGFs"
    "IHRhcmdldCAoYmxvcXVlIGEgYmxvcXVlLCDDrW5kaWNlcyBiYXNlLTApLgogICAgU29sbyBlc2NyaWJl"
    "IGNlbGRhcyBudW3DqXJpY2FzIG5vLWbDs3JtdWxhIGVuIGVsIHRhcmdldC4KICAgIEFncnVwYSBwb3Ig"
    "Y29sdW1uYSB5IHVzYSBwdXRfY29sX3JhbmdlIHBhcmEgbWluaW1pemFyIGxsYW1hZGFzIGEgbGEgQVBJ"
    "LgogICAgIiIiCiAgICBibG9ja19oID0gbWluKHNyY19lbmQgLSBzcmNfc3RhcnQsIHRndF9lbmQgLSB0"
    "Z3Rfc3RhcnQpCiAgICB3cml0ZV9tYXAgPSB7fSAgICMgY29sX2lkeCDihpIge3RndF9yb3dfaWR4OiB2"
    "YWx1ZX0KCiAgICBmb3Igb2Zmc2V0IGluIHJhbmdlKGJsb2NrX2gpOgogICAgICAgIHNpID0gc3JjX3N0"
    "YXJ0ICsgb2Zmc2V0CiAgICAgICAgdGkgPSB0Z3Rfc3RhcnQgKyBvZmZzZXQKICAgICAgICBpZiBzaSA+"
    "PSBsZW4oc3JjX2NlbGxzKSBvciB0aSA+PSBsZW4odGd0X2NlbGxzKToKICAgICAgICAgICAgYnJlYWsK"
    "ICAgICAgICByb3dfc3JjID0gc3JjX2NlbGxzW3NpXQogICAgICAgIHJvd190Z3QgPSB0Z3RfY2VsbHNb"
    "dGldCiAgICAgICAgZm9yIGNvbCBpbiByYW5nZShtYXgobGVuKHJvd19zcmMpLCBsZW4ocm93X3RndCkp"
    "KToKICAgICAgICAgICAgaWYgaXNfZm9ybXVsYShyb3dfdGd0LCBjb2wpOgogICAgICAgICAgICAgICAg"
    "Y29udGludWUKICAgICAgICAgICAgdmFsID0gZ2V0X2N2KHJvd19zcmMsIGNvbCkKICAgICAgICAgICAg"
    "aWYgbm90IGlzaW5zdGFuY2UodmFsLCAoaW50LCBmbG9hdCkpOgogICAgICAgICAgICAgICAgY29udGlu"
    "dWUKICAgICAgICAgICAgd3JpdGVfbWFwLnNldGRlZmF1bHQoY29sLCB7fSlbdGldID0gdmFsCgogICAg"
    "d3JpdHRlbiA9IDAKICAgIGZvciBjb2xfaWR4LCByb3dfdmFscyBpbiBzb3J0ZWQod3JpdGVfbWFwLml0"
    "ZW1zKCkpOgogICAgICAgIGlmIG5vdCByb3dfdmFsczoKICAgICAgICAgICAgY29udGludWUKICAgICAg"
    "ICBtaW5fcm93ID0gbWluKHJvd192YWxzKQogICAgICAgIG1heF9yb3cgPSBtYXgocm93X3ZhbHMpCiAg"
    "ICAgICAgdmFsdWVzICA9IFtyb3dfdmFscy5nZXQoaSkgZm9yIGkgaW4gcmFuZ2UobWluX3JvdywgbWF4"
    "X3JvdyArIDEpXQogICAgICAgIGlmIGFsbCh2IGlzIE5vbmUgZm9yIHYgaW4gdmFsdWVzKToKICAgICAg"
    "ICAgICAgY29udGludWUKICAgICAgICBvayA9IHB1dF9jb2xfcmFuZ2UodGFyZ2V0X2lkLCB0Z3Rfc2lk"
    "LCBjb2xfaWR4LCBtaW5fcm93LCB2YWx1ZXMsICJibG9jayIpCiAgICAgICAgaWYgb2s6CiAgICAgICAg"
    "ICAgIHdyaXR0ZW4gKz0gMQogICAgICAgIHRpbWUuc2xlZXAoMC4yKQogICAgcHJpbnQoZiIgICAge3dy"
    "aXR0ZW59IGNvbHVtbmFzIGVzY3JpdGFzIikKCiMg4pSA4pSA4pSAIFBST0NFU0FSIFVOIEFSQ0hJVk8g"
    "4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA"
    "4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA"
    "4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSACmRlZiBwcm9jZXNzX2ZpbGUo"
    "dGFyZ2V0X2luZm8sIGFsbF9maWxlcyk6CiAgICBmaWQgICAgPSB0YXJnZXRfaW5mb1siaWQiXQogICAg"
    "bmFtZSAgID0gdGFyZ2V0X2luZm9bIm5hbWUiXQogICAgcGFyc2VkID0gdGFyZ2V0X2luZm8KCiAgICBw"
    "cmludChmIlxueyfilIAnKjYwfSIpCiAgICBwcmludChmIlByb2Nlc2FuZG86IHtuYW1lfSIpCiAgICBw"
    "cmludChmInsn4pSAJyo2MH0iKQoKICAgICMgSG9qYXMgZGVsIHRhcmdldAogICAgdGd0X3NoZWV0cyA9"
    "IGdldF9zaGVldHMoZmlkKQogICAgaWYgIkJhc2VzIiBub3QgaW4gdGd0X3NoZWV0czoKICAgICAgICBw"
    "cmludCgiICDinJcgU2luIGhvamEgQmFzZXMg4oCUIHNhbHRhbmRvIikKICAgICAgICByZXR1cm4gMCwg"
    "MAoKICAgICMgQmFzZXMKICAgIGJhc2VzID0gcmVhZF9iYXNlcyhmaWQsIHRndF9zaGVldHMpCiAgICBw"
    "cmludChmIiAgUGVyw61vZG86IHtiYXNlcy5nZXQoJ2N1cnJlbnRfZW5kJywnPycpfSB8IENvbXBhcjog"
    "e2Jhc2VzLmdldCgncHJpb3JfZW5kJywnPycpfSIpCgogICAgIyBGdWVudGVzCiAgICBzb3VyY2VzID0g"
    "ZmluZF9zb3VyY2VfZmlsZXMocGFyc2VkLCBiYXNlcywgYWxsX2ZpbGVzKQoKICAgICMgQ2FyZ2FyIGZ1"
    "ZW50ZXMKICAgIHByaW50KCIgIENhcmdhbmRvIGZ1ZW50ZXMuLi4iKQogICAgbG9hZGVkID0gbG9hZF9z"
    "b3VyY2VzKHNvdXJjZXMpCgogICAgcGVyaW9kX3JlZiA9IHsKICAgICAgICAiYmFsYW5jZSI6ICAgICAg"
    "ICBiYXNlcy5nZXQoInByaW9yX2VuZCIsIiIpLAogICAgICAgICJlZXJyIjogICAgICAgICAgIGJhc2Vz"
    "LmdldCgicHJpb3JfZWVycl9lbmQiLCIiKSwKICAgICAgICAicXVhcnRlcl9wcmV2IjogICBiYXNlcy5n"
    "ZXQoInByaW9yX3ByZXZfcGVyaW9kX2VuZCIsIiIpLAogICAgICAgICJjdXJyX3N1YnBlcmlvZCI6IGJh"
    "c2VzLmdldCgicHJldl9wZXJpb2RfZW5kIiwiIiksCiAgICB9CgogICAgZGVmIGdldF9zcmMoa2V5KToK"
    "ICAgICAgICBmaWQyID0gc291cmNlcy5nZXQoa2V5KQogICAgICAgIGlmIG5vdCBmaWQyIG9yIGZpZDIg"
    "bm90IGluIGxvYWRlZDogcmV0dXJuIE5vbmUsIHt9CiAgICAgICAgcmV0dXJuIGZpZDIsIGxvYWRlZFtm"
    "aWQyXVsiY2VsbHMiXQoKICAgIHRvX3Byb2Nlc3MgPSB7bjpzaWQgZm9yIG4sc2lkIGluIHRndF9zaGVl"
    "dHMuaXRlbXMoKSBpZiBuIG5vdCBpbiBTS0lQX1NIRUVUU30KICAgIG9rX3RvdGFsID0gZXJyX3RvdGFs"
    "ID0gMAoKICAgIGZvciBzbmFtZSwgc2lkX3QgaW4gdG9fcHJvY2Vzcy5pdGVtcygpOgogICAgICAgIHJl"
    "ZnJlc2hfdG9rZW4oKQoKICAgICAgICAjIENvcGlhIGRlIGhvamEgdGlwbyA3OQogICAgICAgIGlmIHNu"
    "YW1lIGluIEZVTExfQ09QWV9QQUlSUzoKICAgICAgICAgICAgc3JjX25hbWUgPSBGVUxMX0NPUFlfUEFJ"
    "UlNbc25hbWVdCiAgICAgICAgICAgIF8sIGNtYXAgID0gZ2V0X3NyYygiYmFsYW5jZSIpCiAgICAgICAg"
    "ICAgIHNyY19jICAgID0gY21hcC5nZXQoc3JjX25hbWUsIFtdKQogICAgICAgICAgICB0Z3RfYyAgICA9"
    "IHJlYWRfc2hlZXQoZmlkLCBzaWRfdCkKICAgICAgICAgICAgcHJpbnQoZiIgIFtDT1BJQV0ge3NuYW1l"
    "fSIpCiAgICAgICAgICAgIGlmIHNyY19jOiBjb3B5X2RldGFpbF9zaGVldChmaWQsIHNpZF90LCBzcmNf"
    "YywgdGd0X2MpCiAgICAgICAgICAgIGVsc2U6ICAgICBwcmludCgiICAgIOKGkiBGdWVudGUgbm8gZW5j"
    "b250cmFkYSIpCiAgICAgICAgICAgIGNvbnRpbnVlCgogICAgICAgICMgQ29waWEgZGUgYmxvcXVlIGZp"
    "am8gKGVqLiBob2phIDYwKQogICAgICAgIGlmIHNuYW1lIGluIEJMT0NLX0NPUFlfU0hFRVRTOgogICAg"
    "ICAgICAgICBzcywgc2UsIHRzLCB0ZSA9IEJMT0NLX0NPUFlfU0hFRVRTW3NuYW1lXQogICAgICAgICAg"
    "ICBfLCBjbWFwID0gZ2V0X3NyYygiYmFsYW5jZSIpCiAgICAgICAgICAgIHNyY19jICAgPSBjbWFwLmdl"
    "dChzbmFtZSwgW10pCiAgICAgICAgICAgIHRndF9jICAgPSByZWFkX3NoZWV0KGZpZCwgc2lkX3QpCiAg"
    "ICAgICAgICAgIHByaW50KGYiICBbQkxPUVVFXSB7c25hbWV9IChzcmMge3NzKzF9OntzZX0g4oaSIHRn"
    "dCB7dHMrMX06e3RlfSkiKQogICAgICAgICAgICBpZiBzcmNfYzogY29weV9ibG9ja19zaGVldChmaWQs"
    "IHNpZF90LCBzcmNfYywgdGd0X2MsIHNzLCBzZSwgdHMsIHRlKQogICAgICAgICAgICBlbHNlOiAgICAg"
    "cHJpbnQoIiAgICDihpIgRnVlbnRlIG5vIGVuY29udHJhZGEiKQogICAgICAgICAgICBjb250aW51ZQoK"
    "ICAgICAgICB0Z3RfY2VsbHMgPSByZWFkX3NoZWV0KGZpZCwgc2lkX3QpCiAgICAgICAgaWYgbm90IHRn"
    "dF9jZWxsczogY29udGludWUKCiAgICAgICAgY29tcF9jb2xzID0gZGV0ZWN0X2NvbXBfY29scyh0Z3Rf"
    "Y2VsbHMsIGJhc2VzKQoKICAgICAgICBpZiBub3QgY29tcF9jb2xzOgogICAgICAgICAgICAjIEludGVu"
    "dGFyIHBhdHLDs24gZGUgYmxvcXVlcyB2ZXJ0aWNhbGVzIChlai4gaG9qYSAxOSkKICAgICAgICAgICAg"
    "YmxvY2tzID0gZGV0ZWN0X3ZlcnRpY2FsX2Jsb2Nrcyh0Z3RfY2VsbHMsIGJhc2VzKQogICAgICAgICAg"
    "ICBpZiBibG9ja3M6CiAgICAgICAgICAgICAgICBfLCBjbWFwICAgPSBnZXRfc3JjKCJiYWxhbmNlIikK"
    "ICAgICAgICAgICAgICAgIHNyY19jZWxscyA9IGNtYXAuZ2V0KHNuYW1lKSBvciBjbWFwLmdldChTSEVF"
    "VF9BTElBU0VTLmdldChzbmFtZSwgIiIpLCBbXSkKICAgICAgICAgICAgICAgIGlmIHNyY19jZWxsczoK"
    "ICAgICAgICAgICAgICAgICAgICBwcmludChmIiAgW1ZFUlRJQ0FMXSB7c25hbWV9IikKICAgICAgICAg"
    "ICAgICAgICAgICBuID0gZmlsbF92ZXJ0aWNhbF9zaGVldChmaWQsIHNpZF90LCB0Z3RfY2VsbHMsIHNy"
    "Y19jZWxscywgYmxvY2tzLCBiYXNlcykKICAgICAgICAgICAgICAgICAgICBpZiBuOiBva190b3RhbCAr"
    "PSBuCiAgICAgICAgICAgICAgICAgICAgZWxzZTogcHJpbnQoIiAgICDihpIgU2luIHZhbG9yZXMgZXNj"
    "cml0b3MiKQogICAgICAgICAgICBjb250aW51ZQoKICAgICAgICBwcmludChmIiAgW3tzbmFtZX1dIOKA"
    "lCB7bGVuKGNvbXBfY29scyl9IGNvbChzKSIpCgogICAgICAgIGZvciBkZXN0X2NvbCwgcGVyaW9kX2tl"
    "eSBpbiBjb21wX2NvbHMuaXRlbXMoKToKICAgICAgICAgICAgIyBSZWdsYSAxMTogZWwgY29tcGFyYXRp"
    "dm8gYmFsYW5jZSAoMzEtMTIpIHNvbG8gc2UgbGxlbmEgY3VhbmRvIGVsCiAgICAgICAgICAgICMgcGVy"
    "w61vZG8gYWN0dWFsIGVzIG1hcnpvICgwMykuIEVuIDA2LzA5LzEyIGVzYSBjb2x1bW5hIHlhIHF1ZWTD"
    "swogICAgICAgICAgICAjIHBvYmxhZGEgZW4gZWwgY2llcnJlIGRlIG1hcnpvIHkgbm8gc2UgdnVlbHZl"
    "IGEgdG9jYXIuCiAgICAgICAgICAgIGlmIHBlcmlvZF9rZXkgPT0gImJhbGFuY2UiIGFuZCBwYXJzZWRb"
    "Im1tIl0gIT0gIjAzIjoKICAgICAgICAgICAgICAgIGNvbnRpbnVlCgogICAgICAgICAgICBfLCBjbWFw"
    "ICAgPSBnZXRfc3JjKHBlcmlvZF9rZXkpCiAgICAgICAgICAgIHNyY19jZWxscyA9IGNtYXAuZ2V0KHNu"
    "YW1lLCBbXSkKICAgICAgICAgICAgaWYgbm90IHNyY19jZWxsczogY29udGludWUKCiAgICAgICAgICAg"
    "IG9mZnNldCAgPSBmaW5kX29mZnNldCh0Z3RfY2VsbHMsIHNyY19jZWxscywgcGVyaW9kX3JlZi5nZXQo"
    "cGVyaW9kX2tleSwiIikpCiAgICAgICAgICAgIHNyY19jb2wgPSBkZXN0X2NvbCAtIG9mZnNldAogICAg"
    "ICAgICAgICBpZiBzcmNfY29sIDwgMDogY29udGludWUKCiAgICAgICAgICAgIHdyaXRlX3ZhbHMgPSBi"
    "dWlsZF93cml0ZV92YWx1ZXModGd0X2NlbGxzLCBzcmNfY2VsbHMsIGRlc3RfY29sLCBzcmNfY29sKQog"
    "ICAgICAgICAgICBuID0gc3VtKDEgZm9yIHYgaW4gd3JpdGVfdmFscyBpZiB2IGlzIG5vdCBOb25lKQog"
    "ICAgICAgICAgICBpZiBuID09IDA6IGNvbnRpbnVlCgogICAgICAgICAgICBvayA9IHB1dF9jb2woZmlk"
    "LCBzaWRfdCwgZGVzdF9jb2wsIHdyaXRlX3ZhbHMsIHBlcmlvZF9rZXkpCiAgICAgICAgICAgIGlmIG9r"
    "OiBva190b3RhbCArPSAxCiAgICAgICAgICAgIGVsc2U6ICBlcnJfdG90YWwgKz0gMQogICAgICAgICAg"
    "ICB0aW1lLnNsZWVwKDAuMykKCiAgICBwcmludChmIiAgUmVzdWx0YWRvOiBPSz17b2tfdG90YWx9ICBF"
    "UlI9e2Vycl90b3RhbH0iKQogICAgcmV0dXJuIG9rX3RvdGFsLCBlcnJfdG90YWwKCiMg4pSA4pSA4pSA"
    "IE1BSU4g4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA"
    "4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA"
    "4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA"
    "4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSACmRlZiBtYWluKCk6CiAgICBfdDAgPSB0"
    "aW1lLnRpbWUoKQogICAgcHJpbnQoIj0iKjYwKQogICAgcHJpbnQoIkxMRU5BRE8gREUgQ09NUEFSQVRJ"
    "Vk9TIHYyIikKICAgIHByaW50KCI9Iio2MCkKCiAgICAjIE1vZG8gcHJ1ZWJhOiB1c2FyIGFyY2hpdm8g"
    "ZGUgcHJ1ZWJhIGRpcmVjdGFtZW50ZQogICAgaWYgVEVTVF9NT0RFOgogICAgICAgIHByaW50KGYiXG5b"
    "TU9ETyBQUlVFQkFdIEFyY2hpdm86IHtURVNUX0ZJTEVfSUR9IikKICAgICAgICBwcmludChmIiAgRW1w"
    "cmVzYToge1RFU1RfQ09ERX0gfCBQZXLDrW9kbzoge1RFU1RfTU19LXtURVNUX1lZWVl9IikKICAgICAg"
    "ICByZWZyZXNoX3Rva2VuKCkKICAgICAgICBhbGxfZmlsZXMgICAgPSBsb2FkX2FsbF9maWxlcygpCiAg"
    "ICAgICAgdGFyZ2V0X2ZpbGVzID0gW3sKICAgICAgICAgICAgImlkIjogVEVTVF9GSUxFX0lELCAibmFt"
    "ZSI6IGYiKHBydWViYSkge1RFU1RfQ09ERX1fe1RFU1RfTU19LXtURVNUX1lZWVl9IiwKICAgICAgICAg"
    "ICAgImNvZGUiOiBURVNUX0NPREUsICJ0aXBvIjogIklORCIsICJtbSI6IFRFU1RfTU0sICJ5eXl5Ijog"
    "VEVTVF9ZWVlZLCAic3VmZml4IjogVEVTVF9TVUZGSVgsCiAgICAgICAgfV0KICAgIGVsc2U6CiAgICAg"
    "ICAgIyBTb2xvIElORCDigJQgQ09OU08gZXhjbHVpZG8KICAgICAgICBwcmludCgpCiAgICAgICAgeXl5"
    "eSA9IGlucHV0KCJBw7FvIGRlbCBwZXLDrW9kbyAoZWo6IDIwMjYpOiAiKS5zdHJpcCgpCiAgICAgICAg"
    "bW0gICA9IGlucHV0KCJNZXMgZGVsIHBlcsOtb2RvIChlajogMDYpOiAiKS5zdHJpcCgpLnpmaWxsKDIp"
    "CiAgICAgICAgdGlwbyA9ICJJTkQiCgogICAgICAgIGlmIG5vdCB5eXl5LmlzZGlnaXQoKSBvciBub3Qg"
    "bW0uaXNkaWdpdCgpIG9yIG5vdCAoMSA8PSBpbnQobW0pIDw9IDEyKToKICAgICAgICAgICAgcHJpbnQo"
    "IkHDsW8gbyBtZXMgaW52w6FsaWRvLiIpCiAgICAgICAgICAgIHJldHVybgoKICAgICAgICBwcmludChm"
    "IlxuQnVzY2FuZG8gYXJjaGl2b3MgSU5EIHBhcmEge21tfS17eXl5eX0uLi4iKQogICAgICAgIHJlZnJl"
    "c2hfdG9rZW4oKQoKICAgICAgICBhbGxfZmlsZXMgICAgPSBsb2FkX2FsbF9maWxlcygpCiAgICAgICAg"
    "dGFyZ2V0X2ZpbGVzID0gZmluZF90YXJnZXRfZmlsZXMobW0sIHl5eXksIHRpcG8sIGFsbF9maWxlcykK"
    "CiAgICBpZiBub3QgdGFyZ2V0X2ZpbGVzOgogICAgICAgIHByaW50KGYiTm8gc2UgZW5jb250cmFyb24g"
    "YXJjaGl2b3MgRXt7Y29kZX19X0lORF97bW19LXt5eXl5fV9CYXNlIE5vdGFzIHt7c3VmZml4fX0iKQog"
    "ICAgICAgIHJldHVybgoKICAgIHByaW50KGYiXG5BcmNoaXZvcyBlbmNvbnRyYWRvcyAoe2xlbih0YXJn"
    "ZXRfZmlsZXMpfSk6IikKICAgIGZvciBpLCB0IGluIGVudW1lcmF0ZSh0YXJnZXRfZmlsZXMsIDEpOgog"
    "ICAgICAgIHByaW50KGYiICB7aX0uIHt0WyduYW1lJ119IikKCiAgICBpZiBub3QgVEVTVF9NT0RFOgog"
    "ICAgICAgIGNvbmZpcm0gPSBpbnB1dChmIlxuwr9Qcm9jZXNhciB0b2RvcyAocyksIGVsZWdpciB1bm8g"
    "cG9yIHVubyAoZSksIG8gY2FuY2VsYXIgKG4pPyAiKS5zdHJpcCgpLmxvd2VyKCkKICAgICAgICBpZiBj"
    "b25maXJtID09ICJuIjoKICAgICAgICAgICAgcHJpbnQoIkNhbmNlbGFkby4iKQogICAgICAgICAgICBy"
    "ZXR1cm4KICAgICAgICBlbGlmIGNvbmZpcm0gPT0gImUiOgogICAgICAgICAgICBzZWxlY2Npb25hZG9z"
    "ID0gW10KICAgICAgICAgICAgZm9yIHQgaW4gdGFyZ2V0X2ZpbGVzOgogICAgICAgICAgICAgICAgcmVz"
    "cCA9IGlucHV0KGYiICDCv1Byb2Nlc2FyIHt0WyduYW1lJ119PyAocy9uKTogIikuc3RyaXAoKS5sb3dl"
    "cigpCiAgICAgICAgICAgICAgICBpZiByZXNwID09ICJzIjoKICAgICAgICAgICAgICAgICAgICBzZWxl"
    "Y2Npb25hZG9zLmFwcGVuZCh0KQogICAgICAgICAgICBpZiBub3Qgc2VsZWNjaW9uYWRvczoKICAgICAg"
    "ICAgICAgICAgIHByaW50KCJObyBzZSBzZWxlY2Npb27DsyBuaW5nw7puIGFyY2hpdm8uIENhbmNlbGFk"
    "by4iKQogICAgICAgICAgICAgICAgcmV0dXJuCiAgICAgICAgICAgIHRhcmdldF9maWxlcyA9IHNlbGVj"
    "Y2lvbmFkb3MKICAgICAgICAgICAgcHJpbnQoZiJcblByb2Nlc2FuZG8ge2xlbih0YXJnZXRfZmlsZXMp"
    "fSBhcmNoaXZvKHMpIHNlbGVjY2lvbmFkbyhzKS4iKQoKICAgICMgUHJvY2VzYXIgY2FkYSBhcmNoaXZv"
    "OiBsaW1waWFyIHByaW1lcm8sIGx1ZWdvIGxsZW5hcgogICAgdG90YWxfb2sgPSB0b3RhbF9lcnIgPSAw"
    "CiAgICBmb3IgdCBpbiB0YXJnZXRfZmlsZXM6CiAgICAgICAgcHJpbnQoZiJcbiAg4oaSIExpbXBpYW5k"
    "byBjb21wYXJhdGl2b3M6IHt0WyduYW1lJ119IikKICAgICAgICBjbGVhbl9maWxlKHRbImlkIl0sIHRb"
    "Im5hbWUiXSkKICAgICAgICBvaywgZXJyID0gcHJvY2Vzc19maWxlKHQsIGFsbF9maWxlcykKICAgICAg"
    "ICB0b3RhbF9vayAgKz0gb2sKICAgICAgICB0b3RhbF9lcnIgKz0gZXJyCgogICAgZWxhcHNlZCA9IHRp"
    "bWUudGltZSgpIC0gX3QwCiAgICBtaW5zLCBzZWNzID0gZGl2bW9kKGludChlbGFwc2VkKSwgNjApCiAg"
    "ICBwcmludChmIlxueyc9Jyo2MH0iKQogICAgcHJpbnQoZiJSRVNVTUVOIEZJTkFMOiB7bGVuKHRhcmdl"
    "dF9maWxlcyl9IGFyY2hpdm9zIHByb2Nlc2Fkb3MiKQogICAgcHJpbnQoZiIgIE9wZXJhY2lvbmVzIE9L"
    "OiAge3RvdGFsX29rfSIpCiAgICBwcmludChmIiAgRXJyb3JlczogICAgICAgICB7dG90YWxfZXJyfSIp"
    "CiAgICBwcmludChmIiAgVGllbXBvIHRvdGFsOiAgICB7bWluc31tIHtzZWNzfXMiKQogICAgcHJpbnQo"
    "Ij0iKjYwKQoKaWYgX19uYW1lX18gPT0gIl9fbWFpbl9fIjoKICAgIG1haW4oKQo="
).decode("utf-8")

# Módulos con acceso restringido: key → contraseña
RESTRICTED_MODULES = {}

NAV_ITEMS = [
    ("Verificador de Sumas",   "verif"),
    ("Llenar Comparativos",    "mod2"),
    ("Cruce de Notas",         "mod3"),
    ("Extraer EEFF",           "mod4"),
]

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Workiva Tool — CGE Workiva")
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
        self._build_view_cruce_notas()
        self._build_view_extraer_eeff()

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
        tk.Entry(inner, textvariable=self._cmp_mes, font=FONT_LABEL,
                 bg=CGE_LIGHT, fg=CGE_TEXT, relief="flat", bd=4, width=12,
                 highlightbackground=CGE_BORDER, highlightthickness=1
                 ).grid(row=0, column=1, sticky="ew", padx=(8,0), pady=4)

        tk.Label(inner, text="Año", font=FONT_SMALL,
                 bg=CGE_CARD, fg=CGE_MUTED).grid(row=1, column=0, sticky="w", pady=4)
        self._cmp_anio = tk.StringVar()
        tk.Entry(inner, textvariable=self._cmp_anio, font=FONT_LABEL,
                 bg=CGE_LIGHT, fg=CGE_TEXT, relief="flat", bd=4, width=12,
                 highlightbackground=CGE_BORDER, highlightthickness=1
                 ).grid(row=1, column=1, sticky="ew", padx=(8,0), pady=4)
        inner.columnconfigure(1, weight=1)

        # Botones
        tk.Frame(left, bg=CGE_LIGHT, height=4).pack()
        self._cmp_btn_buscar = tk.Button(left, text="Buscar archivos",
                  font=FONT_BOLD, bg=CGE_BLUE, fg=CGE_WHITE,
                  activebackground=CGE_BLUE2, activeforeground=CGE_WHITE,
                  relief="flat", bd=0, padx=10, pady=9,
                  cursor="hand2", command=self._cmp_on_buscar)
        self._cmp_btn_buscar.pack(fill="x")
        tk.Frame(left, bg=CGE_LIGHT, height=6).pack()
        self._cmp_btn_procesar = tk.Button(left, text="Procesar seleccionados",
                  font=FONT_BOLD, bg=CGE_GREEN, fg=CGE_WHITE,
                  activebackground="#076b45", activeforeground=CGE_WHITE,
                  relief="flat", bd=0, padx=10, pady=9,
                  cursor="hand2", command=self._cmp_on_procesar, state="disabled")
        self._cmp_btn_procesar.pack(fill="x")

        # Panel derecho
        right = tk.Frame(body, bg=CGE_LIGHT)
        right.pack(side="left", fill="both", expand=True)

        # Archivos encontrados
        tk.Label(right, text="ARCHIVOS ENCONTRADOS", font=("Segoe UI", 8, "bold"),
                 bg=CGE_LIGHT, fg=CGE_MUTED).pack(anchor="w", pady=(0, 4))
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

        # Log actividad
        act_hdr = tk.Frame(right, bg=CGE_LIGHT)
        act_hdr.pack(fill="x", pady=(0, 4))
        tk.Label(act_hdr, text="ACTIVIDAD", font=("Segoe UI", 8, "bold"),
                 bg=CGE_LIGHT, fg=CGE_MUTED).pack(side="left")
        tk.Button(act_hdr, text="Limpiar", font=FONT_SMALL,
                  bg=CGE_BORDER, fg=CGE_TEXT, relief="flat", bd=0,
                  padx=8, pady=2, cursor="hand2",
                  command=lambda: self._cmp_clear_log()).pack(side="right")
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
        for w in self._cmp_inner.winfo_children():
            w.destroy()
        self._cmp_vars = []
        if not files:
            tk.Label(self._cmp_inner, text="No se encontraron archivos.",
                     font=FONT_SMALL, bg=CGE_CARD, fg=CGE_RED, pady=14).pack()
            return
        for i, f in enumerate(files):
            var = tk.BooleanVar(value=True)
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

    def _cmp_on_buscar(self):
        mes  = self._cmp_mes.get().strip().zfill(2)
        anio = self._cmp_anio.get().strip()
        if not re.fullmatch(r"\d{2}", mes) or not re.fullmatch(r"\d{4}", anio):
            messagebox.showerror("Error", "Ingresa mes (01-12) y año válidos.")
            return
        self._cmp_clear_log()
        self._cmp_btn_buscar.configure(state="disabled")
        self._cmp_btn_procesar.configure(state="disabled")
        self._cmp_log_write(f"Buscando archivos IND para {mes}-{anio}...", "blue")
        threading.Thread(target=self._cmp_thread_buscar,
                         args=(mes, anio), daemon=True).start()

    def _cmp_thread_buscar(self, mes, anio):
        try:
            import requests as _req
            s = _req.Session()
            resp = s.post(TOKEN_URL, data={
                "grant_type": "client_credentials",
                "client_id": CLIENT_ID,
                "client_secret": CLIENT_SECRET,
            }, verify=False, timeout=30)
            token = resp.json()["access_token"]
            s.headers.update({"Authorization": f"Bearer {token}",
                               "X-Version": "2022-01-01"})

            # Cargar todos los archivos
            all_files = {}
            url = f"{WDESK_BASE}/platform/v1/files?workspaceId={WORKSPACE_ID}&limit=100"
            while url:
                r    = s.get(url, verify=False, timeout=90)
                data = r.json()
                for f in data.get("data", []):
                    all_files[f["name"]] = f["id"]
                url = data.get("@nextLink")

            # Buscar archivos del periodo
            import re as _re
            pattern = _re.compile(rf"^E\d+_IND_{mes}[-_]{anio}_Base Notas .+$")
            files = []
            for name, fid in all_files.items():
                if pattern.match(name):
                    parsed = _re.match(rf"(E\d+)_(IND)_(\d{{2}})[-_](\d{{4}})_(.*)", name)
                    if parsed:
                        files.append({
                            "id": fid, "name": name,
                            "code": parsed.group(1), "tipo": "IND",
                            "mm": parsed.group(3), "yyyy": parsed.group(4),
                            "suffix": parsed.group(5),
                        })
            files.sort(key=lambda x: x["code"])
            self._cmp_files    = files
            self._cmp_session  = s
            self._cmp_allfiles = all_files
            self.after(0, lambda: self._cmp_render_files(files))
            self._cmp_log_write(f"  {len(files)} archivo(s) encontrado(s).", "ok" if files else "err")
            if files:
                self.after(0, lambda: self._cmp_btn_procesar.configure(state="normal"))
        except Exception as e:
            self._cmp_log_write(f"ERROR: {e}", "err")
        finally:
            self.after(0, lambda: self._cmp_btn_buscar.configure(state="normal"))

    def _cmp_on_procesar(self):
        seleccionados = [f for f, v in zip(self._cmp_files, self._cmp_vars) if v.get()]
        if not seleccionados:
            messagebox.showwarning("Aviso", "Selecciona al menos un archivo.")
            return
        self._cmp_btn_buscar.configure(state="disabled")
        self._cmp_btn_procesar.configure(state="disabled")
        self._cmp_log_write(f"\nProcesando {len(seleccionados)} archivo(s)...", "blue")
        threading.Thread(target=self._cmp_thread_procesar,
                         args=(seleccionados,), daemon=True).start()

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
            try:
                mod = types.ModuleType("llenar_comp")
                mod.session   = self._cmp_session
                mod.all_files = self._cmp_allfiles
                exec(compile(_LLENAR_COMP_SRC, "llenar_comparativos.py", "exec"), mod.__dict__)

                total_ok = total_err = 0
                for t in seleccionados:
                    ok, err = mod.process_file(t, self._cmp_allfiles)
                    total_ok  += ok
                    total_err += err
                self._cmp_log_write(f"\nRESUMEN: OK={total_ok}  ERR={total_err}",
                                    "ok" if total_err == 0 else "warn")
            finally:
                builtins.print = _orig_print
        except Exception as e:
            self._cmp_log_write(f"ERROR inesperado: {e}", "err")
        finally:
            self.after(0, lambda: self._cmp_btn_buscar.configure(state="normal"))
            self.after(0, lambda: self._cmp_btn_procesar.configure(state="normal"))

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
        tk.Label(title_frame, text="Workiva Tool",
                 font=("Segoe UI", 15, "bold"),
                 bg=CGE_BLUE, fg=CGE_WHITE).pack(anchor="w")
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

        # ── Card idioma ──
        self._card_title(parent, "Idioma")
        idf = tk.Frame(parent, bg=CGE_CARD,
                       highlightbackground=CGE_BORDER, highlightthickness=1)
        idf.pack(fill="x", pady=(0, 10))
        iinner = tk.Frame(idf, bg=CGE_CARD, padx=12, pady=8)
        iinner.pack(fill="x")
        self._v_idioma = tk.StringVar(value="AMBOS")
        for txt in ("ESP", "ENG", "AMBOS"):
            tk.Radiobutton(iinner, text=txt, variable=self._v_idioma, value=txt,
                           font=FONT_SMALL, bg=CGE_CARD, fg=CGE_TEXT,
                           selectcolor=CGE_LIGHT, activebackground=CGE_CARD,
                           activeforeground=CGE_BLUE).pack(anchor="w", pady=1)

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
        return var

    def _make_btn(self, parent, text, cmd, color):
        b = tk.Button(parent, text=text, font=FONT_BOLD,
                      bg=color, fg=CGE_WHITE,
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
            return
        for i, doc in enumerate(docs):
            var = tk.BooleanVar(value=True)
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
            self.after(0, self._unlock)


if __name__ == "__main__":
    app = App()
    app.mainloop()
