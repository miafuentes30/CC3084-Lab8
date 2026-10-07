-- Porcentaje de viajes amarillos con cargo CBD, ignorando los nulos de 2024 o tomándolos como 0
WITH crudos AS (
    SELECT regexp_extract(filename, '_(\d{4})-\d{2}\.parquet', 1) AS anio, cbd_congestion_fee
    FROM yellow_crudos
)
SELECT
    coalesce(anio, 'todos') AS anio,
    count(*) AS viajes,
    count(cbd_congestion_fee) AS con_valor,
    round(100 * avg((cbd_congestion_fee > 0)::INT), 1) AS pct_ignorando_nulos,
    round(100 * avg((coalesce(cbd_congestion_fee, 0) > 0)::INT), 1) AS pct_nulos_como_0
FROM crudos
GROUP BY ROLLUP (anio)
ORDER BY grouping(anio), anio
