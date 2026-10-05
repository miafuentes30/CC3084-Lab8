"""Rutas y parametros compartidos por comandos y notebooks."""

import os
from dataclasses import dataclass
from pathlib import Path

ANIOS = (2024, 2025, 2026)
ANIOS_PASAPORTE = (2026,)
TIPOS_TAXI = ("yellow", "green")
URL_BASE = "https://d37ci6vzurychx.cloudfront.net/trip-data"
URL_ZONAS = "https://d37ci6vzurychx.cloudfront.net/misc/taxi_zone_lookup.csv"
PAGINA_TLC = "https://www.nyc.gov/site/tlc/about/tlc-trip-record-data.page"
TIEMPO_ESPERA = 60
INTENTOS = 3
BLOQUE = 1024 * 1024
RAIZ_CODIGO = Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class Configuracion:
    raiz: Path

    @classmethod
    def del_entorno(cls):
        return cls(Path(os.environ.get("LAB8_ROOT", RAIZ_CODIGO)).resolve())

    @property
    def raw(self):
        return self.raiz / "data" / "raw"

    @property
    def procesados(self):
        return self.raiz / "data" / "processed"

    @property
    def sql(self):
        # El codigo SQL permanece en el proyecto aunque los datos se reubiquen.
        return RAIZ_CODIGO / "sql"

    @property
    def resultados(self):
        return self.raiz / "docs" / "resultados"

    def ruta_viajes(self, tipo, anio, mes):
        return self.raw / tipo / str(anio) / construir_nombre(tipo, anio, mes)


def construir_nombre(tipo, anio, mes):
    if tipo not in TIPOS_TAXI or not 1 <= int(mes) <= 12 or int(anio) < 2009:
        raise ValueError("Tipo, anio o mes fuera del dominio TLC")
    return f"{tipo}_tripdata_{int(anio)}-{int(mes):02d}.parquet"


def construir_url(tipo, anio, mes):
    return f"{URL_BASE}/{construir_nombre(tipo, anio, mes)}"


def literal_sql(valor):
    return "'" + str(valor).replace("'", "''") + "'"
