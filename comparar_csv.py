#!/usr/bin/env python3
"""
Compara dos carpetas de CSV y dice si son equivalentes.

Para que sirve
--------------
El archivo fusionado lleva una version corregida de la macro de DBNeT: la
original calculaba la carpeta destino cortandole tres caracteres a la ruta del
libro, lo que en OneDrive no da ninguna carpeta valida. Lo que NO se cambio es
la instruccion que genera el archivo:

    ActiveWorkbook.SaveAs Filename:=..., FileFormat:=xlCSVWindows,
                          CreateBackup:=False, Local:=True

que es la que define separador, decimales y codificacion. Aun asi, eso es un
argumento; esto es una comprobacion. Antes de mandarle nada a DBNeT conviene
verificar contra la salida de la macro original, que los 41 archivos de
salida\\ conservan intacta.

Como conseguir los dos lados
----------------------------
  ORIGINAL  copia un .xlsm de salida\\ a una carpeta llamada exactamente
            "xls" (p.ej. C:\\Temp\\xls\\), crea al lado C:\\Temp\\csv\\, abre
            el archivo y aprieta su boton "Crear CSV". Esos CSV los genera la
            macro de DBNeT sin tocar, con tus datos reales.
  NUEVO     abre el .xlsm fusionado, aprieta su boton y elige una carpeta.

Uso:
    python comparar_csv.py --original C:\\Temp\\csv --nuevo C:\\Temp\\csv_nuevo
    python comparar_csv.py --original ... --nuevo ... --detalle
"""

import argparse
import sys
from pathlib import Path

SEPARADORES = {";": "punto y coma", ",": "coma", "\t": "tabulador", "|": "barra"}


def perfil(datos):
    """Rasgos de formato de un CSV, mirando los bytes crudos."""
    fin = ("CRLF" if b"\r\n" in datos else
           "LF" if b"\n" in datos else
           "CR" if b"\r" in datos else "sin saltos")
    bom = datos.startswith(b"\xef\xbb\xbf")
    for cod in ("cp1252", "utf-8"):
        try:
            texto = datos.decode(cod)
            break
        except UnicodeDecodeError:
            continue
    else:
        texto, cod = datos.decode("latin-1"), "latin-1(?)"
    primera = texto.split("\n", 1)[0]
    sep = max(SEPARADORES, key=lambda s: primera.count(s))
    if primera.count(sep) == 0:
        sep = ";"
    return {"fin de linea": fin, "codificacion": cod, "BOM": "si" if bom else "no",
            "separador": SEPARADORES.get(sep, repr(sep)),
            "lineas": texto.count("\n") + (0 if texto.endswith("\n") else 1)}


def primera_diferencia(a, b):
    """(n_linea, linea_a, linea_b) de la primera linea que no coincide."""
    la = a.decode("cp1252", "replace").splitlines()
    lb = b.decode("cp1252", "replace").splitlines()
    for i, (x, y) in enumerate(zip(la, lb), 1):
        if x != y:
            return i, x, y
    if len(la) != len(lb):
        i = min(len(la), len(lb)) + 1
        return i, (la[i - 1] if i <= len(la) else "(no existe)"), \
                  (lb[i - 1] if i <= len(lb) else "(no existe)")
    return None


def main():
    p = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--original", required=True,
                   help="carpeta con los CSV de la macro de DBNeT sin tocar")
    p.add_argument("--nuevo", required=True,
                   help="carpeta con los CSV del archivo fusionado")
    p.add_argument("--detalle", action="store_true",
                   help="mostrar la primera linea distinta de cada archivo")
    args = p.parse_args()

    dir_a, dir_b = Path(args.original), Path(args.nuevo)
    for d in (dir_a, dir_b):
        if not d.is_dir():
            sys.exit(f"No existe la carpeta {d}")

    a = {f.name.lower(): f for f in dir_a.glob("*.csv")}
    b = {f.name.lower(): f for f in dir_b.glob("*.csv")}
    comunes = sorted(set(a) & set(b))
    if not comunes:
        sys.exit("Ningun CSV con el mismo nombre en las dos carpetas.\n"
                 f"  {dir_a}: {len(a)} archivos\n  {dir_b}: {len(b)} archivos")

    iguales, distintos, formato = [], [], []
    for nombre in comunes:
        da, db = a[nombre].read_bytes(), b[nombre].read_bytes()
        if da == db:
            iguales.append(nombre)
            continue
        pa, pb = perfil(da), perfil(db)
        difs = [k for k in pa if pa[k] != pb[k] and k != "lineas"]
        (formato if difs else distintos).append((nombre, pa, pb, difs))

    print(f"\n  Archivos comparados : {len(comunes)}")
    print(f"  Identicos           : {len(iguales)}")
    print(f"  Difieren en formato : {len(formato)}")
    print(f"  Difieren en datos   : {len(distintos)}")

    if formato:
        print("\n  " + "!" * 56)
        print("  FORMATO DISTINTO -- esto es lo que puede rechazar DBNeT")
        print("  " + "!" * 56)
        for nombre, pa, pb, difs in formato[:10]:
            print(f"\n    {nombre}")
            for k in difs:
                print(f"       {k:16} original={pa[k]!r}  nuevo={pb[k]!r}")

    if distintos:
        print("\n  Mismo formato, pero el contenido no coincide:")
        for nombre, pa, pb, _ in distintos[:10]:
            print(f"    {nombre}  ({pa['lineas']} vs {pb['lineas']} lineas)")
            if args.detalle:
                d = primera_diferencia(a[nombre].read_bytes(), b[nombre].read_bytes())
                if d:
                    n, x, y = d
                    print(f"       linea {n}")
                    print(f"         original: {x[:110]}")
                    print(f"         nuevo   : {y[:110]}")
        if not args.detalle:
            print("    (corre con --detalle para ver la primera linea distinta)")

    solo_a, solo_b = sorted(set(a) - set(b)), sorted(set(b) - set(a))
    if solo_a:
        print(f"\n  Solo en el original ({len(solo_a)}): {', '.join(solo_a[:6])}")
    if solo_b:
        print(f"  Solo en el nuevo ({len(solo_b)}): {', '.join(solo_b[:6])}")

    if not formato and not distintos:
        print("\n  Los CSV son identicos byte a byte.\n")
        return 0
    print()
    return 1


if __name__ == "__main__":
    sys.exit(main())
