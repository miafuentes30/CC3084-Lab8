"""Calculo transaccional de indicadores y publicacion opcional en Metabase."""

import argparse
import os
from .integridad import guardar_procedencia
from .catalogo_indicadores import INDICADORES
from .parametros import Configuracion


def calcular_indicadores(configuracion=None, anios=None, base=None, reutilizar=False, solo_resumen=False):
    from .resultados_indicadores import calcular
    return calcular(configuracion, anios, base, reutilizar, solo_resumen, catalogo=INDICADORES)


def publicar(config):
    from .cliente_metabase import Metabase
    email, clave = os.environ.get("MB_EMAIL"), os.environ.get("MB_PASSWORD")
    if not email or not clave:
        raise ValueError("Defina MB_EMAIL y MB_PASSWORD en el ambiente para publicar el tablero")
    url = os.environ.get("MB_URL", "http://localhost:3000")
    import json
    evidencia = json.loads((config.resultados / 'indicadores.json').read_text(encoding='utf-8'))
    ruta_base = os.environ.get("MB_DUCKDB_PATH", str(config.raiz / evidencia['base']))
    anterior = config.resultados / 'metabase.json'
    objetos = json.loads(anterior.read_text(encoding='utf-8')).get('objetos', {}) if anterior.exists() else {}
    interpretaciones = config.resultados / evidencia['evidencia'].split('/')[0] / 'interpretaciones.json'
    if interpretaciones.exists():
        textos = json.loads(interpretaciones.read_text(encoding='utf-8'))
        for indicador in INDICADORES:
            indicador['interpretacion'] = textos[indicador['tabla']]
    metabase = Metabase(url, email, clave, ruta_base, objetos=objetos)
    try:
        metabase.esperar()
        metabase.entrar()
        base_id = metabase.base_de_datos()
        metabase.pedir("POST", f"database/{base_id}/sync_schema")
        tarjetas = [metabase.pregunta(base_id, indicador) for indicador in INDICADORES]
        tablero_id = metabase.tablero(tarjetas)
        enlace = f"{os.environ.get('MB_PUBLIC_URL', url).rstrip('/')}/dashboard/{tablero_id}"
        guardar_procedencia(config.resultados / "metabase.json", estado='publicado', tablero_id=tablero_id, url=enlace, objetos=metabase.objetos)
        print(f"Tablero listo: {enlace}")
    finally:
        metabase.sesion.close()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--solo-calcular", action="store_true")
    parser.add_argument("--anios", type=int, nargs="+")
    parser.add_argument("--solo-publicar", action="store_true")
    parser.add_argument("--reutilizar-iniciales", action="store_true")
    parser.add_argument('--reanudar-resumen', action='store_true')
    parser.add_argument('--base', type=str, help='Base agregada existente para reanudar solamente el resumen anual')
    args = parser.parse_args(argv)
    config = Configuracion.del_entorno()
    if not args.solo_calcular and (not os.environ.get("MB_EMAIL") or not os.environ.get("MB_PASSWORD")):
        parser.error("Defina MB_EMAIL y MB_PASSWORD o use --solo-calcular")
    if args.solo_calcular and args.solo_publicar:
        parser.error('Seleccione solo una modalidad')
    if not args.solo_publicar:
        from datetime import datetime, timezone
        sello = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
        base = config.raiz / args.base if args.base else config.procesados / f'tablero_{sello}.duckdb'
        if args.reanudar_resumen and (not args.base or not base.is_file()):
            parser.error('--reanudar-resumen requiere --base con una base agregada existente')
        calcular_indicadores(config, args.anios, base=base, reutilizar=args.reutilizar_iniciales, solo_resumen=args.reanudar_resumen)
    if not args.solo_calcular:
        publicar(config)
    return 0
