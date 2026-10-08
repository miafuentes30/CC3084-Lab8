-- I6 Porcentaje de viajes que pagan el cargo de la zona de congestión de Manhattan (CBD)
SELECT
    periodo,
    taxi,
    round(100 * avg((cbd_congestion_fee > 0)::INT), 1) AS valor
FROM viajes_validos
GROUP BY periodo, taxi
ORDER BY taxi DESC, periodo
