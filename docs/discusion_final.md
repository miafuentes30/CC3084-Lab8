# Ejercicio 9 — Discusión final

## 1. Características más útiles de DuckDB

La lectura directa de Parquet, el SQL analítico y la conciliación de esquemas
permitieron procesar viajes sin cargar todo en Python. Las vistas centralizaron
nombres, periodos y columnas opcionales. Los metadatos hicieron posible contar
registros con poco trabajo. Las agregaciones devolvieron resultados pequeños
para gráficas y tablero, manteniendo reglas comunes entre estrategias.

## 2. Consulta directa de Parquet

Evita una carga inicial y conserva un formato portable. Nuevos meses entran
mediante archivos explícitos y sus estadísticas pueden reducir lectura. Abrir
archivos y normalizar columnas tiene costo. En C, la suma de medianas fue
109.83 s para Parquet frente a 129.01 s para tablas. La ventaja depende de
la consulta; estos tiempos no representan una caché fría garantizada.

## 3. Tablas materializadas

Persisten normalización y estadísticas, pero exigen creación, espacio y
mantenimiento. La base C tardó 411.10 s en crearse y ocupó 2,182.10 MB
adicionales. Ganó cinco consultas y perdió dos; para la mezcla completa de C
no amortizó la creación. El tablero guarda únicamente agregados mensuales
pequeños: su costo difiere del de materializar todos los viajes y evita
repetir análisis grandes en cada visita.

## 4. Diferencias frente a pandas

Cargar todas las filas en pandas requiere memoria para columnas, índices y
copias. DuckDB agrega antes de devolver resultados y pandas aquí recibe
solamente CSV pequeños. No se midió una carga completa en pandas, por lo que
no se afirma una ventaja cuantitativa específica. El benchmark registró
2.284 GiB de RSS muestreado; limitar el buffer no limita todo el proceso.

## 5. Incorporación de archivos

Los argumentos por año/mes, carpetas por tipo y descarga incremental permitieron
añadir 2025 conservando 2024/2026. `union_by_name` y los nulos tipados manejaron
columnas opcionales. Los indicadores compartieron normalización y filtros.
Se reutilizaron veinte meses después de comprobar fuentes y SQL, y se
calcularon doce nuevos. Esto no sustituye revisar cambios semánticos y de calidad.

## 6. Automatización en producción

Conviene automatizar descubrimiento oficial, descarga atómica, validación,
inventarios y alertas de esquema/calidad. Los agregados deben actualizarse
incrementalmente, registrando versiones, periodos y fallos. La publicación
debe conservar IDs propios y obtener credenciales del ambiente. Escritores
y lectores deben coordinarse para que un fallo no sustituya resultados útiles.

## 7. Reproducibilidad

Las dependencias fijadas, el SQL modular, los conjuntos explícitos y los
CSV/JSON registran el experimento. Los notebooks de presentación reutilizan
evidencia sin repetir trabajo grande. Se comparó enero–agosto y se utilizaron
días calendario, considerando el año bisiesto. Se distinguieron filas
originales y válidas; datos y secretos permanecieron fuera de Git.

## 8. Aprendizajes sobre grandes volúmenes

El tamaño comprimido no determina la memoria necesaria para una consulta.
La comparación anual inicial agotó 1 GiB; se conservaron los meses guardados
y se separaron medias y medianas exactas sin aumentar memoria ni cargar
viajes en pandas. Procesar por mes y año redujo estados simultáneos.
La cobertura y la exclusión condicionan los resultados; una asociación
temporal no demuestra causalidad.

Evidencia: [benchmark](resultados/ejercicio_6_benchmark.md),
[indicadores iniciales](resultados/ejercicio_7/indicadores.json) y
[tres años](resultados/ejercicio_8/indicadores.json).
