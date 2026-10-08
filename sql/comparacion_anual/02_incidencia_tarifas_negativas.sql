-- Registros amarillos con tarifa negativa por año y forma de pago, y cuántos vienen del proveedor 2
SELECT
    year(periodo) AS anio,
    forma_pago(payment_type) AS forma_pago,
    count(*) AS registros,
    count(*) FILTER (WHERE fare_amount < 0) AS tarifa_negativa,
    round(100 * count(*) FILTER (WHERE fare_amount < 0) / count(*), 2) AS pct,
    count(*) FILTER (WHERE fare_amount < 0 AND VendorID = 2) AS del_proveedor_2
FROM viajes
WHERE taxi = 'yellow'
GROUP BY anio, forma_pago
ORDER BY anio, registros DESC
