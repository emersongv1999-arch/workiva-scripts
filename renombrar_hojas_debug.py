"""
renombrar_hojas_debug.py
Version de consola para probar sin GUI — muestra todos los errores en detalle.
"""

import json, re, ssl, time
import urllib.request, urllib.error

# ── CREDENCIALES ──────────────────────────────────────────────────────────────
CLIENT_ID     = "db2c551e-e18a-417e-8e52-d182716b8ef2"
CLIENT_SECRET = "wk_secret:oa2c:DzlUCmBQDv6raPxG09me"
WORKSPACE_ID  = "w_34913aadaa38420eabd7e4d341b78a1a"
TOKEN_URL     = "https://api.app.wdesk.com/iam/v1/oauth2/token"
WDESK_BASE    = "https://api.app.wdesk.com"

CTX = ssl.create_default_context()
CTX.check_hostname = False
CTX.verify_mode    = ssl.CERT_NONE

def _http(method, url, headers=None, body=None, timeout=60):
    data = json.dumps(body).encode() if body is not None else None
    h = {"Content-Type": "application/json",
         "User-Agent": "Mozilla/5.0",
         **(headers or {})}
    req = urllib.request.Request(url, data=data, headers=h, method=method)
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

_token = None
_token_expiry = 0.0

def get_token():
    global _token, _token_expiry
    if _token and time.time() < _token_expiry:
        return _token
    st, data = _http("POST", TOKEN_URL, body={
        "grant_type": "client_credentials",
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
    })
    if st != 200:
        raise RuntimeError(f"Auth fallida: {st} — {data}")
    _token = data["access_token"]
    _token_expiry = time.time() + data.get("expires_in", 3600) - 60
    print(f"  Token OK")
    return _token

def hdrs():
    return {
        "Authorization": f"Bearer {get_token()}",
        "Content-Type":  "application/json",
        "X-Version":     "2022-01-01",
    }

def api_get(path):
    url = f"{WDESK_BASE}{path}" if path.startswith("/") else path
    print(f"  GET {path[:80]}")
    st, data = _http("GET", url, headers=hdrs())
    if st not in (200, 206):
        raise RuntimeError(f"GET {path} -> {st}: {data}")
    return data

# ── BUSCAR SPREADSHEET ────────────────────────────────────────────────────────
def buscar_spreadsheet(patron):
    print(f"\nBuscando spreadsheet con patron: '{patron}'")
    url = "/platform/v1/spreadsheets?$top=100"
    pagina = 0
    while url:
        pagina += 1
        data = api_get(url)
        items = data.get("value", data.get("data", []))
        print(f"  Pagina {pagina}: {len(items)} spreadsheets")
        for ss in items:
            nombre = ss.get("name", "")
            if patron.lower() in nombre.lower():
                print(f"  ENCONTRADO: '{nombre}' (id={ss['id']})")
                return ss["id"], nombre
        url = data.get("@nextLink") or data.get("nextLink") or None
    print(f"  NO encontrado.")
    return None, None

# ── LISTAR HOJAS ──────────────────────────────────────────────────────────────
def listar_hojas(ss_id):
    print(f"\nListando hojas de spreadsheet {ss_id}")
    hojas = []
    url = f"/platform/v1/spreadsheets/{ss_id}/sheets?$top=200"
    while url:
        data = api_get(url)
        items = data.get("value", data.get("data", []))
        hojas.extend(items)
        url = data.get("@nextLink") or data.get("nextLink") or None
    print(f"  Total hojas: {len(hojas)}")
    for h in hojas:
        pid = h.get("parentId", h.get("parent", {}).get("id", "-"))
        print(f"    [{h['id']}] '{h.get('name','')}' parent={pid}")
    return hojas

# ── LEER RANGO ────────────────────────────────────────────────────────────────
def leer_rango(ss_id, sheet_id, rango):
    print(f"\nLeyendo rango {rango} de hoja {sheet_id}")
    data = api_get(f"/platform/v1/spreadsheets/{ss_id}/sheets/{sheet_id}/values/{rango}")
    print(f"  Respuesta raw (primeras claves): {list(data.keys())}")
    vals = (data.get("values")
            or data.get("data", {}).get("values")
            or data.get("body", {}).get("values")
            or [])
    print(f"  Filas obtenidas: {len(vals)}")
    resultado = []
    for i, fila in enumerate(vals):
        celda = fila[0] if isinstance(fila, list) and fila else fila
        texto = str(celda).strip() if celda is not None else ""
        print(f"    E{i+2}: '{texto}'")
        resultado.append(texto)
    return resultado

# ── MAIN ──────────────────────────────────────────────────────────────────────
def main():
    mes  = input("\nMes (ej: 07): ").strip().zfill(2)
    anio = input("Anio (ej: 2026): ").strip()

    print("\n" + "="*60)
    print("PASO 1: Buscar TE - Bases")
    print("="*60)
    patron_bases = f"TE - Bases {mes}-{anio}"
    ss_id_bases, nom_bases = buscar_spreadsheet(patron_bases)

    if ss_id_bases:
        hojas_bases = listar_hojas(ss_id_bases)
        if hojas_bases:
            leer_rango(ss_id_bases, hojas_bases[0]["id"], "E2:E23")

    print("\n" + "="*60)
    print("PASO 2: Buscar CGE Cash Management")
    print("="*60)
    patron_cash = f"{mes} CGE Cash management"
    ss_id_cash, nom_cash = buscar_spreadsheet(patron_cash)

    if ss_id_cash:
        listar_hojas(ss_id_cash)

    print("\n" + "="*60)
    print("FIN DEL DIAGNOSTICO")
    print("="*60)

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        import traceback
        print(f"\nERROR FATAL: {e}")
        traceback.print_exc()
    input("\nPresiona Enter para salir...")
