-- Filas idénticas en todas las columnas
-- Primero agrupa por el hash de cada fila, que ocupa poca memoria, y después confirma con todas las columnas
WITH yellow AS NOT MATERIALIZED (
    SELECT f.*, hash(f) AS h
    FROM read_parquet({{yellow_files}}, union_by_name = true) AS f
),
green AS NOT MATERIALIZED (
    SELECT f.*, hash(f) AS h
    FROM read_parquet({{green_files}}, union_by_name = true) AS f
),
repetidas_yellow AS (
    SELECT * EXCLUDE (h), count(*) AS copias
    FROM yellow
    WHERE h IN (SELECT h FROM yellow GROUP BY h HAVING count(*) > 1)
    GROUP BY ALL
    HAVING count(*) > 1
),
repetidas_green AS (
    SELECT * EXCLUDE (h), count(*) AS copias
    FROM green
    WHERE h IN (SELECT h FROM green GROUP BY h HAVING count(*) > 1)
    GROUP BY ALL
    HAVING count(*) > 1
)
SELECT 'yellow' AS taxi, count(*) AS grupos_repetidos, coalesce(sum(copias - 1), 0)::BIGINT AS filas_sobrantes
FROM repetidas_yellow
UNION ALL
SELECT 'green', count(*), coalesce(sum(copias - 1), 0)::BIGINT
FROM repetidas_green
