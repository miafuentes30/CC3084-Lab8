-- Tipo, rango, cuartiles y porcentaje de nulos de cada columna de los viajes amarillos
SUMMARIZE SELECT * FROM read_parquet({{yellow_files}}, union_by_name = true)
