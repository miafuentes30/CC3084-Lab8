-- Registros que rompen reglas de fecha, duración, distancia, montos o zona
SELECT
    taxi,
    count(*) AS viajes,
    count(*) FILTER (WHERE date_trunc('month', pickup_datetime) <> periodo) AS inicio_fuera_del_mes,
    count(*) FILTER (WHERE dropoff_datetime <= pickup_datetime) AS duracion_cero_o_negativa,
    count(*) FILTER (WHERE dropoff_datetime - pickup_datetime > INTERVAL 3 HOUR) AS duracion_mayor_3h,
    count(*) FILTER (WHERE trip_distance = 0) AS distancia_cero,
    count(*) FILTER (WHERE trip_distance > 100) AS distancia_mayor_100,
    count(*) FILTER (WHERE dropoff_datetime > pickup_datetime
        AND trip_distance / nullif(epoch(dropoff_datetime - pickup_datetime) / 3600, 0) > 80) AS velocidad_mayor_80,
    count(*) FILTER (WHERE fare_amount < 0) AS tarifa_negativa,
    count(*) FILTER (WHERE total_amount <= 0) AS total_cero_o_negativo,
    count(*) FILTER (WHERE passenger_count = 0) AS pasajeros_cero,
    count(*) FILTER (WHERE PULocationID IN (264, 265) OR DOLocationID IN (264, 265)) AS zona_desconocida
FROM viajes
GROUP BY taxi
ORDER BY taxi DESC
