"""Catalogo unico de indicadores usado por notebooks y Metabase."""

INDICADORES = [
    {
        "tabla": "i1_viajes_por_dia",
        "sql": "01_promedio_diario.sql",
        "titulo": "I1 Viajes por dia",
        "pregunta": "Cuantos viajes hay por dia y como cambia entre meses y anios?",
        "unidad": "Viajes por dia",
    },
    {
        "tabla": "i2_total_mediano",
        "sql": "02_mediana_cobro.sql",
        "titulo": "I2 Total del viaje mediano",
        "pregunta": "Cuanto paga un pasajero en un viaje tipico?",
        "unidad": "Dolares",
    },
    {
        "tabla": "i3_flex_fare",
        "sql": "03_porcentaje_tarifa_fija.sql",
        "titulo": "I3 Viajes Flex Fare",
        "pregunta": "Que parte de los viajes se pide con tarifa fija por aplicacion?",
        "unidad": "% de los viajes",
    },
    {
        "tabla": "i4_efectivo",
        "sql": "04_porcentaje_efectivo.sql",
        "titulo": "I4 Viajes pagados en efectivo",
        "pregunta": "Se sigue usando el efectivo?",
        "unidad": "% de los viajes",
    },
    {
        "tabla": "i5_propina_tarjeta",
        "sql": "05_propina_por_tarjeta.sql",
        "titulo": "I5 Propina con tarjeta",
        "pregunta": "Cuanta propina deja quien paga con tarjeta?",
        "unidad": "% de la tarifa",
    },
    {
        "tabla": "i6_cargo_cbd",
        "sql": "06_incidencia_cargo_cbd.sql",
        "titulo": "I6 Viajes con cargo CBD",
        "pregunta": "A cuantos viajes alcanza el cobro por congestion?",
        "unidad": "% de los viajes",
    },
    {
        "tabla": "i7_velocidad_manhattan",
        "sql": "07_velocidad_interna_manhattan.sql",
        "titulo": "I7 Velocidad en Manhattan",
        "pregunta": "Cambio la velocidad de los viajes dentro de Manhattan?",
        "unidad": "Millas por hora",
    },
    {
        "tabla": "i8_aeropuertos",
        "sql": "08_participacion_aeropuertos.sql",
        "titulo": "I8 Viajes de aeropuerto",
        "pregunta": "Que peso tienen los viajes desde o hacia Newark, JFK y LaGuardia?",
        "unidad": "% de los viajes",
    },
    {
        "tabla": "i9_registros_excluidos",
        "sql": "09_porcentaje_exclusion.sql",
        "titulo": "I9 Registros excluidos",
        "pregunta": "Que parte de los registros no pasa las reglas de calidad?",
        "unidad": "% de los registros",
    },
]

INTERPRETACION_PENDIENTE = "Interpretacion pendiente de regenerar con los datos y evidencias del equipo."

PREGUNTAS = [
    '¿Cuántos viajes válidos se realizan por día en cada mes y tipo de taxi?',
    '¿La demanda mantiene el mismo patrón mensual en los años comparables?',
    '¿Cómo cambia el monto mediano pagado por un viaje válido?',
    '¿Qué proporción se registra con código de pago 0 o nulo (convención Flex Fare)?',
    '¿Cómo evoluciona la proporción de pagos en efectivo?',
    '¿Qué porcentaje de la tarifa representa la propina en pagos con tarjeta?',
    '¿Cómo cambia la incidencia registrada del cargo CBD?',
    '¿Cómo evoluciona la velocidad mediana de viajes internos de Manhattan?',
    '¿Qué participación tienen los viajes con origen o destino en aeropuertos?',
    '¿Qué porcentaje de registros originales excluyen las reglas de calidad?',
]
JUSTIFICACIONES = [
    'Normaliza la demanda por los días calendario del mes; permite comparar meses de distinta duración.',
    'Describe un cobro típico con menor influencia de montos extremos que la media.',
    'Sigue la composición del código de pago. Los nulos se agrupan con 0 por convención, sin demostrar origen en una aplicación.',
    'Compara un medio de pago mediante proporciones, independientemente del tamaño de cada taxi.',
    'Usa pagos con tarjeta y tarifa positiva; la ausencia de propina en efectivo no equivale a ausencia de propina real.',
    'Mide incidencia positiva del cargo. Los nulos históricos se normalizan a cero; no permite inferir causalidad.',
    'Compara velocidad entre zonas de un mismo distrito y limita la influencia de valores extremos con la mediana.',
    'Resume la participación de Newark, JFK y LaGuardia mediante sus identificadores de zona.',
    'Hace explícita la selección analítica y su denominador de registros originales.',
]
for indicador, justificacion in zip(INDICADORES, JUSTIFICACIONES):
    indicador['justificacion'] = justificacion
