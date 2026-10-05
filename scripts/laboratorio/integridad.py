"""Validacion local de formatos y escritura de evidencias."""

import csv
import json
import hashlib
import tempfile
from datetime import datetime, timezone
from pathlib import Path


def es_parquet_completo(ruta, lectura_completa=True):
    ruta = Path(ruta)
    if not ruta.is_file() or ruta.stat().st_size < 12:
        return False
    try:
        with ruta.open("rb") as archivo:
            inicio = archivo.read(4)
            archivo.seek(-4, 2)
            fin = archivo.read(4)
    except OSError:
        return False
    if inicio != b"PAR1" or fin != b"PAR1":
        return False
    # Las marcas y el pie no garantizan paginas de datos legibles.
    import duckdb
    import pyarrow as pa
    import pyarrow.parquet as pq
    try:
        with duckdb.connect() as con:
            registros = con.execute("SELECT num_rows FROM parquet_file_metadata(?)", [str(ruta)]).fetchone()[0]
        if lectura_completa:
            with pq.ParquetFile(ruta) as parquet:
                leidos = sum(lote.num_rows for lote in parquet.iter_batches(batch_size=65536))
            if leidos != registros:
                return False
        return True
    except (duckdb.Error, pa.ArrowException, OSError, ValueError):
        return False


def calcular_sha256(ruta):
    with Path(ruta).open("rb") as archivo:
        return hashlib.file_digest(archivo, "sha256").hexdigest()


def es_catalogo_zonas(ruta):
    try:
        with Path(ruta).open(encoding="utf-8-sig", newline="") as archivo:
            lector = csv.DictReader(archivo)
            return {"LocationID", "Borough", "Zone"}.issubset(lector.fieldnames or []) and next(lector, None) is not None
    except (OSError, UnicodeError, csv.Error):
        return False


def guardar_csv(ruta, filas, campos=None):
    ruta = Path(ruta)
    ruta.parent.mkdir(parents=True, exist_ok=True)
    if not campos and not filas:
        raise ValueError("Un CSV vacio requiere nombres de campos")
    temporal = ruta.with_suffix(ruta.suffix + ".tmp")
    with temporal.open("w", newline="", encoding="utf-8") as archivo:
        escritor = csv.DictWriter(archivo, fieldnames=campos or list(filas[0]))
        escritor.writeheader()
        escritor.writerows(filas)
    temporal.replace(ruta)


def guardar_procedencia(ruta, **detalles):
    ruta = Path(ruta)
    ruta.parent.mkdir(parents=True, exist_ok=True)
    contenido = json.dumps({"fecha_utc": datetime.now(timezone.utc).isoformat(), **detalles},
                           ensure_ascii=True, indent=2) + "\n"
    with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=ruta.parent, suffix=".tmp", delete=False) as archivo:
        temporal = Path(archivo.name)
        archivo.write(contenido)
    try:
        temporal.replace(ruta)
    finally:
        temporal.unlink(missing_ok=True)
