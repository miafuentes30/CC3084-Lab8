"""Presentación de agregados pequeños, sin volver a consultar Parquet."""
import json
from pathlib import Path

import pandas as pd
from .catalogo_indicadores import INDICADORES, PREGUNTAS
from .graficos import grafica_indicador


def interpretar(datos, indicador):
    d = datos.assign(anio=datos.periodo.dt.year, mes=datos.periodo.dt.month)
    anios = sorted(d.anio.unique())
    inicial, final = anios[0], anios[-1]
    textos = []
    for taxi, nombre in [('yellow', 'Amarillos'), ('green', 'Verdes')]:
        parte = d[(d.taxi == taxi) & (d.mes <= 8)]
        a = parte[parte.anio == inicial].set_index('mes').valor
        b = parte[parte.anio == final].set_index('mes').valor
        pareados = pd.concat([a.rename('a'), b.rename('b')], axis=1).dropna()
        if pareados.empty:
            textos.append(f'{nombre}: sin meses comparables con valores disponibles.')
            continue
        if indicador['tabla'] == 'i1_viajes_por_dia':
            diferencia = 100 * (pareados.b / pareados.a - 1)
            unidad = '%'
        else:
            diferencia = pareados.b - pareados.a
            unidad = 'puntos porcentuales' if indicador['unidad'].startswith('%') else indicador['unidad'].lower()
        textos.append(f'{nombre}: de {inicial} a {final}, la diferencia mensual en enero–agosto '
                      f'va de {diferencia.min():.2f} a {diferencia.max():.2f} {unidad}. '
                      f'Valores de {final}: {pareados.b.min():.2f}–{pareados.b.max():.2f} {indicador["unidad"].lower()}.')
    return ' '.join(textos) + ' Comparación descriptiva; no establece causalidad.'


def mostrar(carpeta, indicador):
    from IPython.display import display, Markdown
    datos = pd.read_csv(carpeta / (indicador['tabla'] + '.csv'), parse_dates=['periodo'])
    display(datos.pivot(index='periodo', columns='taxi', values='valor'))
    fig = grafica_indicador(datos, indicador['titulo'], indicador['unidad'])
    fig.savefig(carpeta / (indicador['tabla'] + '.png'), bbox_inches='tight')
    texto = interpretar(datos, indicador)
    display(Markdown(texto))
    return texto


def tabla_md(datos):
    columnas = list(datos.columns)
    lineas = ['| ' + ' | '.join(columnas) + ' |', '| ' + ' | '.join('---' for _ in columnas) + ' |']
    for fila in datos.itertuples(index=False, name=None):
        lineas.append('| ' + ' | '.join(f'{v:.2f}' if isinstance(v, float) else str(v) for v in fila) + ' |')
    return '\n'.join(lineas)


def documentar(config, fase):
    carpeta = config.resultados / fase
    evidencia = json.loads((carpeta / 'indicadores.json').read_text(encoding='utf-8'))
    # Añade las tres consultas realmente usadas, sin ejecutarlas nuevamente.
    from .resultados_indicadores import consultas_resumen
    import hashlib
    if 'sql_comparacion_ejecutado' not in evidencia:
        evidencia['sql_comparacion_ejecutado'] = {str(anio): consultas_resumen(anio,
            sorted({f['periodo'] for f in evidencia['inventario'] if f['anio'] == anio and int(f['periodo'][-2:]) <= 8}))
            for anio in evidencia['anios']}
    if 'contratos_sha256' not in evidencia:
        evidencia['contratos_sha256'] = {n: hashlib.sha256((config.sql / n).read_bytes()).hexdigest()
            for n in ('normalizacion_viajes.sql', 'reglas_compartidas.sql')}
        zonas = config.raw / 'zonas/taxi_zone_lookup.csv'
        evidencia['contratos_sha256']['zonas'] = hashlib.sha256(zonas.read_bytes()).hexdigest() if zonas.exists() else None
    (carpeta / 'indicadores.json').write_text(json.dumps(evidencia, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    inventario = pd.read_csv(carpeta / 'inventario.csv')
    demanda = pd.read_csv(carpeta / 'i1_viajes_por_dia.csv', parse_dates=['periodo'])
    demanda['anio'] = demanda.periodo.dt.year
    bruto = inventario.groupby(['anio', 'taxi']).agg(archivos=('archivo', 'size'), registros_brutos=('registros', 'sum')).reset_index()
    validos = demanda.groupby(['anio', 'taxi']).viajes_validos.sum().reset_index()
    conteos = bruto.merge(validos, how='left').fillna({'viajes_validos': 0})
    conteos['exclusion_pct'] = 100 * (1 - conteos.viajes_validos / conteos.registros_brutos)
    resumen = pd.read_csv(carpeta / 'comparacion_enero_agosto.csv').sort_values(['taxi', 'anio'])
    textos = {}
    secciones = []
    for indicador in INDICADORES:
        datos = pd.read_csv(carpeta / (indicador['tabla'] + '.csv'), parse_dates=['periodo'])
        textos[indicador['tabla']] = interpretar(datos, indicador)
        secciones.append(f"## {indicador['titulo']}\n\n{indicador['pregunta']}\n\n"
            f"Justificación: {indicador['justificacion']}\n\n"
            f"SQL: [metricas/{indicador['sql']}](../../sql/metricas/{indicador['sql']}).\n\n"
            f"```sql\n{evidencia['sql'][indicador['tabla']]}\n```\n\n"
            f"Resultados mensuales: [{indicador['tabla']}.csv]({fase}/{indicador['tabla']}.csv).\n\n"
            f"![{indicador['titulo']}]({fase}/{indicador['tabla']}.png)\n\n{textos[indicador['tabla']]}")
    (carpeta / 'interpretaciones.json').write_text(json.dumps(textos, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    conteos.to_csv(carpeta / 'conteos_por_anio.csv', index=False)
    patrones = []
    for taxi, nombre in [('yellow', 'amarillos'), ('green', 'verdes')]:
        datos = resumen[resumen.taxi == taxi]
        for columna, titulo in [('viajes_por_dia', 'viajes válidos por día'), ('pct_flex_fare', 'porcentaje con pago 0/nulo'), ('pct_efectivo', 'porcentaje en efectivo'), ('total_mediano', 'monto mediano pagado')]:
            secuencia = '; '.join(f"{int(f.anio)}: {getattr(f, columna):.2f}" for f in datos.itertuples())
            patrones.append(f'- Taxis {nombre}, {titulo}, enero–agosto: {secuencia}.')
    titulo = 'Ejercicio 7: indicadores de 2024 y 2026' if fase == 'ejercicio_7' else 'Ejercicio 8: análisis completo de 2024, 2025 y 2026'
    texto = f'''# {titulo}

Resultados reales de `{evidencia['base']}`. Se calculan nueve indicadores
mensuales con DuckDB, dos hilos y 1 GiB; pandas presenta únicamente agregados.
El cálculo por mes limita el estado de las medianas. La comparación anual se
ejecuta por año, separando conteos/medias y las dos medianas exactas,
seleccionando enero–agosto. No se repite el benchmark.

## Cobertura, filas originales y selección analítica

{tabla_md(conteos)}

2024 y 2025 tienen doce meses; 2026 tiene ocho. Los totales anteriores
describen la cobertura disponible y no son una comparación anual equivalente.
Las reglas de [viajes_validos](../../sql/reglas_compartidas.sql) filtran
fechas, duración, distancia, velocidad y montos; no se eliminan filas originales.
I9 usa originales como denominador; los demás indicadores usan viajes válidos,
con filtros adicionales explícitos para tarjeta o zonas de Manhattan.

## Diez preguntas analíticas

{chr(10).join(f'{n}. {p}' for n, p in enumerate(PREGUNTAS, 1))}

## Comparación equivalente enero–agosto

{tabla_md(resumen[['anio','taxi','registros_brutos','viajes_validos','dias_calendario','viajes_por_dia','total_mediano','pct_flex_fare','pct_efectivo','pct_cargo_cbd','velocidad_manhattan','pct_aeropuerto']])}

Se usan 244 días calendario en 2024 y 243 en 2025/2026. Los LEFT JOIN del
catálogo conservan viajes válidos sin zona catalogada en el denominador general;
el indicador de Manhattan exige coincidencia de ambas zonas. Las medianas
anuales se calculan sobre viajes, sin promediar medianas mensuales.

## Hallazgos medidos

{chr(10).join(patrones)}

Las diferencias son descriptivas. El agrupamiento de pago nulo con 0 es una
convención heredada; por sí solo no identifica aplicaciones. CBD cero en
2024 incluye nulos normalizados. Los cambios de calidad pueden alterar la
población analítica; no se atribuyen cambios a una política sin evidencia.

## Tablero y reproducción

Las tablas persistentes contienen agregados pequeños, apropiados para visitas
repetidas del tablero. Esto difiere de materializar viajes completos en el
benchmark. La publicación usa el driver DuckDB existente, modo de lectura,
variables MB_EMAIL/MB_PASSWORD y filtros de taxi, año y fechas simples.
Actualiza solo objetos marcados como CC3084-Lab8; conserva los IDs propios y
no archiva objetos por coincidencia de nombre.

**Estado real:** publicación pendiente por falta de credenciales. No se
presenta una captura histórica como evidencia. Consulte [publicación](../publicacion_metabase.md).
El [tablero HTML local](tablero_indicadores.html) ofrece filtros y gráficas sin credenciales;
no representa una publicación en Metabase.

Los comandos reproducibles están en [README](../../README.md). El notebook
de esta etapa lee estos CSV; no repite la descarga ni las agregaciones.
Inventario, SQL exacto, hashes, tiempos y configuración: [{fase}/indicadores.json]({fase}/indicadores.json).
'''
    if fase == 'ejercicio_8':
        texto += '\nLa ampliación reutiliza los 20 meses de 2024/2026 solo después de verificar tamaño, fecha, filas y hashes del SQL. Calcula los doce meses nuevos de 2025. La validación oficial de 2025 está en `ejercicio_8_verificacion_2025.json` y su CSV.\n'
    texto += '\n\n' + '\n\n'.join(secciones) + '\n'
    nombre = 'ejercicio_7_indicadores.md' if fase == 'ejercicio_7' else 'ejercicio_8_analisis_completo.md'
    (config.resultados / nombre).write_text(texto, encoding='utf-8')
    tablero_local(config, fase)


def tablero_local(config, fase):
    import csv
    series = []
    for i in INDICADORES:
        with (config.resultados / fase / (i['tabla'] + '.csv')).open(encoding='utf-8', newline='') as f:
            valores = list(csv.DictReader(f))
        series.append(dict(titulo=i['titulo'], unidad=i['unidad'], pregunta=i['pregunta'], valores=valores))
    contenido = '''<!doctype html><html lang="es"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>CC3084 · Indicadores de taxis</title><style>
body{margin:24px auto;padding:0 20px;max-width:1300px;font:16px system-ui;color:#263343;background:#f4f6f9}
header{margin-bottom:24px}select{padding:8px;margin:4px 14px 4px 0}main{display:grid;grid-template-columns:repeat(auto-fit,minmax(350px,1fr));gap:16px}
article{background:white;padding:18px;border:1px solid #dce2ea;border-radius:12px}h2{font-size:18px;margin:0 0 8px}p{color:#516073;font-size:14px}svg{width:100%;height:auto}.leyenda{font-size:13px}
</style><header><h1>Indicadores de taxis de Nueva York</h1>
<p>DuckDB · agregados mensuales reales. Vista local reproducible; publicación en Metabase pendiente de credenciales.</p>
<label>Taxi <select id="taxi"><option value="yellow">Amarillo</option><option value="green">Verde</option></select></label>
<label>Año <select id="anio"><option value="todos">Comparar años</option></select></label>
<label>Periodo <select id="mes"><option value="12">Cobertura disponible</option><option value="8">Enero–agosto comparable</option></select></label>
<p>2026 tiene enero–agosto. I9 usa registros originales; los demás usan viajes válidos. Las diferencias no prueban causalidad.</p></header><main></main><script>
const series=__DATOS__, colores={2024:'#2879bd',2025:'#df6b36',2026:'#198260'};
const selector=document.querySelector('#anio');
[...new Set(series.flatMap(s=>s.valores.map(v=>v.periodo.slice(0,4))))].sort().forEach(a=>{const o=document.createElement('option');o.value=a;o.textContent=a;selector.append(o)});
function render(){const taxi=document.querySelector('#taxi').value,anio=selector.value,mes=+document.querySelector('#mes').value;const main=document.querySelector('main');main.replaceChildren();
for(const s of series){const d=s.valores.filter(v=>v.taxi===taxi&&(+v.periodo.slice(5,7)<=mes)&&(anio==='todos'||v.periodo.startsWith(anio))&&v.valor!=='');
const card=document.createElement('article');const h=document.createElement('h2');h.textContent=s.titulo;card.append(h);const p=document.createElement('p');p.textContent=s.pregunta+' · '+s.unidad;card.append(p);
const max=Math.max(1,...d.map(v=>+v.valor))*1.1;let svg='<svg viewBox="0 0 420 250" role="img" aria-label="Serie mensual">';
for(let k=0;k<5;k++){const y=210-k*43;svg+=`<line x1="45" x2="400" y1="${y}" y2="${y}" stroke="#e0e5ed"/><text x="40" y="${y+4}" text-anchor="end" font-size="11">${(k*max/4).toLocaleString('es',{maximumFractionDigits:1})}</text>`}
for(let m=1;m<=12;m++)svg+=`<text x="${45+(m-1)*32}" y="235" text-anchor="middle" font-size="11">${m}</text>`;
const years=[...new Set(d.map(v=>v.periodo.slice(0,4)))].sort();for(const a of years){const rows=d.filter(v=>v.periodo.startsWith(a)).sort((x,y)=>x.periodo.localeCompare(y.periodo));const points=rows.map(v=>`${45+(+v.periodo.slice(5,7)-1)*32},${210-(+v.valor/max)*172}`).join(' ');svg+=`<polyline points="${points}" fill="none" stroke="${colores[a]}" stroke-width="2.5"/>`;for(const v of rows)svg+=`<circle cx="${45+(+v.periodo.slice(5,7)-1)*32}" cy="${210-(+v.valor/max)*172}" r="3" fill="${colores[a]}"><title>${v.periodo}: ${v.valor}</title></circle>`}
svg+='</svg>';card.insertAdjacentHTML('beforeend',svg);const legend=document.createElement('p');legend.className='leyenda';legend.textContent='Mes del año · '+years.join(' / ');card.append(legend);main.append(card)}}
document.querySelectorAll('select').forEach(s=>s.addEventListener('change',render));render();
</script></html>'''
    contenido = contenido.replace('__DATOS__', json.dumps(series, ensure_ascii=False).replace('</', '<\\/'))
    (config.resultados / 'tablero_indicadores.html').write_text(contenido, encoding='utf-8')
