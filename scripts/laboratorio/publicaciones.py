"""Inventario independiente de enlaces de la pagina oficial TLC."""

from html.parser import HTMLParser
from pathlib import PurePosixPath
from urllib.parse import urlparse
import re
import requests
from .parametros import PAGINA_TLC
from .solicitudes import solicitar


class EnlacesTLC(HTMLParser):
    def __init__(self):
        super().__init__()
        self.enlaces = set()

    def handle_starttag(self, tag, attrs):
        if tag.lower() == "a":
            for nombre, valor in attrs:
                if nombre.lower() == "href" and valor:
                    self.enlaces.add(valor.strip())


def publicados(anios, cliente=requests):
    respuesta = solicitar("GET", PAGINA_TLC, cliente, headers={"User-Agent": "CC3084-Pasaporte"})
    try:
        respuesta.raise_for_status()
        pagina = EnlacesTLC()
        pagina.feed(respuesta.text)
    finally:
        respuesta.close()
    archivos = set()
    for enlace in pagina.enlaces:
        nombre = PurePosixPath(urlparse(enlace).path).name
        match = re.fullmatch(r"(yellow|green)_tripdata_(\d{4})-(0[1-9]|1[0-2])\.parquet", nombre)
        if match and int(match[2]) in anios:
            archivos.add(match.groups())
    if not archivos:
        raise ValueError("La pagina TLC no enlaza archivos de los anios solicitados; no se puede certificar completitud")
    return sorted(archivos)
