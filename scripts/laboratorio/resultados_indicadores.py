"""Agregados mensuales limitados en memoria y exportación por etapa."""
import csv
import hashlib
import json
import shutil
import time
import calendar
from pathlib import Path

import duckdb
from .catalogo_indicadores import INDICADORES
from .integridad import guardar_csv, guardar_procedencia
from .mediciones import recursos
from .parametros import Configuracion
from .sesion_consultas import Analisis


def leer_csv(ruta):
    with Path(ruta).open(encoding='utf-8', newline='') as archivo:
        return list(csv.DictReader(archivo))


def consultas_resumen(anio, periodos):
    # Dos estados de medianas simultáneos pueden superar el buffer de 1 GiB.
    dias = sum(calendar.monthrange(int(p[:4]), int(p[-2:]))[1] for p in periodos)
    media = f"""SELECT {anio} AS anio, taxi, count(*) AS viajes_validos,
        {dias} AS dias_calendario, round(count(*) / {dias}, 2) AS viajes_por_dia,
        round(avg(trip_distance), 2) AS distancia_prom,
        round(avg(duracion_min), 2) AS duracion_prom_min,
        round(avg(total_amount), 2) AS total_prom, NULL::DOUBLE AS total_mediano,
        round(100 * avg((coalesce(payment_type, 0) = 0)::INT), 1) AS pct_flex_fare,
        round(100 * avg((coalesce(payment_type, 0) = 2)::INT), 1) AS pct_efectivo,
        round(100 * avg(tip_amount / fare_amount) FILTER (WHERE payment_type = 1 AND fare_amount > 0), 1) AS propina_pct_tarifa,
        round(100 * avg((cbd_congestion_fee > 0)::INT), 1) AS pct_cargo_cbd,
        NULL::DOUBLE AS velocidad_manhattan,
        round(100 * avg((PULocationID IN (1, 132, 138) OR DOLocationID IN (1, 132, 138))::INT), 1) AS pct_aeropuerto
        FROM viajes_validos GROUP BY taxi ORDER BY taxi DESC"""
    return dict(medias=media,
        mediana_monto='SELECT taxi, round(median(total_amount), 2) FROM viajes_validos GROUP BY taxi',
        mediana_velocidad="""SELECT v.taxi, round(median(v.trip_distance / (v.duracion_min / 60)), 2)
            FROM viajes_validos v JOIN zonas i ON v.PULocationID = i.zona_id JOIN zonas f ON v.DOLocationID = f.zona_id
            WHERE i.distrito = 'Manhattan' AND f.distrito = 'Manhattan' GROUP BY v.taxi""")


def resumen_anual(config, anio, periodos, opciones):
    consultas = consultas_resumen(anio, periodos)
    opciones = {**opciones, 'threads': 1}
    with Analisis(config, periodos=periodos, opciones_duckdb=opciones) as sesion:
        cursor = sesion.con.execute(consultas['medias'])
        campos = [d[0] for d in cursor.description]
        filas = [dict(zip(campos, f)) for f in cursor.fetchall()]
        montos = dict(sesion.con.execute(consultas['mediana_monto']).fetchall())
        velocidad = dict(sesion.con.execute(consultas['mediana_velocidad']).fetchall())
        for fila in filas:
            fila['total_mediano'] = montos.get(fila['taxi'])
            fila['velocidad_manhattan'] = velocidad.get(fila['taxi'])
    return filas


def calcular(configuracion=None, anios=None, base=None, reutilizar=False, solo_resumen=False, catalogo=None):
    config = configuracion or Configuracion.del_entorno()
    anios = sorted(set(anios or (2024, 2025, 2026)))
    fase = 'ejercicio_7' if anios == [2024, 2026] else 'ejercicio_8'
    destino = config.resultados / fase
    destino.mkdir(parents=True, exist_ok=True)
    config.procesados.mkdir(parents=True, exist_ok=True)
    temporal = config.procesados / 'temporales_indicadores'
    temporal.mkdir(exist_ok=True)
    opciones = dict(threads=2, memory_limit='1GiB', temp_directory=str(temporal),
                    max_temp_directory_size='2GiB', preserve_insertion_order='false')
    estado_recursos = recursos()
    if (estado_recursos['disponible_efectiva_bytes'] or 0) < 1792 * 1024**2:
        raise RuntimeError('RAM disponible insuficiente para indicadores con los límites establecidos')
    if shutil.disk_usage(config.procesados).free < 3 * 1024**3:
        raise RuntimeError('Se requieren 3 GiB libres como reserva y temporales')
    base = Path(base) if base else config.procesados / 'tablero.duckdb'
    indicadores = catalogo if catalogo is not None else INDICADORES
    consultas = {i['tabla']: (config.sql / 'metricas' / i['sql']).read_text(encoding='utf-8').rstrip().rstrip(';') for i in indicadores}
    hashes = {k: hashlib.sha256(v.encode()).hexdigest() for k, v in consultas.items()}
    contratos = {nombre: hashlib.sha256((config.sql / nombre).read_bytes()).hexdigest()
                 for nombre in ('normalizacion_viajes.sql', 'reglas_compartidas.sql')}
    contratos['zonas'] = hashlib.sha256((config.raw / 'zonas/taxi_zone_lookup.csv').read_bytes()).hexdigest()
    inventario = []
    with duckdb.connect(config=opciones) as con:
        for ruta in sorted(config.raw.glob('*/*/*.parquet')):
            if int(ruta.parent.name) not in anios:
                continue
            inventario.append(dict(archivo=ruta.relative_to(config.raiz).as_posix(), periodo=ruta.stem[-7:],
                anio=int(ruta.parent.name), taxi=ruta.parent.parent.name, bytes=ruta.stat().st_size,
                mtime_ns=ruta.stat().st_mtime_ns,
                registros=con.execute('SELECT num_rows FROM parquet_file_metadata(?)', [str(ruta)]).fetchone()[0]))
    periodos = sorted({f['periodo'] for f in inventario})
    if not periodos:
        raise FileNotFoundError('No hay archivos para los años seleccionados')
    anteriores = config.resultados / 'ejercicio_7'
    reutilizados = set()
    previo = None
    if reutilizar:
        previo = json.loads((anteriores / 'indicadores.json').read_text(encoding='utf-8'))
        if previo['sql_sha256'] != hashes or previo.get('contratos_sha256') != contratos or previo['estado'] != 'completo':
            raise ValueError('Los indicadores previos no corresponden al SQL actual')
        actuales = {f['archivo']: f for f in inventario}
        for fila in previo['inventario']:
            actual = actuales.get(fila['archivo'])
            if not actual or any(actual[k] != fila[k] for k in ('bytes', 'mtime_ns', 'registros')):
                raise ValueError('Las fuentes iniciales cambiaron; no reutilizar agregados')
        reutilizados = {f['periodo'] for f in previo['inventario']}
    evidencias = {i['tabla']: dict(tabla=i['tabla'], filas=0, segundos=0.0) for i in indicadores}
    with duckdb.connect(str(base), config=opciones) as escritor:
        if solo_resumen:
            for nombre in consultas:
                evidencias[nombre]['filas'] = escritor.execute(f'SELECT count(*) FROM {nombre}').fetchone()[0]
                evidencias[nombre]['segundos'] = None
        else:
            _calcular_meses(config, escritor, periodos, opciones, consultas, reutilizar, anteriores, reutilizados, evidencias, destino)
    guardar_csv(destino / 'inventario.csv', inventario)
    datos_evidencia = dict(anios=anios, base=base.relative_to(config.raiz).as_posix(), inventario=inventario,
        tablas=list(evidencias.values()), sql=consultas, sql_sha256=hashes, contratos_sha256=contratos,
        configuracion=opciones, recursos_iniciales=estado_recursos,
        periodos_reutilizados=sorted(reutilizados), bytes_base=base.stat().st_size)
    guardar_procedencia(destino / 'indicadores.json', estado='mensual_completo', **datos_evidencia)
    resumen = leer_csv(anteriores / 'comparacion_enero_agosto.csv') if reutilizar else []
    comparativa = (config.sql / 'comparacion_anual/01_resumen_periodos_comparables.sql').read_text(encoding='utf-8')
    for anio in anios:
        if reutilizar and anio in (2024, 2026):
            continue
        seleccion = [p for p in periodos if p.startswith(str(anio)) and int(p[-2:]) <= 8]
        filas = resumen_anual(config, anio, seleccion, opciones)
        for fila in filas:
            fila['registros_brutos'] = sum(f['registros'] for f in inventario if f['periodo'] in seleccion and f['taxi'] == fila['taxi'])
        resumen.extend(filas)
        print(f'Comparación enero-agosto calculada: {anio}', flush=True)
    guardar_csv(destino / 'comparacion_enero_agosto.csv', resumen)
    guardar_procedencia(destino / 'indicadores.json', estado='completo', **datos_evidencia,
        sql_comparacion=comparativa, comparacion_ejecucion='Medias y conteos, mediana del monto y mediana de velocidad en tres consultas secuenciales por año; 1 hilo, 1 GiB')
    guardar_procedencia(config.resultados / 'indicadores.json', estado='completo', anios=anios,
        base=base.relative_to(config.raiz).as_posix(), evidencia=f'{fase}/indicadores.json',
        inventario=inventario, tablas=list(evidencias.values()))
    return base


def _calcular_meses(config, escritor, periodos, opciones, consultas, reutilizar, anteriores, reutilizados, evidencias, destino):
    escritor.execute('BEGIN')
    try:
        with Analisis(config, periodos=[periodos[0]], opciones_duckdb=opciones) as sesion:
            for nombre, sql in consultas.items():
                columnas = sesion.con.execute('DESCRIBE (' + sql + ')').fetchall()
                definicion = ', '.join(f'"{c[0]}" {c[1]}' for c in columnas)
                escritor.execute(f'CREATE OR REPLACE TABLE {nombre} ({definicion})')
                if reutilizar:
                    filas = leer_csv(anteriores / (nombre + '.csv'))
                    valores = [tuple(f[c[0]] or None for c in columnas) for f in filas]
                    if valores:
                        escritor.executemany(f'INSERT INTO {nombre} VALUES ({",".join("?" for _ in columnas)})', valores)
        for periodo in periodos:
            if periodo in reutilizados:
                continue
            with Analisis(config, periodos=[periodo], opciones_duckdb=opciones) as sesion:
                for nombre, sql in consultas.items():
                    inicio = time.perf_counter()
                    filas = sesion.con.execute(sql).fetchall()
                    evidencias[nombre]['segundos'] += time.perf_counter() - inicio
                    if filas:
                        escritor.executemany(f'INSERT INTO {nombre} VALUES ({",".join("?" for _ in filas[0])})', filas)
            print(f'Indicadores calculados: {periodo}', flush=True)
        escritor.execute('COMMIT')
    except Exception:
        escritor.execute('ROLLBACK')
        raise
    escritor.execute('CHECKPOINT')
    for nombre in consultas:
        cursor = escritor.execute(f'SELECT * FROM {nombre} ORDER BY taxi, periodo')
        campos = [d[0] for d in cursor.description]
        filas = [dict(zip(campos, f)) for f in cursor.fetchall()]
        evidencias[nombre]['filas'] = len(filas)
        guardar_csv(destino / (nombre + '.csv'), filas, campos)
