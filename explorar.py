import warnings
from urllib3.exceptions import InsecureRequestWarning
warnings.filterwarnings("ignore", category=InsecureRequestWarning)

from workiva_client import get_session, BASE_URL

session = get_session()

# Tablas incluyendo compartidas
r = session.get(BASE_URL + "/api/v1/table?includeShared=true&limit=100", timeout=30)
tablas = r.json().get("body", [])
print("Tablas disponibles (incluyendo compartidas): " + str(len(tablas)))
for t in tablas:
    print("  [" + t.get("id", "") + "] " + t.get("name", "") + " | actualizada: " + str(t.get("updated", ""))[:10])

# Carpetas
r2 = session.get(BASE_URL + "/api/v1/folder?limit=100", timeout=30)
carpetas = r2.json().get("body", [])
print("\nCarpetas: " + str(len(carpetas)))
for c in carpetas:
    print("  [" + c.get("id", "") + "] " + c.get("name", ""))

# Archivos
r3 = session.get(BASE_URL + "/api/v1/file?limit=100", timeout=30)
print("\nStatus archivos: " + str(r3.status_code))
if r3.status_code == 200:
    archivos = r3.json().get("body", [])
    print("Archivos: " + str(len(archivos)))
    for a in archivos[:10]:
        print("  [" + a.get("id", "") + "] " + a.get("name", ""))
