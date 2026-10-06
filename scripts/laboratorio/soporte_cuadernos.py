"""Adaptadores de presentacion y ejecucion para los seis notebooks."""

import os
import subprocess
import sys
from pathlib import Path

import pandas as pd
from IPython.display import display

from .graficos import configurar_estilo, grafica_indicador


def configurar_notebook():
    pd.set_option("display.max_columns", 30)
    pd.set_option("display.width", 200)
    configurar_estilo()


def ejecutar_script(nombre, *argumentos):
    # Las pruebas de notebooks omiten red, pero no simulan una descarga exitosa.
    if os.environ.get("LAB8_OFFLINE") == "1":
        print("Descarga/verificacion remota omitida: modo offline; datos existentes no certificados contra TLC")
        return
    ruta = Path(__file__).resolve().parents[1] / nombre
    resultado = subprocess.run([sys.executable, str(ruta), *map(str, argumentos)],
                               capture_output=True, text=True, check=True)
    print(resultado.stdout)
    return resultado


def mostrar_indicador(analisis, archivo, titulo=None, unidad=None, mostrar_sql=True):
    from .generacion_indicadores import INDICADORES
    definicion = next(i for i in INDICADORES if i["sql"] == archivo)
    datos = analisis.consulta(f"metricas/{archivo}", mostrar_sql=mostrar_sql)
    datos["periodo"] = pd.to_datetime(datos.periodo)
    tabla = datos.pivot_table(index=datos.periodo.dt.month.rename("mes"),
                             columns=["taxi", datos.periodo.dt.year.rename("anio")], values="valor")
    display(tabla.reindex(columns=["yellow", "green"], level=0))
    grafica_indicador(datos, titulo or definicion["titulo"], unidad or definicion["unidad"])
    return datos
