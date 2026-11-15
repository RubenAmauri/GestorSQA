"""Pruebas de LimiteAtomico en serie (RNF-05; defecto #41).

La prueba con peticiones simultáneas está en test_limite_concurrente.py.
"""

from unittest import mock

import pytest
from rest_framework.test import APIRequestFactory

from apps.core.models import HistorialDeIntentos
from apps.core.throttling import LimiteAtomico

pytestmark = pytest.mark.django_db

LOGIN = "/api/auth/login/"
CLAVE_LOGIN = "throttle_inicio_sesion_127.0.0.1"


def intento(api_client):
    datos = {"email": "nadie@correo.com", "password": "equivocada"}
    return api_client.post(LOGIN, datos, format="json")


def test_la_fila_solo_guarda_las_marcas_de_la_ventana(api_client):
    """Al guardar se descartan las marcas viejas: la fila no crece con el tiempo."""
    with mock.patch("rest_framework.throttling.SimpleRateThrottle.timer", return_value=1000.0):
        for _ in range(5):
            intento(api_client)
        assert intento(api_client).status_code == 429
    fila = HistorialDeIntentos.objects.get(clave=CLAVE_LOGIN)
    assert len(fila.marcas) == 5  # el intento rechazado no se cuenta

    with mock.patch("rest_framework.throttling.SimpleRateThrottle.timer", return_value=1061.0):
        assert intento(api_client).status_code == 400
    fila.refresh_from_db()
    assert fila.marcas == [1061.0]
    assert str(fila) == f"{CLAVE_LOGIN} (1 intentos en la ventana)"
    assert HistorialDeIntentos.objects.count() == 1


class SinTasa(LimiteAtomico):
    def get_rate(self):
        return None


class SinClave(LimiteAtomico):
    rate = "1/min"

    def get_cache_key(self, request, view):
        return None


@pytest.mark.parametrize("limite", [SinTasa, SinClave])
def test_sin_tasa_o_sin_clave_no_limita_ni_guarda_nada(limite):
    """Igual que en DRF: sin tasa o sin clave no hay límite que aplicar."""
    request = APIRequestFactory().post(LOGIN)
    throttle = limite()
    assert all(throttle.allow_request(request, None) for _ in range(3))
    assert not HistorialDeIntentos.objects.exists()
