import warnings
from urllib3.exceptions import InsecureRequestWarning
warnings.filterwarnings("ignore", category=InsecureRequestWarning)
from workiva_client import get_session

WDESK_BASE = "https://api.app.wdesk.com"
session = get_session()
session.headers.update({"X-Version": "2022-01-01"})

SS_ID   = "1a198bca66b144218e3c70325d39a1c5"
SHEET_ID = "e2e6af1fd78f4e6fb5d53c8e601afd79"  # C.- Estado de resultado por función

url = (WDESK_BASE
    + "/platform/v1/spreadsheets/" + SS_ID
    + "/sheets/" + SHEET_ID
    + "/sheetdata?$fields=cells.calculatedValue&$maxcellsperpage=50000")

r = session.get(url, timeout=60)
print("Status: " + str(r.status_code))

if r.status_code != 200:
    print(r.text[:300])
    exit(1)

cells_grid = r.json().get("data", {}).get("cells", [])
print("Filas: " + str(len(cells_grid)))
print()

# Buscar filas que contengan "utilidad" o valores numéricos relevantes
keywords = ["utilidad", "resultado", "ganancia", "perdida", "impuest", "ejercicio", "neto"]
for i, row in enumerate(cells_grid):
    vals = [str(c.get("calculatedValue","") if isinstance(c, dict) else "") for c in row]
    row_text = " | ".join(v for v in vals if v.strip())
    if row_text.strip():
        low = row_text.lower()
        if any(k in low for k in keywords) or i < 10:
            print(f"Fila {i+1:3d}: {row_text[:120]}")
