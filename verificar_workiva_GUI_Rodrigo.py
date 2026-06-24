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


NAV_ITEMS = [
    ("Verificador de Sumas",  "verif"),
    ("Módulo 2",              "mod2"),
    ("Módulo 3",              "mod3"),
    ("Módulo 4",              "mod4"),
]

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("NOMBRE PENDIENTE — CGE Workiva")
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
        self._build_header()

        # Footer anclado ANTES del contenido para que siempre quede visible
        self._build_footer()

        # Contenedor principal bajo el header
        main = tk.Frame(self, bg=CGE_LIGHT)
        main.pack(fill="both", expand=True)

        self._build_sidebar(main)

        # Área de contenido a la derecha del sidebar
        self._content = tk.Frame(main, bg=CGE_LIGHT)
        self._content.pack(side="left", fill="both", expand=True)

        # Construir vistas
        self._views = {}
        self._build_view_verif()
        self._build_view_placeholder("mod2", "Módulo 2")
        self._build_view_placeholder("mod3", "Módulo 3")
        self._build_view_placeholder("mod4", "Módulo 4")

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

    def _build_footer(self):
        footer = tk.Frame(self, bg=CGE_BORDER, pady=6)
        footer.pack(fill="x", side="bottom")
        tk.Label(footer,
                 text="© Programado por Emerson Garrido — Todos los derechos reservados.",
                 font=("Segoe UI", 8), bg=CGE_BORDER, fg=CGE_MUTED).pack(side="left", padx=14)

    def _build_view_placeholder(self, key, name):
        frame = tk.Frame(self._content, bg=CGE_LIGHT)
        tk.Label(frame, text=name, font=("Segoe UI", 16, "bold"),
                 bg=CGE_LIGHT, fg=CGE_BLUE).pack(pady=(60, 10))
        tk.Label(frame, text="En desarrollo", font=("Segoe UI", 11),
                 bg=CGE_LIGHT, fg=CGE_MUTED).pack()
        self._views[key] = frame

    def _build_header(self):
        hdr = tk.Frame(self, bg=CGE_BLUE, pady=0)
        hdr.pack(fill="x")

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
        tk.Label(title_frame, text="NOMBRE PENDIENTE",
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
