"""Cierra informes e inventarios desde evidencia existente, sin consultar viajes."""
import argparse
import csv
import json
import os
from datetime import datetime, timezone
from pathlib import Path

import requests
from laboratorio.parametros import Configuracion
from laboratorio.integridad import guardar_csv, guardar_procedencia
from laboratorio.presentacion_final import documentar, tabla_md
from laboratorio.resultados_indicadores import leer_csv


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--pruebas-aprobadas', type=int, help='Resultado observado de la suite final; no vuelve a ejecutarla')
    args = parser.parse_args()
    config = Configuracion.del_entorno()
    for fase in ('ejercicio_7', 'ejercicio_8'):
        documentar(config, fase)
    carpeta = config.resultados
    inicial = json.loads((carpeta / 'ejercicio_7/indicadores.json').read_text(encoding='utf-8'))
    final = json.loads((carpeta / 'ejercicio_8/indicadores.json').read_text(encoding='utf-8'))
    actuales = {f['archivo']: f for f in final['inventario']}
    for fila in inicial['inventario']:
        assert all(fila[k] == actuales[fila['archivo']][k] for k in ('bytes', 'mtime_ns', 'registros'))
        estado = (config.raiz / fila['archivo']).stat()
        assert estado.st_size == fila['bytes'] and estado.st_mtime_ns == fila['mtime_ns']
    verificados = leer_csv(carpeta / 'ejercicio_5_verificacion_40.csv') + leer_csv(carpeta / 'ejercicio_8_verificacion_2025.csv')
    assert len(verificados) == len({f['archivo'] for f in verificados}) == len(final['inventario'])
    assert all(f['estado'] == 'completo' and f['sha256_local'] for f in verificados)
    total = sum(f['registros'] for f in final['inventario'])
    assert total == sum(int(f['registros']) for f in verificados)
    guardar_csv(carpeta / 'verificacion_integrada.csv', verificados)
    guardar_procedencia(carpeta / 'verificacion_integrada.json', completos=len(verificados), registros_brutos=total,
        anios=final['anios'], originales_2024_2026_sin_cambios=True,
        metodo='Validación completa previa de 40 archivos + validación nueva de 24 archivos 2025; tamaño/mtime/metadatos originales conservados')
    notebooks = []
    for nombre in ('07_panel_indicadores.ipynb', '08_integracion_tres_anios.ipynb'):
        nb = json.loads((config.raiz / 'notebooks' / nombre).read_text(encoding='utf-8'))
        codigo = [c for c in nb['cells'] if c['cell_type'] == 'code']
        errores = [o for c in codigo for o in c.get('outputs', []) if o['output_type'] == 'error']
        imagenes = sum('image/png' in o.get('data', {}) for c in codigo for o in c.get('outputs', []))
        assert not errores and all(c['execution_count'] is not None for c in codigo) and imagenes == 9
        notebooks.append(dict(notebook=nombre, celdas=len(codigo), ejecutadas=len(codigo), errores=0, imagenes=imagenes))
    try:
        respuesta = requests.get(os.environ.get('MB_URL', 'http://metabase:3000').rstrip('/') + '/api/health', timeout=5)
        salud = respuesta.json().get('status') if respuesta.ok else f'HTTP {respuesta.status_code}'
    except requests.RequestException:
        salud = 'no disponible'
    guardar_procedencia(carpeta / 'metabase_estado.json', publicado=False, estado='pendiente_credenciales',
        salud=salud, credenciales_disponibles=bool(os.environ.get('MB_EMAIL') and os.environ.get('MB_PASSWORD')),
        alternativa='tablero_indicadores.html', instrucciones='../publicacion_metabase.md')
    guardar_procedencia(carpeta / 'entrega_validacion.json', archivos_parquet=len(verificados), registros_brutos=total,
        originales_conservados=40, archivos_2025_validados=24, indicadores=9, notebooks=notebooks,
        pruebas_aprobadas_observadas=args.pruebas_aprobadas,
        pendientes=['Publicación autenticada y comprobación visual de filtros en Metabase: faltan credenciales'],
        benchmark_repetido=False, notebooks_03_06_reejecutados=False)
    import pandas as pd
    conteos = pd.read_csv(carpeta / 'ejercicio_8/conteos_por_anio.csv')
    resumen = pd.read_csv(carpeta / 'ejercicio_8/comparacion_enero_agosto.csv').sort_values(['taxi', 'anio'])
    texto = f'''# Entrega final — Laboratorio 8

CC3084 — Data Science, Universidad del Valle de Guatemala.
[Fork oficial](https://github.com/miafuentes30/CC3084-Lab8).

## Cobertura y resultados

**{len(verificados)} Parquet y {total:,} registros originales**. 2024 y 2025
contienen doce meses por taxi; 2026 conserva enero–agosto. La ampliación
descargó 24 archivos de 2025 y conservó los 40 anteriores. El catálogo no se
volvió a descargar. SHA-256 y validaciones: [inventario integrado](resultados/verificacion_integrada.csv).

{tabla_md(conteos)}

Los totales completos describen cobertura, no tendencias equivalentes.
Las comparaciones interanuales utilizan enero–agosto y días calendario;
se separan registros originales y viajes válidos.

## Evidencia de los nueve ejercicios

| Ejercicio | Resultado y evidencia |
|---|---|
| 1 | Docker, JupyterLab y driver DuckDB; [validación inicial](validacion_etapa_inicial.md) |
| 2 | Descarga incremental, integridad y errores; [pasaportes](resultados/pasaporte/) e [inventario integrado](resultados/verificacion_integrada.json) |
| 3 | Inspección directa; [informe 2026](resultados/ejercicio_3_2026.md), notebook 03 |
| 4 | Trece consultas exploratorias; [informe](resultados/ejercicio_4_2026.md), notebook 04 |
| 5 | 40 archivos, 71,870,407 originales; [informe corregido](resultados/ejercicio_5_incremental.md), notebook 05 |
| 6 | 210 mediciones, 42 calentamientos, 21 equivalencias; [benchmark](resultados/ejercicio_6_benchmark.md), notebook 06 |
| 7 | Diez preguntas y nueve indicadores con 2024/2026; [informe](resultados/ejercicio_7_indicadores.md), notebook 07 |
| 8 | 2025 incorporado, nueve indicadores actualizados y periodos comparables; [informe](resultados/ejercicio_8_analisis_completo.md), notebook 08 |
| 9 | Ocho incisos con evidencia real; [discusión final](discusion_final.md) |

Los notebooks finales están en [notebooks](../notebooks/). Esta continuación
ejecutó únicamente 07 y 08: {notebooks[0]['celdas']} y {notebooks[1]['celdas']}
celdas de código, cero errores y nueve gráficas por etapa. No repitió el
benchmark ni los notebooks 03–06.

## Hallazgos de enero–agosto

{tabla_md(resumen[['anio','taxi','viajes_por_dia','total_mediano','pct_flex_fare','pct_efectivo','pct_cargo_cbd']])}

El informe 8 interpreta demanda, pagos y montos con los mismos meses de los
tres años. El agrupamiento 0/nulo es una convención documentada; los cambios
de selección/calidad afectan la población analítica y no prueban causalidad.

## Tablero, validación y reproducción

El [tablero local](resultados/tablero_indicadores.html) contiene nueve gráficas
y filtros por taxi, año y cobertura comparable. Metabase usa el driver y las
bases agregadas existentes; **la publicación autenticada queda pendiente por
falta de credenciales**. Salud del servicio observada: `{salud}`. No se aporta
una captura ficticia ni se elimina contenido ajeno. Las
[instrucciones de publicación](publicacion_metabase.md) utilizan variables del ambiente.

Suite final observada: **{args.pruebas_aprobadas or 'consultar registro'} pruebas aprobadas**.
Incluye equivalencia del resumen separado y conservación de objetos ajenos en
la API simulada. La API simulada no certifica publicación real. El registro
está en [entrega_validacion.json](resultados/entrega_validacion.json).
Los enlaces del README, exclusiones de Git y diff --check se comprueban en
el cierre local de esta entrega.

La comparación anual original agotó 1 GiB. Se conservaron las tablas mensuales
y se separaron conteos/medias y medianas exactas, con un hilo y el mismo límite.
Los tiempos mensuales iniciales no se recuperaron tras esa reanudación y se
registraron como nulos; no son mediciones de benchmark.

La limpieza está registrada en [limpieza](limpieza_final.md). Se conservan
datos, todas las bases locales, evidencia real e historia académica; Git
excluye datos, bases y secretos. No se hicieron commits, push ni cambios de remotos.

Los comandos mínimos, instalación, puertos configurables y flujo completo
están en [README](../README.md). Para volver a presentar los resultados ya
calculados basta ejecutar los notebooks 07/08; para reconstruir las tablas
utilice construir_tablero.py como indica README.
'''
    (config.raiz / 'docs/entrega_final.md').write_text(texto, encoding='utf-8')
    print(f'Entrega documentada: {len(verificados)} archivos, {total:,} registros; notebooks {notebooks}; salud Metabase: {salud}')
    print(resumen[['anio', 'taxi', 'viajes_por_dia', 'total_mediano', 'pct_flex_fare', 'pct_efectivo']].to_string(index=False))


if __name__ == '__main__':
    main()
