"""
verificar_eeff.py — Verificador interactivo de sumas en EE.FF. Workiva

Pregunta periodo, año e idioma, muestra los documentos disponibles para
que elijas cuáles verificar, y escribe el resultado directo en el
spreadsheet "Verificación de sumas" del workspace.

Uso:
    python verificar_eeff.py
"""
import os
import re
import sys
import time
import warnings
from pathlib import Path

from urllib3.exceptions import InsecureRequestWarning
warnings.filterwarnings("ignore", category=InsecureRequestWarning)

try:
    from docx import Document as DocxDocument
except ImportError:
    print("Falta librería: pip install python-docx")
    sys.exit(1)

from workiva_client import get_session, WDESK_BASE

# ---------------------------------------------------------------------------
# Constantes
# ---------------------------------------------------------------------------

MESES = {
    "1":"01","01":"01","enero":"01",
    "2":"02","02":"02","febrero":"02",
    "3":"03","03":"03","marzo":"03",
    "4":"04","04":"04","abril":"04",
    "5":"05","05":"05","mayo":"05",
    "6":"06","06":"06","junio":"06",
    "7":"07","07":"07","julio":"07",
    "8":"08","08":"08","agosto":"08",
    "9":"09","09":"09","septiembre":"09",
    "10":"10","octubre":"10",
    "11":"11","noviembre":"11",
    "12":"12","diciembre":"12",
}

NOMBRE_MES = {
    "01":"Enero","02":"Febrero","03":"Marzo","04":"Abril",
    "05":"Mayo","06":"Junio","07":"Julio","08":"Agosto",
    "09":"Septiembre","10":"Octubre","11":"Noviembre","12":"Diciembre",
}

# Palabras que identifican una fila de total en las tablas EEFF
TOTAL_KEYWORDS = [
    "total activos","total pasivos","total patrimonio",
    "total activos corrientes","total activos no corrientes",
    "total pasivos corrientes","total pasivos no corrientes",
    "ganancia bruta","ganancia (pérdida)","resultado del periodo",
    "resultado integral","total flujos","total cambios",
    "total","subtotal",
]

SS_VERIF_NAME = "verificación de sumas"   # nombre del spreadsheet destino
DOCX_DIR      = Path("docx_tmp_verif")    # carpeta temporal de descarga


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
            print("  No puede estar vacío.")


def seleccionar_docs(docs):
    """Muestra lista y pide S/N por archivo o TODOS/NINGUNO."""
    hr()
    print(f"  {len(docs)} documento(s) encontrado(s):\n")
    for i, d in enumerate(docs, 1):
        print(f"  {i:>2}. {d['nombre']}")
    hr()
    print()
    resp = input("  ¿Seleccionar todos? [TODOS / NINGUNO / elegir uno por uno]: ").strip().upper()
    if resp == "TODOS":
        print("  ✓ Todos seleccionados.")
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

def buscar_documentos(session, mes, anio, idioma):
    print("  Descargando catálogo de documentos...", end=" ", flush=True)
    all_docs = []
    url = f"{WDESK_BASE}/platform/v1/documents?$top=100"
    while url:
        r = session.get(url, timeout=30)
        r.raise_for_status()
        data = r.json()
        all_docs.extend(data.get("value", data.get("data", [])))
        url = data.get("@nextLink") or data.get("nextLink")
    print(f"{len(all_docs)} docs totales.")

    patrones_fecha = [f"{mes}-{anio}", f"{mes}/{anio}"]

    def ok_idioma(nombre):
        n = nombre.upper()
        if idioma == "AMBOS": return True
        return f"({idioma})" in n

    resultado = [
        {"id": d["id"], "nombre": d["name"]}
        for d in all_docs
        if any(p in d.get("name","") for p in patrones_fecha) and ok_idioma(d.get("name",""))
    ]
    resultado.sort(key=lambda x: x["nombre"])
    return resultado


# ---------------------------------------------------------------------------
# Workiva: buscar spreadsheet "Verificación de sumas"
# ---------------------------------------------------------------------------

def buscar_spreadsheet_verif(session):
    print("  Buscando spreadsheet de verificación...", end=" ", flush=True)
    url = f"{WDESK_BASE}/platform/v1/spreadsheets?$top=100"
    while url:
        r = session.get(url, timeout=30)
        data = r.json()
        for ss in data.get("value", data.get("data", [])):
            if SS_VERIF_NAME in ss.get("name","").lower():
                print(f"encontrado: '{ss['name']}'")
                return ss["id"]
        url = data.get("@nextLink") or data.get("nextLink")
    print("NO encontrado.")
    return None


def obtener_o_crear_hoja(session, ss_id, nombre_hoja):
    """Devuelve el sheet_id de la hoja con ese nombre; la crea si no existe."""
    r = session.get(f"{WDESK_BASE}/platform/v1/spreadsheets/{ss_id}/sheets?$top=50", timeout=30)
    for s in r.json().get("value", r.json().get("data", [])):
        if s.get("name","").lower() == nombre_hoja.lower():
            return s["id"]
    # Crear hoja nueva
    rc = session.post(
        f"{WDESK_BASE}/platform/v1/spreadsheets/{ss_id}/sheets",
        json={"name": nombre_hoja},
        timeout=30,
    )
    if rc.status_code not in (200, 201, 202):
        raise RuntimeError(f"No se pudo crear hoja '{nombre_hoja}': {rc.status_code} {rc.text[:150]}")
    nueva = rc.json()
    return nueva.get("id") or nueva.get("data",{}).get("id")


# ---------------------------------------------------------------------------
# Workiva: descargar .docx
# ---------------------------------------------------------------------------

def exportar_docx(session, doc):
    nombre_archivo = re.sub(r'[\\/:*?"<>|]', "-", doc["nombre"]) + ".docx"
    ruta = DOCX_DIR / nombre_archivo
    if ruta.exists():
        return ruta

    r = session.post(
        f"{WDESK_BASE}/platform/v1/documents/{doc['id']}/export",
        json={"format": "docx"}, timeout=30,
    )
    if r.status_code != 202:
        raise RuntimeError(f"{r.status_code} {r.text[:120]}")

    loc = r.headers.get("Location","")
    for _ in range(40):
        time.sleep(3)
        rp = session.get(loc, timeout=30)
        data = rp.json()
        if data.get("status") == "completed":
            rd = session.get(data["resourceUrl"], timeout=120)
            ruta.write_bytes(rd.content)
            return ruta
        if "fail" in data.get("status","").lower():
            raise RuntimeError(f"Export falló: {data}")
    raise RuntimeError("Timeout export")


# ---------------------------------------------------------------------------
# Verificación de sumas en tablas del .docx
# ---------------------------------------------------------------------------

def limpiar_numero(texto):
    t = texto.strip().replace("\xa0","").replace(" ","")
    if not t or t in ("-","—","–",""):
        return None
    neg = t.startswith("(") and t.endswith(")")
    t = t.strip("()")
    t = t.replace(".","").replace(",",".")
    try:
        v = float(t)
        return -v if neg else v
    except ValueError:
        return None


def es_fila_total(celdas):
    primera = celdas[0].lower().strip() if celdas else ""
    return any(kw in primera for kw in TOTAL_KEYWORDS)


def verificar_tablas(ruta):
    """
    Retorna lista de dicts:
      estado_financiero, descripcion, col_periodo, declarado, calculado, diferencia, ok
    """
    resultados = []
    doc = DocxDocument(ruta)

    estado_actual = "Documento"
    for idx, tabla in enumerate(doc.tables):
        filas = [[c.text.strip() for c in row.cells] for row in tabla.rows]
        if not filas:
            continue

        # Detectar nombre del estado financiero en la primera fila
        primera = " ".join(filas[0]).upper() if filas else ""
        if "ACTIVOS" in primera and "PATRIMONIO" not in primera:
            estado_actual = "Balance - Activos"
        elif "PATRIMONIO" in primera and "PASIVOS" in primera:
            estado_actual = "Balance - Patrimonio y Pasivos"
        elif "RESULTADO" in primera and "INTEGRAL" not in primera:
            estado_actual = "Estado de Resultados"
        elif "RESULTADO INTEGRAL" in primera or "INTEGRAL" in primera:
            estado_actual = "Resultado Integral"
        elif "CAMBIOS EN EL PATRIMONIO" in primera:
            estado_actual = "Cambios en el Patrimonio"
        elif "FLUJO" in primera or "EFECTIVO" in primera:
            estado_actual = "Flujo de Efectivo"

        num_cols = max(len(f) for f in filas)

        # Buscar encabezado de periodos (primera fila con fechas)
        periodos = [""] * num_cols
        for fila in filas[:4]:
            if any(re.search(r"\d{2}-\d{4}", c) for c in fila):
                periodos = fila + [""] * (num_cols - len(fila))
                break

        acum = [0.0] * num_cols
        tiene = [False] * num_cols

        for i, fila in enumerate(filas):
            while len(fila) < num_cols:
                fila.append("")

            if es_fila_total(fila):
                for col in range(1, num_cols):
                    dec = limpiar_numero(fila[col])
                    if dec is None or not tiene[col]:
                        continue
                    diff = round(dec - acum[col], 2)
                    ok = abs(diff) < 2
                    resultados.append({
                        "estado":      estado_actual,
                        "descripcion": fila[0][:70],
                        "periodo":     periodos[col] if col < len(periodos) else "",
                        "declarado":   dec,
                        "calculado":   round(acum[col], 2),
                        "diferencia":  diff,
                        "ok":          ok,
                    })
                acum = [0.0] * num_cols
                tiene = [False] * num_cols
            else:
                for col in range(1, num_cols):
                    v = limpiar_numero(fila[col]) if col < len(fila) else None
                    if v is not None:
                        acum[col] += v
                        tiene[col] = True

    return resultados


# ---------------------------------------------------------------------------
# Escribir resultados en Workiva
# ---------------------------------------------------------------------------

def put_range(session, ss_id, sheet_id, rango, values):
    """PUT values en un rango y hace polling hasta completado."""
    url = f"{WDESK_BASE}/platform/v1/spreadsheets/{ss_id}/sheets/{sheet_id}/values/{rango}"
    r = session.put(url, json={"values": values}, timeout=60)
    if r.status_code == 202:
        loc = r.headers.get("Location","")
        for _ in range(30):
            time.sleep(2)
            rp = session.get(loc, timeout=15)
            if rp.json().get("status") == "completed":
                return
        raise RuntimeError("Timeout escribiendo en Workiva")
    elif r.status_code not in (200,):
        raise RuntimeError(f"Error PUT {r.status_code}: {r.text[:150]}")


def escribir_resultados(session, ss_id, sheet_id, nombre_doc, resultados):
    """
    Escribe en la hoja:
      Col A: Documento
      Col B: Estado Financiero
      Col C: Descripción (línea total)
      Col D: Periodo
      Col E: Declarado
      Col F: Calculado
      Col G: Diferencia
      Col H: Estado (OK / REVISAR)
    """
    if not resultados:
        return

    rows = [
        [
            nombre_doc,
            r["estado"],
            r["descripcion"],
            r["periodo"],
            r["declarado"],
            r["calculado"],
            r["diferencia"],
            "OK" if r["ok"] else "REVISAR ◄",
        ]
        for r in resultados
    ]

    # Encontrar la primera fila vacía de la hoja
    url_read = (f"{WDESK_BASE}/platform/v1/spreadsheets/{ss_id}"
                f"/sheets/{sheet_id}/sheetdata?$fields=cells.calculatedValue&$maxcellsperpage=5000")
    r_read = session.get(url_read, timeout=30)
    cells = r_read.json().get("data", {}).get("cells", [])
    primera_vacia = len(cells) + 1  # 1-based

    rango = f"A{primera_vacia}:H{primera_vacia + len(rows) - 1}"
    put_range(session, ss_id, sheet_id, rango, rows)


def escribir_cabecera(session, ss_id, sheet_id):
    """Escribe cabecera si la hoja está vacía."""
    url_read = (f"{WDESK_BASE}/platform/v1/spreadsheets/{ss_id}"
                f"/sheets/{sheet_id}/sheetdata?$fields=cells.calculatedValue&$maxcellsperpage=5")
    r = session.get(url_read, timeout=30)
    cells = r.json().get("data", {}).get("cells", [])
    if cells:
        return  # ya tiene datos
    cabecera = [["Documento", "Estado Financiero", "Descripción Total",
                 "Periodo", "Declarado (M$)", "Calculado (M$)",
                 "Diferencia (M$)", "Estado"]]
    put_range(session, ss_id, sheet_id, "A1:H1", cabecera)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    hr("═")
    print("  VERIFICADOR DE SUMAS — EE.FF. WORKIVA")
    hr("═")

    # 1. Periodo
    print("\n  PERIODO\n")
    mes_raw = ask("  Mes (número o nombre, ej: 6 / junio)")
    mes = MESES.get(mes_raw.lower())
    while not mes:
        print(f"  Mes '{mes_raw}' no reconocido.")
        mes_raw = ask("  Mes")
        mes = MESES.get(mes_raw.lower())

    anio = ask("  Año (ej: 2026)")
    while not re.fullmatch(r"\d{4}", anio):
        print("  Año inválido.")
        anio = ask("  Año")

    # 2. Idioma
    print("\n  IDIOMA\n")
    idioma = ask("  Idioma", opts=["ESP","ENG","AMBOS"], default="AMBOS")

    # 3. Buscar documentos
    print(f"\n  Buscando {mes}-{anio} [{idioma}]...\n")
    session = get_session()
    docs = buscar_documentos(session, mes, anio, idioma)

    if not docs:
        print(f"\n  No hay documentos {mes}-{anio} [{idioma}] en Workiva.")
        sys.exit(0)

    # 4. Selección
    print()
    seleccionados = seleccionar_docs(docs)
    if not seleccionados:
        print("\n  Ningún documento seleccionado.")
        sys.exit(0)

    # 5. Buscar spreadsheet destino
    print()
    ss_id = buscar_spreadsheet_verif(session)
    if not ss_id:
        print(f"  No se encontró el spreadsheet '{SS_VERIF_NAME}'.")
        sys.exit(1)

    nombre_hoja = f"{NOMBRE_MES[mes]} {anio}"
    print(f"  Hoja destino: '{nombre_hoja}'")
    sheet_id = obtener_o_crear_hoja(session, ss_id, nombre_hoja)

    # Cabecera si la hoja está vacía
    escribir_cabecera(session, ss_id, sheet_id)

    # 6. Descargar y verificar cada documento
    DOCX_DIR.mkdir(exist_ok=True)
    hr()
    total_ok = 0
    total_err = 0

    for i, doc in enumerate(seleccionados, 1):
        print(f"\n  [{i}/{len(seleccionados)}] {doc['nombre']}")

        # Descargar
        print("    Exportando .docx...", end=" ", flush=True)
        try:
            ruta = exportar_docx(session, doc)
            print(f"OK ({ruta.stat().st_size//1024} KB)")
        except Exception as e:
            print(f"ERROR: {e}")
            continue

        # Verificar
        print("    Verificando sumas...", end=" ", flush=True)
        resultados = verificar_tablas(ruta)
        ok  = sum(1 for r in resultados if r["ok"])
        err = len(resultados) - ok
        total_ok  += ok
        total_err += err
        print(f"{len(resultados)} checks | OK: {ok} | REVISAR: {err}")

        # Escribir en Workiva
        print("    Escribiendo en Workiva...", end=" ", flush=True)
        try:
            escribir_resultados(session, ss_id, sheet_id, doc["nombre"], resultados)
            print("OK")
        except Exception as e:
            print(f"ERROR: {e}")

    # 7. Resumen final
    hr("═")
    print(f"\n  RESUMEN FINAL")
    print(f"  Documentos procesados : {len(seleccionados)}")
    print(f"  Verificaciones OK     : {total_ok}")
    print(f"  Para revisar          : {total_err}")
    print(f"\n  Resultados escritos en Workiva:")
    print(f"  Spreadsheet : {SS_VERIF_NAME}")
    print(f"  Hoja        : {nombre_hoja}")
    hr("═")


if __name__ == "__main__":
    main()
