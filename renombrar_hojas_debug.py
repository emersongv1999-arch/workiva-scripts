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

def hdrs(version="2022-01-01"):
    return {
        "Authorization": f"Bearer {get_token()}",
        "Content-Type":  "application/json",
        "X-Version":     version,
    }

def api_get(path, version="2022-01-01"):
    url = f"{WDESK_BASE}{path}" if path.startswith("/") else path
    print(f"  GET {path[:80]}")
    st, data = _http("GET", url, headers=hdrs(version))
    if st not in (200, 206):
        raise RuntimeError(f"GET {path} -> {st}: {data}")
    return data

def api_patch(path, body):
    url = f"{WDESK_BASE}{path}"
    return _http("PATCH", url, headers=hdrs(), body=body)

def api_put(path, body):
    url = f"{WDESK_BASE}{path}"
    return _http("PUT", url, headers=hdrs(), body=body)

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
        pid = h.get("parentId") or (h.get("parent") or {}).get("id", "-")
        print(f"    [{h['id']}] '{h.get('name','')}' parent={pid}")
    return hojas

# ── LEER RANGO ────────────────────────────────────────────────────────────────
def leer_rango(ss_id, sheet_id, rango):
    print(f"\nLeyendo rango {rango} de hoja {sheet_id}")
    data = api_get(f"/platform/v1/spreadsheets/{ss_id}/sheets/{sheet_id}/values/{rango}")
    print(f"  Respuesta raw (primeras claves): {list(data.keys())}")
    # Imprimir estructura completa de 'data' para diagnostico
    raw_data = data.get("data")
    print(f"  Tipo de data['data']: {type(raw_data).__name__}")
    print(f"  Primeros 3 elementos de data['data']: {str(raw_data)[:300]}")

    # data["data"] es lista de objetos: [{"range": "E2:E23", "values": [[v1],[v2],...]}]
    if isinstance(raw_data, list) and raw_data and isinstance(raw_data[0], dict):
        vals = raw_data[0].get("values", [])
    elif isinstance(raw_data, list):
        vals = raw_data
    else:
        vals = data.get("values") or []
    print(f"  Filas obtenidas: {len(vals)}")
    resultado = []
    import datetime as _dt
    for i, fila in enumerate(vals):
        celda = fila[0] if isinstance(fila, list) and fila else fila
        texto = str(celda).strip() if celda is not None else ""
        # Convertir "2026-07-01" → "01.07"
        try:
            dt = _dt.date.fromisoformat(texto)
            texto = f"{dt.day:02d}.{dt.month:02d}"
        except Exception:
            pass
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
            leer_rango(ss_id_bases, hojas_bases[0]["id"], "E2:E50")

    print("\n" + "="*60)
    print("PASO 2: Buscar CGE Cash Management")
    print("="*60)
    patron_cash = f"{mes} CGE Cash management"
    ss_id_cash, nom_cash = buscar_spreadsheet(patron_cash)

    if ss_id_cash:
        listar_hojas(ss_id_cash)

    print("\n" + "="*60)
    print("PASO 3: Construir preview de renombrado")
    print("="*60)

    pares_fr    = []
    fundreq_id  = None
    patron_fundreq = None
    hojas_cash  = []

    if ss_id_cash:
        hojas_cash = listar_hojas(ss_id_cash)

        import re as _re
        patron_cgecash = _re.compile(r"^CGE Cash management \d{2}\.\d{2}$")
        patron_fundreq  = _re.compile(r"^Fund Request \d{2}\.\d{2}$")

        # Encontrar ids de hojas padre
        summary_id   = None
        fundreq_id   = None
        for h in hojas_cash:
            nombre = h.get("name", "").strip()
            if nombre == "CGE Cash management - Summary":
                summary_id = h["id"]
            elif nombre == "Fund Request":
                fundreq_id = h["id"]

        print(f"\n  CGE Cash management - Summary id : {summary_id}")
        print(f"  Fund Request id                  : {fundreq_id}")

        # Obtener bases del paso 1
        bases = []
        if ss_id_bases:
            hojas_b = listar_hojas(ss_id_bases)
            if hojas_b:
                bases = leer_rango(ss_id_bases, hojas_b[0]["id"], "E2:E50")

        def construir_pares(parent_id, patron, prefijo):
            """Filtra subhojas del parent dado, ordena y mapea con bases."""
            hijos = []
            for h in hojas_cash:
                pid = h.get("parentId") or (h.get("parent") or {}).get("id", "")
                if pid == parent_id and patron.match(h.get("name", "")):
                    hijos.append(h)
            hijos.sort(key=lambda h: h.get("name", ""))
            pares = []
            for i, h in enumerate(hijos):
                actual = h.get("name", "")
                nuevo  = f"{prefijo} {bases[i]}" if i < len(bases) and bases[i] else actual
                pid_h  = h.get("parentId") or (h.get("parent") or {}).get("id", "")
                idx    = h.get("index") or h.get("position") or i
                pares.append((h["id"], actual, nuevo, pid_h, idx))
            return pares

        pares_cge = construir_pares(summary_id, patron_cgecash, "CGE Cash management") if summary_id else []
        pares_fr  = construir_pares(fundreq_id,  patron_fundreq,  "Fund Request")        if fundreq_id  else []
        subhojas  = [h for h in hojas_cash
                     if (h.get("parentId") or (h.get("parent") or {}).get("id","")) == summary_id
                     and patron_cgecash.match(h.get("name",""))]
        subhojas.sort(key=lambda h: h.get("name",""))

        todos_pares = pares_cge + pares_fr

        print(f"\n  {'#':<4} {'Nombre actual':<38} {'Nombre nuevo':<38} Cambio")
        print(f"  {'-'*4} {'-'*38} {'-'*38} ------")
        for i, (sid, actual, nuevo, pid, idx) in enumerate(todos_pares):
            cambia = "SI" if actual != nuevo else "-"
            print(f"  {i+1:<4} {actual:<38} {nuevo:<38} {cambia}")

        n_cambios = sum(1 for _, a, n, _, _ in todos_pares if a != n)
        print(f"\n  CGE Cash management: {len(pares_cge)} subhojas")
        print(f"  Fund Request       : {len(pares_fr)} subhojas")
        print(f"  Total cambios      : {n_cambios}")

        if n_cambios > 0:
            resp = input("\n  ¿Aplicar cambios en Workiva? (s/n): ").strip().lower()
            if resp == "s":
                print()
                for sheet_id, actual, nuevo, pid, idx in todos_pares:
                    if actual == nuevo:
                        continue
                    body = {"name": nuevo, "index": idx}
                    if pid:
                        body["parent"] = {"id": pid}
                    st, data = api_patch(
                        f"/platform/v1/spreadsheets/{ss_id_cash}/sheets/{sheet_id}",
                        body
                    )
                    if st in (200, 204, 202):
                        print(f"  OK  {actual} -> {nuevo}")
                    else:
                        st2, data2 = api_put(
                            f"/platform/v1/spreadsheets/{ss_id_cash}/sheets/{sheet_id}",
                            body
                        )
                        if st2 in (200, 204, 202):
                            print(f"  OK  {actual} -> {nuevo} (via PUT)")
                        else:
                            print(f"  ERR {actual} -> PATCH:{st} {data} PUT:{st2} {data2}")
                    time.sleep(0.25)
                print("\n  Proceso terminado.")
            else:
                print("  Cancelado.")

    print("\n" + "="*60)
    print("PASO 4: Limpiar rangos de datos manuales")
    print("="*60)

    RANGOS_LIMPIAR = [
        "D9:J15",
        "M9:N15",
        "D24:J26",
        "M24:N26",
        "Q9:R15",
        "Q18:R19",
        "Q24:R26",
    ]

    def vacias(rango):
        """Genera matriz de strings vacios para el rango dado."""
        col_ini = ord(rango[0]) - 64
        col_fin = ord(rango.split(":")[1][0]) - 64
        fila_ini = int(rango.split(":")[0][1:])
        fila_fin = int(rango.split(":")[1][1:])
        ncols = col_fin - col_ini + 1
        nfilas = fila_fin - fila_ini + 1
        return [[""] * ncols for _ in range(nfilas)]

    if ss_id_cash and subhojas:
        print(f"\n  Rangos a limpiar por hoja: {RANGOS_LIMPIAR}")
        print(f"  Hojas a limpiar: {len(subhojas)}")
        resp2 = input("\n  ¿Limpiar rangos en todas las subhojas? (s/n): ").strip().lower()
        if resp2 == "s":
            for h in subhojas:
                sheet_id = h["id"]
                nombre   = h.get("name", sheet_id)
                print(f"\n  Limpiando: {nombre}")
                for rango in RANGOS_LIMPIAR:
                    vals = vacias(rango)
                    st, resp_data = api_put(
                        f"/platform/v1/spreadsheets/{ss_id_cash}/sheets/{sheet_id}/values/{rango}",
                        {"values": vals}
                    )
                    estado = "OK" if st in (200, 202, 204) else f"ERR {st}"
                    print(f"    {rango}: {estado}")
                    time.sleep(0.1)
            print("\n  Limpieza terminada.")
        else:
            print("  Cancelado.")
    else:
        print("  No hay subhojas cargadas para limpiar.")

    print("\n" + "="*60)
    print("PASO 5: Limpiar rangos Fund Request (celdas sin formula)")
    print("="*60)

    # Rangos exactos que NO contienen formulas (solo datos manuales)
    RANGOS_FUNDREQ = [
        "F4:L8",   "F10:L14",  "F16:L20",  "F22:L26",
        "F28:L32", "F36:L40",  "F42:L46",  "F48:L52",
        "F54:L58",
        "P4:Q8",   "P11:Q15",
        "V4:V8",   "V11:V14",
    ]

    if ss_id_cash and pares_fr:
        hojas_fr = [h for h in hojas_cash
                    if (h.get("parentId") or (h.get("parent") or {}).get("id","")) == fundreq_id
                    and patron_fundreq.match(h.get("name",""))]
        hojas_fr.sort(key=lambda h: h.get("name",""))

        print(f"\n  Rangos a limpiar: {RANGOS_FUNDREQ}")
        print(f"  Subhojas Fund Request: {len(hojas_fr)}")
        resp3 = input("\n  ¿Limpiar rangos Fund Request? (s/n): ").strip().lower()
        if resp3 == "s":
            for h in hojas_fr:
                sheet_id = h["id"]
                nombre   = h.get("name", sheet_id)
                print(f"\n  Limpiando: {nombre}")
                for rango in RANGOS_FUNDREQ:
                    vals = vacias(rango)
                    st, resp_data = api_put(
                        f"/platform/v1/spreadsheets/{ss_id_cash}/sheets/{sheet_id}/values/{rango}",
                        {"values": vals}
                    )
                    estado = "OK" if st in (200, 202, 204) else f"ERR {st} {resp_data}"
                    print(f"    {rango}: {estado}")
                    time.sleep(0.1)
            print("\n  Limpieza Fund Request terminada.")
        else:
            print("  Cancelado.")
    else:
        print("  No hay subhojas Fund Request cargadas para limpiar.")

    print("\n" + "="*60)
    print("FIN")
    print("="*60)

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        import traceback
        print(f"\nERROR FATAL: {e}")
        traceback.print_exc()
    input("\nPresiona Enter para salir...")
