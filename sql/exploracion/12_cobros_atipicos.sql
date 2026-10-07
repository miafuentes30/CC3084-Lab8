-- Viajes válidos con total mayor a Q3 + 3 * IQR, agrupados por código de tarifa
WITH limites AS (
    SELECT
        taxi,
        quantile_cont(total_amount, 0.75)
            + 3 * (quantile_cont(total_amount, 0.75) - quantile_cont(total_amount, 0.25)) AS limite
    FROM viajes_validos
    GROUP BY taxi
)
SELECT
    v.taxi,
    round(l.limite, 2) AS limite_total,
    CASE v.RatecodeID
        WHEN 1 THEN 'Estándar'
        WHEN 2 THEN 'JFK'
        WHEN 3 THEN 'Newark'
        WHEN 4 THEN 'Nassau o Westchester'
        WHEN 5 THEN 'Negociada'
        WHEN 6 THEN 'Grupal'
        WHEN 99 THEN 'Desconocida'
        ELSE 'Sin dato'
    END AS tarifa,
    count(*) AS viajes,
    round(100 * count(*) / sum(count(*)) OVER (PARTITION BY v.taxi), 1) AS pct_atipicos,
    round(avg(v.trip_distance), 1) AS distancia_prom,
    round(avg(v.total_amount), 2) AS total_prom
FROM viajes_validos AS v
JOIN limites AS l USING (taxi)
WHERE v.total_amount > l.limite
GROUP BY v.taxi, l.limite, tarifa
ORDER BY v.taxi DESC, viajes DESC
