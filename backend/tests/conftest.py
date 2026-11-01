import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient


@pytest.fixture
def api_client() -> APIClient:
    return APIClient()


@pytest.fixture
def crear_usuario(db):
    """Fábrica de usuarios: crear_usuario("ana") crea ana@correo.com."""

    def _crear(nombre: str):
        return get_user_model().objects.create_user(f"{nombre}@correo.com", "clave-de-prueba-1")

    return _crear


@pytest.fixture
def cliente_de():
    """Cliente con la sesión iniciada del usuario dado (autenticación real por sesión)."""

    def _cliente(usuario) -> APIClient:
        cliente = APIClient()
        cliente.force_login(usuario)
        return cliente

    return _cliente
