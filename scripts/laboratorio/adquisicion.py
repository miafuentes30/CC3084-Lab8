"""Descarga idempotente a partir del inventario oficial de NYC TLC."""

import argparse
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

from .integridad import es_catalogo_zonas, es_parquet_completo, guardar_procedencia
from .parametros import (ANIOS, ANIOS_PASAPORTE, TIPOS_TAXI, URL_ZONAS, BLOQUE, INTENTOS,
                        TIEMPO_ESPERA, Configuracion, construir_url)
from .publicaciones import publicados
from .solicitudes import solicitar


def tamanio_publicado(url, cliente=requests):
    with solicitar("HEAD", url, cliente, allow_redirects=True) as respuesta:
        if respuesta.status_code == 404:
            return None
        respuesta.raise_for_status()
        return int(respuesta.headers.get("Content-Length", 0))


def descargar_archivo(url, destino, esperado=0, validar=None, cliente=requests):
    destino.parent.mkdir(parents=True, exist_ok=True)
    ultimo_error = None
    for intento in range(1, INTENTOS + 1):
        with tempfile.NamedTemporaryFile(dir=destino.parent, prefix=destino.name + ".", suffix=".part", delete=False) as archivo:
            temporal = Path(archivo.name)
        try:
            with cliente.get(url, stream=True, timeout=TIEMPO_ESPERA) as respuesta:
                respuesta.raise_for_status()
                anunciado = int(respuesta.headers.get("Content-Length", 0))
                escritos = 0
                with temporal.open("wb") as archivo:
                    for bloque in respuesta.iter_content(chunk_size=BLOQUE):
                        if bloque:
                            archivo.write(bloque)
                            escritos += len(bloque)
            if escritos == 0 or (esperado and escritos != esperado):
                raise requests.RequestException(f"Llegaron {escritos} de {esperado} bytes")
            if anunciado and escritos != anunciado:
                raise requests.RequestException(f"El GET anuncio {anunciado} bytes, pero llegaron {escritos}")
            if validar and not validar(temporal):
                raise requests.RequestException("El contenido descargado no tiene el formato esperado")
            temporal.replace(destino)
            return escritos
        except (requests.RequestException, OSError) as error:
            ultimo_error = error
            if intento < INTENTOS:
                print(f"Reintento {intento}/{INTENTOS}: {error}")
                time.sleep(0.25 * 2 ** (intento - 1))
        finally:
            temporal.unlink(missing_ok=True)
    raise requests.RequestException(f"No se pudo descargar {url}: {ultimo_error}")


def descargar(tipo, anio, configuracion=None, meses=range(1, 13), cliente=requests, lista_publicados=None):
    config = configuracion or Configuracion.del_entorno()
    resumen = {"descargados": 0, "omitidos": 0, "no_publicados": [], "fallidos": [], "danados": []}
    for mes in meses:
        etiqueta = f"{tipo} {anio}-{mes:02d}"
        destino = config.ruta_viajes(tipo, anio, mes)
        if es_parquet_completo(destino):
            resumen["omitidos"] += 1
            print(f"{etiqueta}: ya existe integro, se omite")
            continue
        if destino.exists():
            resumen["danados"].append(etiqueta)
            print(f"{etiqueta}: archivo local danado; reemplazo atomico si la descarga termina")
        if lista_publicados is not None and (tipo, str(anio), f"{mes:02d}") not in lista_publicados:
            resumen["no_publicados"].append(etiqueta)
            print(f"{etiqueta}: no enlazado en la pagina oficial")
            continue
        try:
            esperado = tamanio_publicado(construir_url(tipo, anio, mes), cliente)
            if esperado is None:
                if lista_publicados is not None:
                    raise requests.RequestException("Enlace publicado por TLC, pero no disponible en el servidor")
                resumen["no_publicados"].append(etiqueta)
                print(f"{etiqueta}: HTTP 404, sin publicacion confirmada")
                continue
            escritos = descargar_archivo(construir_url(tipo, anio, mes), destino, esperado, es_parquet_completo, cliente)
            resumen["descargados"] += 1
            print(f"{etiqueta}: {escritos:,} bytes descargados y lectura completa verificada")
        except (requests.RequestException, OSError) as error:
            resumen["fallidos"].append(etiqueta)
            print(f"{etiqueta}: ERROR {error}")
    return resumen


def listar_publicaciones(config, args, lista):
    filas = []
    for tipo, anio, mes in sorted(lista):
        if (args.taxi != "all" and tipo != args.taxi) or int(mes) not in args.meses:
            continue
        try:
            tamanio = tamanio_publicado(construir_url(tipo, int(anio), int(mes)))
            estado = "disponible" if tamanio is not None else "enlace no disponible"
        except requests.RequestException as error:
            tamanio, estado = None, f"error remoto: {error}"
        filas.append({"tipo": tipo, "anio": int(anio), "mes": int(mes), "bytes_servidor": tamanio, "estado": estado})
        print(f"{tipo} {anio}-{mes}: {estado}, {tamanio} bytes")
    guardar_procedencia(config.resultados / "publicaciones_tlc.json", fuente="pagina TLC y HEAD", anios=args.anios,
                       archivos=filas, no_enlazados=[f"{t} {a}-{m:02d}" for t in TIPOS_TAXI
                        if args.taxi in ("all", t) for a in args.anios for m in args.meses
                        if (t, str(a), f"{m:02d}") not in lista])
    return int(any(f["estado"] != "disponible" for f in filas))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--taxi", choices=(*TIPOS_TAXI, "all"), default="all")
    parser.add_argument("--anios", type=int, nargs="+", choices=ANIOS, default=list(ANIOS_PASAPORTE))
    parser.add_argument("--meses", type=int, nargs="+", choices=range(1, 13), default=list(range(1, 13)))
    parser.add_argument("--solo-listar", action="store_true", help="Consulta publicaciones y tamanios sin descargar")
    args = parser.parse_args(argv)
    config = Configuracion.del_entorno()
    try:
        lista = set(publicados(args.anios))
    except (requests.RequestException, ValueError) as error:
        print(f"ERROR: no se puede determinar la publicacion oficial: {error}")
        return 1
    if args.solo_listar:
        return listar_publicaciones(config, args, lista)
    total = {"descargados": 0, "omitidos": 0, "no_publicados": [], "fallidos": [], "danados": []}
    for tipo in TIPOS_TAXI if args.taxi == "all" else (args.taxi,):
        for anio in sorted(set(args.anios)):
            resumen = descargar(tipo, anio, config, sorted(set(args.meses)), lista_publicados=lista)
            for campo in total:
                total[campo] += resumen[campo]
    zonas = config.raw / "zonas" / "taxi_zone_lookup.csv"
    if es_catalogo_zonas(zonas):
        total["omitidos"] += 1
    else:
        try:
            esperado = tamanio_publicado(URL_ZONAS)
            if esperado is None:
                raise requests.RequestException("Catalogo de zonas no disponible")
            descargar_archivo(URL_ZONAS, zonas, esperado, es_catalogo_zonas)
            total["descargados"] += 1
        except (requests.RequestException, OSError) as error:
            total["fallidos"].append("zonas")
            print(f"zonas: ERROR {error}")
    print("RESUMEN")
    for campo, valor in total.items():
        print(f"{campo}: {valor}")
    guardar_procedencia(config.resultados / "descarga.json", anios=args.anios, meses=args.meses, resumen=total)
    sello = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    guardar_procedencia(config.resultados / "pasaporte" / f"descarga_{sello}.json",
                       anios=args.anios, meses=args.meses, resumen=total)
    return int(bool(total["fallidos"]))
