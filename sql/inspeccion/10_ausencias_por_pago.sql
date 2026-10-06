-- Relación entre la forma de pago y los nulos en pasajeros, código de tarifa y recargos
SELECT
    taxi,
    payment_type,
    count(*) AS viajes,
    round(100 * count(*) / sum(count(*)) OVER (PARTITION BY taxi), 2) AS pct_viajes,
    count(*) FILTER (WHERE passenger_count IS NULL) AS sin_passenger_count,
    count(*) FILTER (WHERE RatecodeID IS NULL) AS sin_ratecode,
    count(*) FILTER (WHERE congestion_surcharge IS NULL) AS sin_congestion
FROM viajes
GROUP BY taxi, payment_type
ORDER BY taxi, payment_type
