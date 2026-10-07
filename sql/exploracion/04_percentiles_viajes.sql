-- Percentiles de distancia, duración, velocidad y total por tipo de taxi
-- Cada variable se agrega por separado para no juntar cientos de millones de valores en una sola agregación
WITH medidas AS (
    SELECT 'distancia (millas)' AS variable, taxi,
           quantile_cont(trip_distance, [0.05, 0.25, 0.5, 0.75, 0.95]) AS q, avg(trip_distance) AS promedio
    FROM viajes_validos GROUP BY taxi
    UNION ALL
    SELECT 'duración (min)', taxi,
           quantile_cont(duracion_min, [0.05, 0.25, 0.5, 0.75, 0.95]), avg(duracion_min)
    FROM viajes_validos GROUP BY taxi
    UNION ALL
    SELECT 'velocidad (mph)', taxi,
           quantile_cont(trip_distance / (duracion_min / 60), [0.05, 0.25, 0.5, 0.75, 0.95]),
           avg(trip_distance / (duracion_min / 60))
    FROM viajes_validos GROUP BY taxi
    UNION ALL
    SELECT 'total (USD)', taxi,
           quantile_cont(total_amount, [0.05, 0.25, 0.5, 0.75, 0.95]), avg(total_amount)
    FROM viajes_validos GROUP BY taxi
)
SELECT
    variable,
    taxi,
    round(q[1], 2) AS p05,
    round(q[2], 2) AS p25,
    round(q[3], 2) AS mediana,
    round(q[4], 2) AS p75,
    round(q[5], 2) AS p95,
    round(promedio, 2) AS promedio
FROM medidas
ORDER BY variable, taxi DESC
