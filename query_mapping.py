import warnings
import time
from urllib3.exceptions import InsecureRequestWarning
warnings.filterwarnings("ignore", category=InsecureRequestWarning)

from workiva_client import get_session, BASE_URL

TABLE_ID = "c1368f2aa16e466793ad8a6373454ed1"

session = get_session()

# 1. Crear query temporal
print("Creando query...")
r = session.post(BASE_URL + "/api/v1/query", json={
    "queryText": "SELECT * FROM " + TABLE_ID,
    "name": "mapping_select_all",
    "temporary": True
}, timeout=30)
if r.status_code not in (200, 201):
    print("Error creando query: " + str(r.status_code) + " " + r.text[:300])
    exit(1)
query_id = r.json().get("body", {}).get("id", "")
print("Query creada: " + query_id)

# 2. Ejecutar query
print("Ejecutando...")
r2 = session.post(BASE_URL + "/api/v1/queryresult", json={
    "queryId": query_id
}, timeout=30)
if r2.status_code not in (200, 201):
    print("Error ejecutando: " + str(r2.status_code) + " " + r2.text[:300])
    exit(1)
result_id = r2.json().get("body", {}).get("id", "")
print("Result ID: " + result_id)

# 3. Polling hasta COMPLETED
print("Esperando resultado...")
for i in range(30):
    time.sleep(2)
    r3 = session.get(BASE_URL + "/api/v1/queryresult/" + result_id, timeout=30)
    body = r3.json().get("body", {})
    status = body.get("status", "")
    print("  [" + str(i+1) + "] Status: " + status)
    if status in ("COMPLETED", "COMPLETE"):
        print("Filas: " + str(body.get("rowsReturned", 0)))
        break
    if status == "ERROR":
        print("Error: " + str(body.get("error", "")))
        exit(1)
else:
    print("Timeout")
    exit(1)

# 4. Descargar CSV
print("\nDescargando datos...")
r4 = session.get(BASE_URL + "/api/v1/queryresult/" + result_id + "/download", timeout=60)
if r4.status_code == 200:
    lines = r4.text.strip().split("\n")
    print("Total filas (incluye header): " + str(len(lines)))
    print("\n" + "=" * 100)
    for line in lines[:51]:
        print(line)
    if len(lines) > 51:
        print("\n... (" + str(len(lines) - 51) + " filas mas)")
else:
    print("Error descarga: " + str(r4.status_code) + " " + r4.text[:300])
