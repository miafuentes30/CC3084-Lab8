-- Indicadores de enero a agosto de cada año, los meses disponibles en los tres años
WITH base AS (
    SELECT
        v.*,
        year(v.periodo) AS anio,
        inicio.distrito = 'Manhattan' AND fin.distrito = 'Manhattan' AS dentro_de_manhattan
    FROM viajes_validos AS v
    LEFT JOIN zonas AS inicio ON v.PULocationID = inicio.zona_id
    LEFT JOIN zonas AS fin ON v.DOLocationID = fin.zona_id
    WHERE month(v.periodo) <= 8
), dias AS (
    SELECT year(periodo) AS anio,
           sum(day(last_day(periodo))) AS dias_calendario
    FROM (SELECT DISTINCT periodo FROM viajes WHERE month(periodo) <= 8)
    GROUP BY anio
)
SELECT
    anio,
    taxi,
    count(*) AS viajes_validos,
    any_value(dias_calendario) AS dias_calendario,
    round(count(*) / any_value(dias_calendario), 2) AS viajes_por_dia,
    round(avg(trip_distance), 2) AS distancia_prom,
    round(avg(duracion_min), 2) AS duracion_prom_min,
    round(avg(total_amount), 2) AS total_prom,
    round(median(total_amount), 2) AS total_mediano,
    round(100 * avg((coalesce(payment_type, 0) = 0)::INT), 1) AS pct_flex_fare,
    round(100 * avg((coalesce(payment_type, 0) = 2)::INT), 1) AS pct_efectivo,
    round(100 * avg(tip_amount / fare_amount) FILTER (WHERE payment_type = 1 AND fare_amount > 0), 1) AS propina_pct_tarifa,
    round(100 * avg((cbd_congestion_fee > 0)::INT), 1) AS pct_cargo_cbd,
    round(median(trip_distance / (duracion_min / 60)) FILTER (WHERE dentro_de_manhattan), 2) AS velocidad_manhattan,
    round(100 * avg((PULocationID IN (1, 132, 138) OR DOLocationID IN (1, 132, 138))::INT), 1) AS pct_aeropuerto
FROM base JOIN dias USING (anio)
GROUP BY anio, taxi
ORDER BY taxi DESC, anio
