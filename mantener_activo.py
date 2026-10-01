"""
Mantener Activo — evita que el PC entre en suspensión mientras está abierto.

Usa la API oficial de Windows SetThreadExecutionState (la misma que usan
reproductores de video o PowerToys Awake). No mueve el mouse ni simula teclas.

Compilar:
    pyinstaller --onefile --windowed --name MantenerActivo mantener_activo.py
"""

import ctypes
import sys
import time
import tkinter as tk
from tkinter import ttk, messagebox

ES_CONTINUOUS = 0x80000000
ES_SYSTEM_REQUIRED = 0x00000001
ES_DISPLAY_REQUIRED = 0x00000002

REFRESCO_MS = 30_000  # re-afirma el estado cada 30 s

DURACIONES = {
    "Indefinido": None,
    "30 minutos": 30 * 60,
    "1 hora": 60 * 60,
    "2 horas": 2 * 60 * 60,
    "4 horas": 4 * 60 * 60,
    "8 horas": 8 * 60 * 60,
}


def _set_state(flags):
    return ctypes.windll.kernel32.SetThreadExecutionState(flags)


class MantenerActivoApp:
    def __init__(self, root):
        self.root = root
        self.activo = False
        self.inicio = None
        self.fin = None
        self._after_refresco = None

        root.title("Mantener Activo")
        root.resizable(False, False)
        root.protocol("WM_DELETE_WINDOW", self.cerrar)

        frm = ttk.Frame(root, padding=14)
        frm.grid()

        self.lbl_estado = ttk.Label(frm, font=("Segoe UI", 12, "bold"))
        self.lbl_estado.grid(row=0, column=0, columnspan=2, sticky="w")

        self.lbl_tiempo = ttk.Label(frm, foreground="#555")
        self.lbl_tiempo.grid(row=1, column=0, columnspan=2, sticky="w", pady=(2, 10))

        self.var_pantalla = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            frm, text="Mantener pantalla encendida",
            variable=self.var_pantalla, command=self._aplicar,
        ).grid(row=2, column=0, columnspan=2, sticky="w")

        ttk.Label(frm, text="Duración:").grid(row=3, column=0, sticky="w", pady=(8, 0))
        self.var_duracion = tk.StringVar(value="Indefinido")
        cmb = ttk.Combobox(
            frm, textvariable=self.var_duracion, values=list(DURACIONES),
            state="readonly", width=14,
        )
        cmb.grid(row=3, column=1, sticky="e", pady=(8, 0))
        cmb.bind("<<ComboboxSelected>>", lambda e: self._reiniciar_duracion())

        self.btn = ttk.Button(frm, command=self.alternar, width=24)
        self.btn.grid(row=4, column=0, columnspan=2, pady=(12, 0))

        ttk.Label(
            frm, text="Puedes minimizar esta ventana; sigue funcionando.",
            foreground="#888", font=("Segoe UI", 8),
        ).grid(row=5, column=0, columnspan=2, pady=(8, 0))

        self.activar()
        self._tick()

    # ── Estado ────────────────────────────────────────────────────────────────
    def _aplicar(self):
        if not self.activo:
            return
        flags = ES_CONTINUOUS | ES_SYSTEM_REQUIRED
        if self.var_pantalla.get():
            flags |= ES_DISPLAY_REQUIRED
        if not _set_state(flags):
            messagebox.showerror("Mantener Activo", "Windows rechazó la solicitud.")
            self.detener()

    def _refrescar(self):
        self._aplicar()
        self._after_refresco = self.root.after(REFRESCO_MS, self._refrescar)

    def _reiniciar_duracion(self):
        segundos = DURACIONES[self.var_duracion.get()]
        self.fin = time.time() + segundos if (self.activo and segundos) else None

    def activar(self):
        self.activo = True
        self.inicio = time.time()
        self._reiniciar_duracion()
        self._refrescar()
        self._actualizar_ui()

    def detener(self):
        self.activo = False
        self.inicio = self.fin = None
        if self._after_refresco:
            self.root.after_cancel(self._after_refresco)
            self._after_refresco = None
        _set_state(ES_CONTINUOUS)  # devuelve el control normal a Windows
        self._actualizar_ui()

    def alternar(self):
        self.detener() if self.activo else self.activar()

    # ── UI ────────────────────────────────────────────────────────────────────
    def _actualizar_ui(self):
        if self.activo:
            self.lbl_estado.config(text="● Activo — el PC no se suspenderá", foreground="#1a7f37")
            self.btn.config(text="Detener")
        else:
            self.lbl_estado.config(text="○ Detenido — comportamiento normal", foreground="#b42318")
            self.btn.config(text="Activar")
            self.lbl_tiempo.config(text="")

    def _tick(self):
        if self.activo:
            ahora = time.time()
            if self.fin and ahora >= self.fin:
                self.detener()
            else:
                txt = f"Activo hace {_fmt(ahora - self.inicio)}"
                if self.fin:
                    txt += f"  ·  se detiene en {_fmt(self.fin - ahora)}"
                self.lbl_tiempo.config(text=txt)
        self.root.after(1000, self._tick)

    def cerrar(self):
        self.detener()
        self.root.destroy()


def _fmt(segundos):
    s = int(segundos)
    return f"{s // 3600:02d}:{s % 3600 // 60:02d}:{s % 60:02d}"


def main():
    if sys.platform != "win32":
        print("Esta aplicación solo funciona en Windows.")
        sys.exit(1)
    root = tk.Tk()
    MantenerActivoApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
