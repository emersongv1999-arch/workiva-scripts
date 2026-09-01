#!/usr/bin/env python3
"""
Fusiona las hojas de cuadros XBRL de varios .xlsm en un unico libro.

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
  NO   hipervinculos entre hojas y validaciones de datos: las listas
       desplegables apuntan a las hojas auxiliares, que no viajan

Con --con-macros el resultado es un .xlsm con las macros y los botones. No
hace falta generar VBA: como el libro fusionado lleva solo hojas de cuadros,
sin auxiliares al final que saltarse, el bucle correcto es "For H = 1 To
TotalHojas" y varias plantillas ya lo traen asi. Se toma el proyecto VBA de
una de ellas, elegida sin leer el VBA: lo que resta el bucle es exactamente
el numero de hojas auxiliares del libro, asi que basta con uno que no tenga.

El trabajo real es reindexar los formatos. Cada libro tiene su propia
styles.xml y un s="16" no significa lo mismo en dos archivos distintos, asi
que hay que fusionar fuentes, rellenos, bordes y formatos de numero
deduplicando, y reescribir el indice de cada celda.

Uso:
    python fusionar_cuadros.py --origen ./salida --salida E211_XBRL.xlsx
    python fusionar_cuadros.py --origen ./salida --salida E211_XBRL.xlsm --con-macros
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

# En modo .xlsm los dibujos si viajan: son los botones de las macros.
FUERA_XLSM = tuple(t for t in FUERA if t != "drawing")

def _nombres_en_vba(ruta, nombres):
    """Que nombres de macro contiene el proyecto VBA de un libro.

    Los identificadores viajan SIN comprimir dentro de vbaProject.bin, asi que
    basta buscarlos como bytes: comprobado contra la lectura real del VBA con
    oletools en los 41 archivos de la entrega, coincide en los 41. Evita
    depender de oletools, que arrastra media docena de paquetes y en un equipo
    corporativo suele fallar al instalarse."""
    try:
        with zipfile.ZipFile(ruta) as z:
            crudo = z.read("xl/vbaProject.bin")
    except KeyError:
        return set()
    return {n for n in nombres if n.encode("ascii", "ignore") in crudo}


# Las tres macros que trae el modulo de cualquier plantilla de DBNeT.
MACROS_BASE = ("Guarda_Hojas_CSV", "Guarda_Hojas_ZIP", "Copiar_columna")

# Botones cuya macro no existe en el donante. crear_csv exportaba solo la hoja
# activa; en el libro fusionado el equivalente util es exportarlas todas.
EQUIVALE = {"crear_csv": "Guarda_Hojas_CSV"}


def repunta_botones(dxml, disponibles):
    """Reapunta o desactiva las formas que llaman a una macro inexistente."""
    def cambia(m):
        nombre = m.group(1)
        if nombre in disponibles:
            return m.group(0)
        destino = EQUIVALE.get(nombre)
        if destino in disponibles:
            return 'macro="[0]!%s"' % destino
        return 'macro=""'          # sin macro antes que un error al pulsarlo
    return re.sub(r'macro="\[0\]!([^"]+)"', cambia, dxml)


def hojas_auxiliares(ruta):
    """Cuantas hojas del libro NO son cuadros (las listas de codigos)."""
    z = zipfile.ZipFile(ruta)
    try:
        ss = z.read("xl/sharedStrings.xml").decode("utf-8")
    except KeyError:
        ss = ""
    shared = ["".join(re.findall(r"<t[^>]*>(.*?)</t>", s, re.S))
              for s in re.findall(r"<si>(.*?)</si>", ss, re.S)]
    rels = dict(re.findall(r'Id="(rId\d+)"[^>]*Target="([^"]*)"',
                           z.read("xl/_rels/workbook.xml.rels").decode("utf-8")))
    n = 0
    for tag in re.findall(r"<sheet [^>]*?>", z.read("xl/workbook.xml").decode("utf-8")):
        destino = rels[re.search(r'r:id="(rId\d+)"', tag).group(1)].lstrip("/")
        parte = destino if destino.startswith("xl/") else "xl/" + destino
        if not es_cuadro(z.read(parte).decode("utf-8"), shared):
            n += 1
    return n


def sirve_de_donante(ruta):
    """Un donante valido aporta las tres macros y recorre TODAS las hojas.

    El libro fusionado no lleva hojas auxiliares, asi que el bucle tiene que
    ser 'For H = 1 To TotalHojas', sin restar. Y lo que se resta en cada
    plantilla es exactamente su numero de hojas auxiliares: verificado en los
    41 archivos de la entrega, sin una sola excepcion. De modo que un libro
    sin hojas auxiliares trae justo el bucle que necesitamos.

    Ademas se descarta WBReplaceHyperlinkURL: tiene un End If huerfano y su
    modulo no compila, lo que dejaria todos los botones muertos."""
    presentes = _nombres_en_vba(ruta, list(MACROS_BASE) + ["WBReplaceHyperlinkURL"])
    if "WBReplaceHyperlinkURL" in presentes:
        return False
    if not set(MACROS_BASE) <= presentes:
        return False
    return hojas_auxiliares(ruta) == 0


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


def lee_hojas_de_workiva(origen):
    """{(archivo, hoja)} que existen en el export de Workiva, o None."""
    f = Path(origen) / "_hojas_de_workiva.txt"
    if not f.exists():
        return None
    return {tuple(l.split("|", 1)) for l in
            f.read_text(encoding="utf-8").splitlines() if "|" in l}


def es_cuadro(xml, shared):
    for m in re.finditer(r'<c [^>]*t="s"[^>]*><v>(\d+)</v></c>', xml):
        i = int(m.group(1))
        if i < len(shared) and ".xsd#" in shared[i]:
            return True
    return False


def limpia_hoja(xml, mapa_xf, mapa_dxf, shared_si, con_botones=False):
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
    for tag in (FUERA_XLSM if con_botones else FUERA):
        xml = re.sub(r"<%s(?:\s[^>]*)?/>" % tag, "", xml)
        xml = re.sub(r"<%s(?:\s[^>]*)?>.*?</%s>" % (tag, tag), "", xml, flags=re.S)
    if con_botones:
        # el dibujo se queda, y su relacion pasa a ser siempre rId1
        xml = re.sub(r'<drawing[^>]*/>', '<drawing r:id="rId1"/>', xml)
        xml = re.sub(r'\sr:id="[^"]*"',
                     lambda m: m.group(0) if "rId1" in m.group(0) else "", xml)
    else:
        xml = re.sub(r'\sr:id="[^"]*"', "", xml)
    return xml


def escapa(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;") \
            .replace('"', "&quot;")


def dibujo_de_hoja(z, parte_hoja):
    """(xml del dibujo, [(rId, ruta del medio)]) o None."""
    rels_p = re.sub(r"([^/]+)$", r"_rels/\1.rels", parte_hoja)
    try:
        rels = z.read(rels_p).decode("utf-8")
    except KeyError:
        return None
    hoja = z.read(parte_hoja).decode("utf-8")
    m = re.search(r'<drawing[^>]*r:id="(rId\d+)"', hoja)
    if not m:
        return None
    md = re.search(r'Id="%s"[^>]*Target="([^"]*)"' % m.group(1), rels)
    if not md:
        return None
    destino = md.group(1).replace("../", "xl/")
    if not destino.startswith("xl/"):
        destino = "xl/drawings/" + destino.lstrip("/")
    try:
        dxml = z.read(destino).decode("utf-8")
    except KeyError:
        return None
    medios = []
    drels_p = re.sub(r"([^/]+)$", r"_rels/\1.rels", destino)
    try:
        drels = z.read(drels_p).decode("utf-8")
        for rid, tgt in re.findall(r'Id="(rId\d+)"[^>]*Target="([^"]*)"', drels):
            t = tgt.replace("../", "xl/")
            if not t.startswith("xl/"):
                t = "xl/media/" + t.lstrip("/")
            medios.append((rid, t, z.read(t)))
    except KeyError:
        pass
    return dxml, medios


def fusionar(origen, salida, verbose=False, donante=None, solo_workiva=False):
    libros = sorted(p for p in Path(origen).rglob("*.xls[mx]")
                    if not p.name.startswith("~$") and p.resolve() != salida.resolve())
    if not libros:
        sys.exit(f"No hay .xlsm ni .xlsx en {origen}")

    estilos = Estilos()
    hojas = []                                   # (nombre, xml, dibujo|None)
    vistos = collections.Counter()
    omitidas = []
    con_botones = donante is not None
    con_datos = lee_hojas_de_workiva(origen) if solo_workiva else None
    if solo_workiva and con_datos is None:
        sys.exit("Para --solo-workiva hace falta _hojas_de_workiva.txt, que "
                 "genera llenar_dbnet_desde_workiva.py en la carpeta de salida.")

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
            if con_datos is not None and (ruta.name, nombre) not in con_datos:
                omitidas.append(nombre)
                continue
            vistos[nombre] += 1
            if vistos[nombre] > 1:               # no deberia pasar, pero por si acaso
                nombre = f"{nombre[:27]}_{vistos[nombre]}"
            dib = dibujo_de_hoja(z, parte) if con_botones else None
            hojas.append((nombre,
                          limpia_hoja(xml, mapa_xf, mapa_dxf, shared_si,
                                      con_botones and dib is not None),
                          dib))
            n_libro += 1
        if verbose:
            print(f"  {ruta.name[:52]:54} {n_libro:3} hojas")

    if not hojas:
        sys.exit("No se encontro ninguna hoja de cuadros.")

    if omitidas:
        print(f"  omitidas por no estar en Workiva: {len(omitidas)}")
    escribe_paquete(salida, hojas, estilos, libros[0], donante)
    return hojas, estilos


def docprops(hojas):
    """core.xml y app.xml minimos pero completos.

    Faltaban en versiones anteriores del fusionador: un .xlsm sin ellos
    sigue siendo un ZIP valido y Excel lo abre, pero al parecer lo trata
    como un archivo que necesito 'reparar' en silencio, y ese estado deja
    inestable el ActiveWorkbook.Save que hace Copiar_columna -- error 1004
    'no se puede obtener acceso' aunque el archivo no este ni bloqueado ni
    de solo lectura. Los .xlsm originales de DBNeT si las traen."""
    ahora = __import__("datetime").datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
    core = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/'
            '2006/metadata/core-properties" xmlns:dc="http://purl.org/dc/elements/1.1/"'
            ' xmlns:dcterms="http://purl.org/dc/terms/" '
            'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">'
            '<dc:creator>fusionar_cuadros.py</dc:creator>'
            '<cp:lastModifiedBy>fusionar_cuadros.py</cp:lastModifiedBy>'
            '<dcterms:created xsi:type="dcterms:W3CDTF">%s</dcterms:created>'
            '<dcterms:modified xsi:type="dcterms:W3CDTF">%s</dcterms:modified>'
            '</cp:coreProperties>' % (ahora, ahora))
    titulos = "".join("<vt:lpstr>%s</vt:lpstr>" % escapa(n) for n, _, _ in hojas)
    app = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
           '<Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/'
           'extended-properties" xmlns:vt="http://schemas.openxmlformats.org/'
           'officeDocument/2006/docPropsVTypes">'
           '<Application>Microsoft Excel</Application><DocSecurity>0</DocSecurity>'
           '<ScaleCrop>false</ScaleCrop>'
           '<HeadingPairs><vt:vector size="2" baseType="variant">'
           '<vt:variant><vt:lpstr>Hojas de c\u00e1lculo</vt:lpstr></vt:variant>'
           '<vt:variant><vt:i4>%d</vt:i4></vt:variant></vt:vector></HeadingPairs>'
           '<TitlesOfParts><vt:vector size="%d" baseType="lpstr">%s</vt:vector>'
           '</TitlesOfParts>'
           '<LinksUpToDate>false</LinksUpToDate><SharedDoc>false</SharedDoc>'
           '<HyperlinksChanged>false</HyperlinksChanged><AppVersion>16.0300</AppVersion>'
           '</Properties>' % (len(hojas), len(hojas), titulos))
    return core, app


def escribe_paquete(salida, hojas, estilos, ejemplar, donante=None):
    tema = zipfile.ZipFile(ejemplar).read("xl/theme/theme1.xml")
    n = len(hojas)
    macro = donante is not None

    # ---- dibujos (los botones) y sus imagenes, renumerados globalmente ----
    dibujos, medios, rels_hoja = [], [], {}
    vistos_medio = {}
    disponibles = _nombres_en_vba(donante, MACROS_BASE) if macro else set()
    for i, (_, _, dib) in enumerate(hojas, 1):
        if not dib:
            continue
        dxml, mds = dib
        for rid, ruta, datos in mds:
            if datos not in vistos_medio:
                ext = ruta.rsplit(".", 1)[-1].lower()
                vistos_medio[datos] = "image%d.%s" % (len(medios) + 1, ext)
                medios.append((vistos_medio[datos], datos))
        if macro:
            dxml = repunta_botones(dxml, disponibles)
        dibujos.append((len(dibujos) + 1, dxml,
                        [(rid, vistos_medio[d]) for rid, _, d in mds]))
        rels_hoja[i] = len(dibujos)

    sheets_xml = "".join('<sheet name="%s" sheetId="%d" r:id="rId%d"/>'
                         % (escapa(nom), i, i)
                         for i, (nom, _, _) in enumerate(hojas, 1))
    workbook = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"'
        ' xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
        + ('<workbookPr codeName="ThisWorkbook"/>' if macro else "")
        + '<sheets>%s</sheets>'
          '<calcPr calcId="191029" fullCalcOnLoad="1"/>'
          "</workbook>" % sheets_xml)

    REL = "http://schemas.openxmlformats.org/officeDocument/2006/relationships/"
    rel = ['<Relationship Id="rId%d" Type="%sworksheet" Target="worksheets/sheet%d.xml"/>'
           % (i, REL, i) for i in range(1, n + 1)]
    rel.append('<Relationship Id="rId%d" Type="%sstyles" Target="styles.xml"/>' % (n + 1, REL))
    rel.append('<Relationship Id="rId%d" Type="%stheme" Target="theme/theme1.xml"/>' % (n + 2, REL))
    if macro:
        rel.append('<Relationship Id="rId%d" Type="http://schemas.microsoft.com/office/2006/'
                   'relationships/vbaProject" Target="vbaProject.bin"/>' % (n + 3))
    wb_rels = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
               '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/'
               'relationships">' + "".join(rel) + "</Relationships>")

    tipo_wb = ("application/vnd.ms-excel.sheet.macroEnabled.main+xml" if macro else
               "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml")
    ov = ['<Override PartName="/xl/workbook.xml" ContentType="%s"/>' % tipo_wb]
    ov += ['<Override PartName="/xl/worksheets/sheet%d.xml" ContentType="application/vnd.'
           'openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>' % i
           for i in range(1, n + 1)]
    ov.append('<Override PartName="/xl/styles.xml" ContentType="application/vnd.'
              'openxmlformats-officedocument.spreadsheetml.styles+xml"/>')
    ov.append('<Override PartName="/xl/theme/theme1.xml" ContentType="application/vnd.'
              'openxmlformats-officedocument.theme+xml"/>')
    ov += ['<Override PartName="/xl/drawings/drawing%d.xml" ContentType="application/vnd.'
           'openxmlformats-officedocument.drawing+xml"/>' % k for k, _, _ in dibujos]
    if macro:
        ov.append('<Override PartName="/xl/vbaProject.bin" ContentType="application/vnd.'
                  'ms-office.vbaProject"/>')
    ov.append('<Override PartName="/docProps/core.xml" ContentType="application/vnd.'
              'openxmlformats-package.core-properties+xml"/>')
    ov.append('<Override PartName="/docProps/app.xml" ContentType="application/vnd.'
              'openxmlformats-officedocument.extended-properties+xml"/>')
    defaults = ['<Default Extension="rels" ContentType="application/vnd.openxmlformats-'
                'package.relationships+xml"/>',
                '<Default Extension="xml" ContentType="application/xml"/>']
    for ext in sorted({m[0].rsplit(".", 1)[-1] for m in medios}):
        defaults.append('<Default Extension="%s" ContentType="image/%s"/>'
                        % (ext, "jpeg" if ext in ("jpg", "jpeg") else ext))
    tipos = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
             '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
             + "".join(defaults) + "".join(ov) + "</Types>")

    raiz = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/'
            'relationships"><Relationship Id="rId1" Type="%sofficeDocument" '
            'Target="xl/workbook.xml"/>'
            '<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/package/'
            '2006/relationships/metadata/core-properties" Target="docProps/core.xml"/>'
            '<Relationship Id="rId3" Type="%sextended-properties" '
            'Target="docProps/app.xml"/></Relationships>' % (REL, REL))

    salida.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(salida, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", tipos)
        z.writestr("_rels/.rels", raiz)
        core_xml, app_xml = docprops(hojas)
        z.writestr("docProps/core.xml", core_xml)
        z.writestr("docProps/app.xml", app_xml)
        z.writestr("xl/workbook.xml", workbook)
        z.writestr("xl/_rels/workbook.xml.rels", wb_rels)
        z.writestr("xl/styles.xml", estilos.xml())
        z.writestr("xl/theme/theme1.xml", tema)
        for i, (_, xml, _) in enumerate(hojas, 1):
            # Cada hoja llega con el codeName de su libro de origen y al
            # juntarlas se repiten. Se quitan todos y se pone Hoja1 en la
            # primera, que es el modulo de documento que trae el donante.
            xml = re.sub(r'(<sheetPr\b[^>]*?)\s*codeName="[^"]*"', r"\1", xml, count=1)
            if macro and i == 1:
                if re.search(r"<sheetPr\b", xml):
                    xml = re.sub(r"<sheetPr\b", '<sheetPr codeName="Hoja1"', xml, count=1)
                else:
                    xml = re.sub(r"(<worksheet[^>]*>)",
                                 r'\1<sheetPr codeName="Hoja1"/>', xml, count=1)
            z.writestr("xl/worksheets/sheet%d.xml" % i, xml)
            if i in rels_hoja:
                z.writestr("xl/worksheets/_rels/sheet%d.xml.rels" % i,
                           '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                           '<Relationships xmlns="http://schemas.openxmlformats.org/'
                           'package/2006/relationships"><Relationship Id="rId1" '
                           'Type="%sdrawing" Target="../drawings/drawing%d.xml"/>'
                           "</Relationships>" % (REL, rels_hoja[i]))
        for k, dxml, mds in dibujos:
            z.writestr("xl/drawings/drawing%d.xml" % k, dxml)
            if mds:
                z.writestr("xl/drawings/_rels/drawing%d.xml.rels" % k,
                           '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                           '<Relationships xmlns="http://schemas.openxmlformats.org/'
                           'package/2006/relationships">'
                           + "".join('<Relationship Id="%s" Type="%simage" '
                                     'Target="../media/%s"/>' % (rid, REL, nom)
                                     for rid, nom in mds) + "</Relationships>")
        for nom, datos in medios:
            z.writestr("xl/media/" + nom, datos)
        if macro:
            z.writestr("xl/vbaProject.bin",
                       zipfile.ZipFile(donante).read("xl/vbaProject.bin"))


def main():
    p = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--origen", required=True, help="carpeta con los .xlsm llenos")
    p.add_argument("--salida", required=True, help="archivo .xlsx a generar")
    p.add_argument("-v", "--verbose", action="store_true")
    p.add_argument("--solo-workiva", action="store_true",
                   help="deja fuera los cuadros que no existen en el export de "
                        "Workiva (los que no le aplican a la empresa)")
    p.add_argument("--con-macros", action="store_true",
                   help="genera un .xlsm con las macros y los botones, tomando "
                        "el proyecto VBA de una de las plantillas de origen")
    args = p.parse_args()

    salida = Path(args.salida)
    donante = None
    if args.con_macros:
        if salida.suffix.lower() != ".xlsm":
            salida = salida.with_suffix(".xlsm")
        for cand in sorted(Path(args.origen).rglob("*.xlsm")):
            if sirve_de_donante(cand):
                donante = cand
                break
        if donante is None:
            sys.exit("Ninguna plantilla sirve de donante de macros: hace falta una "
                     "con 'For H = 1 To TotalHojas', Copiar_columna y sin "
                     "WBReplaceHyperlinkURL.")
        print(f"Macros tomadas de: {donante.name}")

    hojas, estilos = fusionar(Path(args.origen), salida, args.verbose, donante,
                              args.solo_workiva)
    print(f"\n{len(hojas)} hojas de cuadros -> {salida}")
    if donante:
        print(f"   botones conservados: {sum(1 for h in hojas if h[2])} hojas")
    print(f"   formatos fusionados: {len(estilos.cellXfs)} cellXfs, "
          f"{len(estilos.fonts)} fuentes, {len(estilos.fills)} rellenos, "
          f"{len(estilos.borders)} bordes")
    print(f"   tamano: {salida.stat().st_size/1024:.0f} KB")


if __name__ == "__main__":
    main()
