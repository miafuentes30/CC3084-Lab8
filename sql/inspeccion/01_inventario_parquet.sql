-- Archivos Parquet por tipo de taxi y rango de meses
SELECT
    regexp_extract(file, '(yellow|green)_tripdata', 1) AS tipo,
    count(*) AS archivos,
    min(regexp_extract(file, '(\d{4}-\d{2})\.parquet', 1)) AS primer_mes,
    max(regexp_extract(file, '(\d{4}-\d{2})\.parquet', 1)) AS ultimo_mes
FROM archivos
GROUP BY tipo
ORDER BY tipo
