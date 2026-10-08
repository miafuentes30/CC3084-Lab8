-- Viajes y total promedio de un día, filtro que descarta casi todos los registros
SELECT taxi, count(*) AS viajes, round(avg(total_amount), 2) AS total_prom,
       round(avg(trip_distance), 2) AS distancia_prom,
       round(avg(epoch(dropoff_datetime - pickup_datetime) / 60), 2) AS duracion_prom_min,
       round(avg(fare_amount), 2) AS tarifa_prom
FROM viajes
WHERE pickup_datetime >= TIMESTAMP '2026-01-15' AND pickup_datetime < TIMESTAMP '2026-01-16'
GROUP BY taxi
ORDER BY taxi
