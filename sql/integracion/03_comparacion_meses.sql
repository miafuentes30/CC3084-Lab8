-- Viajes por día de cada mes, para comparar el mismo mes en distintos años
SELECT
    taxi,
    month(periodo) AS mes,
    year(periodo) AS anio,
    viajes_por_dia
FROM viajes_por_mes
ORDER BY taxi DESC, mes, anio
