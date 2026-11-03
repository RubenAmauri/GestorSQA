"""Pruebas del endpoint del reporte de salud (RF-10, RF-11, HU-07). Catálogo: SQAP 5.1.2 e.

El cálculo está probado a fondo en test_salud.py; aquí se prueba que el reporte lee los
datos guardados, aplica el motor de salud y entrega el contenido de la SDS 3.4.
"""

from decimal import Decimal

import pytest

from apps.activities.models import ActivityEntry, Estado, Resultado, Tipo
from apps.metrics.models import MetricEntry
from apps.projects.models import Clase, Membership, Project

pytestmark = pytest.mark.django_db


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
def url(proyecto):
    return f"/api/projects/{proyecto.id}/report/"


@pytest.fixture
def cliente(proyecto, cliente_de):
    return cliente_de(proyecto.creado_por)


def metrica(proyecto, sprint, encontrados, corregidos, horas, kloc, cobertura):
    MetricEntry.objects.create(
        project=proyecto,
        sprint=sprint,
        defectos_encontrados=encontrados,
        defectos_corregidos=corregidos,
        horas_correccion=horas,
        kloc=Decimal(kloc),
        cobertura_pct=cobertura,
        registrado_por=proyecto.creado_por,
    )


def actividad(proyecto, sprint, estado=Estado.REALIZADA, resultado=Resultado.SATISFACTORIO):
    return ActivityEntry.objects.create(
        project=proyecto,
        sprint=sprint,
        tipo=Tipo.PRUEBAS,
        estado=estado,
        resultado=resultado if estado == Estado.REALIZADA else None,
        responsable=proyecto.creado_por,
        registrado_por=proyecto.creado_por,
    )


@pytest.fixture
def ejemplo_wireframes(proyecto):
    """Datos de las láminas 06 y 07: sprints 1 a 3."""
    metrica(proyecto, 1, 10, 5, 30, "0.88", None)
    metrica(proyecto, 2, 8, 6, 27, "2.28", 66)
    metrica(proyecto, 3, 4, 4, 14, "3.6", 78)
    actividad(proyecto, 1)
    actividad(proyecto, 1, Estado.PLANEADA)
    for _ in range(3):
        actividad(proyecto, 2)
    actividad(proyecto, 3)
    actividad(proyecto, 3, resultado=Resultado.CON_HALLAZGOS)


def test_pr_rf11_02_proyecto_nuevo_sin_evaluacion(cliente, url):
    """PR-RF11-02 (HU-07 CA-03), a través de la API."""
    datos = cliente.get(url).json()
    assert datos["estado_general"] == "SIN_EVALUACION"
    assert datos["sprint_referencia"] is None
    assert datos["indicadores"] is None
    assert datos["historial"] == []
    assert datos["proyecto"]["nombre"] == "Gestor SQA"


def test_pr_rf10_reporte_completo_con_el_ejemplo_de_los_wireframes(
    cliente, url, ejemplo_wireframes
):
    """HU-07 CA-01 y CA-02: estado general, indicadores, historial y planeadas/realizadas."""
    response = cliente.get(url)
    assert response.status_code == 200
    datos = response.json()

    assert datos["estado_general"] == "ADVERTENCIA"
    assert datos["sprint_referencia"] == 3
    assert [s["nivel"] for s in datos["historial"]] == ["CRITICO", "ADVERTENCIA", "ADVERTENCIA"]

    indicadores = datos["indicadores"]
    assert indicadores["densidad"] == {"nivel": "ADVERTENCIA", "valor": 6.11}
    assert indicadores["cobertura"] == {"nivel": "OPTIMO", "valor": 78.0}
    assert indicadores["tiempo_correccion"] == {"nivel": "OPTIMO", "valor": 3.5}
    assert indicadores["actividades"] == {"nivel": "OPTIMO", "valor": 2.0}

    sprint_1 = datos["historial"][0]
    assert sprint_1["cobertura"] == {"nivel": "SIN_DATOS", "valor": None}
    assert (sprint_1["actividades_planeadas"], sprint_1["actividades_realizadas"]) == (2, 1)

    assert len(datos["actividades"]) == 7
    assert datos["actividades"][0]["responsable"] == "duena@correo.com"


def test_pr_rf11_03_actividad_planeada_no_cambia_el_sprint_de_referencia(
    cliente, url, ejemplo_wireframes, proyecto
):
    """PR-RF11-03, a través de la API: planear el sprint 4 no lo vuelve el evaluado."""
    actividad(proyecto, 4, Estado.PLANEADA)
    assert cliente.get(url).json()["sprint_referencia"] == 3


def test_el_auditor_tambien_ve_el_reporte(proyecto, url, crear_usuario, cliente_de):
    """HU-07: el reporte es para cualquier miembro, incluido el Auditor (CLU-04)."""
    auditor = crear_usuario("auditor")
    Membership.objects.create(project=proyecto, user=auditor, clase=Clase.AUDITOR)
    assert cliente_de(auditor).get(url).status_code == 200


def test_actividad_otra_muestra_su_nombre(cliente, url, proyecto):
    ActivityEntry.objects.create(
        project=proyecto,
        sprint=1,
        tipo=Tipo.OTRA,
        nombre_otra="Análisis estático",
        estado=Estado.PLANEADA,
        responsable=proyecto.creado_por,
        registrado_por=proyecto.creado_por,
        fecha="2026-09-01",
    )
    actividad_reportada = cliente.get(url).json()["actividades"][0]
    assert actividad_reportada["nombre"] == "Análisis estático"
    assert actividad_reportada["fecha"] == "2026-09-01"
    assert actividad_reportada["resultado"] is None


def test_consultas_constantes_sin_importar_el_volumen(
    cliente, url, proyecto, django_assert_max_num_queries
):
    """RNF-02: el reporte no hace una consulta por registro (sin N+1)."""
    for sprint in range(1, 11):
        metrica(proyecto, sprint, 1, 1, 2, "1", 80)
        for _ in range(5):
            actividad(proyecto, sprint)
    with django_assert_max_num_queries(8):
        response = cliente.get(url)
    assert len(response.json()["historial"]) == 10
