-- Vistas sobre los Parquet de data/raw, sin copiar datos

-- Viajes amarillos y verdes con nombres comunes y periodo como el mes del archivo de origen
-- cbd_congestion_fee vale 0 en los archivos anteriores a 2025, cuando el cargo no existía
CREATE OR REPLACE VIEW viajes AS
SELECT
    'yellow' AS taxi,
    strptime(regexp_extract(filename, '(\d{4}-\d{2})\.parquet', 1), '%Y-%m')::DATE AS periodo,
    tpep_pickup_datetime AS pickup_datetime,
    tpep_dropoff_datetime AS dropoff_datetime,
    * EXCLUDE (tpep_pickup_datetime, tpep_dropoff_datetime, cbd_congestion_fee, filename),
    coalesce(cbd_congestion_fee, 0) AS cbd_congestion_fee
FROM yellow_crudos
UNION ALL BY NAME
SELECT
    'green' AS taxi,
    strptime(regexp_extract(filename, '(\d{4}-\d{2})\.parquet', 1), '%Y-%m')::DATE AS periodo,
    lpep_pickup_datetime AS pickup_datetime,
    lpep_dropoff_datetime AS dropoff_datetime,
    * EXCLUDE (lpep_pickup_datetime, lpep_dropoff_datetime, cbd_congestion_fee, filename),
    coalesce(cbd_congestion_fee, 0) AS cbd_congestion_fee
FROM green_crudos;

-- Catálogo de zonas de la TLC
CREATE OR REPLACE VIEW zonas AS
SELECT LocationID AS zona_id, Borough AS distrito, Zone AS zona
FROM read_csv({{zones_file}});
