-- Indicadores de viaje y pago por tipo de taxi
SELECT
    v.taxi,
    count(*) AS viajes,
    round(avg(v.trip_distance), 2) AS distancia_prom,
    round(median(v.duracion_min), 1) AS duracion_mediana,
    round(avg(v.trip_distance / (v.duracion_min / 60)), 1) AS velocidad_prom,
    round(avg(v.fare_amount), 2) AS tarifa_prom,
    round(avg(v.total_amount), 2) AS total_prom,
    round(100 * avg((coalesce(v.payment_type, 0) = 1)::INT), 1) AS pct_tarjeta,
    round(100 * avg((coalesce(v.payment_type, 0) = 2)::INT), 1) AS pct_efectivo,
    round(100 * avg((coalesce(v.payment_type, 0) = 0)::INT), 1) AS pct_flex_fare,
    round(100 * avg(v.tip_amount / v.fare_amount) FILTER (WHERE v.payment_type = 1 AND v.fare_amount > 0), 1) AS pct_propina_tarjeta,
    round(100 * avg((v.cbd_congestion_fee > 0)::INT), 1) AS pct_con_cargo_cbd,
    round(100 * avg((z.distrito = 'Manhattan')::INT), 1) AS pct_inicio_manhattan
FROM viajes_validos AS v
JOIN zonas AS z ON v.PULocationID = z.zona_id
GROUP BY v.taxi
ORDER BY v.taxi DESC
