"""Lectura de planillas de laboratorio: formatos, números, unidades y errores."""

import pytest

from core.catalogo import convertir, parametro_por_nombre
from core.datos import (interpretar, leer_archivo, leer_valor, libro_laboratorio_ejemplo,
                        separar_unidad)


@pytest.mark.parametrize("crudo, esperado", [
    ("0,012", ("", 0.012)),
    ("<0,005", ("<", 0.005)),
    ("< 0.005", ("<", 0.005)),
    ("ND", ("<", None)),
    ("n.d.", ("<", None)),
    (45, ("", 45.0)),
    ("1.234,5", ("", 1234.5)),
    ("1,234.5", ("", 1234.5)),
    ("12 (est.)", ("", 12.0)),
    ("1,2E-03", ("", 0.0012)),
])
def test_leer_valor(crudo, esperado):
    calificador, valor = leer_valor(crudo)
    assert calificador == esperado[0]
    assert valor == (pytest.approx(esperado[1]) if esperado[1] is not None else None)


@pytest.mark.parametrize("vacio", ["", "s/d", "-", None, float("nan")])
def test_celda_sin_dato(vacio):
    assert leer_valor(vacio) is None


def test_valor_ilegible():
    with pytest.raises(ValueError):
        leer_valor("ver observaciones")


@pytest.mark.parametrize("encabezado, esperado", [
    ("As (mg/L)", ("As", "mg/L")),
    ("PM10 24 h (µg/m³)", ("PM10 24 h", "µg/m³")),
    ("Dureza total [mg/L CaCO3]", ("Dureza total", "mg/L CaCO3")),
    ("As mg/L", ("As", "mg/L")),
    ("pH", ("pH", None)),
])
def test_separar_unidad(encabezado, esperado):
    assert separar_unidad(encabezado) == esperado


@pytest.mark.parametrize("nombre, codigo", [
    ("Arsénico total", "arsenico"), ("CE", "conductividad"), ("PM10 24 h", "pm10"),
    ("Boro soluble", "boro"), ("Cr total", "cromo"), ("LAeq", "nivel_sonoro"),
    ("Nivel freático", "nivel_freatico"), ("Hora", None), ("Densidad", None),
])
def test_parametro_por_nombre(nombre, codigo):
    assert parametro_por_nombre(nombre) == codigo


def test_convertir_unidades():
    assert convertir(45, "µg/L", "arsenico", "agua_superficial") == (pytest.approx(0.045), "mg/L")
    assert convertir(336, "g/L", "sdt", "salmuera") == (336_000, "mg/L")
    assert convertir(2, "ppm", "arsenico", "suelo") == (2, "mg/kg")
    assert convertir(260, "mg/L CaCO3", "dureza", "agua_superficial") == (260, "mg/L")
    with pytest.raises(ValueError, match="no corresponde"):
        convertir(3, "mg/L", "arsenico", "suelo")
    with pytest.raises(ValueError, match="desconocida"):
        convertir(3, "furlongs", "arsenico", "agua_superficial")


def test_planilla_de_ejemplo(escenario):
    tablas = leer_archivo("lab.xlsx", libro_laboratorio_ejemplo(escenario))
    puntos_a = escenario["puntos"][escenario["puntos"]["proyecto_id"] == "SALAR-A"]
    res, informe = interpretar(tablas, puntos_a)
    assert set(informe["formatos"].values()) == {"ancha"}
    assert len(informe["formatos"]) == 4
    # El punto tipeado mal se informa una sola vez, con hoja y fila.
    errores = res[res["error"].notna()]
    assert len(errores) == 1
    assert "SA-AS-9" in errores.iloc[0]["error"] and errores.iloc[0]["hoja"] == "Aguas"
    # La densidad no es un parámetro: se ignora y se dice.
    assert any("Densidad" in c for c in informe["ignoradas"])
    # SDT de la salmuera en g/L, guardado en mg/L.
    sdt = res[(res["punto_id"] == "SA-SM-01") & (res["parametro"] == "sdt")].iloc[0]
    assert sdt["unidad"] == "mg/L" and sdt["valor"] > 100_000
    # El "s/d" no genera fila: no hay dato que cargar.
    assert res[(res["punto_id"] == "SA-SU-01") & (res["parametro"] == "mercurio")].empty
    # Lo no detectado conserva el "<" y su límite de detección.
    nd = res[res["calificador"] == "<"]
    assert not nd.empty and (nd["ld"] == nd["valor"]).all()


def test_punto_de_otro_proyecto_es_error(escenario):
    tablas = leer_archivo("lab.xlsx", libro_laboratorio_ejemplo(escenario))
    puntos_b = escenario["puntos"][escenario["puntos"]["proyecto_id"] == "SALAR-B"]
    res, _ = interpretar(tablas, puntos_b)
    assert res["error"].notna().all()


def test_formato_largo_csv(escenario):
    csv = ("Punto;Fecha de muestreo;Analito;Resultado;Unidad;LD\n"
           "SA-AS-01;03/09/2026;Arsénico;45;µg/L;5\n"
           "SA-AS-01;03/09/2026;Mercurio;<0,001;mg/L;0,001\n"
           "SA-AS-01;03/09/2026;Talio;0,2;mg/L;\n").encode("cp1252", errors="replace")
    tablas = leer_archivo("lab.csv", csv)
    res, informe = interpretar(tablas, escenario["puntos"])
    assert informe["formatos"] == {"CSV": "larga"}
    arsenico = res[res["parametro"] == "arsenico"].iloc[0]
    assert arsenico["valor"] == pytest.approx(0.045) and arsenico["ld"] == pytest.approx(0.005)
    assert res[res["parametro"] == "mercurio"].iloc[0]["calificador"] == "<"
    assert "no reconocido" in res[res["parametro"].isna()].iloc[0]["error"]
