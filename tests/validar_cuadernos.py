"""Ejecuta los seis notebooks completos con datos sinteticos, sin descargar TLC."""

import os
import sys
import tempfile
from pathlib import Path

import nbformat
from nbclient import NotebookClient

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "scripts"))
from datos_prueba import crear_datos
from laboratorio.mediciones import ejecutar
from laboratorio.generacion_indicadores import calcular_indicadores
from laboratorio.parametros import Configuracion


def main():
    with tempfile.TemporaryDirectory(prefix="lab8_notebooks_") as tmp:
        config = Configuracion(Path(tmp))
        crear_datos(config.raiz)
        ejecutar(config, repeticiones=1)
        os.environ["LAB8_ROOT"] = tmp
        os.environ["LAB8_OFFLINE"] = "1"
        os.environ["MPLBACKEND"] = "Agg"
        for ruta in sorted((RAIZ / "notebooks").glob("*.ipynb")):
            if ruta.name.startswith('07_'):
                calcular_indicadores(config, anios=(2024, 2026))
            if ruta.name.startswith('08_'):
                calcular_indicadores(config, anios=(2024, 2025, 2026), reutilizar=True)
            nb = nbformat.read(ruta, as_version=4)
            if ruta.name.startswith('08_'):
                for celda in nb.cells:
                    if celda.cell_type == 'code' and celda.source.startswith('verificacion ='):
                        celda.source = 'print("Fixtures offline: no se acredita descarga ni validación TLC.")'
            nbformat.validate(nb)
            NotebookClient(nb, timeout=180, kernel_name="python3", resources={"metadata": {"path": str(RAIZ / "notebooks")}}).execute()
            print(f"EJECUTADO {ruta.name}: {sum(c.cell_type == 'code' for c in nb.cells)} celdas de codigo", flush=True)
    print("Seis notebooks ejecutados con fixtures sinteticos. Sin certificar resultados TLC ni sobrescribir notebooks.")


if __name__ == "__main__":
    main()
