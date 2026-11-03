"""Pruebas de la API de cuentas y sesión (RF-01, HU-10, RNF-05). Rutas de la SDS 3.4."""

from unittest import mock

import pytest
from django.contrib.auth import get_user_model
from django.db import IntegrityError
from rest_framework.test import APIClient

pytestmark = pytest.mark.django_db

REGISTRO = "/api/auth/register/"
LOGIN = "/api/auth/login/"
LOGOUT = "/api/auth/logout/"
ME = "/api/auth/me/"
CSRF = "/api/auth/csrf/"


@pytest.fixture
def usuario():
    return get_user_model().objects.create_user("ana@correo.com", "secreta123")


# --- Registro (CA-01, CA-02) ---------------------------------------------------------


def test_pr_rf01_01_registro_valido(api_client):
    """PR-RF01-01: registro válido → 201 con {id, email} y la sesión queda iniciada."""
    response = api_client.post(
        REGISTRO, {"email": "  Beto@Correo.COM ", "password": "secreta123"}, format="json"
    )
    assert response.status_code == 201
    usuario = get_user_model().objects.get()
    assert response.json() == {"id": usuario.id, "email": "beto@correo.com"}
    assert usuario.check_password("secreta123")
    assert "password" not in response.json()

    me = api_client.get(ME)
    assert me.status_code == 200
    assert me.json()["email"] == "beto@correo.com"


def test_pr_rf01_02_correo_duplicado_responde_409(api_client, usuario):
    """PR-RF01-02 (CA-01): un correo ya registrado, sin importar mayúsculas → 409."""
    response = api_client.post(
        REGISTRO, {"email": "ANA@correo.com", "password": "otraclave99"}, format="json"
    )
    assert response.status_code == 409
    assert "email" in response.json()
    assert get_user_model().objects.count() == 1


def test_registro_simultaneo_con_el_mismo_correo_responde_409(api_client):
    """Si la restricción única falla entre la consulta y el alta, también es 409."""
    with mock.patch(
        "apps.accounts.models.UserManager.create_user", side_effect=IntegrityError("duplicado")
    ):
        response = api_client.post(
            REGISTRO, {"email": "eva@correo.com", "password": "secreta123"}, format="json"
        )
    assert response.status_code == 409


def test_pr_rf01_03_contrasena_de_menos_de_8_caracteres_responde_400(api_client):
    """PR-RF01-03 (CA-02): contraseña de 7 caracteres → 400 y no se crea la cuenta."""
    response = api_client.post(
        REGISTRO, {"email": "beto@correo.com", "password": "corta12"}, format="json"
    )
    assert response.status_code == 400
    assert "password" in response.json()
    assert not get_user_model().objects.exists()


def test_registro_con_8_caracteres_exactos_es_valido(api_client):
    """Valor límite de CA-02: 8 caracteres sí se aceptan."""
    response = api_client.post(
        REGISTRO, {"email": "beto@correo.com", "password": "ocho1234"}, format="json"
    )
    assert response.status_code == 201


@pytest.mark.parametrize(
    "datos",
    [
        {"email": "no-es-correo", "password": "secreta123"},
        {"password": "secreta123"},
        {"email": "beto@correo.com"},
    ],
)
def test_registro_con_datos_invalidos_responde_400(api_client, datos):
    assert api_client.post(REGISTRO, datos, format="json").status_code == 400


# --- Inicio de sesión (CA-03) ---------------------------------------------------------


def test_inicio_de_sesion_valido(api_client, usuario):
    response = api_client.post(
        LOGIN, {"email": "Ana@Correo.com", "password": "secreta123"}, format="json"
    )
    assert response.status_code == 200
    assert response.json() == {"id": usuario.id, "email": "ana@correo.com"}
    assert api_client.get(ME).json()["id"] == usuario.id


def test_pr_rf01_04_credenciales_incorrectas_responden_400_con_mensaje_generico(
    api_client, usuario
):
    """PR-RF01-04 (CA-03): contraseña mala y correo inexistente dan el mismo mensaje."""
    contrasena_mala = api_client.post(
        LOGIN, {"email": "ana@correo.com", "password": "equivocada"}, format="json"
    )
    correo_inexistente = api_client.post(
        LOGIN, {"email": "nadie@correo.com", "password": "secreta123"}, format="json"
    )
    assert contrasena_mala.status_code == 400
    assert correo_inexistente.status_code == 400
    assert contrasena_mala.json() == correo_inexistente.json()
    assert contrasena_mala.json() == {"detail": "Correo o contraseña incorrectos."}
    assert api_client.get(ME).status_code == 401


def test_cuenta_inactiva_no_inicia_sesion(api_client, usuario):
    usuario.is_active = False
    usuario.save()
    response = api_client.post(
        LOGIN, {"email": "ana@correo.com", "password": "secreta123"}, format="json"
    )
    assert response.status_code == 400


def test_inicio_de_sesion_sin_datos_responde_400(api_client):
    assert api_client.post(LOGIN, {}, format="json").status_code == 400


# --- Cierre de sesión y sesión actual (CA-04) ----------------------------------------


def test_pr_rf01_05_cierre_de_sesion(api_client, usuario):
    """PR-RF01-05 (CA-04): tras cerrar sesión, auth/me/ responde 401."""
    api_client.post(LOGIN, {"email": "ana@correo.com", "password": "secreta123"}, format="json")
    assert api_client.get(ME).status_code == 200

    response = api_client.post(LOGOUT)
    assert response.status_code == 204
    assert api_client.get(ME).status_code == 401


def test_sin_sesion_responde_401_y_no_403(api_client):
    """SDS 3.4: sin sesión es 401, con encabezado WWW-Authenticate."""
    me = api_client.get(ME)
    assert me.status_code == 401
    assert me.has_header("WWW-Authenticate")
    assert api_client.post(LOGOUT).status_code == 401


# --- Límite de intentos (RNF-05) ------------------------------------------------------


def _intento(cliente: APIClient, **extra):
    return cliente.post(
        LOGIN, {"email": "ana@correo.com", "password": "equivocada"}, format="json", **extra
    )


def test_pr_rnf05_02_sexto_intento_en_un_minuto_responde_429(api_client, usuario):
    """PR-RNF05-02: 5 intentos por minuto por IP; el 6.º responde 429, aunque sea correcto."""
    for _ in range(5):
        assert _intento(api_client).status_code == 400

    sexto = api_client.post(
        LOGIN, {"email": "ana@correo.com", "password": "secreta123"}, format="json"
    )
    assert sexto.status_code == 429
    assert sexto.has_header("Retry-After")


def test_limite_de_intentos_es_por_ip_detras_del_proxy(api_client, usuario):
    """Con NUM_PROXIES = 1 la IP es la que agrega Caddy al final de X-Forwarded-For."""
    for _ in range(5):
        _intento(api_client, HTTP_X_FORWARDED_FOR="1.1.1.1, 203.0.113.10")
    bloqueada = _intento(api_client, HTTP_X_FORWARDED_FOR="9.9.9.9, 203.0.113.10")
    otra_ip = _intento(api_client, HTTP_X_FORWARDED_FOR="203.0.113.20")
    assert bloqueada.status_code == 429
    assert otra_ip.status_code == 400


def test_el_limite_se_reinicia_pasado_el_minuto(api_client, usuario):
    with mock.patch("rest_framework.throttling.SimpleRateThrottle.timer", return_value=1000.0):
        for _ in range(5):
            _intento(api_client)
        assert _intento(api_client).status_code == 429
    with mock.patch("rest_framework.throttling.SimpleRateThrottle.timer", return_value=1061.0):
        assert _intento(api_client).status_code == 400


# --- CSRF (ADR-05) --------------------------------------------------------------------


def test_csrf_establece_la_cookie():
    cliente = APIClient(enforce_csrf_checks=True)
    response = cliente.get(CSRF)
    assert response.status_code == 204
    assert "csrftoken" in response.cookies


def test_registro_e_inicio_de_sesion_exigen_csrf(usuario):
    """Sin token CSRF el inicio de sesión se rechaza; con el token de auth/csrf/ funciona."""
    cliente = APIClient(enforce_csrf_checks=True)
    datos = {"email": "ana@correo.com", "password": "secreta123"}
    assert cliente.post(LOGIN, datos, format="json").status_code == 403
    assert (
        cliente.post(
            REGISTRO, {"email": "eva@correo.com", "password": "secreta123"}, format="json"
        ).status_code
        == 403
    )

    token = cliente.get(CSRF).cookies["csrftoken"].value
    response = cliente.post(LOGIN, datos, format="json", HTTP_X_CSRFTOKEN=token)
    assert response.status_code == 200
