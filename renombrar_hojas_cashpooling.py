"""
renombrar_hojas_cashpooling.py
==============================
Renombra las subhojas de "CGE Cash management - Summary"
usando los valores de E2:E23 del archivo "TE - Bases MM-YYYY".

Flujo:
  1. Usuario ingresa mes y año del periodo (ej: 07 / 2026)
  2. Busca "TE - Bases 07-2026" → lee E2:E23 (22 fechas como 01.07, 02.07, ...)
  3. Busca "07 CGE Cash management for Cashpooling"
  4. Encuentra las subhojas con nombre "CGE Cash management DD.MM"
  5. Muestra vista previa: nombre actual → nombre nuevo
  6. Aplica los cambios al confirmar
"""

import json, re, ssl, time, threading
import tkinter as tk
from tkinter import ttk, messagebox

# ── CREDENCIALES ──────────────────────────────────────────────────────────────
CLIENT_ID     = "db2c551e-e18a-417e-8e52-d182716b8ef2"
CLIENT_SECRET = "wk_secret:oa2c:DzlUCmBQDv6raPxG09me"
WORKSPACE_ID  = "w_34913aadaa38420eabd7e4d341b78a1a"
TOKEN_URL     = "https://api.app.wdesk.com/iam/v1/oauth2/token"
WDESK_BASE    = "https://api.app.wdesk.com"

# ── SSL (red corporativa con inspección SSL) ───────────────────────────────────
import urllib.request, urllib.error
CTX = ssl.create_default_context()
CTX.check_hostname = False
CTX.verify_mode    = ssl.CERT_NONE

# ── HTTP base ─────────────────────────────────────────────────────────────────
def _http(method, url, headers=None, body=None, timeout=60):
    data = json.dumps(body).encode() if body is not None else None
    h = {"Content-Type": "application/json",
         "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Python/3",
         **(headers or {})}
    req = urllib.request.Request(url, data=data, headers=h, method=method)
    last_err = None
    for attempt in range(4):
        try:
            with urllib.request.urlopen(req, context=CTX, timeout=timeout) as resp:
                raw = resp.read()
                return resp.status, json.loads(raw) if raw else {}
        except urllib.error.HTTPError as e:
            raw = e.read()
            return e.code, json.loads(raw) if raw else {}
        except Exception as e:
            last_err = e
            time.sleep(2 ** attempt)
    raise last_err

# ── AUTH ──────────────────────────────────────────────────────────────────────
_token = None
_token_expiry = 0.0

def _get_token():
    global _token, _token_expiry
    if _token and time.time() < _token_expiry:
        return _token
    st, data = _http("POST", TOKEN_URL, body={
        "grant_type": "client_credentials",
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
    })
    if st != 200:
        raise RuntimeError(f"Autenticación fallida: {st} — {data}")
    _token = data["access_token"]
    _token_expiry = time.time() + data.get("expires_in", 3600) - 60
    return _token

def _hdrs():
    return {
        "Authorization": f"Bearer {_get_token()}",
        "Content-Type":  "application/json",
        "X-Version":     "2022-01-01",
    }

def _get(path):
    url = f"{WDESK_BASE}{path}" if path.startswith("/") else path
    st, data = _http("GET", url, headers=_hdrs())
    if st not in (200, 206):
        raise RuntimeError(f"GET {path} → {st}: {data}")
    return data

def _patch(path, body):
    url = f"{WDESK_BASE}{path}"
    return _http("PATCH", url, headers=_hdrs(), body=body)

def _put(path, body):
    url = f"{WDESK_BASE}{path}"
    return _http("PUT", url, headers=_hdrs(), body=body)

# ── WORKIVA: búsqueda de spreadsheets ─────────────────────────────────────────
def buscar_spreadsheet(patron):
    """Devuelve (id, nombre) de la primera spreadsheet cuyo nombre contenga 'patron'."""
    url = "/platform/v1/spreadsheets?$top=100"
    while url:
        data = _get(url)
        for ss in data.get("value", data.get("data", [])):
            if patron.lower() in ss.get("name", "").lower():
                return ss["id"], ss["name"]
        url = data.get("@nextLink") or data.get("nextLink") or None
    return None, None

def listar_hojas(ss_id):
    """Devuelve lista de todas las hojas de la spreadsheet."""
    hojas = []
    url = f"/platform/v1/spreadsheets/{ss_id}/sheets?$top=200"
    while url:
        data = _get(url)
        hojas.extend(data.get("value", data.get("data", [])))
        url = data.get("@nextLink") or data.get("nextLink") or None
    return hojas

def leer_rango(ss_id, sheet_id, rango):
    """Lee valores de un rango y devuelve lista plana de strings."""
    data = _get(f"/platform/v1/spreadsheets/{ss_id}/sheets/{sheet_id}/values/{rango}")
    # Workiva puede devolver el arreglo en distintas claves
    vals = (data.get("values")
            or data.get("data", {}).get("values")
            or data.get("body", {}).get("values")
            or [])
    resultado = []
    for fila in vals:
        celda = fila[0] if isinstance(fila, list) and fila else fila
        texto = str(celda).strip() if celda is not None else ""
        resultado.append(texto)
    return resultado

def renombrar_hoja(ss_id, sheet_id, nuevo_nombre):
    """Intenta renombrar una hoja; prueba PATCH y luego PUT si falla."""
    st, data = _patch(f"/platform/v1/spreadsheets/{ss_id}/sheets/{sheet_id}",
                      {"name": nuevo_nombre})
    if st in (200, 204):
        return st, data
    # Algunos endpoints de Workiva usan PUT para actualizar metadatos
    st2, data2 = _put(f"/platform/v1/spreadsheets/{ss_id}/sheets/{sheet_id}",
                      {"name": nuevo_nombre})
    return st2, data2

# ── LÓGICA DE NEGOCIO ─────────────────────────────────────────────────────────
PATRON_SUBHOJA = re.compile(r"^CGE Cash management \d{2}\.\d{2}$")

def obtener_bases(mes, anio):
    """Lee E2:E23 de 'TE - Bases MM-YYYY'. Devuelve (lista_valores, nombre_ss)."""
    patron = f"TE - Bases {mes}-{anio}"
    ss_id, ss_nom = buscar_spreadsheet(patron)
    if not ss_id:
        raise RuntimeError(f"No se encontró: '{patron}'")

    hojas = listar_hojas(ss_id)
    if not hojas:
        raise RuntimeError(f"La spreadsheet '{ss_nom}' no tiene hojas")

    # Buscar primera hoja visible (no la Summary/Cover si hubiese)
    hoja_id = hojas[0]["id"]
    valores = leer_rango(ss_id, hoja_id, "E2:E23")
    bases = [v for v in valores if v]  # filtrar vacíos
    return bases, ss_nom

def obtener_subhojas(mes, anio):
    """
    Busca 'MM CGE Cash management for Cashpooling' y devuelve
    (ss_id, ss_nom, subhojas_ordenadas).
    Las subhojas son las que coinciden con el patrón "CGE Cash management DD.MM".
    """
    patron = f"{mes} CGE Cash management"
    ss_id, ss_nom = buscar_spreadsheet(patron)
    if not ss_id:
        raise RuntimeError(f"No se encontró spreadsheet con: '{patron}'")

    hojas = listar_hojas(ss_id)

    # Primero intentar por parentId de "CGE Cash management - Summary"
    summary_id = None
    for h in hojas:
        if h.get("name", "").strip() == "CGE Cash management - Summary":
            summary_id = h["id"]
            break

    subhojas = []
    if summary_id:
        for h in hojas:
            pid = (h.get("parentId")
                   or h.get("parent", {}).get("id", "")
                   or "")
            if pid == summary_id:
                subhojas.append(h)

    # Si no encontramos por parentId, usar patrón de nombre
    if not subhojas:
        subhojas = [h for h in hojas if PATRON_SUBHOJA.match(h.get("name", ""))]

    # Ordenar por nombre para que coincidan con E2, E3, E4...
    subhojas.sort(key=lambda h: h.get("name", ""))

    if not subhojas:
        raise RuntimeError(
            "No se encontraron subhojas con patrón 'CGE Cash management DD.MM'\n"
            "Verifica que el archivo y las hojas existan en Workiva."
        )

    return ss_id, ss_nom, subhojas

# ── COLORES ───────────────────────────────────────────────────────────────────
AZUL   = "#011689"
AZUL2  = "#0a2abf"
FONDO  = "#f0f3fc"
BLANC  = "#ffffff"
VERDE  = "#0a8f5c"
ROJO   = "#c0001a"
GRIS   = "#6b7aab"
BORDE  = "#c8d0e8"
ROWALT = "#e8ecf8"

# ── GUI ───────────────────────────────────────────────────────────────────────
class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Renombrar Hojas — CGE Cash Management")
        self.configure(bg=FONDO)
        self.resizable(True, True)
        self.minsize(860, 560)
        self._center(960, 660)

        self._ss_id = None
        self._pares = []   # [(sheet_id, nombre_actual, nombre_nuevo), ...]

        self._build_ui()

    def _center(self, w, h):
        self.update_idletasks()
        x = (self.winfo_screenwidth()  - w) // 2
        y = (self.winfo_screenheight() - h) // 2
        self.geometry(f"{w}x{h}+{x}+{y}")

    # ── CONSTRUCCIÓN UI ───────────────────────────────────────────────────────
    def _build_ui(self):
        # Header
        hdr = tk.Frame(self, bg=AZUL, height=62)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)
        tk.Label(hdr, text="Renombrar Hojas  —  CGE Cash Management",
                 font=("Segoe UI", 14, "bold"), bg=AZUL, fg=BLANC
                 ).pack(side="left", padx=22, pady=0)
        tk.Label(hdr, text="Tesorería Estratégica",
                 font=("Segoe UI", 9), bg=AZUL, fg="#8899dd"
                 ).pack(side="right", padx=22)

        # Formulario
        frm = tk.Frame(self, bg=FONDO, pady=14)
        frm.pack(fill="x", padx=24)

        tk.Label(frm, text="Periodo:", font=("Segoe UI", 10, "bold"),
                 bg=FONDO, fg=AZUL).grid(row=0, column=0, sticky="e", padx=(0, 8))

        tk.Label(frm, text="Mes (01-12):", font=("Segoe UI", 10),
                 bg=FONDO).grid(row=0, column=1, sticky="e", padx=(0, 4))
        self._v_mes = tk.StringVar(value="07")
        tk.Entry(frm, textvariable=self._v_mes, width=5,
                 font=("Segoe UI", 10)).grid(row=0, column=2, padx=(0, 16))

        tk.Label(frm, text="Año:", font=("Segoe UI", 10),
                 bg=FONDO).grid(row=0, column=3, sticky="e", padx=(0, 4))
        self._v_anio = tk.StringVar(value="2026")
        tk.Entry(frm, textvariable=self._v_anio, width=7,
                 font=("Segoe UI", 10)).grid(row=0, column=4, padx=(0, 16))

        self._btn_buscar = tk.Button(
            frm, text="  Buscar  ", command=self._on_buscar,
            bg=AZUL, fg=BLANC, font=("Segoe UI", 10, "bold"),
            relief="flat", padx=10, pady=5, cursor="hand2"
        )
        self._btn_buscar.grid(row=0, column=5, padx=(0, 0))

        # Barra de progreso
        self._progress = ttk.Progressbar(self, mode="indeterminate", length=400)
        self._progress.pack(fill="x", padx=24, pady=(0, 4))

        # Status
        self._lbl_status = tk.Label(
            self, text="Ingresa el periodo y presiona Buscar.",
            font=("Segoe UI", 9), bg=FONDO, fg=GRIS, anchor="w"
        )
        self._lbl_status.pack(fill="x", padx=24, pady=(0, 8))

        # Tabla preview
        frm_t = tk.Frame(self, bg=FONDO)
        frm_t.pack(fill="both", expand=True, padx=24, pady=(0, 4))

        tk.Label(frm_t, text="Vista previa — Nombre actual  →  Nombre nuevo",
                 font=("Segoe UI", 10, "bold"), bg=FONDO, fg=AZUL
                 ).pack(anchor="w", pady=(0, 6))

        tree_frame = tk.Frame(frm_t, bg=BORDE, bd=1, relief="flat")
        tree_frame.pack(fill="both", expand=True)

        cols = ("#", "Nombre actual", "Nombre nuevo")
        self._tree = ttk.Treeview(tree_frame, columns=cols, show="headings", height=18)
        self._tree.heading("#",             text="#",             anchor="center")
        self._tree.heading("Nombre actual", text="Nombre actual", anchor="w")
        self._tree.heading("Nombre nuevo",  text="Nombre nuevo",  anchor="w")
        self._tree.column("#",             width=36,  anchor="center", stretch=False)
        self._tree.column("Nombre actual", width=380, anchor="w")
        self._tree.column("Nombre nuevo",  width=380, anchor="w")

        vsb = ttk.Scrollbar(tree_frame, orient="vertical", command=self._tree.yview)
        self._tree.configure(yscrollcommand=vsb.set)
        self._tree.pack(side="left", fill="both", expand=True)
        vsb.pack(side="right", fill="y")

        # Pie
        bot = tk.Frame(self, bg=FONDO, pady=10)
        bot.pack(fill="x", padx=24)

        self._btn_aplicar = tk.Button(
            bot, text="  ✔  Aplicar cambios  ", command=self._on_aplicar,
            bg=VERDE, fg=BLANC, font=("Segoe UI", 10, "bold"),
            relief="flat", padx=12, pady=6, cursor="hand2", state="disabled"
        )
        self._btn_aplicar.pack(side="left")

        self._lbl_res = tk.Label(bot, text="", font=("Segoe UI", 9, "bold"),
                                 bg=FONDO, fg=VERDE)
        self._lbl_res.pack(side="left", padx=18)

        # Estilos Treeview
        style = ttk.Style(self)
        style.configure("Treeview", rowheight=24, font=("Segoe UI", 9))
        style.configure("Treeview.Heading", font=("Segoe UI", 9, "bold"),
                        background=AZUL, foreground=BLANC)

    # ── HELPERS ───────────────────────────────────────────────────────────────
    def _status(self, msg, color=GRIS):
        self._lbl_status.configure(text=msg, fg=color)

    def _lock(self):
        self._btn_buscar.configure(state="disabled")
        self._btn_aplicar.configure(state="disabled")
        self._progress.start(10)

    def _unlock(self):
        self._btn_buscar.configure(state="normal")
        self._progress.stop()

    def _clear_tree(self):
        for item in self._tree.get_children():
            self._tree.delete(item)

    # ── ACCIONES ──────────────────────────────────────────────────────────────
    def _on_buscar(self):
        mes  = self._v_mes.get().strip().zfill(2)
        anio = self._v_anio.get().strip()
        if not re.fullmatch(r"\d{2}", mes) or not re.fullmatch(r"\d{4}", anio):
            messagebox.showerror("Error", "Ingresa mes (01-12) y año (ej: 2026).")
            return
        self._lock()
        self._clear_tree()
        self._lbl_res.configure(text="")
        self._pares = []
        threading.Thread(target=self._thread_buscar, args=(mes, anio), daemon=True).start()

    def _thread_buscar(self, mes, anio):
        try:
            self.after(0, lambda: self._status(f"Buscando 'TE - Bases {mes}-{anio}'...", AZUL))
            bases, nom_bases = obtener_bases(mes, anio)
            self.after(0, lambda: self._status(
                f"✔ '{nom_bases}' encontrado — {len(bases)} valores leídos en E2:E23", VERDE))

            self.after(0, lambda: self._status(f"Buscando '{mes} CGE Cash management...'", AZUL))
            ss_id, ss_nom, subhojas = obtener_subhojas(mes, anio)
            self._ss_id = ss_id

            self.after(0, lambda: self._render_preview(subhojas, bases, ss_nom))

        except Exception as e:
            self.after(0, lambda: self._status(f"ERROR: {e}", ROJO))
        finally:
            self.after(0, self._unlock)

    def _render_preview(self, subhojas, bases, ss_nom):
        self._clear_tree()
        self._pares = []

        n_cambios = 0
        for i, hoja in enumerate(subhojas):
            actual = hoja.get("name", "")
            if i < len(bases) and bases[i]:
                nuevo = f"CGE Cash management {bases[i]}"
            else:
                nuevo = actual  # sin base → sin cambio

            self._pares.append((hoja["id"], actual, nuevo))
            cambia = nuevo != actual
            if cambia:
                n_cambios += 1
            tag = "cambia" if cambia else "igual"
            self._tree.insert("", "end", values=(i + 1, actual, nuevo), tags=(tag,))

        self._tree.tag_configure("cambia", foreground=AZUL2)
        self._tree.tag_configure("igual",  foreground=GRIS)

        self._status(
            f"'{ss_nom}'  |  {len(subhojas)} subhojas  |  {n_cambios} con cambio  |  "
            f"{len(bases)} bases leídas",
            AZUL
        )
        if n_cambios > 0:
            self._btn_aplicar.configure(state="normal")
        else:
            self._lbl_res.configure(text="Todos los nombres ya están actualizados.", fg=GRIS)

    def _on_aplicar(self):
        n = sum(1 for _, a, b in self._pares if a != b)
        if not messagebox.askyesno(
            "Confirmar",
            f"Se aplicarán {n} cambios de nombre en Workiva.\n\n¿Continuar?"
        ):
            return
        self._lock()
        self._lbl_res.configure(text="Aplicando...", fg=AZUL)
        threading.Thread(target=self._thread_aplicar, daemon=True).start()

    def _thread_aplicar(self):
        ok  = 0
        err = 0
        errores = []
        try:
            for sheet_id, actual, nuevo in self._pares:
                if actual == nuevo:
                    continue
                self.after(0, lambda n=nuevo: self._status(f"Renombrando → {n}", AZUL))
                st, data = renombrar_hoja(self._ss_id, sheet_id, nuevo)
                if st in (200, 204, 202):
                    ok += 1
                else:
                    err += 1
                    errores.append(f"{actual}: HTTP {st}")
                time.sleep(0.25)

        except Exception as e:
            errores.append(str(e))
            err += 1
        finally:
            if not errores:
                msg  = f"✔ {ok} hojas renombradas correctamente."
                color = VERDE
            else:
                msg  = f"✔ {ok} OK   ✘ {err} error(es): {'; '.join(errores[:3])}"
                color = ROJO

            self.after(0, lambda: [
                self._status(msg, color),
                self._lbl_res.configure(text=msg, fg=color),
                self._unlock(),
            ])

# ── ENTRY POINT ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    app = App()
    app.mainloop()
