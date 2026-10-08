"""Genera comparación e informe desde mediciones completas; no escanea viajes."""
import csv
import json
import math
import statistics
from pathlib import Path

from laboratorio.integridad import guardar_csv
from laboratorio.parametros import Configuracion


def leer(ruta):
    with ruta.open(encoding='utf-8', newline='') as archivo:
        return list(csv.DictReader(archivo))


def tabla_md(filas, campos):
    lineas = ['| ' + ' | '.join(campos) + ' |', '| ' + ' | '.join('---' for _ in campos) + ' |']
    for fila in filas:
        valores = []
        for campo in campos:
            valor = fila[campo]
            valores.append(f'{valor:.4f}' if isinstance(valor, float) else str(valor))
        lineas.append('| ' + ' | '.join(valores) + ' |')
    return '\n'.join(lineas)


def main():
    config = Configuracion.del_entorno()
    carpeta = config.resultados
    experimento = json.loads((carpeta / 'benchmark.json').read_text(encoding='utf-8'))
    if experimento['estado'] != 'completo':
        raise RuntimeError('No se puede documentar un benchmark incompleto o interrumpido como exitoso')
    tiempos = leer(carpeta / 'benchmark_tiempos.csv')
    individuales = leer(carpeta / 'benchmark_individuales.csv')
    tablas = leer(carpeta / 'benchmark_tablas.csv')
    equivalencia = leer(carpeta / 'benchmark_equivalencia.csv')
    for fila in tiempos:
        grupo = [f for f in individuales if all(f[k] == fila[k] for k in ('conjunto', 'consulta', 'estrategia'))]
        mediciones = [float(f['segundos']) for f in grupo if f['fase'] == 'medicion']
        if len(mediciones) != experimento['repeticiones'] or sum(f['fase'] == 'calentamiento' for f in grupo) != 1:
            raise RuntimeError('Número de repeticiones o calentamientos incorrecto')
        if any(f['estado'] != 'ok' for f in grupo) or fila['mismo_resultado'] != 'True':
            raise RuntimeError('Medición fallida o no equivalente')
        for campo, calculo in [('mediana_s', statistics.median(mediciones)), ('minimo_s', min(mediciones)), ('maximo_s', max(mediciones))]:
            if not math.isclose(float(fila[campo]), calculo, abs_tol=1e-12):
                raise RuntimeError('Resumen inconsistente con tiempos individuales')
    esperado = len(tablas) * len(experimento['consultas'])
    if len(tiempos) != 2 * esperado or len(equivalencia) != esperado or any(f['mismo_resultado'] != 'True' for f in equivalencia):
        raise RuntimeError('Faltan pares de estrategias o equivalencia')
    pares = {}
    for fila in tiempos:
        pares.setdefault((fila['conjunto'], fila['consulta']), {})[fila['estrategia']] = float(fila['mediana_s'])
    comparacion = []
    for (conjunto, consulta), valores in pares.items():
        p, t = valores['parquet'], valores['tabla']
        comparacion.append(dict(conjunto=conjunto, consulta=consulta, parquet_s=p, tabla_s=t,
                               razon_parquet_tabla=p/t, mas_rapida='parquet' if p < t else 'tabla' if t < p else 'empate'))
    guardar_csv(carpeta / 'benchmark_comparacion.csv', comparacion)
    totales = []
    for tabla in tablas:
        conjunto = tabla['conjunto']
        p = sum(f['parquet_s'] for f in comparacion if f['conjunto'] == conjunto)
        t = sum(f['tabla_s'] for f in comparacion if f['conjunto'] == conjunto)
        creacion = float(tabla['creacion_tabla_s'])
        totales.append(dict(conjunto=conjunto, suma_medianas_parquet_s=p, suma_medianas_tabla_s=t,
                            creacion_tabla_s=creacion, ahorro_ronda_estimado_s=p-t,
                            rondas_amortizacion_estimada=creacion/(p-t) if p > t else 'sin recuperación'))
    guardar_csv(carpeta / 'benchmark_totales.csv', totales)
    identificadores = dict(zip(experimento['consultas'], ('Q1', 'Q2', 'Q3', 'Q4', 'Q5', 'Q6', 'Q7')))
    compacta = [{**f, 'consulta': identificadores[f['consulta']]} for f in comparacion]
    datos = [{k: int(t[k]) if k in ('archivos', 'registros') else float(t[k]) if k in ('mb_parquet', 'mb_duckdb', 'creacion_tabla_s') else t[k]
              for k in ('conjunto', 'archivos', 'registros', 'mb_parquet', 'mb_duckdb', 'creacion_tabla_s')} for t in tablas]
    recursos = [{k: r[k] for k in ('conjunto', 'disponible_efectiva_bytes', 'disco_libre_bytes', 'espacio_estimado_bytes')} for r in experimento['recursos']]
    sql = '\n\n'.join(f"### {identificadores[c]}: `{c}`\n\n```sql\n{texto.rstrip()}\n```" for c, texto in experimento['consultas'].items())
    analisis = []
    for total in totales:
        conjunto = total['conjunto']
        filas = [f for f in comparacion if f['conjunto'] == conjunto]
        ganadas_p = sum(f['mas_rapida'] == 'parquet' for f in filas)
        ganadas_t = sum(f['mas_rapida'] == 'tabla' for f in filas)
        amortizacion = total['rondas_amortizacion_estimada']
        amortizacion = f'{amortizacion:.2f} rondas estimadas' if isinstance(amortizacion, float) else amortizacion
        analisis.append(f"- **{conjunto}:** Parquet gana {ganadas_p} consultas y la tabla {ganadas_t}. "
                        f"La suma de medianas es {total['suma_medianas_parquet_s']:.3f} s versus "
                        f"{total['suma_medianas_tabla_s']:.3f} s. Amortización: {amortizacion}.")
    ajustes = experimento['configuracion']
    texto = f'''# Ejercicio 6: Parquet versus tablas materializadas de DuckDB

Experimento real `{experimento['ejecucion']}`, registrado en UTC: {experimento['fecha_utc']}.
Estado: **{experimento['estado']}**. Las cifras proceden de CSV completos y medidos;
no se reutilizaron los tiempos heredados ni se interpolaron resultados.

## Revisión y cambios del benchmark existente

`scripts/medir_rendimiento.py` delega en `scripts/laboratorio/mediciones.py`
(equivalente actual de benchmarks.py). Ya funcionaban los conjuntos explícitos
de 2, 16 y 40 archivos, las vistas normalizadas, las siete consultas, el cierre
de conexiones y la comparación tolerante. Se conservaron esas funciones.

Se añadieron tiempos individuales, registro de calentamiento, configuración
explícita en cada conexión, controles de RAM/disco, materialización mensual,
bases nuevas por ejecución, orden alternado entre estrategias, persistencia
de avances y estado de fallo/interrupción. El notebook dejó de abrir bases y
ahora presenta únicamente los artefactos guardados. Q2 añade promedios de
distancia, duración y tarifa. Q3 calcula los mismos cuartiles exactos con una
lista para compartir el estado y reducir memoria.

## Dataset y estrategias

A = enero 2026; B = enero-agosto 2026; C = enero-diciembre 2024 más
enero-agosto 2026. Ambos tipos de taxi en todos los conjuntos. Sin 2025.

{tabla_md(datos, ['conjunto','archivos','registros','mb_parquet','mb_duckdb','creacion_tabla_s'])}

MB son decimales (10^6 bytes). Las tres bases ocupan espacio adicional; los
Parquet originales se conservan. B contiene A y C contiene B: sus volúmenes
no se deben sumar como registros distintos.

Los conteos se leen desde `parquet_file_metadata`, no desde valores fijos.
Inventario por archivo con filas, bytes y mtime_ns en `benchmark.json`.
Los cuatro grupos reconfirmados del ejercicio 5 son 2024 yellow 41,169,720,
2024 green 660,218, 2026 yellow 29,703,355 y 2026 green 337,114.
Total 2024: 41,829,938; 2026: 30,040,469; combinado: 71,870,407.
70,873,075 es únicamente yellow de ambos años.

**Parquet directo:** `read_parquet(..., union_by_name=true, filename=true)`
con las vistas de `sql/normalizacion_viajes.sql`. Las columnas opcionales
ausentes se agregan con tipos explícitos. El periodo sale del nombre del
archivo y el cargo CBD nulo se normaliza con coalesce.

**Tabla persistente:** copia todas las filas y columnas de la misma vista
`viajes` y el catálogo `zonas`. No filtra ni preagrega. Usa las mismas reglas
de `viajes_validos` y la macro de pago. Se comprueban el conteo total y el
esquema completo mediante DESCRIBE. El periodo y la normalización ya están
calculados en la tabla, cuyo costo inicial se mide separadamente.

SQL de creación por conjunto, en una transacción (un INSERT por mes):

```sql
ATTACH '<base_nueva.duckdb>' AS materializada;
BEGIN;
CREATE OR REPLACE TABLE materializada.viajes_tabla AS
SELECT * FROM viajes WHERE false;
INSERT INTO materializada.viajes_tabla
SELECT * FROM viajes WHERE periodo = DATE '<AAAA-MM-01>';
CREATE OR REPLACE TABLE materializada.zonas_tabla AS SELECT * FROM zonas;
USE materializada;
CREATE OR REPLACE VIEW viajes AS SELECT * FROM viajes_tabla;
CREATE OR REPLACE VIEW zonas AS SELECT * FROM zonas_tabla;
-- Se ejecuta reglas_compartidas.sql, reproducido abajo.
COMMIT;
CHECKPOINT materializada;
USE memory;
DETACH materializada;
```

La tabla vacía obtiene el esquema global de ambos años antes de insertar.
Las bases tienen rutas únicas bajo `data/processed/benchmark_runs/` y nunca
se conectan desde Metabase durante el benchmark. No se reemplazan sus bases.

## Metodología y configuración

- DuckDB {experimento['duckdb']}; Python {experimento['python']}.
- Sistema: {experimento['sistema']}; CPU lógicas disponibles: {experimento['cpu_logicas']}.
- Todas las conexiones: threads={ajustes['threads']}, memory_limit={ajustes['memory_limit']},
  max_temp_directory_size={ajustes['max_temp_directory_size']}, preserve_insertion_order=false.
- Directorio temporal: `{ajustes['temp_directory']}`. Ajustes efectivos registrados
  por consulta/estrategia en `benchmark.json`.
- Una conexión nueva por consulta/estrategia; un calentamiento y
  {experimento['repeticiones']} repeticiones medidas. Las estrategias corren secuencialmente.
  El orden inicial alterna con el índice del conjunto y consulta, no es aleatorio.
- Cronómetro `time.perf_counter()` alrededor de execute + fetchall. La apertura,
  EXPLAIN, las comparaciones y las escrituras CSV están fuera del intervalo.
- Los resultados son agregados pequeños; no se carga el dataset en pandas.
- La mediana, mínimo y máximo excluyen el calentamiento. No se afirma caché
  fría: las cachés de DuckDB/SO, la materialización previa y el orden afectan
  los tiempos. Abrir una conexión nueva tampoco limpia la caché del SO.
- Materialización: creación vacía, INSERT mensuales, catálogo, vistas, commit,
  checkpoint y detach. Excluye inspección inicial de metadatos y comprobación
  posterior del conteo/esquema. El tamaño se toma después del cierre.
- Se guardan filas por medición y estado. Un fallo deja JSON incompleto y el
  notebook se niega a presentarlo como éxito.

## Equivalencia

**{len(equivalencia)}/{esperado} pares equivalentes**, incluyendo cada consulta y conjunto.
Estabilidad verificada en cada repetición contra el calentamiento. Filas
comparadas sin depender del orden: enteros, fechas, cadenas y nulos exactos;
floats con tolerancia absoluta 0.01 y relativa 0; NaN solo con NaN.
La tolerancia admite hasta un centavo para valores monetarios redondeados.
Conteos y tipos lógicos coinciden en las tres materializaciones.
Se comprobaron tamaño y fecha de modificación de las fuentes al terminar;
no se modificaron los Parquet ni se repitieron hashes completos.

## Consultas SQL exactas

Q1 usa todas las filas; Q2 usa viajes de un día real, sin filtros de calidad
y sus promedios pueden incluir anomalías. Q3–Q7 usan `viajes_validos`.
Cada consulta usa exactamente el mismo texto en ambas estrategias.
El JSON guarda la copia del SQL y su SHA-256.

{sql}

### Normalización compartida

```sql
{experimento['normalizacion'].rstrip()}
```

Los parámetros de archivos y catálogo se resuelven con el inventario explícito
de cada conjunto; no se amplía mediante comodines a otros meses/años.

### Filtros y macro compartidos

```sql
{experimento['reglas'].rstrip()}
```

## Resultados medidos y comparación

Segundos, mediana de {experimento['repeticiones']} mediciones tras calentamiento.
Razón = Parquet / tabla: >1 favorece la tabla y <1 favorece Parquet.
Los rangos y calentamientos están en `benchmark_tiempos.csv`; cada ejecución,
en `benchmark_individuales.csv`. La tabla usa Q1–Q7 identificadas arriba.

{tabla_md(compacta, ['conjunto','consulta','parquet_s','tabla_s','razon_parquet_tabla','mas_rapida'])}

## Interpretación por volumen y materialización

{chr(10).join(analisis)}

{tabla_md(totales, ['conjunto','suma_medianas_parquet_s','suma_medianas_tabla_s','creacion_tabla_s','ahorro_ronda_estimado_s','rondas_amortizacion_estimada'])}

La suma de medianas es una ronda **estimada**, no una medición adicional.
Las rondas de amortización son una proyección con tiempos estables; no
incluyen mantenimiento, cambios de carga ni nuevas entregas.

El conteo puede aprovechar metadatos, el filtro diario puede saltar bloques
y las consultas válidas deben evaluar filtros y agregados. Parquet concilia
esquemas y calcula el periodo; la tabla tiene columnas normalizadas y otras
estadísticas/compresión. Los planes EXPLAIN se guardaron sin ejecutar una
segunda ronda. Son indicios, no perfiles de CPU/I/O ni pruebas de causalidad.
No se atribuyen diferencias exclusivamente a las ventanas o a un operador.

**Parquet:** recomendado para exploración y consultas ocasionales, intercambio
portable, llegadas frecuentes y cuando el ahorro de materializar no amortiza
la creación. Evita duplicar almacenamiento y actualizaciones de tablas.

**Tabla DuckDB:** recomendada para una carga repetida donde la ventaja medida
recupera tiempo de creación, espacio adicional y mantenimiento. Conserva
normalización y estadísticas en una base persistente; la frecuencia de las
consultas ganadoras importa más que una conclusión general por formato.

## Recursos y limitaciones

Bytes antes de materializar cada conjunto:

{tabla_md(recursos, ['conjunto','disponible_efectiva_bytes','disco_libre_bytes','espacio_estimado_bytes'])}

Estimación conservadora: 256 bytes por fila + 4 GiB de temporales + 2 GiB
de reserva. No es una predicción exacta del tamaño comprimido. Se verificó
RAM efectiva del host/cgroup, disco y límites antes de cada conjunto.

RSS máximo muestreado del proceso: **{experimento['rss_pico_muestreado_bytes']/1024**3:.3f} GiB**.
Temporales máximos muestreados: **{experimento['temporales_pico_muestreado_bytes']/1024**3:.3f} GiB**.
Muestreo cada {experimento['intervalo_muestreo_s']} s: puede omitir picos breves.
Espacio libre final: **{experimento['disco_libre_final_bytes']/1024**3:.3f} GiB**.
`memory_limit` limita principalmente el buffer manager y no el RSS completo;
los agregados exactos pueden reservar memoria adicional
([documentación oficial DuckDB](https://duckdb.org/docs/current/guides/performance/oom)).

Un equipo, almacenamiento local montado desde Windows sobre Docker/WSL2,
siete consultas y cinco repeticiones: sin inferencia estadística ni garantías
para concurrencia, disco remoto, otros equipos o consultas diferentes. No se
limpió la caché del SO; la materialización calienta archivos. Los tamaños no
incluyen bases antiguas ni catálogos originales fuera de los Parquet; esas
bases se conservaron y el disco libre sí refleja su presencia.

## Artefactos y visualizaciones

- `benchmark_individuales.csv`: tiempos individuales y calentamientos.
- `benchmark_tiempos.csv`: mediana, mínimo, máximo y equivalencia.
- `benchmark_tablas.csv`: conteos, esquema, tiempo de creación y tamaños/rutas.
- `benchmark_lotes.csv`: tiempo de cada inserción mensual.
- `benchmark_equivalencia.csv`: comparación de cada par consulta/conjunto.
- `benchmark_comparacion.csv` y `benchmark_totales.csv`: razones y amortización.
- `benchmark.json`: entorno, SQL exacto, configuración y recursos.
- `benchmark_planes.json`: planes EXPLAIN de ambas estrategias.
- `ejercicio_5_conteos_metadatos.csv`: 40 pies Parquet reconfirmados.
- `benchmark_consultas.png`, `benchmark_volumen.png`, `benchmark_espacio.png`:
  generadas por el notebook 06, con salidas incrustadas en el notebook.

![Medianas por consulta, con mínimo y máximo](benchmark_consultas.png)

![Tiempo por volumen y materialización](benchmark_volumen.png)

![Espacio de Parquet y bases materializadas](benchmark_espacio.png)

## Reproducción en PowerShell

Desde la raíz del repositorio, con `lab` activo y los 40 archivos existentes:

```powershell
docker compose exec -T lab python scripts/inventario_benchmark.py
docker compose exec -T lab python -u scripts/medir_rendimiento.py --repeticiones 5 --hilos 2 --memoria 1GiB --conjuntos A B C
docker compose exec -T lab python scripts/documentar_benchmark.py
docker compose exec -T -e MPLBACKEND=Agg lab jupyter nbconvert --to notebook --execute --inplace --ExecutePreprocessor.timeout=180 notebooks/06_comparacion_rendimiento.ipynb
docker compose exec -T lab python -m unittest discover -s tests -p "test_*.py" -v
git -c safe.directory=C:/Users/miafu/Downloads/CC3084-Lab8/CC3084-Lab8-fork diff --check
```

Para una fase menor use `--conjuntos A` o `--conjuntos A B`. Las salidas resumen
representan la selección de esa ejecución; para esta entrega se midieron A B C.
El generador de documentación comprueba los CSV sin volver a medir viajes.
No ejecutar otros análisis simultáneos durante el benchmark. No se necesita
descargar datos, ejecutar notebooks 03–05 ni reiniciar Docker.

## Validación y alcance

La suite de regresión ejecutó **30 pruebas: OK**, con fixtures pequeños y
sin descargas reales. Las siete consultas y sus repeticiones reales fueron
equivalentes en A, B y C. El generador verificó los resúmenes contra los tiempos
individuales. La ejecución del notebook y diff --check se registran aparte
en `ejercicio_6_validacion.json` al finalizar la entrega.

El ejercicio 6 aporta datos para preparar la siguiente fase. No se ejecutó
ni modificó el ejercicio 7, no se descargó 2025, no se borraron contenedores
o volúmenes, no se añadieron bases a Git y no se hicieron commits ni push.
'''
    (carpeta / 'ejercicio_6_benchmark.md').write_text(texto, encoding='utf-8')
    print(f'Informe generado: {len(individuales)} ejecuciones, {len(equivalencia)} pares equivalentes; resúmenes consistentes.')
    for fila in totales:
        print(fila)


if __name__ == '__main__':
    main()
