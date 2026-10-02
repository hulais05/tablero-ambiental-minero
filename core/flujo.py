"""
Flujo de una campaña: quién puede hacer qué, y en qué orden.

Replica el circuito del MAIM: la empresa carga y presenta, la autoridad revisa
y solo lo que la autoridad aprueba se publica. Ningún cambio de estado ocurre
sin una persona con nombre detrás, y cada paso queda en el historial con
fecha y hora. Sin eso, "la autoridad controla" es una frase, no un control.
"""

from datetime import datetime

from .catalogo import nombre_parametro
from .validacion import SUPERA, hay

BORRADOR = "BORRADOR"
PRESENTADA = "PRESENTADA"
OBSERVADA = "OBSERVADA"
APROBADA = "APROBADA"

ESTADOS = {
    BORRADOR: "Borrador · la empresa está cargando",
    PRESENTADA: "Presentada · espera la revisión de la autoridad",
    OBSERVADA: "Observada · la autoridad pidió correcciones",
    APROBADA: "Aprobada · publicada",
}

# (desde, hasta) -> (rol que puede hacerlo, cómo queda escrito en el historial)
TRANSICIONES = {
    (BORRADOR, PRESENTADA): ("empresa", "Presentó la campaña"),
    (OBSERVADA, PRESENTADA): ("empresa", "Volvió a presentar con correcciones"),
    (PRESENTADA, APROBADA): ("autoridad", "Aprobó y publicó"),
    (PRESENTADA, OBSERVADA): ("autoridad", "Observó la campaña"),
}


def transicionar(campania, hasta, actor, rol, comentario="", ahora=None):
    """Cambia el estado de la campaña y lo deja asentado. Valida rol y firma."""
    desde = campania["estado"]
    regla = TRANSICIONES.get((desde, hasta))
    if regla is None:
        raise ValueError(f"Una campaña {ESTADOS[desde].split(' ·')[0].lower()} no puede "
                         f"pasar a {ESTADOS[hasta].split(' ·')[0].lower()}.")
    rol_habilitado, accion = regla
    if rol != rol_habilitado:
        raise PermissionError(f"Ese paso lo da la {rol_habilitado}, no la {rol}.")
    if not actor or not actor.strip():
        raise ValueError("Falta el nombre de quien firma el paso.")
    if hasta == OBSERVADA and not comentario.strip():
        raise ValueError("Una observación tiene que decir qué hay que corregir.")
    campania["estado"] = hasta
    campania["historial"].append({
        "fecha_hora": ahora or datetime.now(), "actor": actor.strip(), "rol": rol,
        "accion": accion, "estado": hasta, "comentario": comentario.strip(),
    })
    return campania


def faltantes_para_presentar(evaluados, problemas, justificaciones):
    """Lo que impide presentar. Lista vacía: la campaña se puede presentar.

    Dos reglas: ningún error de carga sin resolver, y toda superación del
    nivel guía llega explicada. Una excedencia sin explicación obliga a la
    autoridad a pedirla, y eso es una vuelta entera del expediente.
    """
    faltan = []
    validos = evaluados[evaluados["estado"].map(hay)] if not evaluados.empty else evaluados
    if validos.empty:
        faltan.append("La campaña no tiene resultados válidos.")
    bloqueantes = [p for p in problemas if p["gravedad"] == "bloqueante"]
    if bloqueantes:
        faltan.append(f"{len(bloqueantes)} error(es) de carga sin resolver.")
    if not validos.empty:
        superan = validos[validos["estado"] == SUPERA]
        sin_nota = [f"{r.punto_id} · {nombre_parametro(r.parametro)}"
                    for r in superan.itertuples()
                    if not justificaciones.get(f"{r.punto_id}|{r.parametro}", "").strip()]
        if sin_nota:
            faltan.append("Falta justificar la superación del nivel guía en: "
                          + ", ".join(sin_nota) + ".")
    return faltan


def publicadas(campanias):
    """Ids de las campañas que el público puede ver: solo las aprobadas."""
    return {cid for cid, c in campanias.items() if c["estado"] == APROBADA}
