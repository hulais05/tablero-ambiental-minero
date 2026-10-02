"""Quién puede hacer qué con una campaña."""

import pandas as pd
import pytest

from core.datos import nueva_campania
from core.flujo import (APROBADA, BORRADOR, OBSERVADA, PRESENTADA, faltantes_para_presentar,
                        publicadas, transicionar)
from core.validacion import CUMPLE, SUPERA


@pytest.fixture
def campania():
    from datetime import date
    return nueva_campania("SALAR-A", date(2026, 9, 3))


def test_circuito_completo(campania):
    assert campania["estado"] == BORRADOR
    transicionar(campania, PRESENTADA, "Responsable", "empresa")
    transicionar(campania, OBSERVADA, "Revisor", "autoridad", "Falta la cadena de custodia.")
    transicionar(campania, PRESENTADA, "Responsable", "empresa", "Se adjuntó.")
    transicionar(campania, APROBADA, "Revisor", "autoridad")
    assert campania["estado"] == APROBADA
    assert [h["accion"] for h in campania["historial"]] == [
        "Presentó la campaña", "Observó la campaña", "Volvió a presentar con correcciones",
        "Aprobó y publicó"]
    assert publicadas({campania["id"]: campania}) == {campania["id"]}


def test_la_empresa_no_aprueba(campania):
    transicionar(campania, PRESENTADA, "Responsable", "empresa")
    with pytest.raises(PermissionError):
        transicionar(campania, APROBADA, "Responsable", "empresa")


def test_no_se_saltea_la_revision(campania):
    with pytest.raises(ValueError):
        transicionar(campania, APROBADA, "Revisor", "autoridad")


def test_firma_y_observacion_obligatorias(campania):
    with pytest.raises(ValueError, match="Falta el nombre"):
        transicionar(campania, PRESENTADA, "  ", "empresa")
    transicionar(campania, PRESENTADA, "Responsable", "empresa")
    with pytest.raises(ValueError, match="qué hay que corregir"):
        transicionar(campania, OBSERVADA, "Revisor", "autoridad", "")


def test_faltantes_para_presentar():
    ev = pd.DataFrame([
        {"punto_id": "SA-AS-01", "parametro": "zinc", "estado": SUPERA},
        {"punto_id": "SA-AS-01", "parametro": "boro", "estado": CUMPLE},
    ])
    falta = faltantes_para_presentar(ev, [], {})
    assert len(falta) == 1 and "SA-AS-01 · Zinc" in falta[0]
    assert faltantes_para_presentar(ev, [], {"SA-AS-01|zinc": "Causa y acción."}) == []
    bloqueo = [{"gravedad": "bloqueante", "problema": "x", "indice": 0}]
    assert any("error" in f for f in faltantes_para_presentar(
        ev, bloqueo, {"SA-AS-01|zinc": "ok"}))
