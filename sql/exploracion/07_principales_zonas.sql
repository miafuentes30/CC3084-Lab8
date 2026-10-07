-- Diez zonas con más inicios de viaje por tipo de taxi
SELECT
    v.taxi,
    z.distrito,
    z.zona,
    count(*) AS viajes,
    round(100 * count(*) / sum(count(*)) OVER (PARTITION BY v.taxi), 2) AS pct
FROM viajes_validos AS v
JOIN zonas AS z ON v.PULocationID = z.zona_id
GROUP BY v.taxi, z.distrito, z.zona
QUALIFY row_number() OVER (PARTITION BY v.taxi ORDER BY count(*) DESC) <= 10
ORDER BY v.taxi DESC, viajes DESC
