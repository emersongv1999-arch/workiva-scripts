#!/usr/bin/env python3
"""
Llena las plantillas .xlsm de DBNeT con los montos de un export de Workiva.

Toma el .xlsx que exportas de Workiva (un libro con todas las hojas de cuadros)
y escribe sus valores en una copia de cada .xlsm de DBNeT, dejando intactos el
proyecto VBA, los botones y todo el formato.

Como calza los datos
--------------------
Nunca por posicion de celda: las filas se corren entre versiones de plantilla.

  hoja      nombre normalizado y, si falla, por la firma de conceptos XBRL
            de la hoja (interseccion de elementos) -- resuelve los nombres
            mutilados tipo 'IAS16-Cuadros..' o 'CLCP-Mone Nac Exter'
  fila      (concepto, marca ACT/ANT de la columna D, n-esima aparicion)
            El concepto es el nombre local, DESPUES del '#': las taxonomias
            difieren (cl-ci_cor_2014-03-15 en Workiva, 2016-01-11 en DBNeT)
            pero el nombre del elemento es el mismo.
  columna   por el URI del miembro de la dimension (hojas dimensionales) o
            por el encabezado de periodo (hojas de columnas)

Todo lo que no calza se marca en el reporte; nunca se adivina.
Las celdas con formula (subtotales) no se tocan: Excel las recalcula al abrir.

Uso
---
    python llenar_dbnet_desde_workiva.py --plantillas ./xls \\
        --workiva E211_XBRL_062026.xlsx --salida ./salida

    # ver que haria sin escribir nada
    python llenar_dbnet_desde_workiva.py ... --dry-run

    # confirmar que las macros sobrevivieron
    python llenar_dbnet_desde_workiva.py --verificar ./xls ./salida
"""

import argparse
import collections
import csv
import hashlib
import re
import shutil
import sys
import zipfile
from pathlib import Path

COL_CONCEPTO = "C"
COL_PERIODO = "D"        # marca ACT/ANT en plantillas dimensionales
COL_ETIQUETA = "F"       # los datos van siempre a su derecha

PERIODOS = {
    "actual": ("periodo actual", "trimestre acumulado ano actual", "acumulado actual"),
    "anterior": ("periodo anterior", "cierre anual anterior",
                 "trimestre acumulado ano anterior", "acumulado anterior"),
    "trim_actual": ("ultimo trimestre ano actual", "ultimo trimestre actual"),
    "trim_anterior": ("ultimo trimestre ano anterior", "ultimo trimestre anterior"),
}

CELDA_RE = re.compile(r'<c r="([A-Z]+\d+)"([^>]*?)(?:/>|>(.*?)</c>)', re.S)


# ---------------------------------------------------------------- utilidades

def col_a_num(col):
    n = 0
    for ch in col:
        n = n * 26 + (ord(ch) - 64)
    return n


def num_a_col(n):
    s = ""
    while n:
        n, r = divmod(n - 1, 26)
        s = chr(65 + r) + s
    return s


def parte_ref(ref):
    m = re.match(r"([A-Z]+)(\d+)", ref)
    return m.group(1), int(m.group(2))


def normaliza(txt):
    if txt is None:
        return ""
    t = str(txt).lower().strip()
    for a, b in zip("áéíóúüñ", "aeiouun"):
        t = t.replace(a, b)
    return re.sub(r"\s+", " ", re.sub(r"\[.*?\]", " ", t)).strip()


def clave_nombre(s):
    return re.sub(r"[^a-z0-9]", "", (s or "").lower())


def desescapa(s):
    return (s.replace("&lt;", "<").replace("&gt;", ">").replace("&quot;", '"')
             .replace("&apos;", "'").replace("&#xA;", "\n").replace("&amp;", "&"))


# Caracteres que XML 1.0 no admite en ningun caso: los de control salvo
# tabulador, salto de linea y retorno de carro. Ni siquiera valen escapados
# como &#xB;. Excel tampoco los puede guardar: si alguno se cuela en un <t>,
# el .xlsm queda con XML invalido y al abrirlo sale "Hemos encontrado un
# problema con contenido de ...", con "Registros reparados: Propiedades de
# cadena de /xl/worksheets/sheetN.xml". Se cuelan sin que nadie los vea,
# arrastrados por un copiar y pegar en el texto de origen.
ILEGALES_XML = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]")


def escapa(s):
    s = ILEGALES_XML.sub("", s)
    return (s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


def clave_periodo(texto):
    n = normaliza(texto)
    if not n:
        return None
    if n in PERIODOS:
        return n
    for alias, variantes in PERIODOS.items():
        if any(n == normaliza(v) for v in variantes):
            return alias
    return None


# ------------------------------------------------------------ lectura libro


def rels_de(xml):
    """{Id: Target} de un archivo .rels, sin depender del orden de los atributos.

    Se leia con una sola expresion que exigia Id antes que Target. Los .xlsm de
    DBNeT los escribe Excel, que pone Id primero, asi que funciono siempre --
    hasta que en la carpeta de salida aparecio un .xlsx escrito por openpyxl,
    que los pone al reves: la expresion no encontraba nada y el libro moria con
    KeyError rId1 en vez de saltarselo por no ser un cuadro."""
    out = {}
    for tag in re.findall(r"<Relationship\b[^>]*/>", xml):
        i = re.search(r'Id="([^"]+)"', tag)
        t = re.search(r'Target="([^"]*)"', tag)
        if i and t:
            out[i.group(1)] = t.group(1)
    return out


class Libro:
    def __init__(self, ruta):
        self.ruta = Path(ruta)
        self.z = zipfile.ZipFile(ruta)
        try:
            raw = self.z.read("xl/sharedStrings.xml").decode("utf-8")
            self.S = [desescapa("".join(re.findall(r"<t[^>]*>(.*?)</t>", si, re.S)))
                      for si in re.findall(r"<si>(.*?)</si>", raw, re.S)]
        except KeyError:
            self.S = []
        rels = rels_de(self.z.read("xl/_rels/workbook.xml.rels").decode("utf-8"))
        wb = self.z.read("xl/workbook.xml").decode("utf-8")
        self.hojas = {}
        for tag in re.findall(r"<sheet [^>]*?>", wb):
            nombre = desescapa(re.search(r'name="([^"]*)"', tag).group(1))
            rid = re.search(r'r:id="(rId\d+)"', tag).group(1)
            destino = rels[rid].lstrip("/")
            self.hojas[nombre] = destino if destino.startswith("xl/") else "xl/" + destino
        self._cache = {}
        self._xml = {}
        self.layout_cambiado = False

    def xml(self, hoja):
        if hoja in self._xml:
            return self._xml[hoja]
        return self.z.read(self.hojas[hoja]).decode("utf-8")

    def recarga(self, hoja, xml):
        """Reemplaza el XML de una hoja en memoria y descarta su cache.

        Hace falta al agregar columnas: las celdas ya leidas quedan con las
        referencias viejas, y seguir usandolas escribiria en la columna
        equivocada."""
        self._xml[hoja] = xml
        self._cache.pop(hoja, None)
        self.layout_cambiado = True

    def celdas(self, hoja):
        """{(fila, col): (valor, es_formula, tipo)}"""
        if hoja in self._cache:
            return self._cache[hoja]
        out = {}
        for ref, attrs, inner in CELDA_RE.findall(self.xml(hoja)):
            inner = inner or ""
            col, fila = parte_ref(ref)
            mt = re.search(r't="(\w+)"', attrs)
            tipo = mt.group(1) if mt else None
            mv = re.search(r"<v>(.*?)</v>", inner, re.S)
            val = mv.group(1) if mv else None
            if tipo == "s" and val is not None and val.isdigit():
                val = self.S[int(val)] if int(val) < len(self.S) else ""
            elif tipo == "inlineStr":
                val = desescapa("".join(re.findall(r"<t[^>]*>(.*?)</t>", inner, re.S)))
            elif val is not None:
                val = desescapa(val)
            out[(fila, col)] = (val.strip() if isinstance(val, str) else val,
                                "<f" in inner, tipo)
        self._cache[hoja] = out
        return out


# ------------------------------------------------------ estructura de hoja

def nombre_local(v):
    """Nombre del elemento XBRL, con el prefijo de taxonomia normalizado.

    El ID del elemento lleva el prefijo pegado ('ifrs-full_DeferredTaxLiabilityAsset').
    Workiva escribe algunos con el prefijo antiguo 'ifrs_' y DBNeT con
    'ifrs-full_', que es el mismo elemento: sin unificarlos, las 28 filas de
    IAS12-InfoDifeTemp quedaban vacias en la plantilla y su monto se perdia.
    Solo se unifica ese par; 'cl-ci_' es otra taxonomia y no se toca."""
    local = v.split("#")[-1].strip()
    if local.startswith("ifrs_"):
        return "ifrs-full_" + local[len("ifrs_"):]
    return local


def conceptos_set(cel):
    return {nombre_local(v)
            for (f, c), (v, _, _) in cel.items()
            if c == COL_CONCEPTO and v and ".xsd#" in v}


def filas_indexadas(cel):
    """[(fila, concepto, marca, ordinal)] en orden de aparicion.

    El ordinal desempata los bloques de dimension apilados: una misma pareja
    (concepto, ACT) puede repetirse una vez por bloque."""
    vistos = collections.Counter()
    out = []
    for (fila, col), (v, _, _) in sorted(cel.items()):
        if col != COL_CONCEPTO or not v or ".xsd#" not in v:
            continue
        concepto = nombre_local(v)
        marca = (cel.get((fila, COL_PERIODO)) or ("",))[0] or ""
        marca = marca.strip().upper()
        marca = marca if marca in ("ACT", "ANT") else ""
        vistos[(concepto, marca)] += 1
        out.append((fila, concepto, marca, vistos[(concepto, marca)]))
    return out


def seccion_periodo(cel, fila):
    """'ACTUAL' / 'ANTERIOR' / None segun el encabezado que manda sobre la fila.

    Los cuadros repiten la misma tabla dos veces, una por periodo, separadas
    por un titulo 'Periodo Actual' o 'Periodo Anterior' en la columna de
    etiquetas. Ese titulo es lo que de verdad dice a que ano pertenece una
    cifra; la marca ACT/ANT de la columna D es solo un rotulo, y Workiva y
    DBNeT no siempre la escriben igual."""
    mejor = None
    for (f, c), (v, _, _) in cel.items():
        if c != COL_ETIQUETA or not v or f >= fila:
            continue
        n = normaliza(v)
        if n in ("periodo actual", "periodo anterior"):
            if mejor is None or f > mejor[0]:
                mejor = (f, "ACTUAL" if "actual" in n else "ANTERIOR")
    return mejor[1] if mejor else None


def _por_etiqueta(cel, filas):
    """{(etiqueta, n): fila} — n es la n-esima fila con esa etiqueta.

    Solo para filas que llevan concepto XBRL, y sin etiquetas vacias: la
    etiqueta es un respaldo para identificar la linea cuando el codigo del
    concepto difiere entre Workiva y DBNeT, no un criterio por si sola."""
    vistos = collections.Counter()
    out = {}
    for fila, _, _, _ in filas:
        etq = normaliza((cel.get((fila, COL_ETIQUETA)) or ("",))[0] or "")
        if not etq:
            continue
        vistos[etq] += 1
        out[(etq, vistos[etq])] = fila
    return out


def _por_posicion(filas):
    """{(concepto, n): fila} — n es la n-esima aparicion del concepto en la
    hoja, contada en orden y SIN mirar la marca ACT/ANT."""
    vistos = collections.Counter()
    out = {}
    for fila, concepto, _, _ in filas:
        vistos[concepto] += 1
        out[(concepto, vistos[concepto])] = fila
    return out


def _con_ordinal(claves):
    """{col: (clave, n)} — n desempata columnas que comparten clave.

    Las columnas 'Agregar columna opcional' se llaman todas igual; el orden
    izquierda-a-derecha es lo unico que las distingue, y es el mismo en la
    plantilla y en el export porque salen del mismo origen."""
    vistos = collections.Counter()
    out = {}
    for col in sorted(claves, key=col_a_num):
        k = claves[col]
        vistos[k] += 1
        out[col] = (k, vistos[k])
    return out


def _hereda_opcionales(cel, claves, fila_cod, limite):
    """Da identidad a las columnas opcionales que ya se usaron.

    Workiva deja sin codigo y sin etiqueta las columnas 'Agregar columna
    opcional' que alguien ya lleno: quedan con datos pero sin nada que las
    identifique. Contarlas de menos hace que la plantilla no crezca lo
    suficiente y media tabla se quede sin destino -- en CIRC1901-InfoReveMA
    el tramo son 108 columnas y solo 50 conservan la etiqueta.

    Cada columna sin identificar hereda la clave de la opcional que tiene a
    su izquierda, y nunca se cruza un ancla: una columna a la derecha del
    miembro de la taxonomia ya no pertenece al tramo (las que Workiva deja
    despues del total son celdas de trabajo, no datos del cuadro)."""
    anclas = {c for c, k in claves.items() if not k.startswith("lbl:")}
    con_dato = {c for (f, c), (v, _, _) in cel.items()
                if f > fila_cod and col_a_num(c) > limite and v not in (None, "")}
    ultima = None
    for c in sorted(con_dato | set(claves), key=col_a_num):
        if c in anclas:
            ultima = None
        elif c in claves:
            ultima = claves[c]
        elif ultima and c in con_dato:
            claves[c] = ultima


def columnas_de_datos(cel):
    """{col: (clave, n)}, tipo. La clave es el miembro de la dimension o el
    periodo de la columna."""
    limite = col_a_num(COL_ETIQUETA)

    # 1) hoja dimensional: la fila de codigos de miembro es la ultima marcada
    #    DIMENUE/DIMEAVA/DIMEPERS en la columna A (Workiva renombra la marca),
    #    o la primera que traiga URIs a la derecha de la etiqueta.
    marcas = sorted(f for (f, c), (v, _, _) in cel.items()
                    if c == "A" and v and v.upper().startswith("DIME"))
    fila_cod = marcas[-1] if marcas else None
    if fila_cod is None:
        uris = [f for (f, c), (v, _, _) in cel.items()
                if col_a_num(c) > limite and v and ".xsd#" in v]
        fila_cod = min(uris) if uris else None
    if fila_cod is not None:
        claves = {}
        for (f, c), (v, _, _) in cel.items():
            if f != fila_cod or col_a_num(c) <= limite:
                continue
            if v and ".xsd#" in v:
                claves[c] = nombre_local(v)
            else:
                # miembro agregado por el usuario: su ID lo genera una formula
                # que en el export de Workiva llega rota (#NAME?), asi que la
                # identidad la da la etiqueta de la fila de arriba.
                etq = (cel.get((fila_cod - 1, c)) or ("",))[0] or ""
                etq = normaliza(etq)
                if etq:
                    claves[c] = "lbl:" + etq
        if claves:
            _hereda_opcionales(cel, claves, fila_cod, limite)
            return _con_ordinal(claves), "dimensional"

    # 2) hoja de columnas: encabezados de periodo
    periodos = {}
    for (f, c), (v, _, _) in cel.items():
        if not v or col_a_num(c) <= limite:
            continue
        k = clave_periodo(v)
        if k:
            periodos.setdefault(c, k)
    if periodos:
        return _con_ordinal(periodos), "columnas"
    return {}, "sin-columnas"


# ------------------------------------------------------------- mapa de hojas

# Cuanto del cuadro de DBNeT tiene que estar en la hoja de Workiva para que
# valga la pena avisar. Se mide contra el tamano del cuadro de DBNeT y no
# contra el menor de los dos, porque con el menor una hoja de Workiva de dos
# conceptos daba 50% de parecido con un cuadro de cuarenta: un concepto
# generico compartido bastaba para inventar una alarma. Medido asi, ese mismo
# caso da 3%.
PARECIDO_MINIMO = 0.20


def mapear_hojas(plantillas, wv, mapa_csv=None):
    """[(ruta_xlsm, hoja_dbnet, hoja_workiva|None, metodo)]"""
    wv_conc = {}
    for h in wv.hojas:
        c = conceptos_set(wv.celdas(h))
        if c:
            wv_conc[h] = c
    destinos = []
    for ruta in sorted(plantillas):
        lib = Libro(ruta)
        for h in lib.hojas:
            c = conceptos_set(lib.celdas(h))
            if c:
                destinos.append((ruta, h, c))

    if mapa_csv:
        fijo = {}
        with open(mapa_csv, encoding="utf-8-sig") as fh:
            for r in csv.DictReader(fh, delimiter=";"):
                if r.get("hoja_workiva"):
                    fijo[(r["archivo_dbnet"], r["hoja_dbnet"])] = r["hoja_workiva"]
        return [(ru, h, fijo.get((Path(ru).name, h)), "mapa.csv")
                for ru, h, _ in destinos]

    par, usadas = {}, set()
    for ru, h, _ in destinos:                       # 1) nombre normalizado
        for w in wv_conc:
            if clave_nombre(w) == clave_nombre(h) and w not in usadas:
                par[(ru, h)] = (w, "nombre"); usadas.add(w); break
    cands = []                                      # 2) firma de conceptos
    for ru, h, c in destinos:
        if (ru, h) in par:
            continue
        for w, cw in wv_conc.items():
            if w in usadas:
                continue
            inter = len(c & cw)
            if inter:
                cands.append((inter / min(len(c), len(cw)), inter / len(c | cw), ru, h, w))
    cands.sort(reverse=True)
    for cob, jac, ru, h, w in cands:
        if (ru, h) in par or w in usadas or cob < 0.8:
            continue
        par[(ru, h)] = (w, f"conceptos J={jac:.2f}"); usadas.add(w)

    sobrantes = [w for w in wv_conc if w not in usadas]
    # Un cuadro sin llenar puede ser de dos cosas muy distintas: que la nota
    # no aplique a la empresa (y entonces no hay nada parecido en Workiva), o
    # que DBNeT haya rehecho el cuadro (y entonces quedo una hoja de Workiva
    # suelta con la mitad de los conceptos). La segunda hay que mirarla; la
    # primera no. Se distinguen mirando cuanto se parece la mejor sobrante.
    pistas = {}
    for ru, h, c in destinos:
        if (ru, h) in par:
            continue
        cob, w = max(((len(c & wv_conc[w]) / len(c), w)
                      for w in sobrantes), default=(0.0, None))
        if cob >= PARECIDO_MINIMO:
            pistas[(ru, h)] = (w, cob)
    return ([(ru, h, *par.get((ru, h), (None, "SIN CONTRAPARTE"))) for ru, h, _ in destinos],
            sobrantes, pistas)


# ------------------------------------------------------------- escritura XML

def formatea(valor, tipo):
    if tipo in ("s", "inlineStr", "str"):
        return f'<is><t xml:space="preserve">{escapa(valor)}</t></is>', ' t="inlineStr"'
    return f"<v>{valor}</v>", ""


MAX_CELDA = 32767          # limite duro de Excel: caracteres por celda


def recorta(valor, tipo, ref, reporte, archivo, hoja_d, hoja_w):
    """Recorta un texto que no cabe en una celda, dejando constancia.

    Una celda con mas de 32767 caracteres produce un .xlsm que es XML
    perfectamente valido pero que Excel no puede cargar: al abrirlo ofrece
    "recuperar el maximo de contenido posible" (que para este caso es
    truncarlo), y Workbooks.Open falla de plano, porque para preguntar eso
    necesita mostrar un dialogo y la automatizacion corre con los avisos
    apagados. Los bloques de texto de las revelaciones que exporta Workiva
    llegan a pasarse: se recortan aqui, donde se puede avisar cual se
    corto, en vez de dejar que Excel lo haga sin que nadie se entere."""
    if not isinstance(valor, str) or tipo not in ("s", "inlineStr", "str"):
        return valor
    if len(valor) <= MAX_CELDA:
        return valor
    reporte.append([archivo, hoja_d, hoja_w, "", ref, "", len(valor),
                    f"TEXTO RECORTADO A {MAX_CELDA} CARACTERES (limite de Excel)"])
    return valor[:MAX_CELDA]


def escribe(xml, ref, valor, tipo):
    """Mete el valor en la celda `ref` conservando su atributo s= (formato)."""
    pat = re.compile(r'<c r="%s"([^>]*?)(?:/>|>(.*?)</c>)' % re.escape(ref), re.S)
    m = pat.search(xml)
    cuerpo, attr_tipo = formatea(valor, tipo)
    if m:
        attrs = re.sub(r'\s*t="\w+"', "", m.group(1))
        nuevo = f'<c r="{ref}"{attrs}{attr_tipo}>{cuerpo}</c>'
        return (xml[:m.start()] + nuevo + xml[m.end():], True) if nuevo != m.group(0) else (xml, False)
    return _inserta(xml, ref, cuerpo, attr_tipo), True


def _inserta(xml, ref, cuerpo, attr_tipo):
    col, fila = parte_ref(ref)
    objetivo = col_a_num(col)
    nueva = f'<c r="{ref}"{attr_tipo}>{cuerpo}</c>'
    mf = re.search(r'<row r="%d"([^>]*?)(?:/>|>(.*?)</row>)' % fila, xml, re.S)
    if not mf:
        raise KeyError(f"fila {fila} inexistente")
    attrs, inner = mf.group(1), mf.group(2) or ""
    pos = len(inner)
    for m in CELDA_RE.finditer(inner):
        if col_a_num(parte_ref(m.group(1))[0]) > objetivo:
            pos = m.start(); break
    inner = inner[:pos] + nueva + inner[pos:]
    return xml[:mf.start()] + f'<row r="{fila}"{attrs}>{inner}</row>' + xml[mf.end():]


def actualiza_cache(xml, ref, valor):
    """Refresca el <v> de una celda con formula, sin tocar la formula.

    La plantilla llega con el subtotal en cache 0 y Excel lo recalcula al
    abrir, pero cualquier lector que no evalue formulas (el generador de CSV)
    veria ese 0. Se guarda el valor que ya trae calculado Workiva; si Excel
    llega a otro numero al abrir, lo pisa con el suyo.

    Dos formas autocerradas hay que tener en cuenta, y las dos mordieron:

    La celda: con '<c r="X"[^>]*>' una celda como <c r="D5" s="3"/> tambien
    hacia match -- [^>]* se come el '/' -- y el (.*?)(</c>) seguia de largo
    hasta el cierre de una celda POSTERIOR, cuyo <v> era el que se
    reescribia. El valor terminaba en la celda equivocada.

    El cache: una formula sin valor calculado llega como <f>..</f><v/>, y
    preguntar por '<v>' da falso ahi. Entonces en vez de reemplazar el
    cache se AGREGABA otro, dejando la celda con <v/><v>0</v>. Eso es XML
    bien formado -- pasa cualquier validador -- pero el esquema de Excel
    admite un solo <v> por celda: el archivo abre pidiendo repararse, y
    Workbooks.Open falla porque no puede mostrar esa pregunta."""
    pat = re.compile(r'<c r="%s"([^>]*?)(?:/>|>(.*?)</c>)' % re.escape(ref), re.S)
    m = pat.search(xml)
    if not m or m.group(2) is None or "<f" not in m.group(2):
        return xml, False           # sin cuerpo no hay formula que refrescar
    cuerpo = m.group(2)
    V = re.compile(r"<v(?:\s[^>]*)?/>|<v(?:\s[^>]*)?>.*?</v>", re.S)
    nuevo = (V.sub("<v>%s</v>" % valor, cuerpo, count=1)
             if V.search(cuerpo) else cuerpo + "<v>%s</v>" % valor)
    if nuevo == cuerpo:
        return xml, False
    celda = '<c r="%s"%s>%s</c>' % (ref, m.group(1), nuevo)
    return xml[:m.start()] + celda + xml[m.end():], True


# ------------------------------------------------- presentacion del texto

def _elementos(xml, tag):
    """Cada <tag .../> o <tag ...>...</tag> de primer nivel, como texto."""
    out, i = [], 0
    abre = re.compile(r"<%s(\s[^>]*?)?(/?)>" % tag)
    cierre = "</%s>" % tag
    while True:
        m = abre.search(xml, i)
        if not m:
            return out
        if m.group(2) == "/":
            out.append(m.group(0))
            i = m.end()
        else:
            j = xml.index(cierre, m.end()) + len(cierre)
            out.append(xml[m.start():j])
            i = j


def _con_ajuste(xf):
    """El mismo formato, pero con ajuste de texto y alineado arriba."""
    m = re.search(r"<alignment[^>]*?/>", xf)
    if m:
        a = re.sub(r'\s*(?:wrapText|vertical)="[^"]*"', "", m.group(0))
        xf = xf[:m.start()] + a[:-2] + ' vertical="top" wrapText="1"/>' + xf[m.end():]
    elif "<alignment" in xf:
        return xf                       # forma rara: mejor no tocarlo
    else:
        a = '<alignment vertical="top" wrapText="1"/>'
        xf = xf[:-2] + ">" + a + "</xf>" if xf.endswith("/>") \
            else xf[:xf.rindex("</xf>")] + a + "</xf>"
    # sin applyAlignment Excel ignora el <alignment> propio y hereda el del
    # estilo padre, asi que el ajuste no se veria
    if "applyAlignment" not in xf:
        xf = xf.replace("<xf ", '<xf applyAlignment="1" ', 1)
    return xf


class Estilos:
    """Los formatos del libro, con la posibilidad de agregar variantes.

    Un .xlsm no guarda el formato en la celda sino un indice a la lista
    <cellXfs> de styles.xml. Para que un texto largo se vea envuelto en
    varias lineas la celda tiene que apuntar a un formato con wrapText, y
    ese formato casi nunca existe en la plantilla: se clona el que la celda
    ya traia y se le agrega el ajuste, para no perder ni el borde, ni el
    relleno, ni la fuente que le puso DBNeT."""

    def __init__(self, libro):
        self.raw = libro.z.read("xl/styles.xml").decode("utf-8")
        m = re.search(r"<cellXfs[^>]*>(.*?)</cellXfs>", self.raw, re.S)
        self.tramo = (m.start(), m.end()) if m else None
        self.xfs = _elementos(m.group(1), "xf") if m else []
        self._ya = {}
        self.cambio = False

    def con_ajuste(self, idx):
        if self.tramo is None or not 0 <= idx < len(self.xfs):
            return idx
        if idx not in self._ya:
            nuevo = _con_ajuste(self.xfs[idx])
            if nuevo in self.xfs:
                self._ya[idx] = self.xfs.index(nuevo)
            else:
                self.xfs.append(nuevo)
                self._ya[idx] = len(self.xfs) - 1
                self.cambio = True
        return self._ya[idx]

    def xml(self):
        ini, fin = self.tramo
        return (self.raw[:ini]
                + '<cellXfs count="%d">%s</cellXfs>' % (len(self.xfs), "".join(self.xfs))
                + self.raw[fin:])


def anchos_de_columna(xml):
    """{numero de columna: ancho en caracteres}, mas el ancho por defecto."""
    defecto = 8.43
    m = re.search(r"<sheetFormatPr[^>]*>", xml)
    if m:
        d = re.search(r'defaultColWidth="([\d.]+)"', m.group(0))
        if d:
            defecto = float(d.group(1))
    anchos = {}
    for c in re.findall(r"<col\b[^>]*/>", xml):
        a = re.search(r'width="([\d.]+)"', c)
        lo = re.search(r'min="(\d+)"', c)
        hi = re.search(r'max="(\d+)"', c)
        if a and lo and hi:
            for n in range(int(lo.group(1)), min(int(hi.group(1)), 400) + 1):
                anchos[n] = float(a.group(1))
    return anchos, defecto


def _ancho_util(ref, anchos, defecto, fusiones):
    """Ancho donde se puede escribir: el de la celda, o el de la fusion."""
    col, fila = parte_ref(ref)
    desde = hasta = col_a_num(col)
    hasta = fusiones.get(ref, hasta)
    return sum(anchos.get(n, defecto) for n in range(desde, hasta + 1))


def _fusiones(xml):
    """{celda de arriba a la izquierda: ultima columna de la fusion}."""
    out = {}
    for r in re.findall(r'<mergeCell ref="([A-Z]+\d+):([A-Z]+\d+)"', xml):
        out[r[0]] = col_a_num(parte_ref(r[1])[0])
    return out


ALTO_LINEA = 15.0        # puntos que ocupa un renglon con la fuente base
ALTO_MAX = 409.5         # tope de Excel, el mismo del autoajuste de fila


def _lineas(texto, ancho):
    cabe = max(8, int(ancho) - 1)
    return sum(max(1, -(-len(p) // cabe)) for p in texto.split("\n"))


def ajusta_bloques_texto(xml, est):
    """Envuelve los textos largos recien escritos y le da alto a su fila.

    DBNeT deja esas celdas sin ajuste de texto porque en su plantilla llegan
    vacias, donde una sola linea sobra. Con el texto puesto el parrafo se
    sale por el costado y solo se puede leer en la barra de formulas; Workiva
    lo muestra envuelto. Esto deja el archivo llenado igual que Workiva.

    Solo se tocan las celdas que escribio este programa, que son las unicas
    que quedan como inlineStr -- las de la plantilla van por sharedStrings.

    Es presentacion y nada mas. El boton "Crear CSV" escribe el contenido de
    la celda, que no cambia: ni el ajuste de texto ni el alto de la fila
    aparecen en el CSV."""
    if est.tramo is None or 'inlineStr' not in xml:
        return xml
    anchos, defecto = anchos_de_columna(xml)
    fusiones = _fusiones(xml)

    def rehace_fila(mf):
        attrs, inner = mf.group(2), mf.group(3)
        if not inner or 'inlineStr' not in inner:
            return mf.group(0)
        alto = [0.0]

        def rehace_celda(mc):
            ref, cattrs, cuerpo = mc.group(1), mc.group(2), mc.group(3)
            if cuerpo is None or 'inlineStr' not in cattrs:
                return mc.group(0)
            texto = desescapa("".join(re.findall(r"<t[^>]*>(.*?)</t>", cuerpo, re.S)))
            n = _lineas(texto, _ancho_util(ref, anchos, defecto, fusiones))
            if n < 2:
                return mc.group(0)
            alto[0] = max(alto[0], min(ALTO_MAX, n * ALTO_LINEA))
            ms = re.search(r'\ss="(\d+)"', cattrs)
            if ms:
                cattrs = (cattrs[:ms.start()] + ' s="%d"' % est.con_ajuste(int(ms.group(1)))
                          + cattrs[ms.end():])
            else:
                cattrs = ' s="%d"' % est.con_ajuste(0) + cattrs
            return '<c r="%s"%s>%s</c>' % (ref, cattrs, cuerpo)

        inner = CELDA_RE.sub(rehace_celda, inner)
        if not alto[0]:
            return mf.group(0)
        previo = re.search(r'\sht="([\d.]+)"', attrs)
        if previo:
            alto[0] = max(alto[0], float(previo.group(1)))
        attrs = re.sub(r'\s(?:ht|customHeight)="[^"]*"', "", attrs)
        return '<row r="%s"%s ht="%g" customHeight="1">%s</row>' % (
            mf.group(1), attrs, alto[0], inner)

    return re.sub(r'<row r="(\d+)"([^>]*?)(?:/>|>(.*?)</row>)', rehace_fila, xml, flags=re.S)

def recalculo(wb_xml):
    if "fullCalcOnLoad" in wb_xml:
        return wb_xml
    if "<calcPr" in wb_xml:
        return re.sub(r"<calcPr([^>]*?)/>", r'<calcPr\1 fullCalcOnLoad="1"/>', wb_xml, count=1)
    return wb_xml.replace("</workbook>", '<calcPr fullCalcOnLoad="1"/></workbook>')


def sin_calcchain(zin, cambios):
    """Saca xl/calcChain.xml del paquete, con sus dos referencias.

    calcChain es la cache del orden en que Excel evalua las formulas, y
    apunta a las celdas por posicion. Al insertar columnas las formulas se
    corren, la cache queda apuntando a celdas que ya no las tienen, y Excel
    abre el archivo pidiendo repararlo -- lo que rompe Workbooks.Open, que
    no puede mostrar esa pregunta. Es una cache: se borra y Excel la
    reconstruye sola al abrir."""
    ct = zin.read("[Content_Types].xml").decode("utf-8")
    cambios["[Content_Types].xml"] = re.sub(
        r'<Override PartName="/xl/calcChain\.xml"[^>]*/>', "", ct)
    rels = zin.read("xl/_rels/workbook.xml.rels").decode("utf-8")
    cambios["xl/_rels/workbook.xml.rels"] = re.sub(
        r'<Relationship[^>]*Target="calcChain\.xml"[^>]*/>', "", rels)
    return {"xl/calcChain.xml"}


def reescribe_zip(origen, destino, cambios, quitar=()):
    """Copia el paquete entero cambiando solo las partes de `cambios`.
    vbaProject.bin, drawings, styles y media pasan byte a byte.

    Antes de escribir se valida el XML de cada parte modificada. Un .xlsm con
    XML invalido igual se genera y hasta se abre -- Excel ofrece repararlo --
    pero deja de servir para automatizar: Workbooks.Open falla, porque para
    preguntar si repara necesita mostrar un dialogo, y el script corre con los
    avisos apagados. Sale mas barato parar aqui que descubrirlo tres pasos
    despues, cuando ya no se sabe de donde vino."""
    import xml.etree.ElementTree as ET
    for parte, texto in cambios.items():
        try:
            raiz = ET.fromstring(texto)
        except ET.ParseError as e:
            raise ValueError(
                f"{destino.name}: el XML de {parte} quedo invalido ({e}). "
                "El archivo NO se escribio.") from None
        # Estar bien formado no basta: hay cosas que cualquier parser acepta
        # y el esquema de Excel no. Las dos que ya nos costaron un archivo
        # que no se podia abrir por automatizacion:
        NS = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
        for t in raiz.iter(NS + "t"):
            if t.text and len(t.text) > MAX_CELDA:
                raise ValueError(
                    f"{destino.name}: una celda de {parte} quedo con "
                    f"{len(t.text)} caracteres (el maximo de Excel es "
                    f"{MAX_CELDA}). El archivo NO se escribio.")
        for c in raiz.iter(NS + "c"):
            n_v = len(c.findall(NS + "v"))
            if n_v > 1:
                raise ValueError(
                    f"{destino.name}: la celda {c.get('r')} de {parte} quedo "
                    f"con {n_v} elementos <v>; Excel admite uno solo. "
                    "El archivo NO se escribio.")

    destino.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(origen) as zin, \
         zipfile.ZipFile(destino, "w", zipfile.ZIP_DEFLATED) as zout:
        for info in zin.infolist():
            if info.filename in quitar:
                continue
            datos = cambios.get(info.filename)
            datos = datos.encode("utf-8") if datos is not None else zin.read(info.filename)
            nuevo = zipfile.ZipInfo(info.filename, date_time=info.date_time)
            nuevo.compress_type = info.compress_type
            nuevo.external_attr = info.external_attr
            nuevo.internal_attr = info.internal_attr
            nuevo.create_system = info.create_system
            zout.writestr(nuevo, datos)


# --------------------------------------------- columnas que faltan crear

# Referencia A1 dentro de una formula. El (?<![A-Z0-9_$.!]) de la izquierda no
# es adorno: sin el, el literal "CIRC1901-InfoReveMA_" que va DENTRO de la
# formula del ID de miembro da match como si "IRC1901" fuera una celda, y la
# formula termina diciendo "CIRD1901". Por lo mismo los literales se saltan.
_REF = re.compile(r"(?<![A-Z0-9_$.!])(\$?)([A-Z]{1,3})(\$?)(\d+)(?![\d(A-Z_])")
_LITERAL = re.compile(r'"[^"]*"')
_CELDA_X = re.compile(
    r'<c r="([A-Z]{1,3})(\d+)"((?:[^>"]|"[^"]*")*?)(?:/>|>(.*?)</c>)', re.S)
_FILA_X = re.compile(
    r'<row r="(\d+)"((?:[^>"]|"[^"]*")*?)(?:/>|>(.*?)</row>)', re.S)


def _fuera_de_literales(f, fn):
    salida, ultimo = [], 0
    for m in _LITERAL.finditer(f):
        salida.append(fn(f[ultimo:m.start()]))
        salida.append(m.group(0))
        ultimo = m.end()
    salida.append(fn(f[ultimo:]))
    return "".join(salida)


def _corre_ref(ref, desde, n):
    m = re.fullmatch(r"(\$?)([A-Z]{1,3})(\$?)(\d+)", ref)
    if not m:
        return ref
    d1, col, d2, fila = m.groups()
    nueva = num_a_col(col_a_num(col) + n) if col_a_num(col) >= desde else col
    return f"{d1}{nueva}{d2}{fila}"


def _corre_formula(f, desde, n):
    return _fuera_de_literales(
        f, lambda t: _REF.sub(lambda m: _corre_ref(m.group(0), desde, n), t))


def _corre_rango(txt, desde, n):
    return " ".join(":".join(_corre_ref(p, desde, n) for p in trozo.split(":"))
                    for trozo in txt.split())


def inserta_columnas(xml, col_modelo, n):
    """Duplica `col_modelo` n veces insertando a su derecha.

    Es lo que hace el boton "Copiar Columna" de DBNeT. Se inserta SOBRE una
    columna opcional existente y no despues de la ultima, a proposito: asi el
    rango del total, SUM(G16:H16), se estira a SUM(G16:BD16) e incluye las
    nuevas. Insertando despues, el total las dejaria fuera."""
    if n <= 0:
        return xml
    desde = col_a_num(col_modelo)

    def rehacer_fila(mf):
        r, fattrs, inner = mf.group(1), mf.group(2) or "", mf.group(3)
        if inner is None:
            return mf.group(0)
        modelo, salida, pos_modelo = None, [], None
        for mc in _CELDA_X.finditer(inner):
            col, fila, attrs, cuerpo = mc.groups()
            if col == col_modelo:
                # el modelo se queda igual: ni su nombre ni su formula cambian
                modelo, pos_modelo = (attrs, cuerpo), len(salida)
                salida.append(mc.group(0))
                continue
            # Las celdas a la izquierda conservan su nombre, pero sus formulas
            # igual hay que correrlas: pueden referenciar columnas de la
            # derecha, que si se movieron. El maestro de una formula
            # compartida vive a la izquierda y su ref="O36:AB36" tiene que
            # estirarse, o sus seguidores quedan fuera de rango y Excel da el
            # archivo por danado.
            nuevo_col = col if col_a_num(col) < desde else num_a_col(col_a_num(col) + n)
            salida.append(_recelda(mc.group(0), nuevo_col, fila, desde, n))
        if modelo is not None:
            attrs, cuerpo = modelo
            copias = [_arma_celda(num_a_col(desde + i), r, attrs,
                                  _recuerpo(cuerpo, desde, i, col_modelo,
                                            num_a_col(desde + i)))
                      for i in range(1, n + 1)]
            salida[pos_modelo + 1:pos_modelo + 1] = copias
        fattrs = re.sub(r'spans="(\d+):(\d+)"',
                        lambda m: 'spans="%s:%d"' % (m.group(1), int(m.group(2)) + n),
                        fattrs)
        return f'<row r="{r}"{fattrs}>{"".join(salida)}</row>'

    xml = _FILA_X.sub(rehacer_fila, xml)
    for pat, plantilla in (
            (r'<dimension ref="([^"]+)"/>', '<dimension ref="%s"/>'),
            (r'<mergeCell ref="([^"]+)"/>', '<mergeCell ref="%s"/>')):
        xml = re.sub(pat, lambda m: plantilla % _corre_rango(m.group(1), desde, n), xml)
    for pat in (r'(<conditionalFormatting sqref=")([^"]+)"',
                r'(<dataValidation [^>]*sqref=")([^"]+)"'):
        xml = re.sub(pat, lambda m: m.group(1) + _corre_rango(m.group(2), desde, n) + '"',
                     xml)

    def rehacer_col(m):
        mn, mx, resto = int(m.group(1)), int(m.group(2)), m.group(3)
        if mx < desde:
            return m.group(0)
        if mn <= desde <= mx:          # el ancho del modelo cubre a las nuevas
            mx += n
        else:
            mn, mx = mn + n, mx + n
        return f'<col min="{mn}" max="{mx}"{resto}/>'
    return re.sub(r'<col min="(\d+)" max="(\d+)"([^>]*?)/>', rehacer_col, xml)


def _arma_celda(col, fila, attrs, cuerpo):
    if cuerpo is None:
        return f'<c r="{col}{fila}"{attrs}/>'
    return f'<c r="{col}{fila}"{attrs}>{cuerpo}</c>'


def _recelda(entero, nuevo_col, fila, desde, n):
    m = _CELDA_X.fullmatch(entero)
    attrs, cuerpo = m.group(3), m.group(4)
    if cuerpo:
        cuerpo = re.sub(r"(<f[^>]*>)(.*?)(</f>)",
                        lambda x: x.group(1) + _corre_formula(x.group(2), desde, n)
                        + x.group(3), cuerpo, flags=re.S)
        cuerpo = re.sub(r'(<f[^>]*\bref=")([^"]+)(")',
                        lambda x: x.group(1) + _corre_rango(x.group(2), desde, n)
                        + x.group(3), cuerpo)
    return _arma_celda(nuevo_col, fila, attrs, cuerpo)


def _recuerpo(cuerpo, desde, i, col_modelo, col_nueva):
    if not cuerpo:
        return cuerpo
    if "<f" not in cuerpo:
        return cuerpo          # celda de valor (el encabezado): se copia igual

    def arregla(m):
        f = _corre_formula(m.group(2), desde + 1, i)
        f = _fuera_de_literales(f, lambda t: re.sub(
            r"(?<![A-Z0-9_$.!])(\$?)%s(\$?)(\d+)(?![\d(A-Z_])" % col_modelo,
            lambda x: "%s%s%s%s" % (x.group(1), col_nueva, x.group(2), x.group(3)), t))
        return m.group(1) + f + m.group(3)
    cuerpo = re.sub(r"(<f[^>]*>)(.*?)(</f>)", arregla, cuerpo, flags=re.S)
    # Solo en celdas con formula: el cache heredado es el de OTRA columna.
    # Excel lo recalcula al abrir; dejarlo seria mostrar el valor del vecino.
    return re.sub(r"<v>.*?</v>", "", cuerpo, flags=re.S)


def fila_de_codigos(cel):
    """La fila donde viven los IDs de miembro. Misma deteccion que usa
    columnas_de_datos; la etiqueta visible del miembro va justo arriba."""
    limite = col_a_num(COL_ETIQUETA)
    marcas = sorted(f for (f, c), (v, _, _) in cel.items()
                    if c == "A" and v and v.upper().startswith("DIME"))
    if marcas:
        return marcas[-1]
    uris = [f for (f, c), (v, _, _) in cel.items()
            if col_a_num(c) > limite and v and ".xsd#" in v]
    return min(uris) if uris else None


def _canon_anclas(cols_d, cols_w):
    """Devuelve como comparar los nombres de ancla de los dos lados.

    Para la misma columna DBNeT nombra el eje terminado en 'Domain' y Workiva
    en 'Member' (38 casos en el export real). Como el emparejamiento de tramos
    va por el nombre del ancla, sin unificarlos el tramo entero no se empareja
    y sus columnas opcionales se quedan sin destino: asi se perdian los
    18.384.000 de servidumbres en IAS38-InfoActiIntaUtil.

    Se unifica solo cuando es inequivoco. Si en una hoja el mismo nombre base
    aparece con los dos sufijos -- pasa en IAS36-PerdDeteSign -- ahi son ejes
    distintos de verdad y se dejan tal cual."""
    ambiguos = set()
    for cols in (cols_d, cols_w):
        por_base = collections.defaultdict(set)
        for k in cols.values():
            if not k[0].startswith("lbl:"):
                por_base[re.sub(r"(Domain|Member)$", "", k[0])].add(k[0])
        ambiguos |= {b for b, s in por_base.items() if len(s) > 1}

    def canon(nombre):
        if nombre is None or nombre.startswith("lbl:"):
            return nombre
        base = re.sub(r"(Domain|Member)$", "", nombre)
        return nombre if base in ambiguos else base
    return canon


def _tramos(cols, canon=None):
    """[(ancla_o_None, [columnas opcionales que la preceden])].

    Las columnas ancla son las que llevan un miembro de la taxonomia; las
    opcionales son las que agrega el usuario, cuya unica identidad es su
    posicion dentro del tramo."""
    out, sueltas = [], []
    for c in sorted(cols, key=col_a_num):
        if cols[c][0].startswith("lbl:"):
            sueltas.append(c)
        else:
            out.append((canon(cols[c][0]) if canon else cols[c][0], sueltas))
            sueltas = []
    out.append((None, sueltas))
    return out


def empareja_opcionales(cols_d, cols_w):
    """[(col_dbnet, col_workiva)] para las columnas que agrega el usuario.

    Estas no se pueden emparejar por nombre: en la plantilla se llaman todas
    "Agregar columna opcional" y en Workiva llevan el nombre que les puso el
    usuario ("prestamo 1", "prestamo 2"...). Dentro de un tramo delimitado por
    columnas ancla, lo unico que las identifica es el orden -- que es el mismo
    a ambos lados porque salen del mismo cuadro."""
    pares = []
    usados = collections.Counter()
    canon = _canon_anclas(cols_d, cols_w)
    por_ancla_w = {}
    for ancla, opcs in _tramos(cols_w, canon):
        por_ancla_w.setdefault(ancla, []).append(opcs)
    for ancla, opcs_d in _tramos(cols_d, canon):
        disponibles = por_ancla_w.get(ancla)
        if not disponibles or usados[ancla] >= len(disponibles):
            continue
        opcs_w = disponibles[usados[ancla]]
        usados[ancla] += 1
        pares.extend(zip(opcs_d, opcs_w))
    return pares


def faltan_columnas(cols_d, cols_w):
    """[(col_modelo, cuantas)] para que la plantilla alcance al export.

    Las plantillas de DBNeT traen un numero fijo de columnas 'Agregar columna
    opcional' y esperan que alguien las duplique a mano con su boton antes de
    llenar. Si Workiva trae mas miembros que espacios, los de mas se quedaban
    fuera sin remedio.

    El alineamiento va por las columnas ancla -- las que llevan un miembro de
    la taxonomia de verdad -- y no por posicion: entre dos anclas se cuenta
    cuantas opcionales hay a cada lado, y la diferencia es lo que falta. Asi
    las columnas nuevas caen en el tramo correcto aunque Workiva tenga otras
    diferencias de layout."""
    canon = _canon_anclas(cols_d, cols_w)
    td, tw = _tramos(cols_d, canon), _tramos(cols_w, canon)
    por_ancla_w = {}
    for ancla, opcs in tw:
        por_ancla_w.setdefault(ancla, []).append(opcs)
    faltan = []
    usados = collections.Counter()
    for ancla, opcs_d in td:
        disponibles = por_ancla_w.get(ancla)
        if not disponibles or usados[ancla] >= len(disponibles):
            continue
        opcs_w = disponibles[usados[ancla]]
        usados[ancla] += 1
        if len(opcs_w) > len(opcs_d) and opcs_d:
            faltan.append((opcs_d[-1], len(opcs_w) - len(opcs_d)))
    return faltan


# ------------------------------------------------------------------ proceso

def procesar_hoja(dest, hoja_d, wv, hoja_w, xml, reporte, archivo):
    """Escribe una hoja. Devuelve (xml, celdas_escritas)."""
    cd, cw = dest.celdas(hoja_d), wv.celdas(hoja_w)
    cols_d, tipo_d = columnas_de_datos(cd)
    cols_w, tipo_w = columnas_de_datos(cw)

    # Si Workiva trae mas miembros que espacios tiene la plantilla, se crean
    # las columnas que faltan antes de escribir nada. De derecha a izquierda,
    # para que insertar una no corra la posicion de las siguientes.
    if tipo_d == tipo_w == "dimensional":
        pendientes = faltan_columnas(cols_d, cols_w)
        for col_modelo, cuantas in sorted(pendientes, key=lambda p: -col_a_num(p[0])):
            xml = inserta_columnas(xml, col_modelo, cuantas)
            reporte.append([archivo, hoja_d, hoja_w, "", col_modelo, "", cuantas,
                            "COLUMNAS AGREGADAS (la plantilla traia menos que Workiva)"])
        if pendientes:
            dest.recarga(hoja_d, xml)
            cd = dest.celdas(hoja_d)
            cols_d, tipo_d = columnas_de_datos(cd)

    # Sin columnas de montos la hoja igual se procesa: puede ser un cuadro de
    # solo texto, donde el dato vive en la columna de la etiqueta.
    if tipo_d != tipo_w and cols_d and cols_w:
        reporte.append([archivo, hoja_d, hoja_w, "", "", "", "",
                        f"LAYOUT DISTINTO (dbnet={tipo_d}, workiva={tipo_w})"])
        cols_d = cols_w = {}

    inv_w = {}
    for c, k in cols_w.items():
        inv_w.setdefault(k, c)
    pares_col = {c: inv_w[k] for c, k in cols_d.items() if k in inv_w}

    # Las columnas que agrega el usuario se emparejan por posicion, no por
    # nombre: en la plantilla se llaman todas "Agregar columna opcional" y en
    # Workiva llevan el nombre que les pusieron ("prestamo 1", "prestamo 2"),
    # asi que por nombre no calzan nunca. De paso se copia ese nombre al
    # encabezado de la plantilla, que es lo que haria una persona al crear la
    # columna con el boton de DBNeT.
    fila_cod_d = fila_de_codigos(cd) if tipo_d == "dimensional" else None
    fila_cod_w = fila_de_codigos(cw) if tipo_w == "dimensional" else None
    if fila_cod_d and fila_cod_w:
        for col_d, col_w in empareja_opcionales(cols_d, cols_w):
            pares_col[col_d] = col_w
            etq_w = (cw.get((fila_cod_w - 1, col_w)) or ("", False, None))
            etq_d = (cd.get((fila_cod_d - 1, col_d)) or ("", False, None))
            if etq_w[0] and etq_w[0] != etq_d[0] and not etq_d[1]:
                xml, _ = escribe(xml, f"{col_d}{fila_cod_d - 1}", etq_w[0], etq_w[2])

    for c, k in cols_d.items():
        if c not in pares_col:
            reporte.append([archivo, hoja_d, hoja_w, "", c, "", "",
                            f"COLUMNA SIN ORIGEN: {k}"])

    filas_w = filas_indexadas(cw)
    idx_w = {(co, ma, n): f for f, co, ma, n in filas_w}
    filas_d = filas_indexadas(cd)

    # Respaldo para cuando la marca ACT/ANT no coincide entre los dos lados.
    # Pasa de verdad: en CLCP2016-ProvPagoDia el bloque del periodo anterior
    # viene marcado ANT en Workiva y ACT en la plantilla de DBNeT, y sin esto
    # los 17.871.957.000 de cuentas comerciales del periodo anterior se
    # entregaban en cero. Se calza por la posicion del concepto dentro de la
    # hoja (su n-esima aparicion, sin mirar la marca), nunca sobre una fila que
    # el calce estricto vaya a usar, y cada caso queda anotado en el reporte:
    # es un supuesto, y tiene que poder revisarse.
    pos_w = _por_posicion(filas_w)
    n_pos_d = {f: n for (_, n), f in _por_posicion(filas_d).items()}
    reservadas = {idx_w[k] for k in
                  ((co, ma, n) for _, co, ma, n in filas_d) if k in idx_w}

    # Ultimo respaldo: la misma linea con distinto codigo de concepto. En
    # IAS-1_310000 la fila de diferencias de cambio es cl-ci_DiferenciasCambio
    # en Workiva e ifrs-full_GainsLossesOnExchangeDifferences... en DBNeT, con
    # la etiqueta identica y los vecinos calzando. Quedaba vacia, y como las
    # filas 24 y 26 son formulas que la suman, el cuadro entregaba una ganancia
    # antes de impuestos equivocada por esos mismos 10.211.857: peor que un
    # dato ausente, porque se ve un numero y es incorrecto.
    etq_w = _por_etiqueta(cw, filas_w)
    etq_d = _por_etiqueta(cd, filas_d)
    etq_de_fila_d = {f: k for k, f in etq_d.items()}

    usadas_w = set()
    tomadas_w = set()
    escritas = cacheadas = 0

    for fila_d, concepto, marca, orden in filas_d:
        fila_w = idx_w.get((concepto, marca, orden))
        if fila_w is None:
            cand = pos_w.get((concepto, n_pos_d.get(fila_d)))
            if cand is not None and cand not in reservadas and cand not in tomadas_w:
                # Si las dos filas caen bajo el mismo titulo de periodo, o si
                # la hoja no usa titulos y el numero de fila coincide, no hay
                # forma de que la cifra se cruce de ano: el calce es seguro y
                # no tiene sentido mandarlo a revision humana.
                sec_d, sec_w = seccion_periodo(cd, fila_d), seccion_periodo(cw, cand)
                seguro = (sec_d == sec_w if sec_d or sec_w else fila_d == cand)
                if not seguro:
                    marca_w = next((ma for f, co, ma, _ in filas_w if f == cand), "")
                    reporte.append([archivo, hoja_d, hoja_w, concepto, f"fila {fila_d}",
                                    marca, orden,
                                    f"CALZADO POR POSICION (DBNeT lo pone en "
                                    f"'{sec_d or marca}' y Workiva en "
                                    f"'{sec_w or marca_w}'; revisar)"])
                fila_w = cand
        if fila_w is None:
            clave_etq = etq_de_fila_d.get(fila_d)
            cand = etq_w.get(clave_etq) if clave_etq else None
            if cand is not None and cand not in reservadas and cand not in tomadas_w:
                otro = next((co for f, co, _, _ in filas_w if f == cand), "")
                sec_d, sec_w = seccion_periodo(cd, fila_d), seccion_periodo(cw, cand)
                if (sec_d != sec_w) if (sec_d or sec_w) else (fila_d != cand):
                    reporte.append([archivo, hoja_d, hoja_w, concepto,
                                    f"fila {fila_d}", marca, orden,
                                    f"CALZADO POR ETIQUETA (Workiva usa "
                                    f"'{otro}'; revisar)"])
                fila_w = cand
        if fila_w is None:
            estado = ("CONCEPTO SIN ORIGEN" if not any(
                k[0] == concepto for k in idx_w) else "BLOQUE SIN ORIGEN")
            reporte.append([archivo, hoja_d, hoja_w, concepto, "", marca, orden, estado])
            continue
        usadas_w.add((concepto, marca, orden))
        tomadas_w.add(fila_w)

        # La columna F hace doble papel: es la etiqueta del concepto y, en los
        # cuadros de texto (110000, los "-Cuadros"), tambien la celda del dato.
        # Se escribe solo si la plantilla la tiene vacia en esa fila: si trae
        # texto es la etiqueta, y pisarla romperia la hoja.
        etiqueta_d = (cd.get((fila_d, COL_ETIQUETA)) or (None, False, None))
        if etiqueta_d[0] in (None, "") and not etiqueta_d[1]:
            val_f, _, tipo_f = cw.get((fila_w, COL_ETIQUETA), (None, False, None))
            if val_f not in (None, ""):
                ref_f = f"{COL_ETIQUETA}{fila_d}"
                val_f = recorta(val_f, tipo_f, ref_f, reporte, archivo, hoja_d, hoja_w)
                xml, cambio = escribe(xml, ref_f, val_f, tipo_f)
                if cambio:
                    escritas += 1

        for col_d, col_w in pares_col.items():
            val, _, tipo = cw.get((fila_w, col_w), (None, False, None))
            if val is None or val == "":
                continue
            destino = cd.get((fila_d, col_d), (None, False, None))
            if destino[1]:
                # formula: no se toca, pero su cache se pone al dia con el
                # valor de Workiva para que el CSV no salga con ceros
                try:
                    float(val)
                except (TypeError, ValueError):
                    continue
                xml, cambio = actualiza_cache(xml, f"{col_d}{fila_d}", val)
                if cambio:
                    cacheadas += 1
                continue
            ref = f"{col_d}{fila_d}"
            val = recorta(val, tipo, ref, reporte, archivo, hoja_d, hoja_w)
            xml, cambio = escribe(xml, ref, val, tipo)
            if cambio:
                escritas += 1

    for clave, fila in idx_w.items():
        if clave not in usadas_w and fila not in tomadas_w:
            reporte.append([archivo, hoja_d, hoja_w, clave[0], "", clave[1], clave[2],
                            "DATO DE WORKIVA SIN DESTINO"])
    if cacheadas:
        reporte.append([archivo, hoja_d, hoja_w, "", "", "", cacheadas,
                        "SUBTOTALES CON CACHE ACTUALIZADO"])
    return xml, escritas + cacheadas


def cmd_llenar(args):
    # Busca en subcarpetas: al descomprimir la entrega de DBNeT es normal
    # terminar con xls\xls\*.xlsm porque el .zip ya trae su propia carpeta.
    plantillas = sorted(p for p in Path(args.plantillas).rglob("*.xlsm")
                        if not p.name.startswith("~$"))
    if not plantillas:
        sys.exit(f"No hay .xlsm en {args.plantillas} ni en sus subcarpetas")
    hondas = {p.parent for p in plantillas if p.parent != Path(args.plantillas)}
    if hondas:
        print("  (encontrados en subcarpeta: "
              + ", ".join(sorted(str(h) for h in hondas)[:3]) + ")")
    wv = Libro(args.workiva)
    orden_wk = {h: i for i, h in enumerate(wv.hojas)}
    print(f"Plantillas: {len(plantillas)}   Workiva: {len(wv.hojas)} hojas\n")

    if args.mapa:
        pares = mapear_hojas(plantillas, wv, args.mapa)
        sobrantes, pistas = [], {}
    else:
        pares, sobrantes, pistas = mapear_hojas(plantillas, wv)

    por_archivo = collections.defaultdict(list)
    for ruta, hoja_d, hoja_w, metodo in pares:
        por_archivo[ruta].append((hoja_d, hoja_w, metodo))

    en_workiva = []
    reporte = [["archivo", "hoja_dbnet", "hoja_workiva", "concepto",
                "columna", "periodo", "bloque", "estado"]]
    salida = Path(args.salida)
    total_celdas = total_hojas = archivos_escritos = 0

    for ruta, hojas in por_archivo.items():
        dest = Libro(ruta)
        estilos = Estilos(dest)
        cambios, escritas_archivo = {}, 0
        for hoja_d, hoja_w, metodo in hojas:
            if not hoja_w:
                pista = pistas.get((ruta, hoja_d))
                if pista:
                    w, cob = pista
                    reporte.append([ruta.name, hoja_d, w, "", "", "", "",
                                    "CUADRO SIN LLENAR: se parece a la hoja "
                                    f"'{w}' de Workiva ({cob:.0%} de los "
                                    "conceptos), pero no lo suficiente"])
                else:
                    reporte.append([ruta.name, hoja_d, "", "", "", "", "",
                                    "NO APLICA (sin hoja en Workiva)"])
                continue
            # el indice de la hoja en el export es lo que usa el fusionador
            # para dejar el archivo final en el mismo orden que Workiva, y no
            # en el orden alfabetico de los archivos de DBNeT
            en_workiva.append(f"{ruta.name}|{hoja_d}|{orden_wk.get(hoja_w, 9999)}")
            xml = dest.xml(hoja_d)
            xml, n = procesar_hoja(dest, hoja_d, wv, hoja_w, xml, reporte, ruta.name)
            if n:
                cambios[dest.hojas[hoja_d]] = ajusta_bloques_texto(xml, estilos)
                escritas_archivo += n
                total_hojas += 1

        if cambios:
            cambios["xl/workbook.xml"] = recalculo(
                dest.z.read("xl/workbook.xml").decode("utf-8"))
            if estilos.cambio:
                cambios["xl/styles.xml"] = estilos.xml()
            estado = "escrito" if not args.dry_run else "(dry-run)"
            total_celdas += escritas_archivo
        else:
            # Sin datos que escribir igual va a la salida: la entrega a DBNeT
            # es la carpeta completa, y un cuadro que no aplica se manda vacio.
            estado = "copiado sin datos" if not args.dry_run else "(sin datos)"
        quitar = ()
        if dest.layout_cambiado and "xl/calcChain.xml" in dest.z.namelist():
            quitar = sin_calcchain(dest.z, cambios)
        if not args.dry_run:
            reescribe_zip(ruta, salida / ruta.name, cambios, quitar)
            archivos_escritos += 1
        print(f"  {ruta.name[:48]:50} {escritas_archivo:6} celdas  {estado}")

    for w in sobrantes:
        reporte.append(["", "", w, "", "", "", "", "HOJA DE WORKIVA SIN DESTINO"])

    # En --dry-run no se escribe ningun archivo, y decir "de 0 archivos"
    # parecia que algo habia fallado.
    if args.dry_run:
        print(f"\nTotal: {total_celdas} celdas en {total_hojas} hojas "
              "(simulacion: no se escribio nada)")
    else:
        print(f"\nTotal: {total_celdas} celdas en {total_hojas} hojas "
              f"de {archivos_escritos} archivos")
    if not args.dry_run and en_workiva:
        # lo lee fusionar_cuadros.py --solo-workiva: que cuadros existen en el
        # export, en vez de adivinarlo mirando las celdas
        (salida / "_hojas_de_workiva.txt").write_text(
            "\n".join(en_workiva), encoding="utf-8")

    ruta_rep = Path(args.reporte)
    # En --dry-run no se escribe ningun .xlsm, asi que la carpeta de salida
    # puede no existir todavia; el reporte vive dentro y hay que crearla.
    ruta_rep.parent.mkdir(parents=True, exist_ok=True)
    with open(ruta_rep, "w", newline="", encoding="utf-8-sig") as fh:
        csv.writer(fh, delimiter=";").writerows(reporte)
    # Agrupado por el tipo: hay una variante de texto por cada columna, y sin
    # agrupar se imprimen 219 lineas de las que 211 dicen lo mismo.
    incid = collections.Counter(str(r[7]).split(":")[0] for r in reporte[1:])
    print(f"\nReporte: {ruta_rep}  ({len(reporte)-1} incidencias)")
    for estado, n in incid.most_common():
        print(f"   {n:5}  {estado}")

    ruta_rev = escribe_revisar(
        reporte, Path(args.revisar) if args.revisar
        else ruta_rep.with_name("REVISAR.xlsx"))
    print()
    if ruta_rev:
        n = sum(1 for r in reporte[1:]
                if any(str(r[7]).startswith(t) for t, _, _ in REVISABLES))
        print("  ----------------------------------------------------------")
        print(f"  OJO: {n} avisos necesitan que los mires.")
        print(f"     {ruta_rev}")
        print("  ----------------------------------------------------------")
    else:
        print("  No quedo nada pendiente de revisar.")

    if not args.dry_run and archivos_escritos:
        print()
        verificar(Path(args.plantillas), salida)


# ------------------------------------------------------------ hoja a revisar

# Que mirar en cada caso. El reporte completo tiene cientos de lineas y la
# mayoria son informativas; esto es solo lo que pide ojo humano antes de
# entregar a la CMF.
REVISABLES = [
    ("CUADRO SIN LLENAR",
     "Este cuadro quedo vacio, y en Workiva sobro una hoja que se le parece "
     "pero no lo bastante como para darla por buena. Lo mas probable es que "
     "DBNeT haya cambiado el cuadro en esta version de la plantilla.",
     "Abri esta hoja en el archivo llenado y comparala con la hoja {hojas} "
     "de Workiva. Si son el mismo cuadro, avisame para ajustar el programa; "
     "si no lo son, no hay nada que hacer."),
    ("TEXTO RECORTADO",
     "El texto es mas largo de lo que cabe en una celda de Excel (el tope son "
     "32.767 caracteres), asi que quedo cortado a media palabra.",
     "Anda a esa celda y mira como termina el parrafo. Si no te sirve asi, "
     "hay que acortar el texto en Workiva unos 200 caracteres."),
    ("CALZADO POR POSICION",
     "Workiva y la plantilla de DBNeT rotulan distinto si una cifra es del "
     "periodo actual o del anterior, asi que el programa la ubico por el lugar "
     "que ocupa en el cuadro.",
     "Mira que las cifras del periodo anterior esten en las filas del periodo "
     "anterior, y no mezcladas con las del actual."),
    ("CALZADO POR ETIQUETA",
     "El mismo renglon del cuadro tiene distinto codigo interno en Workiva y "
     "en DBNeT. El programa los junto porque el nombre del renglon y su lugar "
     "en el cuadro si coinciden.",
     "Mira que sea efectivamente el mismo renglon en los dos lados."),
]


def _rangos(numeros):
    """'22 a 29' en vez de '22, 23, 24, 25, 26, 27, 28, 29'."""
    ns = sorted(set(numeros))
    if not ns:
        return ""
    tramos, ini, prev = [], ns[0], ns[0]
    for n in ns[1:] + [None]:
        if n != prev + 1:
            tramos.append(str(ini) if ini == prev else f"{ini} a {prev}")
            ini = n
        prev = n
    return ", ".join(tramos)


def escribe_revisar(reporte, ruta):
    """Deja un libro con las hojas del archivo fusionado que piden revision.

    Devuelve la ruta escrita, o None si no hay nada que revisar."""
    filas = []
    for tipo, porque, que_mirar in REVISABLES:
        casos = [r for r in reporte[1:] if str(r[7]).startswith(tipo)]
        for (hoja, _), grupo in _agrupa(casos):
            refs = [str(r[4]) for r in grupo if r[4]]
            nums = [int(x.split()[1]) for x in refs if x.startswith("fila ")]
            celdas = sorted({x for x in refs if not x.startswith("fila ")})
            if nums:
                donde = ("fila " if len(set(nums)) == 1 else "filas ") + _rangos(nums)
            elif celdas:
                donde = ("celdas " if len(celdas) > 1 else "celda ") + ", ".join(celdas)
            else:
                donde = "toda la hoja"
            otras = sorted({str(r[2]) for r in grupo if r[2]})
            texto = (que_mirar.format(hojas="'" + "', '".join(otras) + "'")
                     if "{hojas}" in que_mirar and otras else que_mirar)
            filas.append([hoja, donde, porque, texto, len(grupo)])
    if not filas:
        return None

    cab = ["Hoja del archivo llenado", "Donde mirar", "Que paso",
           "Que tienes que mirar", "Casos"]
    ruta.parent.mkdir(parents=True, exist_ok=True)
    try:
        from openpyxl import Workbook
        from openpyxl.styles import Alignment, Font, PatternFill
    except ImportError:
        ruta = ruta.with_suffix(".csv")
        with open(ruta, "w", newline="", encoding="utf-8-sig") as fh:
            w = csv.writer(fh, delimiter=";")
            w.writerow(cab)
            w.writerows(filas)
        return ruta

    wb = Workbook()
    ws = wb.active
    ws.title = "Revisar"
    ws.append(cab)
    for c in ws[1]:
        c.font = Font(bold=True, color="FFFFFF")
        c.fill = PatternFill("solid", fgColor="4472C4")
    for f in filas:
        ws.append(f)
    for col, ancho in zip("ABCDE", (26, 18, 62, 62, 8)):
        ws.column_dimensions[col].width = ancho
    for fila in ws.iter_rows(min_row=2):
        for c in fila:
            c.alignment = Alignment(vertical="top", wrap_text=True)
    ws.freeze_panes = "A2"
    wb.save(ruta)
    return ruta


def _agrupa(casos):
    """[( (hoja, archivo), [filas] )] conservando el orden de aparicion."""
    out = {}
    for r in casos:
        out.setdefault((r[1], r[0]), []).append(r)
    return list(out.items())


# ---------------------------------------------------------------- integridad

def botones(z):
    return sum(len(re.findall(r'macro="\[0\]![^"]+"', z.read(n).decode("utf-8")))
               for n in z.namelist()
               if n.startswith("xl/drawings/drawing") and n.endswith(".xml"))


def verificar(dir_orig, dir_nuevo):
    print("Verificacion de integridad:")
    fallos = 0
    # el original puede estar en una subcarpeta (xls\xls\ tras descomprimir)
    originales = {p.name: p for p in Path(dir_orig).rglob("*.xlsm")
                  if not p.name.startswith("~$")}
    for nuevo in sorted(Path(dir_nuevo).glob("*.xlsm")):
        orig = originales.get(nuevo.name)
        if orig is None:
            print(f"   {nuevo.name}: sin original"); fallos += 1; continue
        with zipfile.ZipFile(orig) as a, zipfile.ZipFile(nuevo) as b:
            na, nb = set(a.namelist()), set(b.namelist())
            problemas = []
            # calcChain se quita a proposito al insertar columnas: es la cache
            # del orden de calculo y queda apuntando a las celdas viejas.
            if na - nb - {"xl/calcChain.xml"} or nb - na:
                problemas.append(f"partes {len(na)}->{len(nb)}")
            if "xl/vbaProject.bin" in na & nb:
                if hashlib.md5(a.read("xl/vbaProject.bin")).hexdigest() != \
                   hashlib.md5(b.read("xl/vbaProject.bin")).hexdigest():
                    problemas.append("VBA MODIFICADO")
            ba, bb = botones(a), botones(b)
            if ba != bb:
                problemas.append(f"botones {ba}->{bb}")
            if problemas:
                print(f"   FALLO {nuevo.name}: {', '.join(problemas)}"); fallos += 1
    n = len(list(Path(dir_nuevo).glob('*.xlsm')))
    print(f"   {n - fallos}/{n} archivos con VBA y botones intactos")
    return fallos == 0


def cmd_verificar(args):
    sys.exit(0 if verificar(Path(args.verificar[0]), Path(args.verificar[1])) else 1)


def main():
    p = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--plantillas", help="carpeta con los .xlsm de DBNeT")
    p.add_argument("--workiva", help="export .xlsx de Workiva")
    p.add_argument("--salida", default="./salida")
    p.add_argument("--mapa", help="mapa_hojas.csv para fijar el calce de hojas")
    p.add_argument("--reporte", default="reporte_llenado.csv")
    # Van separados porque no son para lo mismo: REVISAR.xlsx es lo que hay
    # que abrir antes de entregar, y el reporte es material de diagnostico que
    # conviene dejar fuera de la vista.
    p.add_argument("--revisar", default=None,
                   help="donde dejar REVISAR.xlsx (por omision, junto al reporte)")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--verificar", nargs=2, metavar=("ORIG", "NUEVO"))
    args = p.parse_args()
    if args.verificar:
        cmd_verificar(args)
    elif args.plantillas and args.workiva:
        cmd_llenar(args)
    else:
        p.error("se requieren --plantillas y --workiva (o --verificar ORIG NUEVO)")


if __name__ == "__main__":
    main()
