-- Viajes Flex Fare por mes y origen de la solicitud
SELECT
    taxi,
    periodo,
    count(*) AS viajes,
    round(100 * avg((coalesce(payment_type, 0) = 0)::INT), 1) AS pct_flex_fare,
    count(*) FILTER (WHERE request_source = 'HV0003') AS origen_hv0003,
    count(*) FILTER (WHERE request_source = 'HV0005') AS origen_hv0005,
    count(*) FILTER (WHERE request_source NOT IN ('HV0003', 'HV0005')) AS otro_origen
FROM viajes_validos
GROUP BY taxi, periodo
ORDER BY taxi DESC, periodo
