"""Semáforo y control de carga."""

from datetime import date, timedelta

import pandas as pd
import pytest

from core.validacion import (ATENCION, CUMPLE, FONDO_NATURAL, NO_CONCLUYENTE, SIN_REFERENCIA,
                             SUPERA, controles, evaluar_uno, tendencia_anual)


def base(minimo, maximo, n=6):
    return {"n": n, "minimo": minimo, "maximo": maximo, "mediana": (minimo + maximo) / 2}


def test_supera_nivel_guia():
    r = evaluar_uno(0.04, "", "zinc", "vida_acuatica")
    assert r["estado"] == SUPERA and r["nivel_guia"] == 0.03


def test_fondo_natural():
    # La laguna ya tenía 0,10-0,14 mg/L de arsénico antes del proyecto.
    r = evaluar_uno(0.12, "", "arsenico", "vida_acuatica", base(0.10, 0.14))
    assert r["estado"] == FONDO_NATURAL


def test_supera_fuera_del_fondo_natural():
    r = evaluar_uno(0.30, "", "arsenico", "vida_acuatica", base(0.10, 0.14))
    assert r["estado"] == SUPERA


def test_no_detectado_con_limite_mayor_al_nivel_guia():
    r = evaluar_uno(0.005, "<", "cromo", "vida_acuatica")
    assert r["estado"] == NO_CONCLUYENTE


def test_no_detectado_alcanza():
    assert evaluar_uno(0.001, "<", "cromo", "vida_acuatica")["estado"] == CUMPLE


def test_dureza_elige_el_tramo():
    sin_dureza = evaluar_uno(0.003, "", "cobre", "vida_acuatica")
    assert sin_dureza["estado"] == NO_CONCLUYENTE
    blanda = evaluar_uno(0.003, "", "cobre", "vida_acuatica", dureza=50)
    assert blanda["estado"] == SUPERA                      # tramo ≤ 60: 0,002
    dura = evaluar_uno(0.003, "", "cobre", "vida_acuatica", dureza=260)
    assert dura["estado"] == CUMPLE and dura["nivel_guia"] == 0.004


def test_tramo_sin_valor_confirmado_compara_con_base():
    r = evaluar_uno(0.003, "", "plomo", "vida_acuatica", base(0.002, 0.004), dureza=260)
    assert r["estado"] == CUMPLE and "Sin nivel guía confirmado" in r["motivo"]


def test_atencion_al_80_por_ciento():
    r = evaluar_uno(4.4, "", "boro", "bebida_ganado", base(2.5, 3.5))
    assert r["estado"] == ATENCION and "88%" in r["motivo"]


def test_ph_normal_no_es_atencion():
    assert evaluar_uno(8.1, "", "ph", "fuente_bebida", base(7.9, 8.3))["estado"] == CUMPLE


def test_sin_nivel_guia_usa_la_linea_de_base():
    adentro = evaluar_uno(8.1, "", "nivel_freatico", "bebida_ganado", base(7.9, 8.1))
    afuera = evaluar_uno(9.5, "", "nivel_freatico", "bebida_ganado", base(7.9, 8.1))
    assert adentro["estado"] == CUMPLE and afuera["estado"] == ATENCION


def test_sin_referencia():
    assert evaluar_uno(5, "", "nivel_sonoro", None)["estado"] == SIN_REFERENCIA


def test_sugiere_corregir_unidad():
    r = evaluar_uno(45, "", "arsenico", "bebida_ganado", base(0.06, 0.10))
    assert r["valor_sugerido"] == pytest.approx(0.045)
    assert "µg/L" in r["sugerencia"]


def test_controles_de_carga():
    hoy = date(2026, 10, 2)
    filas = pd.DataFrame([
        {"punto_id": "P1", "fecha": hoy, "parametro": "ph", "valor": 15.0, "error": None},
        {"punto_id": "P1", "fecha": hoy, "parametro": "zinc", "valor": 0.01, "error": None},
        {"punto_id": "P1", "fecha": hoy, "parametro": "zinc", "valor": 0.02, "error": None},
        {"punto_id": "P2", "fecha": hoy + timedelta(days=3), "parametro": "zinc",
         "valor": 0.01, "error": None},
        {"punto_id": "P9", "fecha": hoy, "parametro": None, "valor": None,
         "error": "punto no registrado: «P9»"},
    ])
    problemas = controles(filas, hoy)
    textos = " | ".join(p["problema"] for p in problemas)
    assert "pH fuera de escala" in textos
    assert textos.count("duplicado") == 2
    assert "futura" in textos and "no registrado" in textos
    assert all(p["gravedad"] == "bloqueante" for p in problemas)


def test_tendencia_anual():
    fechas = [date(2025, 1, 1) + timedelta(days=91 * i) for i in range(8)]
    valores = [8 + 0.17 * i for i in range(8)]
    assert tendencia_anual(fechas, valores) == pytest.approx(0.68, abs=0.01)
    assert tendencia_anual(fechas[:3], valores[:3]) is None


def test_escenario_cuenta_su_historia(evaluado):
    """Los fenómenos sembrados en los datos sintéticos aparecen donde deben."""
    _, ev = evaluado

    def estados(punto, parametro):
        return set(ev[(ev["punto_id"] == punto) & (ev["parametro"] == parametro)]["estado"])

    assert SUPERA in estados("CC-AS-02", "zinc")            # sube aguas abajo del dique
    assert estados("SA-AS-02", "arsenico") == {FONDO_NATURAL}   # arsénico natural
    assert estados("SB-AS-02", "cromo") == {NO_CONCLUYENTE}     # el LD del laboratorio
    assert ATENCION in estados("SA-SB-02", "nivel_freatico")     # descenso del nivel
    # Ninguna superación queda sin explicar en una campaña aprobada.
    assert set(ev[ev["estado"] == SUPERA]["punto_id"]) == {"CC-AS-02"}
