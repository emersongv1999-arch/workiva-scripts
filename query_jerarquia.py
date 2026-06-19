import warnings, time
from urllib3.exceptions import InsecureRequestWarning
warnings.filterwarnings("ignore", category=InsecureRequestWarning)
from workiva_client import get_session, BASE_URL

TABLE_ID = "42da53bbb90548d8b9ed054a06fa73b4"
session = get_session()

# Esquema
r = session.get(BASE_URL + "/api/v1/table/" + TABLE_ID, timeout=30)
tabla = r.json().get("body", {})
print("Tabla: " + tabla.get("name", ""))
print("Actualizada: " + str(tabla.get("updated", ""))[:19])
print("Columnas:")
for c in tabla.get("tableSchema", {}).get("columns", []):
    print("  " + c.get("name", "") + " [" + c.get("type", "") + "]")

# Crear query
r2 = session.post(BASE_URL + "/api/v1/query",
    json={"queryText": 'SELECT * FROM "' + TABLE_ID + '"', "name": "jerarquia_v2", "temporary": True}, timeout=30)
if r2.status_code not in (200, 201):
    print("Error creando query: " + r2.text[:300])
    exit(1)
query_id = r2.json().get("body", {}).get("id", "")

# Ejecutar
r3 = session.post(BASE_URL + "/api/v1/queryresult", json={"queryId": query_id}, timeout=30)
result_id = r3.json().get("body", {}).get("id", "")

# Polling
print("\nEjecutando query...")
for i in range(30):
    time.sleep(2)
    r4 = session.get(BASE_URL + "/api/v1/queryresult/" + result_id, timeout=30)
    body = r4.json().get("body", {})
    status = body.get("status", "")
    if status in ("COMPLETED", "COMPLETE"):
        print("Filas: " + str(body.get("rowsReturned", 0)))
        break
    if status == "ERROR":
        print("Error: " + str(body.get("error", "")))
        exit(1)

# Descargar
r5 = session.get(BASE_URL + "/api/v1/queryresult/" + result_id + "/download", timeout=60)
lines = r5.text.strip().split("\n")
print("\n" + "=" * 100)
for line in lines[:51]:
    print(line)
if len(lines) > 51:
    print("\n... (" + str(len(lines) - 51) + " filas mas)")
