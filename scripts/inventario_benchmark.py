"""Revisa pies Parquet y recursos locales sin escanear las filas."""
import json
import os
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import duckdb
from laboratorio.integridad import guardar_csv
from laboratorio.parametros import Configuracion
from laboratorio.mediciones import CONJUNTOS

config = Configuracion.del_entorno()
filas = []
with duckdb.connect() as con:
    for ruta in sorted(config.raw.glob('*/*/*.parquet')):
        tipo, anio = ruta.parent.parent.name, int(ruta.parent.name)
        n = con.execute('SELECT num_rows FROM parquet_file_metadata(?)', [str(ruta)]).fetchone()[0]
        filas.append(dict(archivo=ruta.relative_to(config.raiz).as_posix(), tipo=tipo,
                          anio=anio, periodo=ruta.stem[-7:], registros=n, bytes=ruta.stat().st_size))
guardar_csv(config.resultados / 'ejercicio_5_conteos_metadatos.csv', filas)
for anio in (2024, 2026):
    for tipo in ('yellow', 'green'):
        seleccion = [f for f in filas if f['anio'] == anio and f['tipo'] == tipo]
        print(anio, tipo, len(seleccion), sum(f['registros'] for f in seleccion))
for nombre, periodos in CONJUNTOS.items():
    seleccion = [f for f in filas if f['periodo'] in periodos]
    print(nombre, len(seleccion), sum(f['registros'] for f in seleccion), sum(f['bytes'] for f in seleccion))
print('DuckDB', duckdb.__version__, 'CPU', os.cpu_count(), 'disco', shutil.disk_usage(config.procesados))
for archivo in ('/proc/meminfo', '/sys/fs/cgroup/memory/memory.limit_in_bytes',
                '/sys/fs/cgroup/memory/memory.usage_in_bytes', '/sys/fs/cgroup/memory/memory.stat'):
    ruta = Path(archivo)
    if ruta.exists():
        print(archivo, ruta.read_text()[:1300])
