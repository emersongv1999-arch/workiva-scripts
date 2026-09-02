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
        rels = dict(re.findall(r'Id="(rId\d+)"[^>]*Target="([^"]*)"',
                               self.z.read("xl/_rels/workbook.xml.rels").decode("utf-8")))
        wb = self.z.read("xl/workbook.xml").decode("utf-8")
        self.hojas = {}
        for tag in re.findall(r"<sheet [^>]*?>", wb):
            nombre = desescapa(re.search(r'name="([^"]*)"', tag).group(1))
            rid = re.search(r'r:id="(rId\d+)"', tag).group(1)
            destino = rels[rid].lstrip("/")
            self.hojas[nombre] = destino if destino.startswith("xl/") else "xl/" + destino
        self._cache = {}

    def xml(self, hoja):
        return self.z.read(self.hojas[hoja]).decode("utf-8")

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

def conceptos_set(cel):
    return {v.split("#")[-1].strip()
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
        concepto = v.split("#")[-1].strip()
        marca = (cel.get((fila, COL_PERIODO)) or ("",))[0] or ""
        marca = marca.strip().upper()
        marca = marca if marca in ("ACT", "ANT") else ""
        vistos[(concepto, marca)] += 1
        out.append((fila, concepto, marca, vistos[(concepto, marca)]))
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
                claves[c] = v.split("#")[-1].strip()
            else:
                # miembro agregado por el usuario: su ID lo genera una formula
                # que en el export de Workiva llega rota (#NAME?), asi que la
                # identidad la da la etiqueta de la fila de arriba.
                etq = (cel.get((fila_cod - 1, c)) or ("",))[0] or ""
                etq = normaliza(etq)
                if etq:
                    claves[c] = "lbl:" + etq
        if claves:
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
    return ([(ru, h, *par.get((ru, h), (None, "SIN CONTRAPARTE"))) for ru, h, _ in destinos],
            sobrantes)


# ------------------------------------------------------------- escritura XML

def formatea(valor, tipo):
    if tipo in ("s", "inlineStr", "str"):
        return f'<is><t xml:space="preserve">{escapa(valor)}</t></is>', ' t="inlineStr"'
    return f"<v>{valor}</v>", ""


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

    El patron prueba primero la celda autocerrada, igual que CELDA_RE: con
    '<c r="X"[^>]*>' una celda como <c r="D5" s="3"/> tambien hacia match
    -- [^>]* se come el '/' -- y entonces el (.*?)(</c>) seguia de largo
    hasta el cierre de una celda POSTERIOR. El <v> que se reescribia era
    el de esa otra celda: el valor terminaba en la celda equivocada, sin
    error y sin dejar rastro."""
    pat = re.compile(r'<c r="%s"([^>]*?)(?:/>|>(.*?)</c>)' % re.escape(ref), re.S)
    m = pat.search(xml)
    if not m or m.group(2) is None or "<f" not in m.group(2):
        return xml, False           # sin cuerpo no hay formula que refrescar
    cuerpo = m.group(2)
    nuevo = (re.sub(r"<v>.*?</v>", "<v>%s</v>" % valor, cuerpo, count=1, flags=re.S)
             if "<v>" in cuerpo else cuerpo + "<v>%s</v>" % valor)
    if nuevo == cuerpo:
        return xml, False
    celda = '<c r="%s"%s>%s</c>' % (ref, m.group(1), nuevo)
    return xml[:m.start()] + celda + xml[m.end():], True


def recalculo(wb_xml):
    if "fullCalcOnLoad" in wb_xml:
        return wb_xml
    if "<calcPr" in wb_xml:
        return re.sub(r"<calcPr([^>]*?)/>", r'<calcPr\1 fullCalcOnLoad="1"/>', wb_xml, count=1)
    return wb_xml.replace("</workbook>", '<calcPr fullCalcOnLoad="1"/></workbook>')


def reescribe_zip(origen, destino, cambios):
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
            ET.fromstring(texto)
        except ET.ParseError as e:
            raise ValueError(
                f"{destino.name}: el XML de {parte} quedo invalido ({e}). "
                "El archivo NO se escribio.") from None

    destino.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(origen) as zin, \
         zipfile.ZipFile(destino, "w", zipfile.ZIP_DEFLATED) as zout:
        for info in zin.infolist():
            datos = cambios.get(info.filename)
            datos = datos.encode("utf-8") if datos is not None else zin.read(info.filename)
            nuevo = zipfile.ZipInfo(info.filename, date_time=info.date_time)
            nuevo.compress_type = info.compress_type
            nuevo.external_attr = info.external_attr
            nuevo.internal_attr = info.internal_attr
            nuevo.create_system = info.create_system
            zout.writestr(nuevo, datos)


# ------------------------------------------------------------------ proceso

def procesar_hoja(dest, hoja_d, wv, hoja_w, xml, reporte, archivo):
    """Escribe una hoja. Devuelve (xml, celdas_escritas)."""
    cd, cw = dest.celdas(hoja_d), wv.celdas(hoja_w)
    cols_d, tipo_d = columnas_de_datos(cd)
    cols_w, tipo_w = columnas_de_datos(cw)

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
    for c, k in cols_d.items():
        if k not in inv_w:
            reporte.append([archivo, hoja_d, hoja_w, "", c, "", "",
                            f"COLUMNA SIN ORIGEN: {k}"])

    idx_w = {(co, ma, n): f for f, co, ma, n in filas_indexadas(cw)}
    filas_d = filas_indexadas(cd)
    usadas_w = set()
    escritas = cacheadas = 0

    for fila_d, concepto, marca, orden in filas_d:
        fila_w = idx_w.get((concepto, marca, orden))
        if fila_w is None:
            estado = ("CONCEPTO SIN ORIGEN" if not any(
                k[0] == concepto for k in idx_w) else "BLOQUE SIN ORIGEN")
            reporte.append([archivo, hoja_d, hoja_w, concepto, "", marca, orden, estado])
            continue
        usadas_w.add((concepto, marca, orden))

        # La columna F hace doble papel: es la etiqueta del concepto y, en los
        # cuadros de texto (110000, los "-Cuadros"), tambien la celda del dato.
        # Se escribe solo si la plantilla la tiene vacia en esa fila: si trae
        # texto es la etiqueta, y pisarla romperia la hoja.
        etiqueta_d = (cd.get((fila_d, COL_ETIQUETA)) or (None, False, None))
        if etiqueta_d[0] in (None, "") and not etiqueta_d[1]:
            val_f, _, tipo_f = cw.get((fila_w, COL_ETIQUETA), (None, False, None))
            if val_f not in (None, ""):
                xml, cambio = escribe(xml, f"{COL_ETIQUETA}{fila_d}", val_f, tipo_f)
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
            xml, cambio = escribe(xml, f"{col_d}{fila_d}", val, tipo)
            if cambio:
                escritas += 1

    for clave in idx_w:
        if clave not in usadas_w:
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
    print(f"Plantillas: {len(plantillas)}   Workiva: {len(wv.hojas)} hojas\n")

    if args.mapa:
        pares = mapear_hojas(plantillas, wv, args.mapa)
        sobrantes = []
    else:
        pares, sobrantes = mapear_hojas(plantillas, wv)

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
        cambios, escritas_archivo = {}, 0
        for hoja_d, hoja_w, metodo in hojas:
            if not hoja_w:
                reporte.append([ruta.name, hoja_d, "", "", "", "", "",
                                "NO APLICA (sin hoja en Workiva)"])
                continue
            en_workiva.append(f"{ruta.name}|{hoja_d}")
            xml = dest.xml(hoja_d)
            xml, n = procesar_hoja(dest, hoja_d, wv, hoja_w, xml, reporte, ruta.name)
            if n:
                cambios[dest.hojas[hoja_d]] = xml
                escritas_archivo += n
                total_hojas += 1

        if cambios:
            cambios["xl/workbook.xml"] = recalculo(
                dest.z.read("xl/workbook.xml").decode("utf-8"))
            estado = "escrito" if not args.dry_run else "(dry-run)"
            total_celdas += escritas_archivo
        else:
            # Sin datos que escribir igual va a la salida: la entrega a DBNeT
            # es la carpeta completa, y un cuadro que no aplica se manda vacio.
            estado = "copiado sin datos" if not args.dry_run else "(sin datos)"
        if not args.dry_run:
            reescribe_zip(ruta, salida / ruta.name, cambios)
            archivos_escritos += 1
        print(f"  {ruta.name[:48]:50} {escritas_archivo:6} celdas  {estado}")

    for w in sobrantes:
        reporte.append(["", "", w, "", "", "", "", "HOJA DE WORKIVA SIN DESTINO"])

    print(f"\nTotal: {total_celdas} celdas en {total_hojas} hojas "
          f"de {archivos_escritos} archivos")
    if not args.dry_run and en_workiva:
        # lo lee fusionar_cuadros.py --solo-workiva: que cuadros existen en el
        # export, en vez de adivinarlo mirando las celdas
        (salida / "_hojas_de_workiva.txt").write_text(
            "\n".join(en_workiva), encoding="utf-8")

    ruta_rep = Path(args.reporte)
    with open(ruta_rep, "w", newline="", encoding="utf-8-sig") as fh:
        csv.writer(fh, delimiter=";").writerows(reporte)
    incid = collections.Counter(r[7] for r in reporte[1:])
    print(f"\nReporte: {ruta_rep}  ({len(reporte)-1} incidencias)")
    for estado, n in incid.most_common():
        print(f"   {n:5}  {estado}")

    if not args.dry_run and archivos_escritos:
        print()
        verificar(Path(args.plantillas), salida)


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
            if na != nb:
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
