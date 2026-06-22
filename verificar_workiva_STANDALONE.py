# verificar_workiva_STANDALONE.py
# NO necesita instalar ninguna libreria. Solo Python puro (stdlib).

import io, json, os, re, ssl, sys, time, urllib.request, urllib.error, zipfile
import xml.etree.ElementTree as ET
from pathlib import Path

# ---------------------------------------------------------------------------
# CREDENCIALES
# ---------------------------------------------------------------------------
CLIENT_ID     = "db2c551e-e18a-417e-8e52-d182716b8ef2"
CLIENT_SECRET = "wk_secret:oa2c:DzlUCmBQDv6raPxG09me"
WORKSPACE_ID  = "w_34913aadaa38420eabd7e4d341b78a1a"

TOKEN_URL  = "https://api.app.wdesk.com/iam/v1/oauth2/token"
WDESK_BASE = "https://api.app.wdesk.com"

SS_VERIF_NAME = "verificación de sumas"
DOCX_DIR      = Path("docx_tmp_verif")

MESES = {
    "1":"01","01":"01","enero":"01","2":"02","02":"02","febrero":"02",
    "3":"03","03":"03","marzo":"03","4":"04","04":"04","abril":"04",
    "5":"05","05":"05","mayo":"05","6":"06","06":"06","junio":"06",
    "7":"07","07":"07","julio":"07","8":"08","08":"08","agosto":"08",
    "9":"09","09":"09","septiembre":"09","10":"10","octubre":"10",
    "11":"11","noviembre":"11","12":"12","diciembre":"12",
}
NOMBRE_MES = {
    "01":"Enero","02":"Febrero","03":"Marzo","04":"Abril","05":"Mayo",
    "06":"Junio","07":"Julio","08":"Agosto","09":"Septiembre",
    "10":"Octubre","11":"Noviembre","12":"Diciembre",
}
TOTAL_KEYWORDS = [
    "total activos","total pasivos","total patrimonio",
    "total activos corrientes","total activos no corrientes",
    "total pasivos corrientes","total pasivos no corrientes",
    "ganancia bruta","ganancia (pérdida)","resultado del periodo",
    "resultado integral","total flujos","total cambios","total","subtotal",
]

# SSL sin verificacion (red corporativa)
CTX = ssl.create_default_context()
CTX.check_hostname = False
CTX.verify_mode = ssl.CERT_NONE

# ---------------------------------------------------------------------------
# HTTP helpers (sin requests)
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
            wait = 2 ** attempt
            print(f"\n    [reintento {attempt+1}/3 en {wait}s...]", end=" ", flush=True)
            time.sleep(wait)
    raise last_err

def http_bytes(url, headers=None, timeout=120):
    req = urllib.request.Request(url, headers=headers or {})
    with urllib.request.urlopen(req, context=CTX, timeout=timeout) as resp:
        return resp.read()

# ---------------------------------------------------------------------------
# Autenticacion Workiva
# ---------------------------------------------------------------------------
_token = None
_token_expiry = 0

def get_token():
    global _token, _token_expiry
    if _token and time.time() < _token_expiry:
        return _token
    status, data = http("POST", TOKEN_URL, body={
        "grant_type": "client_credentials",
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
    })
    if status != 200:
        raise RuntimeError(f"Auth fallida: {status} {data}")
    _token = data["access_token"]
    _token_expiry = time.time() + data.get("expires_in", 3600) - 60
    return _token

def api_get(path, params=""):
    url = f"{WDESK_BASE}{path}{params}"
    token = get_token()
    status, data = http("GET", url, headers={
        "Authorization": f"Bearer {token}",
        "X-Version": "2022-01-01",
    })
    if status not in (200,):
        raise RuntimeError(f"GET {path} → {status}: {data}")
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
                location = resp.getheader("Location","")
                return resp.status, {}, location
        except urllib.error.HTTPError as e:
            location = e.headers.get("Location","")
            raw = e.read()
            return e.code, json.loads(raw) if raw else {}, location
        except Exception as e:
            last_err = e
            wait = 2 ** attempt
            time.sleep(wait)
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
                location = resp.getheader("Location","")
                return resp.status, {}, location
        except urllib.error.HTTPError as e:
            location = e.headers.get("Location","")
            raw = e.read()
            return e.code, json.loads(raw) if raw else {}, location
        except Exception as e:
            last_err = e
            wait = 2 ** attempt
            time.sleep(wait)
    raise last_err

def poll_operation(location, max_tries=40, wait=3):
    token = get_token()
    for _ in range(max_tries):
        time.sleep(wait)
        status, data = http("GET", location, headers={
            "Authorization": f"Bearer {token}",
            "X-Version": "2022-01-01",
        })
        if data.get("status") == "completed":
            return data
        if "fail" in data.get("status","").lower() or "error" in data.get("status","").lower():
            raise RuntimeError(f"Operacion fallida: {data}")
    raise RuntimeError("Timeout esperando operacion")

def paginar(path):
    results = []
    url_suffix = path
    while url_suffix:
        data = api_get(url_suffix) if url_suffix.startswith("/") else http("GET", url_suffix, headers={
            "Authorization": f"Bearer {get_token()}",
            "X-Version": "2022-01-01",
        })[1]
        items = data.get("value", data.get("data", []))
        results.extend(items)
        next_url = data.get("@nextLink") or data.get("nextLink")
        url_suffix = next_url if next_url and not next_url.startswith("/") else None
        if next_url and next_url.startswith("/"):
            url_suffix = next_url
        if not next_url:
            break
    return results

# ---------------------------------------------------------------------------
# Consola helpers
# ---------------------------------------------------------------------------
def hr(c="─", n=64): print(c * n)

def ask(prompt, opts=None, default=None):
    while True:
        suffix = f" [{'/'.join(opts)}]" if opts else ""
        suffix += f" (Enter={default})" if default else ""
        val = input(f"{prompt}{suffix}: ").strip()
        if not val and default:
            return default
        if opts:
            if val.upper() in [o.upper() for o in opts]:
                return val.upper()
            print(f"  Elige: {', '.join(opts)}")
        elif val:
            return val
        else:
            print("  No puede estar vacio.")

def seleccionar_docs(docs):
    hr()
    print(f"  {len(docs)} documento(s) encontrado(s):\n")
    for i, d in enumerate(docs, 1):
        print(f"  {i:>2}. {d['nombre']}")
    hr()
    print()
    resp = input("  Seleccionar todos? [TODOS / NINGUNO / uno por uno]: ").strip().upper()
    if resp == "TODOS":
        print("  Todos seleccionados.")
        return list(docs)
    if resp == "NINGUNO":
        return []
    sel = []
    print()
    for i, d in enumerate(docs, 1):
        r = ask(f"  {i:>2}. {d['nombre']}", opts=["S","N"])
        if r == "S":
            sel.append(d)
    return sel

# ---------------------------------------------------------------------------
# Workiva: buscar documentos
# ---------------------------------------------------------------------------
def buscar_documentos(mes, anio, idioma):
    print("  Descargando catalogo...", end=" ", flush=True)
    todos = []
    url = "/platform/v1/documents?$top=100"
    while url:
        data = api_get(url) if url.startswith("/") else http("GET", url, headers={
            "Authorization": f"Bearer {get_token()}",
            "X-Version": "2022-01-01",
        })[1]
        items = data.get("value", data.get("data", []))
        todos.extend(items)
        nxt = data.get("@nextLink") or data.get("nextLink","")
        url = nxt if nxt else None

    print(f"{len(todos)} docs.")
    def ok_idioma(n):
        if idioma == "AMBOS": return True
        return f"({idioma})" in n.upper()
    resultado = [
        {"id": d["id"], "nombre": d["name"]}
        for d in todos
        if any(p in d.get("name","") for p in [f"{mes}-{anio}", f"{mes}/{anio}"])
        and ok_idioma(d.get("name",""))
    ]
    resultado.sort(key=lambda x: x["nombre"])
    return resultado

# ---------------------------------------------------------------------------
# Workiva: spreadsheet verificacion
# ---------------------------------------------------------------------------
SS_CACHE = Path(__file__).parent / ".ss_verif_id"

def buscar_spreadsheet_verif():
    # Usar ID cacheado si existe (evita paginar 2745 spreadsheets cada vez)
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
            if SS_VERIF_NAME in ss.get("name","").lower():
                sid = ss["id"]
                print(f"encontrado: '{ss['name']}' [{sid}]")
                SS_CACHE.write_text(sid)
                return sid
        url = data.get("@nextLink") or data.get("nextLink","") or None
    print("NO encontrado.")
    return None

def obtener_o_crear_hoja(ss_id, nombre_hoja):
    data = api_get(f"/platform/v1/spreadsheets/{ss_id}/sheets?$top=50")
    for s in data.get("value", data.get("data", [])):
        if s.get("name","").lower() == nombre_hoja.lower():
            return s["id"]
    status, resp, _ = api_post(f"/platform/v1/spreadsheets/{ss_id}/sheets", {"name": nombre_hoja})
    if status not in (200, 201, 202):
        raise RuntimeError(f"No se pudo crear hoja: {status}")
    return resp.get("id") or resp.get("data",{}).get("id")

def put_range(ss_id, sheet_id, rango, values):
    status, _, location = api_put(
        f"/platform/v1/spreadsheets/{ss_id}/sheets/{sheet_id}/values/{rango}",
        {"values": values}
    )
    if status == 202 and location:
        poll_operation(location, wait=2)

def contar_filas(ss_id, sheet_id):
    """Cuenta filas usadas leyendo A1:A2000 y buscando la ultima no vacia."""
    try:
        data = api_get(f"/platform/v1/spreadsheets/{ss_id}/sheets/{sheet_id}/values/A1:A2000")
        rows = data.get("values", [])
        last = 0
        for i, row in enumerate(rows, 1):
            if row and any(c for c in row if str(c).strip()):
                last = i
        return last
    except Exception:
        return 0

def hoja_tiene_datos(ss_id, sheet_id):
    return contar_filas(ss_id, sheet_id) > 0

# ---------------------------------------------------------------------------
# Descarga .docx desde Workiva (sin requests)
# ---------------------------------------------------------------------------
def exportar_docx(doc):
    nombre = re.sub(r'[\\/:*?"<>|]', "-", doc["nombre"]) + ".docx"
    ruta = DOCX_DIR / nombre
    if ruta.exists():
        return ruta

    status, _, location = api_post(
        f"/platform/v1/documents/{doc['id']}/export",
        {"format": "docx"}
    )
    if status != 202:
        raise RuntimeError(f"Export fallo: {status}")

    data = poll_operation(location, max_tries=40, wait=3)
    download_url = data.get("resourceUrl","")

    token = get_token()
    content = http_bytes(download_url, headers={
        "Authorization": f"Bearer {token}",
    })
    ruta.write_bytes(content)
    return ruta

# ---------------------------------------------------------------------------
# Parsear .docx con stdlib (zipfile + xml)
# ---------------------------------------------------------------------------
NS = {
    "w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main",
}

def get_cell_text(tc):
    texts = []
    for t in tc.iter(f"{{{NS['w']}}}t"):
        if t.text:
            texts.append(t.text)
    return "".join(texts).strip()

def extraer_tablas_docx(ruta):
    """Retorna lista de tablas, cada tabla es lista de filas, cada fila lista de strings."""
    tablas = []
    with zipfile.ZipFile(ruta) as z:
        with z.open("word/document.xml") as f:
            tree = ET.parse(f)
    root = tree.getroot()
    body = root.find(f"{{{NS['w']}}}body")
    if body is None:
        return tablas
    for tbl in body.iter(f"{{{NS['w']}}}tbl"):
        filas = []
        for tr in tbl.findall(f"{{{NS['w']}}}tr"):
            celdas = [get_cell_text(tc) for tc in tr.findall(f"{{{NS['w']}}}tc")]
            filas.append(celdas)
        if filas:
            tablas.append(filas)
    return tablas

# ---------------------------------------------------------------------------
# Verificacion de sumas
# ---------------------------------------------------------------------------
def limpiar_numero(texto):
    t = texto.strip().replace("\xa0","").replace(" ","")
    if not t or t in ("-","—","–"): return None
    neg = t.startswith("(") and t.endswith(")")
    t = t.strip("()").replace(".","").replace(",",".")
    try:
        v = float(t)
        return -v if neg else v
    except ValueError:
        return None

def es_fila_total(celdas):
    primera = celdas[0].lower().strip() if celdas else ""
    return any(kw in primera for kw in TOTAL_KEYWORDS)

def detectar_estado(primera_fila):
    txt = " ".join(primera_fila).upper()
    if "ACTIVOS" in txt and "PATRIMONIO" not in txt:
        return "Balance - Activos"
    if "PATRIMONIO" in txt and "PASIVOS" in txt:
        return "Balance - Patrimonio y Pasivos"
    if "RESULTADO" in txt and "INTEGRAL" not in txt:
        return "Estado de Resultados"
    if "INTEGRAL" in txt:
        return "Resultado Integral"
    if "CAMBIOS EN EL PATRIMONIO" in txt:
        return "Cambios en el Patrimonio"
    if "FLUJO" in txt or "EFECTIVO" in txt:
        return "Flujo de Efectivo"
    return None

def verificar_tablas(ruta):
    """
    Retorna lista de dicts con keys: estado, descripcion, actual, anterior, ok
    Una fila por total detectado, con valor del periodo actual (col 1) y anterior (col 2).
    Verifica que cada total = suma de sus componentes (tolerancia < 2 M$).
    """
    resultados = []
    tablas = extraer_tablas_docx(ruta)
    estado_actual = "Documento"

    for filas in tablas:
        if not filas: continue
        estado = detectar_estado(filas[0])
        if estado:
            estado_actual = estado

        num_cols = max(len(f) for f in filas)

        # acumuladores por columna: col1=Actual, col2=Anterior
        acum  = [0.0] * num_cols
        tiene = [False] * num_cols

        for fila in filas:
            while len(fila) < num_cols:
                fila.append("")
            if es_fila_total(fila):
                dec1 = limpiar_numero(fila[1]) if num_cols > 1 else None
                dec2 = limpiar_numero(fila[2]) if num_cols > 2 else None

                ok1 = (dec1 is None or not tiene[1] or abs(dec1 - acum[1]) < 2)
                ok2 = (dec2 is None or not tiene[2] or abs(dec2 - acum[2]) < 2)

                if dec1 is not None or dec2 is not None:
                    resultados.append({
                        "estado":      estado_actual,
                        "descripcion": fila[0][:80],
                        "actual":      dec1,
                        "anterior":    dec2,
                        "ok":          ok1 and ok2,
                    })
                acum  = [0.0] * num_cols
                tiene = [False] * num_cols
            else:
                for col in range(1, num_cols):
                    v = limpiar_numero(fila[col]) if col < len(fila) else None
                    if v is not None:
                        acum[col]  += v
                        tiene[col]  = True
    return resultados

ENCABEZADOS = ["Seccion", "Linea", "Actual", "Anterior", "Estado"]

def escribir_resultados(ss_id, sheet_id, resultados):
    if not resultados: return
    rows = [[
        r["estado"],
        r["descripcion"],
        r["actual"]   if r["actual"]   is not None else "",
        r["anterior"] if r["anterior"] is not None else "",
        "OK" if r["ok"] else "REVISAR",
    ] for r in resultados]
    primera = contar_filas(ss_id, sheet_id) + 1
    put_range(ss_id, sheet_id, f"A{primera}:E{primera+len(rows)-1}", rows)

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    hr("=")
    print("  VERIFICADOR DE SUMAS - EE.FF. WORKIVA")
    print("  (sin instalacion de librerias)")
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
    idioma = ask("  Idioma", opts=["ESP","ENG","AMBOS"], default="AMBOS")

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
    total_ok = total_err = 0

    for i, doc in enumerate(seleccionados, 1):
        # Extraer codigo de sociedad del nombre del documento (ej: "E514 (ESP) - ...")
        m = re.match(r"^([A-Z]\d+)", doc["nombre"].strip())
        nombre_hoja = m.group(1) if m else doc["nombre"][:20]

        print(f"\n  [{i}/{len(seleccionados)}] {doc['nombre']}")
        print(f"    Hoja destino: '{nombre_hoja}'")
        print("    Exportando .docx...", end=" ", flush=True)
        try:
            ruta = exportar_docx(doc)
            print(f"OK ({ruta.stat().st_size//1024} KB)")
        except Exception as e:
            print(f"ERROR: {e}")
            continue

        print("    Verificando sumas...", end=" ", flush=True)
        try:
            resultados = verificar_tablas(ruta)
        except Exception as e:
            print(f"ERROR al leer: {e}")
            continue
        ok  = sum(1 for r in resultados if r["ok"])
        err = len(resultados) - ok
        total_ok += ok; total_err += err
        print(f"{len(resultados)} checks | OK: {ok} | REVISAR: {err}")

        print("    Escribiendo en Workiva...", end=" ", flush=True)
        try:
            sheet_id = obtener_o_crear_hoja(ss_id, nombre_hoja)
            if not hoja_tiene_datos(ss_id, sheet_id):
                put_range(ss_id, sheet_id, "A1:E1", [ENCABEZADOS])
            escribir_resultados(ss_id, sheet_id, resultados)
            print("OK")
        except Exception as e:
            print(f"ERROR: {e}")

    hr("=")
    print(f"\n  RESUMEN FINAL")
    print(f"  Documentos  : {len(seleccionados)}")
    print(f"  OK          : {total_ok}")
    print(f"  REVISAR     : {total_err}")
    print(f"\n  Resultados en Workiva -> '{SS_VERIF_NAME}' -> hoja por sociedad")
    hr("=")
    input("\n  Presiona Enter para salir...")

if __name__ == "__main__":
    main()
