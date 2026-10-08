"""Fallos de red, publicaciones oficiales, integridad y diagnostico del Pasaporte."""

import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

import requests
import pyarrow as pa
import pyarrow.parquet as pq

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from laboratorio.adquisicion import descargar, descargar_archivo, main as descargar_main, tamanio_publicado
from laboratorio.completitud import revisar
from laboratorio.diagnostico import comprobar_versiones, comprobar_persistencia, comprobar_servicios, versiones_esperadas
from laboratorio.integridad import es_parquet_completo
from laboratorio.parametros import Configuracion
from laboratorio.publicaciones import publicados
from laboratorio.solicitudes import solicitar


def respuesta(estado=200, contenido=b"", headers=None):
    r = Mock()
    r.status_code = estado
    r.headers = headers if headers is not None else {"Content-Length": str(len(contenido))}
    r.text = contenido.decode("utf-8")
    r.iter_content.return_value = [contenido]
    r.__enter__ = Mock(return_value=r)
    r.__exit__ = Mock(return_value=False)
    if estado >= 400:
        r.raise_for_status.side_effect = requests.HTTPError(f"HTTP {estado}", response=r)
    return r


class Pasaporte(unittest.TestCase):
    def setUp(self):
        self.temporal = tempfile.TemporaryDirectory(prefix="pasaporte_pruebas_")
        self.config = Configuracion(Path(self.temporal.name))
        self.cliente = Mock()

    def tearDown(self):
        self.temporal.cleanup()

    @patch("laboratorio.solicitudes.time.sleep")
    def test_head_reintenta_timeout_y_recupera(self, pausa):
        self.cliente.head.side_effect = [requests.Timeout("timeout"), respuesta(headers={"Content-Length": "100"})]
        self.assertEqual(tamanio_publicado("https://ejemplo", self.cliente), 100)
        self.assertEqual(self.cliente.head.call_count, 2)
        pausa.assert_called_once()

    @patch("laboratorio.solicitudes.time.sleep")
    def test_http_503_se_reintenta(self, pausa):
        self.cliente.get.side_effect = [respuesta(503), respuesta()]
        self.assertEqual(solicitar("GET", "https://ejemplo", self.cliente).status_code, 200)
        self.assertEqual(self.cliente.get.call_count, 2)

    def test_http_403_no_se_reporta_como_no_publicado(self):
        self.cliente.head.return_value = respuesta(403)
        resumen = descargar("yellow", 2026, self.config, (1,), self.cliente, {("yellow", "2026", "01")})
        self.assertEqual(resumen["no_publicados"], [])
        self.assertEqual(resumen["fallidos"], ["yellow 2026-01"])
        self.assertEqual(self.cliente.head.call_count, 1)

    def test_mes_no_enlazado_no_hace_head_ni_get(self):
        resumen = descargar("green", 2026, self.config, (12,), self.cliente, {("green", "2026", "01")})
        self.assertEqual(resumen["no_publicados"], ["green 2026-12"])
        self.cliente.head.assert_not_called()
        self.cliente.get.assert_not_called()

    def test_enlace_publicado_pero_404_es_error(self):
        self.cliente.head.return_value = respuesta(404)
        resumen = descargar("green", 2026, self.config, (1,), self.cliente, {("green", "2026", "01")})
        self.assertEqual(resumen["no_publicados"], [])
        self.assertEqual(resumen["fallidos"], ["green 2026-01"])

    def test_parsea_solo_enlaces_reales_del_anio_y_tipo(self):
        html = b'''<a href="https://ejemplo/green_tripdata_2026-01.parquet">G</a>
        <a href="https://ejemplo/green_tripdata_2026-01.parquet">G duplicado</a>
        <a href="yellow_tripdata_2025-02.parquet">Y 2025</a>
        <a href="fhv_tripdata_2026-01.parquet">FHV</a>
        <p>yellow_tripdata_2026-09.parquet</p>
        <a href="yellow_tripdata_2026-13.parquet">Mes invalido</a>'''
        self.cliente.get.return_value = respuesta(contenido=html)
        self.assertEqual(publicados((2026,), self.cliente), [("green", "2026", "01")])

    def test_parsea_los_tres_primeros_meses_con_espacios_en_href(self):
        html = b"""<a href="https://ejemplo/yellow_tripdata_2024-01.parquet ">Y enero</a>
        <a href="https://ejemplo/yellow_tripdata_2024-02.parquet ">Y febrero</a>
        <a href="https://ejemplo/yellow_tripdata_2024-03.parquet ">Y marzo</a>
        <a href="https://ejemplo/green_tripdata_2024-01.parquet ">G enero</a>
        <a href="https://ejemplo/green_tripdata_2024-02.parquet">G febrero</a>
        <a href="https://ejemplo/green_tripdata_2024-03.parquet ">G marzo</a>"""
        self.cliente.get.return_value = respuesta(contenido=html)
        self.assertEqual(
            publicados((2024,), self.cliente),
            [
                ("green", "2024", "01"),
                ("green", "2024", "02"),
                ("green", "2024", "03"),
                ("yellow", "2024", "01"),
                ("yellow", "2024", "02"),
                ("yellow", "2024", "03"),
            ],
        )

    @patch("laboratorio.adquisicion.publicados", side_effect=requests.ConnectionError("sin red"))
    @patch("laboratorio.adquisicion.descargar_archivo")
    def test_no_descarga_si_no_hay_inventario_oficial(self, transferencia, listado):
        self.assertEqual(descargar_main(["--anios", "2026"]), 1)
        transferencia.assert_not_called()

    def test_get_truncado_sin_content_length_en_head(self):
        ruta = self.config.raiz / "archivo.parquet"
        ruta.write_bytes(b"original")
        self.cliente.get.return_value = respuesta(contenido=b"corto", headers={"Content-Length": "100"})
        with patch("laboratorio.adquisicion.time.sleep"), self.assertRaises(requests.RequestException):
            descargar_archivo("https://ejemplo", ruta, esperado=0, cliente=self.cliente)
        self.assertEqual(ruta.read_bytes(), b"original")
        self.assertEqual(list(self.config.raiz.glob("*.part")), [])

    def test_pie_legible_con_paginas_danadas_se_rechaza(self):
        ruta = self.config.raiz / "paginas_danadas.parquet"
        pq.write_table(pa.table({"dato": list(range(100))}), ruta, compression="gzip", use_dictionary=False)
        contenido = bytearray(ruta.read_bytes())
        longitud_pie = int.from_bytes(contenido[-8:-4], "little")
        inicio_pie = len(contenido) - longitud_pie - 8
        contenido[4:inicio_pie] = b"\0" * (inicio_pie - 4)
        ruta.write_bytes(contenido)
        self.assertTrue(es_parquet_completo(ruta, lectura_completa=False))
        self.assertFalse(es_parquet_completo(ruta))

    def test_tamanio_remoto_desconocido_no_certifica(self):
        self.cliente.head.return_value = respuesta(headers={})
        self.assertEqual(revisar("yellow", 2026, 1, self.config, self.cliente)["estado"], "tamanio remoto desconocido")

    def test_archivo_danado_se_repara(self):
        ruta = self.config.ruta_viajes("green", 2026, 1)
        ruta.parent.mkdir(parents=True)
        ruta.write_bytes(b"danado")
        completo = self.config.raiz / "fuente.parquet"
        pq.write_table(pa.table({"dato": [1, 2]}), completo)
        contenido = completo.read_bytes()
        self.cliente.head.return_value = respuesta(headers={"Content-Length": str(len(contenido))})
        # El cuerpo binario no se necesita como texto en este ensayo.
        r = respuesta(headers={"Content-Length": str(len(contenido))})
        r.iter_content.return_value = [contenido]
        self.cliente.get.return_value = r
        resumen = descargar("green", 2026, self.config, (1,), self.cliente, {("green", "2026", "01")})
        self.assertEqual(resumen["danados"], ["green 2026-01"])
        self.assertEqual(resumen["descargados"], 1)
        self.assertTrue(es_parquet_completo(ruta))

    def test_version_incorrecta_produce_error(self):
        esperadas = versiones_esperadas()
        with patch("laboratorio.diagnostico.version", side_effect=lambda nombre: "0.0.0" if nombre == "duckdb" else esperadas[nombre]):
            _, errores = comprobar_versiones()
        self.assertTrue(any("duckdb" in e and "0.0.0" in e for e in errores))

    def test_persistencia_detecta_carpetas_faltantes(self):
        _, errores = comprobar_persistencia(self.config)
        self.assertTrue(any("data/raw" in e for e in errores))
        self.assertTrue(any("data/processed" in e for e in errores))

    @patch("laboratorio.diagnostico.solicitar", side_effect=requests.ConnectionError("servicio caido"))
    def test_diagnostico_no_oculta_servicios_caidos(self, solicitud):
        _, errores = comprobar_servicios()
        self.assertTrue(any("JupyterLab" in e for e in errores))
        self.assertTrue(any("Metabase" in e for e in errores))


if __name__ == "__main__":
    unittest.main()
