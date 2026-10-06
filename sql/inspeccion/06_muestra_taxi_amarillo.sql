-- Muestra aleatoria reproducible de viajes amarillos
SELECT *
FROM read_parquet({{yellow_files}}, union_by_name = true)
USING SAMPLE bernoulli(0.00002%) REPEATABLE (42)
