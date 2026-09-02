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

Con --con-macros el resultado es un .xlsm con las macros y los botones
funcionando de verdad. Esto lo arma Excel mismo por COM (pywin32), no
Python: un .xlsm ensamblado a mano (ZIP/XML, sin pasar por Excel) abre y se
ve bien pero su ActiveWorkbook.Save revienta con error 1004 de forma
consistente -- probado en OneDrive, SharePoint y disco local, causa nunca
aislada del todo. Lo unico que resulto confiable es un libro que Excel
mismo construyo con Worksheets.Copy nativo, asi que --con-macros abre Excel
en segundo plano y le copia hojas de cuadro a un libro base.

Ese libro base es SIEMPRE plantilla_base_macros.xlsm, fijo en el repo junto
a este script -- nunca una de las 41 plantillas que entrega DBNeT ese
periodo. Asi la macro no depende de que trae la entrega de turno: las 41
solo aportan hojas con datos, la base solo aporta las macros, y sus propias
hojas (sin datos de ninguna empresa) se descartan siempre. Requiere Excel
instalado en la maquina donde se corre esto (no sirve en un servidor sin
Office) y `pip install pywin32`.

El trabajo real es reindexar los formatos. Cada libro tiene su propia
styles.xml y un s="16" no significa lo mismo en dos archivos distintos, asi
que hay que fusionar fuentes, rellenos, bordes y formatos de numero
deduplicando, y reescribir el indice de cada celda.

Uso:
    python fusionar_cuadros.py --origen ./salida --salida E211_XBRL.xlsx
    python fusionar_cuadros.py --origen ./salida --salida E211_XBRL.xlsm --con-macros
"""

import argparse
import base64
import collections
import re
import sys
import tempfile
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


# Copia embebida de plantilla_base_macros.xlsm (mismo archivo que esta en el
# repo junto a este script, para poder inspeccionarlo/actualizarlo con Excel).
# Va tambien en base64 aqui adentro para que el .xlsm con macros no dependa
# de que alguien copie el archivo correcto a la carpeta correcta -- el mismo
# problema que se evito en verificar_workiva_GUI.py con sus scripts _XXX_SRC.
#
# Para actualizarla: reemplaza plantilla_base_macros.xlsm, y reencodea con
#   python3 -c "import base64; print(base64.b64encode(open('plantilla_base_macros.xlsm','rb').read()).decode())"
_PLANTILLA_BASE_MACROS_B64 = (
    "UEsDBBQABgAIAAAAIQAVrOhRsQEAAPQFAAATAAgCW0NvbnRlbnRfVHlwZXNdLnhtbCCiBAIooAACAAAAAAAAAAAAAAAAAAAAAAAA"
    "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
    "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
    "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
    "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
    "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
    "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
    "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAACsVMlu2zAQvRfoPwi8FiKdHoqisJxDmxzTAEk/gCbH"
    "Emtu4Ewc++87lJ0ugWM1cC7aqLfMcPjml9vgmw0UdCl24kLORAPRJOti34kf99ftZ9Eg6Wi1TxE6sQMUl4v37+b3uwzYMDpiJwai"
    "/EUpNAMEjTJliLyySiVo4tfSq6zNWvegPs5mn5RJkSBSS5VDLObfYKUfPDVXW/68d7J0UTRf9/9VqU7onL0zmtio2kT7TKRNq5Uz"
    "YJN5CEwtMRfQFgcACl7m4lix3AERF4ZCHdXMsX+m6UL1XL8fRxTw+Dqbhz5IRo6l4OAyfuBmvaBQV17uwwH3nTewOAvNrS50owN3"
    "S229ekxlvUxpLU+T1GYGbGFrwMuxYzJoU9JV1EsPvKZdfHJ4QmlEohpvF/8h+e+QnN6/WslIPOGDeP5AjdfzLYw0E4JIOw/4xtXu"
    "SaeUB13A3hFPdv/mBv7mnvBhi36sFtTh4fy+H4gmdDdLfVvSTzAkp7OCx3ufD/IPrB64Y+PMEcLEGTmlCrx+Z58OeEW3mYmgkIPf"
    "R/ykIkfc2aMENUMt2CPaaszsxS8AAAD//wMAUEsDBBQABgAIAAAAIQC1VTAj9AAAAEwCAAALAAgCX3JlbHMvLnJlbHMgogQCKKAA"
    "AgAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
    "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
    "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
    "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
    "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
    "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
    "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAArJJNT8MwDIbvSPyH"
    "yPfV3ZAQQkt3QUi7IVR+gEncD7WNoyQb3b8nHBBUGoMDR3+9fvzK2908jerIIfbiNKyLEhQ7I7Z3rYaX+nF1ByomcpZGcazhxBF2"
    "1fXV9plHSnkodr2PKqu4qKFLyd8jRtPxRLEQzy5XGgkTpRyGFj2ZgVrGTVneYviuAdVCU+2thrC3N6Dqk8+bf9eWpukNP4g5TOzS"
    "mRXIc2Jn2a58yGwh9fkaVVNoOWmwYp5yOiJ5X2RswPNEm78T/XwtTpzIUiI0Evgyz0fHJaD1f1q0NPHLnXnENwnDq8jwyYKLH6je"
    "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"
    "UHJvamVjdC5iaW7sfA18W9WV531PsiI7TpCDYU2Swott8oWtSrLjOCEO+rAcB+LYxCGE1MWW5WdbiSwZSQ7mM3IIhLaUSSlN6XYA"
    "M3QobRnqlF2GMrR1wrabdtKpaZmZdHZ2gML+lmWYadjSheku8f7PffdKT7KcOKHb/vgt1z56951777nnnnvuud9v6mdlrz52ZPFr"
    "LM9tZBZ2erqY2Ux4BX4C7hyMqfAQnJ6enpZoeD92HyEJfABeL0blaQCrqEuq83kAO6AYUAK4CFAKWABYCLgA4ACUARYBLgSUAyyA"
    "fwdYCqgAXAJYDFgC+ATgCsClgMsAywCkO5V4VgGqAZcDlgNWAFYCVgFWA2pE3Frx/FjJfj8S2Mbi+Euh/oMshmeC3QIJz91dzIqY"
    "5IT04kxusnrjlQ8NvaQUIZJ3jRFzB/Mz3znlmBvZDosk8yfdK+QmPmji+cr8zXHa2G9YHxthUUjBfR58OGABzTUxFxLzEek+aiRw"
    "3fjrZNtYB56e88tfke2V+JgriWuoMcORPScbTrKj9k91U6j9E89zaf9kJ8ieUPHy2z/ZBLIBsv1r8JMNmEv7J7tBNoDavxPwSYAL"
    "QHVGNqQOz3oAqRW9r8WzEbAOsB5wJWADoAmwEXAVwAsg3fMDAoBmQFCk34RnK2Az4GrANYAtgDbAVkA7oANwLWAboBOwHXAdYAfg"
    "esBOAPGyC89PAboAnwbcCOgWYSHxDOPZB9AB/YABwCAgAtgN2AOIAoYAMUAcMAy4CZAAJAEpwAhgL+BmwCiAWvOtgNsAtwPuANwJ"
    "2AdIA55hvlQqEekdSTFd2+Hv3hoagqdJq2z7DZpFNO6uXFDSyUZ6tU0joUQfC3W3xneHkt0s0Llj5aoFJdtd8VQoqjazG31hlors"
    "1a+PJ/ZovfH4HqfiSA4yXU8lnYH4iBZLLSjRIO5hNhyNhEOpSJzFnM2R5HA0lL7FF9UTqSTzai2haFK/YHkwxkK9UT24V49ZFlxu"
    "uWJvd18kofvDzNsW6VtZencHC6UGazR3jWbfosfKlqzSajVbHfvxWFtLPKG1vsaq3Nr2OFOKhu7yKIpjb3csPtSbeFG5/+K9K1tX"
    "OZXxg4ttner+sfmdelQPH7QeGFtxsDQQH77lYIVS6uwM7dV9SU1riUT1GPvp+ibl7tHlWmU4ubfr1UptudZ98NKxmruVznt2HnZU"
    "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"
    "mwTPC0qa4+GRIVyGaDJz+8nlrTibyJ0pBmc0Jwhf6tSbKrPjfNBv1aPDgTi+yDiaIr5cQO3AhQYsYWF8NYzFAXxUs87TVFm3rs7j"
    "8SALRAi0bWqq9Hl8roaGQIMrEPCZAeHNHf6myvr6+oZGl6+x0VXvb3QbgLBNgabKYEOwHrR8DQ2uoGudq4WgpQGBC0o+1RrHWkVw"
    "NKXH+nChYnOsP/7pBSWZ4rmbbqtrrPM0N9S7agMt61y1bnegpbYxWF9X63KBjXVut8u1xnfHleiwrzQLBZS5PcXJTB0EhTibPGtq"
    "NIJGDz7PCKI12i58oNSkB01AZf4DEBetzOUjP2xj/Iil/78CAAAA//8DAFBLAwQKAAAAAAAAACEAl6p3HbIbAACyGwAAEwAAAHhs"
    "L21lZGlhL2ltYWdlMS5wbmeJUE5HDQoaCgAAAA1JSERSAAABLAAAAFUIAwAAAMT5KfoAAAAZdEVYdFNvZnR3YXJlAEFkb2JlIElt"
    "YWdlUmVhZHlxyWU8AAADXGlUWHRYTUw6Y29tLmFkb2JlLnhtcAAAAAAAPD94cGFja2V0IGJlZ2luPSLvu78iIGlkPSJXNU0wTXBD"
    "ZWhpSHpyZVN6TlRjemtjOWQiPz4gPHg6eG1wbWV0YSB4bWxuczp4PSJhZG9iZTpuczptZXRhLyIgeDp4bXB0az0iQWRvYmUgWE1Q"
    "IENvcmUgNS4wLWMwNjAgNjEuMTM0MzQyLCAyMDEwLzAxLzEwLTE4OjA2OjQzICAgICAgICAiPiA8cmRmOlJERiB4bWxuczpyZGY9"
    "Imh0dHA6Ly93d3cudzMub3JnLzE5OTkvMDIvMjItcmRmLXN5bnRheC1ucyMiPiA8cmRmOkRlc2NyaXB0aW9uIHJkZjphYm91dD0i"
    "IiB4bWxuczp4bXBNTT0iaHR0cDovL25zLmFkb2JlLmNvbS94YXAvMS4wL21tLyIgeG1sbnM6c3RSZWY9Imh0dHA6Ly9ucy5hZG9i"
    "ZS5jb20veGFwLzEuMC9zVHlwZS9SZXNvdXJjZVJlZiMiIHhtbG5zOnhtcD0iaHR0cDovL25zLmFkb2JlLmNvbS94YXAvMS4wLyIg"
    "eG1wTU06T3JpZ2luYWxEb2N1bWVudElEPSJ4bXAuZGlkOjgwMzRGMzgwMEUyOUUyMTFBQTU4RkIyQTE1MDlGNUIwIiB4bXBNTTpE"
    "b2N1bWVudElEPSJ4bXAuZGlkOkI5MUNBNTgzMjkwRTExRTI4OTY5QjcxMzFCRUYxQkNGIiB4bXBNTTpJbnN0YW5jZUlEPSJ4bXAu"
    "aWlkOkI5MUNBNTgyMjkwRTExRTI4OTY5QjcxMzFCRUYxQkNGIiB4bXA6Q3JlYXRvclRvb2w9IkFkb2JlIFBob3Rvc2hvcCBDUzUi"
    "PiA8eG1wTU06RGVyaXZlZEZyb20gc3RSZWY6aW5zdGFuY2VJRD0ieG1wLmlpZDo4MDM0RjM4MDBFMjlFMjExQUE1OEZCMkExNTA5"
    "RjVCMCIgc3RSZWY6ZG9jdW1lbnRJRD0ieG1wLmRpZDo4MDM0RjM4MDBFMjlFMjExQUE1OEZCMkExNTA5RjVCMCIvPiA8L3JkZjpE"
    "ZXNjcmlwdGlvbj4gPC9yZGY6UkRGPiA8L3g6eG1wbWV0YT4gPD94cGFja2V0IGVuZD0iciI/PpNi2T4AAAMAUExUReqHs8jk5Mzh"
    "8PXH2uSWu5nD4dzq9bjW67HZ2KqqqjMzM3d3d/7+/wCJ1GS45ZC83c6JsisrK/vr8uNxqFOw4vr8/VVVVZiYmABmtMDa7eLi4nS/"
    "55rMzABks+jC1xh/v6rN5mVlZPX5/FSazcLCwujx+IaGhtfr6yV9vrd9sqnS6iqCwXqx2NXm8rTT6eLx8eXw+AB2vgBst2y1tqTK"
    "5evc4dzc3Law0QBotUuGwHSs1RRzuvz+/naVxu7E2PPj7KbW8Fan2UaTyvT09LOzs0hISOrq6wBptvzx9fz1+ABjsDSIxeHu9/r6"
    "+ru7u4+QwvD3+/j7/Sec2jqKxh17vvHx8O31+eW11nJ0s3q+vTGFw2Oj0onH6vDe4b7Y7BuW2PXp7sbd7vLR5uuoxs3NzZ17s4y7"
    "3uydwEuVy/nj7u3J4oG02vaJs9TU1ABrtOTu9/G50ve0z9e1z+j09Dql3t2mytbd6uzK2/Pc7PP4/D+OyACG0tHq92il0z09PW2o"
    "1Pz8/Pz4+r3g8y+p4vKpyO7R4PL4+fXh49Hk8iyPklqczuzq8Rp1usfl9ef0+7fH2/z9/uHg7QBosgtttwVqtbTe83ikzFOWyvnc"
    "6ffV4wdvuQBntMq305nR7frk5OG/1tnu+PbN3uyItAxwuaDH5Pro6fjZ5tzl8A6R19Xr9+6wzRd4vevi6eHT5iuSywBdrpC+3/HX"
    "5v36+zc3N/78/fL1+P79/rHQ6ASM1eLN3+n1+wZstxKFx+PW6K7Q6Pbu8fHv9u+WveN+r8/i8EWQyO33/Pbx9Ovz+fDj597w+fX6"
    "+uqDsU+YzM3o9lisqoa43ANrt2OxsABgsWGvrwJotcnf7+Xv97nR55uouIadyZOy1ODf3wRnsq/Z8PCKtkKanT6AvX2erNfn856O"
    "quTH3srL4uLZ4ebf7V6g0OzY6nG02waO1uPk8cjC0GytsUSb0HShrJ2iy/f7/hBxucHQ5cDf38rQ5ff39+Ho8WGQxAJptmSv1dPQ"
    "3djY14a22////7KfjR4AAAEAdFJOU///////////////////////////////////////////////////////////////////////"
    "////////////////////////////////////////////////////////////////////////////////////////////////////"
    "////////////////////////////////////////////////////////////////////////////////////////////////////"
    "/////////////////////////////////////////////////////////////////////wBT9wclAAAT1ElEQVR42uycC1hTV57A"
    "kaeQG9qACVfttSQ8zA6PYho1hZRaXpf38DKzgkVpXUBpp7YyrSHysrV1Ldp8PiqatiOVulZmRgRXaZ3BKlR0oVPHbXRbx47LPuqU"
    "2Zkd2C47s6tnzzn33uTem5sQ3Pbb+Zz8/YRw78lNzi//9zk3fsAreQX4BAA/bwYRux5S+lB5B0szb+srD/lQeQXrUlmjXTnXh8ob"
    "WDsn5B/1jsz1eS0vYO2zyD8G//2dOXN8rGaEtcIi3wpOfvUT0yofq5lgrbBMbMnbmNu6JHhVkQ+WZ1hbLWXBnV+MRjy6RP+Azw49"
    "w9piafzNc6N+o+uXL/ndHJ8deoT1wcC8X58b9fMb7dzWs8T/57681AOs0rKyf3569B0IK2D9zSU3Vi32wXJf4yycWI5QQVgv5/7V"
    "kq/mPuCD5cG5rxj5i6cRLL9zeYEP/mTxz40+WG7ko6NrNMbvMrD8Ljz3xpLCX5h8sNwYYbjlLQA+P49ZjUYEPP9T/we+9sFyUxFa"
    "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"
    "AAAAAA=="
)


def _plantilla_base_temporal(carpeta):
    """Vuelca la plantilla embebida a un .xlsm real, listo para abrir con COM."""
    ruta = Path(carpeta) / "plantilla_base_macros.xlsm"
    ruta.write_bytes(base64.b64decode(_PLANTILLA_BASE_MACROS_B64))
    return ruta


def _plantilla_base_valida(ruta):
    """Chequeo de integridad del activo fijo, no una busqueda de candidatos.

    plantilla_base_macros.xlsm es un .xlsm real de DBNeT, congelado en el
    repo solo por su vbaProject.bin -- sus propias hojas se descartan en
    tiempo de ejecucion, nunca aportan datos. Esta funcion no elige entre
    varios candidatos (eso es justamente lo que se saco: que la macro del
    archivo final dependiera de cual de las 41 plantillas del periodo
    calificara); solo confirma que el archivo fijo sigue teniendo lo que
    tiene que tener, por si alguien lo reemplaza por error."""
    presentes = _nombres_en_vba(ruta, list(MACROS_BASE) + ["WBReplaceHyperlinkURL"])
    return set(MACROS_BASE) <= presentes and "WBReplaceHyperlinkURL" not in presentes


def _hojas_cuadro_com(libro):
    """Hojas del libro COM que llevan URI de taxonomia en la columna C."""
    cuadros = []
    for hoja in libro.Worksheets:
        valores = hoja.Range("C1:C500").Value
        if valores and any(isinstance(v, str) and ".xsd#" in v
                            for fila in valores for v in fila):
            cuadros.append(hoja)
    return cuadros


def fusionar_con_macros(origen, salida, verbose=False, solo_workiva=False):
    """Arma el .xlsm fusionado dejando que Excel mismo copie las hojas.

    Ver el docstring del modulo: el ensamblado a mano (ZIP/XML) quedo
    descartado porque el Save() de la macro Copiar_columna reventaba con
    error 1004 sin causa aislada. Esto abre Excel real por COM (pywin32) y
    hace lo mismo que hacia el usuario a mano con VBA (Worksheets.Copy),
    pero automatico y desde el mismo script.

    Las macros salen SIEMPRE de la plantilla embebida mas arriba en este
    mismo archivo (_PLANTILLA_BASE_MACROS_B64) -- nunca de las 41 plantillas
    que entrega DBNeT cada periodo. Eso es a proposito: si la macro saliera
    de "la primera de las 41 que califique", el resultado dependeria de que
    trae DBNeT ese periodo puntual, no de algo que controlamos nosotros. Las
    41 solo aportan hojas con datos; la base solo aporta las macros. Sus
    propias hojas (que no tienen datos reales de ninguna empresa) se
    descartan siempre, nunca terminan en el archivo final.

    Al ir embebida no depende de que alguien copie plantilla_base_macros.xlsm
    a la carpeta correcta -- se vuelca a un archivo temporal en cada corrida
    y se borra solo al terminar."""
    try:
        import win32com.client
    except ImportError:
        sys.exit(
            "Para --con-macros hace falta pywin32 y Excel instalado en esta "
            "maquina: pip install pywin32\n"
            "El .xlsm con macros lo arma Excel mismo (Worksheets.Copy), no "
            "es un archivo hecho a mano por Python -- por eso hace falta el "
            "Excel real, no solo la libreria.")

    libros = sorted(p for p in Path(origen).rglob("*.xlsm")
                    if not p.name.startswith("~$")
                    and p.resolve() != Path(salida).resolve())
    if not libros:
        sys.exit(f"No hay .xlsm en {origen}")

    con_datos = lee_hojas_de_workiva(origen) if solo_workiva else None
    if solo_workiva and con_datos is None:
        sys.exit("Para --solo-workiva hace falta _hojas_de_workiva.txt, que "
                 "genera llenar_dbnet_desde_workiva.py en la carpeta de salida.")

    salida = Path(salida)
    if salida.suffix.lower() != ".xlsm":
        salida = salida.with_suffix(".xlsm")
    salida = salida.resolve()
    if salida.exists():
        salida.unlink()

    def permitida(archivo, nombre):
        return con_datos is None or (archivo, nombre) in con_datos

    app = win32com.client.DispatchEx("Excel.Application")
    app.Visible = False
    app.DisplayAlerts = False
    app.AskToUpdateLinks = False
    app.ScreenUpdating = False

    total = 0
    omitidas = []
    fallidos = []
    try:
        with tempfile.TemporaryDirectory() as tmp:
            plantilla_base = _plantilla_base_temporal(tmp)
            if not _plantilla_base_valida(plantilla_base):
                sys.exit("La plantilla base embebida no tiene las macros "
                         "esperadas (Guarda_Hojas_CSV, Guarda_Hojas_ZIP, "
                         "Copiar_columna sin WBReplaceHyperlinkURL). El "
                         "script esta corrupto, no un archivo suelto.")

            base = app.Workbooks.Open(str(plantilla_base), ReadOnly=False, UpdateLinks=0)
            try:
                # las hojas propias de la base no son datos de ninguna
                # empresa: se renombran para que jamas puedan chocar con una
                # hoja real que entre despues, y se borran al final por ese
                # nombre temporal.
                propias = []
                for i, hoja in enumerate(base.Worksheets):
                    propias.append(f"_BASE_{i}")
                    hoja.Name = f"_BASE_{i}"

                vistos = set()
                for ruta in libros:
                    libro = None
                    try:
                        libro = app.Workbooks.Open(str(ruta.resolve()), ReadOnly=True, UpdateLinks=0)
                    except Exception:
                        fallidos.append(ruta.name)
                        continue
                    n_libro = 0
                    for hoja in _hojas_cuadro_com(libro):
                        nombre = hoja.Name
                        if nombre in vistos:
                            continue
                        if not permitida(ruta.name, nombre):
                            omitidas.append(nombre)
                            continue
                        antes = base.Worksheets.Count
                        # Posicional, no por nombre: con COM en despacho
                        # dinamico (sin type library registrada localmente,
                        # que es como se abre Excel.Application aqui) el
                        # argumento con nombre After=... no siempre se
                        # resuelve contra el parametro correcto -- y si no
                        # se resuelve, Worksheet.Copy() sin destino crea un
                        # libro nuevo aparte en vez de pegar en el actual,
                        # sin avisar de ningun error.
                        hoja.Copy(None, base.Worksheets(antes))
                        if base.Worksheets.Count != antes + 1:
                            sys.exit(f"'{nombre}' no quedo copiada dentro del libro "
                                     "fusionado (Worksheets.Count no aumento). Esto "
                                     "no deberia pasar -- avisar para revisar.")
                        nueva = base.Worksheets(base.Worksheets.Count)
                        # DBNeT trae varias hojas ocultas por defecto (las
                        # que no aplican a cada plantilla). La copia hereda
                        # ese estado; se fuerza visible ademas porque el
                        # archivo que se entrega no deberia llevar pestanas
                        # escondidas.
                        nueva.Visible = -1  # xlSheetVisible
                        vistos.add(nombre)
                        total += 1
                        n_libro += 1
                    libro.Close(SaveChanges=False)
                    if verbose:
                        print(f"  {ruta.name[:52]:54} {n_libro:3} hojas")

                if total == 0:
                    sys.exit("No se copio ninguna hoja de cuadro: revisa --solo-workiva "
                             "y que origen apunte a la carpeta correcta.")

                if base.Worksheets.Count <= len(propias):
                    sys.exit(f"El libro fusionado quedo con {base.Worksheets.Count} "
                             f"hoja(s) pero se copiaron {total} -- algo las esta "
                             "mandando a otro lado en vez de pegarlas aqui.")

                for nombre in propias:
                    base.Worksheets(nombre).Delete()

                base.SaveAs(str(salida), FileFormat=52)   # xlOpenXMLWorkbookMacroEnabled
            finally:
                base.Close(SaveChanges=False)
    finally:
        app.Quit()

    if omitidas:
        print(f"  omitidas por no estar en Workiva: {len(omitidas)}")
    if fallidos:
        print(f"  no se pudieron abrir: {', '.join(fallidos)}")
    return total, salida


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
                   help="genera un .xlsm con las macros y los botones "
                        "funcionando de verdad. Requiere Excel instalado en "
                        "esta maquina y 'pip install pywin32': lo arma Excel "
                        "mismo por COM, no es un archivo hecho a mano")
    args = p.parse_args()

    if args.con_macros:
        total, salida = fusionar_con_macros(Path(args.origen), Path(args.salida),
                                            args.verbose, args.solo_workiva)
        print(f"\n{total} hojas de cuadros -> {salida}")
        print(f"   botones y macros: funcionando (libro armado por Excel)")
        print(f"   tamano: {salida.stat().st_size/1024:.0f} KB")
        return

    salida = Path(args.salida)
    hojas, estilos = fusionar(Path(args.origen), salida, args.verbose, None,
                              args.solo_workiva)
    print(f"\n{len(hojas)} hojas de cuadros -> {salida}")
    print(f"   formatos fusionados: {len(estilos.cellXfs)} cellXfs, "
          f"{len(estilos.fonts)} fuentes, {len(estilos.fills)} rellenos, "
          f"{len(estilos.borders)} bordes")
    print(f"   tamano: {salida.stat().st_size/1024:.0f} KB")


if __name__ == "__main__":
    main()
