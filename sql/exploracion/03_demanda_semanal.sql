-- Promedio de viajes por fecha según el día de la semana
WITH por_fecha AS (
    SELECT taxi, CAST(pickup_datetime AS DATE) AS fecha, count(*) AS viajes
    FROM viajes_validos
    GROUP BY taxi, fecha
)
SELECT
    taxi,
    isodow(fecha) AS dia_semana,
    ['lunes', 'martes', 'miércoles', 'jueves', 'viernes', 'sábado', 'domingo'][isodow(fecha)] AS dia,
    count(*) AS fechas,
    round(avg(viajes)) AS viajes_por_dia
FROM por_fecha
GROUP BY taxi, dia_semana, dia
ORDER BY taxi DESC, dia_semana
