-- Monto promedio de cada componente del cobro en viajes pagados con tarjeta o efectivo
SELECT
    taxi,
    round(avg(fare_amount), 2) AS tarifa,
    round(avg(tip_amount), 2) AS propina,
    round(avg(tolls_amount), 2) AS peajes,
    round(avg(congestion_surcharge), 2) AS recargo_congestion,
    round(avg(cbd_congestion_fee), 2) AS cargo_cbd,
    round(avg(coalesce(Airport_fee, 0)), 2) AS cargo_aeropuerto,
    round(avg(extra + mta_tax + improvement_surcharge), 2) AS otros_recargos,
    round(avg(total_amount), 2) AS total
FROM viajes_validos
WHERE payment_type IN (1, 2)
GROUP BY taxi
ORDER BY taxi DESC
