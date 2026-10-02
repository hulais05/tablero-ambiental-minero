"""
Tablero Ambiental Minero — prototipo.

Monitoreos ambientales de la minería: de la planilla del laboratorio al dato
público, y de ahí a cada canal oficial (TAD/GDE, MAIM, SIMSa, CyMA, datos
abiertos). Replica el circuito del MAIM de Jujuy —la empresa carga, la
autoridad controla, la ciudadanía consulta— pensado para el lado de la
empresa.

Ejecutar, parado en esta carpeta:  streamlit run app.py
"""

import copy
import functools
import hashlib
import json
from datetime import date, timedelta

import altair as alt
import pandas as pd
import pydeck as pdk
import streamlit as st

from core.catalogo import MATRICES, PARAMETROS, USOS, nombre_parametro
from core.conectores import (EXPORTADORES, Envio, cargar_perfiles, contenido, enviar,
                             nombre_archivo, solicitud_api)
from core.datos import (TIPO_BASE, interpretar, leer_archivo, libro_laboratorio,
                        nueva_campania)
from core.escenario import cargar as cargar_escenario
from core.flujo import (APROBADA, OBSERVADA, PRESENTADA, faltantes_para_presentar,
                        publicadas, transicionar)
from core.flujo import ESTADOS as ESTADOS_CAMPANIA
from core.validacion import (ATENCION, CUMPLE, ESTADOS, NO_CONCLUYENTE, PRIORIDAD, SUPERA,
                             controles, evaluar, hay, linea_base, peor_estado, rango,
                             tendencia_anual)

st.set_page_config(page_title="Tablero Ambiental Minero", page_icon="⛰️", layout="wide")

BG, CARD, BORDE, TXT, MUT, ACENTO = (
    "#F6F8FB", "#FFFFFF", "#E2E8F0", "#0F172A", "#64748B", "#155E75")
# El lema vive en una constante: aparece en la barra lateral, el encabezado y
# el pie, y tiene que cambiar en un solo lugar.
LEMA = "Del laboratorio al dato público."
REPO = "https://github.com/hulais05/tablero-ambiental-minero/blob/main"

st.markdown(f"""
<style>
  .stApp {{ background: {BG}; }}
  section[data-testid="stSidebar"] {{ background: {CARD}; border-right: 1px solid {BORDE}; }}
  .brand {{ font-size: 28px; font-weight: 700; color: {TXT}; line-height: 1.1; }}
  .brand span {{ color: {ACENTO}; }}
  .lema {{ color: {ACENTO}; font-size: 15px; font-weight: 600; letter-spacing: .02em;
           margin-top: 4px; }}
  section[data-testid="stSidebar"] .lema {{ font-size: 13px; }}
  .sub {{ color: {MUT}; font-size: 13px; }}
  /* Franja de métricas: número grande arriba, etiqueta chica abajo, todo en
     una sola caja dividida. */
  .franja {{ display: flex; background: {CARD}; border: 1px solid {BORDE};
             border-radius: 10px; overflow: hidden; flex-wrap: wrap; margin: 6px 0 10px; }}
  .franja .m {{ flex: 1 1 140px; padding: 12px 16px; border-right: 1px solid {BORDE}; }}
  .franja .m:last-child {{ border-right: none; }}
  .franja .n {{ font-size: clamp(20px, 2vw, 28px); font-weight: 600; letter-spacing: -.02em;
                line-height: 1.1; color: {TXT}; }}
  .franja .t {{ color: {MUT}; font-size: 12px; margin-top: 4px; }}
  /* Estado: el color va en el punto, nunca en el texto. El ícono repite el
     estado en forma, para quien no distingue el verde del rojo. */
  .chip {{ display: inline-flex; align-items: center; gap: 6px; padding: 3px 10px;
           border: 1px solid {BORDE}; border-radius: 999px; background: {CARD};
           font-size: 12px; color: {TXT}; margin: 0 6px 6px 0; white-space: nowrap; }}
  /* El ícono es la marca: lleva el color y la forma a la vez. El contorno
     tenue lo mantiene visible cuando el color es claro (el ámbar). */
  .chip .ico {{ font-size: 13px; line-height: 1; text-shadow: 0 0 1px rgba(15,23,42,.55); }}
  .chip .c {{ color: {MUT}; }}
  /* Recorrido de etapas: cada una dice quién interviene. La revisión de la
     autoridad va resaltada: es el control que el sistema no reemplaza. */
  .pipe {{ display: flex; gap: 8px; flex-wrap: wrap; margin: 4px 0 6px; }}
  .paso {{ flex: 1 1 0; min-width: min-content; background: {CARD};
           border: 1px solid {BORDE}; border-radius: 10px; padding: 9px 11px; }}
  .paso .n {{ color: {MUT}; font-size: 10px; letter-spacing: .1em; }}
  .paso .q {{ font-size: clamp(12px, .9vw, 14px); font-weight: 650; line-height: 1.2;
              margin: 2px 0 3px; color: {TXT}; }}
  .paso .w {{ color: {MUT}; font-size: 11px; }}
  .paso.humano {{ border: 1.5px solid {ACENTO}; background: #ECFEFF; }}
  .paso.humano .q, .paso.humano .w {{ color: {ACENTO}; }}
  .canal-tipo {{ display: inline-block; padding: 2px 9px; border-radius: 999px;
                 font-size: 11px; letter-spacing: .04em; border: 1px solid {BORDE};
                 color: {TXT}; background: #F1F5F9; margin-right: 6px; }}
  .pie {{ text-align: center; padding: 28px 12px 36px; color: {MUT}; font-size: 12px; }}
  .pie .nom {{ font-size: 16px; font-weight: 700; color: {TXT}; }}
  .pie .nom span {{ color: {ACENTO}; }}
  .pie .norma {{ display: inline-block; margin: 6px 4px 0; padding: 3px 10px;
                 border: 1px solid {BORDE}; border-radius: 999px; background: {CARD};
                 font-size: 11px; white-space: nowrap; }}
</style>
""", unsafe_allow_html=True)


# ------------------------------------------------------------------ apoyo ---

def fmt(x, decimales=None):
    """Número con coma decimal y punto de miles, como se lee acá."""
    if not hay(x):
        return "—"
    if decimales is None:
        txt = f"{x:,.3g}" if abs(x) < 1000 else f"{x:,.0f}"
    else:
        txt = f"{x:,.{decimales}f}"
    return txt.replace(",", "§").replace(".", ",").replace("§", ".")


def valor_txt(calificador, valor):
    if not hay(valor):
        return "no detectado"
    return f"< {fmt(valor)}" if calificador == "<" else fmt(valor)


def etiqueta(estado):
    """Estado como texto: ícono y nombre, para tablas y desplegables."""
    if not hay(estado):
        return "—"
    return f"{ESTADOS[estado]['icono']} {ESTADOS[estado]['nombre']}"


def chip(estado, cantidad=None):
    d = ESTADOS[estado]
    extra = f' <span class="c">{cantidad}</span>' if cantidad is not None else ""
    return (f'<span class="chip" title="{d["descripcion"]}"><span class="ico" '
            f'style="color:{d["color"]}">{d["icono"]}</span>{d["nombre"]}{extra}</span>')


def leyenda(estados, cuentas=None):
    st.markdown("".join(chip(e, (cuentas or {}).get(e)) for e in PRIORIDAD if e in estados),
                unsafe_allow_html=True)


def franja(metricas):
    st.markdown('<div class="franja">' + "".join(
        f'<div class="m"><div class="n">{n}</div><div class="t">{t}</div></div>'
        for n, t in metricas) + "</div>", unsafe_allow_html=True)


def orden_parametro(codigo):
    lista = list(PARAMETROS)
    return lista.index(codigo) if codigo in lista else len(lista)


def gravedad(estado):
    return PRIORIDAD.index(estado) if estado in PRIORIDAD else len(PRIORIDAD)


def zoom_para(lats, lons, alto_px=420, ancho_px=900):
    """Zoom que encuadra todos los puntos con un margen, sin depender del mapa base."""
    import math
    alto = max(max(lats) - min(lats), 0.005) * 1.6
    ancho = max(max(lons) - min(lons), 0.005) * 1.6
    z_ancho = math.log2(360 * ancho_px / 256 / ancho)
    z_alto = math.log2(180 * alto_px / 256 / alto)
    return max(4.0, min(13.0, min(z_ancho, z_alto)))


def _rgb(hex_color):
    return [int(hex_color[i:i + 2], 16) for i in (1, 3, 5)]


def asegurar_opcion(clave, opciones, defecto=None):
    """Si el valor guardado de un widget ya no es una opción válida, lo repone.

    Pasa al cambiar un filtro de arriba: el desplegable de abajo cambia de
    opciones y el valor viejo queda colgado.
    """
    if st.session_state.get(clave) not in opciones:
        st.session_state[clave] = defecto if defecto in opciones else opciones[0]


# --------------------------------------------------------------- estado ---

def iniciar(forzar=False):
    if forzar or "esc" not in st.session_state:
        esc = cargar_escenario()
        st.session_state.esc = esc
        st.session_state.campanias = copy.deepcopy(esc["campanias"])
        st.session_state.resultados = esc["resultados"].copy()
        st.session_state.version = 0
        st.session_state.borrador = None
        st.session_state.usar_ejemplo = False
        # La planilla de ejemplo se arma una sola vez: el XLSX lleva la hora de
        # creación adentro, y regenerarla en cada recarga la volvería "otro
        # archivo" y borraría las correcciones ya hechas.
        st.session_state.ejemplo = libro_laboratorio(esc)
        st.session_state.aviso = None
        st.session_state.pop("eval", None)


def evaluacion():
    """Línea de base y semáforo de todo el historial, recalculados solo si cambió algo."""
    v = st.session_state.version
    cache = st.session_state.get("eval")
    if cache and cache[0] == v:
        return cache[1], cache[2]
    base = linea_base(st.session_state.resultados, st.session_state.campanias)
    ev = evaluar(st.session_state.resultados, st.session_state.esc["puntos"], base)
    st.session_state.eval = (v, base, ev)
    return base, ev


iniciar()
esc = st.session_state.esc
puntos = esc["puntos"]
META = esc["meta"]
PROYECTOS = esc["proyectos"].to_dict("records")
proyectos = {p["id"]: p for p in PROYECTOS}
nombre_punto = dict(zip(puntos["id"], puntos["nombre"]))
perfiles = cargar_perfiles()
campanias = st.session_state.campanias


def nombre_proyecto(pid):
    p = proyectos[pid]
    return f"{p['nombre']} · {p['empresa']} · {p['provincia']}"


def envio(campania_id, ev, perfil=None, canal=None):
    """Lo que necesita un conector para exportar una campaña."""
    c = campanias[campania_id]
    evc = ev[(ev["campania_id"] == campania_id) & ev["estado"].map(hay)]
    return Envio(campania=c, proyecto=proyectos[c["proyecto_id"]],
                 puntos=puntos[puntos["id"].isin(evc["punto_id"])], evaluados=evc,
                 perfil=perfil, canal=canal)


# ---------------------------------------------------------------- gráfico ---

LOCALE = {
    "number": {"decimal": ",", "thousands": ".", "grouping": [3], "currency": ["$", ""]},
    "time": {"dateTime": "%A, %e de %B de %Y, %X", "date": "%d/%m/%Y", "time": "%H:%M:%S",
             "periods": ["AM", "PM"],
             "days": ["domingo", "lunes", "martes", "miércoles", "jueves", "viernes", "sábado"],
             "shortDays": ["dom", "lun", "mar", "mié", "jue", "vie", "sáb"],
             "months": ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio",
                        "agosto", "septiembre", "octubre", "noviembre", "diciembre"],
             "shortMonths": ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep",
                             "oct", "nov", "dic"]},
}


def grafico_serie(serie, titulo_y, guia, rango_base, fin_base):
    """Serie de un parámetro en un punto: valores, nivel guía y línea de base.

    Una sola línea en tinta neutra; el estado de cada muestra va en el color Y
    en la forma del marcador. El nivel guía es la única línea punteada: es un
    umbral, no una grilla. La línea de base es una franja tenue, no un bloque.
    """
    nombres = [ESTADOS[e]["nombre"] for e in PRIORIDAD]
    presentes = [ESTADOS[e]["nombre"] for e in PRIORIDAD if e in set(serie["estado"])]
    datos = serie.assign(
        fecha=pd.to_datetime(serie["fecha"]),
        estado_nombre=serie["estado"].map(lambda e: ESTADOS[e]["nombre"]),
        valor_texto=[valor_txt(c, v) for c, v in zip(serie["calificador"], serie["valor"])],
    )
    eje_x = alt.X("fecha:T", title=None,
                  axis=alt.Axis(format="%b %Y", labelAngle=0, grid=False, tickCount=6))
    eje_y = alt.Y("valor:Q", title=titulo_y, scale=alt.Scale(zero=False),
                  axis=alt.Axis(gridColor="#EEF0F3"))
    capas = []
    if rango_base:
        capas.append(alt.Chart(pd.DataFrame({"y": [rango_base[0]], "y2": [rango_base[1]]}))
                     .mark_rect(color="#64748B", opacity=0.10)
                     .encode(y="y:Q", y2="y2:Q"))
    if fin_base is not None:
        corte = pd.DataFrame({"x": [pd.Timestamp(fin_base)],
                              "t": ["fin de la línea de base"]})
        capas.append(alt.Chart(corte).mark_rule(color="#CBD5E1", strokeWidth=1)
                     .encode(x="x:T"))
        capas.append(alt.Chart(corte).mark_text(align="left", dx=4, dy=-4, baseline="top",
                                                color=MUT, fontSize=11)
                     .encode(x="x:T", y=alt.value(0), text="t:N"))
    capas.append(alt.Chart(datos).mark_line(strokeWidth=2, color="#52514e",
                                            strokeJoin="round", strokeCap="round")
                 .encode(x=eje_x, y=eje_y))
    capas.append(
        alt.Chart(datos).mark_point(filled=True, size=120, opacity=1, stroke="white",
                                    strokeWidth=2)
        .encode(
            x=eje_x, y=eje_y,
            color=alt.Color("estado_nombre:N",
                            scale=alt.Scale(domain=nombres,
                                            range=[ESTADOS[e]["color"] for e in PRIORIDAD]),
                            legend=alt.Legend(title=None, orient="bottom", values=presentes)),
            shape=alt.Shape("estado_nombre:N",
                            scale=alt.Scale(domain=nombres,
                                            range=[ESTADOS[e]["forma"] for e in PRIORIDAD]),
                            legend=alt.Legend(title=None, orient="bottom", values=presentes)),
            tooltip=[alt.Tooltip("valor_texto:N", title="Valor"),
                     alt.Tooltip("fecha:T", title="Fecha", format="%d/%m/%Y"),
                     alt.Tooltip("estado_nombre:N", title="Estado"),
                     alt.Tooltip("motivo:N", title="Por qué")]))
    if hay(guia):
        regla = pd.DataFrame({"y": [guia], "t": [f"nivel guía {fmt(guia)}"]})
        capas.append(alt.Chart(regla).mark_rule(color="#d03b3b", strokeDash=[6, 4],
                                                strokeWidth=1.5).encode(y="y:Q"))
        capas.append(alt.Chart(regla).mark_text(align="left", dx=4, dy=-7, color=MUT,
                                                fontSize=11)
                     .encode(x=alt.value(0), y="y:Q", text="t:N"))
    return (alt.layer(*capas).properties(height=320)
            .configure(locale=LOCALE)
            .configure_view(strokeWidth=0)
            .configure_axis(labelColor=MUT, titleColor=MUT, domainColor="#CBD5E1",
                            tickColor="#CBD5E1"))


# ---------------------------------------------------------------- sidebar ---
with st.sidebar:
    st.markdown('<div class="brand">Tablero <span>Ambiental</span> Minero</div>'
                f'<div class="lema">{LEMA}</div>', unsafe_allow_html=True)
    st.caption("Monitoreo ambiental minero · prototipo")
    st.divider()
    st.markdown("**Quién firma cada paso**")
    firma_empresa = st.text_input("Responsable ambiental de la empresa",
                                  value=META["firma_empresa"])
    firma_autoridad = st.text_input("Revisor de la autoridad", value=META["firma_autoridad"])
    st.caption("Cada cambio de estado queda en el historial con este nombre, la fecha y la "
               "hora. Sin una persona detrás, «la autoridad controla» es una frase.")
    st.divider()
    if st.button("Reiniciar la demostración", width="stretch"):
        iniciar(forzar=True)
        st.rerun()
    st.caption(META["aviso_datos"])

# ------------------------------------------------------------------ header ---
st.markdown(
    '<div class="brand">Tablero <span>Ambiental</span> Minero</div>'
    f'<div class="lema">{LEMA}</div>'
    f'<div class="sub">{META["subtitulo"]}</div>', unsafe_allow_html=True)

if st.session_state.aviso:
    st.success(st.session_state.aviso)
    st.session_state.aviso = None

base, ev = evaluacion()

# La pestaña de cumplimiento aparece cuando el escenario trae las obligaciones
# del proyecto (DIA, PGA). El escenario sintético no las tiene.
HAY_CUMPLIMIENTO = not esc["obligaciones"].empty or not esc["programa"].empty
_pestanas = ["🌎 Ciudadanía", "🏭 Empresa"] + (["📋 Cumplimiento"] if HAY_CUMPLIMIENTO else []) \
    + ["🏛️ Autoridad", "🔌 Conectores", "📚 Cómo funciona"]
_tabs = dict(zip(_pestanas, st.tabs(_pestanas)))
tab_pub, tab_emp = _tabs["🌎 Ciudadanía"], _tabs["🏭 Empresa"]
tab_cum = _tabs.get("📋 Cumplimiento")
tab_aut, tab_con, tab_info = (_tabs["🏛️ Autoridad"], _tabs["🔌 Conectores"],
                              _tabs["📚 Cómo funciona"])

# =========================================================================
# Ciudadanía: lo que se publica, y nada más que eso.
# =========================================================================
with tab_pub:
    ids_publicados = publicadas(campanias)
    pub = ev[ev["campania_id"].isin(ids_publicados) & ev["estado"].map(hay)]
    st.caption("Solo se publican las campañas que la autoridad revisó y aprobó. Lo que una "
               "empresa presenta y todavía está en revisión no aparece acá.")

    # Filtros: una fila, arriba de todo lo que filtran.
    f1, f2, f3 = st.columns(3)
    op_proy = ["todos"] + [p["id"] for p in PROYECTOS]
    sel_proy = f1.selectbox("Proyecto", op_proy, key="pub_proyecto",
                            format_func=lambda x: "Todos los proyectos" if x == "todos"
                            else nombre_proyecto(x))
    vista = pub if sel_proy == "todos" else pub[pub["proyecto_id"] == sel_proy]
    op_mat = ["todos"] + [m for m in MATRICES if m in set(vista["matriz"])]
    asegurar_opcion("pub_matriz", op_mat)
    sel_mat = f2.selectbox("Componente", op_mat, key="pub_matriz",
                           format_func=lambda m: "Todos los componentes" if m == "todos"
                           else MATRICES[m])
    if sel_mat != "todos":
        vista = vista[vista["matriz"] == sel_mat]
    op_par = ["todos"] + sorted(set(vista["parametro"]), key=orden_parametro)
    asegurar_opcion("pub_parametro", op_par)
    sel_par = f3.selectbox("Parámetro", op_par, key="pub_parametro",
                           format_func=lambda q: "Todos los parámetros" if q == "todos"
                           else nombre_parametro(q))
    if sel_par != "todos":
        vista = vista[vista["parametro"] == sel_par]

    if vista.empty:
        st.info("No hay resultados publicados para esa combinación de filtros.")
    else:
        # Estado de cada punto: el peor resultado de su último muestreo
        # publicado. Es la foto de hoy; la historia está en la serie. Se toma
        # por punto y no por proyecto: en los datos reales cada campaña cubre
        # solo una parte de la red.
        ultima = vista.groupby("punto_id")["fecha"].transform("max")
        recientes = vista[vista["fecha"] == ultima]
        estado_punto = recientes.groupby("punto_id")["estado"].agg(peor_estado)
        cuentas = estado_punto.value_counts().to_dict()

        franja([
            (vista["proyecto_id"].nunique(), "proyectos"),
            (vista["punto_id"].nunique(), "puntos de monitoreo"),
            (vista["campania_id"].nunique(), "campañas publicadas"),
            (fmt(len(vista), 0), "resultados publicados"),
            (f"{max(vista['fecha']):%d/%m/%Y}", "último muestreo publicado"),
        ])

        pts = puntos[puntos["id"].isin(estado_punto.index)].copy()
        pts["estado"] = pts["id"].map(estado_punto)
        pts["estado_txt"] = pts["estado"].map(etiqueta)
        pts["componente"] = pts["matriz"].map(MATRICES)
        pts["proyecto"] = pts["proyecto_id"].map(lambda x: proyectos[x]["nombre"])
        pts["color"] = pts["estado"].map(lambda e: _rgb(ESTADOS[e]["color"]) + [235])
        # El tamaño repite la gravedad: un punto que supera se ve aunque no se
        # distinga el rojo del verde.
        pts["radio"] = pts["estado"].map({SUPERA: 12, ATENCION: 10}).fillna(7)
        pts = pts.sort_values("estado", key=lambda s: s.map(gravedad), ascending=False)

        capa = pdk.Layer(
            "ScatterplotLayer", data=pts, id="puntos", pickable=True, stroked=True,
            get_position="[lon, lat]", get_fill_color="color", get_radius="radio",
            # Entre comillas: pydeck lee cualquier texto como expresión, y
            # "pixels" a secas termina en círculos de kilómetros.
            radius_units="'pixels'", get_line_color=[255, 255, 255],
            line_width_min_pixels=2)
        capas_mapa = []
        contornos = esc.get("contornos")
        if contornos is not None and not contornos.empty:
            capas_mapa.append(pdk.Layer(
                "PolygonLayer", data=contornos, id="contornos", pickable=False,
                get_polygon="camino", get_fill_color=[21, 94, 117, 18],
                get_line_color=[21, 94, 117, 140], line_width_min_pixels=1, stroked=True,
                filled=True))
        comp = esc.get("componentes")
        if comp is not None and not comp.empty:
            # Las instalaciones del proyecto dan contexto: sin ellas, un punto de
            # agua es un círculo en el vacío.
            capas_mapa.append(pdk.Layer(
                "ScatterplotLayer", data=comp, id="componentes", pickable=False,
                get_position="[lon, lat]", get_fill_color=[100, 116, 139, 150], get_radius=4,
                radius_units="'pixels'"))
            rotulos = pdk.Layer(
                "TextLayer", data=comp, id="rotulos", pickable=False,
                get_position="[lon, lat]", get_text="nombre", get_size=12,
                get_color=[51, 65, 85], get_pixel_offset=[0, -11],
                character_set="'auto'", font_family="'Arial'", font_weight=600,
                outline_width=2, outline_color=[255, 255, 255], font_settings={"sdf": True})
        capas_mapa.append(capa)
        if comp is not None and not comp.empty:
            capas_mapa.append(rotulos)             # los rótulos, arriba de todo
        todas_lat = list(pts["lat"]) + (list(comp["lat"]) if comp is not None and
                                        not comp.empty else [])
        todas_lon = list(pts["lon"]) + (list(comp["lon"]) if comp is not None and
                                        not comp.empty else [])
        vista_mapa = pdk.ViewState(latitude=(min(todas_lat) + max(todas_lat)) / 2,
                                   longitude=(min(todas_lon) + max(todas_lon)) / 2,
                                   zoom=zoom_para(todas_lat, todas_lon))
        mapa = pdk.Deck(layers=capas_mapa, initial_view_state=vista_mapa, map_style=None,
                        tooltip={"html": "<b>{id}</b> · {nombre}<br/>{proyecto} · "
                                         "{componente}<br/>{estado_txt}",
                                 "style": {"backgroundColor": "#0F172A", "color": "white",
                                           "fontSize": "12px"}})
        evento = st.pydeck_chart(mapa, on_select="rerun", selection_mode="single-object",
                                 key="pub_mapa", height=420)
        elegidos = (evento.selection or {}).get("objects", {}).get("puntos", []) \
            if evento is not None and hasattr(evento, "selection") else []
        # La selección del mapa persiste entre recargas: se aplica solo cuando
        # cambia, para no pisar lo que se elija después en el desplegable.
        tocado = elegidos[0]["id"] if elegidos else None
        if tocado and tocado != st.session_state.get("pub_mapa_ultimo"):
            st.session_state["pub_punto"] = tocado
        st.session_state["pub_mapa_ultimo"] = tocado
        leyenda(set(estado_punto), cuentas)
        st.caption("Color, ícono y tamaño dicen lo mismo: el estado del peor resultado del punto "
                   "en la última campaña publicada. Tocá un punto del mapa para ver su historia.")

        with st.expander("Ver los puntos como tabla"):
            st.dataframe(
                pts.sort_values("estado", key=lambda s: s.map(gravedad))[
                    ["id", "nombre", "proyecto", "componente", "estado_txt"]],
                hide_index=True, width="stretch",
                column_config={"id": "Punto", "nombre": "Nombre", "proyecto": "Proyecto",
                               "componente": "Componente", "estado_txt": "Estado"})

        # --- serie de un punto -----------------------------------------------
        st.markdown("##### La historia de un punto")
        orden_pts = pts.sort_values("estado", key=lambda s: s.map(gravedad))["id"].tolist()
        # Abre en el punto con más alertas en su historia publicada, no en el
        # peor de hoy: la serie es la que cuenta qué pasó y qué se hizo.
        alertas = vista[vista["estado"].isin([SUPERA, ATENCION])].groupby("punto_id")[
            "estado"].agg(lambda e: 3 * (e == SUPERA).sum() + (e == ATENCION).sum())
        candidato = alertas.idxmax() if not alertas.empty else orden_pts[0]
        asegurar_opcion("pub_punto", orden_pts, candidato)
        punto_sel = st.selectbox(
            "Punto de monitoreo", orden_pts, key="pub_punto",
            format_func=lambda i: f"{i} · {nombre_punto[i]} — {etiqueta(estado_punto[i])}")
        del_punto = pub[pub["punto_id"] == punto_sel]
        if sel_par != "todos":
            del_punto = del_punto[del_punto["parametro"] == sel_par]
        ultimos = del_punto[del_punto["fecha"] == del_punto["fecha"].max()]
        params = sorted(set(del_punto["parametro"]), key=orden_parametro)
        # Abre en el parámetro con más alertas en su historia; si no hay, en
        # el de peor estado hoy.
        alertas_par = del_punto[del_punto["estado"].isin([SUPERA, ATENCION])].groupby(
            "parametro")["estado"].agg(
            lambda e: 3 * (e == SUPERA).sum() + (e == ATENCION).sum())
        peor = (alertas_par.idxmax() if not alertas_par.empty else
                min(ultimos.itertuples(), key=lambda r: gravedad(r.estado)).parametro)
        clave_par = f"pub_param_{punto_sel}"
        asegurar_opcion(clave_par, params, peor)
        par_sel = st.selectbox("Parámetro", params, key=clave_par, format_func=lambda q:
                               f"{nombre_parametro(q)} — "
                               f"{etiqueta(ultimos[ultimos['parametro'] == q]['estado'].iloc[0]) if q in set(ultimos['parametro']) else 'sin dato reciente'}")
        serie = del_punto[del_punto["parametro"] == par_sel].sort_values("fecha")
        ultimo = serie.iloc[-1]
        fila_base = base[(base["punto_id"] == punto_sel) & (base["parametro"] == par_sel)]
        n_base = int(fila_base.iloc[0]["n"]) if not fila_base.empty else 0
        rango_base = rango(fila_base.iloc[0], par_sel) if n_base >= 1 else None
        proy = puntos.loc[puntos["id"] == punto_sel, "proyecto_id"].iloc[0]
        fechas_base = [c["fecha"] for c in campanias.values()
                       if c["proyecto_id"] == proy and c["tipo"] == TIPO_BASE]
        fin_base = max(fechas_base) + timedelta(days=45) if fechas_base else None
        operacion = serie[serie["fecha"] > (max(fechas_base) if fechas_base else date.min)]
        if operacion.empty:
            fin_base = None          # todo el historial del punto es línea de base
        pendiente = tendencia_anual(list(operacion["fecha"]), list(operacion["valor"]))
        unidad = ultimo["unidad"]
        uso = puntos.loc[puntos["id"] == punto_sel, "uso"].iloc[0]

        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Último valor", f"{valor_txt(ultimo['calificador'], ultimo['valor'])} {unidad}",
                  help=f"Muestreo del {ultimo['fecha']:%d/%m/%Y}")
        m2.metric("Estado", etiqueta(ultimo["estado"]))
        m3.metric("Nivel guía", f"{fmt(ultimo['nivel_guia'])} {unidad}" if
                  hay(ultimo["nivel_guia"]) else "sin nivel guía",
                  help=(f"{USOS.get(uso, uso)} · {ultimo['norma']}" if hay(uso) and
                        hay(ultimo["norma"]) else "Este parámetro no tiene nivel guía para el "
                                                  "uso del punto: se compara con la línea de base."))
        m4.metric(f"Tendencia ({unidad} por año)",
                  ("+" if pendiente > 0 else "") + f"{pendiente:.2g}".replace(".", ",")
                  if pendiente is not None else "—",
                  help="Pendiente por mínimos cuadrados de las campañas desde que el proyecto "
                       "opera. Para el nivel freático, positivo es que el agua está más "
                       "profunda.")

        st.altair_chart(grafico_serie(serie, f"{nombre_parametro(par_sel)} ({unidad})",
                                      ultimo["nivel_guia"], rango_base, fin_base),
                        width="stretch")
        explicacion = [f"**Por qué este estado:** {ultimo['motivo']}"]
        if rango_base:
            explicacion.append(
                f"La franja gris es lo que el punto registraba antes del proyecto (línea de base, "
                f"{n_base} campaña{'s' if n_base != 1 else ''}, con su tolerancia): "
                f"{fmt(rango_base[0])} a {fmt(rango_base[1])} {unidad}."
                + ("" if n_base >= 3 else " Con menos de tres campañas sirve para saber si una "
                   "superación ya existía, no para marcar desvíos."))
        nota = campanias[ultimo["campania_id"]]["justificaciones"].get(
            f"{punto_sel}|{par_sel}")
        if nota:
            explicacion.append(f"**Lo que informó la empresa:** {nota}")
        st.markdown("  \n".join(explicacion))

        with st.expander("Ver la serie como tabla"):
            st.dataframe(pd.DataFrame({
                "Fecha": serie["fecha"], "Campaña": serie["campania_id"],
                "Valor": [valor_txt(c, v) for c, v in zip(serie["calificador"], serie["valor"])],
                "Unidad": serie["unidad"], "Estado": serie["estado"].map(etiqueta),
                "Por qué": serie["motivo"],
                **({"Fuente": serie["fuente"].fillna("")} if "fuente" in serie.columns
                   else {})}), hide_index=True, width="stretch")

        with st.expander("Cómo leer estos datos"):
            for e, d in ESTADOS.items():
                st.markdown(f"{chip(e)} {d['descripcion']}", unsafe_allow_html=True)
            st.markdown(
                "- **Un nivel guía no es un límite de vuelco.** Es la calidad que el recurso "
                "debería tener para un uso (beber, regar, sostener vida acuática). Por eso cada "
                "punto declara su uso y se compara contra la tabla de ese uso.\n"
                "- **En la Puna, superar un nivel guía puede ser natural.** El arsénico y el boro "
                "de muchas lagunas y vertientes ya superaban los niveles guía antes de cualquier "
                "proyecto. La línea de base existe para distinguir eso de un impacto.\n"
                "- **«No detectado» no siempre alcanza.** Si el método del laboratorio no llega a "
                "medir tan bajo como el nivel guía, el resultado no permite afirmar que cumple.")

        st.markdown("##### Datos abiertos")
        env_pub = Envio(campania=None, proyecto=None,
                        puntos=puntos[puntos["id"].isin(vista["punto_id"])],
                        evaluados=vista)
        d1, d2, d3 = st.columns(3)
        for col, clave in zip((d1, d2, d3), ("datos_abiertos", "geojson", "sensorthings")):
            col.download_button(EXPORTADORES[clave][0],
                                data=functools.partial(contenido, clave, env_pub),
                                file_name=nombre_archivo(clave, env_pub),
                                mime=EXPORTADORES[clave][3], width="stretch",
                                key=f"pub_dl_{clave}")
        st.caption("Lo mismo que se ve en pantalla, con la selección de filtros actual, en "
                   "formatos abiertos: Frictionless (CSV + esquema, publicable en un portal CKAN), "
                   "GeoJSON y OGC SensorThings.")

# =========================================================================
# Empresa: de la planilla del laboratorio a la presentación.
# =========================================================================
ETAPAS = [("1", "Carga", "Empresa"), ("2", "Lectura", "Sistema"),
          ("3", "Control de carga", "Sistema"), ("4", "Semáforo", "Sistema"),
          ("5", "Justificación", "Empresa"), ("6", "Presentación", "Empresa"),
          ("7", "Revisión", "Autoridad"), ("8", "Publicación", "Sistema")]

def usar_ejemplo():
    # Va como callback: cambia el proyecto elegido, y el estado de un widget
    # solo se puede tocar antes de que se dibuje.
    st.session_state.usar_ejemplo = True
    st.session_state.emp_proyecto = META["demo_proyecto"]
    st.session_state.emp_fecha = date.fromisoformat(META["demo_fecha"])
    st.session_state.borrador = None


with tab_emp:
    st.markdown(
        '<div class="pipe">' + "".join(
            f'<div class="paso{" humano" if quien == "Autoridad" else ""}">'
            f'<div class="n">ETAPA {n}</div><div class="q">{nom}</div>'
            f'<div class="w">{quien}</div></div>' for n, nom, quien in ETAPAS) + "</div>",
        unsafe_allow_html=True)
    st.caption("El sistema lee, controla y arma el semáforo; la empresa justifica y presenta; "
               "**la autoridad decide**. Nada se publica sin su aprobación.")

    observadas = [c for c in campanias.values() if c["estado"] == OBSERVADA]
    for c in observadas:
        ultima_obs = [h for h in c["historial"] if h["estado"] == OBSERVADA][-1]
        with st.container(border=True):
            st.warning(f"La autoridad observó la campaña **{c['id']}**: «{ultima_obs['comentario']}» "
                       f"({ultima_obs['actor']}, {ultima_obs['fecha_hora']:%d/%m/%Y %H:%M}).")
            if st.button(f"Volver a presentar {c['id']}", key=f"represent_{c['id']}"):
                try:
                    transicionar(c, PRESENTADA, firma_empresa, "empresa",
                                 "Se responde la observación.")
                    st.session_state.version += 1
                    st.session_state.aviso = f"Campaña {c['id']} presentada de nuevo."
                    st.rerun()
                except (ValueError, PermissionError) as e:
                    st.error(str(e))

    # --- etapa 1: carga -------------------------------------------------------
    st.markdown("##### 1 · Carga — *Empresa*")
    c1, c2 = st.columns([3, 2])
    with c1:
        emp_proy = st.selectbox("Proyecto", [p["id"] for p in PROYECTOS], key="emp_proyecto",
                                format_func=nombre_proyecto)
        if "emp_fecha" not in st.session_state:
            st.session_state.emp_fecha = date.fromisoformat(META["demo_fecha"])
        emp_fecha = st.date_input("Fecha de muestreo (si la planilla no la trae)",
                                  format="DD/MM/YYYY", key="emp_fecha")
        archivo = st.file_uploader("Planilla del laboratorio: Excel con una o varias hojas, o CSV",
                                   type=["xlsx", "csv"], key="emp_archivo")
    with c2:
        st.markdown("**¿No tenés una planilla a mano?**")
        st.caption(META["demo_texto"])
        st.button(META["demo_boton"], type="primary", width="stretch", on_click=usar_ejemplo)
        st.download_button("Descargar la planilla de ejemplo",
                           data=st.session_state.ejemplo,
                           file_name="planilla-laboratorio-ejemplo.xlsx",
                           mime=EXPORTADORES["planilla_xlsx"][3], width="stretch")

    fuente = None
    if archivo is not None:
        fuente = (archivo.name, archivo.getvalue())
    elif st.session_state.usar_ejemplo:
        fuente = ("planilla-laboratorio-ejemplo.xlsx", st.session_state.ejemplo)

    if fuente is None:
        st.info("Subí la planilla del laboratorio o usá la de ejemplo para seguir el recorrido.")
    else:
        firma = (fuente[0], hashlib.sha256(fuente[1]).hexdigest(), emp_proy, emp_fecha)
        borrador = st.session_state.borrador
        if borrador is None or borrador["firma"] != firma:
            # Solo los puntos del proyecto elegido: un punto de otro proyecto en
            # la planilla es un error de carga, no un dato más.
            puntos_proy = puntos[puntos["proyecto_id"] == emp_proy]
            try:
                tablas = leer_archivo(fuente[0], fuente[1])
                res, informe = interpretar(tablas, puntos_proy, emp_fecha)
                borrador = {"firma": firma, "nombre": fuente[0], "res": res, "informe": informe,
                            "correcciones": {}, "descartadas": set(), "justificaciones": {}}
            except Exception as e:                       # noqa: BLE001
                # Que un archivo roto no deje la pantalla en blanco: se avisa.
                borrador = {"firma": firma, "nombre": fuente[0], "falla": str(e)}
            st.session_state.borrador = borrador

        if "falla" in borrador:
            st.error(f"No se pudo leer «{borrador['nombre']}»: {borrador['falla']}")
        else:
            res, informe = borrador["res"], borrador["informe"]

            # --- etapa 2: lectura -------------------------------------------------
            st.markdown("##### 2 · Lectura — *Sistema*")
            hojas = ", ".join(f"«{h}» ({f})" for h, f in informe["formatos"].items())
            st.markdown(f"Se leyó **{borrador['nombre']}**: {len(informe['formatos'])} hoja(s) "
                        f"— {hojas}. **{informe['leidos']}** resultados leídos, "
                        f"**{informe['con_error']}** con problemas.")
            with st.expander("Cómo se interpretó cada columna"):
                tabla_cols = pd.DataFrame(informe["columnas"])
                if not tabla_cols.empty:
                    tabla_cols["se lee como"] = tabla_cols["se lee como"].map(
                        lambda x: {"punto_id": "punto de muestreo", "fecha": "fecha de muestreo",
                                   "parametro": "parámetro", "valor": "valor",
                                   "unidad": "unidad", "ld": "límite de detección"}.get(
                            x, nombre_parametro(x.split(" [")[0]) +
                            (f" [{x.split(' [')[1]}" if " [" in x else "")))
                    st.dataframe(tabla_cols, hide_index=True, width="stretch")
                if informe["ignoradas"]:
                    st.caption("Columnas que no son parámetros y se dejaron de lado: "
                               + " · ".join(informe["ignoradas"]))
            for aviso in informe["avisos"]:
                st.warning(aviso)

            # Correcciones y descartes que la empresa ya decidió.
            trabajo = res.copy()
            for idx, valor in borrador["correcciones"].items():
                trabajo.loc[idx, "valor"] = valor
                trabajo.loc[idx, "valor_original"] = f"{trabajo.loc[idx, 'valor_original']} → " \
                                                     f"{fmt(valor)} (corregido)"
            trabajo = trabajo.drop(index=list(borrador["descartadas"]))
            evb = evaluar(trabajo, puntos, base)
            problemas = controles(evb)

            # --- etapa 3: control de carga ------------------------------------------
            st.markdown("##### 3 · Control de carga — *Sistema*")
            if not problemas:
                st.success("Sin problemas de carga: puntos registrados, unidades coherentes, "
                           "fechas válidas, sin duplicados y nada fuera de escala.")
            for p in problemas:
                fila = evb.loc[p["indice"]]
                lugar = f"Hoja «{fila['hoja']}», fila {fila['fila']}, columna «{fila['columna']}»"
                with st.container(border=True):
                    a, b = st.columns([4, 1])
                    icono = "⛔" if p["gravedad"] == "bloqueante" else "⚠️"
                    a.markdown(f"{icono} **{p['problema']}**  \n<span class='sub'>{lugar} · "
                               f"valor leído: «{fila['valor_original']}»</span>",
                               unsafe_allow_html=True)
                    if hay(fila.get("valor_sugerido")):
                        if b.button(f"Corregir a {fmt(fila['valor_sugerido'])}",
                                    key=f"corr_{p['indice']}", width="stretch"):
                            borrador["correcciones"][p["indice"]] = float(fila["valor_sugerido"])
                            st.rerun()
                    elif p["gravedad"] == "bloqueante":
                        if b.button("Descartar fila", key=f"desc_{p['indice']}",
                                    width="stretch"):
                            borrador["descartadas"].add(p["indice"])
                            st.rerun()

            # --- etapa 4: semáforo ---------------------------------------------------
            st.markdown("##### 4 · Semáforo — *Sistema*")
            validos = evb[evb["estado"].map(hay)]
            cuenta = validos["estado"].value_counts().to_dict()
            leyenda(set(cuenta), cuenta)
            solo_alertas = st.toggle("Mostrar solo lo que no cumple", value=True,
                                     key="emp_solo_alertas")
            mostrar = validos[validos["estado"] != CUMPLE] if solo_alertas else validos
            mostrar = mostrar.assign(orden=mostrar["estado"].map(gravedad)).sort_values(
                ["orden", "punto_id"])
            st.dataframe(pd.DataFrame({
                "Punto": mostrar["punto_id"],
                "Parámetro": mostrar["parametro"].map(nombre_parametro),
                "Valor": [valor_txt(c, v) for c, v in zip(mostrar["calificador"],
                                                          mostrar["valor"])],
                "Unidad": mostrar["unidad"], "Estado": mostrar["estado"].map(etiqueta),
                "Por qué": mostrar["motivo"],
                "Norma": mostrar["norma"].map(lambda x: x if hay(x) else "—"),
            }), hide_index=True, width="stretch",
                column_config={"Por qué": st.column_config.TextColumn(width="large")})

            # --- etapa 5: justificación ------------------------------------------------
            st.markdown("##### 5 · Justificación — *Empresa*")
            superan = validos[validos["estado"] == SUPERA]
            otras = validos[validos["estado"].isin([ATENCION, NO_CONCLUYENTE])]
            if superan.empty:
                st.caption("Ningún resultado supera el nivel guía: no hace falta justificar nada "
                           "para presentar. Podés comentar lo que pide atención, si querés.")
            else:
                st.caption("Toda superación del nivel guía tiene que llegar explicada: causa, "
                           "acción tomada y seguimiento. Sin eso no se puede presentar.")
            for r in pd.concat([superan, otras]).itertuples():
                k = f"{r.punto_id}|{r.parametro}"
                obligatoria = r.estado == SUPERA
                borrador["justificaciones"][k] = st.text_area(
                    f"{ESTADOS[r.estado]['icono']} {r.punto_id} · {nombre_parametro(r.parametro)}"
                    f" — {valor_txt(r.calificador, r.valor)} {r.unidad}"
                    + (" (obligatoria)" if obligatoria else " (opcional)"),
                    value=borrador["justificaciones"].get(k, ""), key=f"just_{k}", height=68,
                    placeholder="Qué pasó, qué se hizo y cómo se sigue.")

            # --- etapa 6: presentación ---------------------------------------------------
            st.markdown("##### 6 · Presentación — *Empresa*")
            cid = f"{emp_proy}-{emp_fecha.year}-{emp_fecha.month:02d}"
            faltan = faltantes_para_presentar(evb, problemas, borrador["justificaciones"])
            existente = campanias.get(cid)
            if existente and existente["estado"] != OBSERVADA:
                faltan.append(f"Ya hay una campaña {cid} en estado "
                              f"{ESTADOS_CAMPANIA[existente['estado']].split(' ·')[0].lower()}.")
            if faltan:
                st.markdown("Para presentar falta:\n" + "\n".join(f"- {f}" for f in faltan))
            presentar = st.button(f"Presentar la campaña {cid} a la autoridad", type="primary",
                                  disabled=bool(faltan), key="emp_presentar")
            if presentar and not faltan:
                campania = existente or nueva_campania(
                    proyectos[emp_proy], emp_fecha, META["demo_tipo"],
                    esc.get("demo_campania") if META.get("real") else None)
                campania["justificaciones"] = {k: v for k, v in
                                               borrador["justificaciones"].items() if v.strip()}
                try:
                    transicionar(campania, PRESENTADA, firma_empresa, "empresa")
                except (ValueError, PermissionError) as e:
                    st.error(str(e))
                else:
                    nuevos = validos.drop(columns=[c for c in validos.columns if c not in
                                                   st.session_state.resultados.columns])
                    nuevos = nuevos.assign(campania_id=cid, proyecto_id=emp_proy,
                                           calificador=nuevos["calificador"].fillna(""))
                    previos = st.session_state.resultados
                    previos = previos[previos["campania_id"] != cid]
                    st.session_state.resultados = pd.concat([previos, nuevos],
                                                            ignore_index=True)
                    campanias[cid] = campania
                    st.session_state.version += 1
                    st.session_state.borrador = None
                    st.session_state.usar_ejemplo = False
                    st.session_state.aviso = (
                        f"Campaña {cid} presentada. Ahora está en la pestaña Autoridad esperando "
                        "revisión, y en Conectores ya podés armar el paquete para el expediente.")
                    st.rerun()

# =========================================================================
# Cumplimiento: las condiciones de la DIA y el programa de monitoreo del PGA.
# El estado de cada obligación lo declara la empresa: el sistema no lo infiere.
# =========================================================================
ESTADOS_OBLIGACION = ["Sin relevar", "Pendiente", "En curso", "Cumplida", "No aplica"]

if tab_cum is not None:
    with tab_cum:
        obl = esc["obligaciones"]
        prog = esc["programa"]
        hoy_c = date.today()
        if not obl.empty:
            if "obl_editadas" not in st.session_state:
                st.session_state.obl_editadas = obl.assign(
                    estado="Sin relevar", responsable="", evidencia="")
            tabla_obl = st.session_state.obl_editadas
            vence = pd.to_datetime(tabla_obl["vence"], errors="coerce").dt.date
            abiertas = ~tabla_obl["estado"].isin(["Cumplida", "No aplica"])
            proximas = sorted(v for v, a in zip(vence, abiertas) if a and pd.notna(v)
                              and v >= hoy_c)
            # Vencida es lo que la empresa marcó como abierto y ya pasó su plazo.
            # Lo que nadie relevó todavía no se presume incumplido.
            marcadas = tabla_obl["estado"].isin(["Pendiente", "En curso"])
            vencidas = [f"{i} ({v:%d/%m/%Y})" for i, v, m in
                        zip(tabla_obl["item"], vence, marcadas) if m and pd.notna(v) and v < hoy_c]
            franja([
                (len(tabla_obl), "obligaciones relevadas"),
                (tabla_obl["jurisdiccion"].nunique(), "jurisdicciones"),
                (int(vence.notna().sum()), "con plazo fijo"),
                (int((tabla_obl["estado"] == "Sin relevar").sum()), "sin estado cargado"),
                (f"{proximas[0]:%d/%m/%Y}" if proximas else "—", "próximo vencimiento"),
            ])
            if vencidas:
                st.warning("Con plazo vencido y marcadas como abiertas: " + ", ".join(vencidas))
            st.markdown("##### Condiciones de las DIA y compromisos")
            st.caption("Cada fila cita la resolución y el ítem del que sale. El estado, el "
                       "responsable y la evidencia los completa la empresa: el tablero no "
                       "presume que algo esté cumplido. Los vencimientos con plazo en días se "
                       "cuentan desde la fecha indicada en «Desde» y hay que confirmarlos con "
                       "la fecha de notificación.")
            columnas_obl = {
                "jurisdiccion": st.column_config.TextColumn("Jurisdicción", disabled=True),
                "item": st.column_config.TextColumn("Ítem", disabled=True, width="small"),
                "requisito": st.column_config.TextColumn("Qué exige", disabled=True,
                                                         width="large"),
                "plazo": st.column_config.TextColumn("Plazo / frecuencia", disabled=True),
                "vence": st.column_config.DateColumn("Vence (estimado)", disabled=True,
                                                     format="DD/MM/YYYY"),
                "estado": st.column_config.SelectboxColumn("Estado", options=ESTADOS_OBLIGACION,
                                                           required=True),
                "responsable": st.column_config.TextColumn("Responsable"),
                "evidencia": st.column_config.TextColumn("Evidencia"),
                "fuente": st.column_config.TextColumn("Fuente", disabled=True),
            }
            visibles = [c for c in columnas_obl if c in tabla_obl.columns]
            editada = st.data_editor(
                tabla_obl.assign(vence=vence)[visibles], hide_index=True, width="stretch",
                column_config=columnas_obl, key="obl_editor")
            for col in ("estado", "responsable", "evidencia"):
                st.session_state.obl_editadas[col] = editada[col].values
        if not prog.empty:
            st.markdown("##### Programa de monitoreo del PGA")
            ultima_por_punto = {}
            for c in campanias.values():
                if c["estado"] != APROBADA:
                    continue
                for pid_ in set(st.session_state.resultados.loc[
                        st.session_state.resultados["campania_id"] == c["id"], "punto_id"]):
                    ultima_por_punto[pid_] = max(ultima_por_punto.get(pid_, c["fecha"]),
                                                 c["fecha"])
            filas_prog = []
            for r in prog.to_dict("records"):
                ids = [x.strip() for x in r.get("puntos", "").split(";") if x.strip()]
                fechas = [ultima_por_punto[i] for i in ids if i in ultima_por_punto]
                filas_prog.append({
                    "Componente": r.get("componente", ""),
                    "Puntos": len(ids) if ids else r.get("n_puntos", ""),
                    "Parámetros": r.get("parametros", ""),
                    "Frecuencia": r.get("frecuencia", ""),
                    "Último dato en el tablero": max(fechas) if fechas else None,
                    "Referencia": r.get("norma", ""),
                    "Fuente": r.get("fuente", ""),
                })
            st.dataframe(pd.DataFrame(filas_prog), hide_index=True, width="stretch",
                         column_config={
                             "Último dato en el tablero": st.column_config.DateColumn(
                                 format="DD/MM/YYYY"),
                             "Parámetros": st.column_config.TextColumn(width="large")})
            st.caption("«Último dato en el tablero» es la campaña más reciente cargada para esos "
                       "puntos. En este prototipo solo está la línea de base del IIA: las "
                       "campañas posteriores a la DIA se incorporan en la implementación.")

# =========================================================================
# Autoridad: revisar, observar o aprobar. Lo aprobado se publica.
# =========================================================================
with tab_aut:
    hoy = date.today()
    filas_estado = []
    for p in PROYECTOS:
        mias = [c for c in campanias.values() if c["proyecto_id"] == p["id"]]
        aprobadas = [c for c in mias if c["estado"] == APROBADA]
        pendientes_p = [c for c in mias if c["estado"] in (PRESENTADA, OBSERVADA)]
        ultima_c = max(mias, key=lambda c: c["fecha"]) if mias else None
        # Campañas trimestrales: la próxima se espera tres meses después de la
        # última, con 30 días de margen para tener los resultados del laboratorio.
        esperada = (ultima_c["fecha"] + timedelta(days=91)) if ultima_c and \
            META["vencimientos"] else None
        margen = 30 - (hoy - esperada).days if esperada else None
        if not META["vencimientos"]:
            situacion = META.get("situacion", "—")
        elif margen is None or hoy <= esperada:
            situacion = "al día"
        elif margen > 0:
            situacion = f"vence en {margen} d"
        elif margen == 0:
            situacion = "vence hoy"
        else:
            situacion = f"atrasada {-margen} d"
        filas_estado.append({
            "Proyecto": p["nombre"], "Empresa": p["empresa"], "Provincia": p["provincia"],
            "Última aprobada": max(c["fecha"] for c in aprobadas) if aprobadas else None,
            "En revisión": len([c for c in pendientes_p if c["estado"] == PRESENTADA]),
            "Observadas": len([c for c in pendientes_p if c["estado"] == OBSERVADA]),
            **({"Próxima campaña esperada": esperada} if META["vencimientos"] else {}),
            "Situación": situacion})
    st.markdown("##### Entregas por proyecto")
    st.dataframe(pd.DataFrame(filas_estado), hide_index=True, width="stretch",
                 column_config={
                     "Última aprobada": st.column_config.DateColumn(format="DD/MM/YYYY"),
                     "Próxima campaña esperada": st.column_config.DateColumn(format="DD/MM/YYYY")})
    st.caption(META.get("nota_entregas") or
               "Las campañas son trimestrales. El aviso de vencimientos es lo que CyMA (Santa "
               "Cruz) hace por la autoridad: nadie tiene que acordarse de pedir lo que falta.")

    en_revision = sorted([c for c in campanias.values() if c["estado"] == PRESENTADA],
                         key=lambda c: c["fecha"], reverse=True)
    st.markdown("##### Campañas esperando revisión")
    if not en_revision:
        st.success("No hay campañas esperando revisión.")
    else:
        sel = st.selectbox("Campaña", [c["id"] for c in en_revision], key="aut_campania",
                           format_func=lambda i: f"{i} · {nombre_proyecto(campanias[i]['proyecto_id'])}")
        c = campanias[sel]
        evc = ev[(ev["campania_id"] == sel) & ev["estado"].map(hay)]
        cuenta = evc["estado"].value_counts().to_dict()
        franja([(f"{c['fecha']:%d/%m/%Y}", "fecha de muestreo"),
                (evc["punto_id"].nunique(), "puntos"), (len(evc), "resultados"),
                (cuenta.get(SUPERA, 0), "superan el nivel guía"),
                (len(c["justificaciones"]), "justificaciones de la empresa")])
        st.caption(f"Laboratorio: {c['laboratorio']} · {c['acreditacion']}. Participantes: "
                   + (", ".join(c["participantes"]) or "—") + ".")
        leyenda(set(cuenta), cuenta)
        st.markdown("**Lo que la autoridad tiene que mirar**")
        mirar = evc[evc["estado"] != CUMPLE]
        mirar = mirar.assign(orden=mirar["estado"].map(gravedad)).sort_values("orden")
        st.dataframe(pd.DataFrame({
            "Punto": mirar["punto_id"],
            "Parámetro": mirar["parametro"].map(nombre_parametro),
            "Valor": [f"{valor_txt(a, b)} {u}" for a, b, u in
                      zip(mirar["calificador"], mirar["valor"], mirar["unidad"])],
            "Estado": mirar["estado"].map(etiqueta),
            "Justificación de la empresa": [c["justificaciones"].get(f"{p}|{q}", "—")
                                            for p, q in zip(mirar["punto_id"],
                                                            mirar["parametro"])],
            "Por qué": mirar["motivo"],
        }), hide_index=True, width="stretch", column_config={
            "Justificación de la empresa": st.column_config.TextColumn(width="large"),
            "Por qué": st.column_config.TextColumn(width="large")})
        with st.expander("Historial de la campaña"):
            st.dataframe(pd.DataFrame(c["historial"]).rename(columns={
                "fecha_hora": "Fecha y hora", "actor": "Quién", "rol": "Rol",
                "accion": "Qué hizo", "estado": "Estado", "comentario": "Comentario"}),
                hide_index=True, width="stretch")
        comentario = st.text_area("Comentario de la revisión", key=f"aut_com_{sel}",
                                  placeholder="Obligatorio para observar: qué hay que corregir.")
        a1, a2, _ = st.columns([1, 1, 2])
        if a1.button("Aprobar y publicar", type="primary", key=f"aut_ok_{sel}",
                     width="stretch"):
            try:
                transicionar(c, APROBADA, firma_autoridad, "autoridad", comentario)
                st.session_state.version += 1
                st.session_state.aviso = (f"Campaña {sel} aprobada: ya está publicada en la "
                                          "vista de Ciudadanía.")
                st.rerun()
            except (ValueError, PermissionError) as e:
                st.error(str(e))
        if a2.button("Observar", key=f"aut_obs_{sel}", width="stretch"):
            try:
                transicionar(c, OBSERVADA, firma_autoridad, "autoridad", comentario)
                st.session_state.version += 1
                st.session_state.aviso = f"Campaña {sel} observada: vuelve a la empresa."
                st.rerun()
            except (ValueError, PermissionError) as e:
                st.error(str(e))

# =========================================================================
# Conectores: la misma campaña, en el formato de cada canal oficial.
# =========================================================================
TIPOS_CANAL = {"expediente": "Expediente TAD/GDE", "plataforma_web": "Plataforma web",
               "api": "API", "geoservicio": "Geoservicio OGC",
               "datos_abiertos": "Datos abiertos", "estandar": "Estándar abierto"}

with tab_con:
    st.caption("Hoy ninguna plataforma provincial publica una API de carga. Lo que existe son "
               "expedientes electrónicos (TAD + GDE) y plataformas web donde la empresa carga a "
               "mano. El conector arma exactamente lo que pide cada canal, y deja lista la "
               "conexión por API para el día que la autoridad la habilite.")
    disponibles = sorted([c for c in campanias.values() if c["estado"] != "BORRADOR"],
                         key=lambda c: (c["fecha"], c["id"]), reverse=True)
    k1, k2 = st.columns(2)
    sel_c = k1.selectbox("Campaña", [c["id"] for c in disponibles], key="con_campania",
                         format_func=lambda i: f"{i} · "
                         f"{ESTADOS_CAMPANIA[campanias[i]['estado']].split(' ·')[0]}")
    asegurar_opcion("con_perfil", [p["id"] for p in perfiles], META.get("perfil"))
    sel_perfil = k2.selectbox("Jurisdicción", [p["id"] for p in perfiles], key="con_perfil",
                              format_func=lambda i: next(p["jurisdiccion"] for p in perfiles
                                                         if p["id"] == i))
    perfil = next(p for p in perfiles if p["id"] == sel_perfil)
    if perfil.get("nota"):
        st.caption(perfil["nota"])
    for canal in perfil["canales"]:
        with st.container(border=True):
            st.markdown(
                f"**{canal['nombre']}**  \n"
                f"<span class='canal-tipo'>{TIPOS_CANAL.get(canal['tipo'], canal['tipo'])}</span>"
                f"<span class='canal-tipo'>{canal['estado']}</span>"
                + (f" <a href='{canal['url']}' target='_blank'>{canal['url']}</a>"
                   if canal.get("url") else ""), unsafe_allow_html=True)
            st.markdown(canal["descripcion"])
            if canal.get("a_confirmar"):
                st.caption(f"⚠️ A confirmar: {canal['a_confirmar']}")
            env_c = envio(sel_c, ev, perfil, canal)
            entregables = canal.get("entregables", [])
            if entregables:
                columnas = st.columns(min(len(entregables), 3))
                for i, clave in enumerate(entregables):
                    columnas[i % len(columnas)].download_button(
                        EXPORTADORES[clave][0], data=functools.partial(contenido, clave, env_c),
                        file_name=nombre_archivo(clave, env_c), mime=EXPORTADORES[clave][3],
                        width="stretch", key=f"dl_{sel_c}_{canal['id']}_{clave}")
            if canal["tipo"] == "api":
                solicitud = solicitud_api(env_c)
                things = solicitud["cuerpo"]["Things"]
                st.markdown(f"Solicitud que se enviaría: **{solicitud['metodo']}** "
                            f"`{solicitud['url']}`")
                if things:
                    t0, d0 = things[0], things[0]["Datastreams"][0]
                    muestra = {"Things": [{**t0, "Datastreams": [
                        {**d0, "Observations": d0["Observations"][:1]}]}]}
                    series = sum(len(t["Datastreams"]) for t in things)
                    observaciones = sum(len(d["Observations"]) for t in things
                                        for d in t["Datastreams"])
                    st.code(json.dumps({"encabezados": solicitud["encabezados"],
                                        "cuerpo": muestra}, ensure_ascii=False, indent=1),
                            language="json", height=260)
                    st.caption(f"Muestra: el primer punto, su primera serie y su primera "
                               f"observación. El envío completo lleva {len(things)} puntos, "
                               f"{series} series y {observaciones} observaciones.")
                if st.button("Enviar por API", disabled=not solicitud["lista_para_enviar"],
                             key=f"api_{canal['id']}",
                             help="Se habilita cuando el perfil tenga la URL del punto de acceso "
                                  "y el token esté en la variable de entorno indicada."):
                    try:
                        estado_http, respuesta = enviar(env_c)
                        st.success(f"Enviado: HTTP {estado_http}. {respuesta[:300]}")
                    except Exception as e:                   # noqa: BLE001
                        st.error(f"No se pudo enviar: {e}")
            if canal["tipo"] == "geoservicio" and canal.get("url"):
                st.code(f"{canal['url']}?service={'WFS' if 'wfs' in canal['url'] else 'WMS'}"
                        f"&request=GetCapabilities", language="text")
                st.caption("Capas oficiales para el mapa base: se consumen, no se cargan.")
            fuentes = canal.get("fuentes", [])
            if fuentes:
                st.caption("Fuentes: " + " · ".join(f"[{f['titulo']}]({f['url']})"
                                                    for f in fuentes))

# =========================================================================
# Cómo funciona: qué replica, qué es real y qué no.
# =========================================================================
with tab_info:
    st.markdown(f"""
#### Qué replica

**[MAIM Jujuy](https://maim.mineriajujuy.gob.ar/)** — *Monitoreos Ambientales de la Industria
Minera* — es la plataforma del Ministerio de Minería de Jujuy (ex Secretaría de Minería e
Hidrocarburos) con tres usuarios:

| Actor | Qué hace en el MAIM | Dónde está en este prototipo |
|---|---|---|
| Empresas mineras | Cargan su línea de base y sus monitoreos | 🏭 Empresa |
| Ministerio de Minería | Sistematiza, controla y publica | 🏛️ Autoridad |
| Público en general | Consulta históricos y mapas | 🌎 Ciudadanía |

En Santa Cruz funciona desde 2023 un sistema equivalente, **CyMA**, desarrollado por MiningIDEAS
y la Universidad Nacional de San Luis: la empresa carga cada monitoreo al obtenerlo, la autoridad
lo audita en tableros y el sistema avisa los vencimientos. Salta todavía no tiene uno, pero el
préstamo del Banco Mundial P510696 (aprobado en julio de 2026) financia un *sistema integrado de
control y monitoreo ambiental* y una plataforma de interoperabilidad.

#### Lo que agrega del lado de la empresa

- **Lee la planilla del laboratorio tal como llega**: varias hojas, encabezados libres, unidad en
  el encabezado, coma decimal, «<0,005».
- **Controla la carga antes de presentar**: puntos no registrados, unidades que no corresponden
  a la matriz, valores mil veces corridos (con la corrección sugerida), duplicados.
- **Semáforo de seis estados**, que distingue un impacto de un fondo natural y un «no detectado»
  que no alcanza para afirmar que cumple.
- **Un solo origen, todas las salidas**: el paquete para el expediente TAD/GDE (informe, Excel por
  componente, puntos en Shape POSGAR 94 y KMZ, con manifiesto de hashes), la planilla para las
  plataformas web, datos abiertos y OGC SensorThings para cuando haya API.

#### Qué es real y qué no

{chr(10).join("- " + linea for linea in META["que_es_real"])}
- **Niveles guía relevados de fuentes secundarias** (Ley 24.585 Anexo IV, Dec. 831/93 Anexo II,
  CAA art. 982). Cada uno lleva su norma; antes de usar datos reales hay que cotejarlos con el
  Boletín Oficial. Los de aire, suelo de uso industrial y ruido son los que aplica el Informe de
  Impacto Ambiental de la línea de base, con la tabla y el tiempo de promedio que cita. El PM2,5
  no tiene nivel guía en la Ley 24.585: se compara solo contra la línea de base.
- **Ninguna conexión a sistemas oficiales.** No hay APIs públicas de carga; el prototipo genera
  los archivos que cada canal pide hoy y deja escrita la conexión por API.

La investigación completa, con fuentes, está en
[`INVESTIGACION.md`]({REPO}/INVESTIGACION.md).
""")

# -------------------------------------------------------------------- pie ---
st.markdown(
    '<div class="pie"><div class="nom">Tablero <span>Ambiental</span> Minero</div>'
    f'<div class="lema" style="font-size:13px">{LEMA}</div>'
    f'<div>{META["pie"]}</div>'
    + "".join(f'<span class="norma">{n}</span>' for n in (
        "Ley 24.585", "Dec. 831/93", "CAA art. 982", "Dec. 7751-DEyP-2023", "Ley 6260 (Jujuy)"))
    + "</div>", unsafe_allow_html=True)
