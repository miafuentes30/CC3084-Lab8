-- Columnas que no están en todos los archivos de un tipo o que cambian de tipo físico
WITH esquema AS (
    SELECT
        regexp_extract(file_name, '(yellow|green)_tripdata', 1) AS tipo,
        regexp_extract(file_name, '(\d{4}-\d{2})\.parquet', 1) AS mes,
        name AS columna,
        type AS tipo_fisico
    FROM parquet_schema({{all_files}})
    WHERE num_children IS NULL
),
totales AS (
    SELECT tipo, count(DISTINCT mes) AS archivos_tipo
    FROM esquema
    GROUP BY tipo
)
SELECT
    e.tipo,
    e.columna,
    count(*) AS archivos_con_columna,
    t.archivos_tipo,
    min(e.mes) AS desde,
    max(e.mes) AS hasta,
    string_agg(DISTINCT e.tipo_fisico, ', ') AS tipos_fisicos
FROM esquema AS e
JOIN totales AS t USING (tipo)
GROUP BY e.tipo, e.columna, t.archivos_tipo
HAVING count(*) < t.archivos_tipo OR count(DISTINCT e.tipo_fisico) > 1
ORDER BY e.tipo, e.columna
