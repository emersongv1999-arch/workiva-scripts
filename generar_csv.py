#!/usr/bin/env python3
"""
Genera los CSV de los cuadros XBRL sin pasar por Excel ni por la macro.

Reemplaza al boton "Crear CSV" / "Crear/Comprimir CSV" de las plantillas de
DBNeT, que en la practica es fragil: calcula la carpeta destino cortandole
tres letras al nombre de la carpeta actual (da por hecho que se llama 'xls'),
necesita un zip.exe al lado y no funciona si el libro se abre desde OneDrive.

Que hace la macro y se replica aqui
-----------------------------------
Una CSV por hoja, con el nombre de la hoja, y todas juntas en csv.zip.
La macro guarda con FileFormat:=xlCSVWindows y Local:=True, o sea con la
configuracion regional de Windows: en Chile separador ';' y coma decimal.
Y Excel escribe el valor COMO SE VE, no el crudo: una celda con formato
'#,##0' sale como 22.683.150.240.

  OJO: esto reproduce el comportamiento documentado de Excel, no esta
  contrastado contra un csv.zip real de DBNeT. Si tienes uno que ya te
  hayan aceptado, comparalo: la diferencia esperable esta en el formato de
  los numeros. Con --crudo salen sin separador de miles.

Uso:
    python generar_csv.py --origen E211_LLENADO.xlsm --salida csv
    python generar_csv.py --origen ./salida --salida csv --zip csv.zip
    python generar_csv.py --origen E211_LLENADO.xlsm --salida csv --crudo
"""

import argparse
import datetime
import re
import sys
import zipfile
from pathlib import Path

CELDA_RE = re.compile(r'<c r="([A-Z]+)(\d+)"([^>]*?)(?:/>|>(.*?)</c>)', re.S)

SEP = ";"          # separador de listas de Windows en Chile
DECIMAL = ","
MILES = "."


def col_a_num(col):
    n = 0
    for ch in col:
        n = n * 26 + (ord(ch) - 64)
    return n


def desescapa(s):
    return (s.replace("&lt;", "<").replace("&gt;", ">").replace("&quot;", '"')
             .replace("&apos;", "'").replace("&#xA;", "\n").replace("&#x9;", "\t")
             .replace("&amp;", "&"))


def es_fecha(fmt):
    limpio = re.sub(r'\[[^\]]*\]|"[^"]*"', "", fmt or "")
    return bool(re.search(r"[dmyhs]", limpio, re.I)) and "General" not in (fmt or "")


def numero_a_texto(valor, fmt, crudo=False):
    """Como lo escribiria Excel con la configuracion regional chilena."""
    try:
        n = float(valor)
    except (TypeError, ValueError):
        return str(valor)

    if es_fecha(fmt):
        # serial de Excel; el sistema de 1900 arrastra el bug del 29-feb-1900
        try:
            f = datetime.datetime(1899, 12, 30) + datetime.timedelta(days=n)
            return f.strftime("%d-%m-%Y") if n == int(n) else f.strftime("%d-%m-%Y %H:%M")
        except (OverflowError, ValueError):
            pass

    cuerpo = (fmt or "General").split(";")[0]
    m = re.search(r"\.(0+)", cuerpo)
    decimales = len(m.group(1)) if m else (0 if re.search(r"[#0]", cuerpo) else None)
    if crudo or decimales is None:
        texto = ("%d" % n) if n == int(n) else repr(n)
        return texto.replace(".", DECIMAL)

    texto = "%.*f" % (decimales, abs(n))
    entera, _, frac = texto.partition(".")
    if "#,##" in cuerpo or "," in cuerpo.replace("#,##", ""):
        grupos = []
        while len(entera) > 3:
            grupos.insert(0, entera[-3:])
            entera = entera[:-3]
        grupos.insert(0, entera)
        entera = MILES.join(grupos)
    signo = "-" if n < 0 else ""
    return signo + entera + ((DECIMAL + frac) if frac else "")


def campo(texto):
    """Entrecomillado al estilo de Excel."""
    if texto is None:
        return ""
    if any(c in texto for c in (SEP, '"', "\n", "\r")):
        return '"' + texto.replace('"', '""') + '"'
    return texto


def es_cuadro(xml, shared):
    """Lleva URIs de taxonomia en alguna celda. Sirve tanto si el texto va
    inline (asi queda el libro fusionado) como si va en sharedStrings."""
    if ".xsd#" in xml:
        return True
    return any(".xsd#" in (shared[int(i)] if int(i) < len(shared) else "")
               for i in re.findall(r't="s"[^>]*><v>(\d+)</v>', xml))


class Hoja:
    def __init__(self, z, parte, shared, fmt_por_estilo):
        self.filas = {}
        xml = z.read(parte).decode("utf-8")
        for col, fila, attrs, cuerpo in CELDA_RE.findall(xml):
            cuerpo = cuerpo or ""
            mt = re.search(r't="(\w+)"', attrs)
            tipo = mt.group(1) if mt else None
            ms = re.search(r's="(\d+)"', attrs)
            fmt = fmt_por_estilo.get(int(ms.group(1)) if ms else 0, "General")
            if tipo == "inlineStr":
                val = desescapa("".join(re.findall(r"<t[^>]*>(.*?)</t>", cuerpo, re.S)))
            else:
                mv = re.search(r"<v>(.*?)</v>", cuerpo, re.S)
                if mv is None:
                    continue
                val = mv.group(1)
                if tipo == "s":
                    i = int(val) if val.isdigit() else -1
                    val = shared[i] if 0 <= i < len(shared) else ""
                elif tipo in (None, "n"):
                    val = numero_a_texto(desescapa(val), fmt, Hoja.crudo)
                else:
                    val = desescapa(val)
            if val == "":
                continue
            self.filas.setdefault(int(fila), {})[col_a_num(col)] = val

    def texto(self):
        if not self.filas:
            return ""
        ultima = max(self.filas)
        salida = []
        for f in range(1, ultima + 1):
            cols = self.filas.get(f, {})
            ancho = max(cols) if cols else 0
            salida.append(SEP.join(campo(cols.get(c)) for c in range(1, ancho + 1)))
        return "\r\n".join(salida) + "\r\n"


Hoja.crudo = False


def formatos(z):
    """{indice de cellXf: codigo de formato}"""
    integrados = {0: "General", 1: "0", 2: "0.00", 3: "#,##0", 4: "#,##0.00",
                  9: "0%", 10: "0.00%", 14: "dd-mm-yyyy", 15: "d-mmm-yy",
                  16: "d-mmm", 17: "mmm-yy", 22: "dd-mm-yyyy hh:mm",
                  37: "#,##0 ;(#,##0)", 38: "#,##0 ;[Red](#,##0)",
                  39: "#,##0.00;(#,##0.00)", 40: "#,##0.00;[Red](#,##0.00)"}
    s = z.read("xl/styles.xml").decode("utf-8")
    propios = dict(re.findall(r'<numFmt numFmtId="(\d+)" formatCode="([^"]*)"', s))
    m = re.search(r"<cellXfs[^>]*>(.*?)</cellXfs>", s, re.S)
    out = {}
    if m:
        for i, xf in enumerate(re.findall(r"<xf(?:\s[^>]*?)?/>|<xf(?:\s[^>]*?)?>.*?</xf>",
                                          m.group(1), re.S)):
            mid = re.search(r'numFmtId="(\d+)"', xf)
            idv = mid.group(1) if mid else "0"
            out[i] = desescapa(propios.get(idv, integrados.get(int(idv), "General")))
    return out


def csv_de_libro(ruta, solo_cuadros=True):
    """{nombre de hoja: texto csv}"""
    z = zipfile.ZipFile(ruta)
    try:
        ss = z.read("xl/sharedStrings.xml").decode("utf-8")
    except KeyError:
        ss = ""
    shared = [desescapa("".join(re.findall(r"<t[^>]*>(.*?)</t>", si, re.S)))
              for si in re.findall(r"<si>(.*?)</si>", ss, re.S)]
    fmt = formatos(z)
    rels = dict(re.findall(r'Id="(rId\d+)"[^>]*Target="([^"]*)"',
                           z.read("xl/_rels/workbook.xml.rels").decode("utf-8")))
    out = {}
    for tag in re.findall(r"<sheet [^>]*?>", z.read("xl/workbook.xml").decode("utf-8")):
        nombre = desescapa(re.search(r'name="([^"]*)"', tag).group(1))
        destino = rels[re.search(r'r:id="(rId\d+)"', tag).group(1)].lstrip("/")
        parte = destino if destino.startswith("xl/") else "xl/" + destino
        crudo_xml = z.read(parte).decode("utf-8")
        if solo_cuadros and not es_cuadro(crudo_xml, shared):
            continue
        out[nombre] = Hoja(z, parte, shared, fmt).texto()
    return out


def main():
    p = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--origen", required=True,
                   help="un .xlsm/.xlsx, o una carpeta con varios")
    p.add_argument("--salida", default="csv", help="carpeta donde dejar los .csv")
    p.add_argument("--zip", dest="zip_", help="ademas, empaquetar todo en este .zip")
    p.add_argument("--crudo", action="store_true",
                   help="numeros sin separador de miles")
    p.add_argument("--todas", action="store_true",
                   help="incluir tambien las hojas que no son cuadros")
    args = p.parse_args()

    Hoja.crudo = args.crudo
    origen = Path(args.origen)
    libros = ([p for p in sorted(origen.rglob("*.xls[mx]"))
               if not p.name.startswith("~$")] if origen.is_dir() else [origen])
    if not libros:
        sys.exit(f"No hay libros en {origen}")

    destino = Path(args.salida)
    destino.mkdir(parents=True, exist_ok=True)
    total = 0
    for libro in libros:
        hojas = csv_de_libro(libro, not args.todas)
        for nombre, texto in hojas.items():
            seguro = re.sub(r'[\\\\/:*?"<>|]', "_", nombre).strip()
            (destino / (seguro + ".csv")).write_bytes(
                texto.encode("cp1252", errors="replace"))
            total += 1
        if len(libros) > 1:
            print(f"  {libro.name[:52]:54} {len(hojas):3} csv")
    print(f"\n{total} archivos .csv en {destino}")

    if args.zip_:
        with zipfile.ZipFile(args.zip_, "w", zipfile.ZIP_DEFLATED) as z:
            for f in sorted(destino.glob("*.csv")):
                z.write(f, f.name)          # -j de la macro: sin rutas
        print(f"Empaquetados en {args.zip_} "
              f"({Path(args.zip_).stat().st_size/1024:.0f} KB)")


if __name__ == "__main__":
    main()
