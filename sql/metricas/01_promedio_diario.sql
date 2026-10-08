-- I1 Viajes válidos por día en cada mes
SELECT
    periodo,
    taxi,
    viajes_por_dia AS valor,
    viajes AS viajes_validos,
    day(last_day(periodo)) AS dias
FROM viajes_por_mes
ORDER BY taxi DESC, periodo
