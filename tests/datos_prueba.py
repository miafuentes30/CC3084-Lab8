"""Datos sinteticos identificados como pruebas, nunca como evidencia TLC."""

from datetime import datetime, timedelta
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq


def crear_datos(raiz):
    periodos = [(2024, m) for m in range(1, 13)] + [(2025, m) for m in range(1, 13)] + [(2026, m) for m in range(1, 9)]
    for tipo in ("yellow", "green"):
        for anio, mes in periodos:
            inicio = datetime(anio, mes, 15, 12)
            prefijo = "tpep" if tipo == "yellow" else "lpep"
            registros = []
            for n in range(9):
                fila = {"VendorID": 2, f"{prefijo}_pickup_datetime": inicio,
                        f"{prefijo}_dropoff_datetime": inicio + timedelta(minutes=15),
                        "passenger_count": 1.0, "trip_distance": 2.0, "RatecodeID": 1,
                        "store_and_fwd_flag": "N", "PULocationID": 132 if n == 8 else 1,
                        "DOLocationID": 2, "payment_type": 2 if n == 8 else 1,
                        "fare_amount": 10.0, "extra": 1.0, "mta_tax": 0.5,
                        "tip_amount": 2.0, "tolls_amount": 0.0, "improvement_surcharge": 1.0,
                        "total_amount": 20.0, "congestion_surcharge": 2.5}
                if tipo == "yellow":
                    fila["Airport_fee"] = 2.0
                else:
                    fila.update(ehail_fee=None, trip_type=1)
                if anio >= 2025:
                    fila["cbd_congestion_fee"] = 0.75
                if anio == 2026 and mes >= 6:
                    fila["request_source"] = "HV0003" if n == 7 else None
                if n == 2:
                    fila["trip_distance"] = 0.0
                if n == 3:
                    fila["fare_amount"] = -10.0
                if n == 4:
                    fila[f"{prefijo}_dropoff_datetime"] = inicio
                if n == 5:
                    fila[f"{prefijo}_pickup_datetime"] = datetime(anio - 1, mes, 15)
                if n == 6:
                    fila["trip_distance"] = 1000.0
                if n == 7:
                    fila.update(payment_type=None, passenger_count=None, RatecodeID=None, congestion_surcharge=None)
                if tipo == "green" and anio == 2024 and mes == 2:
                    fila["trip_distance"] = 0.0
                registros.append(fila)
            ruta = Path(raiz) / "data/raw" / tipo / str(anio) / f"{tipo}_tripdata_{anio}-{mes:02d}.parquet"
            ruta.parent.mkdir(parents=True, exist_ok=True)
            pq.write_table(pa.Table.from_pylist(registros), ruta)
    zonas = Path(raiz) / "data/raw/zonas/taxi_zone_lookup.csv"
    zonas.parent.mkdir(parents=True, exist_ok=True)
    zonas.write_text("LocationID,Borough,Zone,service_zone\n1,Manhattan,Zona A,Yellow Zone\n2,Manhattan,Zona B,Yellow Zone\n132,Queens,JFK,Airports\n", encoding="utf-8")
