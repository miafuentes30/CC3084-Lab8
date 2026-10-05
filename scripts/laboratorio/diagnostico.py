"""Diagnostico reproducible de versiones, persistencia y servicios."""

import argparse
import os
import platform
import re
import tempfile
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

import duckdb
import requests

from .integridad import guardar_procedencia
from .parametros import Configuracion, RAIZ_CODIGO
from .solicitudes import solicitar


def versiones_esperadas():
    versiones = {}
    for linea in (RAIZ_CODIGO / "requirements.txt").read_text(encoding="utf-8").splitlines():
        nombre, separador, pin = linea.partition("==")
        if separador:
            versiones[nombre.strip()] = pin.strip()
    return versiones


def comprobar_versiones():
    errores, versiones = [], {"python": platform.python_version(), "sistema": platform.system()}
    for paquete, esperada in versiones_esperadas().items():
        try:
            actual = version(paquete)
            versiones[paquete] = actual
            if actual != esperada:
                errores.append(f"{paquete}: esperado {esperada}, instalado {actual}")
        except PackageNotFoundError:
            errores.append(f"Falta paquete {paquete}")
    dockerfile = RAIZ_CODIGO / "Dockerfile"
    if dockerfile.exists():
        match = re.search(r"FROM python:([0-9.]+)-", dockerfile.read_text(encoding="utf-8"))
        if match and platform.python_version() != match[1]:
            errores.append(f"Python: Dockerfile requiere {match[1]}, instalado {platform.python_version()}")
    return versiones, errores


def comprobar_persistencia(config):
    errores, persistencia = [], {}
    for relativa in ("data/raw", "data/processed"):
        carpeta = config.raiz / relativa
        if not carpeta.is_dir():
            errores.append(f"Falta carpeta {relativa}")
            continue
        try:
            with tempfile.TemporaryDirectory(prefix=".diagnostico_", dir=carpeta) as tmp:
                ruta = Path(tmp) / "prueba.parquet"
                with duckdb.connect() as con:
                    con.execute("COPY (SELECT range AS id FROM range(1000)) TO ? (FORMAT parquet)", [str(ruta)])
                    filas = con.execute("SELECT count(*) FROM read_parquet(?)", [str(ruta)]).fetchone()[0]
                persistencia[relativa] = {"escritura_y_lectura": filas == 1000}
                if filas != 1000:
                    errores.append(f"{relativa}: conteo inesperado")
        except (OSError, duckdb.Error) as error:
            errores.append(f"{relativa}: {error}")
    mountinfo = Path("/proc/self/mountinfo")
    if mountinfo.exists():
        destinos = {linea.split()[4] for linea in mountinfo.read_text().splitlines()}
        montada = (config.raiz / "data").as_posix() in destinos
        persistencia["data_montada"] = montada
        if not montada:
            errores.append("data/ no aparece como volumen montado en el contenedor")
    return persistencia, errores


def comprobar_servicios():
    errores, servicios = [], {}
    try:
        with solicitar("GET", "http://localhost:8888/api/status") as respuesta:
            respuesta.raise_for_status()
            servicios["jupyterlab"] = {"http": respuesta.status_code}
    except requests.RequestException as error:
        errores.append(f"JupyterLab: {error}")
    url = os.environ.get("MB_URL", "http://localhost:3000").rstrip("/")
    try:
        with solicitar("GET", f"{url}/api/health") as respuesta:
            respuesta.raise_for_status()
            estado = respuesta.json().get("status")
            servicios["metabase"] = {"estado": estado}
            if estado != "ok":
                errores.append("Metabase no esta listo")
        with solicitar("GET", f"{url}/api/session/properties") as respuesta:
            respuesta.raise_for_status()
            propiedades = respuesta.json()
        metabase_version = propiedades.get("version", {}).get("tag")
        driver = "duckdb" in propiedades.get("engines", {})
        servicios["metabase"].update(version=metabase_version, driver_duckdb=driver)
        imagen = RAIZ_CODIGO / "metabase.Dockerfile"
        if imagen.exists():
            contenido = imagen.read_text(encoding="utf-8")
            esperada = re.search(r"ARG METABASE_VERSION=(\\S+)", contenido)
            driver_version = re.search(r"ARG DUCKDB_DRIVER_VERSION=(\\S+)", contenido)
            if esperada and metabase_version != esperada[1]:
                errores.append(f"Metabase: esperado {esperada[1]}, activo {metabase_version}")
            servicios["metabase"]["version_driver_configurada"] = driver_version[1] if driver_version else None
        if not driver:
            errores.append("El driver DuckDB no aparece en los motores de Metabase")
    except (requests.RequestException, ValueError) as error:
        errores.append(f"Metabase: {error}")
    return servicios, errores


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sin-servicios", action="store_true", help="Verifica Python y disco sin exigir servidores activos")
    args = parser.parse_args(argv)
    config = Configuracion.del_entorno()
    versiones, errores = comprobar_versiones()
    persistencia, errores_disco = comprobar_persistencia(config)
    errores.extend(errores_disco)
    for carpeta in ("notebooks", "scripts", "sql", "docs"):
        if not (config.raiz / carpeta).is_dir():
            errores.append(f"Falta carpeta {carpeta}")
    servicios = {}
    if not args.sin_servicios:
        servicios, errores_servicios = comprobar_servicios()
        errores.extend(errores_servicios)
    guardar_procedencia(config.resultados / "diagnostico_entorno.json", versiones=versiones,
                       persistencia=persistencia, servicios=servicios, errores=errores)
    for nombre, valor in versiones.items():
        print(f"{nombre}: {valor}")
    print(f"Persistencia: {persistencia}")
    print(f"Servicios: {servicios}")
    print("\\n".join(errores) if errores else "Verificacion completa")
    return int(bool(errores))
