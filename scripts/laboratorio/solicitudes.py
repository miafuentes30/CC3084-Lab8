"""Peticiones de lectura con reintentos ante errores transitorios."""

import time
import requests
from .parametros import INTENTOS, TIEMPO_ESPERA

ESTADOS_TRANSITORIOS = (429, 500, 502, 503, 504)


def solicitar(metodo, url, cliente=requests, **opciones):
    opciones.setdefault("timeout", TIEMPO_ESPERA)
    for intento in range(INTENTOS):
        respuesta = None
        try:
            respuesta = getattr(cliente, metodo.lower())(url, **opciones)
            if respuesta.status_code in ESTADOS_TRANSITORIOS:
                respuesta.raise_for_status()
            return respuesta
        except requests.RequestException:
            if respuesta is not None:
                respuesta.close()
            if intento + 1 == INTENTOS:
                raise
            time.sleep(0.25 * 2 ** intento)
