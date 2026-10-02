"""Los datos reales de datos/: completos, coherentes y con su fuente."""

import pandas as pd
import pytest

from core.catalogo import MATRICES, PARAMETROS, USOS, unidad_canonica
from core.escenario import DATOS, cargar, disponibles
from core.validacion import evaluar, linea_base

pytestmark = pytest.mark.skipif(not disponibles(), reason="no hay datos reales en datos/")


@pytest.fixture(scope="module")
def esc():
    return cargar(disponibles()[0])


def test_cada_resultado_tiene_punto_parametro_y_fuente(esc):
    res = pd.concat([esc["resultados"], esc["demo"]])
    assert set(res["punto_id"]) <= set(esc["puntos"]["id"])
    assert set(res["parametro"]) <= set(PARAMETROS)
    assert res["fuente"].str.len().gt(10).all()
    unidades = res.apply(lambda r: unidad_canonica(r["parametro"], r["matriz"]), axis=1)
    assert (res["unidad"] == unidades).all()


def test_puntos_con_matriz_uso_y_coordenadas(esc):
    p = esc["puntos"]
    assert p["id"].is_unique
    assert set(p["matriz"]) <= set(MATRICES)
    assert set(p["uso"].dropna()) <= set(USOS)
    assert p["lat"].between(-56, -21).all() and p["lon"].between(-74, -53).all()


def test_la_demo_es_una_campania_aparte(esc):
    meta = esc["meta"]
    assert meta["real"] and not esc["demo"].empty
    assert meta["demo_campania"] not in esc["campanias"]
    assert set(esc["demo"]["campania_id"]) == {meta["demo_campania"]}


def test_el_semaforo_evalua_todo_el_historial(esc):
    base = linea_base(esc["resultados"], esc["campanias"])
    ev = evaluar(esc["resultados"], esc["puntos"], base)
    assert ev["estado"].notna().all()


def test_el_archivo_de_fuentes_existe():
    for carpeta in disponibles():
        assert (DATOS / carpeta / "FUENTES.md").exists()
