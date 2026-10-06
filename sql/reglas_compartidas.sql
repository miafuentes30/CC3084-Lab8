-- Reglas de calidad compartidas por Parquet y tablas materializadas.
CREATE OR REPLACE VIEW viajes_validos AS
SELECT *, epoch(dropoff_datetime - pickup_datetime) / 60 AS duracion_min
FROM viajes
WHERE date_trunc('month', pickup_datetime) = periodo
  AND dropoff_datetime > pickup_datetime
  AND dropoff_datetime - pickup_datetime <= INTERVAL 3 HOUR
  AND trip_distance > 0 AND trip_distance <= 100
  AND trip_distance / nullif(epoch(dropoff_datetime - pickup_datetime) / 3600, 0) <= 80
  AND fare_amount >= 0 AND total_amount > 0;

CREATE OR REPLACE VIEW viajes_por_mes AS
SELECT taxi, periodo, count(*) AS viajes,
       round(count(*) / day(last_day(periodo))) AS viajes_por_dia
FROM viajes_validos
GROUP BY taxi, periodo;

CREATE OR REPLACE MACRO forma_pago(codigo) AS
CASE coalesce(codigo, 0)
    WHEN 0 THEN 'Flex Fare'
    WHEN 1 THEN 'Tarjeta'
    WHEN 2 THEN 'Efectivo'
    WHEN 3 THEN 'Sin cargo'
    WHEN 4 THEN 'Disputa'
    ELSE 'Otro'
END;
