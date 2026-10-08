# Refactorización funcional

Se inspeccionó `lab8/`: cinco scripts, seis notebooks, 44 consultas, Dockerfiles,
Compose, dependencias y documentación de seis etapas, incluido el texto de
`discusion.docx`. No se encontró un ZIP adicional dentro del proyecto.
La carpeta original permanece intacta y excluida de Git; la raíz es el proyecto activo.
El inventario histórico está en `manifiesto_referencia.json`. Los comandos
y resultados iniciales están en `validacion_etapa_inicial.md`.

| Archivo | Cambio y motivo |
| --- | --- |
| `scripts/laboratorio/parametros.py` | Años, tipos, URLs, rutas y literales SQL compartidos |
| `scripts/laboratorio/integridad.py` | Validación del pie Parquet, catálogo y escritura de evidencias |
| `scripts/laboratorio/adquisicion.py` | Descarga atómica, reintentos y selección por años/meses |
| `scripts/laboratorio/completitud.py` | Completitud contra TLC, tamaños, lectura y errores explícitos |
| `scripts/laboratorio/sesion_consultas.py` | Sesión compartida, selección de archivos, esquemas y revisión SQL |
| `scripts/laboratorio/mediciones.py` | Conjuntos fijos, materialización SQL y procedencia de mediciones |
| `scripts/laboratorio/catalogo_indicadores.py` | Catálogo único de indicadores y diez preguntas |
| `scripts/laboratorio/generacion_indicadores.py` | Entrada transaccional separada de publicación |
| `scripts/laboratorio/cliente_metabase.py` | Cliente API idempotente con credenciales por ambiente y conexión de lectura |
| `scripts/laboratorio/resultados_indicadores.py` | Agregados mensuales, reutilización comprobada y medianas anuales separadas |
| `scripts/laboratorio/presentacion_final.py` | Informes, gráficas y tablero local a partir de CSV pequeños |
| `scripts/laboratorio/graficos.py` | Estilo y gráficas de indicadores compartidos |
| `scripts/laboratorio/soporte_cuadernos.py` | Presentación y comandos con errores comprobados |
| `scripts/laboratorio/diagnostico.py` | Verificación con código de salida acorde con fallos |
| `scripts/*.py` | Entradas CLI y documentación reproducible sin configuración duplicada |
| Los seis notebooks | Imports compartidos, años explícitos, rutas estables y cierre de conexiones |
| `sql/normalizacion_viajes.sql`, `sql/reglas_compartidas.sql` | Normalización, reglas de calidad, agregación mensual y traducción de pagos únicas |
| SQL de ejercicios/indicadores | Rutas resueltas por sesión, menos normalización repetida e I9 corregido |
| `docker-compose.yml` | Servicios conservados, credenciales y puertos configurables, datos de Metabase de lectura |
| `.gitignore` | Excluye datos, bases, temporales, secretos, ambientes y referencia |
| `tests` | Pruebas funcionales y ejecución completa de notebooks con fixtures |
| `README.md`, `docs` | Flujo reproducible, cobertura y resultados históricos identificados |

Los Dockerfiles y `requirements.txt` mantienen las versiones y el contenido de referencia.
`docs/historial/traslado_inicial.py.txt` registra la migración inicial; no sobrescribe una estructura
ya migrada ni se usa en el flujo habitual.

El conjunto anterior “20 meses” seleccionaba todos los años disponibles. Ahora fija
2024 y enero-agosto de 2026. Los notebooks 03/04 y 07 conservan sus etapas aunque
existan archivos de 2025 en disco.

La sesión añade nulos tipados para `cbd_congestion_fee`, `request_source` y `Airport_fee`
si faltan completamente; las consultas de esquema siguen inspeccionando los originales.
La vista normalizada aplica la convención histórica de CBD como cero antes del cargo.
I9 incluye meses sin viajes válidos con 100% de exclusión.

Las bases se actualizan con transacciones en lugar de borrarse antes del cálculo.
Los viajes se materializan en SQL sin pasar por pandas. Los notebooks comprueban
códigos de procesos y estados de consultas, en vez de continuar después de errores.

Las reglas analíticas provienen del material. La cobertura se mapea a los incisos
de los notebooks y a las ocho preguntas de discusión indicadas en el enunciado.
La entrega y las evidencias reales están en `docs/entrega_final.md`.
