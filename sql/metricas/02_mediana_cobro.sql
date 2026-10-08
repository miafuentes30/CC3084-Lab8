-- I2 Total cobrado en el viaje mediano, en dólares
SELECT
    periodo,
    taxi,
    round(median(total_amount), 2) AS valor
FROM viajes_validos
GROUP BY periodo, taxi
ORDER BY taxi DESC, periodo
