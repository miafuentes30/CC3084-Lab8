-- Registros que conserva la vista viajes_validos (requiere sql/normalizacion_viajes.sql)
WITH todos AS (
    SELECT taxi, count(*) AS registros FROM viajes GROUP BY taxi
),
validos AS (
    SELECT taxi, count(*) AS validos FROM viajes_validos GROUP BY taxi
)
SELECT
    taxi,
    registros,
    validos,
    registros - validos AS excluidos,
    round(100 * validos / registros, 2) AS pct_validos
FROM todos
JOIN validos USING (taxi)
ORDER BY taxi DESC
