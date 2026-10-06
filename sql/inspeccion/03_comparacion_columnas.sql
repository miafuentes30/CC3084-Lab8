-- Columnas y tipos de datos de taxis amarillos y verdes, en el orden de los archivos
WITH yellow AS (
    SELECT row_number() OVER () AS orden, column_name, column_type
    FROM (DESCRIBE SELECT * FROM read_parquet({{yellow_files}}, union_by_name = true))
),
green AS (
    SELECT row_number() OVER () AS orden, column_name, column_type
    FROM (DESCRIBE SELECT * FROM read_parquet({{green_files}}, union_by_name = true))
)
SELECT
    coalesce(y.column_name, g.column_name) AS columna,
    y.column_type AS tipo_yellow,
    g.column_type AS tipo_green
FROM yellow AS y
FULL JOIN green AS g ON y.column_name = g.column_name
ORDER BY coalesce(y.orden, g.orden + 0.5)
