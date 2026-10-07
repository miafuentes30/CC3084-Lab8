-- Viajes amarillos por valor del cargo de aeropuerto y mes
SELECT
    periodo,
    count(*) FILTER (WHERE Airport_fee = 1.75) AS cargo_1_75,
    count(*) FILTER (WHERE Airport_fee = 2.00) AS cargo_2_00,
    count(*) FILTER (WHERE Airport_fee NOT IN (1.75, 2.00)) AS otro_valor,
    min(pickup_datetime) FILTER (WHERE Airport_fee = 2.00) AS primer_cargo_2_00
FROM viajes_validos
WHERE taxi = 'yellow' AND Airport_fee > 0
GROUP BY periodo
ORDER BY periodo
