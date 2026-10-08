# Evidencia de los ejercicios

Este índice enlaza archivos presentes en la entrega. Las salidas de los
notebooks y los agregados conservan los resultados reales sin repetir análisis.

| Ejercicio | Consultas, documentación y evidencia |
|---|---|
| 1 | [Diagnóstico](diagnostico_entorno.json), Dockerfiles y Compose de la raíz |
| 2 | [Validación integrada](verificacion_integrada.json), [inventario y hashes](verificacion_integrada.csv), [pasaportes](pasaporte/) |
| 3 | [Notebook de inspección](../../notebooks/03_inspeccion_parquet.ipynb), [trece SQL](../../sql/inspeccion/) |
| 4 | [Notebook exploratorio](../../notebooks/04_exploracion_viajes.ipynb), [trece SQL](../../sql/exploracion/) |
| 5 | [Notebook de integración](../../notebooks/05_integracion_2024.ipynb), [SQL](../../sql/integracion/), [conteos](ejercicio_5_conteos_metadatos.csv), [validación de 40 archivos](ejercicio_5_verificacion_40.json) |
| 6 | [Informe del benchmark](ejercicio_6_benchmark.md), [notebook](../../notebooks/06_comparacion_rendimiento.ipynb), [validación](ejercicio_6_validacion.json) |
| 7 | [Notebook de indicadores](../../notebooks/07_panel_indicadores.ipynb), [SQL exacto y configuración](ejercicio_7/indicadores.json), [interpretaciones](ejercicio_7/interpretaciones.json), [comparación enero–agosto](ejercicio_7/comparacion_enero_agosto.csv), [CSV y PNG](ejercicio_7/) |
| 8 | [Notebook de tres años](../../notebooks/08_integracion_tres_anios.ipynb), [SQL exacto y configuración](ejercicio_8/indicadores.json), [interpretaciones](ejercicio_8/interpretaciones.json), [comparación enero–agosto](ejercicio_8/comparacion_enero_agosto.csv), [CSV y PNG](ejercicio_8/), [validación de 2025](ejercicio_8_verificacion_2025.json) |
| 9 | [Ocho incisos de discusión](../discusion_final.md), [resumen de entrega](../entrega_final.md) |

Los JSON de indicadores incluyen las consultas y sus hashes. Cada CSV mensual
corresponde a un indicador y cada PNG muestra su evolución por año y tipo.
El [tablero local](tablero_indicadores.html) tiene filtros; el
[estado de Metabase](metabase_estado.json) registra publicación pendiente.
No se incluyen Parquet ni bases DuckDB.
