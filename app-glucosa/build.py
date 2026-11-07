"""Genera las versiones instalables de Diario de Glucosa a partir de app.html.

app.html es la fuente única de la app. Se publica tal cual como Artifact en
claude.ai (que le agrega su propio <head>). Este script la envuelve en un
documento completo para:

  * index.html                      PWA para hosting estático (GitHub Pages, etc.)
  * android/app/src/main/assets/www App Android (APK), con fuentes locales

Uso:  python build.py
Luego, para el APK:  cd android && gradle assembleRelease
"""
import re
import shutil
from pathlib import Path

HERE = Path(__file__).resolve().parent
SRC = HERE / "app.html"
OUT_PWA = HERE / "index.html"
FONTS = HERE / "fonts"
OUT_ANDROID = HERE / "android" / "app" / "src" / "main" / "assets" / "www"

RESET = ("<style>:root{color-scheme:light;padding-top:env(safe-area-inset-top,0px);"
         "padding-bottom:env(safe-area-inset-bottom,0px)}body{margin:0;font:14px system-ui,-apple-system,sans-serif}"
         "img{max-width:100%}[hidden]{display:none!important}</style>")

PWA_HEAD = """<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<title>{title}</title>
<meta name="description" content="Registro personal de glucosa capilar: promedio, HbA1c estimada, tiempo en objetivo y tendencias.">
<meta name="theme-color" content="#F3F5F9" media="(prefers-color-scheme: light)">
<meta name="theme-color" content="#0D1020" media="(prefers-color-scheme: dark)">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="default">
<meta name="apple-mobile-web-app-title" content="Glucosa">
<link rel="manifest" href="manifest.webmanifest">
<link rel="icon" href="icon.svg" type="image/svg+xml">
<link rel="apple-touch-icon" href="icon-180.png">
{reset}
</head>
<body>
"""

PWA_TAIL = """
<script>
if ('serviceWorker' in navigator) {
  addEventListener('load', () => navigator.serviceWorker.register('sw.js').catch(() => {}));
}
</script>
</body>
</html>
"""

ANDROID_HEAD = """<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<title>{title}</title>
<link rel="stylesheet" href="fonts/fonts.css">
{reset}
</head>
<body>
"""


def split_source():
    src = SRC.read_text(encoding="utf-8")
    m = re.search(r"<title>(.*?)</title>\s*", src, re.S)
    title = m.group(1).strip() if m else "Diario de Glucosa"
    body = src.replace(m.group(0), "", 1) if m else src
    body = re.sub(r'<meta name="claude:[^"]+"[^>]*>\s*', "", body)
    return title, body


def build_pwa(title, body):
    OUT_PWA.write_text(PWA_HEAD.format(title=title, reset=RESET) + body.rstrip() + "\n" + PWA_TAIL, encoding="utf-8")
    print(f"OK -> {OUT_PWA.relative_to(HERE)} ({OUT_PWA.stat().st_size // 1024} KB)")


def build_android(title, body):
    # Sin conexión: fuentes locales en vez de Google Fonts, y sin service worker.
    body = re.sub(r'<link rel="preconnect"[^>]*>\s*', "", body)
    body = re.sub(r'<link rel="stylesheet" href="https://fonts\.googleapis\.com[^>]*>\s*', "", body)
    OUT_ANDROID.mkdir(parents=True, exist_ok=True)
    out = OUT_ANDROID / "index.html"
    out.write_text(ANDROID_HEAD.format(title=title, reset=RESET) + body.rstrip() + "\n</body>\n</html>\n", encoding="utf-8")
    dst_fonts = OUT_ANDROID / "fonts"
    if dst_fonts.exists():
        shutil.rmtree(dst_fonts)
    shutil.copytree(FONTS, dst_fonts)
    print(f"OK -> {out.relative_to(HERE)} ({out.stat().st_size // 1024} KB) + fuentes")


def main():
    title, body = split_source()
    build_pwa(title, body)
    build_android(title, body)


if __name__ == "__main__":
    main()
