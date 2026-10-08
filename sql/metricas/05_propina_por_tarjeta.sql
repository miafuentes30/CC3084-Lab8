-- I5 Propina promedio como porcentaje de la tarifa en viajes pagados con tarjeta
SELECT
    periodo,
    taxi,
    round(100 * avg(tip_amount / fare_amount), 1) AS valor
FROM viajes_validos
WHERE payment_type = 1 AND fare_amount > 0
GROUP BY periodo, taxi
ORDER BY taxi DESC, periodo
