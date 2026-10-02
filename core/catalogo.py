"""
Catálogo: matrices, parámetros, unidades, usos del recurso y niveles guía.

Todo lo que el sistema compara sale de este archivo. Los niveles guía no son
criterio propio: cada uno lleva la norma y la tabla de donde sale. Una
autoridad que use otras tablas cambia este archivo, no el código que valida.
"""

import unicodedata

# --- Matrices -----------------------------------------------------------------
# Son las que relevan los monitoreos ambientales participativos de la Puna:
# agua superficial y subterránea, salmuera, aire, suelo, costra salina y ruido.
MATRICES = {
    "agua_superficial": "Agua superficial",
    "agua_subterranea": "Agua subterránea",
    "salmuera": "Salmuera",
    "aire": "Aire",
    "suelo": "Suelo",
    "costra_salina": "Costra salina",
    "ruido": "Ruido",
}

# La matriz decide la unidad de las concentraciones: mg/L en líquidos, mg/kg en
# sólidos. Por eso "ppm" no se puede convertir sin saber de qué matriz viene.
LIQUIDAS = {"agua_superficial", "agua_subterranea", "salmuera"}
SOLIDAS = {"suelo", "costra_salina"}

# --- Usos del recurso -----------------------------------------------------------
# Un nivel guía no es único: depende del uso que se protege. El mismo arsénico
# puede cumplir para bebida de ganado y no para vida acuática. Cada punto de
# monitoreo declara su uso, y con eso se elige la tabla que corresponde.
USOS = {
    # Fuente de agua cruda que se potabiliza (Ley 24.585, Anexo IV, Tabla 1)
    # y agua que se toma sin tratar (referencia del CAA, art. 982). Son dos
    # usos distintos: una vertiente de la que una comunidad bebe directo no se
    # puede medir con la vara de una fuente que pasa por una planta.
    "fuente_bebida": "Fuente de agua para bebida humana (con tratamiento)",
    "agua_potable": "Agua para consumo directo (referencia: CAA art. 982)",
    "vida_acuatica": "Protección de la vida acuática (agua dulce)",
    "bebida_ganado": "Bebida de ganado",
    "riego": "Irrigación",
    "agricola": "Suelo de uso agrícola",
    "residencial": "Suelo de uso residencial",
    "industrial": "Suelo de uso industrial",
    "aire_ambiente": "Calidad de aire ambiente",
}

# --- Parámetros -------------------------------------------------------------------
# `unidad` solo está cuando no depende de la matriz (pH, conductividad, nivel,
# material particulado). `alias` son los nombres con que los laboratorios
# encabezan sus columnas, ya normalizados con `clave()`.
PARAMETROS = {
    "ph": {"nombre": "pH", "unidad": "upH",
           "alias": ["ph", "p_h", "ph_campo", "ph_laboratorio", "potencial_hidrogeno"]},
    "conductividad": {"nombre": "Conductividad eléctrica", "unidad": "µS/cm",
                      "alias": ["conductividad", "conductividad_electrica", "ce", "cond",
                                "c_e", "conductividad_25_c"]},
    "sdt": {"nombre": "Sólidos disueltos totales",
            "alias": ["sdt", "tds", "solidos_disueltos_totales", "solidos_disueltos",
                      "residuo_seco"]},
    # La dureza no tiene nivel guía propio, pero decide cuál corresponde a cobre,
    # plomo y cadmio para vida acuática. Sin dureza medida en la misma muestra,
    # esos tres no se pueden evaluar.
    "dureza": {"nombre": "Dureza total (como CaCO₃)",
               "alias": ["dureza", "dureza_total", "dureza_caco3", "dureza_total_caco3",
                         "caco3"]},
    "arsenico": {"nombre": "Arsénico",
                 "alias": ["as", "arsenico", "arsenico_total", "as_total", "as_disuelto",
                           "arsenico_disuelto"]},
    "boro": {"nombre": "Boro", "alias": ["b", "boro", "boro_total"]},
    "litio": {"nombre": "Litio", "alias": ["li", "litio", "litio_total"]},
    "potasio": {"nombre": "Potasio", "alias": ["k", "potasio"]},
    "magnesio": {"nombre": "Magnesio", "alias": ["mg", "magnesio"]},
    "plomo": {"nombre": "Plomo", "alias": ["pb", "plomo", "plomo_total"]},
    "cadmio": {"nombre": "Cadmio", "alias": ["cd", "cadmio", "cadmio_total"]},
    "cromo": {"nombre": "Cromo total", "alias": ["cr", "cromo", "cromo_total", "cr_total"]},
    "cobre": {"nombre": "Cobre", "alias": ["cu", "cobre", "cobre_total"]},
    "zinc": {"nombre": "Zinc", "alias": ["zn", "zinc", "cinc", "zinc_total"]},
    "mercurio": {"nombre": "Mercurio", "alias": ["hg", "mercurio", "mercurio_total"]},
    "hierro": {"nombre": "Hierro", "alias": ["fe", "hierro", "hierro_total"]},
    "manganeso": {"nombre": "Manganeso", "alias": ["mn", "manganeso"]},
    "sulfatos": {"nombre": "Sulfatos", "alias": ["sulfatos", "sulfato", "so4"]},
    "cloruros": {"nombre": "Cloruros", "alias": ["cloruros", "cloruro", "cl"]},
    "nitratos": {"nombre": "Nitratos", "alias": ["nitratos", "nitrato", "no3"]},
    "cianuro": {"nombre": "Cianuro", "alias": ["cianuro", "cianuros", "cn", "cianuro_total",
                                               "cn_total"]},
    "nivel_freatico": {"nombre": "Profundidad del nivel freático", "unidad": "m",
                       "alias": ["nivel_freatico", "nivel_estatico", "profundidad_nivel",
                                 "nivel_agua", "prof_nivel", "nf"]},
    "pm10": {"nombre": "Material particulado PM10 (24 h)", "unidad": "µg/m³",
             "alias": ["pm10", "mp10", "pm_10", "material_particulado_pm10",
                       "material_particulado_10"]},
    "nivel_sonoro": {"nombre": "Nivel sonoro continuo equivalente (LAeq)", "unidad": "dBA",
                     "alias": ["nivel_sonoro", "laeq", "leq", "ruido", "nps",
                               "nivel_presion_sonora"]},
}


def clave(texto):
    """Normaliza un encabezado: sin acentos, sin mayúsculas, sin separadores.

    "Arsénico total" y "arsenico-total" son el mismo encabezado. Sacar los
    conectores evita tener que enumerar cada variante como sinónimo.
    """
    txt = unicodedata.normalize("NFKD", str(texto))
    txt = "".join(c for c in txt if not unicodedata.combining(c))
    txt = txt.strip().lower()
    for viejo in (" ", "-", ".", "/", "°", "º"):
        txt = txt.replace(viejo, "_")
    while "__" in txt:
        txt = txt.replace("__", "_")
    partes = [p for p in txt.split("_") if p not in ("de", "del", "la", "el", "en", "a")]
    return "_".join(partes).strip("_") or txt


# Índice inverso alias -> parámetro, armado una sola vez.
_POR_ALIAS = {a: cod for cod, p in PARAMETROS.items() for a in p["alias"]}


def parametro_por_nombre(nombre):
    """Código interno del parámetro para un encabezado, o None si no se reconoce.

    Si el encabezado completo no es un sinónimo conocido, se le van sacando
    palabras del final: "PM10 24 h" es PM10 y "Boro soluble" es boro, sin tener
    que enumerar cada adorno que le agrega un laboratorio.
    """
    partes = clave(nombre).split("_")
    while partes:
        codigo = _POR_ALIAS.get("_".join(partes))
        if codigo:
            return codigo
        partes.pop()
    return None


def nombre_parametro(codigo):
    return PARAMETROS.get(codigo, {}).get("nombre", codigo)


def unidad_canonica(parametro, matriz):
    """Unidad en la que el sistema guarda y compara cada parámetro."""
    fija = PARAMETROS.get(parametro, {}).get("unidad")
    if fija:
        return fija
    if matriz in LIQUIDAS:
        return "mg/L"
    if matriz in SOLIDAS:
        return "mg/kg"
    return "µg/m³"


# --- Unidades -------------------------------------------------------------------
# unidad normalizada -> (magnitud, factor hasta la unidad canónica de esa magnitud)
# Las canónicas son mg/L (líquidos), mg/kg (sólidos), µg/m³ (aire), µS/cm
# (conductividad), upH y metros.
_UNIDADES = {
    "mg/l": ("liquido", 1.0), "ug/l": ("liquido", 1e-3), "g/l": ("liquido", 1e3),
    "ng/l": ("liquido", 1e-6),
    "mg/kg": ("solido", 1.0), "ug/kg": ("solido", 1e-3), "g/kg": ("solido", 1e3),
    "%": ("solido", 1e4),
    "ug/m3": ("aire", 1.0), "mg/m3": ("aire", 1e3),
    "us/cm": ("conductividad", 1.0), "ms/cm": ("conductividad", 1e3),
    "ms/m": ("conductividad", 10.0),
    "uph": ("ph", 1.0), "unidadesph": ("ph", 1.0), "unidadesdeph": ("ph", 1.0),
    "unidadph": ("ph", 1.0),
    "m": ("longitud", 1.0), "cm": ("longitud", 0.01), "mbbp": ("longitud", 1.0),
    "mbnt": ("longitud", 1.0),
    "dba": ("sonido", 1.0), "db(a)": ("sonido", 1.0), "db": ("sonido", 1.0),
}

# ppm y ppb dependen de la matriz: en agua son mg/L y µg/L; en suelo, mg/kg y µg/kg.
_AMBIGUAS = {"ppm": 1.0, "ppb": 1e-3}

_MAGNITUD_CANONICA = {
    "mg/L": "liquido", "mg/kg": "solido", "µg/m³": "aire", "µS/cm": "conductividad",
    "upH": "ph", "m": "longitud", "dBA": "sonido",
}


def normalizar_unidad(texto):
    """'µg/L', 'ug/l', 'μg / L' y 'ug/L' son la misma unidad."""
    txt = str(texto or "").strip().lower()
    for viejo, nuevo in (("µ", "u"), ("μ", "u"), ("³", "3"), ("₃", "3"), (" ", "")):
        txt = txt.replace(viejo, nuevo)
    # "mg/L CaCO3" es mg/L: la especie química acompaña la unidad, no la cambia.
    for especie in ("comocaco3", "caco3"):
        txt = txt.replace(especie, "")
    return txt


def unidad_conocida(texto):
    """True si el texto es una unidad que el sistema sabe convertir."""
    u = normalizar_unidad(texto)
    return bool(u) and (u in _UNIDADES or u in _AMBIGUAS)


def convertir(valor, unidad, parametro, matriz):
    """Lleva un valor a la unidad canónica de su parámetro en su matriz.

    Devuelve (valor_convertido, unidad_canonica). Si la unidad no corresponde a
    la matriz (mg/kg en un agua, por ejemplo) levanta ValueError: convertir en
    silencio un dato mal rotulado es peor que rechazarlo.
    """
    destino = unidad_canonica(parametro, matriz)
    u = normalizar_unidad(unidad)
    if not u:
        raise ValueError("sin unidad")
    if u in _AMBIGUAS:
        if matriz in LIQUIDAS or matriz in SOLIDAS:
            factor = _AMBIGUAS[u]
            magnitud = "liquido" if matriz in LIQUIDAS else "solido"
        else:
            raise ValueError(f"'{unidad}' no se puede usar en {MATRICES.get(matriz, matriz)}")
    elif u in _UNIDADES:
        magnitud, factor = _UNIDADES[u]
    else:
        raise ValueError(f"unidad desconocida: '{unidad}'")
    if magnitud != _MAGNITUD_CANONICA[destino]:
        raise ValueError(
            f"'{unidad}' no corresponde a {nombre_parametro(parametro)} en "
            f"{MATRICES.get(matriz, matriz).lower()} (se espera {destino})"
        )
    return (None if valor is None else valor * factor), destino


# --- Tolerancia de la línea de base ----------------------------------------------
# Cuánto puede apartarse un valor del rango registrado en la línea de base antes
# de marcarlo. Para concentraciones es relativa; para pH, niveles y ruido tiene
# que ser absoluta: un 20 % de un nivel freático a 8 m son 1,6 m, y un descenso
# de ese tamaño es justamente lo que hay que ver.
TOLERANCIA_BASE = {
    "ph": ("abs", 0.5),
    "nivel_freatico": ("abs", 0.5),
    "nivel_sonoro": ("abs", 3.0),
}
TOLERANCIA_POR_DEFECTO = ("rel", 0.20)


def tolerancia(parametro):
    return TOLERANCIA_BASE.get(parametro, TOLERANCIA_POR_DEFECTO)


# --- Niveles guía ------------------------------------------------------------------
# Relevados de fuentes públicas secundarias (ver INVESTIGACION.md, sección 4).
# `estado` dice qué tan firme es cada valor:
#   "confirmado"  la cifra y la tabla aparecen en la fuente citada;
#   "a verificar" la cifra aparece, pero la tabla o el contexto son dudosos.
# Antes de usar el sistema con datos reales, todos se cotejan contra el texto
# del Boletín Oficial: un nivel guía mal cargado es un semáforo mal pintado.
#
# Lo que no se encontró no se inventa. Sin nivel guía, el valor se compara solo
# contra la línea de base del punto. Es el caso del PM10: no apareció una cifra
# argentina confirmada, y poner la de otro país sería decidir por la autoridad.

LEY_24585_T1 = "Ley 24.585, Anexo IV, Tabla 1"
LEY_24585_T2 = "Ley 24.585, Anexo IV, Tabla 2"
LEY_24585_T5 = "Ley 24.585, Anexo IV, Tabla 5"
LEY_24585_T6 = "Ley 24.585, Anexo IV, Tabla 6"
DEC_831_T1 = "Dec. 831/93, Anexo II, Tabla 1"
DEC_831_T2 = "Dec. 831/93, Anexo II, Tabla 2"
DEC_831_T5 = "Dec. 831/93, Anexo II, Tabla 5"
DEC_831_T9 = "Dec. 831/93, Anexo II, Tabla 9"
CAA_982 = "Código Alimentario Argentino, art. 982"


def _g(parametro, uso, maximo=None, minimo=None, norma="", estado="confirmado",
       nota="", por_dureza=None):
    return {"parametro": parametro, "uso": uso, "max": maximo, "min": minimo,
            "norma": norma, "estado": estado, "nota": nota, "por_dureza": por_dureza}


NIVELES_GUIA = [
    # Fuente de agua para bebida humana con tratamiento convencional (mg/L).
    _g("ph", "fuente_bebida", 8.5, 6.5, LEY_24585_T1),
    _g("sdt", "fuente_bebida", 1000, norma=LEY_24585_T1),
    _g("arsenico", "fuente_bebida", 0.05, norma=f"{LEY_24585_T1} · {DEC_831_T1}"),
    _g("cadmio", "fuente_bebida", 0.005, norma=f"{LEY_24585_T1} · {DEC_831_T1}"),
    _g("cobre", "fuente_bebida", 1.0, norma=LEY_24585_T1),
    _g("plomo", "fuente_bebida", 0.05, norma=f"{LEY_24585_T1} · {DEC_831_T1}"),
    _g("zinc", "fuente_bebida", 5.0, norma=LEY_24585_T1),
    _g("mercurio", "fuente_bebida", 0.001, norma=DEC_831_T1, estado="a verificar",
       nota="Confirmado en el Dec. 831/93; su presencia en la Ley 24.585 es inferida."),
    _g("cianuro", "fuente_bebida", 0.1, norma=DEC_831_T1, estado="a verificar",
       nota="Confirmado en el Dec. 831/93; su presencia en la Ley 24.585 es inferida."),

    # Agua que se consume sin tratar: se toma como referencia el agua potable.
    _g("arsenico", "agua_potable", 0.01, norma=CAA_982,
       nota="La autoridad sanitaria puede admitir hasta 0,05 mg/L en zonas con "
            "arsénico natural elevado."),
    _g("plomo", "agua_potable", 0.05, norma=CAA_982),
    _g("cadmio", "agua_potable", 0.005, norma=CAA_982),
    _g("mercurio", "agua_potable", 0.001, norma=CAA_982),
    _g("cianuro", "agua_potable", 0.10, norma=CAA_982),
    _g("zinc", "agua_potable", 5.0, norma=CAA_982),
    _g("cromo", "agua_potable", 0.05, norma=CAA_982),
    _g("nitratos", "agua_potable", 45, norma=CAA_982),
    _g("sulfatos", "agua_potable", 400, norma=CAA_982),
    _g("cloruros", "agua_potable", 350, norma=CAA_982),
    _g("sdt", "agua_potable", 1500, norma=CAA_982),
    _g("hierro", "agua_potable", 0.30, norma=CAA_982),
    _g("manganeso", "agua_potable", 0.10, norma=CAA_982),
    _g("boro", "agua_potable", 0.5, norma=CAA_982),
    _g("cobre", "agua_potable", 1.0, norma=CAA_982, estado="a verificar"),
    _g("ph", "agua_potable", 8.5, 6.5, CAA_982, estado="a verificar"),

    # Protección de la vida acuática, agua dulce superficial (mg/L).
    _g("arsenico", "vida_acuatica", 0.05, norma=f"{LEY_24585_T2} · {DEC_831_T2}"),
    _g("zinc", "vida_acuatica", 0.03, norma=DEC_831_T2),
    _g("boro", "vida_acuatica", 0.75, norma=DEC_831_T2),
    _g("cromo", "vida_acuatica", 0.002, norma=DEC_831_T2),
    # Tramos de dureza en mg/L de CaCO3: hasta 60, hasta 120, hasta 180 y más.
    _g("cobre", "vida_acuatica", norma=DEC_831_T2,
       por_dureza=[(60, 0.002), (120, 0.002), (180, 0.003), (None, 0.004)]),
    _g("plomo", "vida_acuatica", norma=DEC_831_T2, estado="a verificar",
       nota="No se obtuvo el valor para dureza mayor a 180 mg/L CaCO₃.",
       por_dureza=[(60, 0.001), (120, 0.002), (180, 0.004), (None, None)]),
    _g("cadmio", "vida_acuatica", norma=DEC_831_T2, estado="a verificar",
       nota="Valores confirmados; la tabla de origen es inferida.",
       por_dureza=[(60, 0.0002), (120, 0.0008), (180, 0.0013), (None, 0.0018)]),

    # Irrigación y bebida de ganado (mg/L).
    _g("arsenico", "riego", 0.1, norma=f"{LEY_24585_T5} · {DEC_831_T5}"),
    _g("boro", "riego", 0.5, norma=f"{LEY_24585_T5} · {DEC_831_T5}"),
    _g("litio", "riego", 2.5, norma=DEC_831_T5),
    _g("arsenico", "bebida_ganado", 0.5, norma=LEY_24585_T6, estado="a verificar"),
    _g("boro", "bebida_ganado", 5.0, norma=LEY_24585_T6, estado="a verificar"),

    # Suelos (mg/kg de peso seco). Solo el arsénico apareció confirmado.
    _g("arsenico", "agricola", 20, norma=DEC_831_T9),
    _g("arsenico", "residencial", 30, norma=DEC_831_T9),
    _g("arsenico", "industrial", 50, norma=DEC_831_T9),
]


def _tramo(dureza, tramos):
    for tope, valor in tramos:
        if tope is None or dureza <= tope:
            return tope, valor
    return None, None


def nivel_guia(parametro, uso, dureza=None):
    """Nivel guía aplicable a un parámetro según el uso del punto.

    Devuelve None si no hay nivel guía para ese par. Si el nivel depende de la
    dureza y no se la informó, devuelve el registro con `requiere_dureza=True`:
    no se puede elegir el tramo, y adivinarlo sería inventar el límite.
    """
    for n in NIVELES_GUIA:
        if n["parametro"] != parametro or n["uso"] != uso:
            continue
        if not n["por_dureza"]:
            return n
        if dureza is None:
            return {**n, "requiere_dureza": True}
        tope, valor = _tramo(dureza, n["por_dureza"])
        tramo = f"dureza ≤ {tope:g} mg/L CaCO₃" if tope else "dureza > 180 mg/L CaCO₃"
        if valor is None:
            return {**n, "sin_tramo": True, "tramo": tramo}
        return {**n, "max": valor, "tramo": tramo}
    return None


def niveles_del_parametro(parametro):
    """Todos los niveles guía de un parámetro, para mostrar contra qué se mide."""
    return [n for n in NIVELES_GUIA if n["parametro"] == parametro]
