"""Verificacion independiente contra la pagina oficial y los pies de Parquet."""

import argparse
import requests
import duckdb

from .integridad import es_catalogo_zonas, es_parquet_completo, calcular_sha256, guardar_csv, guardar_procedencia
from .parametros import ANIOS, ANIOS_PASAPORTE, Configuracion, construir_url
from .adquisicion import tamanio_publicado
from .publicaciones import publicados

CAMPOS = ["tipo", "archivo", "bytes_servidor", "bytes_local", "registros", "estado", "sha256_local"]


def revisar(tipo, anio, mes, configuracion=None, cliente=requests):
    config = configuracion or Configuracion.del_entorno()
    ruta = config.ruta_viajes(tipo, int(anio), int(mes))
    fila = dict.fromkeys(CAMPOS)
    fila.update(tipo=tipo, archivo=ruta.name)
    try:
        servidor = tamanio_publicado(construir_url(tipo, int(anio), int(mes)), cliente)
        fila["bytes_servidor"] = servidor
        if servidor is None:
            return fila | {"estado": "enlace no disponible"}
        if servidor <= 0:
            return fila | {"estado": "tamanio remoto desconocido"}
        if not ruta.exists():
            return fila | {"estado": "falta"}
        fila["bytes_local"] = ruta.stat().st_size
        if servidor and fila["bytes_local"] != servidor:
            return fila | {"estado": "tamanio distinto"}
        if not es_parquet_completo(ruta):
            return fila | {"estado": "archivo danado"}
        with duckdb.connect() as con:
            fila["registros"] = con.execute("SELECT num_rows FROM parquet_file_metadata(?)", [str(ruta)]).fetchone()[0]
        fila["sha256_local"] = calcular_sha256(ruta)
        return fila | {"estado": "completo"}
    except requests.RequestException:
        return fila | {"estado": "error de red"}
    except (duckdb.Error, OSError):
        return fila | {"estado": "no se puede leer"}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--anios", type=int, nargs="+", choices=ANIOS, default=list(ANIOS_PASAPORTE))
    args = parser.parse_args(argv)
    config = Configuracion.del_entorno()
    try:
        esperados = publicados(args.anios)
    except (requests.RequestException, ValueError) as error:
        print(f"ERROR: {error}")
        return 1
    filas = [revisar(*archivo, configuracion=config) for archivo in esperados]
    nombres = {f["archivo"] for f in filas}
    for anio in args.anios:
        for ruta in sorted(config.raw.glob(f"*/{anio}/*.parquet")):
            if ruta.name not in nombres:
                filas.append({"tipo": ruta.parent.parent.name, "archivo": ruta.name,
                              "bytes_servidor": None, "bytes_local": ruta.stat().st_size,
                              "registros": None, "estado": "no publicado"})
    guardar_csv(config.resultados / "verificacion_descarga.csv", filas, CAMPOS)
    zonas_ok = es_catalogo_zonas(config.raw / "zonas" / "taxi_zone_lookup.csv")
    completos = sum(f["estado"] == "completo" for f in filas)
    for fila in filas:
        print(f"{fila['archivo']}: {fila['estado']}")
    print(f"{completos} de {len(esperados)} archivos publicados completos; catalogo de zonas: {zonas_ok}")
    guardar_procedencia(config.resultados / "verificacion_descarga.json", anios=args.anios,
                       completos=completos, esperados=len(esperados), zonas_ok=zonas_ok)
    return int(completos != len(filas) or not zonas_ok)
