"""
De dónde salen los datos que muestra el tablero.

Si existe una carpeta datos/<proyecto>/ con su proyecto.json, el tablero
trabaja con esos datos reales. Si no, usa el escenario sintético de
core/datos.py, que sigue siendo la base de las pruebas del motor.

Los datos reales no se generan: se transcriben de su fuente (informe, tabla,
página) y cada resultado lleva esa cita. Lo que el tablero agrega —estado,
motivo, nivel guía— se calcula, nunca se escribe a mano.
"""

import json
import os
from datetime import date, datetime, timedelta
from pathlib import Path

import pandas as pd

from .catalogo import MATRICES, PARAMETROS, USOS, unidad_canonica
from .datos import TIPO_BASE, TIPO_MAP, generar_escenario

DATOS = Path(__file__).resolve().parent.parent / "datos"

# Campos de texto de la interfaz que cambian con el escenario.
META_SINTETICO = {
    "real": False,
    "titulo": "Tablero Ambiental Minero",
    "subtitulo": "El circuito del MAIM de Jujuy —la empresa carga, la autoridad controla, la "
                 "ciudadanía consulta—, del lado de la empresa y con salida a cada canal oficial.",
    "aviso_datos": "⚠️ Datos sintéticos. Proyectos, empresas, comunidades, laboratorios y valores "
                   "son ficticios; las coordenadas no corresponden a ningún proyecto real.",
    "pie": "Prototipo · datos sintéticos",
    "firma_empresa": "Responsable ambiental · Empresa A S.A.",
    "firma_autoridad": "Revisor · Área de Control Ambiental",
    "demo_proyecto": "SALAR-A",
    "demo_fecha": "2026-09-03",
    "demo_boton": "Usar la planilla de ejemplo (Proyecto Salar A)",
    "demo_texto": "La del ejemplo es la de un laboratorio real en forma: cuatro hojas, "
                  "encabezados a su manera, coma decimal y «<0,005» para lo no detectado. "
                  "Trae cuatro errores sembrados para ver qué hace el sistema con ellos.",
    "demo_tipo": TIPO_MAP,
    "vencimientos": True,
    "perfil": None,
    "que_es_real": [
        "**Datos sintéticos.** Ninguna empresa, proyecto, comunidad, laboratorio ni valor es real.",
    ],
}


def disponibles():
    """Carpetas de datos reales que hay en datos/."""
    if not DATOS.exists():
        return []
    return sorted(d.name for d in DATOS.iterdir() if (d / "proyecto.json").exists())


def _fecha(x):
    if isinstance(x, date):
        return x
    return datetime.strptime(str(x)[:10], "%Y-%m-%d").date()


def _texto(x):
    return "" if x is None or (isinstance(x, float) and pd.isna(x)) else str(x)


def _renombrar(esc, ruta):
    """Nombres reales, para una presentación privada.

    El repositorio público lleva los datos con nombres genéricos. Quien tenga
    el archivo de nombres (fuera del repositorio) puede apuntarlo con la
    variable de entorno TABLERO_NOMBRES y ver el proyecto con su nombre. El
    archivo es un JSON {"texto genérico": "texto real"}.
    """
    reemplazos = json.loads(Path(ruta).read_text(encoding="utf-8"))
    orden = sorted(reemplazos, key=len, reverse=True)

    def cambiar(texto):
        if not isinstance(texto, str):
            return texto
        for k in orden:
            texto = texto.replace(k, reemplazos[k])
        return texto

    # Los identificadores no se tocan: atan resultados, campañas y puntos.
    ids = {"id", "punto_id", "proyecto_id", "campania_id", "puntos"}
    for clave_df in ("proyectos", "puntos", "componentes", "obligaciones", "programa"):
        df = esc.get(clave_df)
        if df is not None and not df.empty:
            esc[clave_df] = df.apply(lambda col: col.map(cambiar) if col.name not in ids
                                     and (col.dtype == object or
                                          pd.api.types.is_string_dtype(col)) else col)
    for c in esc["campanias"].values():
        for k in ("laboratorio", "consultora", "fuente", "descripcion"):
            c[k] = cambiar(c.get(k, ""))
        for h in c["historial"]:
            h["actor"], h["comentario"] = cambiar(h["actor"]), cambiar(h["comentario"])
    esc["meta"] = {k: (cambiar(v) if isinstance(v, str) else
                       [cambiar(x) for x in v] if isinstance(v, list) and
                       all(isinstance(x, str) for x in v) else v)
                   for k, v in esc["meta"].items()}
    return esc


def cargar(nombre=None):
    """Escenario completo: el real de datos/<nombre> o, si no hay, el sintético."""
    esc = _cargar(nombre)
    ruta = os.environ.get("TABLERO_NOMBRES")
    if ruta and esc["meta"].get("real") and Path(ruta).exists():
        esc = _renombrar(esc, ruta)
    return esc


def _cargar(nombre=None):
    # TABLERO_DATOS elige el conjunto: el nombre de una carpeta de datos/ o
    # "sintetico". Sin la variable, el primero que haya en datos/.
    nombre = nombre or os.environ.get("TABLERO_DATOS") or None
    if nombre == "sintetico":
        nombre = ""
    reales = disponibles()
    if nombre is None and reales:
        nombre = reales[0]
    if not nombre:
        esc = generar_escenario()
        esc["meta"] = dict(META_SINTETICO)
        esc.setdefault("componentes", pd.DataFrame())
        esc.setdefault("obligaciones", pd.DataFrame())
        esc.setdefault("programa", pd.DataFrame())
        return esc
    return cargar_real(DATOS / nombre)


def cargar_real(carpeta):
    carpeta = Path(carpeta)
    meta = json.loads((carpeta / "proyecto.json").read_text(encoding="utf-8"))
    proyecto = meta["proyecto"]
    pid = proyecto["id"]

    puntos = pd.read_csv(carpeta / "puntos.csv", dtype={"id": str})
    puntos["proyecto_id"] = pid
    puntos["uso"] = puntos["uso"].where(puntos["uso"].isin(USOS), None)
    desconocidas = set(puntos["matriz"]) - set(MATRICES)
    if desconocidas:
        raise ValueError(f"matrices desconocidas en puntos.csv: {sorted(desconocidas)}")

    res = pd.read_csv(carpeta / "resultados.csv", dtype={"punto_id": str, "campania_id": str,
                                                          "calificador": str})
    res["fecha"] = res["fecha"].map(_fecha)
    res["calificador"] = res["calificador"].fillna("")
    res["proyecto_id"] = pid
    res["matriz"] = res["punto_id"].map(dict(zip(puntos["id"], puntos["matriz"])))
    sin_punto = res[res["matriz"].isna()]
    if not sin_punto.empty:
        raise ValueError(f"resultados de puntos que no están en puntos.csv: "
                         f"{sorted(set(sin_punto['punto_id']))}")
    sin_param = set(res["parametro"]) - set(PARAMETROS)
    if sin_param:
        raise ValueError(f"parámetros sin catálogo: {sorted(sin_param)}")
    esperadas = res.apply(lambda r: unidad_canonica(r["parametro"], r["matriz"]), axis=1)
    malas = res[res["unidad"] != esperadas]
    if not malas.empty:
        fila = malas.iloc[0]
        raise ValueError(f"unidad no canónica en resultados.csv: {fila['parametro']} "
                         f"{fila['unidad']} (se espera {esperadas[malas.index[0]]})")

    cam = pd.read_csv(carpeta / "campanias.csv", dtype=str).fillna("")
    campanias = {}
    for c in cam.to_dict("records"):
        fecha = _fecha(c["fecha"])
        es_base = c.get("tipo", "") in ("", TIPO_BASE)
        historial = [
            {"fecha_hora": datetime.combine(fecha, datetime.min.time()) + timedelta(days=30),
             "actor": c.get("presento") or meta.get("firma_empresa", "Empresa"),
             "rol": "empresa", "accion": "Presentó la campaña", "estado": "PRESENTADA",
             "comentario": c.get("fuente", "")},
            {"fecha_hora": datetime.combine(fecha, datetime.min.time()) + timedelta(days=31),
             "actor": c.get("aprobo") or "Autoridad de aplicación", "rol": "autoridad",
             "accion": "Aprobó y publicó", "estado": "APROBADA",
             "comentario": c.get("nota_aprobacion", "")},
        ]
        campanias[c["id"]] = {
            "id": c["id"], "proyecto_id": pid, "fecha": fecha,
            "tipo": TIPO_BASE if es_base else c["tipo"],
            "laboratorio": c.get("laboratorio") or "s/d",
            "acreditacion": c.get("acreditacion") or "s/d",
            "consultora": c.get("consultora") or "s/d",
            "participantes": [x for x in c.get("participantes", "").split(";") if x],
            "estado": "APROBADA", "historial": historial, "justificaciones": {},
            "fuente": c.get("fuente", ""), "descripcion": c.get("descripcion", ""),
        }
    huerfanas = set(res["campania_id"]) - set(campanias)
    if huerfanas:
        raise ValueError(f"resultados de campañas que no están en campanias.csv: "
                         f"{sorted(huerfanas)}")

    demo_id = meta.get("demo_campania")
    demo = res[res["campania_id"] == demo_id].reset_index(drop=True) if demo_id else res.iloc[0:0]
    if demo_id:
        campanias.pop(demo_id, None)

    def opcional(archivo):
        ruta = carpeta / archivo
        return pd.read_csv(ruta, dtype=str).fillna("") if ruta.exists() else pd.DataFrame()

    componentes = opcional("componentes.csv")
    if not componentes.empty:
        componentes["lat"] = componentes["lat"].astype(float)
        componentes["lon"] = componentes["lon"].astype(float)
    # Contornos (propiedades mineras): un polígono por id, vértices en orden.
    vertices = opcional("contornos.csv")
    contornos = pd.DataFrame(columns=["poligono", "camino"])
    if not vertices.empty:
        vertices = vertices.astype({"orden": int, "lat": float, "lon": float})
        contornos = pd.DataFrame([
            {"poligono": pid_, "camino": [[r.lon, r.lat] for r in g.sort_values("orden").itertuples()]}
            for pid_, g in vertices.groupby("poligono", sort=False)])

    textos = {k: v for k, v in META_SINTETICO.items()}
    textos.update(meta.get("textos", {}))
    textos["real"] = True
    textos["errores_demo"] = meta.get("errores_demo", [])
    textos["demo_proyecto"] = pid
    textos["demo_campania"] = demo_id
    if demo_id and not demo.empty:
        textos["demo_fecha"] = str(demo["fecha"].min())

    return {
        "proyectos": pd.DataFrame([proyecto]),
        "puntos": puntos,
        "campanias": campanias,
        "resultados": res[res["campania_id"] != demo_id].reset_index(drop=True),
        "demo": demo,
        "demo_campania": meta.get("demo_campania_datos", {}),
        "componentes": componentes,
        "contornos": contornos,
        "obligaciones": opcional("obligaciones.csv"),
        "programa": opcional("programa.csv"),
        "meta": textos,
    }
