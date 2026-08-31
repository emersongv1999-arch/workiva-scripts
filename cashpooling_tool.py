"""
cashpooling_tool.py
Herramienta GUI para renombrar hojas y limpiar rangos en Workiva.
"""

import json, re, ssl, time, threading, datetime
from collections import namedtuple
import tkinter as tk
from tkinter import ttk, messagebox
import urllib.request, urllib.error

# ── CREDENCIALES ──────────────────────────────────────────────────────────────
CLIENT_ID     = "db2c551e-e18a-417e-8e52-d182716b8ef2"
CLIENT_SECRET = "wk_secret:oa2c:DzlUCmBQDv6raPxG09me"
TOKEN_URL     = "https://api.app.wdesk.com/iam/v1/oauth2/token"
WDESK_BASE    = "https://api.app.wdesk.com"

CTX = ssl.create_default_context()
CTX.check_hostname = False
CTX.verify_mode    = ssl.CERT_NONE

# ── COLORES CGE ───────────────────────────────────────────────────────────────
BG        = "#1a1a2e"
BG2       = "#16213e"
ACCENT    = "#0f3460"
BTN_BLUE  = "#1565c0"
BTN_GREEN = "#2e7d32"
BTN_RED   = "#c62828"
BTN_GRAY  = "#424242"
FG        = "#e0e0e0"
FG_DIM    = "#9e9e9e"
GREEN     = "#66bb6a"
RED       = "#ef5350"
YELLOW    = "#ffd54f"

# ── HTTP / AUTH ───────────────────────────────────────────────────────────────
_token = None
_token_expiry = 0.0

def _http(method, url, headers=None, body=None, timeout=60):
    data = json.dumps(body).encode() if body is not None else None
    h = {"Content-Type": "application/json", "User-Agent": "Mozilla/5.0", **(headers or {})}
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

def get_token():
    global _token, _token_expiry
    if _token and time.time() < _token_expiry:
        return _token
    st, data = _http("POST", TOKEN_URL, body={
        "grant_type": "client_credentials",
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
    })
    if st != 200:
        raise RuntimeError(f"Auth fallida: {st} — {data}")
    _token = data["access_token"]
    _token_expiry = time.time() + data.get("expires_in", 3600) - 60
    return _token

def hdrs(version="2022-01-01"):
    return {"Authorization": f"Bearer {get_token()}", "Content-Type": "application/json", "X-Version": version}

def api_get(path, version="2022-01-01"):
    url = f"{WDESK_BASE}{path}" if path.startswith("/") else path
    st, data = _http("GET", url, headers=hdrs(version))
    if st not in (200, 206):
        raise RuntimeError(f"GET {path} -> {st}: {data}")
    return data

def api_patch(path, body):
    return _http("PATCH", f"{WDESK_BASE}{path}", headers=hdrs(), body=body)

def api_put(path, body):
    return _http("PUT", f"{WDESK_BASE}{path}", headers=hdrs(), body=body)

# ── LÓGICA DE NEGOCIO ─────────────────────────────────────────────────────────
def buscar_spreadsheet(patron, log):
    log(f"Buscando: '{patron}'...")
    url = "/platform/v1/spreadsheets?$top=100"
    pagina = 0
    while url:
        pagina += 1
        data = api_get(url)
        items = data.get("value", data.get("data", []))
        log(f"  Página {pagina}: {len(items)} spreadsheets")
        for ss in items:
            nombre = ss.get("name", "")
            if patron.lower() in nombre.lower():
                log(f"  ✓ Encontrado: '{nombre}'")
                return ss["id"], nombre
        url = data.get("@nextLink") or data.get("nextLink") or None
    log(f"  ✗ No encontrado.")
    return None, None

def listar_hojas(ss_id):
    hojas = []
    url = f"/platform/v1/spreadsheets/{ss_id}/sheets?$top=200"
    while url:
        data = api_get(url)
        items = data.get("value", data.get("data", []))
        hojas.extend(items)
        url = data.get("@nextLink") or data.get("nextLink") or None
    return hojas

def leer_bases(ss_id, sheet_id, log):
    data = api_get(f"/platform/v1/spreadsheets/{ss_id}/sheets/{sheet_id}/values/E2:E50")
    raw_data = data.get("data")
    if isinstance(raw_data, list) and raw_data and isinstance(raw_data[0], dict):
        vals = raw_data[0].get("values", [])
    elif isinstance(raw_data, list):
        vals = raw_data
    else:
        vals = data.get("values") or []
    resultado = []
    for fila in vals:
        celda = fila[0] if isinstance(fila, list) and fila else fila
        texto = str(celda).strip() if celda is not None else ""
        try:
            dt = datetime.date.fromisoformat(texto)
            texto = f"{dt.day:02d}.{dt.month:02d}"
        except Exception:
            pass
        if texto:
            resultado.append(texto)
    log(f"  {len(resultado)} fechas leídas de TE - Bases")
    return resultado

def vacias(rango):
    def col_n(s):
        n = 0
        for c in s.upper():
            n = n * 26 + (ord(c) - 64)
        return n
    m_ini = re.match(r"([A-Z]+)(\d+)", rango.split(":")[0])
    m_fin = re.match(r"([A-Z]+)(\d+)", rango.split(":")[1])
    ncols  = col_n(m_fin.group(1)) - col_n(m_ini.group(1)) + 1
    nfilas = int(m_fin.group(2)) - int(m_ini.group(2)) + 1
    return [[""] * ncols for _ in range(nfilas)]

RANGOS_CGE = ["D9:J15","M9:N15","D24:J26","M24:N26","Q9:R15","Q18:R19","Q24:R26"]

RANGOS_FR  = [
    "F4:L8","F10:L14","F16:L20","F22:L26",
    "F28:L32","F36:L40","F42:L46","F48:L52","F54:L58",
    "P4:Q8","P11:Q15","V4:V8","V11:V14",
]

# Una hoja a renombrar. 'parent' es el grupo al que debe pertenecer y
# 'parent_orig' el que tiene hoy: si difieren, la hoja está suelta y hay que
# volver a colgarla aunque su nombre no cambie.
Par = namedtuple("Par", "sheet_id actual nuevo parent idx parent_orig")

def par_cambia(p):
    """True si hay que tocar la hoja: cambia de nombre o está fuera de su grupo."""
    return p.actual != p.nuevo or p.parent_orig != p.parent

# Grupos del archivo "MM Total Cash Management": (hoja padre, prefijo de subhojas)
GRUPOS_TOTAL = [
    ("SGCH Cash management - Summary", "SGCH Cash management"),
    ("CGE S.A.",                       "CGE S.A."),
    ("Chilquinta",                     "Chilquinta"),
    ("SGCI",                           "SGCI"),
    ("SGCE",                           "SGCE"),
]

# ── VENTANA PRINCIPAL ─────────────────────────────────────────────────────────
class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("CGE Cash Management Tool")
        self.configure(bg=BG)
        self.resizable(True, True)
        self.minsize(760, 600)
        self._datos = {}   # resultado del paso "Buscar"

        self._build_ui()
        self.after(0, lambda: self.state("zoomed"))

    # ── UI ────────────────────────────────────────────────────────────────────
    def _build_ui(self):
        # ── Cabecera ──────────────────────────────────────────────────────────
        hdr = tk.Frame(self, bg=ACCENT, pady=12)
        hdr.pack(fill="x")
        tk.Label(hdr, text="CGE Cash Management Tool",
                 font=("Segoe UI", 16, "bold"), bg=ACCENT, fg=FG).pack()
        tk.Label(hdr, text="Tesorería Estratégica — Workiva Automation",
                 font=("Segoe UI", 9), bg=ACCENT, fg=FG_DIM).pack()

        # ── Periodo ───────────────────────────────────────────────────────────
        pf = tk.Frame(self, bg=BG2, padx=20, pady=14)
        pf.pack(fill="x", padx=16, pady=(14, 0))

        tk.Label(pf, text="Mes", font=("Segoe UI", 9), bg=BG2, fg=FG_DIM).grid(row=0, column=0, sticky="w")
        tk.Label(pf, text="Año",  font=("Segoe UI", 9), bg=BG2, fg=FG_DIM).grid(row=0, column=2, sticky="w", padx=(20,0))

        self.v_mes  = tk.StringVar(value=f"{datetime.date.today().month:02d}")
        self.v_anio = tk.StringVar(value=str(datetime.date.today().year))

        e_mes  = tk.Entry(pf, textvariable=self.v_mes,  width=6,
                          font=("Segoe UI", 13, "bold"), bg=ACCENT, fg=FG,
                          insertbackground=FG, relief="flat", justify="center")
        e_mes.grid(row=1, column=0, ipady=4)

        tk.Label(pf, text=" - ", font=("Segoe UI", 13, "bold"), bg=BG2, fg=FG_DIM).grid(row=1, column=1)

        e_anio = tk.Entry(pf, textvariable=self.v_anio, width=8,
                          font=("Segoe UI", 13, "bold"), bg=ACCENT, fg=FG,
                          insertbackground=FG, relief="flat", justify="center")
        e_anio.grid(row=1, column=2, ipady=4, padx=(20,0))

        self.btn_buscar = self._btn(pf, "Buscar en Workiva", BTN_BLUE, self._buscar)
        self.btn_buscar.grid(row=1, column=3, padx=(28,0), ipady=4)

        # ── Tabla preview ─────────────────────────────────────────────────────
        tf = tk.Frame(self, bg=BG, padx=16, pady=8)
        tf.pack(fill="both", expand=True)

        tk.Label(tf, text="Preview de renombrado", font=("Segoe UI", 9, "bold"),
                 bg=BG, fg=FG_DIM).pack(anchor="w")

        cols = ("tipo", "actual", "nuevo", "cambio")
        self.tree = ttk.Treeview(tf, columns=cols, show="headings", height=12,
                                 selectmode="none")
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Treeview",
                        background=BG2, foreground=FG,
                        fieldbackground=BG2, rowheight=22,
                        font=("Segoe UI", 9))
        style.configure("Treeview.Heading",
                        background=ACCENT, foreground=FG,
                        font=("Segoe UI", 9, "bold"))
        style.map("Treeview", background=[("selected", ACCENT)])

        self.tree.heading("tipo",   text="Tipo")
        self.tree.heading("actual", text="Nombre actual")
        self.tree.heading("nuevo",  text="Nombre nuevo")
        self.tree.heading("cambio", text="")
        self.tree.column("tipo",   width=200, anchor="w")
        self.tree.column("actual", width=230, anchor="w")
        self.tree.column("nuevo",  width=230, anchor="w")
        self.tree.column("cambio", width=50,  anchor="center")

        vsb = ttk.Scrollbar(tf, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        self.tree.pack(side="left", fill="both", expand=True)
        vsb.pack(side="right", fill="y")

        self.tree.tag_configure("cambia",  foreground=YELLOW)
        self.tree.tag_configure("igual",   foreground=FG_DIM)
        self.tree.tag_configure("cge",     foreground="#64b5f6")
        self.tree.tag_configure("fr",      foreground="#a5d6a7")

        # ── Botones de acción ─────────────────────────────────────────────────
        af = tk.Frame(self, bg=BG, padx=16, pady=10)
        af.pack(fill="x")
        for c in range(3):
            af.columnconfigure(c, weight=1, uniform="tarjetas")

        # ── Tarjeta CGE Cash Management ───────────────────────────────────────
        card_cge = self._tarjeta(af, "CGE Cash Management", 0)
        self.btn_renombrar   = self._btn_card(card_cge, "Renombrar hojas",     BTN_GREEN, self._renombrar)
        self.btn_limpiar_cge = self._btn_card(card_cge, "Limpiar CGE",         BTN_BLUE,  self._limpiar_cge)
        self.btn_limpiar_fr  = self._btn_card(card_cge, "Limpiar Fund Request", BTN_BLUE, self._limpiar_fr)

        # ── Tarjeta Chilquinta ────────────────────────────────────────────────
        card_ch = self._tarjeta(af, "Chilquinta Cash Management", 1)
        self.btn_renombrar_ch  = self._btn_card(card_ch, "Renombrar hojas",          BTN_GREEN, self._renombrar_ch)
        self.btn_limpiar_ch    = self._btn_card(card_ch, "Limpiar Chilquinta",       BTN_BLUE,  self._limpiar_ch)
        self.btn_limpiar_ch_fr = self._btn_card(card_ch, "Limpiar CC Funds request", BTN_BLUE,  self._limpiar_ch_fr)

        # ── Tarjeta Total (solo renombrado) ───────────────────────────────────
        card_tot = self._tarjeta(af, "Total Cash Management", 2)
        self.btn_renombrar_tot = self._btn_card(card_tot, "Renombrar hojas", BTN_GREEN, self._renombrar_tot)
        tk.Label(card_tot, text="(solo renombrado)", font=("Segoe UI", 8, "italic"),
                 bg=BG2, fg=FG_DIM).pack(pady=(2,0))

        # ── Log ───────────────────────────────────────────────────────────────
        lf = tk.Frame(self, bg=BG, padx=16, pady=7)
        lf.pack(fill="both", expand=True)

        tk.Label(lf, text="Log", font=("Segoe UI", 9, "bold"),
                 bg=BG, fg=FG_DIM).pack(anchor="w")

        self.log_txt = tk.Text(lf, height=9, bg=BG2, fg=FG,
                               font=("Consolas", 8), relief="flat",
                               insertbackground=FG, state="disabled",
                               wrap="word")
        vsb2 = ttk.Scrollbar(lf, orient="vertical", command=self.log_txt.yview)
        self.log_txt.configure(yscrollcommand=vsb2.set)
        self.log_txt.pack(side="left", fill="both", expand=True)
        vsb2.pack(side="right", fill="y")

        self.log_txt.tag_configure("ok",  foreground=GREEN)
        self.log_txt.tag_configure("err", foreground=RED)
        self.log_txt.tag_configure("dim", foreground=FG_DIM)

        # ── Barra de estado ───────────────────────────────────────────────────
        self.status_var = tk.StringVar(value="Ingrese el período y presione Buscar.")
        sb = tk.Label(self, textvariable=self.status_var,
                      font=("Segoe UI", 8), bg=ACCENT, fg=FG_DIM,
                      anchor="w", padx=12, pady=4)
        sb.pack(fill="x", side="bottom")

    def _tarjeta(self, parent, titulo, columna):
        """Crea una tarjeta con encabezado para agrupar botones de un archivo."""
        wrap = tk.Frame(parent, bg=BG2)
        wrap.grid(row=0, column=columna, sticky="nsew",
                  padx=(0 if columna == 0 else 8, 0))

        cab = tk.Frame(wrap, bg=ACCENT)
        cab.pack(fill="x")
        tk.Label(cab, text=titulo, font=("Segoe UI", 9, "bold"),
                 bg=ACCENT, fg=FG, pady=6).pack()

        cuerpo = tk.Frame(wrap, bg=BG2, padx=10, pady=10)
        cuerpo.pack(fill="both", expand=True)
        return cuerpo

    def _btn_card(self, parent, text, color, cmd):
        """Botón de ancho completo dentro de una tarjeta."""
        b = self._btn(parent, text, color, cmd, state="disabled")
        b.pack(fill="x", pady=2, ipady=4)
        return b

    def _btn(self, parent, text, color, cmd, state="normal"):
        b = tk.Button(parent, text=text, bg=color, fg="white",
                      font=("Segoe UI", 10, "bold"), relief="flat",
                      activebackground=color, activeforeground="white",
                      cursor="hand2", command=cmd, state=state,
                      disabledforeground="#aaaaaa")
        return b

    # ── LOG ───────────────────────────────────────────────────────────────────
    def log(self, msg, tag=None):
        def _do():
            self.log_txt.configure(state="normal")
            ts = datetime.datetime.now().strftime("%H:%M:%S")
            self.log_txt.insert("end", f"[{ts}] {msg}\n", tag or "")
            self.log_txt.see("end")
            self.log_txt.configure(state="disabled")
        self.after(0, _do)

    def status(self, msg):
        self.after(0, lambda: self.status_var.set(msg))

    def _set_btns(self, **kwargs):
        def _do():
            for btn_name, state in kwargs.items():
                getattr(self, btn_name).configure(state=state)
        self.after(0, _do)

    # ── BUSCAR ────────────────────────────────────────────────────────────────
    def _buscar(self):
        mes  = self.v_mes.get().strip().zfill(2)
        anio = self.v_anio.get().strip()
        if not mes.isdigit() or not anio.isdigit():
            messagebox.showerror("Error", "Ingrese mes (2 dígitos) y año válidos.")
            return
        self._set_btns(btn_buscar="disabled", btn_renombrar="disabled",
                       btn_limpiar_cge="disabled", btn_limpiar_fr="disabled")
        self._limpiar_tree()
        self._datos.clear()
        self.status("Buscando en Workiva...")
        threading.Thread(target=self._buscar_worker, args=(mes, anio), daemon=True).start()

    def _buscar_worker(self, mes, anio):
        try:
            self.log(f"── Período {mes}-{anio} ──", "dim")

            # Bases
            patron_bases = f"TE - Bases {mes}-{anio}"
            ss_id_bases, _ = buscar_spreadsheet(patron_bases, self.log)
            bases = []
            if ss_id_bases:
                hojas_b = listar_hojas(ss_id_bases)
                if hojas_b:
                    bases = leer_bases(ss_id_bases, hojas_b[0]["id"], self.log)

            def indice_hoja(h):
                """Índice físico de la hoja en Workiva (None si no viene)."""
                for clave in ("index", "position", "order"):
                    v = h.get(clave)
                    if v is not None:
                        return v
                return None

            def construir_pares_desde(hojas, parent_id, prefijo):
                """
                Toma las subhojas de parent_id cuyo nombre es "<prefijo> DD.MM"
                o "<prefijo> xx.xx[N]" (hojas de reserva) y les asigna las fechas
                de TE - Bases en orden.

                IMPORTANTE: se ordenan por su POSICIÓN FÍSICA en Workiva, no por
                nombre. Al renombrar se conserva el index de cada hoja, así que si
                se ordenara por nombre las fechas quedarían asignadas a posiciones
                equivocadas y las hojas se verían desordenadas.
                """
                pat = re.compile(rf"^{re.escape(prefijo)} (\d{{2}}\.\d{{2}}|xx\.xx\d*)$", re.IGNORECASE)

                def padre_de(h):
                    return h.get("parentId") or (h.get("parent") or {}).get("id", "")

                # Se identifican por NOMBRE, no por parent: el prefijo es único
                # dentro del archivo, así que el nombre ya dice a qué grupo
                # pertenece la hoja. Si alguna quedó suelta (perdió el vínculo de
                # subhoja), igual entra y se la vuelve a colgar del grupo al
                # renombrar. Filtrar por parent la dejaría fuera y el grupo se
                # quedaría corto de hojas para las fechas disponibles.
                hijos = [h for h in hojas if pat.match(h.get("name", ""))]

                sueltas = [h for h in hijos if padre_de(h) != parent_id]
                if sueltas:
                    self.log(f"    ↻ {prefijo}: {len(sueltas)} hoja(s) fuera del grupo, "
                             f"se reincorporan al renombrar:", "dim")
                    for h in sueltas:
                        self.log(f"        '{h.get('name','')}' parent={padre_de(h) or '(ninguno)'}", "dim")

                # Orden físico. Si la API no entrega índice, se respeta el orden
                # en que vinieron las hojas (que ya es el orden del documento).
                orig = {id(h): i for i, h in enumerate(hijos)}
                def orden(h):
                    idx = indice_hoja(h)
                    return (idx if idx is not None else orig[id(h)],)
                hijos.sort(key=orden)

                pares = []
                sobrantes = 0
                for i, h in enumerate(hijos):
                    actual = h.get("name","")
                    if i < len(bases) and bases[i]:
                        nuevo = f"{prefijo} {bases[i]}"
                    else:
                        # Sin fecha disponible: vuelve a ser hoja de reserva. Si
                        # conservara su fecha vieja podría chocar con el nombre
                        # que se le asignó a otra hoja del mismo grupo.
                        sufijo = "xx.xx" if sobrantes == 0 else f"xx.xx{sobrantes}"
                        nuevo  = f"{prefijo} {sufijo}"
                        sobrantes += 1
                    idx = indice_hoja(h)
                    if idx is None:
                        idx = i
                    # Se apunta siempre al parent del grupo: así una hoja suelta
                    # vuelve a quedar como subhoja en lugar de seguir rota.
                    pares.append(Par(h["id"], actual, nuevo, parent_id, idx, padre_de(h)))

                if sobrantes:
                    self.log(f"    {prefijo}: {sobrantes} hoja(s) sin fecha quedan como reserva (xx.xx)", "dim")
                return pares

            # ── CGE Cash Management ───────────────────────────────────────────
            patron_cash = f"{mes} CGE Cash management"
            ss_id_cash, nom_cash = buscar_spreadsheet(patron_cash, self.log)
            pares_cge = []; pares_fr = []; subhojas_cge = []; subhojas_fr = []

            if ss_id_cash:
                hojas_cash = listar_hojas(ss_id_cash)
                self.log(f"  CGE: {len(hojas_cash)} hojas")
                pat_cge = re.compile(r"^CGE Cash management \d{2}\.\d{2}$")
                pat_fr  = re.compile(r"^Fund Request \d{2}\.\d{2}$")
                summary_id = next((h["id"] for h in hojas_cash if h.get("name","").strip() == "CGE Cash management - Summary"), None)
                fundreq_id = next((h["id"] for h in hojas_cash if h.get("name","").strip() == "Fund Request"), None)
                pares_cge = construir_pares_desde(hojas_cash, summary_id, "CGE Cash management") if summary_id else []
                pares_fr  = construir_pares_desde(hojas_cash, fundreq_id,  "Fund Request")        if fundreq_id  else []
                subhojas_cge = sorted([h for h in hojas_cash if (h.get("parentId") or (h.get("parent") or {}).get("id","")) == summary_id and pat_cge.match(h.get("name",""))], key=lambda h: h.get("name",""))
                subhojas_fr  = sorted([h for h in hojas_cash if (h.get("parentId") or (h.get("parent") or {}).get("id","")) == fundreq_id  and pat_fr.match(h.get("name",""))],  key=lambda h: h.get("name",""))
                self.log(f"  CGE subhojas: {len(pares_cge)} | Fund Request: {len(pares_fr)}", "dim")
                self._avisar_duplicados(pares_cge, "CGE Cash management")
                self._avisar_duplicados(pares_fr,  "Fund Request")
            else:
                self.log("✗ No se encontró CGE Cash management.", "err")

            # ── Chilquinta Cash Management ────────────────────────────────────
            patron_ch = f"{mes} Chilquinta Cash Management"
            ss_id_ch, nom_ch = buscar_spreadsheet(patron_ch, self.log)
            pares_ch = []; pares_ch_fr = []; subhojas_ch = []; subhojas_ch_fr = []

            if ss_id_ch:
                hojas_ch = listar_hojas(ss_id_ch)
                self.log(f"  Chilquinta: {len(hojas_ch)} hojas")
                pat_ch    = re.compile(r"^Chilquinta \d{2}\.\d{2}$")
                pat_ch_fr = re.compile(r"^CC Funds request \d{2}\.\d{2}$")
                cc_sum_id = next((h["id"] for h in hojas_ch if h.get("name","").strip() == "CC Cash management - Summary"), None)
                cc_fr_id  = next((h["id"] for h in hojas_ch if h.get("name","").strip() == "Funds request"), None)
                pares_ch    = construir_pares_desde(hojas_ch, cc_sum_id, "Chilquinta")       if cc_sum_id else []
                pares_ch_fr = construir_pares_desde(hojas_ch, cc_fr_id,  "CC Funds request") if cc_fr_id  else []
                subhojas_ch    = sorted([h for h in hojas_ch if (h.get("parentId") or (h.get("parent") or {}).get("id","")) == cc_sum_id and pat_ch.match(h.get("name",""))],    key=lambda h: h.get("name",""))
                subhojas_ch_fr = sorted([h for h in hojas_ch if (h.get("parentId") or (h.get("parent") or {}).get("id","")) == cc_fr_id  and pat_ch_fr.match(h.get("name",""))], key=lambda h: h.get("name",""))
                self.log(f"  Chilquinta subhojas: {len(pares_ch)} | CC Funds request: {len(pares_ch_fr)}", "dim")
                self._avisar_duplicados(pares_ch,    "Chilquinta")
                self._avisar_duplicados(pares_ch_fr, "CC Funds request")
            else:
                self.log("✗ No se encontró Chilquinta Cash Management.", "err")

            # ── Total Cash Management (solo renombrado) ───────────────────────
            patron_tot = f"{mes} Total Cash Management"
            ss_id_tot, nom_tot = buscar_spreadsheet(patron_tot, self.log)
            pares_tot = []

            if ss_id_tot:
                hojas_tot = listar_hojas(ss_id_tot)
                self.log(f"  Total: {len(hojas_tot)} hojas")
                for nombre_padre, prefijo in GRUPOS_TOTAL:
                    padre_id = next((h["id"] for h in hojas_tot
                                     if h.get("name","").strip() == nombre_padre), None)
                    if not padre_id:
                        self.log(f"    ⚠ No se encontró el grupo '{nombre_padre}'", "err")
                        continue
                    grupo = construir_pares_desde(hojas_tot, padre_id, prefijo)
                    pares_tot.extend(grupo)
                    n_g = sum(1 for p in grupo if par_cambia(p))
                    self.log(f"    {prefijo}: {len(grupo)} subhojas ({n_g} cambian)", "dim")
                    self._avisar_duplicados(grupo, prefijo)
            else:
                self.log("✗ No se encontró Total Cash Management.", "err")

            if not ss_id_cash and not ss_id_ch and not ss_id_tot:
                self.status("No se encontró ningún archivo.")
                self._set_btns(btn_buscar="normal")
                return

            self._datos = {
                "ss_id_cash":    ss_id_cash,
                "ss_id_ch":      ss_id_ch,
                "ss_id_tot":     ss_id_tot,
                "pares_cge":     pares_cge,
                "pares_fr":      pares_fr,
                "subhojas_cge":  subhojas_cge,
                "subhojas_fr":   subhojas_fr,
                "pares_ch":      pares_ch,
                "pares_ch_fr":   pares_ch_fr,
                "subhojas_ch":   subhojas_ch,
                "subhojas_ch_fr":subhojas_ch_fr,
                "pares_tot":     pares_tot,
            }

            n_cge = sum(1 for p in pares_cge + pares_fr if par_cambia(p))
            n_ch  = sum(1 for p in pares_ch + pares_ch_fr if par_cambia(p))
            n_tot = sum(1 for p in pares_tot if par_cambia(p))
            self.log(f"  Cambios — CGE: {n_cge} | Chilquinta: {n_ch} | Total: {n_tot}", "ok")

            todos_pares = pares_cge + pares_fr + pares_ch + pares_ch_fr + pares_tot
            self.after(0, lambda: self._poblar_tree(todos_pares))

            self._set_btns(
                btn_buscar="normal",
                btn_renombrar="normal"     if n_cge > 0      else "disabled",
                btn_limpiar_cge="normal"   if subhojas_cge   else "disabled",
                btn_limpiar_fr="normal"    if subhojas_fr    else "disabled",
                btn_renombrar_ch="normal"  if n_ch > 0       else "disabled",
                btn_limpiar_ch="normal"    if subhojas_ch    else "disabled",
                btn_limpiar_ch_fr="normal" if subhojas_ch_fr else "disabled",
                btn_renombrar_tot="normal" if n_tot > 0      else "disabled",
            )
            self.status(f"Listo — {nom_cash or ''} {nom_ch or ''} {nom_tot or ''}")

        except Exception as e:
            self.log(f"ERROR: {e}", "err")
            self.status("Error. Revise el log.")
            self._set_btns(btn_buscar="normal")

    # ── TREE ──────────────────────────────────────────────────────────────────
    def _limpiar_tree(self):
        for item in self.tree.get_children():
            self.tree.delete(item)

    def _poblar_tree(self, todos_pares):
        self._limpiar_tree()
        for p in todos_pares:
            cambia = par_cambia(p)
            tag    = "cambia" if cambia else "igual"
            if p.actual != p.nuevo:
                marca = "✔"
            elif cambia:
                marca = "↻"          # solo se reincorpora al grupo
            else:
                marca = ""
            # El tipo es el nombre sin la fecha final (ej: "CGE S.A. 03.08" -> "CGE S.A.")
            tipo = re.sub(r"\s+(\d{2}\.\d{2}|xx\.xx\d*)$", "", p.actual, flags=re.IGNORECASE) or p.actual
            self.tree.insert("", "end", values=(tipo, p.actual, p.nuevo, marca), tags=(tag,))

    # ── RENOMBRAR ─────────────────────────────────────────────────────────────
    def _renombrar(self):
        if not self._datos:
            return
        if not messagebox.askyesno("Confirmar", "¿Renombrar hojas CGE Cash Management en Workiva?"):
            return
        self._deshabilitar_todos()
        self.status("Renombrando hojas CGE...")
        threading.Thread(target=self._renombrar_worker,
                         args=(self._datos["pares_cge"] + self._datos["pares_fr"],
                               self._datos["ss_id_cash"], "CGE"), daemon=True).start()

    def _renombrar_ch(self):
        if not self._datos:
            return
        if not messagebox.askyesno("Confirmar", "¿Renombrar hojas Chilquinta en Workiva?"):
            return
        self._deshabilitar_todos()
        self.status("Renombrando hojas Chilquinta...")
        threading.Thread(target=self._renombrar_worker,
                         args=(self._datos["pares_ch"] + self._datos["pares_ch_fr"],
                               self._datos["ss_id_ch"], "Chilquinta"), daemon=True).start()

    def _renombrar_tot(self):
        if not self._datos:
            return
        if not messagebox.askyesno("Confirmar", "¿Renombrar hojas de Total Cash Management en Workiva?"):
            return
        self._deshabilitar_todos()
        self.status("Renombrando hojas Total...")
        threading.Thread(target=self._renombrar_worker,
                         args=(self._datos["pares_tot"],
                               self._datos["ss_id_tot"], "Total"), daemon=True).start()

    def _aplicar_nombre(self, ss_id, sheet_id, nombre, pid, idx):
        """PATCH y, si falla, PUT. Devuelve (ok, detalle_del_error)."""
        body = {"name": nombre, "index": idx}
        if pid:
            body["parent"] = {"id": pid}
        st, data = api_patch(f"/platform/v1/spreadsheets/{ss_id}/sheets/{sheet_id}", body)
        if st in (200, 202, 204):
            return True, ""
        st2, data2 = api_put(f"/platform/v1/spreadsheets/{ss_id}/sheets/{sheet_id}", body)
        if st2 in (200, 202, 204):
            return True, ""
        return False, f"PATCH:{st} {data} PUT:{st2} {data2}"

    def _renombrar_worker(self, pares, ss_id, etiqueta):
        try:
            cambios = [p for p in pares if par_cambia(p)]
            if not cambios:
                self.log(f"Renombrado {etiqueta}: no hay cambios que aplicar.", "dim")
                self.status(f"{etiqueta}: sin cambios.")
                self._habilitar_todos()
                return

            # ¿Algún nombre nuevo ya lo tiene otra hoja del grupo? (ej: intercambio
            # 24.09 <-> 25.09). Workiva rechaza con 400 si el nombre está ocupado,
            # así que en ese caso hay que pasar por un nombre temporal.
            nombres_actuales = {p.actual for p in pares}
            necesita_temp = any(p.nuevo in nombres_actuales for p in cambios if p.nuevo != p.actual)

            ok = err = 0

            if necesita_temp:
                self.log("  Hay nombres cruzados: se renombra en dos pasos.", "dim")
                # Paso 1: todas a un nombre temporal único, para liberar los
                # nombres que otra hoja necesita ocupar.
                temporales = []
                for i, p in enumerate(cambios):
                    tmp = f"~tmp{i}~"
                    bien, detalle = self._aplicar_nombre(ss_id, p.sheet_id, tmp, p.parent, p.idx)
                    if bien:
                        temporales.append(p)
                    else:
                        self.log(f"  ✗ {p.actual} (paso 1) {detalle}", "err")
                        err += 1
                    time.sleep(0.25)
                # Paso 2: del temporal al nombre definitivo
                for p in temporales:
                    bien, detalle = self._aplicar_nombre(ss_id, p.sheet_id, p.nuevo, p.parent, p.idx)
                    if bien:
                        self.log(f"  ✓ {p.actual}  →  {p.nuevo}", "ok")
                        ok += 1
                    else:
                        self.log(f"  ✗ {p.actual}  →  {p.nuevo} (paso 2) {detalle}", "err")
                        err += 1
                    time.sleep(0.25)
            else:
                for p in cambios:
                    bien, detalle = self._aplicar_nombre(ss_id, p.sheet_id, p.nuevo, p.parent, p.idx)
                    if bien:
                        flecha = f"{p.actual}  →  {p.nuevo}" if p.actual != p.nuevo \
                                 else f"{p.actual}  (reincorporada al grupo)"
                        self.log(f"  ✓ {flecha}", "ok")
                        ok += 1
                    else:
                        self.log(f"  ✗ {p.actual}  →  {p.nuevo}  {detalle}", "err")
                        err += 1
                    time.sleep(0.25)

            self.log(f"Renombrado {etiqueta}: {ok} OK, {err} errores.", "ok" if err == 0 else "err")
            self.status(f"Renombrado {etiqueta}: {ok} OK, {err} errores.")
            self._habilitar_todos()
        except Exception as e:
            self.log(f"ERROR renombrar: {e}", "err")
            self.status("Error al renombrar.")
            self._set_btns(btn_buscar="normal")

    # ── LIMPIAR CGE ───────────────────────────────────────────────────────────
    def _limpiar_cge(self):
        if not self._datos or not self._datos.get("subhojas_cge"):
            return
        n = len(self._datos["subhojas_cge"])
        if not messagebox.askyesno("Confirmar", f"¿Limpiar rangos en {n} hojas CGE Cash management?"):
            return
        self._deshabilitar_todos()
        self.status("Limpiando hojas CGE...")
        threading.Thread(target=self._limpiar_worker,
                         args=(self._datos["subhojas_cge"], RANGOS_CGE,
                               self._datos["ss_id_cash"], "CGE"), daemon=True).start()

    def _limpiar_fr(self):
        if not self._datos or not self._datos.get("subhojas_fr"):
            return
        n = len(self._datos["subhojas_fr"])
        if not messagebox.askyesno("Confirmar", f"¿Limpiar rangos en {n} hojas Fund Request?"):
            return
        self._deshabilitar_todos()
        self.status("Limpiando hojas Fund Request...")
        threading.Thread(target=self._limpiar_worker,
                         args=(self._datos["subhojas_fr"], RANGOS_FR,
                               self._datos["ss_id_cash"], "Fund Request"), daemon=True).start()

    def _limpiar_ch(self):
        if not self._datos or not self._datos.get("subhojas_ch"):
            return
        n = len(self._datos["subhojas_ch"])
        if not messagebox.askyesno("Confirmar", f"¿Limpiar rangos en {n} hojas Chilquinta?"):
            return
        self._deshabilitar_todos()
        self.status("Limpiando hojas Chilquinta...")
        threading.Thread(target=self._limpiar_worker,
                         args=(self._datos["subhojas_ch"], RANGOS_CGE,
                               self._datos["ss_id_ch"], "Chilquinta"), daemon=True).start()

    def _limpiar_ch_fr(self):
        if not self._datos or not self._datos.get("subhojas_ch_fr"):
            return
        n = len(self._datos["subhojas_ch_fr"])
        if not messagebox.askyesno("Confirmar", f"¿Limpiar rangos en {n} hojas CC Funds request?"):
            return
        self._deshabilitar_todos()
        self.status("Limpiando hojas CC Funds request...")
        threading.Thread(target=self._limpiar_worker,
                         args=(self._datos["subhojas_ch_fr"], RANGOS_FR,
                               self._datos["ss_id_ch"], "CC Funds request"), daemon=True).start()

    def _limpiar_worker(self, subhojas, rangos, ss_id, etiqueta):
        try:
            ok = err = 0
            for h in subhojas:
                sheet_id = h["id"]
                nombre   = h.get("name", sheet_id)
                self.log(f"  Limpiando {nombre}...", "dim")
                for rango in rangos:
                    vals = vacias(rango)
                    st, _ = api_put(
                        f"/platform/v1/spreadsheets/{ss_id}/sheets/{sheet_id}/values/{rango}",
                        {"values": vals}
                    )
                    if st in (200, 202, 204):
                        ok += 1
                    else:
                        self.log(f"    ✗ {nombre} {rango}: ERR {st}", "err")
                        err += 1
                    time.sleep(0.1)
            self.log(f"Limpieza {etiqueta}: {ok} OK, {err} errores.", "ok" if err == 0 else "err")
            self.status(f"Limpieza {etiqueta}: {ok} OK, {err} errores.")
            self._habilitar_todos()
        except Exception as e:
            self.log(f"ERROR limpiar: {e}", "err")
            self.status("Error al limpiar.")
            self._set_btns(btn_buscar="normal")

    def _avisar_duplicados(self, pares, etiqueta):
        """Avisa en el log si el renombrado dejaría dos hojas con el mismo nombre."""
        vistos, repetidos = set(), set()
        for p in pares:
            if p.nuevo in vistos:
                repetidos.add(p.nuevo)
            vistos.add(p.nuevo)
        if repetidos:
            self.log(f"    ⚠ {etiqueta}: nombres duplicados → {', '.join(sorted(repetidos))}", "err")

    def _deshabilitar_todos(self):
        self._set_btns(btn_buscar="disabled", btn_renombrar="disabled",
                       btn_limpiar_cge="disabled", btn_limpiar_fr="disabled",
                       btn_renombrar_ch="disabled", btn_limpiar_ch="disabled",
                       btn_limpiar_ch_fr="disabled", btn_renombrar_tot="disabled")

    def _habilitar_todos(self):
        d = self._datos
        self._set_btns(
            btn_buscar="normal",
            btn_renombrar="normal"     if any(par_cambia(p) for p in d.get("pares_cge",[]) + d.get("pares_fr",[]))    else "disabled",
            btn_limpiar_cge="normal"   if d.get("subhojas_cge")   else "disabled",
            btn_limpiar_fr="normal"    if d.get("subhojas_fr")    else "disabled",
            btn_renombrar_ch="normal"  if any(par_cambia(p) for p in d.get("pares_ch",[]) + d.get("pares_ch_fr",[]))  else "disabled",
            btn_limpiar_ch="normal"    if d.get("subhojas_ch")    else "disabled",
            btn_limpiar_ch_fr="normal" if d.get("subhojas_ch_fr") else "disabled",
            btn_renombrar_tot="normal" if any(par_cambia(p) for p in d.get("pares_tot",[]))                           else "disabled",
        )

# ── ENTRY POINT ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    app = App()
    app.mainloop()
