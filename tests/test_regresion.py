"""Pruebas integradas de consultas, benchmarks y fallos de descarga."""

import csv
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

import duckdb
import requests

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from laboratorio.sesion_consultas import Analisis
from laboratorio.integridad import es_parquet_completo, es_catalogo_zonas
from laboratorio.mediciones import CONJUNTOS, ejecutar, iguales, medir
from laboratorio.parametros import Configuracion
from laboratorio.adquisicion import descargar, descargar_archivo, tamanio_publicado
from laboratorio.generacion_indicadores import calcular_indicadores
from laboratorio.cliente_metabase import Metabase
from laboratorio.completitud import publicados, revisar
from datos_prueba import crear_datos


class Funcional(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temporal = tempfile.TemporaryDirectory(prefix="lab8_pruebas_")
        cls.config = Configuracion(Path(cls.temporal.name))
        crear_datos(cls.config.raiz)

    @classmethod
    def tearDownClass(cls):
        cls.temporal.cleanup()

    def test_todas_las_consultas_en_las_tres_etapas(self):
        for anios in ((2026,), (2024, 2026), (2024, 2025, 2026)):
            with self.subTest(anios=anios), Analisis(self.config, anios=anios) as analisis:
                revision = analisis.revisar_consultas()
                self.assertEqual(len(revision), 44)
                self.assertTrue(revision.estado.eq("ok").all(), revision[revision.estado.ne("ok")].to_string())

    def test_columnas_ausentes_y_reglas_de_calidad(self):
        with Analisis(self.config, anios=(2024,)) as analisis:
            self.assertEqual(analisis.con.execute("SELECT max(cbd_congestion_fee) FROM viajes").fetchone()[0], 0)
            self.assertEqual(analisis.con.execute("SELECT count(request_source) FROM viajes").fetchone()[0], 0)
        with Analisis(self.config, periodos=("2026-01",)) as analisis:
            self.assertEqual(analisis.con.execute("SELECT count(*) FROM viajes_validos").fetchone()[0], 8)
            self.assertEqual(analisis.con.execute("SELECT count(*) FROM viajes").fetchone()[0], 18)

    def test_refrescar_vistas_incorpora_archivos_recien_descargados(self):
        ruta = self.config.ruta_viajes("yellow", 2026, 12)
        with Analisis(self.config, anios=(2026,)) as analisis:
            antes = analisis.con.execute("SELECT count(*) FROM viajes").fetchone()[0]
            try:
                ruta.write_bytes(self.config.ruta_viajes("yellow", 2026, 1).read_bytes())
                analisis.crear_vistas()
                despues = analisis.con.execute("SELECT count(*) FROM viajes").fetchone()[0]
                self.assertEqual(despues, antes + 9)
            finally:
                ruta.unlink(missing_ok=True)

    def test_mes_sin_viajes_validos_reporta_cien_por_ciento(self):
        with Analisis(self.config, anios=(2024,)) as analisis:
            datos = analisis.consulta("metricas/09_porcentaje_exclusion.sql", mostrar_sql=False)
            fila = datos[(datos.taxi == "green") & (datos.periodo.dt.month == 2)]
            self.assertEqual(fila.valor.tolist(), [100.0])

    def test_benchmarks_no_incorporan_2025(self):
        tablas, tiempos = ejecutar(self.config, repeticiones=2)
        self.assertEqual([t["archivos"] for t in tablas], [2, 16, 40])
        self.assertEqual(len(tiempos), 42)
        self.assertTrue(all(t["mismo_resultado"] for t in tiempos))
        with duckdb.connect(str(self.config.procesados / "benchmark_20_meses.duckdb"), read_only=True) as con:
            self.assertEqual(con.execute("SELECT DISTINCT year(periodo) FROM viajes ORDER BY 1").fetchall(), [(2024,), (2026,)])
        with (self.config.resultados / "benchmark_tiempos.csv").open(newline="") as archivo:
            self.assertEqual(len(list(csv.DictReader(archivo))), 42)

    def test_indicadores_recalculables_y_solo_lectura(self):
        base = calcular_indicadores(self.config, anios=(2024, 2026))
        calcular_indicadores(self.config, anios=(2024, 2025, 2026))
        with duckdb.connect(str(base), read_only=True) as con:
            self.assertEqual(con.execute("SELECT count(*) FROM information_schema.tables").fetchone()[0], 9)
            self.assertEqual(con.execute("SELECT DISTINCT year(periodo) FROM i1_viajes_por_dia ORDER BY 1").fetchall(), [(2024,), (2025,), (2026,)])

    def test_indicadores_conservan_tablas_anteriores_si_falla_un_sql(self):
        from laboratorio.catalogo_indicadores import INDICADORES
        base = calcular_indicadores(self.config, anios=(2024,))
        alterados = [dict(i) for i in INDICADORES]
        alterados[4]["sql"] = "archivo_inexistente.sql"
        with patch("laboratorio.generacion_indicadores.INDICADORES", alterados):
            with self.assertRaises(FileNotFoundError):
                calcular_indicadores(self.config, anios=(2024, 2025, 2026))
        with duckdb.connect(str(base), read_only=True) as con:
            self.assertEqual(con.execute("SELECT DISTINCT year(periodo) FROM i1_viajes_por_dia").fetchall(), [(2024,)])

    def test_comparacion_de_resultados(self):
        self.assertFalse(iguales([(1, 2)], [(1,)]))
        self.assertFalse(iguales([(float('nan'),)], [(1.0,)]))
        self.assertTrue(iguales([(1, 2.0), (2, 4.0)], [(2, 4.001), (1, 2.001)]))
        self.assertFalse(iguales([(1, 2.0)], [(1, 3.0)]))
        with self.assertRaises(ValueError):
            medir(None, "SELECT 1", repeticiones=0)

    def test_resumen_separado_conserva_resultados(self):
        from laboratorio.resultados_indicadores import resumen_anual
        periodos = ['2026-01']
        with Analisis(self.config, periodos=periodos) as sesion:
            cursor = sesion.con.execute(sesion.leer_sql('comparacion_anual/01_resumen_periodos_comparables.sql'))
            columnas = [d[0] for d in cursor.description]
            esperado = cursor.fetchall()
        separado = resumen_anual(self.config, 2026, periodos, {'threads': 1, 'memory_limit': '1GiB'})
        self.assertTrue(iguales(esperado, [tuple(f[c] for c in columnas) for f in separado]))

    def test_metabase_conserva_objetos_ajenos_y_actualiza_propios(self):
        from laboratorio.cliente_metabase import MARCA, NOMBRE_BASE
        from laboratorio.catalogo_indicadores import INDICADORES
        cliente = Metabase('http://ejemplo', 'equipo@example.test', 'clave-prueba', '/workspace/data/processed/tablero.duckdb')
        cliente.pedir = Mock(side_effect=[{'data': [{'id': 3, 'name': NOMBRE_BASE, 'description': 'ajeno'}]}, {'id': 12}])
        self.assertEqual(cliente.base_de_datos(), 12)
        self.assertEqual(cliente.pedir.call_args_list[1].args[:2], ('POST', 'database'))
        cliente.objetos['tarjetas'] = {INDICADORES[0]['tabla']: 77}
        cliente.pedir = Mock(side_effect=[{'id': 77, 'description': MARCA}, {'id': 77}])
        self.assertEqual(cliente.pregunta(12, INDICADORES[0]), 77)
        self.assertEqual(cliente.pedir.call_args_list[1].args[:2], ('PUT', 'card/77'))
        self.assertEqual(set(cliente.pedir.call_args.kwargs['json']['dataset_query']['native']['template-tags']), {'taxi', 'anio', 'desde', 'hasta'})
        cliente.sesion.close()

    def test_parquet_falso_y_catalogo_invalido(self):
        ruta = self.config.raiz / "falso.parquet"
        ruta.write_bytes(b"PAR1contenido_invalidoPAR1")
        self.assertFalse(es_parquet_completo(ruta))
        self.assertFalse(es_catalogo_zonas(ruta))

    @staticmethod
    def respuesta(contenido=b"", estado=200, headers=None):
        respuesta = Mock()
        respuesta.__enter__ = Mock(return_value=respuesta)
        respuesta.__exit__ = Mock(return_value=False)
        respuesta.status_code = estado
        respuesta.headers = headers or {"Content-Length": str(len(contenido))}
        respuesta.iter_content.return_value = [contenido]
        respuesta.text = contenido.decode("utf-8", errors="replace")
        return respuesta

    def test_descarga_no_publicado_y_error_de_red(self):
        cliente = Mock()
        cliente.head.return_value = self.respuesta(estado=404)
        self.assertIsNone(tamanio_publicado("https://ejemplo", cliente))
        cliente.head.side_effect = requests.ConnectionError("Sin red")
        with self.assertRaises(requests.ConnectionError):
            tamanio_publicado("https://ejemplo", cliente)

    def test_descarga_atomica_rechaza_html_y_transferencia_incompleta(self):
        destino = self.config.raiz / "conservar.parquet"
        destino.write_bytes(b"original")
        cliente = Mock()
        cliente.get.return_value = self.respuesta(b"<html>error</html>")
        with self.assertRaises(requests.RequestException):
            descargar_archivo("https://ejemplo", destino, validar=es_parquet_completo, cliente=cliente)
        self.assertEqual(destino.read_bytes(), b"original")
        self.assertFalse(destino.with_name(destino.name + ".part").exists())
        with self.assertRaises(requests.RequestException):
            descargar_archivo("https://ejemplo", destino, esperado=1000, cliente=cliente)

    def test_descarga_valida_se_omite_en_la_segunda_ejecucion(self):
        contenido = self.config.ruta_viajes("yellow", 2026, 1).read_bytes()
        destino = self.config.ruta_viajes("yellow", 2026, 12)
        destino.unlink(missing_ok=True)
        cliente = Mock()
        cliente.head.return_value = self.respuesta(contenido)
        cliente.get.return_value = self.respuesta(contenido)
        primero = descargar("yellow", 2026, self.config, (12,), cliente)
        segundo = descargar("yellow", 2026, self.config, (12,), cliente)
        self.assertEqual(primero["descargados"], 1)
        self.assertEqual(segundo["omitidos"], 1)
        self.assertEqual(cliente.get.call_count, 1)
        destino.unlink()

    def test_verificacion_no_certifica_una_pagina_vacia(self):
        cliente = Mock()
        cliente.get.return_value = self.respuesta(b"<html></html>")
        with self.assertRaises(ValueError):
            publicados((2026,), cliente)
        cliente.get.return_value.raise_for_status.side_effect = requests.HTTPError("HTTP 500")
        with self.assertRaises(requests.HTTPError):
            publicados((2026,), cliente)

    def test_verificacion_local_y_error_remoto(self):
        cliente = Mock()
        ruta = self.config.ruta_viajes("yellow", 2026, 1)
        cliente.head.return_value = self.respuesta(headers={"Content-Length": str(ruta.stat().st_size)})
        fila = revisar("yellow", 2026, 1, self.config, cliente)
        self.assertEqual((fila["estado"], fila["registros"]), ("completo", 9))
        cliente.head.side_effect = requests.ConnectionError("Sin red")
        self.assertEqual(revisar("yellow", 2026, 1, self.config, cliente)["estado"], "error de red")

    def test_metabase_conexion_solo_lectura_y_filtro(self):
        cliente = Metabase("http://ejemplo", "equipo@example.test", "clave-prueba", "/workspace/data/processed/tablero.duckdb")
        cliente.pedir = Mock(side_effect=[{"data": []}, {"id": 12}])
        self.assertEqual(cliente.base_de_datos(), 12)
        self.assertTrue(cliente.pedir.call_args.kwargs["json"]["details"]["read_only"])
        cliente.pedir = Mock(side_effect=[{"id": 15}, {}])
        self.assertEqual(cliente.tablero(list(range(9))), 15)
        carga = cliente.pedir.call_args.kwargs["json"]
        tarjetas = [c for c in carga["dashcards"] if c["card_id"] is not None]
        self.assertEqual(len(tarjetas), 9)
        self.assertTrue(all(c["parameter_mappings"][0]["parameter_id"] == "taxi" for c in tarjetas))
        cliente.sesion.close()


if __name__ == "__main__":
    unittest.main()
