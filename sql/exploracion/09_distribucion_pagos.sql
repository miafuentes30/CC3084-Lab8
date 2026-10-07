-- Formas de pago, propina promedio y propina como porcentaje de la tarifa
SELECT
    taxi,
    forma_pago(payment_type) AS forma_pago,
    count(*) AS viajes,
    round(100 * count(*) / sum(count(*)) OVER (PARTITION BY taxi), 2) AS pct_viajes,
    round(avg(total_amount), 2) AS total_prom,
    round(avg(tip_amount), 2) AS propina_prom,
    round(100 * avg((tip_amount > 0)::INT), 1) AS pct_con_propina,
    round(100 * avg(tip_amount / fare_amount) FILTER (WHERE fare_amount > 0), 1) AS propina_pct_tarifa
FROM viajes_validos
GROUP BY taxi, forma_pago
ORDER BY taxi DESC, viajes DESC
