-- Viajes válidos e indicadores por año y tipo de taxi, en una sola consulta sobre todos los años
SELECT
    year(periodo) AS anio,
    taxi,
    count(DISTINCT periodo) AS meses,
    count(*) AS viajes,
    round(count(*) / count(DISTINCT CAST(pickup_datetime AS DATE))) AS viajes_por_dia,
    round(avg(trip_distance), 2) AS distancia_prom,
    round(avg(total_amount), 2) AS total_prom,
    round(100 * avg((coalesce(payment_type, 0) = 0)::INT), 1) AS pct_flex_fare,
    round(100 * avg((cbd_congestion_fee > 0)::INT), 1) AS pct_con_cargo_cbd
FROM viajes_validos
GROUP BY anio, taxi
ORDER BY taxi DESC, anio
