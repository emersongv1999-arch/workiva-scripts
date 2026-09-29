#!/usr/bin/env python3
"""XBRL DBNeT: llena las plantillas de DBNeT directo desde Workiva.

Se elige empresa y periodo; la aplicacion descarga la planilla
"E___ XBRL MM-AAAA" desde Workiva, simula, llena los .xlsm de DBNeT de esa
empresa en su lugar y arma el archivo unico con los botones funcionando.

Cada empresa es una carpeta junto al .exe, con sus plantillas en xls\\:

    XBRL_DBNeT.exe
    E211\\xls\\   las plantillas .xlsm de DBNeT de E211
    E205\\xls\\   ...

Para sumar una empresa basta con crear su carpeta y copiar ahi sus
plantillas; en Workiva aparece sola en cuanto existe su planilla XBRL.

El llenado y la fusion corren como procesos aparte -- el mismo .exe llamado
con --tarea -- y su salida se lee linea a linea: la ventana sigue
respondiendo, y si Excel se cae armando el archivo unico no se lleva la
ventana con el.
"""

import json
import os
import queue
import re
import subprocess
import sys
import tempfile
import threading
import time
import traceback
from pathlib import Path

RESPALDO = "_original_dbnet"


def carpeta_base():
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


# ════════════════════════════════════════════════════════ tareas (hijo) ══
def corre_tarea(nombre, args):
    """El .exe llamado con --tarea: corre el llenado o la fusion y termina."""
    salida_alt = None
    if sys.stdout is None:
        # Un .exe sin consola a veces arranca sin salida estandar aunque el
        # padre le pase una tuberia; entonces se escribe a un archivo que el
        # padre lee al terminar.
        salida_alt = open(os.environ.get("XBRL_SALIDA", os.devnull), "w",
                          encoding="utf-8", buffering=1)
        sys.stdout = sys.stderr = salida_alt
    else:
        for flujo in (sys.stdout, sys.stderr):
            try:
                flujo.reconfigure(encoding="utf-8", errors="replace",
                                  line_buffering=True)
            except (AttributeError, ValueError):
                pass

    if nombre == "llenar":
        import llenar_dbnet_desde_workiva as modulo
    elif nombre == "fusionar":
        import fusionar_cuadros as modulo
    else:
        print(f"Tarea desconocida: {nombre}")
        return 2

    sys.argv = [nombre, *args]
    try:
        modulo.main()
        codigo = 0
    except SystemExit as e:
        if e.code is None or isinstance(e.code, int):
            codigo = e.code or 0
        else:
            print(e.code)
            codigo = 1
    except Exception:                                    # noqa: BLE001
        traceback.print_exc()
        codigo = 1
    sys.stdout.flush()
    if salida_alt:
        salida_alt.close()
    return codigo


# ═══════════════════════════════════════════════════════════ ventana ══
if __name__ == "__main__" and len(sys.argv) > 2 and sys.argv[1] == "--tarea":
    sys.exit(corre_tarea(sys.argv[2], sys.argv[3:]))

import tkinter as tk                                     # noqa: E402
from tkinter import messagebox, ttk                      # noqa: E402

from xbrl_workiva import ErrorWorkiva, Planilla, Workiva  # noqa: E402

BASE = carpeta_base()
TEMPORAL = Path(tempfile.gettempdir()) / "XBRL_llenado"
CACHE = Path(os.environ.get("LOCALAPPDATA") or tempfile.gettempdir()) \
    / "XBRL_DBNeT" / "planillas.json"
SIN_CONSOLA = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0

AZUL, AZUL_OSC, FONDO, BLANCO = "#0B5394", "#083D6E", "#F4F6F8", "#FFFFFF"
VERDE, ROJO, GRIS, TENUE = "#1E7B34", "#B3261E", "#5A5A5A", "#8A94A0"
FUENTE = "Segoe UI"

# "  IAS12-Cuadros(835110)_2025.xlsm    202 celdas  (dry-run)", una por
# plantilla. El nombre va en un campo de 50 de ancho: eso la distingue del
# "OJO: N avisos", y aguanta los nombres largos a los que el script les come
# la extension.
AVANCE = re.compile(r"^\s{2}.{50}\s*\d+\s+celdas\b")
N_PLANTILLAS = re.compile(r"^Plantillas:\s*(\d+)")
TOTAL = re.compile(r"^Total:\s*([\d.,]+)\s+celdas\s+en\s+(\d+)\s+hojas")
AVISOS = re.compile(r"OJO:\s*(\d+)\s+avisos")

PASOS = ("Descargar de Workiva", "Simular", "Llenar las plantillas",
         "Armar el archivo único")


def plantillas_de(carpeta):
    xls = carpeta / "xls"
    if not xls.is_dir():
        return []
    return [p for p in xls.rglob("*.xlsm")
            if RESPALDO not in p.parts and not p.name.startswith("~$")]


def empresas_locales():
    if not BASE.is_dir():
        return []
    return sorted(d.name.upper() for d in BASE.iterdir()
                  if d.is_dir() and re.fullmatch(r"E\d+", d.name, re.IGNORECASE))


def miles(n):
    return f"{n:,}".replace(",", ".")


def abre(ruta):
    if os.name == "nt":
        os.startfile(ruta)                               # noqa: S606
    else:
        subprocess.Popen(["xdg-open", str(ruta)])


class Aplicacion(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("XBRL DBNeT")
        self.configure(bg=FONDO)
        # Los notebooks de CGE van con la pantalla al 125-150%: el tamano se
        # escala con eso y se limita a la pantalla, o la ventana no cabe.
        escala = max(1.0, self.winfo_fpixels("1i") / 96)
        ancho = min(int(1000 * escala), int(self.winfo_screenwidth() * 0.95))
        alto = min(int(700 * escala), int(self.winfo_screenheight() * 0.88))
        self.geometry(f"{ancho}x{alto}")
        self.minsize(min(ancho, int(820 * escala)), min(alto, int(560 * escala)))

        self.empresa = tk.StringVar()
        self.periodo = tk.StringVar()
        self.info_workiva = tk.StringVar()
        self.info_plantillas = tk.StringVar()
        self.estado = tk.StringVar()
        self.planillas = self._lee_cache()
        self.cola = queue.Queue()
        self.corriendo = False
        self.buscando = False
        self.resultado = None
        self.hechos = self.total = self.paso = 0
        self.confirmacion = queue.Queue()

        self._estilos()
        self._construye()
        self._refresca_empresas()
        self._busca_planillas()
        self.after(80, self._drena)

    # ------------------------------------------------------------ aspecto
    def _estilos(self):
        s = ttk.Style(self)
        try:
            s.theme_use("vista" if os.name == "nt" else "clam")
        except tk.TclError:
            pass
        s.configure("TCombobox", padding=5)
        s.configure("Treeview", rowheight=26, font=(FUENTE, 9))
        s.configure("Treeview.Heading", font=(FUENTE, 9, "bold"))
        s.configure("TNotebook.Tab", padding=(14, 5), font=(FUENTE, 9))
        s.configure("Horizontal.TProgressbar", thickness=8)

    def _construye(self):
        cab = tk.Frame(self, bg=AZUL, padx=24, pady=16)
        cab.pack(fill="x")
        tk.Label(cab, text="XBRL DBNeT", bg=AZUL, fg=BLANCO,
                 font=(FUENTE, 18, "bold")).pack(anchor="w")
        tk.Label(cab, text="Llena las plantillas de DBNeT directo desde Workiva",
                 bg=AZUL, fg="#CFE0F0", font=(FUENTE, 10)).pack(anchor="w")

        cuerpo = tk.Frame(self, bg=FONDO, padx=24, pady=18)
        cuerpo.pack(fill="both", expand=True)
        cuerpo.columnconfigure(0, weight=1)
        cuerpo.rowconfigure(3, weight=1)

        # ---- 1. que llenar
        tarjeta = self._tarjeta(cuerpo, 0)
        fila = tk.Frame(tarjeta, bg=BLANCO)
        fila.pack(fill="x")
        self._etiqueta(fila, "Empresa").pack(side="left")
        self.c_empresa = ttk.Combobox(fila, textvariable=self.empresa, width=10,
                                      state="readonly", font=(FUENTE, 11))
        self.c_empresa.pack(side="left", padx=(8, 28))
        self.c_empresa.bind("<<ComboboxSelected>>", lambda e: self._cambia_eleccion())
        self._etiqueta(fila, "Período").pack(side="left")
        self.c_periodo = ttk.Combobox(fila, textvariable=self.periodo, width=10,
                                      state="readonly", font=(FUENTE, 11))
        self.c_periodo.pack(side="left", padx=(8, 28))
        self.c_periodo.bind("<<ComboboxSelected>>", lambda e: self._cambia_eleccion())
        self.b_buscar = tk.Button(fila, text="↻  Buscar en Workiva",
                                  command=self._busca_planillas, bg=BLANCO,
                                  fg=AZUL, relief="flat", bd=0, cursor="hand2",
                                  font=(FUENTE, 9, "underline"),
                                  activebackground=BLANCO)
        self.b_buscar.pack(side="left")

        self.l_workiva = tk.Label(tarjeta, textvariable=self.info_workiva,
                                  bg=BLANCO, fg=GRIS, font=(FUENTE, 9), anchor="w")
        self.l_workiva.pack(fill="x", pady=(12, 0))
        fila_pl = tk.Frame(tarjeta, bg=BLANCO)
        fila_pl.pack(fill="x", pady=(2, 0))
        self.l_plantillas = tk.Label(fila_pl, textvariable=self.info_plantillas,
                                     bg=BLANCO, fg=GRIS, font=(FUENTE, 9), anchor="w")
        self.l_plantillas.pack(side="left")
        self.b_carpeta = tk.Button(fila_pl, text="Abrir carpeta",
                                   command=self._abre_carpeta_empresa, bg=BLANCO,
                                   fg=AZUL, relief="flat", bd=0, cursor="hand2",
                                   font=(FUENTE, 9, "underline"),
                                   activebackground=BLANCO)
        self.b_carpeta.pack(side="left", padx=8)

        # ---- 2. llenar y avance
        tarjeta = self._tarjeta(cuerpo, 1)
        arriba = tk.Frame(tarjeta, bg=BLANCO)
        arriba.pack(fill="x")
        self.b_llenar = tk.Button(arriba, text="Llenar", command=self.llenar,
                                  bg=VERDE, fg=BLANCO, activebackground=VERDE,
                                  activeforeground=BLANCO, relief="flat", bd=0,
                                  padx=34, pady=10, cursor="hand2",
                                  font=(FUENTE, 11, "bold"))
        self.b_llenar.pack(side="left")
        pasos = tk.Frame(arriba, bg=BLANCO)
        pasos.pack(side="left", padx=(28, 0))
        self.l_pasos = []
        for i, texto in enumerate(PASOS):
            marca = tk.Label(pasos, text="○", bg=BLANCO, fg=TENUE,
                             font=(FUENTE, 11), width=2)
            marca.grid(row=0, column=2 * i)
            nombre = tk.Label(pasos, text=texto, bg=BLANCO, fg=TENUE,
                              font=(FUENTE, 9))
            nombre.grid(row=0, column=2 * i + 1, padx=(0, 14))
            self.l_pasos.append((marca, nombre))
        self.barra = ttk.Progressbar(tarjeta, mode="determinate", maximum=100)
        self.barra.pack(fill="x", pady=(14, 4))
        tk.Label(tarjeta, textvariable=self.estado, bg=BLANCO, fg="#333",
                 font=(FUENTE, 9), anchor="w").pack(fill="x")

        # ---- 3. resultado
        acciones = tk.Frame(cuerpo, bg=FONDO)
        acciones.grid(row=2, column=0, sticky="ew", pady=(14, 6))
        self.b_archivo = self._boton_sec(acciones, "Abrir archivo único",
                                         lambda: self._abre_resultado("archivo"))
        self.b_revisar = self._boton_sec(acciones, "Abrir REVISAR",
                                         lambda: self._abre_resultado("revisar"))
        self.b_resultado = self._boton_sec(acciones, "Abrir carpeta",
                                           lambda: self._abre_resultado("carpeta"))
        for b in (self.b_archivo, self.b_revisar, self.b_resultado):
            b.config(state="disabled")

        pestanas = ttk.Notebook(cuerpo)
        pestanas.grid(row=3, column=0, sticky="nsew")
        self.pestanas = pestanas

        # Arriba la lista de avisos; abajo, el aviso elegido entero. Los
        # textos de REVISAR son de dos o tres lineas y en una columna de
        # tabla quedaban cortados a la mitad.
        marco = tk.Frame(pestanas, bg=BLANCO)
        pestanas.add(marco, text="Por revisar")
        lista = tk.Frame(marco, bg=BLANCO)
        cols = ("hoja", "donde", "casos")
        self.tabla = ttk.Treeview(lista, columns=cols, show="headings", height=5)
        for c, txt, ancho, estira in zip(cols, ("Hoja", "Dónde mirar", "Casos"),
                                         (220, 600, 60), (False, True, False)):
            self.tabla.heading(c, text=txt, anchor="w")
            self.tabla.column(c, width=ancho, anchor="w", stretch=estira)
        barra_t = ttk.Scrollbar(lista, orient="vertical", command=self.tabla.yview)
        self.tabla.configure(yscrollcommand=barra_t.set)
        self.tabla.pack(side="left", fill="both", expand=True)
        barra_t.pack(side="right", fill="y")
        self.tabla.bind("<<TreeviewSelect>>", self._muestra_aviso)
        self.avisos = {}
        self.detalle = tk.Text(marco, height=7, bg="#FBFBF8", fg="#222", bd=0,
                               wrap="word", padx=12, pady=10, font=(FUENTE, 9),
                               highlightbackground="#DDE3EA", highlightthickness=1)
        self.detalle.pack(side="bottom", fill="x")
        lista.pack(fill="both", expand=True)
        self.detalle.tag_config("titulo", font=(FUENTE, 9, "bold"), foreground=AZUL_OSC)
        self.detalle.tag_config("vacio", foreground=TENUE)
        self._pon_detalle([])

        marco = tk.Frame(pestanas, bg=BLANCO)
        pestanas.add(marco, text="Detalle")
        self.log = tk.Text(marco, bg="#1E1E1E", fg="#D4D4D4", bd=0,
                           font=("Consolas", 9), wrap="none", padx=10, pady=8)
        barra_l = ttk.Scrollbar(marco, orient="vertical", command=self.log.yview)
        self.log.configure(yscrollcommand=barra_l.set, state="disabled")
        self.log.pack(side="left", fill="both", expand=True)
        barra_l.pack(side="right", fill="y")
        self.log.tag_config("err", foreground="#F48771")
        self.log.tag_config("ok", foreground="#7BD88F")
        self.log.tag_config("paso", foreground="#9CDCFE")

    def _tarjeta(self, padre, fila):
        marco = tk.Frame(padre, bg=BLANCO, padx=18, pady=14,
                         highlightbackground="#DDE3EA", highlightthickness=1)
        marco.grid(row=fila, column=0, sticky="ew", pady=(0, 12))
        return marco

    def _etiqueta(self, padre, texto):
        return tk.Label(padre, text=texto, bg=BLANCO, fg="#222",
                        font=(FUENTE, 10, "bold"))

    def _boton_sec(self, padre, texto, accion):
        b = tk.Button(padre, text=texto, command=accion, bg=BLANCO, fg=AZUL_OSC,
                      activebackground="#E8EEF5", relief="solid", bd=1,
                      padx=14, pady=5, cursor="hand2", font=(FUENTE, 9))
        b.pack(side="left", padx=(0, 8))
        return b

    # -------------------------------------------------- empresas y periodos
    def _lee_cache(self):
        try:
            return [Planilla(**d) for d in json.loads(CACHE.read_text("utf-8"))]
        except (OSError, ValueError, TypeError):
            return []

    def _guarda_cache(self):
        try:
            CACHE.parent.mkdir(parents=True, exist_ok=True)
            CACHE.write_text(json.dumps([p.__dict__ for p in self.planillas]), "utf-8")
        except OSError:
            pass

    def _refresca_empresas(self):
        todas = sorted(set(empresas_locales()) | {p.empresa for p in self.planillas})
        self.c_empresa["values"] = todas
        if self.empresa.get() not in todas:
            # Por omision la primera que tenga plantillas: es la que se usa.
            con_plantillas = [e for e in todas if plantillas_de(BASE / e)]
            self.empresa.set((con_plantillas or todas or [""])[0])
        self._refresca_periodos()

    def _refresca_periodos(self):
        propias = [p for p in self.planillas if p.empresa == self.empresa.get()]
        propias.sort(key=lambda p: p.orden, reverse=True)
        valores = [p.periodo for p in propias]
        self.c_periodo["values"] = valores
        if self.periodo.get() not in valores:
            self.periodo.set(valores[0] if valores else "")
        self._refresca_info()

    def _cambia_eleccion(self):
        """Otra empresa o periodo: lo que muestra la ventana ya no es de esto."""
        self._refresca_periodos()
        self.resultado = None
        for b in (self.b_archivo, self.b_revisar, self.b_resultado):
            b.config(state="disabled")
        self.tabla.delete(*self.tabla.get_children())
        self.avisos = {}
        self._pon_detalle([])
        for i in range(len(PASOS)):
            self._marca_paso(i, "pendiente")
        self.barra["value"] = 0
        self.estado.set("")

    def _planilla(self):
        return next((p for p in self.planillas if p.empresa == self.empresa.get()
                     and p.periodo == self.periodo.get()), None)

    def _refresca_info(self):
        emp = self.empresa.get()
        p = self._planilla()
        if p:
            f = p.modificada_local()
            cuando = f" · modificada el {f:%d-%m-%Y a las %H:%M}" if f else ""
            self.info_workiva.set(f"En Workiva: «{p.nombre}»{cuando}")
            self.l_workiva.config(fg=GRIS)
        elif self.buscando:
            self.info_workiva.set("Buscando las planillas XBRL en Workiva…")
            self.l_workiva.config(fg=GRIS)
        elif emp:
            self.info_workiva.set(f"En Workiva no hay ninguna planilla «{emp} XBRL MM-AAAA».")
            self.l_workiva.config(fg=ROJO)
        else:
            self.info_workiva.set("")

        if not emp:
            self.info_plantillas.set("")
            self.b_carpeta.pack_forget()
            return
        n = len(plantillas_de(BASE / emp))
        if n:
            self.info_plantillas.set(f"Plantillas de DBNeT: {n} archivos en {emp}\\xls")
            self.l_plantillas.config(fg=GRIS)
            self.b_carpeta.config(text="Abrir carpeta")
        else:
            self.info_plantillas.set(f"Faltan las plantillas de DBNeT de {emp}: "
                                     f"cópialas en la carpeta {emp}\\xls")
            self.l_plantillas.config(fg=ROJO)
            self.b_carpeta.config(text="Crear y abrir la carpeta")
        self.b_carpeta.pack(side="left", padx=8)

    def _abre_carpeta_empresa(self):
        emp = self.empresa.get()
        if not emp:
            return
        xls = BASE / emp / "xls"
        xls.mkdir(parents=True, exist_ok=True)
        abre(xls)

    def _busca_planillas(self):
        if self.buscando:
            return
        self.buscando = True
        self.b_buscar.config(state="disabled", text="Buscando en Workiva…")
        self._refresca_info()

        def trabajo():
            try:
                self.cola.put(("planillas", Workiva().planillas()))
            except ErrorWorkiva as e:
                self.cola.put(("planillas_error", str(e)))
            except Exception as e:                       # noqa: BLE001
                self.cola.put(("planillas_error", f"{type(e).__name__}: {e}"))

        threading.Thread(target=trabajo, daemon=True).start()

    # ------------------------------------------------------------ llenado
    def llenar(self):
        if self.corriendo:
            return
        emp, p = self.empresa.get(), self._planilla()
        if not emp or not p:
            messagebox.showwarning("Falta elegir",
                                   "Elige una empresa y un período que existan en Workiva.")
            return
        if not plantillas_de(BASE / emp):
            messagebox.showwarning(
                "Faltan las plantillas",
                f"No hay plantillas de DBNeT en {BASE / emp / 'xls'}.\n\n"
                "Copia ahí los archivos .xlsm que entrega DBNeT para esta empresa.")
            return

        self.corriendo = True
        self.resultado = None
        for b in (self.b_llenar, self.b_archivo, self.b_revisar,
                  self.b_resultado, self.b_buscar):
            b.config(state="disabled")
        self.c_empresa.config(state="disabled")
        self.c_periodo.config(state="disabled")
        self.tabla.delete(*self.tabla.get_children())
        self._pon_detalle([])
        self.log.config(state="normal")
        self.log.delete("1.0", "end")
        self.log.config(state="disabled")
        for i in range(len(PASOS)):
            self._marca_paso(i, "pendiente")
        self.barra.config(mode="determinate")
        self.barra["value"] = 0
        self.confirmacion = queue.Queue()
        threading.Thread(target=self._trabaja, args=(emp, p), daemon=True).start()

    def _trabaja(self, emp, planilla):
        """En un hilo aparte; habla con la ventana solo por la cola."""
        carpeta = BASE / emp
        xls = carpeta / "xls"
        export = carpeta / "workiva" / f"{planilla.nombre}.xlsx"
        revisar = carpeta / "REVISAR.xlsx"
        temporal = TEMPORAL / emp
        temporal.mkdir(parents=True, exist_ok=True)
        base = carpeta / f"{planilla.nombre}_LLENADO"
        comun = ["--plantillas", str(xls), "--workiva", str(export),
                 "--sobre-plantillas", "--revisar", str(revisar),
                 "--reporte", str(temporal / "reporte_llenado.csv")]
        paso = 0
        try:
            # 1. Workiva
            self.cola.put(("paso", (paso, f"Descargando «{planilla.nombre}» desde Workiva…")))
            t0 = time.time()
            Workiva().descarga(planilla, export)
            self.cola.put(("linea", (f"Descargado de Workiva en {time.time() - t0:.0f} s: "
                                     f"{export}", "ok")))

            # 2. Simulacion
            paso = 1
            self.cola.put(("paso", (paso, "Simulando: todavía no se escribe nada…")))
            codigo, lineas = self._corre("llenar", comun + ["--dry-run"])
            if codigo:
                return self._falla(paso, lineas)
            celdas, avisos = self._resumen(lineas)
            self.cola.put(("revisar", str(revisar)))
            self.cola.put(("confirma", (emp, planilla.nombre, celdas, avisos,
                                        len(plantillas_de(carpeta)))))
            if not self.confirmacion.get():
                return self.cola.put(("fin", ("cancelado", paso,
                                              "Cancelado. No se escribió ningún archivo.")))

            # 3. Llenado
            paso = 2
            self.cola.put(("paso", (paso, "Llenando las plantillas…")))
            codigo, lineas = self._corre("llenar", comun)
            if codigo:
                return self._falla(paso, lineas)
            celdas, avisos = self._resumen(lineas)
            self.cola.put(("revisar", str(revisar)))

            # 4. Archivo unico
            paso = 3
            self.cola.put(("paso", (paso, "Armando el archivo único con Excel "
                                          "(toma un par de minutos)…")))
            # Igual que el .bat: si el .xlsm con macros no sale (sin Excel en
            # el equipo), queda al menos el .xlsx. Un archivo abierto, en
            # cambio, es para cerrarlo y volver a correr, no para seguir.
            codigo_macros, lineas = self._corre(
                "fusionar", ["--origen", str(xls), "--salida", f"{base}.xlsm",
                             "--con-macros", "--solo-workiva"])
            if codigo_macros and any("esta abierto en Excel" in l for l in lineas):
                return self._falla(paso, lineas)
            codigo, lineas_x = self._corre(
                "fusionar", ["--origen", str(xls), "--salida", f"{base}.xlsx",
                             "--solo-workiva"])
            if codigo:
                return self._falla(paso, lineas_x)
            final = Path(f"{base}.xlsx" if codigo_macros else f"{base}.xlsm")
            if codigo_macros:
                self.cola.put(("aviso", (
                    "Sin macros",
                    "No se pudo armar el archivo único con macros (hace falta Excel "
                    "en este computador). Quedó el .xlsx, sin botones.\n\n"
                    f"Los archivos de {emp}\\xls están llenos y sus botones "
                    "funcionan igual.")))
            self.cola.put(("fin", ("ok", paso, (final, revisar, celdas, avisos))))
        except ErrorWorkiva as e:
            self.cola.put(("linea", (str(e), "err")))
            self.cola.put(("fin", ("error", paso, str(e))))
        except Exception as e:                           # noqa: BLE001
            self.cola.put(("linea", (traceback.format_exc(), "err")))
            self.cola.put(("fin", ("error", paso, f"{type(e).__name__}: {e}")))

    def _corre(self, tarea, args):
        """Corre una tarea como proceso aparte y devuelve (codigo, lineas)."""
        if getattr(sys, "frozen", False):
            orden = [sys.executable, "--tarea", tarea, *args]
        else:
            orden = [sys.executable, "-u", str(Path(__file__).resolve()),
                     "--tarea", tarea, *args]
        respaldo = Path(tempfile.gettempdir()) / f"xbrl_{tarea}_{os.getpid()}.log"
        respaldo.unlink(missing_ok=True)
        entorno = {**os.environ, "PYTHONIOENCODING": "utf-8",
                   "PYTHONUNBUFFERED": "1", "XBRL_SALIDA": str(respaldo)}
        self.cola.put(("linea", (f"\n── {tarea} " + "─" * 50, "paso")))
        proc = subprocess.Popen(orden, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                stdin=subprocess.DEVNULL, text=True, encoding="utf-8",
                                errors="replace", cwd=str(BASE), env=entorno,
                                creationflags=SIN_CONSOLA)
        lineas = []
        for linea in proc.stdout:
            lineas.append(linea.rstrip())
            self.cola.put(("linea", (lineas[-1], None)))
        codigo = proc.wait()
        if not lineas and respaldo.exists():
            for linea in respaldo.read_text("utf-8", "replace").splitlines():
                lineas.append(linea)
                self.cola.put(("linea", (linea, None)))
        respaldo.unlink(missing_ok=True)
        return codigo, lineas

    @staticmethod
    def _resumen(lineas):
        celdas, avisos = None, 0
        for l in lineas:
            m = TOTAL.match(l.strip())
            if m:
                celdas = int(re.sub(r"\D", "", m.group(1)))
            m = AVISOS.search(l)
            if m:
                avisos = int(m.group(1))
        return celdas, avisos

    def _falla(self, paso, lineas):
        # El mensaje util es lo ultimo que imprimio el script (los sys.exit
        # con texto explican que hacer); se salta el traceback si lo hay.
        utiles = [l for l in lineas if l.strip()]
        texto = "\n".join(utiles[-8:]) or "El proceso terminó sin decir por qué."
        self.cola.put(("fin", ("error", paso, texto)))

    # ------------------------------------------------------------ recepcion
    def _drena(self):
        try:
            while True:
                tipo, dato = self.cola.get_nowait()
                getattr(self, f"_en_{tipo}")(dato)
        except queue.Empty:
            pass
        self.after(80, self._drena)

    def _en_planillas(self, lista):
        self.buscando = False
        self.planillas = lista
        self._guarda_cache()
        self.b_buscar.config(state="normal" if not self.corriendo else "disabled",
                             text="↻  Buscar en Workiva")
        self._refresca_empresas()

    def _en_planillas_error(self, texto):
        self.buscando = False
        self.b_buscar.config(state="normal" if not self.corriendo else "disabled",
                             text="↻  Buscar en Workiva")
        self._refresca_info()
        if not self.planillas:
            messagebox.showerror("Workiva", texto)
        else:
            self.estado.set("No se pudo actualizar la lista de Workiva; "
                            "se muestra la última que se encontró.")

    def _en_linea(self, dato):
        texto, tag = dato
        self._escribe(texto, tag)
        m = N_PLANTILLAS.match(texto)
        if m:
            self.total, self.hechos = int(m.group(1)), 0
        elif self.total and AVANCE.match(texto):
            self.hechos += 1
            self.barra["value"] = min(100, self.hechos * 100 / self.total)
            self.estado.set(f"{self.l_pasos[self.paso][1]['text']}… "
                            f"{self.hechos} de {self.total} plantillas")

    def _en_paso(self, dato):
        paso, texto = dato
        self.paso = paso
        for i in range(paso):
            self._marca_paso(i, "hecho")
        self._marca_paso(paso, "actual")
        self.estado.set(texto)
        self.total = self.hechos = 0
        if paso in (0, 3):
            self.barra.config(mode="indeterminate")
            self.barra.start(12)
        else:
            self.barra.stop()
            self.barra.config(mode="determinate")
            self.barra["value"] = 0

    def _en_revisar(self, ruta):
        self._carga_revisar(Path(ruta))

    def _en_aviso(self, dato):
        messagebox.showwarning(*dato)

    def _en_confirma(self, dato):
        emp, nombre, celdas, avisos, n = dato
        texto = (f"La simulación con «{nombre}» está lista.\n\n"
                 f"Se van a llenar los {n} archivos de {emp}\\xls"
                 + (f" con {miles(celdas)} celdas" if celdas is not None else "") + ".")
        if avisos:
            texto += (f"\n\nHay {avisos} aviso{'s' if avisos != 1 else ''} para revisar: "
                      "los ves en la pestaña «Por revisar».")
        texto += ("\n\nLos archivos se sobrescriben; las plantillas originales de "
                  "DBNeT quedan respaldadas y se reponen en cada llenado.\n\n¿Continuar?")
        self.barra.stop()
        self.confirmacion.put(messagebox.askyesno("Confirmar llenado", texto))

    def _en_fin(self, dato):
        tipo, paso, info = dato
        self.corriendo = False
        self.barra.stop()
        self.barra.config(mode="determinate")
        for b in (self.b_llenar, self.b_buscar):
            b.config(state="normal")
        self.c_empresa.config(state="readonly")
        self.c_periodo.config(state="readonly")

        if tipo == "ok":
            final, revisar, celdas, avisos = info
            for i in range(len(PASOS)):
                self._marca_paso(i, "hecho")
            self.barra["value"] = 100
            self.resultado = {"archivo": final, "revisar": revisar,
                              "carpeta": final.parent}
            self.b_archivo.config(state="normal")
            self.b_resultado.config(state="normal")
            self.b_revisar.config(state="normal" if revisar.exists() else "disabled")
            resumen = f"Listo: {final.name}"
            if celdas is not None:
                resumen += f" · {miles(celdas)} celdas"
            resumen += (f" · {avisos} aviso{'s' if avisos != 1 else ''} por revisar"
                        if avisos else " · nada que revisar")
            self.estado.set(resumen)
            self._escribe(f"\n{resumen}", "ok")
            if avisos:
                self.pestanas.select(0)
        elif tipo == "cancelado":
            self._marca_paso(paso, "pendiente")
            self.barra["value"] = 0
            self.estado.set(info)
        else:
            self._marca_paso(paso, "error")
            self.estado.set(f"Se detuvo en: {PASOS[paso]}")
            self._escribe(info, "err")
            messagebox.showerror(f"No se pudo terminar: {PASOS[paso]}", info)

    # ------------------------------------------------------------ utilidades
    def _marca_paso(self, i, como):
        marca, nombre = self.l_pasos[i]
        simbolo, color, peso = {"pendiente": ("○", TENUE, "normal"),
                                "actual": ("●", AZUL, "bold"),
                                "hecho": ("✔", VERDE, "normal"),
                                "error": ("✖", ROJO, "bold")}[como]
        marca.config(text=simbolo, fg=color)
        nombre.config(fg="#222" if como != "pendiente" else TENUE,
                      font=(FUENTE, 9, peso))

    def _escribe(self, texto, tag=None):
        self.log.config(state="normal")
        self.log.insert("end", texto + "\n", tag or ())
        self.log.see("end")
        self.log.config(state="disabled")

    def _carga_revisar(self, ruta):
        self.tabla.delete(*self.tabla.get_children())
        self.avisos = {}
        if not ruta.exists():
            self._pon_detalle([("Nada que revisar", "todo calzó sin suponer nada.")])
            return
        try:
            from openpyxl import load_workbook
            libro = load_workbook(ruta, read_only=True)
            for i, fila in enumerate(libro.active.iter_rows(values_only=True)):
                if not i or not any(fila):
                    continue
                hoja, donde, paso, mirar, casos = ([v if v is not None else ""
                                                    for v in fila] + [""] * 5)[:5]
                iid = self.tabla.insert("", "end", values=(hoja, donde, casos))
                self.avisos[iid] = (hoja, donde, paso, mirar)
            libro.close()
        except Exception as e:                           # noqa: BLE001
            self._escribe(f"No se pudo leer {ruta.name}: {e}", "err")
        filas = self.tabla.get_children()
        if filas:
            self.tabla.selection_set(filas[0])
        else:
            self._pon_detalle([])

    def _muestra_aviso(self, _evento=None):
        sel = self.tabla.selection()
        if not sel or sel[0] not in self.avisos:
            return
        hoja, donde, paso, mirar = self.avisos[sel[0]]
        self._pon_detalle([(hoja, ""), ("Dónde mirar", donde), ("Qué pasó", paso),
                           ("Qué hay que revisar", mirar)])

    def _pon_detalle(self, partes):
        self.detalle.config(state="normal")
        self.detalle.delete("1.0", "end")
        if not partes:
            self.detalle.insert("end", "Después de llenar, aquí aparece lo que "
                                "hay que mirar antes de entregar. Si no aparece "
                                "nada, no hay nada que revisar.", "vacio")
        for i, (titulo, texto) in enumerate(partes):
            if i:
                self.detalle.insert("end", "\n")
            self.detalle.insert("end", titulo + (": " if titulo and texto else ""), "titulo")
            self.detalle.insert("end", str(texto))
        self.detalle.config(state="disabled")

    def _abre_resultado(self, que):
        if self.resultado and Path(self.resultado[que]).exists():
            abre(self.resultado[que])


def main():
    if os.name == "nt":
        # Sin esto Windows estira la ventana y el texto sale borroso en
        # pantallas con escala.
        try:
            import ctypes
            ctypes.windll.shcore.SetProcessDpiAwareness(1)
        except (AttributeError, OSError):
            pass
    Aplicacion().mainloop()


if __name__ == "__main__":
    main()
