"""
PASO 1 — Listar todos los documentos de junio 2026 en Workiva.
Genera un archivo JSON con los IDs y nombres para los pasos siguientes.

Uso:
    python 1_listar_documentos_junio.py
"""
import json
import warnings
from urllib3.exceptions import InsecureRequestWarning
warnings.filterwarnings("ignore", category=InsecureRequestWarning)

from workiva_client import get_session, WDESK_BASE

KEYWORDS_JUNIO = ["06-2026", "junio 2026", "jun 2026", "06/2026"]
OUTPUT_FILE = "documentos_junio_2026.json"


def main():
    session = get_session()
    print("Buscando documentos en Workiva...")

    all_docs = []
    url = f"{WDESK_BASE}/platform/v1/documents?$top=100"
    page = 0
    while url:
        r = session.get(url, timeout=30)
        r.raise_for_status()
        data = r.json()
        items = data.get("value", data.get("data", []))
        all_docs.extend(items)
        url = data.get("@nextLink") or data.get("nextLink")
        page += 1

    print(f"Total documentos en workspace: {len(all_docs)}")

    junio = [
        {"id": d["id"], "nombre": d["name"]}
        for d in all_docs
        if any(k.lower() in d.get("name", "").lower() for k in KEYWORDS_JUNIO)
    ]

    junio.sort(key=lambda x: x["nombre"])
    print(f"\nDocumentos junio 2026 encontrados: {len(junio)}")
    for d in junio:
        print(f"  [{d['id']}] {d['nombre']}")

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(junio, f, ensure_ascii=False, indent=2)

    print(f"\nGuardado en: {OUTPUT_FILE}")
    print("Ejecuta ahora: python 2_descargar_docx.py")


if __name__ == "__main__":
    main()
