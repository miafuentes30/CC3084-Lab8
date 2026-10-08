-- I3 Porcentaje de viajes Flex Fare (payment_type 0 en amarillos, nulo en verdes)
SELECT
    periodo,
    taxi,
    round(100 * avg((coalesce(payment_type, 0) = 0)::INT), 1) AS valor
FROM viajes_validos
GROUP BY periodo, taxi
ORDER BY taxi DESC, periodo
