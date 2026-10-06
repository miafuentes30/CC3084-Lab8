"""Sesiones de analisis sobre conjuntos explicitos de archivos."""

import re
import time
from pathlib import Path

import duckdb

from .parametros import Configuracion, TIPOS_TAXI, literal_sql


class Analisis:
    def __init__(self, configuracion=None, anios=None, periodos=None, opciones_duckdb=None):
        self.config = configuracion or Configuracion.del_entorno()
        self.anios = None if anios is None else set(anios)
        self.periodos = None if periodos is None else set(periodos)
        self.archivos = {}
        self.con = duckdb.connect(config=opciones_duckdb or {})
        try:
            self.crear_vistas()
        except Exception:
            self.con.close()
            raise

    def actualizar_archivos(self):
        for tipo in TIPOS_TAXI:
            rutas = sorted(self.config.raw.glob(f"{tipo}/*/{tipo}_tripdata_*.parquet"))
            self.archivos[tipo] = [r for r in rutas if self._incluido(r)]
            if not self.archivos[tipo]:
                raise FileNotFoundError(f"No hay Parquet {tipo} para el conjunto seleccionado en {self.config.raw}")

    def _incluido(self, ruta):
        match = re.fullmatch(r"(?:yellow|green)_tripdata_(\d{4})-(\d{2})\.parquet", ruta.name)
        return bool(match and (self.anios is None or int(match[1]) in self.anios)
                    and (self.periodos is None or f"{match[1]}-{match[2]}" in self.periodos))

    def leer_sql(self, ruta):
        archivo = (self.config.sql / ruta).resolve()
        if not archivo.is_relative_to(self.config.sql.resolve()):
            raise ValueError("La consulta debe estar dentro de sql/")
        texto = archivo.read_text(encoding="utf-8")
        valores = {f"{tipo}_files": self._lista_sql(self.archivos[tipo]) for tipo in TIPOS_TAXI}
        valores["all_files"] = self._lista_sql(self.archivos["yellow"] + self.archivos["green"])
        valores["zones_file"] = literal_sql((self.config.raw / "zonas" / "taxi_zone_lookup.csv").as_posix())
        for nombre, valor in valores.items():
            texto = texto.replace("{{" + nombre + "}}", valor)
        if "{{" in texto:
            raise ValueError(f"Parametro SQL sin resolver en {ruta}")
        return texto

    @staticmethod
    def _lista_sql(rutas):
        return "[" + ", ".join(literal_sql(r.as_posix()) for r in rutas) + "]"

    def crear_vistas(self):
        self.actualizar_archivos()
        for tipo in TIPOS_TAXI:
            archivos = self._lista_sql(self.archivos[tipo])
            fuente = f"read_parquet({archivos}, union_by_name=true, filename=true)"
            columnas = {r[0].lower() for r in self.con.execute(f"DESCRIBE SELECT * FROM {fuente}").fetchall()}
            opcionales = {"cbd_congestion_fee": "DOUBLE", "request_source": "VARCHAR", "Airport_fee": "DOUBLE"}
            extras = [f"NULL::{tipo_sql} AS {nombre}" for nombre, tipo_sql in opcionales.items()
                      if nombre.lower() not in columnas]
            proyeccion = "*" + (", " + ", ".join(extras) if extras else "")
            self.con.execute(f"CREATE OR REPLACE VIEW {tipo}_crudos AS SELECT {proyeccion} FROM {fuente}")
        rutas = self.archivos["yellow"] + self.archivos["green"]
        self.con.execute(f"CREATE OR REPLACE VIEW archivos AS SELECT unnest({self._lista_sql(rutas)}) AS file")
        self.con.execute(self.leer_sql("normalizacion_viajes.sql"))
        self.con.execute(self.leer_sql("reglas_compartidas.sql"))

    def consulta(self, ruta, mostrar_sql=True):
        texto = self.leer_sql(ruta)
        if mostrar_sql:
            print(texto)
        inicio = time.perf_counter()
        resultado = self.con.execute(texto).df()
        print(f"-- {time.perf_counter() - inicio:.2f} s")
        return resultado

    def revisar_consultas(self, patron="*/*.sql"):
        import pandas as pd
        filas = []
        for ruta in sorted(self.config.sql.glob(patron)):
            nombre = ruta.relative_to(self.config.sql).as_posix()
            inicio = time.perf_counter()
            try:
                resultado = self.con.execute(self.leer_sql(nombre)).fetchall()
                estado, n = "ok", len(resultado)
            except duckdb.Error as error:
                estado, n = str(error).splitlines()[0], None
            filas.append({"consulta": nombre, "estado": estado, "filas": n,
                          "segundos": round(time.perf_counter() - inicio, 4)})
        return pd.DataFrame(filas)

    def cerrar(self):
        self.con.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.cerrar()
