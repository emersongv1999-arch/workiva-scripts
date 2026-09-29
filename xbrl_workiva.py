#!/usr/bin/env python3
"""Conexion con Workiva para el llenado XBRL.

Busca las planillas "E___ XBRL MM-AAAA" y las descarga como .xlsx: el mismo
archivo que sale al exportarlas a mano desde Workiva, asi que el llenado no
cambia en nada, solo deja de depender de que alguien haga el export.

Sin dependencias fuera de la libreria estandar, igual que el Auditor.
"""

import json
import re
import ssl
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

# ── CREDENCIALES (las mismas del Auditor) ─────────────────────────────────────
CLIENT_ID     = "db2c551e-e18a-417e-8e52-d182716b8ef2"
CLIENT_SECRET = "wk_secret:oa2c:DzlUCmBQDv6raPxG09me"

TOKEN_URL = "https://api.app.wdesk.com/iam/v1/oauth2/token"
API       = "https://api.app.wdesk.com/platform/v1"
VERSION   = "2022-01-01"

# La red de CGE inspecciona SSL: igual que el Auditor, sin verificar
# certificados, o ninguna llamada pasa del proxy.
CTX = ssl.create_default_context()
CTX.check_hostname = False
CTX.verify_mode = ssl.CERT_NONE

# "E211 XBRL 06-2026". La empresa sale del nombre, asi que una empresa nueva
# aparece sola en cuanto alguien crea su planilla en Workiva.
PATRON = re.compile(r"^\s*(E\d+)\s+XBRL\s+(\d{1,2})-(\d{4})\s*$", re.IGNORECASE)


class ErrorWorkiva(RuntimeError):
    """Un problema con Workiva, con un mensaje que se puede mostrar tal cual."""


@dataclass
class Planilla:
    empresa: str
    mes: int
    anio: int
    nombre: str
    id: str
    modificada: str = ""        # ISO 8601 en UTC, como lo entrega Workiva

    @property
    def periodo(self):
        return f"{self.mes:02d}-{self.anio}"

    @property
    def orden(self):
        return (self.anio, self.mes)

    def modificada_local(self):
        """La fecha de modificacion en la hora de este computador."""
        if not self.modificada:
            return None
        try:
            f = datetime.fromisoformat(self.modificada.replace("Z", "+00:00"))
        except ValueError:
            return None
        if f.tzinfo is None:
            f = f.replace(tzinfo=timezone.utc)
        return f.astimezone()


class Workiva:
    def __init__(self):
        self._token = None
        self._vence = 0

    # ------------------------------------------------------------ http
    def _llama(self, metodo, url, cuerpo=None, cabeceras=None, bruto=False,
               espera=60):
        datos = json.dumps(cuerpo).encode() if cuerpo is not None else None
        cab = {"User-Agent": "XBRL-DBNeT/1.0", **(cabeceras or {})}
        if datos is not None:
            cab["Content-Type"] = "application/json"
        ultimo = None
        for intento in range(4):
            req = urllib.request.Request(url, data=datos, headers=cab, method=metodo)
            try:
                with urllib.request.urlopen(req, context=CTX, timeout=espera) as r:
                    contenido = r.read()
                    if bruto:
                        return r.status, r.headers, contenido
                    return r.status, r.headers, json.loads(contenido) if contenido else {}
            except urllib.error.HTTPError as e:
                if e.code in (429, 500, 502, 503, 504) and intento < 3:
                    ultimo = e
                    time.sleep(2 ** intento)
                    continue
                texto = e.read()[:500].decode("utf-8", "replace")
                if e.code == 401:
                    raise ErrorWorkiva(
                        "Workiva rechazo las credenciales de la aplicacion.") from e
                if e.code == 403:
                    raise ErrorWorkiva(
                        "Workiva no da permiso para esta planilla a la aplicacion.") from e
                raise ErrorWorkiva(f"Workiva respondio {e.code}: {texto}") from e
            except (urllib.error.URLError, TimeoutError, OSError) as e:
                ultimo = e
                time.sleep(2 ** intento)
        raise ErrorWorkiva(
            "No se pudo conectar con Workiva. Revisa que tengas internet "
            f"(o la VPN) y vuelve a intentar.\n\nDetalle: {ultimo}")

    def _autoriza(self):
        if self._token and time.time() < self._vence:
            return self._token
        _, _, datos = self._llama("POST", TOKEN_URL, {
            "grant_type": "client_credentials",
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
        })
        self._token = datos["access_token"]
        self._vence = time.time() + datos.get("expires_in", 3600) - 60
        return self._token

    def _api(self, metodo, url, cuerpo=None, bruto=False, espera=60):
        if url.startswith("/"):
            url = API + url
        return self._llama(metodo, url, cuerpo, bruto=bruto, espera=espera,
                           cabeceras={"Authorization": f"Bearer {self._autoriza()}",
                                      "X-Version": VERSION})

    # ------------------------------------------------------------ planillas
    def planillas(self):
        """Todas las planillas XBRL de todas las empresas.

        La API no deja filtrar por nombre, asi que hay que recorrer todas las
        planillas del workspace (unas 3.400, ~20 segundos) y quedarse con las
        que calzan con el patron."""
        encontradas = []
        url = "/spreadsheets?$top=1000"
        while url:
            _, _, datos = self._api("GET", url)
            for s in datos.get("data", datos.get("value", [])):
                m = PATRON.match(s.get("name", ""))
                if not m:
                    continue
                mod = s.get("modified")
                if isinstance(mod, dict):
                    mod = mod.get("dateTime", "")
                encontradas.append(Planilla(
                    empresa=m.group(1).upper(), mes=int(m.group(2)),
                    anio=int(m.group(3)), nombre=s["name"].strip(),
                    id=s["id"], modificada=mod or ""))
            url = datos.get("@nextLink") or datos.get("nextLink")
        encontradas.sort(key=lambda p: (p.empresa, p.orden), reverse=True)
        return encontradas

    def descarga(self, planilla, destino):
        """Exporta la planilla a .xlsx y la deja en destino."""
        estado, cab, _ = self._api(
            "POST", f"/spreadsheets/{planilla.id}/export", {"format": "xlsx"})
        operacion = cab.get("Location")
        if estado != 202 or not operacion:
            raise ErrorWorkiva(f"Workiva no acepto exportar '{planilla.nombre}' "
                               f"(respuesta {estado}).")
        limite = time.time() + 600
        while True:
            time.sleep(3)
            _, _, op = self._api("GET", operacion)
            s = str(op.get("status", "")).lower()
            if s == "completed":
                break
            if s in ("failed", "cancelled"):
                raise ErrorWorkiva(f"Workiva no pudo exportar '{planilla.nombre}': "
                                   f"{op.get('error') or s}")
            if time.time() > limite:
                raise ErrorWorkiva(f"Workiva lleva 10 minutos exportando "
                                   f"'{planilla.nombre}' y no termina.")
        _, _, contenido = self._api("GET", op["resourceUrl"], bruto=True, espera=300)

        destino = Path(destino)
        destino.parent.mkdir(parents=True, exist_ok=True)
        temporal = destino.with_name(destino.name + ".tmp")
        temporal.write_bytes(contenido)
        try:
            temporal.replace(destino)
        except PermissionError:
            temporal.unlink(missing_ok=True)
            raise ErrorWorkiva(
                f"{destino.name} esta abierto en Excel. Cierralo y vuelve a "
                "intentar: cada llenado lo reemplaza con lo que hay hoy en Workiva.")
        return destino


if __name__ == "__main__":
    import sys
    w = Workiva()
    lista = w.planillas()
    for p in lista:
        print(f"{p.empresa:6} {p.periodo}  {p.nombre:30} {p.modificada}")
    if len(sys.argv) == 3:
        elegida = next(p for p in lista if p.nombre == sys.argv[1])
        print(w.descarga(elegida, sys.argv[2]))
