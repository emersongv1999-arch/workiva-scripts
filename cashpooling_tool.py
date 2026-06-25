"""
cashpooling_tool.py
Herramienta GUI para renombrar hojas y limpiar rangos en Workiva.
"""

import json, re, ssl, time, threading, datetime
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

# ── VENTANA PRINCIPAL ─────────────────────────────────────────────────────────
class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("CGE Cash Management Tool")
        self.configure(bg=BG)
        self.resizable(False, False)
        self._datos = {}   # resultado del paso "Buscar"

        self._build_ui()
        self._center()

    def _center(self):
        self.update_idletasks()
        w, h = self.winfo_width(), self.winfo_height()
        x = (self.winfo_screenwidth()  - w) // 2
        y = (self.winfo_screenheight() - h) // 2
        self.geometry(f"{w}x{h}+{x}+{y}")

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
        self.tree.column("tipo",   width=160, anchor="w")
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

        self.btn_renombrar = self._btn(af, "Renombrar hojas",        BTN_GREEN, self._renombrar, state="disabled")
        self.btn_renombrar.pack(side="left", padx=(0,8), ipady=5, ipadx=8)

        self.btn_limpiar_cge = self._btn(af, "Limpiar CGE Cash mgmt", BTN_BLUE, self._limpiar_cge, state="disabled")
        self.btn_limpiar_cge.pack(side="left", padx=(0,8), ipady=5, ipadx=8)

        self.btn_limpiar_fr = self._btn(af, "Limpiar Fund Request",   BTN_BLUE, self._limpiar_fr,  state="disabled")
        self.btn_limpiar_fr.pack(side="left", padx=(0,8), ipady=5, ipadx=8)

        # ── Log ───────────────────────────────────────────────────────────────
        lf = tk.Frame(self, bg=BG, padx=16, pady=(0,14))
        lf.pack(fill="both", expand=True)

        tk.Label(lf, text="Log", font=("Segoe UI", 9, "bold"),
                 bg=BG, fg=FG_DIM).pack(anchor="w")

        self.log_txt = tk.Text(lf, height=9, bg="#0d0d1a", fg=FG,
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

    def _btn(self, parent, text, color, cmd, state="normal"):
        b = tk.Button(parent, text=text, bg=color, fg=FG,
                      font=("Segoe UI", 9, "bold"), relief="flat",
                      activebackground=color, activeforeground=FG,
                      cursor="hand2", command=cmd, state=state,
                      disabledforeground="#666")
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

            # Cash management
            patron_cash = f"{mes} CGE Cash management"
            ss_id_cash, nom_cash = buscar_spreadsheet(patron_cash, self.log)
            if not ss_id_cash:
                self.log("✗ No se encontró el archivo CGE Cash management.", "err")
                self.status("No encontrado.")
                self._set_btns(btn_buscar="normal")
                return

            hojas_cash = listar_hojas(ss_id_cash)
            self.log(f"  {len(hojas_cash)} hojas en total")

            pat_cge = re.compile(r"^CGE Cash management \d{2}\.\d{2}$")
            pat_fr  = re.compile(r"^Fund Request \d{2}\.\d{2}$")

            summary_id = None
            fundreq_id = None
            for h in hojas_cash:
                nombre = h.get("name", "").strip()
                if nombre == "CGE Cash management - Summary":
                    summary_id = h["id"]
                elif nombre == "Fund Request":
                    fundreq_id = h["id"]

            def construir_pares(parent_id, patron, prefijo):
                hijos = [h for h in hojas_cash
                         if (h.get("parentId") or (h.get("parent") or {}).get("id","")) == parent_id
                         and patron.match(h.get("name",""))]
                hijos.sort(key=lambda h: h.get("name",""))
                pares = []
                for i, h in enumerate(hijos):
                    actual = h.get("name","")
                    nuevo  = f"{prefijo} {bases[i]}" if i < len(bases) and bases[i] else actual
                    pid_h  = h.get("parentId") or (h.get("parent") or {}).get("id","")
                    idx    = h.get("index") or h.get("position") or i
                    pares.append((h["id"], actual, nuevo, pid_h, idx))
                return pares

            pares_cge = construir_pares(summary_id, pat_cge, "CGE Cash management") if summary_id else []
            pares_fr  = construir_pares(fundreq_id,  pat_fr,  "Fund Request")        if fundreq_id  else []

            subhojas_cge = [h for h in hojas_cash
                            if (h.get("parentId") or (h.get("parent") or {}).get("id","")) == summary_id
                            and pat_cge.match(h.get("name",""))]
            subhojas_cge.sort(key=lambda h: h.get("name",""))

            subhojas_fr = [h for h in hojas_cash
                           if (h.get("parentId") or (h.get("parent") or {}).get("id","")) == fundreq_id
                           and pat_fr.match(h.get("name",""))]
            subhojas_fr.sort(key=lambda h: h.get("name",""))

            self._datos = {
                "ss_id_cash":   ss_id_cash,
                "pares_cge":    pares_cge,
                "pares_fr":     pares_fr,
                "subhojas_cge": subhojas_cge,
                "subhojas_fr":  subhojas_fr,
            }

            n_cambios = sum(1 for _, a, n, _, _ in pares_cge + pares_fr if a != n)
            self.log(f"  CGE Cash mgmt: {len(pares_cge)} subhojas  |  Fund Request: {len(pares_fr)} subhojas", "dim")
            self.log(f"  Cambios de nombre pendientes: {n_cambios}", "ok" if n_cambios > 0 else "dim")

            self.after(0, lambda: self._poblar_tree(pares_cge, pares_fr))

            self._set_btns(btn_buscar="normal",
                           btn_renombrar="normal" if n_cambios > 0 else "disabled",
                           btn_limpiar_cge="normal" if subhojas_cge else "disabled",
                           btn_limpiar_fr="normal"  if subhojas_fr  else "disabled")
            self.status(f"Listo — {nom_cash}")

        except Exception as e:
            self.log(f"ERROR: {e}", "err")
            self.status("Error. Revise el log.")
            self._set_btns(btn_buscar="normal")

    # ── TREE ──────────────────────────────────────────────────────────────────
    def _limpiar_tree(self):
        for item in self.tree.get_children():
            self.tree.delete(item)

    def _poblar_tree(self, pares_cge, pares_fr):
        self._limpiar_tree()
        for sid, actual, nuevo, pid, idx in pares_cge:
            tag = "cambia" if actual != nuevo else "igual"
            marca = "✔" if actual != nuevo else ""
            self.tree.insert("", "end", values=("CGE Cash mgmt", actual, nuevo, marca), tags=(tag,))
        for sid, actual, nuevo, pid, idx in pares_fr:
            tag = "cambia" if actual != nuevo else "igual"
            marca = "✔" if actual != nuevo else ""
            self.tree.insert("", "end", values=("Fund Request", actual, nuevo, marca), tags=(tag,))

    # ── RENOMBRAR ─────────────────────────────────────────────────────────────
    def _renombrar(self):
        if not self._datos:
            return
        if not messagebox.askyesno("Confirmar", "¿Aplicar renombrado de hojas en Workiva?"):
            return
        self._set_btns(btn_renombrar="disabled", btn_buscar="disabled",
                       btn_limpiar_cge="disabled", btn_limpiar_fr="disabled")
        self.status("Renombrando hojas...")
        threading.Thread(target=self._renombrar_worker, daemon=True).start()

    def _renombrar_worker(self):
        try:
            d = self._datos
            todos = d["pares_cge"] + d["pares_fr"]
            ok = err = 0
            for sheet_id, actual, nuevo, pid, idx in todos:
                if actual == nuevo:
                    continue
                body = {"name": nuevo, "index": idx}
                if pid:
                    body["parent"] = {"id": pid}
                st, data = api_patch(f"/platform/v1/spreadsheets/{d['ss_id_cash']}/sheets/{sheet_id}", body)
                if st in (200, 202, 204):
                    self.log(f"  ✓ {actual}  →  {nuevo}", "ok")
                    ok += 1
                else:
                    st2, data2 = api_put(f"/platform/v1/spreadsheets/{d['ss_id_cash']}/sheets/{sheet_id}", body)
                    if st2 in (200, 202, 204):
                        self.log(f"  ✓ {actual}  →  {nuevo}  (PUT)", "ok")
                        ok += 1
                    else:
                        self.log(f"  ✗ {actual}  PATCH:{st} PUT:{st2}", "err")
                        err += 1
                time.sleep(0.25)
            self.log(f"Renombrado completado: {ok} OK, {err} errores.", "ok" if err == 0 else "err")
            self.status(f"Renombrado: {ok} OK, {err} errores.")
            self._set_btns(btn_buscar="normal",
                           btn_limpiar_cge="normal" if d["subhojas_cge"] else "disabled",
                           btn_limpiar_fr="normal"  if d["subhojas_fr"]  else "disabled")
        except Exception as e:
            self.log(f"ERROR renombrar: {e}", "err")
            self.status("Error al renombrar.")
            self._set_btns(btn_buscar="normal", btn_renombrar="normal")

    # ── LIMPIAR CGE ───────────────────────────────────────────────────────────
    def _limpiar_cge(self):
        if not self._datos or not self._datos.get("subhojas_cge"):
            return
        n = len(self._datos["subhojas_cge"])
        if not messagebox.askyesno("Confirmar", f"¿Limpiar rangos en {n} hojas CGE Cash management?"):
            return
        self._set_btns(btn_buscar="disabled", btn_renombrar="disabled",
                       btn_limpiar_cge="disabled", btn_limpiar_fr="disabled")
        self.status("Limpiando hojas CGE...")
        threading.Thread(target=self._limpiar_worker,
                         args=(self._datos["subhojas_cge"], RANGOS_CGE, "CGE"), daemon=True).start()

    # ── LIMPIAR FR ────────────────────────────────────────────────────────────
    def _limpiar_fr(self):
        if not self._datos or not self._datos.get("subhojas_fr"):
            return
        n = len(self._datos["subhojas_fr"])
        if not messagebox.askyesno("Confirmar", f"¿Limpiar rangos en {n} hojas Fund Request?"):
            return
        self._set_btns(btn_buscar="disabled", btn_renombrar="disabled",
                       btn_limpiar_cge="disabled", btn_limpiar_fr="disabled")
        self.status("Limpiando hojas Fund Request...")
        threading.Thread(target=self._limpiar_worker,
                         args=(self._datos["subhojas_fr"], RANGOS_FR, "Fund Request"), daemon=True).start()

    def _limpiar_worker(self, subhojas, rangos, etiqueta):
        try:
            d = self._datos
            ok = err = 0
            for h in subhojas:
                sheet_id = h["id"]
                nombre   = h.get("name", sheet_id)
                self.log(f"  Limpiando {nombre}...", "dim")
                for rango in rangos:
                    vals = vacias(rango)
                    st, _ = api_put(
                        f"/platform/v1/spreadsheets/{d['ss_id_cash']}/sheets/{sheet_id}/values/{rango}",
                        {"values": vals}
                    )
                    if st in (200, 202, 204):
                        ok += 1
                    else:
                        self.log(f"    ✗ {nombre} {rango}: ERR {st}", "err")
                        err += 1
                    time.sleep(0.1)
            self.log(f"Limpieza {etiqueta} completada: {ok} OK, {err} errores.", "ok" if err == 0 else "err")
            self.status(f"Limpieza {etiqueta}: {ok} OK, {err} errores.")
            self._set_btns(btn_buscar="normal",
                           btn_limpiar_cge="normal" if d["subhojas_cge"] else "disabled",
                           btn_limpiar_fr="normal"  if d["subhojas_fr"]  else "disabled")
        except Exception as e:
            self.log(f"ERROR limpiar: {e}", "err")
            self.status("Error al limpiar.")
            self._set_btns(btn_buscar="normal")

# ── ENTRY POINT ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    app = App()
    app.mainloop()
