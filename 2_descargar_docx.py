"""
PASO 2 — Exportar y descargar cada documento de junio 2026 como .docx.
Lee documentos_junio_2026.json generado en el paso 1.

Uso:
    python 2_descargar_docx.py

Los archivos se guardan en la carpeta ./docx_junio_2026/
"""
import json
import time
import os
import warnings
from urllib3.exceptions import InsecureRequestWarning
warnings.filterwarnings("ignore", category=InsecureRequestWarning)

from workiva_client import get_session, WDESK_BASE

INPUT_FILE  = "documentos_junio_2026.json"
OUTPUT_DIR  = "docx_junio_2026"
POLL_WAIT   = 3    # segundos entre polls
MAX_POLLS   = 40   # máximo intentos por documento


def exportar_documento(session, doc_id):
    """Inicia export, hace polling y devuelve la URL de descarga."""
    r = session.post(
        f"{WDESK_BASE}/platform/v1/documents/{doc_id}/export",
        json={"format": "docx"},
        timeout=30,
    )
    if r.status_code != 202:
        raise RuntimeError(f"Export falló: {r.status_code} {r.text[:200]}")

    location = r.headers.get("Location", "")
    if not location:
        raise RuntimeError("No se recibió Location header")

    for i in range(MAX_POLLS):
        time.sleep(POLL_WAIT)
        rp = session.get(location, timeout=30)
        rp.raise_for_status()
        data = rp.json()
        status = data.get("status", "")
        if status == "completed":
            return data.get("resourceUrl", "")
        if "fail" in status.lower() or "error" in status.lower():
            raise RuntimeError(f"Export error: {data}")

    raise RuntimeError("Timeout esperando export")


def main():
    if not os.path.exists(INPUT_FILE):
        print(f"No se encontró {INPUT_FILE}. Ejecuta primero: python 1_listar_documentos_junio.py")
        return

    with open(INPUT_FILE, encoding="utf-8") as f:
        documentos = json.load(f)

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    session = get_session()

    resultados = []
    for i, doc in enumerate(documentos, 1):
        nombre = doc["nombre"]
        doc_id = doc["id"]
        # Nombre de archivo seguro para Windows
        nombre_archivo = nombre.replace("/", "-").replace("\\", "-").replace(":", "-")
        ruta = os.path.join(OUTPUT_DIR, f"{nombre_archivo}.docx")

        if os.path.exists(ruta):
            print(f"[{i}/{len(documentos)}] Ya existe, saltando: {nombre_archivo}.docx")
            resultados.append({"id": doc_id, "nombre": nombre, "archivo": ruta, "ok": True})
            continue

        print(f"[{i}/{len(documentos)}] Exportando: {nombre}...")
        try:
            download_url = exportar_documento(session, doc_id)
            rd = session.get(download_url, timeout=120)
            rd.raise_for_status()
            with open(ruta, "wb") as f:
                f.write(rd.content)
            kb = len(rd.content) // 1024
            print(f"  ✓ Guardado ({kb} KB): {ruta}")
            resultados.append({"id": doc_id, "nombre": nombre, "archivo": ruta, "ok": True})
        except Exception as e:
            print(f"  ✗ Error: {e}")
            resultados.append({"id": doc_id, "nombre": nombre, "archivo": None, "ok": False, "error": str(e)})

    ok  = sum(1 for r in resultados if r["ok"])
    err = len(resultados) - ok
    print(f"\nDescarga completada: {ok} OK, {err} errores")
    print("Ejecuta ahora: python 3_verificar_sumas.py")


if __name__ == "__main__":
    main()
