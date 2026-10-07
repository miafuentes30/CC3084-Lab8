-- Porcentaje de viajes por intervalo de distancia (1 milla) y de total (5 USD)
WITH totales AS (
    SELECT taxi, count(*) AS viajes_taxi
    FROM viajes_validos
    GROUP BY taxi
),
intervalos AS (
    SELECT taxi, 'distancia' AS variable, floor(trip_distance) AS desde, count(*) AS viajes
    FROM viajes_validos
    WHERE trip_distance < 25
    GROUP BY ALL
    UNION ALL
    SELECT taxi, 'total', floor(total_amount / 5) * 5, count(*)
    FROM viajes_validos
    WHERE total_amount < 125
    GROUP BY ALL
)
SELECT
    i.variable,
    i.taxi,
    i.desde,
    i.viajes,
    round(100 * i.viajes / t.viajes_taxi, 2) AS pct
FROM intervalos AS i
JOIN totales AS t USING (taxi)
ORDER BY i.variable, i.taxi DESC, i.desde
