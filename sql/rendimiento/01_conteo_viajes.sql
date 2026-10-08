-- Registros por tipo de taxi
SELECT taxi, count(*) AS viajes
FROM viajes
GROUP BY taxi
ORDER BY taxi
