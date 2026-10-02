"""Salidas a los canales oficiales y estándares abiertos."""

import hashlib
import io
import json
import zipfile
from xml.etree import ElementTree

import pytest
import shapefile

from core.conectores import (EXPORTADORES, Envio, cargar_perfiles, exportar,
                             faja_gauss_kruger, gauss_kruger, nombre_archivo, prj_posgar94,
                             solicitud_api)
from core.datos import PROYECTOS
from core.validacion import hay

# Referencias calculadas con PROJ (pyproj, EPSG 4326 → 22183 y 22182).
REFERENCIAS = [
    (-23.80, -66.45, 3, 3454140.896, 7368755.756),
]


@pytest.fixture(scope="module")
def envio(escenario, evaluado):
    _, ev = evaluado
    cid = "CERRO-C-2026-03"
    evc = ev[(ev["campania_id"] == cid) & ev["estado"].map(hay)]
    perfil = next(p for p in cargar_perfiles() if p["id"] == "jujuy")
    return Envio(escenario["campanias"][cid], PROYECTOS[2],
                 escenario["puntos"][escenario["puntos"]["id"].isin(evc["punto_id"])], evc,
                 perfil, perfil["canales"][0])


@pytest.mark.parametrize("lat, lon, faja, este, norte", REFERENCIAS)
def test_gauss_kruger_contra_referencia(lat, lon, faja, este, norte):
    e, n, f = gauss_kruger(lat, lon)
    assert f == faja
    assert e == pytest.approx(este, abs=0.01) and n == pytest.approx(norte, abs=0.01)


def test_gauss_kruger_contra_pyproj():
    pyproj = pytest.importorskip("pyproj")
    for faja, lon0 in ((2, -69), (3, -66), (4, -63)):
        t = pyproj.Transformer.from_crs(4326, 22180 + faja, always_xy=True)
        for lat in (-22.0, -24.5, -27.0):
            for dlon in (-1.4, 0.0, 1.4):
                e, n, _ = gauss_kruger(lat, lon0 + dlon, faja)
                pe, pn = t.transform(lon0 + dlon, lat)
                assert abs(e - pe) < 0.01 and abs(n - pn) < 0.01


def test_faja():
    assert faja_gauss_kruger(-66.45) == 3 and faja_gauss_kruger(-67.6) == 2
    assert "Central_Meridian\",-66.0" in prj_posgar94(3)


def test_todos_los_exportadores(envio):
    for clave, (_, _, sufijo, mime) in EXPORTADORES.items():
        nombre, datos, tipo = exportar(clave, envio)
        assert datos and nombre == nombre_archivo(clave, envio) and tipo == mime


def test_kmz_es_kml_valido(envio):
    _, datos, _ = exportar("kmz", envio)
    kml = zipfile.ZipFile(io.BytesIO(datos)).read("doc.kml")
    raiz = ElementTree.fromstring(kml)
    marcas = raiz.findall(".//{http://www.opengis.net/kml/2.2}Placemark")
    assert len(marcas) == len(envio.puntos)


def test_shapefile_en_posgar94(envio):
    _, datos, _ = exportar("shp", envio)
    z = zipfile.ZipFile(io.BytesIO(datos))
    base = next(n[:-4] for n in z.namelist() if n.endswith(".shp"))
    lector = shapefile.Reader(shp=io.BytesIO(z.read(f"{base}.shp")),
                              shx=io.BytesIO(z.read(f"{base}.shx")),
                              dbf=io.BytesIO(z.read(f"{base}.dbf")))
    assert len(lector.shapes()) == len(envio.puntos)
    x, y = lector.shapes()[0].points[0]
    assert 3_000_000 < x < 4_000_000 and 7_000_000 < y < 8_000_000
    assert "POSGAR_1994_Argentina_Zone_3" in z.read(f"{base}.prj").decode()


def test_paquete_tad_con_manifiesto(envio):
    _, datos, _ = exportar("paquete_tad", envio)
    z = zipfile.ZipFile(io.BytesIO(datos))
    manifiesto = json.loads(z.read("manifiesto.json"))
    for archivo in manifiesto["archivos"]:
        assert hashlib.sha256(z.read(archivo["nombre"])).hexdigest() == archivo["sha256"]
    leame = z.read("LEAME.txt").decode()
    assert "Cadena de custodia" in leame              # lo que la empresa adjunta aparte
    nombres = z.namelist()
    assert any(n.endswith(".kmz") for n in nombres) and any("shp" in n for n in nombres)


def test_datos_abiertos_frictionless(envio):
    _, datos, _ = exportar("datos_abiertos", envio)
    z = zipfile.ZipFile(io.BytesIO(datos))
    paquete = json.loads(z.read("datapackage.json"))
    assert {r["path"] for r in paquete["resources"]} == {"resultados.csv", "puntos.csv"}


def test_sensorthings(envio):
    _, datos, _ = exportar("sensorthings", envio)
    things = json.loads(datos)["Things"]
    assert len(things) == len(envio.puntos)
    ds = things[0]["Datastreams"][0]
    assert {"unitOfMeasurement", "ObservedProperty", "Sensor", "Observations"} <= set(ds)
    assert things[0]["Locations"][0]["location"]["type"] == "Point"


def test_api_sin_punto_de_acceso_no_envia(envio):
    canal = {"id": "x", "api": {"url": None, "token_env": "TOKEN_QUE_NO_EXISTE"}}
    s = solicitud_api(Envio(envio.campania, envio.proyecto, envio.puntos, envio.evaluados,
                            canal=canal))
    assert s["lista_para_enviar"] is False
    assert s["encabezados"]["Authorization"] == "Bearer ${TOKEN_QUE_NO_EXISTE}"


def test_perfiles_coherentes():
    perfiles = cargar_perfiles()
    assert [p["id"] for p in perfiles][:2] == ["jujuy", "salta"]
    for p in perfiles:
        for canal in p["canales"]:
            assert {"id", "nombre", "tipo", "estado", "descripcion"} <= set(canal)
            assert all(e in EXPORTADORES for e in canal.get("entregables", []))
