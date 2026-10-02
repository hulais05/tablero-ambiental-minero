"""La app de punta a punta: cargar, corregir, presentar, aprobar, publicar."""

from pathlib import Path

import pytest

AppTest = pytest.importorskip("streamlit.testing.v1").AppTest
APP = str(Path(__file__).resolve().parent.parent / "app.py")


def boton(at, inicio):
    return next(b for b in at.button if b.label.startswith(inicio))


def test_arranca_sin_errores():
    at = AppTest.from_file(APP, default_timeout=90).run()
    assert not at.exception
    assert [t.label for t in at.tabs][0] == "🌎 Ciudadanía"


def test_recorrido_completo():
    at = AppTest.from_file(APP, default_timeout=90).run()
    boton(at, "Usar la planilla de ejemplo").click().run()
    presentar = boton(at, "Presentar la campaña")
    assert presentar.disabled                     # error de carga y superación sin justificar
    boton(at, "Corregir a").click().run()         # 45 mg/L → 0,045 mg/L
    boton(at, "Descartar fila").click().run()     # el punto que no existe
    boton(at, "Presentar la campaña").click().run()
    assert not at.exception
    assert at.session_state.campanias["SALAR-A-2026-09"]["estado"] == "PRESENTADA"

    revision = next(s for s in at.selectbox if s.label == "Campaña")
    revision.select("SALAR-A-2026-09").run()
    boton(at, "Aprobar y publicar").click().run()
    assert not at.exception
    campania = at.session_state.campanias["SALAR-A-2026-09"]
    assert campania["estado"] == "APROBADA"
    assert [h["rol"] for h in campania["historial"]] == ["empresa", "autoridad"]


def test_observar_y_volver_a_presentar():
    at = AppTest.from_file(APP, default_timeout=90).run()
    revision = next(s for s in at.selectbox if s.label == "Campaña")
    revision.select("SALAR-B-2026-09").run()
    boton(at, "Observar").click().run()
    assert at.error and "corregir" in at.error[0].value     # observar exige comentario
    at.text_area(key="aut_com_SALAR-B-2026-09").input("Falta la cadena de custodia del aire.")
    boton(at, "Observar").click().run()
    assert at.session_state.campanias["SALAR-B-2026-09"]["estado"] == "OBSERVADA"
    assert any("cadena de custodia" in w.value for w in at.warning)
    boton(at, "Volver a presentar SALAR-B-2026-09").click().run()
    assert at.session_state.campanias["SALAR-B-2026-09"]["estado"] == "PRESENTADA"


def test_conectores_y_filtros():
    at = AppTest.from_file(APP, default_timeout=90).run()
    perfil = next(s for s in at.selectbox if s.label == "Jurisdicción")
    perfil.select("salta").run()
    assert not at.exception
    assert any("todavía no publicó el punto de acceso" in m.value for m in at.markdown)
    envio = next(b for b in at.button if b.label == "Enviar por API")
    assert envio.disabled
    proyecto = next(s for s in at.selectbox if s.label == "Proyecto")
    proyecto.select("CERRO-C").run()
    parametro = next(s for s in at.selectbox if s.label == "Parámetro")
    parametro.select("zinc").run()
    assert not at.exception
