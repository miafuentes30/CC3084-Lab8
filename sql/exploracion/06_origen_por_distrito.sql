-- Distrito donde empiezan los viajes por tipo de taxi
SELECT
    v.taxi,
    z.distrito,
    count(*) AS viajes,
    round(100 * count(*) / sum(count(*)) OVER (PARTITION BY v.taxi), 1) AS pct
FROM viajes_validos AS v
JOIN zonas AS z ON v.PULocationID = z.zona_id
GROUP BY v.taxi, z.distrito
ORDER BY v.taxi DESC, viajes DESC
