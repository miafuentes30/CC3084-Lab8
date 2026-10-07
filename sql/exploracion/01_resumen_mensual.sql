-- Viajes válidos por mes y tipo de taxi
SELECT taxi, periodo, viajes, viajes_por_dia
FROM viajes_por_mes
ORDER BY taxi DESC, periodo
