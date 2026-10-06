-- Registros por tipo de taxi según el pie de cada Parquet, sin leer las filas
WITH archivos AS (
    SELECT
        regexp_extract(file_name, '(yellow|green)_tripdata', 1) AS tipo,
        num_rows,
        num_row_groups
    FROM parquet_file_metadata({{all_files}})
)
SELECT
    coalesce(tipo, 'total') AS tipo,
    count(*) AS archivos,
    sum(num_rows)::BIGINT AS registros,
    sum(num_row_groups)::BIGINT AS grupos_de_filas
FROM archivos
GROUP BY ROLLUP (tipo)
ORDER BY grouping(tipo), tipo
