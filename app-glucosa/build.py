"""Genera index.html (PWA instalable) a partir de app.html.

app.html es la fuente única de la app. Se publica tal cual como Artifact en
claude.ai (que le agrega su propio <head>), y este script la envuelve en un
documento completo con manifest, íconos y service worker para instalarla en
el teléfono desde cualquier hosting estático (por ejemplo GitHub Pages).

Uso:  python build.py
"""
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
SRC = HERE / "app.html"
OUT = HERE / "index.html"

HEAD = """<!doctype html>
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
<style>:root{{color-scheme:light;padding-top:env(safe-area-inset-top,0px);padding-bottom:env(safe-area-inset-bottom,0px)}}body{{margin:0;font:14px system-ui,-apple-system,sans-serif}}img{{max-width:100%}}[hidden]{{display:none!important}}</style>
</head>
<body>
"""

TAIL = """
<script>
if ('serviceWorker' in navigator) {
  addEventListener('load', () => navigator.serviceWorker.register('sw.js').catch(() => {}));
}
</script>
</body>
</html>
"""


def main():
    src = SRC.read_text(encoding="utf-8")
    m = re.search(r"<title>(.*?)</title>\s*", src, re.S)
    title = m.group(1).strip() if m else "Diario de Glucosa"
    body = src
    if m:
        body = body.replace(m.group(0), "", 1)
    body = re.sub(r'<meta name="claude:[^"]+"[^>]*>\s*', "", body)
    OUT.write_text(HEAD.format(title=title) + body.rstrip() + "\n" + TAIL, encoding="utf-8")
    print(f"OK -> {OUT.name} ({OUT.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main()
