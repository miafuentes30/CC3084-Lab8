"""Cliente de Metabase para publicar los indicadores ya calculados."""

import time
import uuid
import requests
from .catalogo_indicadores import INDICADORES, INTERPRETACION_PENDIENTE

NOMBRE_BASE = "Taxis de Nueva York (DuckDB)"
NOMBRE_TABLERO = "Viajes de taxi en Nueva York"
MARCA = 'CC3084-Lab8; gestionado por scripts/construir_tablero.py'

class Metabase:
    def __init__(self, url, email, clave, ruta_base, objetos=None):
        self.url = url.rstrip('/')
        self.email = email
        self.clave = clave
        self.ruta_base = ruta_base
        self.sesion = requests.Session()
        self.objetos = objetos or {}

    def pedir(self, metodo, ruta, **kwargs):
        respuesta = self.sesion.request(metodo, f"{self.url}/api/{ruta}", timeout=120, **kwargs)
        respuesta.raise_for_status()
        return respuesta.json() if respuesta.content else None

    def esperar(self):
        for _ in range(120):
            try:
                if self.pedir("GET", "health").get("status") == "ok":
                    return
            except requests.RequestException:
                pass
            time.sleep(5)
        raise SystemExit("Metabase no respondió en 10 minutos")

    def entrar(self):
        token = self.pedir("GET", "session/properties").get("setup-token")
        if token and not self.pedir("GET", "session/properties").get("has-user-setup"):
            self.pedir("POST", "setup", json={
                "token": token,
                "user": {"email": self.email, "password": self.clave, "first_name": "Lab", "last_name": "DuckDB",
                         "site_name": "Laboratorio 8"},
                "prefs": {"site_name": "Laboratorio 8", "site_locale": "es", "allow_tracking": False},
            })
            print(f"Usuario administrador creado: {self.email}")
        sesion = self.pedir("POST", "session", json={"username": self.email, "password": self.clave})
        self.sesion.headers["X-Metabase-Session"] = sesion["id"]

    def base_de_datos(self):
        detalles = {"database_file": self.ruta_base, "read_only": True, "old_implicit_casting": True}
        for base in self.pedir("GET", "database")["data"]:
            if base.get('description') == MARCA:
                self.pedir("PUT", f"database/{base['id']}", json={"details": detalles})
                self.objetos['base_id'] = base['id']
                return base["id"]
        base = self.pedir("POST", "database", json={"engine": "duckdb", "name": NOMBRE_BASE, "details": detalles, 'description': MARCA})
        self.objetos['base_id'] = base['id']
        return base["id"]

    def archivar_anteriores(self):
        # Compatibilidad: actualizar los objetos propios sustituye el archivado por nombre.
        return None

    def pregunta(self, base_id, indicador):
        etiqueta = {"id": str(uuid.uuid4()), "name": "taxi", "display-name": "Tipo de taxi", "type": "text",
                    "default": "yellow", "required": True}
        etiquetas = {'taxi': etiqueta}
        for nombre, tipo, titulo in [('anio', 'number', 'Año'), ('desde', 'date', 'Periodo desde'), ('hasta', 'date', 'Periodo hasta')]:
            etiquetas[nombre] = {'id': str(uuid.uuid4()), 'name': nombre, 'display-name': titulo, 'type': tipo, 'required': False}
        consulta = (f"SELECT periodo, valor FROM {indicador['tabla']} WHERE taxi = {{{{taxi}}}} "
                    "[[AND year(periodo) = {{anio}}]] [[AND periodo >= {{desde}}]] [[AND periodo <= {{hasta}}]] ORDER BY periodo")
        contenido = {
            "name": indicador["titulo"],
            "description": MARCA + '\n' + indicador["pregunta"] + '\n' + indicador.get('interpretacion', ''),
            "display": "line",
            "dataset_query": {"type": "native", "database": base_id,
                              "native": {"query": consulta, "template-tags": etiquetas}},
            "visualization_settings": {
                "graph.dimensions": ["periodo"],
                "graph.metrics": ["valor"],
                "graph.x_axis.title_text": "Mes",
                "graph.y_axis.title_text": indicador["unidad"],
                "graph.y_axis.auto_range": True,
                "series_settings": {"valor": {"color": "#2a78d6", "title": indicador["unidad"], "line.missing": "none"}},
            },
        }
        identificador = self.objetos.get('tarjetas', {}).get(indicador['tabla'])
        if identificador:
            actual = self.pedir('GET', f'card/{identificador}')
            if not actual.get('description', '').startswith(MARCA):
                raise ValueError('La pregunta registrada no pertenece al laboratorio')
            tarjeta = self.pedir('PUT', f'card/{identificador}', json=contenido)
        else:
            # Recupera creaciones parciales propias, sin tocar objetos homónimos ajenos.
            propias = [c for c in self.pedir('GET', 'card') if c.get('description', '').startswith(MARCA)
                       and c['name'] == indicador['titulo'] and not c.get('archived')]
            tarjeta = self.pedir('PUT', f"card/{propias[0]['id']}", json=contenido) if propias else self.pedir('POST', 'card', json=contenido)
        self.objetos.setdefault('tarjetas', {})[indicador['tabla']] = tarjeta['id']
        return tarjeta["id"]

    def tablero(self, tarjetas):
        filtro = {"id": "taxi", "name": "Tipo de taxi", "slug": "taxi", "type": "string/=",
                  "sectionId": "string", "default": ["yellow"],
                  "values_source_type": "static-list", "values_source_config": {"values": ["yellow", "green"]}}
        filtros = [filtro, {'id': 'anio', 'name': 'Año', 'slug': 'anio', 'type': 'number/='},
                   {'id': 'desde', 'name': 'Periodo desde (inicio de mes)', 'slug': 'desde', 'type': 'date/single'},
                   {'id': 'hasta', 'name': 'Periodo hasta', 'slug': 'hasta', 'type': 'date/single'}]
        identificador = self.objetos.get('tablero_id')
        if identificador:
            tablero = self.pedir('GET', f'dashboard/{identificador}')
            if tablero.get('description') != MARCA:
                raise ValueError('El tablero registrado no pertenece al laboratorio')
        else:
            propios = []
            if self.objetos.get('tarjetas'):
                propios = [d for d in self.pedir('GET', 'dashboard') if d.get('description') == MARCA and not d.get('archived')]
            tablero = propios[0] if propios else self.pedir("POST", "dashboard", json={"name": NOMBRE_TABLERO, 'description': MARCA, "parameters": filtros})
        encabezado = ("# Viajes de taxi en Nueva York\n"
                      "Indicadores mensuales de taxis amarillos (yellow) y verdes (green) calculados con DuckDB sobre los "
                      "Parquet de la TLC. El filtro de arriba cambia el tipo de taxi de todas las gráficas.")
        celdas = [self.texto(-1, 0, 0, 24, 3, encabezado)]
        siguiente = -2
        for n, (indicador, tarjeta_id) in enumerate(zip(INDICADORES, tarjetas)):
            fila, columna = 3 + (n // 3) * 11, (n % 3) * 8
            celdas.append({
                "id": siguiente, "card_id": tarjeta_id, "row": fila, "col": columna, "size_x": 8, "size_y": 6,
                "parameter_mappings": [{"parameter_id": nombre, "card_id": tarjeta_id,
                                        "target": ["variable", ["template-tag", nombre]]} for nombre in ('taxi', 'anio', 'desde', 'hasta')],
                "visualization_settings": {},
            })
            texto = f"**{indicador['pregunta']}**\n\n{indicador.get('interpretacion', INTERPRETACION_PENDIENTE)}"
            celdas.append(self.texto(siguiente - 1, fila + 6, columna, 8, 5, texto))
            siguiente -= 2
        self.pedir("PUT", f"dashboard/{tablero['id']}", json={"dashcards": celdas, "parameters": filtros})
        self.objetos['tablero_id'] = tablero['id']
        return tablero["id"]

    @staticmethod
    def texto(id_, fila, columna, ancho, alto, contenido):
        return {
            "id": id_, "card_id": None, "row": fila, "col": columna, "size_x": ancho, "size_y": alto,
            "parameter_mappings": [],
            "visualization_settings": {
                "virtual_card": {"name": None, "display": "text", "visualization_settings": {},
                                 "dataset_query": {}, "archived": False},
                "text": contenido,
            },
        }
