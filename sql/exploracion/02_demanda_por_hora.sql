-- Porcentaje de viajes por hora de inicio, de lunes a viernes y en fin de semana
WITH conteo AS (
    SELECT
        taxi,
        CASE WHEN isodow(pickup_datetime) <= 5 THEN 'Lunes a viernes' ELSE 'Sábado y domingo' END AS dias,
        hour(pickup_datetime) AS hora,
        count(*) AS viajes
    FROM viajes_validos
    GROUP BY taxi, dias, hora
)
SELECT
    taxi,
    dias,
    hora,
    viajes,
    round(100 * viajes / sum(viajes) OVER (PARTITION BY taxi, dias), 2) AS pct
FROM conteo
ORDER BY taxi DESC, dias, hora
