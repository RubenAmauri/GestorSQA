"""Regresión del defecto #41: el límite de intentos con peticiones simultáneas (RNF-05).

Varias peticiones salen a la vez (threading.Barrier), cada una en su hilo y con su propia
conexión a la base de datos, y se cuenta cuántas pasan el límite. El tiempo está fijo,
así que todas caen en la misma ventana y el resultado es exacto.

Necesita escrituras concurrentes reales: con SQLite en memoria (pruebas locales) se omite,
y la CI la corre contra MariaDB.
"""

import threading
from unittest import mock

import pytest
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.db import connection
from rest_framework.test import APIClient

pytestmark = [
    pytest.mark.django_db(transaction=True),
    pytest.mark.skipif(
        connection.vendor == "sqlite",
        reason="Requiere escrituras concurrentes reales; corre en la CI con MariaDB.",
    ),
]

AHORA = 1_000_000.0


@pytest.fixture(autouse=True)
def cache_limpia():
    """Con transaction=True los datos se confirman: la caché no se limpia sola."""
    cache.clear()
    yield
    cache.clear()


def en_paralelo(peticiones: int, hacer_peticion) -> list[int]:
    """Lanza las peticiones a la vez y devuelve sus códigos de respuesta."""
    salida = threading.Barrier(peticiones)
    codigos: list[int] = []
    errores: list[BaseException] = []
    candado = threading.Lock()

    def trabajador() -> None:
        try:
            salida.wait()
            codigo = hacer_peticion()
            with candado:
                codigos.append(codigo)
        except BaseException as error:  # noqa: BLE001 - se reporta en el hilo principal
            with candado:
                errores.append(error)
        finally:
            connection.close()  # cada hilo abre su propia conexión

    hilos = [threading.Thread(target=trabajador) for _ in range(peticiones)]
    with mock.patch("rest_framework.throttling.SimpleRateThrottle.timer", return_value=AHORA):
        for hilo in hilos:
            hilo.start()
        for hilo in hilos:
            hilo.join(timeout=60)
    assert not errores, errores
    return codigos


def test_pr_rnf05_02_inicios_de_sesion_simultaneos_respetan_el_limite():
    """PR-RNF05-02 (#41): 10 inicios de sesión a la vez desde una IP; solo pasan 5."""

    def iniciar_sesion() -> int:
        datos = {"email": "nadie@correo.com", "password": "equivocada"}
        return APIClient().post("/api/auth/login/", datos, format="json").status_code

    codigos = en_paralelo(10, iniciar_sesion)

    assert sorted(codigos) == [400] * 5 + [429] * 5


def test_uniones_simultaneas_respetan_el_limite():
    """RNF-05 (#41): 15 intentos de unión a la vez del mismo usuario; solo pasan 10."""
    # Sin contraseña: force_authenticate no la necesita.
    usuario = get_user_model().objects.create_user("ana@correo.com", None)

    def unirse() -> int:
        cliente = APIClient()
        cliente.force_authenticate(usuario)
        respuesta = cliente.post("/api/projects/join/", {"codigo": "NOEXISTE00"}, format="json")
        return respuesta.status_code

    codigos = en_paralelo(15, unirse)

    assert sorted(codigos) == [400] * 10 + [429] * 5
