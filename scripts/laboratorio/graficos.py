"""Estilo y graficas compartidas por los notebooks."""

import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.ticker import FuncFormatter

COLOR = {"yellow": "#eda100", "green": "#008300"}
NOMBRE = {"yellow": "Amarillo", "green": "Verde"}
COLOR_ANIO = {2024: "#2a78d6", 2025: "#eb6834", 2026: "#1baf7a"}
MESES = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"]
miles = FuncFormatter(lambda x, _: f"{x:,.0f}")


def configurar_estilo():
    plt.rcParams.update({
        "figure.facecolor": "#fcfcfb", "axes.facecolor": "#fcfcfb", "savefig.facecolor": "#fcfcfb",
        "axes.edgecolor": "#c3c2b7", "axes.labelcolor": "#52514e", "axes.titlecolor": "#0b0b0b",
        "axes.titlesize": 11, "axes.titleweight": "bold", "axes.titlelocation": "left",
        "xtick.color": "#52514e", "ytick.color": "#52514e", "xtick.labelsize": 9, "ytick.labelsize": 9,
        "axes.grid": True, "axes.grid.axis": "y", "grid.color": "#e1e0d9", "grid.linewidth": 0.8,
        "axes.axisbelow": True, "axes.spines.top": False, "axes.spines.right": False,
        "lines.linewidth": 2, "legend.frameon": False, "legend.fontsize": 9,
        "figure.dpi": 110, "font.size": 10,
    })


def grafica_indicador(datos, titulo, unidad):
    fig, ejes = plt.subplots(1, 2, figsize=(10, 3.2))
    fechas = pd.to_datetime(datos.periodo)
    datos = datos.assign(periodo=fechas)
    for eje, taxi in zip(ejes, ("yellow", "green")):
        d = datos[datos.taxi == taxi]
        for anio, grupo in d.groupby(d.periodo.dt.year):
            eje.plot(grupo.periodo.dt.month, grupo.valor, color=COLOR_ANIO.get(anio), label=str(anio),
                     marker="o", markersize=5, markeredgecolor="#fcfcfb", markeredgewidth=1.5)
        eje.set_title(f"Taxi {NOMBRE[taxi].lower()}")
        eje.set_xticks(range(1, 13), MESES)
        maximo = d.valor.max()
        eje.set_ylim(0, maximo * 1.15 if pd.notna(maximo) and maximo > 0 else 1)
        eje.yaxis.set_major_formatter(miles if pd.notna(maximo) and maximo >= 1000 else FuncFormatter(lambda x, _: f"{x:g}"))
    ejes[0].set_ylabel(unidad)
    if ejes[0].lines:
        ejes[0].legend(loc="lower left", ncols=3)
    fig.suptitle(titulo, x=0.01, ha="left", fontweight="bold")
    fig.tight_layout()
    plt.show()
    return fig
