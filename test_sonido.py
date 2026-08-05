#!/usr/bin/env python3
"""
test_sonido.py — Diagnostico del aviso sonoro del Auditor.

Prueba, una por una, todas las formas de emitir sonido que usa la app y
reporta cual funciona. Correr con:

    py test_sonido.py

Escuchar despues de cada prueba y anotar cual se oyo.
"""
import io
import math
import struct
import sys
import time
import wave

print("=" * 60)
print("  Diagnostico de sonido — Auditor CGE")
print("=" * 60)
print(f"Python  : {sys.version.split()[0]}")
print(f"Platform: {sys.platform}")
print(f"Frozen  : {getattr(sys, 'frozen', False)}  (True si es un .exe)")
print()

# ── 1. Importar winsound ──────────────────────────────────────────────────
try:
    import winsound
    print("[1] import winsound ............ OK")
except Exception as e:
    winsound = None
    print(f"[1] import winsound ............ FALLO: {type(e).__name__}: {e}")
    print()
    print(">>> Sin winsound no hay sonido posible por esta via.")
    print(">>> Si esto pasa en el .exe pero no en python suelto,")
    print(">>> el problema es que PyInstaller no lo empaqueto.")
    sys.exit(1)

print()


def probar(nombre, fn):
    """Ejecuta una prueba de sonido y reporta el resultado."""
    print(f"--- {nombre} ---")
    try:
        t0 = time.time()
        fn()
        dt = time.time() - t0
        print(f"    Ejecutado sin error (tardo {dt:.2f}s)")
        print(f"    >>> Se escucho algo? (anotar)")
    except Exception as e:
        print(f"    FALLO: {type(e).__name__}: {e}")
    print()
    time.sleep(1.2)


# ── 2. WAV en memoria (metodo principal de la app) ────────────────────────
def _wav_aviso(tonos=((880, 0.16), (1175, 0.24)), fr=44100, vol=0.45):
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(fr)
        frames = bytearray()
        for freq, dur in tonos:
            n = int(fr * dur)
            for i in range(n):
                env = min(1.0, i / 400.0, (n - i) / 400.0)
                frames += struct.pack(
                    "<h", int(32767 * vol * env * math.sin(2 * math.pi * freq * i / fr)))
        w.writeframes(bytes(frames))
    return buf.getvalue()


try:
    wav = _wav_aviso()
    print(f"[2] WAV generado en memoria .... OK ({len(wav)} bytes)")
except Exception as e:
    wav = None
    print(f"[2] WAV generado en memoria .... FALLO: {type(e).__name__}: {e}")
print()

if wav:
    probar("A) PlaySound(SND_MEMORY)  <-- metodo principal de la app",
           lambda: winsound.PlaySound(wav, winsound.SND_MEMORY))

probar("B) Beep(880, 400)",
       lambda: winsound.Beep(880, 400))

probar("C) MessageBeep(MB_ICONASTERISK)",
       lambda: winsound.MessageBeep(winsound.MB_ICONASTERISK))

probar("D) MessageBeep(MB_OK)",
       lambda: winsound.MessageBeep(winsound.MB_OK))

probar("E) PlaySound('SystemExclamation', SND_ALIAS)",
       lambda: winsound.PlaySound("SystemExclamation", winsound.SND_ALIAS))

# ── 3. Campana de tkinter ─────────────────────────────────────────────────
try:
    import tkinter as tk
    root = tk.Tk()
    root.withdraw()
    probar("F) tkinter bell()", lambda: (root.bell(), root.update()))
    root.destroy()
except Exception as e:
    print(f"[F] tkinter bell .............. FALLO: {type(e).__name__}: {e}")
    print()

print("=" * 60)
print("  RESULTADO")
print("=" * 60)
print("Anotar cuales se escucharon (A, B, C, D, E, F) y cuales no.")
print()
print("Si NINGUNA se escucho pero tampoco hubo errores:")
print("  -> el audio no llega desde esta sesion (tipico en RDP/VDI sin")
print("     redireccion de audio). El aviso visual es la alternativa.")
print()
print("Si alguna se escucho:")
print("  -> avisar cual, y la app se cambia a ese metodo.")
print("=" * 60)
