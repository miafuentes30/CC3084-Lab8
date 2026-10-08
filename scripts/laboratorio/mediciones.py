"""Medicion reproducible sobre Parquet y tablas con los mismos archivos."""

import argparse
import math
import platform
import statistics
import time
import hashlib
import os
import shutil
import threading
from datetime import datetime, timezone
from pathlib import Path

import duckdb

from .sesion_consultas import Analisis
from .integridad import guardar_csv, guardar_procedencia
from .parametros import Configuracion, TIPOS_TAXI, literal_sql

CONJUNTOS = {
    "1 mes": ("2026-01",),
    "8 meses": tuple(f"2026-{mes:02d}" for mes in range(1, 9)),
    "20 meses": tuple(f"2024-{mes:02d}" for mes in range(1, 13)) + tuple(f"2026-{mes:02d}" for mes in range(1, 9)),
}
CONSULTAS = ["rendimiento/01_conteo_viajes.sql", "rendimiento/02_seleccion_diaria.sql", "rendimiento/03_cuartiles_cobro.sql",
             "exploracion/01_resumen_mensual.sql", "exploracion/02_demanda_por_hora.sql", "exploracion/06_origen_por_distrito.sql", "exploracion/09_distribucion_pagos.sql"]


def ruta_base(config, conjunto, ejecucion=None):
    carpeta = config.procesados if ejecucion is None else config.procesados / "benchmark_runs" / ejecucion
    return carpeta / f"benchmark_{conjunto.replace(' ', '_')}.duckdb"


def medir(con, texto, repeticiones=5, registrar=None):
    if repeticiones < 1:
        raise ValueError("Se requiere al menos una repeticion")
    tiempos = []
    for repeticion in range(repeticiones + 1):
        inicio = time.perf_counter()
        resultado = con.execute(texto).fetchall()
        tiempos.append(time.perf_counter() - inicio)
        if registrar:
            registrar(repeticion, tiempos[-1], resultado)
    return resultado, {"primera_s": tiempos[0], "mediana_s": statistics.median(tiempos[1:]),
                       "minimo_s": min(tiempos[1:]), "maximo_s": max(tiempos[1:])}


def iguales(a, b, tolerancia=0.01):
    if len(a) != len(b):
        return False
    # Agrupa por columnas exactas; compara valores flotantes dentro de cada grupo.
    def agrupar(filas):
        grupos = {}
        for fila in filas:
            clave = tuple((i, x) for i, x in enumerate(fila) if not isinstance(x, float))
            grupos.setdefault((len(fila), clave), []).append(tuple(x for x in fila if isinstance(x, float)))
        return grupos
    ga, gb = agrupar(a), agrupar(b)
    if ga.keys() != gb.keys():
        return False
    for clave in ga:
        x, y = ga[clave], gb[clave]
        if len(x) != len(y):
            return False
        for fila in x:
            for n, candidata in enumerate(y):
                if all((math.isnan(v) and math.isnan(w)) or math.isclose(v, w, rel_tol=0, abs_tol=tolerancia)
                       for v, w in zip(fila, candidata)):
                    y.pop(n)
                    break
            else:
                return False
    return True


def recursos():
    """Memoria efectiva del host/cgroup; no confunde swap con RAM disponible."""
    disponibles = []
    detalle = {}
    ruta = Path("/proc/meminfo")
    if ruta.exists():
        valores = {linea.split(':')[0]: int(linea.split()[1]) * 1024 for linea in ruta.read_text().splitlines()}
        detalle = {k: valores[k] for k in ("MemTotal", "MemAvailable", "SwapTotal", "SwapFree")}
        disponibles.append(valores["MemAvailable"])
    for limite, uso in (("/sys/fs/cgroup/memory.max", "/sys/fs/cgroup/memory.current"),
                        ("/sys/fs/cgroup/memory/memory.limit_in_bytes", "/sys/fs/cgroup/memory/memory.usage_in_bytes")):
        if Path(limite).exists():
            valor = Path(limite).read_text().strip()
            if valor != "max":
                detalle["cgroup_limite_bytes"] = int(valor)
                detalle["cgroup_uso_bytes"] = int(Path(uso).read_text())
                disponibles.append(max(0, int(valor) - detalle["cgroup_uso_bytes"]))
    if not disponibles and os.name == "nt":
        import ctypes
        class Memoria(ctypes.Structure):
            _fields_ = [("length", ctypes.c_ulong), ("load", ctypes.c_ulong)] + [(k, ctypes.c_ulonglong) for k in
                ("total", "available", "page_total", "page_available", "virtual_total", "virtual_available", "extended")]
        estado = Memoria()
        estado.length = ctypes.sizeof(estado)
        if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(estado)):
            disponibles.append(estado.available)
            detalle.update(MemTotal=estado.total, MemAvailable=estado.available)
    detalle["disponible_efectiva_bytes"] = min(disponibles) if disponibles else None
    return detalle


def bytes_memoria(valor):
    import re
    match = re.fullmatch(r"([0-9.]+)\s*(GiB|MiB|GB|MB)", valor, re.I)
    if not match:
        raise ValueError("Memoria debe expresarse en GB, GiB, MB o MiB")
    factor = {"gib": 1024**3, "mib": 1024**2, "gb": 10**9, "mb": 10**6}[match[2].lower()]
    return int(float(match[1]) * factor)


class Monitor:
    """Muestreo de RSS y temporales cada 0.5 s; pico inferior al pico instantáneo."""
    def __init__(self, temporal):
        self.temporal, self.rss, self.temp = temporal, 0, 0
        self.fin = threading.Event()
        self.hilo = threading.Thread(target=self._muestrear, daemon=True)

    def _muestrear(self):
        while not self.fin.is_set():
            ruta = Path("/proc/self/status")
            if ruta.exists():
                datos = {l.split(':')[0]: l.split(':')[1].strip() for l in ruta.read_text().splitlines()}
                self.rss = max(self.rss, int(datos["VmRSS"].split()[0]) * 1024)
            total = 0
            for archivo in self.temporal.rglob('*'):
                try:
                    if archivo.is_file():
                        total += archivo.stat().st_size
                except FileNotFoundError:
                    pass
            self.temp = max(self.temp, total)
            self.fin.wait(0.5)

    def cerrar(self):
        self.fin.set()
        self.hilo.join()


def ejecutar(config=None, conjuntos=None, repeticiones=5, hilos=2, memoria="1GiB", ejecucion=None):
    if repeticiones < 1:
        raise ValueError("Se requiere al menos una repeticion")
    config = config or Configuracion.del_entorno()
    conjuntos = CONJUNTOS if conjuntos is None else conjuntos
    config.procesados.mkdir(parents=True, exist_ok=True)
    config.resultados.mkdir(parents=True, exist_ok=True)
    carpeta = ruta_base(config, next(iter(conjuntos)), ejecucion).parent
    carpeta.mkdir(parents=True, exist_ok=True)
    temporal = carpeta / "temporales_benchmark"
    temporal.mkdir(exist_ok=True)
    opciones = {"threads": hilos, "memory_limit": memoria, "temp_directory": str(temporal),
                "max_temp_directory_size": "4GiB", "preserve_insertion_order": "false"}
    if hilos < 1 or bytes_memoria(memoria) <= 0:
        raise ValueError("Hilos y memoria deben ser positivos")
    tablas, tiempos, individuales, equivalencia, lotes, planes = [], [], [], [], [], []
    inventario, comprobaciones = {}, []
    consultas = {c: (config.sql / c).read_text(encoding="utf-8") for c in CONSULTAS}
    evidencia = dict(ejecucion=ejecucion, estado="en_curso", duckdb=duckdb.__version__, python=platform.python_version(),
                     sistema=platform.platform(), cpu_logicas=os.cpu_count(), repeticiones=repeticiones,
                     configuracion=opciones, inventario=inventario, recursos=comprobaciones,
                     tolerancia=dict(absoluta=0.01, relativa=0, enteros="exactos", nulos="exactos"),
                     consultas=consultas, sha256_sql={c: hashlib.sha256(t.encode()).hexdigest() for c, t in consultas.items()},
                     normalizacion=(config.sql / "normalizacion_viajes.sql").read_text(encoding="utf-8"),
                     reglas=(config.sql / "reglas_compartidas.sql").read_text(encoding="utf-8"),
                     cache="Una conexión nueva por consulta/estrategia; un calentamiento y N mediciones. Caché OS no controlada.",
                     orden="Consulta a consulta; estrategia inicial alternada según índice del conjunto y consulta.")
    def guardar():
        for nombre, filas in (("tablas", tablas), ("tiempos", tiempos), ("individuales", individuales),
                               ("equivalencia", equivalencia), ("lotes", lotes)):
            if filas:
                guardar_csv(config.resultados / f"benchmark_{nombre}.csv", filas)
        guardar_procedencia(config.resultados / "benchmark.json", **evidencia)
    monitor = Monitor(temporal)
    monitor.hilo.start()
    try:
        # El JSON invalida salidas antiguas mientras una ejecución está incompleta.
        guardar()
        for indice_conjunto, (conjunto, periodos) in enumerate(conjuntos.items()):
            archivos = [config.ruta_viajes(tipo, int(p[:4]), int(p[5:])) for tipo in TIPOS_TAXI for p in periodos]
            faltan = [str(r) for r in archivos if not r.is_file()]
            if faltan:
                raise FileNotFoundError(f"Conjunto {conjunto} incompleto: {faltan}")
            with duckdb.connect(config=opciones) as con:
                inventario[conjunto] = [{"archivo": r.relative_to(config.raiz).as_posix(), "bytes": r.stat().st_size,
                    "mtime_ns": r.stat().st_mtime_ns,
                    "registros": con.execute("SELECT num_rows FROM parquet_file_metadata(?)", [str(r)]).fetchone()[0]}
                    for r in archivos]
            registros = sum(f["registros"] for f in inventario[conjunto])
            ruta = ruta_base(config, conjunto, ejecucion)
            if ejecucion and ruta.exists():
                raise FileExistsError(f"La base de esta ejecución ya existe: {ruta}")
            recurso = recursos()
            libre = shutil.disk_usage(carpeta).free
            # Cota conservadora de almacenamiento: 256 bytes/fila + temporales + reserva.
            estimado = registros * 256 + 4 * 1024**3 + 2 * 1024**3
            comprobaciones.append(dict(conjunto=conjunto, **recurso, disco_libre_bytes=libre,
                                        espacio_estimado_bytes=estimado, estimacion="256 bytes/fila + 4 GiB temporales + 2 GiB reserva"))
            if recurso["disponible_efectiva_bytes"] is None:
                raise RuntimeError("No se pudo comprobar memoria disponible; se requiere autorización para continuar")
            if recurso["disponible_efectiva_bytes"] < bytes_memoria(memoria) + 768 * 1024**2 or libre < estimado:
                raise RuntimeError("Recursos insuficientes; se requiere autorización antes de cambiar límites o metodología")
            print(f"{conjunto}: {registros:,} filas, {len(archivos)} archivos; materializando por mes", flush=True)
            with Analisis(config, periodos=periodos, opciones_duckdb=opciones) as analisis:
                tabla = analisis.con
                esquema = tabla.execute("DESCRIBE viajes").fetchall()
                tabla.execute(f"ATTACH {literal_sql(ruta.as_posix())} AS materializada")
                inicio = time.perf_counter()
                try:
                    tabla.execute("BEGIN")
                    tabla.execute("CREATE OR REPLACE TABLE materializada.viajes_tabla AS SELECT * FROM viajes WHERE false")
                    for periodo in periodos:
                        inicio_lote = time.perf_counter()
                        tabla.execute(f"INSERT INTO materializada.viajes_tabla SELECT * FROM viajes WHERE periodo = DATE '{periodo}-01'")
                        lotes.append(dict(conjunto=conjunto, periodo=periodo, segundos=time.perf_counter() - inicio_lote))
                        print(f"  insertado {periodo}", flush=True)
                    tabla.execute("CREATE OR REPLACE TABLE materializada.zonas_tabla AS SELECT * FROM zonas")
                    tabla.execute("USE materializada")
                    tabla.execute("CREATE OR REPLACE VIEW viajes AS SELECT * FROM viajes_tabla")
                    tabla.execute("CREATE OR REPLACE VIEW zonas AS SELECT * FROM zonas_tabla")
                    tabla.execute(analisis.leer_sql("reglas_compartidas.sql"))
                    tabla.execute("COMMIT")
                except Exception:
                    tabla.execute("ROLLBACK")
                    raise
                tabla.execute("CHECKPOINT materializada")
                tabla.execute("USE memory")
                tabla.execute("DETACH materializada")
                segundos = time.perf_counter() - inicio
            with duckdb.connect(str(ruta), read_only=True, config=opciones) as con:
                n = con.execute("SELECT count(*) FROM viajes").fetchone()[0]
                esquema_tabla = con.execute("DESCRIBE viajes").fetchall()
            if n != registros or esquema != esquema_tabla:
                raise RuntimeError("Materialización con conteo o esquema diferente")
            tablas.append(dict(conjunto=conjunto, archivos=len(archivos), registros=registros,
                mb_parquet=sum(f["bytes"] for f in inventario[conjunto]) / 1e6, mb_duckdb=ruta.stat().st_size / 1e6,
                creacion_tabla_s=segundos, base=ruta.relative_to(config.raiz).as_posix(), esquema_igual=True,
                registros_tabla=n, rss_pico_acumulado_bytes=monitor.rss))
            guardar()
            for indice_consulta, (consulta, texto) in enumerate(consultas.items()):
                resultados, referencias = {}, {}
                estrategias = ("parquet", "tabla") if (indice_conjunto + indice_consulta) % 2 == 0 else ("tabla", "parquet")
                for orden, estrategia in enumerate(estrategias):
                    if estrategia == "parquet":
                        sesion = Analisis(config, periodos=periodos, opciones_duckdb=opciones)
                        con = sesion.con
                    else:
                        con = duckdb.connect(str(ruta), read_only=True, config=opciones)
                    contexto = dict(conjunto=conjunto, registros=registros, consulta=consulta, estrategia=estrategia)
                    try:
                        planes.append(dict(**contexto, plan=con.execute("EXPLAIN " + texto).fetchall()[0][1]))
                        configuracion_real = con.execute("SELECT current_setting('threads'), current_setting('memory_limit'), current_setting('max_temp_directory_size'), current_setting('preserve_insertion_order')").fetchone()
                        evidencia.setdefault("configuracion_efectiva", []).append(dict(**contexto, valores=configuracion_real))
                        def registrar(repeticion, duracion, resultado):
                            if repeticion == 0:
                                referencias[estrategia] = resultado
                            estable = iguales(referencias[estrategia], resultado)
                            individuales.append(dict(**contexto, fase="calentamiento" if repeticion == 0 else "medicion",
                                repeticion=repeticion, segundos=duracion, orden_estrategia=orden + 1,
                                estado="ok" if estable else "resultado_inestable", filas_resultado=len(resultado)))
                            guardar()
                            if not estable:
                                raise RuntimeError("Resultado inestable entre repeticiones")
                        resultado, medidas = medir(con, texto, repeticiones, registrar)
                        resultados[estrategia] = resultado
                        tiempos.append(dict(**contexto, **medidas, mismo_resultado=False))
                        print(f"  {consulta} {estrategia}: mediana {medidas['mediana_s']:.4f} s", flush=True)
                    except Exception as error:
                        individuales.append(dict(**contexto, fase="fallo", repeticion=-1, segundos=None,
                            orden_estrategia=orden + 1, estado=type(error).__name__, filas_resultado=None))
                        raise
                    finally:
                        con.close()
                igual = iguales(resultados["parquet"], resultados["tabla"])
                equivalencia.append(dict(conjunto=conjunto, consulta=consulta, mismo_resultado=igual,
                    filas_parquet=len(resultados["parquet"]), filas_tabla=len(resultados["tabla"]),
                    tolerancia_absoluta=0.01, tolerancia_relativa=0))
                for fila in tiempos:
                    if fila["conjunto"] == conjunto and fila["consulta"] == consulta:
                        fila["mismo_resultado"] = igual
                guardar()
                if not igual:
                    raise RuntimeError(f"Resultados distintos: {conjunto}, {consulta}")
        # Verifica identidad de fuentes sin repetir lectura completa ni hashes masivos.
        for filas in inventario.values():
            for fila in filas:
                estadistica = (config.raiz / fila["archivo"]).stat()
                if (estadistica.st_size, estadistica.st_mtime_ns) != (fila["bytes"], fila["mtime_ns"]):
                    raise RuntimeError("Un archivo Parquet cambió durante el experimento")
        evidencia["estado"] = "completo"
        evidencia["fuentes_sin_cambios"] = True
        guardar_procedencia(config.resultados / "benchmark_planes.json", planes=planes)
        return tablas, tiempos
    except BaseException as error:
        evidencia.update(estado="fallido_o_interrumpido", error=f"{type(error).__name__}: {error}")
        raise
    finally:
        monitor.cerrar()
        evidencia.update(rss_pico_muestreado_bytes=monitor.rss, temporales_pico_muestreado_bytes=monitor.temp,
                         intervalo_muestreo_s=0.5, disco_libre_final_bytes=shutil.disk_usage(carpeta).free)
        guardar()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repeticiones", type=int, default=5)
    parser.add_argument("--hilos", type=int, default=2)
    parser.add_argument("--memoria", default="1GiB")
    parser.add_argument("--conjuntos", nargs="+", choices=("A", "B", "C"), default=["A", "B", "C"])
    args = parser.parse_args(argv)
    if args.repeticiones < 1:
        parser.error("--repeticiones debe ser mayor o igual a 1")
    if args.hilos < 1:
        parser.error("--hilos debe ser positivo")
    nombres = dict(zip(("A", "B", "C"), CONJUNTOS))
    seleccion = {nombres[c]: CONJUNTOS[nombres[c]] for c in args.conjuntos}
    ejecutar(conjuntos=seleccion, repeticiones=args.repeticiones, hilos=args.hilos, memoria=args.memoria,
             ejecucion=datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ"))
    return 0
