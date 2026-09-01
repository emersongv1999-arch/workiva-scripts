#!/usr/bin/env python3
"""
Fusiona las hojas de cuadros XBRL de varios .xlsm en un unico .xlsx.

Pensado para el paso final: una vez que llenar_dbnet_desde_workiva.py escribio
los .xlsm de DBNeT con los datos de Workiva, este junta todas sus hojas de
cuadros en un solo libro para devolverselo a DBNeT.

Solo entran las hojas de cuadros: las que llevan URIs de taxonomia en la
columna C. Quedan fuera las hojas auxiliares de listas (codigo, Codigos,
Hoja3) y, por construccion, las hojas de notas del libro de trabajo.

Que se conserva y que no
------------------------
  SI   valores, formulas, formatos, anchos de columna, alto de fila,
       celdas combinadas y formato condicional
  NO   macros (un .xlsx no puede llevarlas), botones, imagenes,
       hipervinculos entre hojas y validaciones de datos: las listas
       desplegables apuntan a las hojas auxiliares, que no viajan

El trabajo real es reindexar los formatos. Cada libro tiene su propia
styles.xml y un s="16" no significa lo mismo en dos archivos distintos, asi
que hay que fusionar fuentes, rellenos, bordes y formatos de numero
deduplicando, y reescribir el indice de cada celda.

Uso:
    python fusionar_cuadros.py --origen ./salida --salida E211_XBRL.xlsx
"""

import argparse
import collections
import re
import sys
import zipfile
from pathlib import Path

CELDA_RE = re.compile(r'<c ([^>]*?)(?:/>|>(.*?)</c>)', re.S)

# lo que no puede viajar a un libro sin relaciones propias por hoja
FUERA = ("drawing", "legacyDrawing", "legacyDrawingHF", "picture", "oleObjects",
         "controls", "tableParts", "hyperlinks", "dataValidations", "extLst",
         "pageSetup")


_CACHE_TAG = {}


def elementos(xml, tag):
    """Cada <tag .../> o <tag ...>...</tag> de primer nivel, como texto.

    La forma auto-cerrada va primero a proposito: si se prueba antes la
    pareja, un <xf/> sin cierre hace que .*?</xf> siga buscando y se trague
    todos los elementos que vengan hasta el primer </xf> de verdad."""
    rx = _CACHE_TAG.get(tag)
    if rx is None:
        rx = _CACHE_TAG[tag] = re.compile(
            r"<%s(?:\s[^>]*?)?/>|<%s(?:\s[^>]*?)?>.*?</%s>" % (tag, tag, tag), re.S)
    return [m.group(0) for m in rx.finditer(xml)]


def elementos_contados(xml, contenedor, tag):
    """Como elementos(), pero contrasta contra el count= que declara el XML.

    Es la red de seguridad del parser: si vuelve a descuadrar, revienta aqui
    en vez de producir un libro con los formatos corridos."""
    lst = elementos(seccion(xml, contenedor), tag)
    m = re.search(r'<%s[^>]*count="(\d+)"' % contenedor, xml)
    if m and int(m.group(1)) != len(lst):
        raise ValueError(
            f"{contenedor}: el XML declara {m.group(1)} elementos <{tag}> "
            f"y se leyeron {len(lst)}")
    return lst


def seccion(xml, tag):
    m = re.search(r"<%s(?:\s[^>]*)?>(.*?)</%s>" % (tag, tag), xml, re.S)
    if m:
        return m.group(1)
    return "" if re.search(r"<%s(?:\s[^>]*)?/>" % tag, xml) else ""


def attr(txt, nombre, defecto="0"):
    m = re.search(r'%s="([^"]*)"' % nombre, txt)
    return m.group(1) if m else defecto


class Estilos:
    """Acumula los estilos de varios libros deduplicando."""

    def __init__(self):
        self.fonts, self.fills, self.borders = [], [], []
        self.cellStyleXfs, self.cellXfs, self.dxfs = [], [], []
        self.numFmts = {}                      # codigo -> id nuevo
        self._idx = {k: {} for k in
                     ("font", "fill", "border", "csxf", "xf", "dxf")}
        self._prox_fmt = 200

    def _mete(self, lista, clave, texto):
        d = self._idx[clave]
        if texto not in d:
            d[texto] = len(lista)
            lista.append(texto)
        return d[texto]

    def absorbe(self, styles_xml):
        """Devuelve (mapa_cellXfs, mapa_dxfs) del libro a los indices nuevos."""
        fuente = {
            "font": elementos_contados(styles_xml, "fonts", "font"),
            "fill": elementos_contados(styles_xml, "fills", "fill"),
            "border": elementos_contados(styles_xml, "borders", "border"),
        }
        fmt_local = {re.search(r'numFmtId="(\d+)"', n).group(1):
                     re.search(r'formatCode="([^"]*)"', n).group(1)
                     for n in elementos(styles_xml, "numFmt")
                     if 'formatCode="' in n}

        mapa_f = {i: self._mete(self.fonts, "font", t)
                  for i, t in enumerate(fuente["font"])}
        mapa_r = {i: self._mete(self.fills, "fill", t)
                  for i, t in enumerate(fuente["fill"])}
        mapa_b = {i: self._mete(self.borders, "border", t)
                  for i, t in enumerate(fuente["border"])}

        def num_fmt(idv):
            if idv not in fmt_local:
                return idv                      # formato integrado de Excel
            codigo = fmt_local[idv]
            if codigo not in self.numFmts:
                self.numFmts[codigo] = str(self._prox_fmt)
                self._prox_fmt += 1
            return self.numFmts[codigo]

        def reescribe(xf, mapa_xfid=None):
            out = re.sub(r'fontId="(\d+)"',
                         lambda m: 'fontId="%d"' % mapa_f.get(int(m.group(1)), 0), xf)
            out = re.sub(r'fillId="(\d+)"',
                         lambda m: 'fillId="%d"' % mapa_r.get(int(m.group(1)), 0), out)
            out = re.sub(r'borderId="(\d+)"',
                         lambda m: 'borderId="%d"' % mapa_b.get(int(m.group(1)), 0), out)
            out = re.sub(r'numFmtId="(\d+)"',
                         lambda m: 'numFmtId="%s"' % num_fmt(m.group(1)), out)
            if mapa_xfid is not None:
                out = re.sub(r'xfId="(\d+)"',
                             lambda m: 'xfId="%d"' % mapa_xfid.get(int(m.group(1)), 0), out)
            return out

        mapa_csxf = {}
        for i, xf in enumerate(elementos_contados(styles_xml, "cellStyleXfs", "xf")):
            mapa_csxf[i] = self._mete(self.cellStyleXfs, "csxf", reescribe(xf))

        mapa_xf = {}
        for i, xf in enumerate(elementos_contados(styles_xml, "cellXfs", "xf")):
            mapa_xf[i] = self._mete(self.cellXfs, "xf", reescribe(xf, mapa_csxf))

        mapa_dxf = {}
        for i, dxf in enumerate(elementos_contados(styles_xml, "dxfs", "dxf")):
            mapa_dxf[i] = self._mete(self.dxfs, "dxf", dxf)
        return mapa_xf, mapa_dxf

    def xml(self):
        fmts = "".join('<numFmt numFmtId="%s" formatCode="%s"/>' % (i, c)
                       for c, i in sorted(self.numFmts.items(), key=lambda kv: kv[1]))
        def bloque(tag, items):
            return '<%s count="%d">%s</%s>' % (tag, len(items), "".join(items), tag)
        return (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
            + ('<numFmts count="%d">%s</numFmts>' % (len(self.numFmts), fmts) if fmts else "")
            + bloque("fonts", self.fonts)
            + bloque("fills", self.fills)
            + bloque("borders", self.borders)
            + bloque("cellStyleXfs", self.cellStyleXfs or ['<xf numFmtId="0" fontId="0" fillId="0" borderId="0"/>'])
            + bloque("cellXfs", self.cellXfs)
            + '<cellStyles count="1"><cellStyle name="Normal" xfId="0" builtinId="0"/></cellStyles>'
            + (bloque("dxfs", self.dxfs) if self.dxfs else '<dxfs count="0"/>')
            + '<tableStyles count="0"/>'
            "</styleSheet>")


def es_cuadro(xml, shared):
    for m in re.finditer(r'<c [^>]*t="s"[^>]*><v>(\d+)</v></c>', xml):
        i = int(m.group(1))
        if i < len(shared) and ".xsd#" in shared[i]:
            return True
    return False


def limpia_hoja(xml, mapa_xf, mapa_dxf, shared_si):
    """Reindexa formatos, pasa los textos a inline y saca lo que no viaja."""
    # 1. formato de cada celda y de las filas
    def re_s(m):
        return 's="%d"' % mapa_xf.get(int(m.group(1)), 0)
    xml = re.sub(r's="(\d+)"', re_s, xml)
    xml = re.sub(r'dxfId="(\d+)"',
                 lambda m: 'dxfId="%d"' % mapa_dxf.get(int(m.group(1)), 0), xml)

    # 2. cadenas compartidas -> inline, para no fusionar sharedStrings.
    #    <si> y <is> tienen el mismo contenido, asi que el texto enriquecido
    #    (negritas dentro de una celda) se conserva tal cual.
    def re_str(m):
        attrs, cuerpo = m.group(1), m.group(2) or ""
        if 't="s"' not in attrs:
            return m.group(0)
        mv = re.search(r"<v>(\d+)</v>", cuerpo)
        if not mv:
            return m.group(0)
        i = int(mv.group(1))
        if i >= len(shared_si):
            return m.group(0)
        attrs = attrs.replace('t="s"', 't="inlineStr"')
        return "<c %s><is>%s</is></c>" % (attrs, shared_si[i])
    xml = CELDA_RE.sub(re_str, xml)

    # 3. lo que necesitaria relaciones propias de la hoja
    for tag in FUERA:
        xml = re.sub(r"<%s(?:\s[^>]*)?/>" % tag, "", xml)
        xml = re.sub(r"<%s(?:\s[^>]*)?>.*?</%s>" % (tag, tag), "", xml, flags=re.S)
    xml = re.sub(r'\sr:id="[^"]*"', "", xml)
    return xml


def escapa(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;") \
            .replace('"', "&quot;")


def fusionar(origen, salida, verbose=False):
    libros = sorted(p for p in Path(origen).rglob("*.xls[mx]")
                    if not p.name.startswith("~$") and p.resolve() != salida.resolve())
    if not libros:
        sys.exit(f"No hay .xlsm ni .xlsx en {origen}")

    estilos = Estilos()
    hojas = []                                   # (nombre, xml)
    vistos = collections.Counter()

    for ruta in libros:
        z = zipfile.ZipFile(ruta)
        try:
            ss = z.read("xl/sharedStrings.xml").decode("utf-8")
        except KeyError:
            ss = ""
        shared_si = re.findall(r"<si>(.*?)</si>", ss, re.S)
        shared_txt = ["".join(re.findall(r"<t[^>]*>(.*?)</t>", s, re.S)) for s in shared_si]
        mapa_xf, mapa_dxf = estilos.absorbe(z.read("xl/styles.xml").decode("utf-8"))

        rels = dict(re.findall(r'Id="(rId\d+)"[^>]*Target="([^"]*)"',
                               z.read("xl/_rels/workbook.xml.rels").decode("utf-8")))
        wb = z.read("xl/workbook.xml").decode("utf-8")
        n_libro = 0
        for tag in re.findall(r"<sheet [^>]*?>", wb):
            nombre = re.search(r'name="([^"]*)"', tag).group(1)
            destino = rels[re.search(r'r:id="(rId\d+)"', tag).group(1)].lstrip("/")
            parte = destino if destino.startswith("xl/") else "xl/" + destino
            xml = z.read(parte).decode("utf-8")
            if not es_cuadro(xml, shared_txt):
                continue
            vistos[nombre] += 1
            if vistos[nombre] > 1:               # no deberia pasar, pero por si acaso
                nombre = f"{nombre[:27]}_{vistos[nombre]}"
            hojas.append((nombre, limpia_hoja(xml, mapa_xf, mapa_dxf, shared_si)))
            n_libro += 1
        if verbose:
            print(f"  {ruta.name[:52]:54} {n_libro:3} hojas")

    if not hojas:
        sys.exit("No se encontro ninguna hoja de cuadros.")

    escribe_paquete(salida, hojas, estilos, libros[0])
    return hojas, estilos


def escribe_paquete(salida, hojas, estilos, ejemplar):
    tema = zipfile.ZipFile(ejemplar).read("xl/theme/theme1.xml")

    sheets_xml = "".join(
        '<sheet name="%s" sheetId="%d" r:id="rId%d"/>' % (escapa(n), i, i)
        for i, (n, _) in enumerate(hojas, 1))
    workbook = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"'
        ' xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
        '<sheets>%s</sheets>'
        '<calcPr calcId="191029" fullCalcOnLoad="1"/>'
        "</workbook>" % sheets_xml)

    n = len(hojas)
    wb_rels = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
               '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
               + "".join('<Relationship Id="rId%d" Type="http://schemas.openxmlformats.org/'
                         'officeDocument/2006/relationships/worksheet" Target="worksheets/sheet%d.xml"/>'
                         % (i, i) for i in range(1, n + 1))
               + '<Relationship Id="rId%d" Type="http://schemas.openxmlformats.org/'
                 'officeDocument/2006/relationships/styles" Target="styles.xml"/>' % (n + 1)
               + '<Relationship Id="rId%d" Type="http://schemas.openxmlformats.org/'
                 'officeDocument/2006/relationships/theme" Target="theme/theme1.xml"/>' % (n + 2)
               + "</Relationships>")

    tipos = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
             '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
             '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
             '<Default Extension="xml" ContentType="application/xml"/>'
             '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-'
             'officedocument.spreadsheetml.sheet.main+xml"/>'
             + "".join('<Override PartName="/xl/worksheets/sheet%d.xml" ContentType="application/'
                       'vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>' % i
                       for i in range(1, n + 1))
             + '<Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-'
               'officedocument.spreadsheetml.styles+xml"/>'
               '<Override PartName="/xl/theme/theme1.xml" ContentType="application/vnd.openxmlformats-'
               'officedocument.theme+xml"/>'
             + "</Types>")

    raiz = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/'
            'relationships/officeDocument" Target="xl/workbook.xml"/></Relationships>')

    salida.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(salida, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", tipos)
        z.writestr("_rels/.rels", raiz)
        z.writestr("xl/workbook.xml", workbook)
        z.writestr("xl/_rels/workbook.xml.rels", wb_rels)
        z.writestr("xl/styles.xml", estilos.xml())
        z.writestr("xl/theme/theme1.xml", tema)
        for i, (_, xml) in enumerate(hojas, 1):
            z.writestr("xl/worksheets/sheet%d.xml" % i, xml)


def main():
    p = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--origen", required=True, help="carpeta con los .xlsm llenos")
    p.add_argument("--salida", required=True, help="archivo .xlsx a generar")
    p.add_argument("-v", "--verbose", action="store_true")
    args = p.parse_args()

    salida = Path(args.salida)
    hojas, estilos = fusionar(Path(args.origen), salida, args.verbose)
    print(f"\n{len(hojas)} hojas de cuadros -> {salida}")
    print(f"   formatos fusionados: {len(estilos.cellXfs)} cellXfs, "
          f"{len(estilos.fonts)} fuentes, {len(estilos.fills)} rellenos, "
          f"{len(estilos.borders)} bordes")
    print(f"   tamano: {salida.stat().st_size/1024:.0f} KB")


if __name__ == "__main__":
    main()
