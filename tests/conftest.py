import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))


@pytest.fixture(scope="session")
def escenario():
    from core.datos import generar_escenario
    return generar_escenario()


@pytest.fixture(scope="session")
def evaluado(escenario):
    from core.validacion import evaluar, linea_base
    base = linea_base(escenario["resultados"], escenario["campanias"])
    return base, evaluar(escenario["resultados"], escenario["puntos"], base)
