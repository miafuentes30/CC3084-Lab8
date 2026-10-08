# Entrega final — Laboratorio 8

CC3084 — Data Science, Universidad del Valle de Guatemala.
[Fork oficial](https://github.com/miafuentes30/CC3084-Lab8).

## Cobertura y resultados

**64 Parquet y 121,184,384 registros originales**. 2024 y 2025
contienen doce meses por taxi; 2026 conserva enero–agosto. La ampliación
descargó 24 archivos de 2025 y conservó los 40 anteriores. El catálogo no se
volvió a descargar. SHA-256 y validaciones: [inventario integrado](resultados/verificacion_integrada.csv).

| anio | taxi | archivos | registros_brutos | viajes_validos | exclusion_pct |
| --- | --- | --- | --- | --- | --- |
| 2024 | green | 12 | 660218 | 618891 | 6.26 |
| 2024 | yellow | 12 | 41169720 | 39673306 | 3.63 |
| 2025 | green | 12 | 591375 | 557475 | 5.73 |
| 2025 | yellow | 12 | 48722602 | 44148202 | 9.39 |
| 2026 | green | 8 | 337114 | 321395 | 4.66 |
| 2026 | yellow | 8 | 29703355 | 28223766 | 4.98 |

Los totales completos describen cobertura, no tendencias equivalentes.
Las comparaciones interanuales utilizan enero–agosto y días calendario;
se separan registros originales y viajes válidos.

## Evidencia de los nueve ejercicios

| Ejercicio | Resultado y evidencia |
|---|---|
| 1 | Docker, JupyterLab y driver DuckDB; [diagnóstico guardado](resultados/diagnostico_entorno.json) |
| 2 | Descarga incremental, integridad y errores; [pasaportes](resultados/pasaporte/) e [inventario integrado](resultados/verificacion_integrada.json) |
| 3 | Inspección directa; [notebook 03](../notebooks/03_inspeccion_parquet.ipynb) y [SQL](../sql/inspeccion/) |
| 4 | Trece consultas exploratorias; [notebook 04](../notebooks/04_exploracion_viajes.ipynb) y [SQL](../sql/exploracion/) |
| 5 | 40 archivos, 71,870,407 originales; [conteos](resultados/ejercicio_5_conteos_metadatos.csv) y [notebook 05](../notebooks/05_integracion_2024.ipynb) |
| 6 | 210 mediciones, 42 calentamientos, 21 equivalencias; [benchmark](resultados/ejercicio_6_benchmark.md), notebook 06 |
| 7 | Diez preguntas y nueve indicadores con 2024/2026; [evidencia](resultados/ejercicio_7/) y [notebook 07](../notebooks/07_panel_indicadores.ipynb) |
| 8 | 2025 incorporado, indicadores actualizados y periodos comparables; [evidencia](resultados/ejercicio_8/) y [notebook 08](../notebooks/08_integracion_tres_anios.ipynb) |
| 9 | Ocho incisos con evidencia real; [discusión final](discusion_final.md) |

Los notebooks finales están en [notebooks](../notebooks/). Esta continuación
ejecutó únicamente 07 y 08: 13 y 14
celdas de código, cero errores y nueve gráficas por etapa. No repitió el
benchmark ni los notebooks 03–06.

## Hallazgos de enero–agosto

| anio | taxi | viajes_por_dia | total_mediano | pct_flex_fare | pct_efectivo | pct_cargo_cbd |
| --- | --- | --- | --- | --- | --- | --- |
| 2024 | green | 1703.06 | 19.14 | 4.00 | 27.80 | 0.00 |
| 2025 | green | 1532.05 | 19.80 | 6.60 | 23.20 | 9.80 |
| 2026 | green | 1322.61 | 20.52 | 14.70 | 19.40 | 8.50 |
| 2024 | yellow | 104466.16 | 21.00 | 9.00 | 13.80 | 0.00 |
| 2025 | yellow | 118024.47 | 21.61 | 19.60 | 10.00 | 73.00 |
| 2026 | yellow | 116147.19 | 23.58 | 24.90 | 9.10 | 72.40 |

El informe 8 interpreta demanda, pagos y montos con los mismos meses de los
tres años. El agrupamiento 0/nulo es una convención documentada; los cambios
de selección/calidad afectan la población analítica y no prueban causalidad.

## Tablero, validación y reproducción

El [tablero local](resultados/tablero_indicadores.html) contiene nueve gráficas
y filtros por taxi, año y cobertura comparable. Metabase usa el driver y las
bases agregadas existentes; **la publicación autenticada queda pendiente por
falta de credenciales**. Salud del servicio observada: `ok`. No se aporta
una captura ficticia ni se elimina contenido ajeno. Las
[instrucciones de publicación del README](../README.md) utilizan variables del ambiente.

Suite final observada: **32 pruebas aprobadas**.
Incluye equivalencia del resumen separado y conservación de objetos ajenos en
la API simulada. La API simulada no certifica publicación real. El registro
está en [entrega_validacion.json](resultados/entrega_validacion.json).
El cierre local confirmó 32 enlaces del README sin destinos faltantes,
diff --check correcto y cero datasets, bases, credenciales o temporales
rastreados por Git. Parquet, bases y `.env` están ignorados.

La comparación anual original agotó 1 GiB. Se conservaron las tablas mensuales
y se separaron conteos/medias y medianas exactas, con un hilo y el mismo límite.
Los tiempos mensuales iniciales no se recuperaron tras esa reanudación y se
registraron como nulos; no son mediciones de benchmark.

La historia de la migración está en [historial](historial/). Se conservan
datos, todas las bases locales, evidencia real e historia académica; Git
excluye datos, bases y secretos. No se hicieron commits, push ni cambios de remotos.

Los comandos mínimos, instalación, puertos configurables y flujo completo
están en [README](../README.md). Para volver a presentar los resultados ya
calculados basta ejecutar los notebooks 07/08; para reconstruir las tablas
utilice construir_tablero.py como indica README.
