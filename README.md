# Lab 8 - DuckDB

**Universidad del Valle de Guatemala · CC3084 - Data Science · Ciclo 2, 2026.**
Laboratorio 8 con datos de **NYC TLC Trip Record Data**.

Este es el [fork desarrollado por nuestro equipo](https://github.com/miafuentes30/CC3084-Lab8),
derivado del [repositorio original del docente](https://github.com/menene/duckdb).
La relación de fork se verificó con la API pública de GitHub: `fork=true`,
`parent=menene/duckdb`.

| Integrante | Correo institucional |
|---|---|
| [DufreyM](https://github.com/DufreyM) | [mej23648@uvg.edu.gt](mailto:mej23648@uvg.edu.gt) |
| [tismajo](https://github.com/tismajo) | [gir23559@uvg.edu.gt](mailto:gir23559@uvg.edu.gt) |
| [miafuentes30](https://github.com/miafuentes30) | [fue23775@uvg.edu.gt](mailto:fue23775@uvg.edu.gt) |

## Trabajo con fork

Clone el fork del equipo, no el repositorio docente:

```powershell
git clone https://github.com/miafuentes30/CC3084-Lab8.git
Set-Location CC3084-Lab8
git remote -v
```

Opcionalmente, agregue `upstream` **solo si todavía no existe**:

```powershell
git remote add upstream https://github.com/menene/duckdb.git
git fetch upstream
```

En la copia de trabajo actual, `origin` y `upstream` ya están configurados.
La entrega es la URL del fork. Los commits nuevos deben ser descriptivos y
acreditar las contribuciones confirmadas por sus autores.

El equipo comenzó el trabajo entre el **5 y el 7 de octubre de 2026** sobre
una descarga ZIP y posteriormente migró al fork, creado el **12 de octubre**.
Ese antecedente fue informado por el equipo: el historial Git disponible
conserva únicamente dos commits docentes del 1 de octubre. Por acuerdo del
equipo, los commits de migración usarán fechas retrospectivas del 5 al 7 de
octubre mediante `GIT_AUTHOR_DATE` y `GIT_COMMITTER_DATE`. Estas fechas representan
el período de desarrollo declarado; los commits se crearán después de la
migración y también incluirán documentación y evidencias generadas posteriormente.
Los registros de ejecución conservan sus propias fechas. Esta reconstrucción
no acredita que existieran commits Git durante el trabajo con ZIP ni modifica
los autores o fechas del historial docente.

## Estructura

```text
.
├── data/
│   ├── raw/                    # Parquet por tipo/año; catálogo en zonas/
│   └── processed/              # Bases DuckDB y temporales locales
├── notebooks/                 # Seis notebooks finales, ejercicios 3–8
├── scripts/
│   ├── laboratorio/           # Módulos compartidos de cálculo y publicación
│   ├── comprobar_entorno.py
│   ├── descargar_taxis.py
│   ├── validar_taxis.py
│   ├── medir_rendimiento.py
│   ├── inventario_benchmark.py
│   ├── documentar_benchmark.py
│   ├── construir_tablero.py
│   ├── estado_metabase.py
│   └── documentar_entrega.py
├── sql/                       # Inspección, exploración, integración y métricas
├── docs/
│   ├── resultados/            # CSV, JSON, PNG y tablero HTML del equipo
│   └── historial/             # Material académico de la migración
├── tests/                     # Fixtures y regresión sin descargas reales
├── Dockerfile
├── metabase.Dockerfile
├── docker-compose.yml
├── requirements.txt
├── .dockerignore
├── .gitignore
├── .env.example
└── README.md
```

La implementación activa está en la raíz. `data/raw` y `data/processed`
conservan archivos locales y están excluidos de Git, salvo sus `.gitkeep`.
El SQL y los módulos normalizan columnas y aplican reglas de calidad comunes;
pandas se utiliza para resultados agregados pequeños.

## Requisitos

- Git, Docker Desktop con contenedores Linux y Docker Compose v2 (`docker compose`).
- Espacio para imágenes y dependencias, unos **2.07 GB de Parquet** en el corte
  entregado y las bases derivadas. Para reproducir el benchmark completo,
  reserve **30 GiB libres**: el script comprueba una estimación conservadora
  de aproximadamente 24.84 GB antes de materializar C.
- Recomendación para ejecutar análisis y Metabase juntos: 8 GiB de RAM o más
  disponibles para Docker/WSL2. El benchmark utilizó dos hilos y un buffer de
  1 GiB, pero registró **2.284 GiB de RSS**; ese límite no cubre toda la memoria
  del proceso. El script comprueba recursos y se detiene si no son suficientes.
- Puertos libres para JupyterLab y Metabase. Compose utiliza 8888/3000 sin
  variables; `.env.example` propone **8889/3001**. La ejecución entregada
  utilizó **8890/3002**, sin exigir esos puertos en otro equipo.

La primera construcción descarga imágenes y paquetes. Las versiones están
fijadas en [requirements.txt](requirements.txt) y los Dockerfiles; el driver
DuckDB de Metabase debe mantenerse alineado con DuckDB Python.

Copie `.env.example` a `.env`, edite `LAB_PORT` y `METABASE_PORT`, y configure
credenciales únicamente en el ambiente local. `.env` y archivos de secretos
están ignorados; `.env.example` contiene valores públicos y credenciales vacías.

## Datos

Fuente oficial: [NYC TLC Trip Record Data](https://www.nyc.gov/site/tlc/about/tlc-trip-record-data.page).
El corte entregado contiene **64 Parquet y 121,184,384 registros originales**:

| Año | Cobertura por tipo | Yellow | Green |
|---|---|---:|---:|
| 2024 | Enero–diciembre, 12 archivos | 41,169,720 | 660,218 |
| 2025 | Enero–diciembre, 12 archivos | 48,722,602 | 591,375 |
| 2026 | Enero–agosto, 8 archivos | 29,703,355 | 337,114 |

Los archivos se guardan en `data/raw/{tipo}/{anio}/`; el catálogo está en
`data/raw/zonas/`. Dentro de Docker se acceden por `/workspace/data`.
Para tendencias interanuales se compara enero–agosto de los tres años y
se distinguen registros originales de viajes válidos.

Parquet y bases DuckDB no se incluyen en GitHub por su volumen y porque pueden
reconstruirse mediante los scripts. Se incluyen inventarios, hashes, agregados
y salidas para acreditar los resultados: [evidencia por ejercicio](docs/resultados/indice_resultados.md).
Las publicaciones oficiales pueden ampliarse después de este corte.

## Material a entregar

| Material | Ubicación |
|---|---|
| Código y descarga incremental | [scripts](scripts/) y [módulos](scripts/laboratorio/) |
| 44 consultas analíticas y reglas comunes | [sql](sql/) |
| Seis notebooks con salidas | [notebooks](notebooks/) |
| Documentación y evidencia de consultas | [índice de resultados](docs/resultados/indice_resultados.md), notebooks y JSON de SQL |
| Scripts y resultados del benchmark | [informe del ejercicio 6](docs/resultados/ejercicio_6_benchmark.md) |
| Indicadores, visualizaciones y tablero local | [tablero con filtros](docs/resultados/tablero_indicadores.html) y carpetas de ejercicios 7/8 |
| Discusión y resumen de los nueve ejercicios | [discusión final](docs/discusion_final.md) y [entrega final](docs/entrega_final.md) |
| Reproducción del laboratorio | Este README |

La publicación autenticada en Metabase sigue pendiente por credenciales;
la evidencia local y el código de publicación están incluidos. No se entrega
una captura histórica como prueba de publicación actual.

## Documentación del equipo

Las siguientes instrucciones utilizan los servicios `lab` y `metabase` y
se ejecutan desde la raíz del clon en PowerShell. La
[arquitectura modular](docs/arquitectura_modular.md) describe las responsabilidades.

### Cómo levantar el ambiente

Después de clonar e ingresar al directorio como se indicó arriba:

```powershell
if (-not (Test-Path -LiteralPath .env)) { Copy-Item -LiteralPath .env.example -Destination .env }
notepad .env
docker compose build
docker compose up -d
docker compose ps
docker compose exec -T lab python scripts/comprobar_entorno.py
```

Si `.env` ya existe, conserve su configuración. Abra JupyterLab en
`http://localhost:<LAB_PORT>` y Metabase en `http://localhost:<METABASE_PORT>`.
Con el ejemplo suministrado: `http://localhost:8889` y `http://localhost:3001`.
Si un servicio falla, consulte `docker compose logs lab` o
`docker compose logs metabase`. El diagnóstico comprueba versiones,
persistencia y disponibilidad de los servicios.

Para detenerlos conservando contenedores, datos y volumen de Metabase:

```powershell
docker compose stop
```

Vuelva a iniciarlos con `docker compose start`. No borre volúmenes para
reproducir el laboratorio. Metabase monta los datos en lectura; los cálculos
de indicadores crean bases nuevas para evitar conflictos con lectores activos.

### Cómo descargar los datos

Opciones de `scripts/descargar_taxis.py`:

| Opción | Uso |
|---|---|
| `--anios 2024`, `2025` o `2026` | Selecciona uno o varios años; predeterminado: 2026 |
| `--taxi yellow` / `--taxi green` | Selecciona tipo; `all` descarga ambos por defecto |
| `--meses 1 2 3` | Limita meses; por defecto revisa los doce |
| `--solo-listar` | Consulta publicaciones oficiales y tamaños sin descargar |

Para obtener todos los archivos publicados y validar los tres años:

```powershell
docker compose exec -T lab python scripts/descargar_taxis.py --anios 2024 2025 2026
docker compose exec -T lab python scripts/validar_taxis.py --anios 2024 2025 2026
```

Para reproducir específicamente la cobertura entregada:

```powershell
docker compose exec -T lab python scripts/descargar_taxis.py --anios 2024 2025
docker compose exec -T lab python scripts/descargar_taxis.py --anios 2026 --meses 1 2 3 4 5 6 7 8
docker compose exec -T lab python scripts/validar_taxis.py --anios 2024 2025 2026
```

Ejemplos por tipo:

```powershell
docker compose exec -T lab python scripts/descargar_taxis.py --anios 2025 --taxi yellow
docker compose exec -T lab python scripts/descargar_taxis.py --anios 2025 --taxi green
```

La descarga es incremental: omite archivos íntegros, descubre enlaces de TLC,
usa temporales y valida antes de publicar cada archivo. Distingue meses no
publicados de errores de red, HTTP o integridad; los fallos generan salida
no exitosa. El validador comprueba tamaño, lectura Parquet y SHA-256, y guarda
`verificacion_descarga.csv` y `.json`. Los pasaportes conservan ejecuciones previas.
El validador acepta `--anios` y verifica ambos tipos; no admite `--meses` ni `--taxi`.
Si TLC publica meses posteriores de 2026, puede exigirlos aunque el corte
entregado conserve enero–agosto; consulte su inventario y no confunda ambas coberturas.

### Cómo ejecutar el análisis

Abra JupyterLab, entre a `notebooks/` y ejecute el notebook de la etapa elegida.
Las salidas ya guardadas pueden consultarse sin repetir las consultas.

| Orden | Notebook | Datos y función |
|---|---|---|
| 1 | [03_inspeccion_parquet](notebooks/03_inspeccion_parquet.ipynb) | 2026: conteos, esquemas y calidad |
| 2 | [04_exploracion_viajes](notebooks/04_exploracion_viajes.ipynb) | 2026: trece consultas y gráficas exploratorias |
| 3 | [05_integracion_2024](notebooks/05_integracion_2024.ipynb) | 2024/2026: integración y comparación de esquemas |
| 4 | [06_comparacion_rendimiento](notebooks/06_comparacion_rendimiento.ipynb) | Presenta los CSV del benchmark existente |
| 5 | [07_panel_indicadores](notebooks/07_panel_indicadores.ipynb) | Presenta agregados y nueve indicadores de 2024/2026 |
| 6 | [08_integracion_tres_anios](notebooks/08_integracion_tres_anios.ipynb) | Presenta agregados de 2024/2025/2026 y periodos comparables |

Los notebooks 03–05 consultan datos reales; 06–08 presentan agregados y
evidencia existentes. No es necesario repetir el benchmark al ejecutar 06.
05 omite operaciones de red por defecto; `LAB8_EJECUTAR_RED=1` las habilita
explícitamente. Para reconstruir agregados, use la última sección.

Alternativa con nbconvert: elija el comando correspondiente, sin ejecutar
todo el bloque automáticamente si solo necesita una etapa.

```powershell
docker compose exec -T lab jupyter nbconvert --to notebook --execute --inplace --ExecutePreprocessor.timeout=600 notebooks/03_inspeccion_parquet.ipynb
docker compose exec -T lab jupyter nbconvert --to notebook --execute --inplace --ExecutePreprocessor.timeout=600 notebooks/04_exploracion_viajes.ipynb
docker compose exec -T lab jupyter nbconvert --to notebook --execute --inplace --ExecutePreprocessor.timeout=600 notebooks/05_integracion_2024.ipynb
docker compose exec -T lab jupyter nbconvert --to notebook --execute --inplace notebooks/06_comparacion_rendimiento.ipynb
docker compose exec -T lab jupyter nbconvert --to notebook --execute --inplace notebooks/07_panel_indicadores.ipynb
docker compose exec -T lab jupyter nbconvert --to notebook --execute --inplace notebooks/08_integracion_tres_anios.ipynb
```

Para ejecutar SQL modular dentro de JupyterLab:

```python
from pathlib import Path
import sys
raiz = next(p for p in (Path.cwd(), *Path.cwd().parents) if (p / "scripts/laboratorio").is_dir())
sys.path.insert(0, str(raiz / "scripts"))
from laboratorio.sesion_consultas import Analisis
with Analisis(anios=[2026], opciones_duckdb={"threads": 2, "memory_limit": "1GiB"}) as a:
    resultado = a.consulta("exploracion/01_resumen_mensual.sql")
```

`Analisis.leer_sql()` resuelve archivos explícitos. Las vistas usan `union_by_name`,
nulos tipados y [reglas compartidas](sql/reglas_compartidas.sql). `LAB8_ROOT`
permite reubicar datos/resultados. Evite ejecutar indiscriminadamente todas
las consultas sobre el conjunto completo.

### Cómo reproducir los benchmarks

El ejercicio 6 compara Parquet directo (`read_parquet`) con tablas persistentes
que contienen las mismas filas y columnas normalizadas, sin preagregar.
La creación y el espacio de las tablas se miden por separado.

| Conjunto | Cobertura, ambos taxis | Archivos | Registros originales |
|---|---|---:|---:|
| A | Enero 2026 | 2 | 3,765,161 |
| B | Enero–agosto 2026 | 16 | 30,040,469 |
| C | 2024 completo + enero–agosto 2026 | 40 | 71,870,407 |

2025 está excluido del benchmark. Se usan dos hilos, `memory_limit=1GiB`,
un calentamiento y cinco mediciones por consulta/estrategia. Se guardaron
210 mediciones, 42 calentamientos y 21 comparaciones equivalentes.

Solo si necesita reconstruir las mediciones:

```powershell
docker compose exec -T lab python scripts/inventario_benchmark.py
docker compose exec -T lab python -u scripts/medir_rendimiento.py --repeticiones 5 --hilos 2 --memoria 1GiB --conjuntos A B C
docker compose exec -T lab python scripts/documentar_benchmark.py
```

Puede seleccionar `--conjuntos A` o `--conjuntos A B`. Para volver a dibujar
los resultados guardados, ejecute únicamente el notebook 06.
`docs/resultados/benchmark_individuales.csv` conserva tiempos; `benchmark_tiempos.csv`
resume mediana/mínimo/máximo; `benchmark_tablas.csv` registra filas, creación y
tamaños. Los CSV de equivalencia/comparación/totales y los JSON de configuración
y planes completan la evidencia. Las bases quedan excluidas de Git en
`data/processed/benchmark_runs/`.

**Recursos:** consulte los requisitos antes de recrear C; el script revisa RAM
y disco y materializa por mes. No ejecute análisis competidores a la vez.
La caché del SO no se controla y el calentamiento no garantiza una caché fría.
En A/B la suma de medianas favorece a la tabla; en C favorece a Parquet.
Consulte [el informe del ejercicio 6](docs/resultados/ejercicio_6_benchmark.md)
para los costos iniciales, las razones y las limitaciones.

### Cómo generar los resultados principales

Para **presentar los resultados incluidos**, ejecute 07/08 o abra el
[tablero HTML local](docs/resultados/tablero_indicadores.html), que filtra
tipo de taxi, año y cobertura comparable. Las gráficas no vuelven a consultar
el dataset completo.

Para **reconstruir indicadores** con los Parquet existentes, primero 2024/2026:

```powershell
docker compose exec -T lab python -u scripts/construir_tablero.py --solo-calcular --anios 2024 2026
docker compose exec -T lab jupyter nbconvert --to notebook --execute --inplace notebooks/07_panel_indicadores.ipynb
```

Después de incorporar y validar 2025:

```powershell
docker compose exec -T lab python -u scripts/construir_tablero.py --solo-calcular --anios 2024 2025 2026 --reutilizar-iniciales
docker compose exec -T lab jupyter nbconvert --to notebook --execute --inplace notebooks/08_integracion_tres_anios.ipynb
```

La reutilización comprueba fuentes y hashes del SQL; conserva veinte meses
iniciales y calcula los doce nuevos. En otro equipo con Parquet descargados
nuevamente, reconstruya primero los agregados iniciales para renovar esa
evidencia. Sin `--reutilizar-iniciales` se recalculan los años seleccionados.
Hay nueve indicadores: demanda diaria, monto mediano, pago 0/nulo, efectivo,
propina con tarjeta, CBD, velocidad en Manhattan, aeropuertos y exclusión.
Se procesan meses con dos hilos/1 GiB y comparaciones anuales con un hilo/1 GiB.

Los CSV, JSON, interpretaciones y nueve PNG por etapa se guardan en
`docs/resultados/ejercicio_7/` y `ejercicio_8/`. La última base agregada queda
identificada en `docs/resultados/indicadores.json`. Si los meses ya están
guardados, `--reanudar-resumen --base data/processed/<base>.duckdb` retoma
solamente el resumen anual. No se carga todo en pandas.

**Estado de Metabase:** el registro [metabase_estado.json](docs/resultados/metabase_estado.json)
documenta servicio saludable y publicación pendiente por falta de credenciales.
No hay evidencia de un tablero autenticado publicado. El tablero local
funciona con los agregados incluidos y es una alternativa independiente.

Para publicar, abra Metabase en su puerto configurado, complete el usuario
administrador si es necesario y proporcione credenciales autorizadas mediante
variables de entorno. En PowerShell, sin escribir la clave en el comando:

```powershell
$env:MB_EMAIL = Read-Host 'Correo de Metabase'
$claveMetabase = Read-Host 'Clave de Metabase' -AsSecureString
$env:MB_PASSWORD = [System.Net.NetworkCredential]::new('', $claveMetabase).Password
try {
    docker compose exec -T -e MB_EMAIL -e MB_PASSWORD lab python scripts/construir_tablero.py --solo-publicar
} finally {
    Remove-Item Env:MB_PASSWORD
}
```

También puede configurar `.env` antes de levantar un ambiente nuevo, sin
versionarlo. `--solo-publicar` no recalcula datos: conecta la última base
en lectura, crea o actualiza nueve preguntas y conserva IDs propios. Ofrece
filtros de taxi, año y fechas simples, sin archivar objetos ajenos.
Después de una publicación exitosa, `docs/resultados/metabase.json` guardará
el enlace `/dashboard/<id>` y los IDs. No use el estado del servicio como
evidencia de que el tablero fue publicado.

Los nueve ejercicios se resumen en [entrega final](docs/entrega_final.md);
las consultas y evidencias están enlazadas en [el índice](docs/resultados/indice_resultados.md).
La suite previamente ejecutada aprobó 32 pruebas. Para una validación nueva
explícita: `docker compose exec -T lab python -m unittest discover -s tests -p "test_*.py" -v`.
Los tests usan fixtures y API simulada; no acreditan publicación real.
`scripts/documentar_entrega.py` reconstruye el resumen desde la evidencia;
su opción `--pruebas-aprobadas` registra un conteo observado y no ejecuta tests.

Los commits se organizarán por funcionalidad, con autores confirmados y aprobación
previa. La planificación interna se conserva localmente y está excluida de Git.
No se versionan datos, bases, credenciales ni temporales, ni se modifican las
fechas de los commits docentes.

**Limitación de la copia actual:** faltan `docs/resultados/benchmark.json`,
`docs/resultados/ejercicio_8_verificacion_2025.json` y
`docs/resultados/indicadores.json`, entre otros metadatos previamente referenciados.
Los CSV, gráficas y notebooks con salidas se conservan. Antes de volver a ejecutar
el notebook 06, la celda de validación del 08, el generador del informe del benchmark
o la publicación del tablero, restaure los JSON originales correspondientes desde
un respaldo. No reconstruya tiempos ni evidencia ausente como si fueran registros originales.
