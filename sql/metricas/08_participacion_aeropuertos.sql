-- I8 Porcentaje de viajes que empiezan o terminan en Newark (1), JFK (132) o LaGuardia (138)
SELECT
    periodo,
    taxi,
    round(100 * avg((PULocationID IN (1, 132, 138) OR DOLocationID IN (1, 132, 138))::INT), 1) AS valor
FROM viajes_validos
GROUP BY periodo, taxi
ORDER BY taxi DESC, periodo
