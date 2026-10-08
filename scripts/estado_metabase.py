"""Diagnóstico sin mostrar credenciales ni tokens."""
import json
import os
import requests

estado = {k + '_disponible': bool(os.environ.get(k)) for k in ('MB_EMAIL', 'MB_PASSWORD')}
for url in (os.environ.get('MB_URL', 'http://metabase:3000'),):
    try:
        respuesta = requests.get(url.rstrip('/') + '/api/health', timeout=5)
        estado['salud'] = respuesta.status_code
    except requests.RequestException:
        estado['salud'] = 'no disponible'
print(json.dumps(estado))
