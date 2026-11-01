"""Pruebas de infraestructura: healthcheck y entrega de la SPA (SDS 3.5 y 5.1)."""

from unittest import mock

import pytest

pytestmark = pytest.mark.django_db


def test_health_responde_ok_sin_sesion(api_client):
    response = api_client.get("/api/health/")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": "ok"}


def test_health_reporta_error_si_falla_la_base_de_datos(api_client):
    with mock.patch("apps.core.views.connection.cursor", side_effect=Exception("sin BD")):
        response = api_client.get("/api/health/")
    assert response.status_code == 503
    assert response.json()["database"] == "error"


def test_rutas_fuera_de_api_devuelven_la_spa(client):
    with mock.patch("apps.core.views.render_to_string", return_value="<html>SPA</html>"):
        response = client.get("/proyectos/5/metricas")
    assert response.status_code == 200
    assert b"SPA" in response.content


def test_sin_spa_compilada_responde_503(client):
    from django.template import TemplateDoesNotExist

    with mock.patch("apps.core.views.render_to_string", side_effect=TemplateDoesNotExist("x")):
        response = client.get("/login")
    assert response.status_code == 503
