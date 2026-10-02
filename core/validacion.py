"""
Validación de resultados: control de carga y semáforo ambiental.

Son dos preguntas distintas y no se mezclan:
  1. ¿El dato está bien cargado?  Punto, fecha, unidad, escala, duplicados.
  2. ¿Qué dice el dato del ambiente?  Nivel guía según el uso del punto y
     rango registrado en la línea de base.

Un dato mal cargado no se interpreta: se corrige primero. Y un valor por
encima del nivel guía no es automáticamente un incumplimiento: en la Puna hay
arsénico y boro naturales por encima de varios niveles guía desde mucho antes
que cualquier proyecto. Por eso el semáforo tiene seis estados y no tres.
"""

from datetime import date

import pandas as pd

from .catalogo import USOS, nivel_guia, nombre_parametro, tolerancia
from .datos import TIPO_BASE

SUPERA = "SUPERA"
ATENCION = "ATENCION"
NO_CONCLUYENTE = "NO_CONCLUYENTE"
FONDO_NATURAL = "FONDO_NATURAL"
CUMPLE = "CUMPLE"
SIN_REFERENCIA = "SIN_REFERENCIA"

# El orden es la prioridad: el color de un punto en el mapa es el de su peor
# resultado. Fondo natural va por debajo de no concluyente porque está
# explicado; no concluyente todavía no.
# Colores de la paleta de estado validada para daltonismo: el par verde-rojo
# del semáforo se confunde en deuteranopía (ΔE 4,1), así que ningún estado se
# comunica solo con color. Cada uno lleva además una forma (en los gráficos) y
# un ícono con su nombre (en tablas y leyendas).
ESTADOS = {
    SUPERA: {"nombre": "Supera nivel guía", "color": "#d03b3b", "forma": "triangle-up",
             "icono": "▲",
             "descripcion": "Supera el nivel guía aplicable al uso del punto y no se "
                            "explica por la línea de base."},
    ATENCION: {"nombre": "Atención", "color": "#fab219", "forma": "diamond", "icono": "◆",
               "descripcion": "Cerca del nivel guía, o fuera del rango registrado en la "
                              "línea de base del punto."},
    NO_CONCLUYENTE: {"nombre": "No concluyente", "color": "#52514e", "forma": "cross",
                     "icono": "✚",
                     "descripcion": "El dato no permite afirmar que cumple: el límite de "
                                    "detección del laboratorio es mayor que el nivel guía, o "
                                    "falta la dureza para elegir el nivel."},
    FONDO_NATURAL: {"nombre": "Fondo natural", "color": "#4a3aa7", "forma": "square",
                    "icono": "■",
                    "descripcion": "Supera el nivel guía, pero dentro del rango natural que "
                                   "el punto ya tenía antes del proyecto."},
    CUMPLE: {"nombre": "Cumple", "color": "#0ca30c", "forma": "circle", "icono": "●",
             "descripcion": "Dentro del nivel guía y del rango de la línea de base."},
    SIN_REFERENCIA: {"nombre": "Sin referencia", "color": "#898781", "forma": "circle",
                     "icono": "○",
                     "descripcion": "Sin nivel guía ni línea de base con qué comparar."},
}
PRIORIDAD = list(ESTADOS)

N_MIN_BASE = 3          # con menos campañas, el rango no alcanza para marcar desvíos
UMBRAL_ATENCION = 0.8   # al 80 % del nivel guía empieza la atención
FACTOR_ESCALA = 50      # más de 50 veces el máximo histórico: casi seguro un error de carga


def hay(x):
    """True si la celda trae algo. En pandas 3 los vacíos de una columna de
    texto llegan como NaN, y NaN es verdadero para Python: `if fila["error"]`
    daría por erróneas todas las filas sanas."""
    if x is None or x == "":
        return False
    try:
        return not pd.isna(x)
    except (TypeError, ValueError):
        return True


def _fmt(x):
    if x is None or pd.isna(x):
        return "—"
    return f"{x:.3g}".replace(".", ",")


# ---------------------------------------------------------- línea de base ---

def linea_base(resultados, campanias):
    """Rango registrado por punto y parámetro en las campañas de línea de base.

    Los no detectados entran con su límite de detección: si en la línea de
    base nunca se detectó un metal, el máximo es ese límite, y una detección
    posterior por encima ya es una novedad.
    """
    ids = [cid for cid, c in campanias.items() if c.get("tipo") == TIPO_BASE]
    base = resultados[resultados["campania_id"].isin(ids) & resultados["valor"].notna()]
    if base.empty:
        return pd.DataFrame(columns=["punto_id", "parametro", "n", "minimo", "maximo",
                                     "mediana"])
    g = base.groupby(["punto_id", "parametro"])["valor"]
    return pd.DataFrame({"n": g.size(), "minimo": g.min(), "maximo": g.max(),
                         "mediana": g.median()}).reset_index()


def rango(fila_base, parametro):
    """Rango de la línea de base ensanchado por la tolerancia del parámetro."""
    tipo, t = tolerancia(parametro)
    if tipo == "abs":
        return fila_base["minimo"] - t, fila_base["maximo"] + t
    return fila_base["minimo"] * (1 - t), fila_base["maximo"] * (1 + t)


# ----------------------------------------------------------------- semáforo ---

def _minimo_por_dureza(guia):
    valores = [v for _, v in guia["por_dureza"] if v is not None]
    return min(valores) if valores else None


def evaluar_uno(valor, calificador, parametro, uso, base=None, dureza=None):
    """Estado de un resultado. Devuelve un dict con estado, motivo y referencias.

    `base` es la fila de la línea de base del punto para ese parámetro (o None).
    """
    nombre = nombre_parametro(parametro)
    guia = nivel_guia(parametro, uso, dureza) if uso else None
    # Con pocas campañas el rango de la línea de base sirve para una sola
    # pregunta: si una superación del nivel guía ya existía antes del proyecto.
    # Para marcar que un valor "se salió" de lo habitual hacen falta al menos
    # N_MIN_BASE campañas; con menos, cualquier variación natural sería alarma.
    r = rango(base, parametro) if base is not None and base["n"] >= 1 else None
    base_firme = r is not None and base["n"] >= N_MIN_BASE
    salida = {"estado": None, "motivo": "", "nivel_guia": None, "norma": "",
              "base_min": r[0] if base_firme else None,
              "base_max": r[1] if base_firme else None,
              "sugerencia": None, "valor_sugerido": None}

    if guia and guia.get("sin_tramo"):
        salida["norma"] = guia["norma"]
        salida["motivo"] = f"Sin nivel guía confirmado para {guia['tramo']}. "
        guia = None
    if guia:
        salida["norma"] = guia["norma"] + (f" ({guia['tramo']})" if guia.get("tramo") else "")
        salida["nivel_guia"] = guia.get("max")

    def fin(estado, motivo):
        salida["estado"] = estado
        salida["motivo"] += motivo
        return salida

    # --- control de escala: ¿el dato está mil veces corrido? -----------------
    if base is not None and valor is not None and calificador != "<" and base["maximo"] > 0:
        if valor > FACTOR_ESCALA * base["maximo"]:
            candidato = valor / 1000
            if r and r[0] / 2 <= candidato <= r[1] * 2:
                salida["sugerencia"] = (
                    f"Parece un valor en µg/L cargado en una columna de mg/L: "
                    f"¿corresponde {_fmt(candidato)} en lugar de {_fmt(valor)}?")
                salida["valor_sugerido"] = candidato
            else:
                salida["sugerencia"] = (
                    f"{_fmt(valor)} es más de {FACTOR_ESCALA} veces el máximo de la línea de "
                    f"base ({_fmt(base['maximo'])}). Verificar con el laboratorio.")
        elif base["minimo"] > 0 and valor < base["minimo"] / FACTOR_ESCALA:
            candidato = valor * 1000
            if r and r[0] / 2 <= candidato <= r[1] * 2:
                salida["sugerencia"] = (
                    f"Parece un valor en mg/L cargado en una columna de µg/L: "
                    f"¿corresponde {_fmt(candidato)} en lugar de {_fmt(valor)}?")
                salida["valor_sugerido"] = candidato

    # --- no detectado ----------------------------------------------------------
    if calificador == "<":
        if guia and guia.get("requiere_dureza"):
            minimo = _minimo_por_dureza(guia)
            if valor is not None and minimo is not None and valor <= minimo:
                return fin(CUMPLE, "No detectado, por debajo de cualquier tramo del nivel "
                                   "guía.")
            return fin(NO_CONCLUYENTE, f"No detectado, pero el nivel guía de {nombre} depende "
                                       "de la dureza y la muestra no la informa.")
        if valor is None:
            if guia and guia.get("max") is not None:
                return fin(NO_CONCLUYENTE, "No detectado, sin límite de detección informado: "
                                           "no se puede afirmar que cumpla.")
            return fin(CUMPLE, "No detectado.")
        if guia and guia.get("max") is not None and valor > guia["max"]:
            return fin(NO_CONCLUYENTE,
                       f"No detectado, pero el límite de detección ({_fmt(valor)}) es mayor que "
                       f"el nivel guía ({_fmt(guia['max'])}): el método del laboratorio no "
                       "alcanza para afirmar que cumple.")
        return fin(CUMPLE, f"No detectado (< {_fmt(valor)}).")

    # --- detectado ---------------------------------------------------------------
    if guia and guia.get("requiere_dureza"):
        minimo = _minimo_por_dureza(guia)
        if minimo is not None and valor <= minimo:
            return fin(CUMPLE, "Por debajo de cualquier tramo del nivel guía.")
        return fin(NO_CONCLUYENTE, f"El nivel guía de {nombre} depende de la dureza y la "
                                   "muestra no la informa.")

    gmax = guia.get("max") if guia else None
    gmin = guia.get("min") if guia else None
    dentro_base = base_firme and r[0] <= valor <= r[1]
    if gmax is not None or gmin is not None:
        alto = gmax is not None and valor > gmax
        bajo = gmin is not None and valor < gmin
        if alto or bajo:
            limite = gmax if alto else gmin
            base_tambien = base is not None and (
                (alto and base["maximo"] > gmax) or (bajo and base["minimo"] < gmin))
            # Fondo natural: la línea de base ya superaba el nivel guía y el
            # valor no está peor que entonces, del lado en que lo supera. Un
            # arsénico más bajo que el de la línea de base no es un impacto.
            no_peor = r is not None and ((alto and valor <= r[1]) or (bajo and valor >= r[0]))
            if base_tambien and no_peor:
                corta = "" if base_firme else (
                    f" La línea de base tiene {int(base['n'])} campaña"
                    f"{'s' if base['n'] != 1 else ''}: conviene confirmarlo con más datos.")
                verbo = "Supera el" if alto else "Está por debajo del"
                return fin(FONDO_NATURAL,
                           f"{verbo} nivel guía ({_fmt(limite)}), pero no está peor que antes "
                           f"del proyecto: la línea de base ya registraba "
                           f"{_fmt(base['maximo'] if alto else base['minimo'])} "
                           f"(con su tolerancia, {_fmt(r[1] if alto else r[0])}).{corta}")
            return fin(SUPERA, f"{'Supera' if alto else 'Por debajo de'} el nivel guía para "
                               f"{USOS.get(guia['uso'], guia['uso']).lower()}: "
                               f"{_fmt(valor)} frente a {_fmt(limite)}.")
        # El 80 % solo tiene sentido en niveles de un solo lado, que parten de
        # cero, y en escalas lineales. En un rango como el del pH (6,5 a 8,5),
        # un 8,1 es el 95 % del máximo y está perfectamente normal; y 56 dBA no
        # es "el 80 %" de 70 dBA en ningún sentido acústico.
        lineal = tolerancia(parametro)[0] == "rel"
        if gmax is not None and gmin is None and lineal and valor >= UMBRAL_ATENCION * gmax:
            return fin(ATENCION, f"Al {valor / gmax:.0%} del nivel guía ({_fmt(gmax)}).")
        if base_firme and not dentro_base:
            return fin(ATENCION, f"Cumple el nivel guía, pero está fuera del rango de la línea "
                                 f"de base ({_fmt(r[0])}–{_fmt(r[1])}).")
        return fin(CUMPLE, "Dentro del nivel guía" +
                   (" y del rango de la línea de base." if base_firme else "."))

    if base_firme:
        if dentro_base:
            return fin(CUMPLE, "Sin nivel guía: dentro del rango de la línea de base.")
        return fin(ATENCION, f"Sin nivel guía: fuera del rango de la línea de base "
                             f"({_fmt(r[0])}–{_fmt(r[1])}).")
    if r is not None:
        n = int(base["n"])
        return fin(SIN_REFERENCIA, f"Sin nivel guía, y la línea de base tiene {n} campaña"
                                   f"{'s' if n != 1 else ''} ({_fmt(base['minimo'])}–"
                                   f"{_fmt(base['maximo'])}): hacen falta al menos "
                                   f"{N_MIN_BASE} para marcar desvíos.")
    return fin(SIN_REFERENCIA, "Sin nivel guía ni línea de base con qué comparar.")


def evaluar(resultados, puntos, base):
    """Agrega a cada resultado válido su estado, motivo y referencias.

    Las filas con error de carga quedan con estado vacío: no se interpretan.
    """
    if resultados.empty:
        return resultados.assign(estado=pd.Series(dtype=object))
    uso_de = dict(zip(puntos["id"], puntos["uso"]))
    base_de = {(b["punto_id"], b["parametro"]): b for b in base.to_dict("records")}
    durezas = resultados[(resultados["parametro"] == "dureza")
                         & (resultados["calificador"] != "<")]
    dureza_de = {(d["punto_id"], d["fecha"]): d["valor"] for d in durezas.to_dict("records")}

    filas = []
    for fila in resultados.to_dict("records"):
        calificador = fila.get("calificador") if hay(fila.get("calificador")) else ""
        if hay(fila.get("error")) or not hay(fila.get("parametro")) or (
                not hay(fila.get("valor")) and calificador != "<"):
            filas.append({**fila, "estado": None})
            continue
        uso = uso_de.get(fila["punto_id"])
        uso = uso if hay(uso) else None
        valor = fila["valor"] if hay(fila["valor"]) else None
        res = evaluar_uno(valor, calificador, fila["parametro"], uso,
                          base_de.get((fila["punto_id"], fila["parametro"])),
                          dureza_de.get((fila["punto_id"], fila["fecha"])))
        filas.append({**fila, **res})
    # Mismo índice que la entrada: las correcciones y los descartes de la
    # interfaz se hacen por índice, y tienen que caer en la fila que se ve.
    return pd.DataFrame(filas, index=resultados.index)


# ------------------------------------------------------------ control de carga ---

def controles(evaluados, hoy=None):
    """Problemas de carga, uno por fila: [{indice, gravedad, problema}].

    `bloqueante` impide presentar la campaña; `advertencia` pide revisión.
    """
    hoy = hoy or date.today()
    problemas = []
    validos = evaluados[~evaluados["error"].map(hay) & evaluados["parametro"].map(hay)]
    duplicados = validos.duplicated(subset=["punto_id", "fecha", "parametro"], keep=False)
    for i, fila in evaluados.iterrows():
        def anotar(gravedad, texto):
            problemas.append({"indice": i, "gravedad": gravedad, "problema": texto})
        if hay(fila.get("error")):
            anotar("bloqueante", fila["error"])
            continue
        if not hay(fila.get("parametro")):
            continue
        if duplicados.get(i, False):
            anotar("bloqueante", "Resultado duplicado: mismo punto, fecha y parámetro.")
        if hay(fila.get("fecha")) and fila["fecha"] > hoy:
            anotar("bloqueante", f"Fecha de muestreo futura ({fila['fecha']:%d/%m/%Y}).")
        valor = fila.get("valor")
        if hay(valor):
            if fila["parametro"] == "ph" and not 0 <= valor <= 14:
                anotar("bloqueante", f"pH fuera de escala ({_fmt(valor)}).")
            elif valor < 0:
                anotar("bloqueante", "Valor negativo.")
        if hay(fila.get("sugerencia")):
            anotar("advertencia", fila["sugerencia"])
    return problemas


# ------------------------------------------------------------------ resúmenes ---

def peor_estado(estados):
    presentes = [e for e in estados if e in ESTADOS]
    return min(presentes, key=PRIORIDAD.index) if presentes else SIN_REFERENCIA


def resumen(evaluados):
    """Cantidad de resultados por estado, en el orden del semáforo."""
    cuenta = evaluados["estado"].value_counts()
    return {e: int(cuenta.get(e, 0)) for e in ESTADOS}


def tendencia_anual(fechas, valores):
    """Pendiente por año de una serie, por mínimos cuadrados. None si no alcanza."""
    pares = [(f, v) for f, v in zip(fechas, valores) if f is not None and pd.notna(v)]
    if len(pares) < 4:
        return None
    x = [f.toordinal() / 365.25 for f, _ in pares]
    y = [v for _, v in pares]
    mx, my = sum(x) / len(x), sum(y) / len(y)
    sxx = sum((a - mx) ** 2 for a in x)
    if sxx == 0:
        return None
    return sum((a - mx) * (b - my) for a, b in zip(x, y)) / sxx
