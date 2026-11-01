"""PR-RNF03-01: batería de confidencialidad (RF-06, RNF-03; SQAP 5.1.2 e).

Cada ruta que recibe el id de un proyecto se prueba en dos situaciones:
- sin sesión → 401;
- con sesión, pero sin ser miembro del proyecto → 404 (no revela que existe).

Regla para el equipo: todo PR que agregue una ruta de proyecto la agrega a RUTAS_DE_PROYECTO.
"""

import pytest
from rest_framework.test import APIClient

from apps.projects.models import Clase, Membership, Project

pytestmark = pytest.mark.django_db

RUTAS_DE_PROYECTO = [
    ("get", "/api/projects/{id}/"),
    ("post", "/api/projects/{id}/codigo/regenerar/"),
    ("get", "/api/projects/{id}/metrics/"),
    ("post", "/api/projects/{id}/metrics/"),
    ("get", "/api/projects/{id}/activities/"),
    ("post", "/api/projects/{id}/activities/"),
]

RUTAS_CON_SESION = [
    ("get", "/api/projects/"),
    ("post", "/api/projects/"),
    ("post", "/api/projects/join/"),
]


@pytest.fixture
def proyecto(crear_usuario):
    duena = crear_usuario("duena")
    proyecto = Project.objects.create(
        creado_por=duena,
        nombre="Privado",
        periodo_nombre="2026-2",
        fecha_inicio="2026-08-10",
        fecha_fin="2026-12-04",
    )
    Membership.objects.create(project=proyecto, user=duena, clase=Clase.ADMIN_CREADOR)
    return proyecto


@pytest.mark.parametrize(("metodo", "ruta"), RUTAS_DE_PROYECTO)
def test_pr_rnf03_01_sin_sesion_responde_401(proyecto, metodo, ruta):
    response = getattr(APIClient(), metodo)(ruta.format(id=proyecto.id), {}, format="json")
    assert response.status_code == 401


@pytest.mark.parametrize(("metodo", "ruta"), RUTAS_DE_PROYECTO)
def test_pr_rnf03_01_no_miembro_responde_404(proyecto, crear_usuario, cliente_de, metodo, ruta):
    cliente = cliente_de(crear_usuario("intruso"))
    response = getattr(cliente, metodo)(ruta.format(id=proyecto.id), {}, format="json")
    assert response.status_code == 404
    assert "Privado" not in response.content.decode()


@pytest.mark.parametrize(("metodo", "ruta"), RUTAS_DE_PROYECTO)
def test_pr_rnf03_01_proyecto_inexistente_responde_igual_que_ajeno(
    crear_usuario, cliente_de, metodo, ruta
):
    """Un id que no existe y uno ajeno dan la misma respuesta: no se puede sondear."""
    cliente = cliente_de(crear_usuario("intruso"))
    response = getattr(cliente, metodo)(ruta.format(id=999999), {}, format="json")
    assert response.status_code == 404


@pytest.mark.parametrize(("metodo", "ruta"), RUTAS_CON_SESION)
def test_rutas_generales_de_proyectos_exigen_sesion(metodo, ruta):
    response = getattr(APIClient(), metodo)(ruta, {}, format="json")
    assert response.status_code == 401
