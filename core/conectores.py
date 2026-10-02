"""
Conectores: llevar una campaña a cada canal oficial, en el formato que pide.

Hoy ninguna plataforma provincial publica una API de carga (ver
INVESTIGACION.md). Lo que existe es:
  - expedientes electrónicos por Trámites a Distancia + GDE (Jujuy y
    Catamarca, desde el 1/9/2026);
  - plataformas web donde la empresa carga a mano (MAIM, CyMA, SIMSa);
  - portales de datos abiertos y geoservicios, que son de solo lectura.

Por eso el conector hace lo que se puede hacer hoy —armar exactamente el
paquete que pide cada canal— y deja escrita la pieza para cuando haya una API:
el mismo contenido como solicitud HTTP, listo para enviar en cuanto la
autoridad publique el punto de acceso.

Agregar una jurisdicción es agregar un archivo en perfiles/, no tocar código.
"""

import hashlib
import io
import json
import math
import os
import urllib.request
import zipfile
from dataclasses import dataclass
from datetime import date, datetime
from html import escape
from pathlib import Path

import pandas as pd
import shapefile

from .catalogo import MATRICES, PARAMETROS, USOS, nombre_parametro
from .validacion import ESTADOS, hay, peor_estado

PERFILES = Path(__file__).resolve().parent.parent / "perfiles"
GENERADOR = "Tablero Ambiental Minero (prototipo)"


def cargar_perfiles(directorio=PERFILES):
    """Perfiles de jurisdicción, en el orden en que se muestran."""
    perfiles = [json.loads(p.read_text(encoding="utf-8"))
                for p in sorted(Path(directorio).glob("*.json"))]
    return sorted(perfiles, key=lambda p: p.get("orden", 99))


@dataclass
class Envio:
    """Todo lo que un exportador necesita saber de una campaña."""
    campania: dict | None          # None en exportaciones de varias campañas
    proyecto: dict | None
    puntos: pd.DataFrame           # los puntos que aparecen en los resultados
    evaluados: pd.DataFrame        # resultados válidos, con su estado
    perfil: dict | None = None
    canal: dict | None = None

    @property
    def base_nombre(self):
        if self.campania:
            return f"{self.campania['id']}".lower()
        return "tablero-ambiental"


# ---------------------------------------------------------- Gauss-Krüger ---
# Las presentaciones geográficas en Jujuy se piden en Gauss-Krüger POSGAR 94.
# La proyección está escrita acá (serie de Snyder sobre el elipsoide WGS84,
# que es el de POSGAR) para no sumar una dependencia de 30 MB por cuatro
# fórmulas; los tests la verifican contra pyproj al centímetro.

_A = 6378137.0
_F = 1 / 298.257223563
_E2 = _F * (2 - _F)
_EP2 = _E2 / (1 - _E2)


def faja_gauss_kruger(lon):
    """Faja 1 a 7: meridianos centrales -72, -69, ..., -54."""
    return min(7, max(1, int(round((lon + 72) / 3)) + 1))


def _arco_meridiano(phi):
    e2, e4, e6 = _E2, _E2 ** 2, _E2 ** 3
    return _A * ((1 - e2 / 4 - 3 * e4 / 64 - 5 * e6 / 256) * phi
                 - (3 * e2 / 8 + 3 * e4 / 32 + 45 * e6 / 1024) * math.sin(2 * phi)
                 + (15 * e4 / 256 + 45 * e6 / 1024) * math.sin(4 * phi)
                 - (35 * e6 / 3072) * math.sin(6 * phi))


def gauss_kruger(lat, lon, faja=None):
    """(este, norte, faja) en POSGAR 94 / Argentina <faja> (EPSG 22181-22187)."""
    faja = faja or faja_gauss_kruger(lon)
    phi, lam = math.radians(lat), math.radians(lon)
    lam0 = math.radians(-72 + 3 * (faja - 1))
    n = _A / math.sqrt(1 - _E2 * math.sin(phi) ** 2)
    t = math.tan(phi) ** 2
    c = _EP2 * math.cos(phi) ** 2
    a = (lam - lam0) * math.cos(phi)
    m = _arco_meridiano(phi) - _arco_meridiano(-math.pi / 2)   # origen en el polo sur
    x = n * (a + (1 - t + c) * a ** 3 / 6
             + (5 - 18 * t + t ** 2 + 72 * c - 58 * _EP2) * a ** 5 / 120)
    y = m + n * math.tan(phi) * (a ** 2 / 2 + (5 - t + 9 * c + 4 * c ** 2) * a ** 4 / 24
                                 + (61 - 58 * t + t ** 2 + 600 * c - 330 * _EP2) * a ** 6 / 720)
    return faja * 1_000_000 + 500_000 + x, y, faja


def prj_posgar94(faja):
    """WKT (formato ESRI) del .prj para POSGAR 94 / Argentina <faja>."""
    return (f'PROJCS["POSGAR_1994_Argentina_Zone_{faja}",GEOGCS["GCS_POSGAR_1994",'
            f'DATUM["D_POSGAR_1994",SPHEROID["WGS_1984",6378137.0,298.257223563]],'
            f'PRIMEM["Greenwich",0.0],UNIT["Degree",0.0174532925199433]],'
            f'PROJECTION["Transverse_Mercator"],'
            f'PARAMETER["False_Easting",{faja * 1_000_000 + 500_000:.1f}],'
            f'PARAMETER["False_Northing",0.0],'
            f'PARAMETER["Central_Meridian",{-72 + 3 * (faja - 1):.1f}],'
            f'PARAMETER["Scale_Factor",1.0],PARAMETER["Latitude_Of_Origin",-90.0],'
            f'UNIT["Meter",1.0]]')


# ------------------------------------------------------------------ apoyo ---

def _estado_por_punto(evaluados):
    if evaluados.empty:
        return {}
    return {pid: peor_estado(g["estado"]) for pid, g in evaluados.groupby("punto_id")}


def _texto_valor(calificador, valor):
    if not hay(valor):
        return "ND"
    return f"<{valor:g}" if calificador == "<" else valor


def _orden_parametro(codigo):
    lista = list(PARAMETROS)
    return lista.index(codigo) if codigo in lista else len(lista)


def _justificacion(env, punto_id, parametro):
    if not env.campania:
        return ""
    return env.campania.get("justificaciones", {}).get(f"{punto_id}|{parametro}", "")


# ------------------------------------------------- planilla por componente ---

def planilla_xlsx(env):
    """Resultados por componente: una hoja por matriz, como pide el IMAP."""
    salida = io.BytesIO()
    puntos = env.puntos.set_index("id")
    with pd.ExcelWriter(salida, engine="openpyxl") as libro:
        for matriz, nombre_hoja in MATRICES.items():
            sub = env.evaluados[env.evaluados["matriz"] == matriz]
            if sub.empty:
                continue
            sub = sub.assign(
                columna=[f"{nombre_parametro(p)} ({u})" for p, u in
                         zip(sub["parametro"], sub["unidad"])],
                celda=[_texto_valor(c, v) for c, v in zip(sub["calificador"], sub["valor"])],
                orden=sub["parametro"].map(_orden_parametro),
            )
            columnas = (sub.sort_values("orden").drop_duplicates("columna")["columna"].tolist())
            tabla = sub.pivot_table(index=["punto_id", "fecha"], columns="columna",
                                    values="celda", aggfunc="first")
            tabla = tabla.reindex(columns=columnas).reset_index()
            tabla.insert(1, "Nombre del punto", tabla["punto_id"].map(puntos["nombre"]))
            tabla.insert(3, "Latitud", tabla["punto_id"].map(puntos["lat"]))
            tabla.insert(4, "Longitud", tabla["punto_id"].map(puntos["lon"]))
            tabla = tabla.rename(columns={"punto_id": "Punto", "fecha": "Fecha de muestreo"})
            tabla.columns.name = None
            tabla.to_excel(libro, sheet_name=nombre_hoja[:31], index=False)

        semaforo = env.evaluados.assign(
            Parametro=env.evaluados["parametro"].map(nombre_parametro),
            Estado=env.evaluados["estado"].map(lambda e: ESTADOS[e]["nombre"]),
            Valor=[_texto_valor(c, v) for c, v in
                   zip(env.evaluados["calificador"], env.evaluados["valor"])],
            Justificacion=[_justificacion(env, p, q) for p, q in
                           zip(env.evaluados["punto_id"], env.evaluados["parametro"])],
        )[["punto_id", "fecha", "Parametro", "Valor", "unidad", "Estado", "motivo",
           "nivel_guia", "norma", "Justificacion"]]
        semaforo.columns = ["Punto", "Fecha", "Parámetro", "Valor", "Unidad", "Estado",
                            "Motivo", "Nivel guía", "Norma", "Justificación"]
        semaforo.to_excel(libro, sheet_name="Semáforo", index=False)

        if env.campania:
            c, p = env.campania, env.proyecto or {}
            meta = [("Campaña", c["id"]), ("Empresa", p.get("empresa", "")),
                    ("Proyecto", p.get("nombre", "")), ("Provincia", p.get("provincia", "")),
                    ("Fecha de muestreo", c["fecha"].strftime("%d/%m/%Y")),
                    ("Tipo", c["tipo"]), ("Laboratorio", c["laboratorio"]),
                    ("Acreditación", c["acreditacion"]), ("Consultora", c["consultora"]),
                    ("Participantes", ", ".join(c["participantes"])),
                    ("Generado por", f"{GENERADOR} · {datetime.now():%d/%m/%Y %H:%M}")]
            pd.DataFrame(meta, columns=["Dato", "Valor"]).to_excel(
                libro, sheet_name="Campaña", index=False)
    return (f"{env.base_nombre}-resultados.xlsx", salida.getvalue(),
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")


# ------------------------------------------------------------------- KMZ ---

def _color_kml(hex_rgb):
    """#RRGGBB → aabbggrr, el orden al revés que usa KML."""
    r, g, b = hex_rgb[1:3], hex_rgb[3:5], hex_rgb[5:7]
    return f"ff{b}{g}{r}".lower()


def puntos_kmz(env):
    """Puntos de monitoreo en KMZ, coloreados por su estado en la campaña."""
    estados = _estado_por_punto(env.evaluados)
    estilos = "".join(
        f'<Style id="{e}"><IconStyle><color>{_color_kml(d["color"])}</color><scale>1.1</scale>'
        f'<Icon><href>http://maps.google.com/mapfiles/kml/shapes/placemark_circle.png</href>'
        f'</Icon></IconStyle></Style>'
        for e, d in ESTADOS.items())
    marcas = []
    for p in env.puntos.itertuples():
        estado = estados.get(p.id)
        detalle = (f"{escape(p.nombre)}<br/>Matriz: {MATRICES[p.matriz]}<br/>"
                   f"Uso: {USOS.get(p.uso, 'sin uso asignado') if hay(p.uso) else 'sin uso asignado'}"
                   + (f"<br/>Estado: {ESTADOS[estado]['nombre']}" if estado else ""))
        marcas.append(
            f"<Placemark><name>{escape(p.id)}</name>"
            f"<description><![CDATA[{detalle}]]></description>"
            + (f"<styleUrl>#{estado}</styleUrl>" if estado else "")
            + f"<Point><coordinates>{p.lon:.6f},{p.lat:.6f},0</coordinates></Point></Placemark>")
    titulo = escape(env.campania["id"] if env.campania else "Puntos de monitoreo")
    kml = ('<?xml version="1.0" encoding="UTF-8"?>'
           '<kml xmlns="http://www.opengis.net/kml/2.2"><Document>'
           f"<name>{titulo}</name>{estilos}{''.join(marcas)}</Document></kml>")
    salida = io.BytesIO()
    with zipfile.ZipFile(salida, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("doc.kml", kml)
    return f"{env.base_nombre}-puntos.kmz", salida.getvalue(), "application/vnd.google-earth.kmz"


# ------------------------------------------------------------------- SHP ---

def puntos_shp(env):
    """Puntos de monitoreo en Shapefile, Gauss-Krüger POSGAR 94, comprimido en ZIP.

    Todos los puntos van en la faja del primero: un shapefile tiene una sola
    proyección, y un proyecto no se reparte entre dos fajas.
    """
    if env.puntos.empty:
        raise ValueError("No hay puntos para exportar.")
    estados = _estado_por_punto(env.evaluados)
    faja = faja_gauss_kruger(float(env.puntos["lon"].iloc[0]))
    shp, shx, dbf = io.BytesIO(), io.BytesIO(), io.BytesIO()
    w = shapefile.Writer(shp=shp, shx=shx, dbf=dbf, shapeType=shapefile.POINT,
                         encoding="utf-8")
    w.field("ID", "C", size=12)
    w.field("NOMBRE", "C", size=80)
    w.field("MATRIZ", "C", size=20)
    w.field("USO", "C", size=20)
    w.field("ESTADO", "C", size=16)
    w.field("LAT", "N", size=12, decimal=6)
    w.field("LON", "N", size=12, decimal=6)
    w.field("X_GK", "N", size=14, decimal=2)
    w.field("Y_GK", "N", size=14, decimal=2)
    w.field("FAJA", "N", size=2, decimal=0)
    for p in env.puntos.itertuples():
        este, norte, _ = gauss_kruger(p.lat, p.lon, faja)
        w.point(este, norte)
        w.record(p.id, p.nombre, p.matriz, p.uso if hay(p.uso) else "",
                 estados.get(p.id, ""), p.lat, p.lon, round(este, 2), round(norte, 2), faja)
    w.close()
    base = f"{env.base_nombre}-puntos"
    salida = io.BytesIO()
    with zipfile.ZipFile(salida, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr(f"{base}.shp", shp.getvalue())
        z.writestr(f"{base}.shx", shx.getvalue())
        z.writestr(f"{base}.dbf", dbf.getvalue())
        z.writestr(f"{base}.prj", prj_posgar94(faja))
        z.writestr(f"{base}.cpg", "UTF-8")
    return f"{base}-shp.zip", salida.getvalue(), "application/zip"


# --------------------------------------------------------------- GeoJSON ---

def puntos_geojson(env):
    estados = _estado_por_punto(env.evaluados)
    ultimo = (env.evaluados.groupby("punto_id")["fecha"].max().to_dict()
              if not env.evaluados.empty else {})
    rasgos = [{
        "type": "Feature",
        "geometry": {"type": "Point", "coordinates": [p.lon, p.lat]},
        "properties": {"id": p.id, "nombre": p.nombre, "matriz": p.matriz,
                       "uso": p.uso if hay(p.uso) else None,
                       "estado": estados.get(p.id),
                       "ultimo_muestreo": str(ultimo[p.id]) if p.id in ultimo else None},
    } for p in env.puntos.itertuples()]
    datos = {"type": "FeatureCollection", "features": rasgos}
    return (f"{env.base_nombre}-puntos.geojson",
            json.dumps(datos, ensure_ascii=False, indent=1).encode("utf-8"),
            "application/geo+json")


# ----------------------------------------------------------- SensorThings ---
# OGC SensorThings API: el estándar abierto para observaciones ambientales.
# Cada punto es un Thing con su Location; cada parámetro, un Datastream; cada
# resultado, una Observation. El JSON sale en la forma de "inserción profunda"
# que acepta un servidor SensorThings (por ejemplo FROST) en POST /Things.

def _sensorthings_dict(env):
    things = []
    lab = env.campania["laboratorio"] if env.campania else "Laboratorio"
    for p in env.puntos.itertuples():
        mios = env.evaluados[env.evaluados["punto_id"] == p.id]
        datastreams = []
        for parametro, g in mios.groupby("parametro"):
            unidad = g["unidad"].iloc[0]
            observaciones = [{
                "phenomenonTime": f"{o.fecha.isoformat()}T00:00:00Z",
                "result": None if not hay(o.valor) else float(o.valor),
                "parameters": {
                    "calificador": o.calificador or None,
                    "limite_deteccion": None if not hay(o.ld) else float(o.ld),
                    "estado": o.estado,
                    "campania": getattr(o, "campania_id", None) if hay(
                        getattr(o, "campania_id", None)) else (
                        env.campania["id"] if env.campania else None),
                },
            } for o in g.itertuples()]
            datastreams.append({
                "name": f"{p.id} · {nombre_parametro(parametro)}",
                "description": f"{nombre_parametro(parametro)} en {p.nombre}",
                "observationType":
                    "http://www.opengis.net/def/observationType/OGC-OM/2.0/OM_Measurement",
                "unitOfMeasurement": {"name": unidad, "symbol": unidad, "definition": ""},
                "ObservedProperty": {"name": nombre_parametro(parametro),
                                     "definition": f"urn:tablero-ambiental:parametro:{parametro}",
                                     "description": nombre_parametro(parametro)},
                "Sensor": {"name": lab, "encodingType": "text/plain",
                           "description": "Análisis de laboratorio",
                           "metadata": env.campania["acreditacion"] if env.campania else ""},
                "Observations": observaciones,
            })
        things.append({
            "name": p.id, "description": p.nombre,
            "properties": {"proyecto": env.proyecto["id"] if env.proyecto else None,
                           "matriz": p.matriz, "uso": p.uso if hay(p.uso) else None},
            "Locations": [{"name": p.nombre, "description": p.nombre,
                           "encodingType": "application/geo+json",
                           "location": {"type": "Point", "coordinates": [p.lon, p.lat]}}],
            "Datastreams": datastreams,
        })
    return {"Things": things}


def sensorthings(env):
    datos = _sensorthings_dict(env)
    return (f"{env.base_nombre}-sensorthings.json",
            json.dumps(datos, ensure_ascii=False, indent=1).encode("utf-8"),
            "application/json")


# --------------------------------------------------------------- informe ---

_ESTILO_INFORME = """
body{font-family:Georgia,'Times New Roman',serif;color:#0F172A;max-width:900px;margin:32px auto;
     padding:0 16px;line-height:1.45}
h1{font-size:24px;margin-bottom:2px} h2{font-size:17px;margin-top:28px;border-bottom:1px solid
#CBD5E1;padding-bottom:4px} .sub{color:#475569;font-size:13px}
table{border-collapse:collapse;width:100%;font-size:12px;margin:8px 0}
th,td{border:1px solid #CBD5E1;padding:4px 6px;text-align:left;vertical-align:top}
th{background:#F1F5F9} .e{display:inline-block;width:10px;height:10px;border-radius:50%;
margin-right:5px;vertical-align:middle}
.aviso{background:#FFFBEB;border-left:4px solid #B45309;padding:8px 12px;font-size:13px}
.firmas{display:flex;gap:40px;margin-top:56px} .firmas div{flex:1;border-top:1px solid #0F172A;
padding-top:6px;font-size:12px;text-align:center}
@media print{body{margin:0}}
"""


def _tabla_html(encabezados, filas):
    cab = "".join(f"<th>{escape(str(h))}</th>" for h in encabezados)
    cuerpo = "".join("<tr>" + "".join(f"<td>{c}</td>" for c in f) + "</tr>" for f in filas)
    return f"<table><thead><tr>{cab}</tr></thead><tbody>{cuerpo}</tbody></table>"


def _chip(estado):
    d = ESTADOS[estado]
    return f'<span class="e" style="background:{d["color"]}"></span>{d["nombre"]}'


def informe_html(env):
    """Informe de monitoreo con la estructura del IMAP de Jujuy, para imprimir a PDF."""
    c, p = env.campania, env.proyecto or {}
    if not c:
        raise ValueError("El informe es por campaña.")
    ev = env.evaluados
    cuenta = ev["estado"].value_counts()
    nombres = env.puntos.set_index("id")["nombre"]
    partes = [
        f"<h1>Informe de Monitoreo Ambiental</h1>"
        f"<div class='sub'>{escape(c['tipo'])} · Campaña {escape(c['id'])} · "
        f"muestreo del {c['fecha']:%d/%m/%Y}</div>",
        "<p class='aviso'>Documento generado por un prototipo con datos sintéticos. Ninguna "
        "empresa, proyecto, comunidad ni valor corresponde a la realidad.</p>",
        "<h2>1. Datos de la empresa y del proyecto</h2>",
        _tabla_html(["Dato", "Valor"], [
            ("Empresa", escape(p.get("empresa", ""))), ("Proyecto", escape(p.get("nombre", ""))),
            ("Provincia", escape(p.get("provincia", ""))),
            ("Mineral", escape(p.get("mineral", ""))), ("Etapa", escape(p.get("etapa", ""))),
        ]),
        "<h2>2. Resumen ejecutivo</h2>",
        f"<p>Se informan {len(ev)} resultados en {ev['punto_id'].nunique()} puntos de "
        f"monitoreo. Estado de los resultados frente a los niveles guía aplicables y a la línea "
        f"de base de cada punto:</p>",
        _tabla_html(["Estado", "Resultados", "Qué significa"], [
            (_chip(e), int(cuenta.get(e, 0)), escape(d["descripcion"]))
            for e, d in ESTADOS.items() if cuenta.get(e, 0)]),
        "<h2>3. Metodología</h2>",
        _tabla_html(["Dato", "Valor"], [
            ("Fecha de muestreo", f"{c['fecha']:%d/%m/%Y}"),
            ("Laboratorio", escape(c["laboratorio"])),
            ("Acreditación", escape(c["acreditacion"])),
            ("Consultora", escape(c["consultora"])),
            ("Criterio de evaluación",
             "Niveles guía según el uso de cada punto (Ley 24.585, Anexo IV; Dec. 831/93, "
             "Anexo II; CAA art. 982) y rango de la línea de base del punto."),
        ]),
        "<h2>4. Participación</h2>",
        "<p>" + (escape(", ".join(c["participantes"])) or "Campaña sin participación "
                                                           "comunitaria (línea de base).") + "</p>",
        "<h2>5. Resultados por componente</h2>",
    ]
    for matriz, nombre_matriz in MATRICES.items():
        sub = ev[ev["matriz"] == matriz]
        if sub.empty:
            continue
        sub = sub.assign(orden=sub["parametro"].map(_orden_parametro)).sort_values(
            ["punto_id", "orden"])
        partes.append(f"<h3>{nombre_matriz}</h3>")
        partes.append(_tabla_html(
            ["Punto", "Parámetro", "Valor", "Unidad", "Estado", "Nivel guía", "Norma"],
            [(f"{escape(r.punto_id)}<br/><span class='sub'>{escape(nombres.get(r.punto_id, ''))}"
              f"</span>", escape(nombre_parametro(r.parametro)),
              escape(str(_texto_valor(r.calificador, r.valor))).replace(".", ","),
              escape(r.unidad or ""), _chip(r.estado),
              "—" if not hay(r.nivel_guia) else f"{r.nivel_guia:g}".replace(".", ","),
              escape(r.norma or "—"))
             for r in sub.itertuples()]))
    destacados = ev[ev["estado"].isin(["SUPERA", "ATENCION", "NO_CONCLUYENTE",
                                       "FONDO_NATURAL"])]
    partes.append("<h2>6. Resultados que requieren atención y justificaciones</h2>")
    if destacados.empty:
        partes.append("<p>Todos los resultados cumplen los niveles guía y se encuentran dentro "
                      "del rango de la línea de base.</p>")
    else:
        partes.append(_tabla_html(
            ["Punto", "Parámetro", "Estado", "Motivo", "Justificación de la empresa"],
            [(escape(r.punto_id), escape(nombre_parametro(r.parametro)), _chip(r.estado),
              escape(r.motivo), escape(_justificacion(env, r.punto_id, r.parametro)) or "—")
             for r in destacados.itertuples()]))
    anexos = (env.canal or {}).get("anexos", [])
    if anexos:
        partes.append("<h2>7. Documentación que acompaña la presentación</h2>")
        partes.append(_tabla_html(["Documento", "Origen"], [
            (escape(a["documento"]),
             "Generado por el sistema" if a.get("genera_el_sistema") else
             "A adjuntar por la empresa")
            for a in anexos]))
    partes.append("<div class='firmas'><div>Responsable de la empresa</div>"
                  "<div>Consultora ambiental</div></div>")
    partes.append(f"<p class='sub' style='margin-top:24px'>{GENERADOR} · "
                  f"{datetime.now():%d/%m/%Y %H:%M}</p>")
    html = ("<!doctype html><html lang='es'><head><meta charset='utf-8'>"
            f"<title>Informe {escape(c['id'])}</title><style>{_ESTILO_INFORME}</style></head>"
            f"<body>{''.join(partes)}</body></html>")
    return f"{env.base_nombre}-informe.html", html.encode("utf-8"), "text/html"


# --------------------------------------------------- paquete para TAD/GDE ---

def _nota_presentacion(env):
    c, p = env.campania, env.proyecto or {}
    canal = (env.canal or {}).get("nombre", "la autoridad de aplicación")
    return (
        "<!doctype html><html lang='es'><head><meta charset='utf-8'>"
        "<title>Nota de presentación</title></head><body style='font-family:Georgia,serif;"
        "max-width:720px;margin:40px auto;line-height:1.6'>"
        f"<p style='text-align:right'>{date.today():%d/%m/%Y}</p>"
        f"<p>Sres. {escape((env.perfil or {}).get('autoridad', 'Autoridad de aplicación'))}</p>"
        "<p>De nuestra consideración:</p>"
        f"<p>{escape(p.get('empresa', ''))}, titular del {escape(p.get('nombre', ''))}, presenta "
        f"el informe de la campaña {escape(c['id'])} ({escape(c['tipo'].lower())}), con muestreo "
        f"del {c['fecha']:%d/%m/%Y}, a través de {escape(canal)}.</p>"
        "<p>Se acompañan el informe, los resultados por componente en planilla Excel y los "
        "puntos de monitoreo en formato Shape (Gauss-Krüger POSGAR 94) y KMZ.</p>"
        "<p>Sin otro particular, saludamos atentamente.</p>"
        "<p style='margin-top:60px'>______________________<br/>Representante legal</p>"
        "</body></html>")


def paquete_tad(env):
    """ZIP con todo lo que se sube al expediente, más un manifiesto con hashes.

    El manifiesto guarda el SHA-256 de cada archivo: si lo que se firmó en GDE
    y lo que publicó la empresa no coinciden, se nota.
    """
    archivos = [
        ("01-nota-de-presentacion.html", _nota_presentacion(env).encode("utf-8")),
    ]
    for i, fn in enumerate((informe_html, planilla_xlsx, puntos_kmz, puntos_shp), start=2):
        nombre, contenido, _ = fn(env)
        archivos.append((f"{i:02d}-{nombre}", contenido))
    anexos = (env.canal or {}).get("anexos", [])
    leame = [f"Paquete para {(env.canal or {}).get('nombre', 'el expediente')}", "",
             "Archivos generados por el sistema:"]
    leame += [f"  - {n}" for n, _ in archivos]
    pendientes = [a["documento"] for a in anexos if not a.get("genera_el_sistema")]
    if pendientes:
        leame += ["", "La empresa tiene que adjuntar, además:"]
        leame += [f"  - {d}" for d in pendientes]
    leame += ["", "Los archivos se firman digitalmente al incorporarlos al expediente (GDE).",
              "Datos sintéticos: este paquete sale de un prototipo."]
    archivos.append(("LEAME.txt", "\n".join(leame).encode("utf-8")))
    manifiesto = {
        "campania": env.campania["id"], "generado": datetime.now().isoformat(timespec="seconds"),
        "generador": GENERADOR, "canal": (env.canal or {}).get("id"),
        "archivos": [{"nombre": n, "bytes": len(b), "sha256": hashlib.sha256(b).hexdigest()}
                     for n, b in archivos],
    }
    archivos.append(("manifiesto.json",
                     json.dumps(manifiesto, ensure_ascii=False, indent=1).encode("utf-8")))
    salida = io.BytesIO()
    with zipfile.ZipFile(salida, "w", zipfile.ZIP_DEFLATED) as z:
        for nombre, contenido in archivos:
            z.writestr(nombre, contenido)
    return f"{env.base_nombre}-paquete-expediente.zip", salida.getvalue(), "application/zip"


# --------------------------------------------------------- datos abiertos ---

def datos_abiertos(env):
    """Paquete Frictionless (datapackage.json + CSV), publicable en un portal CKAN."""
    res = env.evaluados.assign(
        estado_nombre=env.evaluados["estado"].map(lambda e: ESTADOS[e]["nombre"]))
    columnas = ["campania_id", "proyecto_id", "punto_id", "fecha", "matriz", "parametro",
                "calificador", "valor", "unidad", "ld", "estado", "estado_nombre",
                "nivel_guia", "norma"]
    res = res[[c for c in columnas if c in res.columns]]
    puntos = env.puntos[["id", "proyecto_id", "nombre", "matriz", "uso", "lat", "lon"]]
    tipos = {"fecha": "date", "valor": "number", "ld": "number", "nivel_guia": "number",
             "lat": "number", "lon": "number"}
    paquete = {
        "name": "monitoreo-ambiental-minero",
        "title": "Monitoreos ambientales mineros (datos sintéticos de demostración)",
        "licenses": [{"name": "CC-BY-4.0", "path": "https://creativecommons.org/licenses/by/4.0/"}],
        "created": datetime.now().isoformat(timespec="seconds"),
        "resources": [
            {"name": "resultados", "path": "resultados.csv", "format": "csv",
             "schema": {"fields": [{"name": c, "type": tipos.get(c, "string")}
                                   for c in res.columns]}},
            {"name": "puntos", "path": "puntos.csv", "format": "csv",
             "schema": {"fields": [{"name": c, "type": tipos.get(c, "string")}
                                   for c in puntos.columns],
                        "primaryKey": "id"}},
        ],
    }
    salida = io.BytesIO()
    with zipfile.ZipFile(salida, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("datapackage.json", json.dumps(paquete, ensure_ascii=False, indent=1))
        z.writestr("resultados.csv", res.to_csv(index=False))
        z.writestr("puntos.csv", puntos.to_csv(index=False))
    return f"{env.base_nombre}-datos-abiertos.zip", salida.getvalue(), "application/zip"


_XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

# clave -> (etiqueta, función, sufijo del archivo, tipo MIME). El nombre y el
# tipo se conocen sin generar el archivo: la interfaz los necesita para
# dibujar el botón, y el contenido recién se arma cuando alguien lo pide.
EXPORTADORES = {
    "paquete_tad": ("Paquete completo para el expediente (.zip)", paquete_tad,
                    "paquete-expediente.zip", "application/zip"),
    "informe_html": ("Informe de monitoreo (HTML imprimible a PDF)", informe_html,
                     "informe.html", "text/html"),
    "planilla_xlsx": ("Resultados por componente (.xlsx)", planilla_xlsx,
                      "resultados.xlsx", _XLSX),
    "kmz": ("Puntos de monitoreo (.kmz)", puntos_kmz, "puntos.kmz",
            "application/vnd.google-earth.kmz"),
    "shp": ("Puntos de monitoreo (Shape POSGAR 94, .zip)", puntos_shp, "puntos-shp.zip",
            "application/zip"),
    "geojson": ("Puntos y estado (.geojson)", puntos_geojson, "puntos.geojson",
                "application/geo+json"),
    "sensorthings": ("Observaciones OGC SensorThings (.json)", sensorthings,
                     "sensorthings.json", "application/json"),
    "datos_abiertos": ("Datos abiertos Frictionless (.zip)", datos_abiertos,
                       "datos-abiertos.zip", "application/zip"),
}


def exportar(clave_exportador, env):
    """(nombre_archivo, bytes, mime) para un exportador del registro."""
    return EXPORTADORES[clave_exportador][1](env)


def nombre_archivo(clave_exportador, env):
    return f"{env.base_nombre}-{EXPORTADORES[clave_exportador][2]}"


def contenido(clave_exportador, env):
    """Solo los bytes: es lo que pide un botón de descarga diferida."""
    return exportar(clave_exportador, env)[1]


# -------------------------------------------------------------------- API ---
# Para el día en que una autoridad publique un punto de acceso. El perfil del
# canal dice la URL y en qué variable de entorno está el token; el token nunca
# se escribe en el perfil ni en el repositorio.

def solicitud_api(env):
    """La solicitud HTTP que se enviaría, con el token oculto."""
    api = (env.canal or {}).get("api") or {}
    cuerpo = _sensorthings_dict(env)
    return {
        "metodo": "POST",
        "url": api.get("url") or "(la autoridad todavía no publicó el punto de acceso)",
        "encabezados": {"Content-Type": "application/json",
                        "Authorization": f"Bearer ${{{api.get('token_env', 'TOKEN')}}}"},
        "cuerpo": cuerpo,
        "lista_para_enviar": bool(api.get("url")) and bool(os.environ.get(
            api.get("token_env", ""), "")),
    }


def enviar(env, tiempo_maximo=30):
    """Envía la campaña al canal por API. Solo si el canal tiene URL y token."""
    api = (env.canal or {}).get("api") or {}
    url, token = api.get("url"), os.environ.get(api.get("token_env", ""), "")
    if not url:
        raise RuntimeError("El canal no tiene punto de acceso configurado.")
    if not token:
        raise RuntimeError(f"Falta el token en la variable de entorno {api.get('token_env')}.")
    datos = json.dumps(_sensorthings_dict(env), ensure_ascii=False).encode("utf-8")
    pedido = urllib.request.Request(url, data=datos, method="POST", headers={
        "Content-Type": "application/json", "Authorization": f"Bearer {token}"})
    with urllib.request.urlopen(pedido, timeout=tiempo_maximo) as respuesta:
        return respuesta.status, respuesta.read().decode("utf-8", errors="replace")
