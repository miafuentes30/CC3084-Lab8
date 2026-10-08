-- I9 Porcentaje de registros que no pasan las reglas de calidad de viajes_validos
WITH registros AS (
    SELECT periodo, taxi, count(*) AS total
    FROM viajes
    GROUP BY periodo, taxi
),
validos AS (
    SELECT periodo, taxi, count(*) AS validos
    FROM viajes_validos
    GROUP BY periodo, taxi
)
SELECT
    periodo,
    taxi,
    round(100 * (1 - coalesce(validos, 0) / total), 2) AS valor
FROM registros
LEFT JOIN validos USING (periodo, taxi)
ORDER BY taxi DESC, periodo
