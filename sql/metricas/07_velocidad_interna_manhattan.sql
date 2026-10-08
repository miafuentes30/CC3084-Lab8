-- I7 Velocidad mediana, en millas por hora, de los viajes que empiezan y terminan en Manhattan
SELECT
    v.periodo,
    v.taxi,
    round(median(v.trip_distance / (v.duracion_min / 60)), 2) AS valor
FROM viajes_validos AS v
JOIN zonas AS inicio ON v.PULocationID = inicio.zona_id
JOIN zonas AS fin ON v.DOLocationID = fin.zona_id
WHERE inicio.distrito = 'Manhattan' AND fin.distrito = 'Manhattan'
GROUP BY v.periodo, v.taxi
ORDER BY v.taxi DESC, v.periodo
