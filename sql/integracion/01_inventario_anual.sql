-- Archivos, meses y registros por tipo de taxi y año, según el pie de cada Parquet
SELECT
    regexp_extract(file_name, '(yellow|green)_tripdata', 1) AS tipo,
    regexp_extract(file_name, '_(\d{4})-\d{2}\.parquet', 1)::INT AS anio,
    count(*) AS archivos,
    min(regexp_extract(file_name, '(\d{4}-\d{2})\.parquet', 1)) AS primer_mes,
    max(regexp_extract(file_name, '(\d{4}-\d{2})\.parquet', 1)) AS ultimo_mes,
    sum(num_rows)::BIGINT AS registros
FROM parquet_file_metadata({{all_files}})
GROUP BY tipo, anio
ORDER BY tipo DESC, anio
