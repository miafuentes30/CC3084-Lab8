-- I4 Porcentaje de viajes pagados en efectivo
SELECT
    periodo,
    taxi,
    round(100 * avg((coalesce(payment_type, 0) = 2)::INT), 1) AS valor
FROM viajes_validos
GROUP BY periodo, taxi
ORDER BY taxi DESC, periodo
