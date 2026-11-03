"""Pruebas de métricas por sprint (RF-07, HU-06). Catálogo: SQAP 5.1.2 e."""

from decimal import Decimal
from unittest import mock

import pytest
from django.db import IntegrityError

from apps.metrics.models import MetricEntry
from apps.projects.models import Clase, Membership, Project

pytestmark = pytest.mark.django_db

COMPLETA = {
    "sprint": 3,
    "defectos_encontrados": 4,
    "defectos_corregidos": 4,
    "horas_correccion": 14,
    "kloc": "3.6",
    "cobertura_pct": 78,
}


@pytest.fixture
def proyecto(crear_usuario):
    duena = crear_usuario("duena")
    proyecto = Project.objects.create(
        creado_por=duena,
        nombre="Gestor SQA",
        periodo_nombre="2026-2",
        fecha_inicio="2026-08-10",
        fecha_fin="2026-12-04",
    )
    Membership.objects.create(project=proyecto, user=duena, clase=Clase.ADMIN_CREADOR)
    return proyecto


@pytest.fixture
def miembro(proyecto, crear_usuario, cliente_de):
    """miembro(Clase.X) devuelve un cliente con sesión de un miembro de esa clase."""

    def _miembro(clase):
        usuario = crear_usuario(clase.lower())
        Membership.objects.create(project=proyecto, user=usuario, clase=clase)
        return cliente_de(usuario)

    return _miembro


@pytest.fixture
def url(proyecto):
    return f"/api/projects/{proyecto.id}/metrics/"


def test_pr_rf07_01_captura_valida(miembro, url, proyecto):
    """PR-RF07-01 (HU-06): un Colaborador captura las métricas de un sprint."""
    response = miembro(Clase.COLABORADOR).post(url, COMPLETA, format="json")
    assert response.status_code == 201
    assert response.json() == {
        "sprint": 3,
        "defectos_encontrados": 4,
        "defectos_corregidos": 4,
        "horas_correccion": 14.0,
        "kloc": 3.6,
        "cobertura_pct": 78.0,
    }
    metrica = MetricEntry.objects.get()
    assert metrica.project == proyecto
    assert metrica.kloc == Decimal("3.6")


def test_pr_rf07_02_sprint_repetido_responde_409(miembro, url):
    """PR-RF07-02 (HU-06 CA-01): un solo registro por sprint."""
    cliente = miembro(Clase.COLABORADOR)
    assert cliente.post(url, COMPLETA, format="json").status_code == 201
    response = cliente.post(url, {"sprint": 3}, format="json")
    assert response.status_code == 409
    assert "sprint" in response.json()
    assert MetricEntry.objects.count() == 1


@pytest.mark.parametrize("cobertura", [-1, "100.01", 150])
def test_pr_rf07_03_cobertura_fuera_de_0_a_100_responde_400(miembro, url, cobertura):
    """PR-RF07-03 (HU-06 CA-03)."""
    response = miembro(Clase.COLABORADOR).post(
        url, {"sprint": 1, "cobertura_pct": cobertura}, format="json"
    )
    assert response.status_code == 400
    assert "cobertura_pct" in response.json()


@pytest.mark.parametrize("cobertura", [0, 100])
def test_cobertura_en_los_limites_es_valida(miembro, url, cobertura):
    response = miembro(Clase.COLABORADOR).post(
        url, {"sprint": 1, "cobertura_pct": cobertura}, format="json"
    )
    assert response.status_code == 201


@pytest.mark.parametrize(
    "campo", ["defectos_encontrados", "defectos_corregidos", "horas_correccion", "kloc"]
)
def test_pr_rf07_04_valores_negativos_responden_400(miembro, url, campo):
    """PR-RF07-04 (HU-06 CA-03)."""
    response = miembro(Clase.COLABORADOR).post(url, {"sprint": 1, campo: -1}, format="json")
    assert response.status_code == 400
    assert campo in response.json()


@pytest.mark.parametrize("sprint", [0, -2, None])
def test_sprint_obligatorio_y_desde_1(miembro, url, sprint):
    datos = {} if sprint is None else {"sprint": sprint}
    response = miembro(Clase.COLABORADOR).post(url, datos, format="json")
    assert response.status_code == 400
    assert "sprint" in response.json()


def test_pr_rf07_05_vacio_y_cero_se_conservan_distintos(miembro, url):
    """PR-RF07-05 (HU-06 CA-02): vacío es "Sin datos"; cero es un dato."""
    cliente = miembro(Clase.COLABORADOR)
    cliente.post(url, {"sprint": 1, "defectos_encontrados": 0, "kloc": None}, format="json")

    metrica = MetricEntry.objects.get()
    assert metrica.defectos_encontrados == 0
    assert metrica.kloc is None
    assert metrica.cobertura_pct is None  # campo omitido

    listado = cliente.get(url).json()
    assert listado[0]["defectos_encontrados"] == 0
    assert listado[0]["kloc"] is None
    assert listado[0]["cobertura_pct"] is None


def test_listado_ordenado_por_sprint_para_cualquier_miembro(miembro, url):
    captura = miembro(Clase.COLABORADOR)
    for sprint in (3, 1, 2):
        captura.post(url, {"sprint": sprint}, format="json")
    listado = miembro(Clase.AUDITOR).get(url)
    assert listado.status_code == 200
    assert [m["sprint"] for m in listado.json()] == [1, 2, 3]


@pytest.mark.parametrize("clase", [Clase.ADMIN_CREADOR, Clase.ADMIN_NORMAL])
def test_los_admin_tambien_capturan(proyecto, miembro, url, clase, cliente_de):
    if clase == Clase.ADMIN_CREADOR:
        cliente = cliente_de(proyecto.creado_por)
    else:
        cliente = miembro(clase)
    assert cliente.post(url, {"sprint": 1}, format="json").status_code == 201


def test_el_auditor_no_captura_metricas(miembro, url):
    """RF-05: el Auditor es de solo lectura; recibe 403."""
    response = miembro(Clase.AUDITOR).post(url, COMPLETA, format="json")
    assert response.status_code == 403
    assert not MetricEntry.objects.exists()


def test_las_metricas_no_se_mezclan_entre_proyectos(proyecto, miembro, url, cliente_de):
    miembro(Clase.COLABORADOR).post(url, COMPLETA, format="json")
    otro = Project.objects.create(
        creado_por=proyecto.creado_por,
        nombre="Otro",
        periodo_nombre="2026-2",
        fecha_inicio="2026-08-10",
        fecha_fin="2026-12-04",
    )
    Membership.objects.create(project=otro, user=proyecto.creado_por, clase=Clase.ADMIN_CREADOR)
    response = cliente_de(proyecto.creado_por).get(f"/api/projects/{otro.id}/metrics/")
    assert response.json() == []


def test_captura_simultanea_del_mismo_sprint_responde_409(miembro, url):
    with mock.patch(
        "apps.metrics.serializers.MetricaSerializer.save", side_effect=IntegrityError("repetido")
    ):
        response = miembro(Clase.COLABORADOR).post(url, {"sprint": 1}, format="json")
    assert response.status_code == 409


def test_restricciones_tambien_en_la_base_de_datos(proyecto):
    with pytest.raises(IntegrityError):
        MetricEntry.objects.create(
            project=proyecto, sprint=1, cobertura_pct=101, registrado_por=proyecto.creado_por
        )


def test_representacion_en_texto(proyecto):
    metrica = MetricEntry.objects.create(
        project=proyecto, sprint=2, registrado_por=proyecto.creado_por
    )
    assert str(metrica) == "Gestor SQA (2026-2) · sprint 2"
