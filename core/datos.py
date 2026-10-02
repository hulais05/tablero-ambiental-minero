"""
Escenario sintético de monitoreo ambiental minero y lectura de planillas de
laboratorio.

IMPORTANTE: todo lo que produce este módulo es ficticio. Proyectos, empresas,
comunidades, laboratorios, puntos y valores son inventados. Las coordenadas
caen en la Puna pero no corresponden a ningún proyecto real.

Lo que sí es realista son los órdenes de magnitud y los fenómenos que un
tablero ambiental tiene que saber mostrar sin asustar ni tapar nada:
  - arsénico y boro naturales por encima del nivel guía (el fondo de la Puna);
  - un nivel freático que desciende desde que empieza el bombeo;
  - picos de material particulado en temporada de viento;
  - un metal que sube aguas abajo de un dique de colas, y baja con la medida
    correctiva;
  - un laboratorio cuyo límite de detección no alcanza para evaluar.
"""

import io
import math
import random
import re
from datetime import date, datetime, timedelta

import pandas as pd

from .catalogo import (LIQUIDAS, SOLIDAS, clave, convertir, parametro_por_nombre,
                       unidad_canonica, unidad_conocida)

# --------------------------------------------------------------- escenario ---

PROYECTOS = [
    {"id": "SALAR-A", "nombre": "Proyecto Salar A", "empresa": "Empresa A S.A.",
     "provincia": "Jujuy", "mineral": "Litio (salmuera)", "etapa": "Producción",
     "lat": -23.80, "lon": -66.45, "laboratorio": "Laboratorio Norte"},
    {"id": "SALAR-B", "nombre": "Proyecto Salar B", "empresa": "Empresa B S.A.",
     "provincia": "Salta", "mineral": "Litio (salmuera)", "etapa": "Construcción",
     "lat": -24.35, "lon": -66.95, "laboratorio": "Laboratorio Andino"},
    {"id": "CERRO-C", "nombre": "Proyecto Cerro C", "empresa": "Empresa C S.A.",
     "provincia": "Jujuy", "mineral": "Plata y zinc", "etapa": "Producción",
     "lat": -22.55, "lon": -66.05, "laboratorio": "Laboratorio Norte"},
]

# (id, proyecto, nombre, matriz, uso, Δlat, Δlon respecto del centro del proyecto)
_PUNTOS = [
    ("SA-AS-01", "SALAR-A", "Vega Norte", "agua_superficial", "bebida_ganado", 0.06, 0.04),
    ("SA-AS-02", "SALAR-A", "Laguna del salar", "agua_superficial", "vida_acuatica",
     -0.03, -0.04),
    ("SA-SB-01", "SALAR-A", "Pozo de agua PA-1 (campamento)", "agua_subterranea",
     "fuente_bebida", 0.03, 0.07),
    ("SA-SB-02", "SALAR-A", "Pozo de monitoreo PM-3 (borde del salar)", "agua_subterranea",
     "bebida_ganado", 0.01, -0.02),
    ("SA-SM-01", "SALAR-A", "Pozo de salmuera PS-2", "salmuera", None, -0.02, -0.01),
    ("SA-AI-01", "SALAR-A", "Estación de aire · campamento", "aire", "aire_ambiente",
     0.03, 0.06),
    ("SA-AI-02", "SALAR-A", "Estación de aire · Comunidad A", "aire", "aire_ambiente",
     0.10, 0.09),
    ("SA-RU-01", "SALAR-A", "Ruido · límite de planta", "ruido", None, 0.02, 0.05),
    ("SA-SU-01", "SALAR-A", "Suelo · área de pozas", "suelo", "industrial", -0.01, 0.01),
    ("SA-SU-02", "SALAR-A", "Suelo · Vega Norte", "suelo", "agricola", 0.06, 0.045),
    ("SA-CS-01", "SALAR-A", "Costra salina · núcleo", "costra_salina", None, -0.04, -0.05),

    ("SB-AS-01", "SALAR-B", "Arroyo de aporte", "agua_superficial", "bebida_ganado",
     0.07, 0.05),
    ("SB-AS-02", "SALAR-B", "Laguna de flamencos", "agua_superficial", "vida_acuatica",
     -0.04, 0.03),
    ("SB-SB-01", "SALAR-B", "Pozo de agua industrial PI-1", "agua_subterranea", "riego",
     0.02, 0.06),
    ("SB-SB-02", "SALAR-B", "Pozo de monitoreo PM-1", "agua_subterranea", "bebida_ganado",
     -0.01, 0.02),
    ("SB-SM-01", "SALAR-B", "Pozo de salmuera exploratorio", "salmuera", None, -0.03, -0.02),
    ("SB-AI-01", "SALAR-B", "Estación de aire · Comunidad B", "aire", "aire_ambiente",
     0.09, 0.08),
    ("SB-RU-01", "SALAR-B", "Ruido · obrador", "ruido", None, 0.02, 0.07),
    ("SB-SU-01", "SALAR-B", "Suelo · obrador", "suelo", "industrial", 0.02, 0.065),
    ("SB-CS-01", "SALAR-B", "Costra salina · sector sur", "costra_salina", None, -0.06, -0.01),

    ("CC-AS-01", "CERRO-C", "Río · aguas arriba (control)", "agua_superficial",
     "vida_acuatica", 0.05, -0.05),
    ("CC-AS-02", "CERRO-C", "Río · aguas abajo del dique de colas", "agua_superficial",
     "vida_acuatica", -0.04, 0.03),
    ("CC-AS-03", "CERRO-C", "Vertiente · Comunidad C", "agua_superficial", "agua_potable",
     -0.07, 0.06),
    ("CC-SB-01", "CERRO-C", "Pozo de monitoreo · pie del dique", "agua_subterranea",
     "bebida_ganado", -0.02, 0.01),
    ("CC-AI-01", "CERRO-C", "Estación de aire · planta", "aire", "aire_ambiente", 0.01, 0.0),
    ("CC-AI-02", "CERRO-C", "Estación de aire · Comunidad C", "aire", "aire_ambiente",
     -0.07, 0.07),
    ("CC-RU-01", "CERRO-C", "Ruido · Comunidad C", "ruido", None, -0.068, 0.065),
    ("CC-SU-01", "CERRO-C", "Suelo · escombrera", "suelo", "industrial", 0.015, -0.015),
    ("CC-SU-02", "CERRO-C", "Suelo · pastizal aguas abajo", "suelo", "agricola", -0.05, 0.04),
]

_PROYECTO_DE = {i: pr for i, pr, *_ in _PUNTOS}

_AGUA = ["ph", "conductividad", "sdt", "dureza", "arsenico", "boro", "litio", "plomo",
         "cadmio", "cromo", "cobre", "zinc", "mercurio", "sulfatos", "cloruros", "nitratos"]
PARAMETROS_MATRIZ = {
    "agua_superficial": _AGUA,
    "agua_subterranea": _AGUA + ["nivel_freatico"],
    "salmuera": ["ph", "sdt", "litio", "potasio", "magnesio", "boro"],
    "aire": ["pm10"],
    "ruido": ["nivel_sonoro"],
    "suelo": ["arsenico", "plomo", "cadmio", "cromo", "cobre", "zinc", "mercurio"],
    "costra_salina": ["litio", "boro", "arsenico"],
}
# El agua de un yacimiento metalífero suma hierro y manganeso.
_METALIFERO = {"CERRO-C": ["hierro", "manganeso"]}

# Fondo natural típico por familia de matriz, en unidades canónicas.
_FONDO = {
    "agua": {"ph": 8.1, "conductividad": 2400, "sdt": 1500, "dureza": 260,
             "arsenico": 0.03, "boro": 3.0, "litio": 1.2, "plomo": 0.003,
             "cadmio": 0.0004, "cromo": 0.0008, "cobre": 0.0025, "zinc": 0.012,
             "mercurio": 0.0003, "sulfatos": 260, "cloruros": 420, "nitratos": 2.5,
             "hierro": 0.15, "manganeso": 0.05, "nivel_freatico": 12.0},
    "salmuera": {"ph": 7.1, "sdt": 330_000, "litio": 650, "potasio": 5400,
                 "magnesio": 1700, "boro": 880},
    "aire": {"pm10": 30},
    "ruido": {"nivel_sonoro": 41},
    "suelo": {"arsenico": 12, "plomo": 18, "cadmio": 0.3, "cromo": 22, "cobre": 19,
              "zinc": 58, "mercurio": 0.04},
    "costra_salina": {"litio": 580, "boro": 2900, "arsenico": 35},
}

# Lo que hace distinto a cada punto. Acá vive el fondo natural de la Puna:
# la laguna tiene arsénico y boro por encima del nivel guía desde antes de que
# existiera el proyecto, y eso es lo que la línea de base tiene que demostrar.
_FONDO_PUNTO = {
    ("SA-AS-02", "arsenico"): 0.12, ("SA-AS-02", "boro"): 9.0,
    ("SA-AS-02", "conductividad"): 9800, ("SA-AS-02", "sdt"): 6500,
    ("SA-SB-01", "sdt"): 700, ("SA-SB-01", "conductividad"): 1100,
    ("SA-SB-01", "nivel_freatico"): 35.0,
    ("SA-SB-02", "nivel_freatico"): 8.0,
    ("SA-AS-01", "arsenico"): 0.08,
    ("SA-SU-02", "arsenico"): 24,
    ("SA-RU-01", "nivel_sonoro"): 52,
    ("SB-AS-02", "arsenico"): 0.025, ("SB-AS-02", "boro"): 7.0,
    ("SB-SB-01", "nivel_freatico"): 22.0, ("SB-SB-02", "nivel_freatico"): 6.5,
    ("SB-RU-01", "nivel_sonoro"): 49,
    ("CC-AS-01", "boro"): 0.4, ("CC-AS-01", "arsenico"): 0.02,
    ("CC-AS-02", "boro"): 0.45, ("CC-AS-02", "arsenico"): 0.022,
    ("CC-AS-03", "arsenico"): 0.028, ("CC-AS-03", "boro"): 0.25,
    ("CC-AS-03", "sdt"): 600, ("CC-AS-03", "conductividad"): 900,
    ("CC-AS-03", "sulfatos"): 150, ("CC-AS-03", "cloruros"): 120,
    ("CC-SB-01", "nivel_freatico"): 4.2,
    ("CC-SU-01", "arsenico"): 34, ("CC-SU-01", "plomo"): 160, ("CC-SU-01", "zinc"): 420,
    ("CC-AI-01", "pm10"): 38,
}

# Variabilidad natural entre campañas: relativa para concentraciones, absoluta
# para pH, niveles y ruido.
_VARIACION = {"ph": ("abs", 0.10), "nivel_freatico": ("abs", 0.06),
              "nivel_sonoro": ("abs", 1.2), "pm10": ("rel", 0.22)}
_VARIACION_SALMUERA = ("rel", 0.05)
_VARIACION_POR_DEFECTO = ("rel", 0.10)

# Límites de detección habituales, en unidades canónicas.
_LD = {
    "liquido": {"sdt": 10, "dureza": 2, "arsenico": 0.005, "boro": 0.05, "litio": 0.01,
                "plomo": 0.002, "cadmio": 0.001, "cromo": 0.001, "cobre": 0.002,
                "zinc": 0.005, "mercurio": 0.001, "sulfatos": 5, "cloruros": 5,
                "nitratos": 0.5, "hierro": 0.02, "manganeso": 0.01, "potasio": 1,
                "magnesio": 1},
    "solido": {"arsenico": 0.5, "plomo": 1, "cadmio": 0.1, "cromo": 1, "cobre": 1,
               "zinc": 2, "mercurio": 0.05, "litio": 1, "boro": 5},
}
# El Laboratorio Andino informa cromo con un método de LD 0,005 mg/L. El nivel
# guía para vida acuática es 0,002: "no detectado" con ese método no prueba
# que cumpla. Es un problema real y frecuente, y el tablero lo tiene que decir.
_LD_LABORATORIO = {"Laboratorio Andino": {"cromo": 0.005}}

# 6 campañas de línea de base (antes de operar) y 8 de operación, trimestrales.
CALENDARIO = [(2023, 6), (2023, 9), (2023, 12), (2024, 3), (2024, 6), (2024, 9),
              (2024, 12), (2025, 3), (2025, 6), (2025, 9), (2025, 12), (2026, 3),
              (2026, 6), (2026, 9)]
N_LINEA_BASE = 6
_DIA = {"SALAR-A": 3, "SALAR-B": 5, "CERRO-C": 8}

TIPO_BASE = "Línea de base"
TIPO_MAP = "Monitoreo ambiental participativo"

# La campaña de septiembre de 2026 del Salar A no está en el historial: es la
# que la empresa sube en la demostración, desde la planilla del laboratorio.
CAMPANIA_DEMO = "SALAR-A-2026-09"
# La del Salar B está presentada y espera la revisión de la autoridad.
CAMPANIA_EN_REVISION = "SALAR-B-2026-09"


def _familia(matriz):
    return "agua" if matriz in ("agua_superficial", "agua_subterranea") else matriz


def _tendencia(punto, parametro, k):
    """Cambio respecto del fondo en la campaña operativa k (0 = primera)."""
    if (punto, parametro) == ("SA-SB-02", "nivel_freatico"):
        # Descenso del nivel desde que arranca el bombeo: la profundidad crece.
        return 0.17 * (k + 1)
    if (punto, parametro) == ("CC-AS-02", "zinc"):
        # Sube aguas abajo del dique y empieza a bajar con la medida correctiva,
        # aplicada después de la campaña de marzo de 2026 (k = 5).
        pico = min(k, 5)
        return 0.0042 * (pico + 1) - 0.006 * max(0, k - 5)
    return 0.0


def _estacional(parametro, mes):
    # Agosto-septiembre es la temporada de viento en la Puna.
    return 1.8 if parametro == "pm10" and mes == 9 else 1.0


# Eventos puntuales, ya en unidades canónicas.
_EVENTOS = {
    ("SB-AI-01", "pm10", (2025, 9)): 176.0,
    ("SB-AI-01", "pm10", (2026, 9)): 163.0,
}

_JUSTIFICACIONES = {
    ("SB-AI-01", "pm10", (2025, 9)):
        "Evento de viento blanco con ráfagas de más de 60 km/h, registrado por la "
        "estación meteorológica del proyecto. Se suspendieron los movimientos de suelo "
        "durante 48 h y se reforzó el riego de caminos.",
    ("SB-AI-01", "pm10", (2026, 9)):
        "Temporada de viento: dos días con ráfagas superiores a 55 km/h. Se aplicó el "
        "protocolo de suspensión de movimientos de suelo y se adjunta el registro "
        "meteorológico.",
}
for _k, (_a, _m) in enumerate(CALENDARIO[N_LINEA_BASE:]):
    if _k == 3:
        _JUSTIFICACIONES[("CC-AS-02", "zinc", (_a, _m))] = (
            "Primer registro de zinc por encima del nivel guía aguas abajo del dique de "
            "colas. Se abrió una investigación de causa y el muestreo pasó a ser mensual.")
    elif _k in (4, 5):
        _JUSTIFICACIONES[("CC-AS-02", "zinc", (_a, _m))] = (
            "Continúa la investigación de causa: se identificó una filtración en el canal "
            "perimetral del dique. El muestreo sigue siendo mensual.")
    elif _k >= 6:
        _JUSTIFICACIONES[("CC-AS-02", "zinc", (_a, _m))] = (
            "El canal perimetral del dique se impermeabilizó en abril de 2026. El zinc "
            "aguas abajo bajó desde entonces; el muestreo sigue siendo mensual hasta "
            "volver al rango de la línea de base.")


def _redondear(valor, parametro):
    if parametro in ("ph", "nivel_freatico"):
        return round(valor, 2)
    if parametro in ("nivel_sonoro", "pm10"):
        return round(valor, 1)
    if valor == 0:
        return 0.0
    # Tres cifras significativas: lo que informa un laboratorio.
    return round(valor, -int(math.floor(math.log10(abs(valor)))) + 2)


def _simular(semilla):
    """Todas las campañas de todos los proyectos, incluida la de la demo."""
    rnd = random.Random(semilla)
    puntos = puntos_df()
    filas = []
    for proyecto in PROYECTOS:
        pid = proyecto["id"]
        lab = proyecto["laboratorio"]
        mios = puntos[puntos["proyecto_id"] == pid]
        for n, (anio, mes) in enumerate(CALENDARIO):
            fecha = date(anio, mes, _DIA[pid])
            cid = f"{pid}-{anio}-{mes:02d}"
            k = n - N_LINEA_BASE                      # < 0 durante la línea de base
            for _, p in mios.iterrows():
                fam = _familia(p["matriz"])
                params = PARAMETROS_MATRIZ[p["matriz"]] + (
                    _METALIFERO.get(pid, []) if fam == "agua" else [])
                for par in params:
                    base = _FONDO_PUNTO.get((p["id"], par), _FONDO[fam][par])
                    tipo, sigma = _VARIACION.get(
                        par, _VARIACION_SALMUERA if fam == "salmuera" else _VARIACION_POR_DEFECTO)
                    if tipo == "abs":
                        valor = base + rnd.gauss(0, sigma)
                    else:
                        valor = base * math.exp(rnd.gauss(0, sigma)) * _estacional(par, mes)
                    if k >= 0:
                        valor += _tendencia(p["id"], par, k)
                    valor = _EVENTOS.get((p["id"], par, (anio, mes)), valor)

                    ld = None
                    medio = ("liquido" if p["matriz"] in LIQUIDAS
                             else "solido" if p["matriz"] in SOLIDAS else None)
                    if medio:
                        ld = _LD_LABORATORIO.get(lab, {}).get(par, _LD[medio].get(par))
                    calificador = ""
                    if ld is not None and valor < ld:
                        calificador, valor = "<", ld
                    filas.append({
                        "campania_id": cid, "proyecto_id": pid, "punto_id": p["id"],
                        "fecha": fecha, "matriz": p["matriz"], "parametro": par,
                        "calificador": calificador,
                        "valor": _redondear(valor, par),
                        "unidad": unidad_canonica(par, p["matriz"]),
                        "ld": ld,
                    })
    return pd.DataFrame(filas)


def puntos_df():
    centro = {p["id"]: (p["lat"], p["lon"]) for p in PROYECTOS}
    return pd.DataFrame([
        {"id": i, "proyecto_id": pr, "nombre": nom, "matriz": mat, "uso": uso,
         "lat": round(centro[pr][0] + dlat, 5), "lon": round(centro[pr][1] + dlon, 5)}
        for i, pr, nom, mat, uso, dlat, dlon in _PUNTOS
    ])


def _campania(pid, anio, mes, n):
    proyecto = next(p for p in PROYECTOS if p["id"] == pid)
    letra = pid.split("-")[1]
    fecha = date(anio, mes, _DIA[pid])
    cid = f"{pid}-{anio}-{mes:02d}"
    es_base = n < N_LINEA_BASE
    participantes = ([] if es_base else
                     [f"Comunidad {letra}", "Municipio", "Autoridad minera provincial",
                      "Autoridad ambiental provincial"])
    presentada = datetime.combine(fecha + timedelta(days=12), datetime.min.time()).replace(
        hour=10)
    aprobada = presentada + timedelta(days=12, hours=5)
    historial = [
        {"fecha_hora": presentada, "actor": f"Responsable ambiental · {proyecto['empresa']}",
         "rol": "empresa", "accion": "Presentó la campaña", "estado": "PRESENTADA",
         "comentario": ""},
    ]
    estado = "PRESENTADA"
    if cid != CAMPANIA_EN_REVISION:
        historial.append(
            {"fecha_hora": aprobada, "actor": "Dirección de Minería · Área de Control Ambiental",
             "rol": "autoridad", "accion": "Aprobó y publicó", "estado": "APROBADA",
             "comentario": "Revisada sin observaciones."})
        estado = "APROBADA"
    justificaciones = {
        f"{punto}|{par}": texto
        for (punto, par, cuando), texto in _JUSTIFICACIONES.items()
        if _PROYECTO_DE[punto] == pid and cuando == (anio, mes)
    }
    return {
        "id": cid, "proyecto_id": pid, "fecha": fecha,
        "tipo": TIPO_BASE if es_base else TIPO_MAP,
        "laboratorio": f"{proyecto['laboratorio']} (ficticio)",
        "acreditacion": "ISO/IEC 17025",
        "consultora": "Consultora ambiental (ficticia)",
        "participantes": participantes,
        "estado": estado, "historial": historial, "justificaciones": justificaciones,
    }


def generar_escenario(semilla=2026):
    """Proyectos, puntos, campañas y resultados del historial publicado.

    Devuelve un dict. `resultados` trae todas las campañas salvo la de la demo,
    que sale en `demo` para armar la planilla del laboratorio.
    """
    todos = _simular(semilla)
    campanias = {}
    for pid in (p["id"] for p in PROYECTOS):
        for n, (anio, mes) in enumerate(CALENDARIO):
            c = _campania(pid, anio, mes, n)
            if c["id"] != CAMPANIA_DEMO:
                campanias[c["id"]] = c
    demo = todos[todos["campania_id"] == CAMPANIA_DEMO].reset_index(drop=True)
    return {
        "proyectos": pd.DataFrame(PROYECTOS),
        "puntos": puntos_df(),
        "campanias": campanias,
        "resultados": todos[todos["campania_id"] != CAMPANIA_DEMO].reset_index(drop=True),
        "demo": demo,
    }


def nueva_campania(proyecto, fecha, tipo=TIPO_MAP, datos=None):
    """Campaña en borrador, lista para recibir los resultados de una planilla.

    `proyecto` es el registro del proyecto (o su id, en el escenario
    sintético). `datos` trae laboratorio, consultora y participantes cuando se
    conocen; si no, quedan los del escenario sintético.
    """
    if isinstance(proyecto, str):
        proyecto = next(p for p in PROYECTOS if p["id"] == proyecto)
    pid = proyecto["id"]
    if datos is None:
        letra = pid.split("-")[1] if "-" in pid else pid
        datos = {"laboratorio": f"{proyecto.get('laboratorio', 'Laboratorio')} (ficticio)",
                 "acreditacion": "ISO/IEC 17025",
                 "consultora": "Consultora ambiental (ficticia)",
                 "participantes": [f"Comunidad {letra}", "Municipio",
                                   "Autoridad minera provincial",
                                   "Autoridad ambiental provincial"]}
    return {
        "id": f"{pid}-{fecha.year}-{fecha.month:02d}",
        "proyecto_id": pid, "fecha": fecha, "tipo": tipo,
        "laboratorio": datos.get("laboratorio", "s/d"),
        "acreditacion": datos.get("acreditacion", "s/d"),
        "consultora": datos.get("consultora", "s/d"),
        "participantes": list(datos.get("participantes", [])),
        "estado": "BORRADOR", "historial": [], "justificaciones": {},
    }


# ------------------------------------------------- planilla del laboratorio ---
# Así llega una campaña real: un libro de Excel con una hoja por grupo de
# matrices, encabezados a gusto del laboratorio, coma decimal, "<0,005" para lo
# no detectado y algún que otro error de carga. La planilla de la demo trae
# cuatro errores sembrados a propósito, para que se vea qué hace el sistema.

_HOJAS = {
    "Aguas": {
        "matrices": ("agua_superficial", "agua_subterranea"),
        "columnas": [("pH", "ph", None), ("CE (µS/cm)", "conductividad", None),
                     ("SDT (mg/L)", "sdt", None),
                     ("Dureza total (mg/L CaCO3)", "dureza", None),
                     ("As (mg/L)", "arsenico", None), ("B (mg/L)", "boro", None),
                     ("Li (mg/L)", "litio", None), ("Pb (mg/L)", "plomo", None),
                     ("Cd (mg/L)", "cadmio", None), ("Cr total (mg/L)", "cromo", None),
                     ("Cu (mg/L)", "cobre", None), ("Zn (mg/L)", "zinc", None),
                     ("Hg (mg/L)", "mercurio", None), ("Sulfatos (mg/L)", "sulfatos", None),
                     ("Cloruros (mg/L)", "cloruros", None),
                     ("Nitratos (mg/L)", "nitratos", None),
                     ("Nivel freático (m)", "nivel_freatico", None)],
    },
    "Salmuera": {
        "matrices": ("salmuera",),
        # La salmuera se informa en g/L de sólidos: el sistema convierte solo.
        "columnas": [("pH", "ph", None), ("Densidad (g/cm3)", None, None),
                     ("SDT (g/L)", "sdt", 1e-3), ("Li (mg/L)", "litio", None),
                     ("K (mg/L)", "potasio", None), ("Mg (mg/L)", "magnesio", None),
                     ("B (mg/L)", "boro", None)],
    },
    "Aire y ruido": {
        "matrices": ("aire", "ruido"),
        "columnas": [("PM10 24 h (µg/m³)", "pm10", None), ("LAeq (dBA)", "nivel_sonoro", None)],
    },
    "Suelos y costra": {
        "matrices": ("suelo", "costra_salina"),
        "columnas": [("As (mg/kg)", "arsenico", None), ("Pb (mg/kg)", "plomo", None),
                     ("Cd (mg/kg)", "cadmio", None), ("Cr (mg/kg)", "cromo", None),
                     ("Cu (mg/kg)", "cobre", None), ("Zn (mg/kg)", "zinc", None),
                     ("Hg (mg/kg)", "mercurio", None), ("Li (mg/kg)", "litio", None),
                     ("B (mg/kg)", "boro", None)],
    },
}


def _texto_lab(calificador, valor):
    """Como lo escribe el laboratorio: coma decimal y '<' para lo no detectado."""
    txt = f"{valor:.6g}".replace(".", ",")
    return f"<{txt}" if calificador == "<" else txt


def libro_laboratorio_ejemplo(escenario):
    """XLSX de la campaña de la demo, tal como lo entregaría el laboratorio."""
    demo = escenario["demo"]
    puntos = escenario["puntos"].set_index("id")
    salida = io.BytesIO()
    with pd.ExcelWriter(salida, engine="openpyxl") as libro:
        for hoja, spec in _HOJAS.items():
            filas = []
            for pid, grupo in demo.groupby("punto_id", sort=True):
                if puntos.loc[pid, "matriz"] not in spec["matrices"]:
                    continue
                valores = {r.parametro: (r.calificador, r.valor) for r in grupo.itertuples()}
                fila = {"Punto de muestreo": pid,
                        "Fecha de muestreo": grupo["fecha"].iloc[0].strftime("%d/%m/%Y"),
                        "Hora": "10:30"}
                for encabezado, par, factor in spec["columnas"]:
                    if par is None:
                        fila[encabezado] = "1,21"           # densidad: no es un parámetro
                    elif par in valores:
                        cal, val = valores[par]
                        fila[encabezado] = _texto_lab(cal, val * (factor or 1))
                    else:
                        fila[encabezado] = ""
                fila["Observaciones"] = ""
                filas.append(fila)
            tabla = pd.DataFrame(filas)
            if hoja == "Aguas":
                # Error 1: el arsénico de la Vega Norte cargado en µg/L dentro de
                # una columna en mg/L. Mil veces más: el sistema lo tiene que ver.
                i = tabla.index[tabla["Punto de muestreo"] == "SA-AS-01"][0]
                tabla.loc[i, "As (mg/L)"] = "45"
                tabla.loc[i, "Observaciones"] = "Repetida por control de calidad"
                # Boro de la Vega Norte en el 88 % del nivel guía de bebida de
                # ganado: no supera, pero merece atención.
                tabla.loc[i, "B (mg/L)"] = "4,4"
                # Error 2: un punto que no existe en el registro (tipeo).
                fantasma = tabla.loc[[i]].copy()
                fantasma["Punto de muestreo"] = "SA-AS-9"
                tabla = pd.concat([tabla, fantasma], ignore_index=True)
            if hoja == "Suelos y costra":
                # Error 3: un dato sin informar.
                i = tabla.index[tabla["Punto de muestreo"] == "SA-SU-01"][0]
                tabla.loc[i, "Hg (mg/kg)"] = "s/d"
            tabla.to_excel(libro, sheet_name=hoja, index=False)
    return salida.getvalue()


# Etiqueta corta con la que un laboratorio encabeza cada parámetro. Lo que no
# está acá se encabeza con el nombre del catálogo.
_ETIQUETA_LAB = {
    "ph": "pH", "conductividad": "CE", "sdt": "SDT", "dureza": "Dureza total",
    "arsenico": "As", "boro": "B", "litio": "Li", "potasio": "K", "magnesio": "Mg",
    "plomo": "Pb", "cadmio": "Cd", "cromo": "Cr total", "cobre": "Cu", "zinc": "Zn",
    "mercurio": "Hg", "hierro": "Fe", "manganeso": "Mn", "sulfatos": "Sulfatos",
    "cloruros": "Cloruros", "nitratos": "Nitratos", "cianuro": "CN total",
    "nivel_freatico": "Nivel freático", "pm10": "PM10 24 h", "nivel_sonoro": "LAeq",
}

# Hojas de la planilla de un escenario real: una por grupo de matrices.
_HOJAS_REALES = [
    ("Aguas", ("agua_superficial", "agua_subterranea")),
    ("Aire y ruido", ("aire", "ruido")),
    ("Suelos y sedimentos", ("suelo", "sedimento", "costra_salina")),
]


def _encabezado(parametro, unidad):
    from .catalogo import nombre_parametro
    etiqueta = _ETIQUETA_LAB.get(parametro) or nombre_parametro(parametro)
    return f"{etiqueta} ({unidad})" if unidad and unidad != "upH" else etiqueta


def libro_laboratorio(escenario):
    """XLSX de la campaña de la demostración, como lo entregaría el laboratorio.

    En el escenario sintético es la planilla de siempre. En uno real se arma
    con los valores tal cual los informó el laboratorio, más los errores de
    carga que el escenario declara en su proyecto.json (`errores_demo`), para
    que se vea qué hace el control con ellos. Esos errores son lo único que
    no viene de la fuente, y la interfaz lo dice.
    """
    meta = escenario.get("meta", {})
    if not meta.get("real"):
        return libro_laboratorio_ejemplo(escenario)
    demo = escenario["demo"]
    puntos = escenario["puntos"].set_index("id")
    errores = meta.get("errores_demo", [])
    salida = io.BytesIO()
    with pd.ExcelWriter(salida, engine="openpyxl") as libro:
        for hoja, matrices in _HOJAS_REALES:
            parte = demo[demo["matriz"].isin(matrices)]
            if parte.empty:
                continue
            columnas = []
            for par, uni in parte[["parametro", "unidad"]].drop_duplicates().itertuples(
                    index=False):
                if (par, uni) not in columnas:
                    columnas.append((par, uni))
            from .catalogo import PARAMETROS
            orden = list(PARAMETROS)
            columnas.sort(key=lambda c: orden.index(c[0]) if c[0] in orden else len(orden))
            filas = []
            for (pid, fecha), grupo in parte.groupby(["punto_id", "fecha"], sort=True):
                valores = {r.parametro: r for r in grupo.itertuples()}
                fila = {"Punto de muestreo": pid,
                        "Fecha de muestreo": fecha.strftime("%d/%m/%Y")}
                for par, uni in columnas:
                    r = valores.get(par)
                    if r is None:
                        fila[_encabezado(par, uni)] = ""
                    elif hay_texto(getattr(r, "valor_original", "")):
                        fila[_encabezado(par, uni)] = str(r.valor_original)
                    else:
                        fila[_encabezado(par, uni)] = _texto_lab(r.calificador, r.valor)
                fila["Observaciones"] = ""
                filas.append(fila)
            tabla = pd.DataFrame(filas)
            for e in errores:
                if e.get("hoja") != hoja:
                    continue
                donde = tabla.index[tabla["Punto de muestreo"] == e["punto"]]
                if len(donde) == 0:
                    continue
                i = donde[0]
                if e["tipo"] == "valor":
                    tabla.loc[i, e["columna"]] = e["valor"]
                    if e.get("observacion"):
                        tabla.loc[i, "Observaciones"] = e["observacion"]
                elif e["tipo"] == "punto":
                    copia = tabla.loc[[i]].copy()
                    copia["Punto de muestreo"] = e["valor"]
                    tabla = pd.concat([tabla, copia], ignore_index=True)
            tabla.to_excel(libro, sheet_name=hoja, index=False)
    return salida.getvalue()


def hay_texto(x):
    return x is not None and not (isinstance(x, float) and math.isnan(x)) and str(x).strip() != ""


# ------------------------------------------------------------------ ingesta ---
# El sistema no pide un formato nuevo: toma la planilla tal como la entrega el
# laboratorio. Reconoce las columnas por sinónimo, saca la unidad del
# encabezado, entiende la coma decimal y el "<LD", y si algo no se puede leer
# lo informa con hoja, fila y columna en vez de descartarlo en silencio.

ALIAS = {
    "punto_id": ["punto", "punto_id", "id_punto", "punto_muestreo", "codigo_punto",
                 "estacion", "sitio", "id_sitio", "codigo"],
    "fecha": ["fecha", "fecha_muestreo", "fecha_toma", "fecha_extraccion", "fecha_medicion"],
    "parametro": ["parametro", "analito", "determinacion", "variable"],
    "valor": ["valor", "resultado", "concentracion", "medicion", "valor_medido"],
    "unidad": ["unidad", "unidades", "um", "unid"],
    "ld": ["ld", "lod", "limite_deteccion", "lim_deteccion", "lc", "lq",
           "limite_cuantificacion"],
}

_SIN_DATO = {"", "-", "--", "—", "s/d", "sd", "n/a", "na", "nan", "none", "nm",
             "no medido", "sin dato"}
_NO_DETECTADO = {"nd", "n.d.", "n/d", "no detectado", "<ld", "< ld", "<lc", "<lq", "bld"}
_NUMERO = re.compile(r"[-+]?\d[\d.,]*(?:[eE][-+]?\d+)?")
_UNIDAD_ENTRE = re.compile(r"[\(\[]\s*([^\)\]]+?)\s*[\)\]]")


def _a_numero(texto):
    """Número desde texto de laboratorio. La coma es decimal.

    Con un solo separador no hay forma segura de distinguir decimal de miles
    ("1.500" puede ser uno y medio o mil quinientos). Se toma como decimal, que
    es lo habitual en resultados de laboratorio, y el control de escala contra
    la línea de base marca después cualquier valor que haya quedado mil veces
    corrido.
    """
    m = _NUMERO.search(str(texto))
    if not m:
        raise ValueError(f"no es un número: {texto!r}")
    num = m.group(0)
    coma, punto = num.rfind(","), num.rfind(".")
    if coma >= 0 and punto >= 0:
        num = (num.replace(".", "").replace(",", ".") if coma > punto
               else num.replace(",", ""))
    elif coma >= 0:
        num = num.replace(",", ".") if num.count(",") == 1 else num.replace(",", "")
    elif num.count(".") > 1:
        num = num.replace(".", "")
    return float(num)


def leer_valor(crudo):
    """(calificador, valor) desde una celda. None si la celda no trae dato.

    '0,012' → ('', 0.012) · '<0,005' → ('<', 0.005) · 'ND' → ('<', None)
    """
    if crudo is None:
        return None
    if isinstance(crudo, float) and math.isnan(crudo):
        return None
    if isinstance(crudo, (int, float)) and not isinstance(crudo, bool):
        return "", float(crudo)
    txt = str(crudo).strip()
    bajo = txt.lower()
    if bajo in _SIN_DATO:
        return None
    if bajo in _NO_DETECTADO:
        return "<", None
    calificador = ""
    if txt[:1] in "<>":
        calificador, txt = txt[0], txt[1:].strip()
    return calificador, _a_numero(txt)


def leer_fecha(crudo):
    """Fecha desde celda de Excel o texto. Día primero: acá se escribe d/m/a."""
    if crudo is None or (isinstance(crudo, float) and math.isnan(crudo)):
        raise ValueError("fecha vacía")
    if isinstance(crudo, pd.Timestamp):
        return crudo.date()
    if isinstance(crudo, datetime):
        return crudo.date()
    if isinstance(crudo, date):
        return crudo
    txt = str(crudo).strip()[:10]
    for formato in ("%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y", "%d/%m/%y", "%d.%m.%Y"):
        try:
            return datetime.strptime(txt, formato).date()
        except ValueError:
            continue
    raise ValueError(f"fecha ilegible: {crudo!r}")


def separar_unidad(encabezado):
    """'As (mg/L)' → ('As', 'mg/L'). 'As mg/L' → ('As', 'mg/L'). 'pH' → ('pH', None)."""
    texto = str(encabezado).strip()
    m = _UNIDAD_ENTRE.search(texto)
    if m:
        return (texto[:m.start()] + texto[m.end():]).strip(), m.group(1)
    partes = texto.rsplit(" ", 1)
    if len(partes) == 2 and unidad_conocida(partes[1]):
        return partes[0].strip(), partes[1]
    return texto, None


def _mapear_identificadores(columnas):
    normalizadas = {clave(c): c for c in columnas}
    mapa = {}
    for campo, alias in ALIAS.items():
        for a in alias:
            if a in normalizadas:
                mapa[campo] = normalizadas[a]
                break
    return mapa


def leer_archivo(nombre, contenido):
    """[(hoja, DataFrame)] desde un XLSX (todas las hojas) o un CSV."""
    if nombre.lower().endswith((".xlsx", ".xlsm")):
        hojas = pd.read_excel(io.BytesIO(contenido), sheet_name=None, dtype=object)
        return [(h, t) for h, t in hojas.items() if not t.dropna(how="all").empty]
    try:
        texto = contenido.decode("utf-8-sig")
    except UnicodeDecodeError:
        # Los CSV que exporta Excel en Windows vienen en cp1252, no en UTF-8.
        texto = contenido.decode("cp1252", errors="replace")
    tabla = pd.read_csv(io.StringIO(texto), sep=None, engine="python", dtype=str)
    return [("CSV", tabla)]


def interpretar(tablas, puntos, fecha_campania=None):
    """Convierte las hojas del laboratorio en resultados en formato largo.

    Acepta dos formas: "ancha" (una fila por muestra, una columna por
    parámetro, la unidad en el encabezado) y "larga" (una fila por resultado,
    con columnas de parámetro, valor y unidad). Devuelve (resultados, informe).
    Las filas que no se pueden leer quedan en `resultados` con `error`
    completo: el sistema las muestra para corregir, no las esconde.
    """
    por_id = {str(i).upper(): i for i in puntos["id"]}
    por_nombre = {clave(n): i for i, n in zip(puntos["id"], puntos["nombre"])}
    matriz_de = dict(zip(puntos["id"], puntos["matriz"]))

    filas, columnas, ignoradas, avisos = [], [], [], []
    formatos = {}
    sin_unidad_avisada = set()

    for hoja, tabla in tablas:
        tabla = tabla.dropna(how="all")
        ids = _mapear_identificadores(tabla.columns)
        if "punto_id" not in ids:
            avisos.append(f"Hoja «{hoja}»: no se encontró la columna del punto de muestreo; "
                          "se omitió la hoja.")
            continue
        largo = "parametro" in ids and "valor" in ids
        formatos[hoja] = "larga" if largo else "ancha"
        for campo, col in ids.items():
            columnas.append({"hoja": hoja, "columna": str(col), "se lee como": campo})

        parametros = []
        if not largo:
            for col in tabla.columns:
                if col in ids.values():
                    continue
                nombre, unidad = separar_unidad(col)
                codigo = parametro_por_nombre(nombre)
                if codigo:
                    parametros.append((col, codigo, unidad))
                    columnas.append({"hoja": hoja, "columna": str(col),
                                     "se lee como": f"{codigo}" + (f" [{unidad}]" if unidad
                                                                  else "")})
                else:
                    ignoradas.append(f"{hoja} · {col}")

        for i, fila in tabla.iterrows():
            nro = int(i) + 2                     # la fila 1 es el encabezado
            crudo_punto = fila[ids["punto_id"]]
            texto_punto = "" if crudo_punto is None else str(crudo_punto).strip()
            if not texto_punto or texto_punto.lower() == "nan":
                continue
            punto = por_id.get(texto_punto.upper()) or por_nombre.get(clave(texto_punto))
            error_fila = None if punto else f"punto no registrado: «{texto_punto}»"
            try:
                fecha = (leer_fecha(fila[ids["fecha"]]) if "fecha" in ids
                         else fecha_campania)
                if fecha is None:
                    raise ValueError("falta la fecha de muestreo")
            except ValueError as e:
                fecha, error_fila = None, error_fila or str(e)
            if error_fila:
                # Un error de fila (punto o fecha) se informa una vez, no una por
                # cada parámetro de la fila.
                filas.append({"hoja": hoja, "fila": nro, "columna": str(ids["punto_id"]),
                              "punto_id": texto_punto, "fecha": fecha, "parametro": None,
                              "calificador": "", "valor": None, "unidad": None, "ld": None,
                              "valor_original": texto_punto, "unidad_original": "",
                              "error": error_fila})
                continue

            if largo:
                celdas = [(ids["valor"], parametro_por_nombre(fila[ids["parametro"]]),
                           fila[ids["unidad"]] if "unidad" in ids else None,
                           str(fila[ids["parametro"]]))]
            else:
                celdas = [(col, cod, uni, None) for col, cod, uni in parametros]

            for col, codigo, unidad, nombre_param in celdas:
                crudo = fila[col]
                base = {"hoja": hoja, "fila": nro, "columna": str(col),
                        "punto_id": punto or texto_punto, "fecha": fecha,
                        "parametro": codigo, "calificador": "", "valor": None,
                        "unidad": None, "ld": None,
                        "valor_original": "" if crudo is None else str(crudo),
                        "unidad_original": "" if unidad is None else str(unidad),
                        "error": None}
                try:
                    leido = leer_valor(crudo)
                except ValueError as e:
                    filas.append({**base, "error": str(e)})
                    continue
                if leido is None:
                    continue                      # celda vacía: no hay dato que cargar
                if codigo is None:
                    filas.append({**base, "error": f"parámetro no reconocido: «{nombre_param}»"})
                    continue
                calificador, valor = leido
                base["calificador"] = calificador
                matriz = matriz_de[punto]
                unidad_txt = unidad
                if unidad_txt is None or str(unidad_txt).strip() == "":
                    unidad_txt = unidad_canonica(codigo, matriz)
                    if codigo not in ("ph",) and (hoja, col) not in sin_unidad_avisada:
                        sin_unidad_avisada.add((hoja, col))
                        avisos.append(f"Hoja «{hoja}», columna «{col}»: sin unidad; "
                                      f"se asumió {unidad_txt}.")
                try:
                    v, u = convertir(valor, unidad_txt, codigo, matriz)
                    ld = None
                    if largo and "ld" in ids:
                        ld_leido = leer_valor(fila[ids["ld"]])
                        if ld_leido and ld_leido[1] is not None:
                            ld, _ = convertir(ld_leido[1], unidad_txt, codigo, matriz)
                    if calificador == "<" and v is not None:
                        ld = v                     # "<0,005": el número es el LD
                except ValueError as e:
                    filas.append({**base, "error": str(e)})
                    continue
                filas.append({**base, "valor": v, "unidad": u, "ld": ld,
                              "matriz": matriz})

    resultados = pd.DataFrame(filas, columns=[
        "hoja", "fila", "columna", "punto_id", "fecha", "parametro", "calificador",
        "valor", "unidad", "ld", "valor_original", "unidad_original", "error", "matriz"])
    if not resultados.empty:
        resultados["matriz"] = resultados["punto_id"].map(matriz_de)
    informe = {
        "formatos": formatos,
        "columnas": columnas,
        "ignoradas": ignoradas,
        "avisos": avisos,
        "leidos": int(resultados["error"].isna().sum()) if not resultados.empty else 0,
        "con_error": int(resultados["error"].notna().sum()) if not resultados.empty else 0,
    }
    return resultados, informe
