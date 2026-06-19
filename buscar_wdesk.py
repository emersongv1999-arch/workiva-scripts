import warnings
from urllib3.exceptions import InsecureRequestWarning
warnings.filterwarnings("ignore", category=InsecureRequestWarning)
from workiva_client import get_session

WDESK_BASE = "https://api.app.wdesk.com"
WORKSPACE_ID = "w_34913aadaa38420eabd7e4d341b78a1a"

session = get_session()
session.headers.update({"X-Version": "2022-01-01"})

# Traer todos los archivos (paginando)
print("Buscando archivos CGE 2024/2025 en wdesk...\n")
all_files = []
cursor = None
while True:
    url = WDESK_BASE + "/platform/v1/files?workspaceId=" + WORKSPACE_ID + "&limit=100"
    if cursor:
        url += "&cursor=" + cursor
    r = session.get(url, timeout=30)
    data = r.json()
    items = data.get("data", [])
    all_files.extend(items)
    cursor = data.get("meta", {}).get("nextCursor") or data.get("nextCursor")
    if not cursor or not items:
        break

print("Total archivos encontrados: " + str(len(all_files)))

# Filtrar por nombres relevantes
keywords = ["2024", "2025", "estado", "resultado", "utilidad", "fecu", "eeff", "ee.ff", "financier"]
relevantes = []
for f in all_files:
    name = f.get("name","").lower()
    if any(k in name for k in keywords):
        relevantes.append(f)

print("Archivos relevantes: " + str(len(relevantes)) + "\n")
for f in sorted(relevantes, key=lambda x: x.get("name","")):
    print("  [" + f.get("kind","") + "] " + f.get("name","") + " (" + f.get("id","") + ")")
