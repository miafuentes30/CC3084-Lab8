-- Muestra aleatoria reproducible de viajes verdes
SELECT *
FROM read_parquet({{green_files}}, union_by_name = true)
USING SAMPLE bernoulli(0.002%) REPEATABLE (42)
