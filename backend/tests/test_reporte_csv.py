"""Pruebas de la descarga del reporte en CSV (RF-12, HU-09). Catálogo: SQAP 5.1.2 e.

Reutiliza los datos del ejemplo de los wireframes de test_reporte_api.py.
"""

import csv
import io
from datetime import date
from unittest import mock

import pytest

from apps.activities.models import ActivityEntry, Estado, Resultado, Tipo
from apps.projects.models import Clase, Membership
from apps.reports.exportar_csv import texto_seguro
from tests.test_reporte_api import actividad, ejemplo_wireframes, proyecto  # noqa: F401

pytestmark = pytest.mark.django_db

BOM = "﻿"


@pytest.fixture
def url(proyecto):  # noqa: F811
    return f"/api/projects/{proyecto.id}/report.csv"


@pytest.fixture
def cliente(proyecto, cliente_de):  # noqa: F811
    return cliente_de(proyecto.creado_por)


def secciones(response) -> list[list[list[str]]]:
    """Separa el CSV en sus secciones (bloques separados por una fila vacía)."""
    texto = response.content.decode("utf-8")
    assert texto.startswith(BOM)
    bloques: list[list[list[str]]] = [[]]
    for fila in csv.reader(io.StringIO(texto.removeprefix(BOM))):
        if fila:
            bloques[-1].append(fila)
        else:
            bloques.append([])
    return bloques


# --- PR-RF12-01 · Contenido del CSV (HU-09 CA-01) ----------------------------------------


@pytest.mark.usefixtures("ejemplo_wireframes")
def test_pr_rf12_01_el_csv_tiene_indicadores_historial_y_actividades(cliente, url):
    """PR-RF12-01 con el ejemplo de las láminas 06 y 07."""
    response = cliente.get(url)
    assert response.status_code == 200
    indicadores, historial, actividades = secciones(response)

    encabezado = dict(fila for fila in indicadores if len(fila) == 2)
    assert encabezado["Proyecto"] == "Gestor SQA"
    assert encabezado["Estado general"] == "ADVERTENCIA"
    assert encabezado["Sprint de referencia"] == "3"
    tabla = {fila[0]: fila[1:] for fila in indicadores if len(fila) == 3}
    assert tabla["Densidad de defectos (def/KLOC)"] == ["6.11", "ADVERTENCIA"]
    assert tabla["Cobertura de pruebas (%)"] == ["78", "OPTIMO"]

    assert historial[0] == ["Historial por sprint"]
    columnas, *sprints = historial[1:]
    assert columnas[:3] == ["Sprint", "Nivel", "Densidad de defectos (def/KLOC)"]
    assert columnas[-2:] == ["Planeadas", "Realizadas"]
    assert [(s[0], s[1]) for s in sprints] == [
        ("1", "CRITICO"),
        ("2", "ADVERTENCIA"),
        ("3", "ADVERTENCIA"),
    ]
    assert sprints[0][-2:] == ["2", "1"]  # sprint 1: 2 planeadas, 1 realizada

    assert actividades[0] == ["Actividades"]
    assert actividades[1][-1] == "Hallazgos"
    assert len(actividades) - 2 == 7
    assert actividades[2][:5] == ["1", "PRUEBAS", "Pruebas", "REALIZADA", "SATISFACTORIO"]
    assert actividades[2][5] == "duena@correo.com"


def test_pr_rf12_01_sin_evaluacion_sale_con_secciones_vacias(cliente, url):
    """Proyecto nuevo: el estado y los encabezados de cada sección, sin filas de datos."""
    indicadores, historial, actividades = secciones(cliente.get(url))
    assert ["Estado general", "SIN_EVALUACION"] in indicadores
    assert ["Sprint de referencia", ""] in indicadores
    assert indicadores[-1] == ["Indicador", "Valor", "Nivel"]
    assert len(historial) == 2
    assert len(actividades) == 2


# --- PR-RF12-02 · Cualquier miembro lo descarga (HU-09 CA-03) ------------------------------


@pytest.mark.parametrize("clase", [Clase.ADMIN_NORMAL, Clase.COLABORADOR, Clase.AUDITOR])
def test_pr_rf12_02_cualquier_miembro_descarga(proyecto, url, crear_usuario, cliente_de, clase):  # noqa: F811
    """PR-RF12-02, incluido el Auditor."""
    usuario = crear_usuario(clase.lower())
    Membership.objects.create(project=proyecto, user=usuario, clase=clase)
    response = cliente_de(usuario).get(url)
    assert response.status_code == 200
    assert response["Content-Type"] == "text/csv; charset=utf-8"


# --- Formato de la respuesta ---------------------------------------------------------------


def test_es_un_adjunto_con_nombre_normalizado(cliente, url, proyecto):  # noqa: F811
    proyecto.nombre = "Gestión  de Calidad Ñ"
    proyecto.save()
    with mock.patch(
        "apps.reports.exportar_csv.timezone.localdate", return_value=date(2026, 11, 19)
    ):
        response = cliente.get(url)
    assert response["Content-Disposition"] == (
        'attachment; filename="reporte-gestion-de-calidad-n-2026-11-19.csv"'
    )


def test_nombre_sin_letras_usa_el_id_del_proyecto(cliente, url, proyecto):  # noqa: F811
    proyecto.nombre = "¡¿?!"
    proyecto.save()
    assert f'filename="reporte-proyecto-{proyecto.id}-' in cliente.get(url)["Content-Disposition"]


@pytest.mark.parametrize("accept", ["text/csv", "text/csv, application/json", "*/*"])
def test_responde_csv_con_cualquier_accept(cliente, url, accept):
    response = cliente.get(url, HTTP_ACCEPT=accept)
    assert response.status_code == 200
    assert response["Content-Type"] == "text/csv; charset=utf-8"


def test_un_no_miembro_recibe_404_en_json_aunque_pida_csv(url, crear_usuario, cliente_de):
    response = cliente_de(crear_usuario("intruso")).get(url, HTTP_ACCEPT="text/csv")
    assert response.status_code == 404
    assert response.json() == {"detail": "Proyecto no encontrado."}


# --- Inyección de fórmulas ----------------------------------------------------------------


@pytest.mark.parametrize("texto", ["=1+1", "+SUMA(A1)", "-2+3", "@cmd", "\t=1", "\r=1"])
def test_texto_seguro_neutraliza_formulas(texto):
    assert texto_seguro(texto) == f"'{texto}"


@pytest.mark.parametrize("texto", ["Gestor SQA", "2026-2", "", "a=b"])
def test_texto_seguro_no_toca_texto_normal(texto):
    assert texto_seguro(texto) == texto


def test_formulas_neutralizadas_en_el_csv(cliente, url, proyecto):  # noqa: F811
    """Nombre del proyecto, nombre de "Otra" y hallazgos son texto libre del usuario."""
    proyecto.nombre = '=HYPERLINK("http://malo")'
    proyecto.save()
    ActivityEntry.objects.create(
        project=proyecto,
        sprint=1,
        tipo=Tipo.OTRA,
        nombre_otra="+cmd|' /C calc'!A0",
        estado=Estado.REALIZADA,
        resultado=Resultado.CON_HALLAZGOS,
        hallazgos="@SUM(1+1)",
        responsable=proyecto.creado_por,
        registrado_por=proyecto.creado_por,
    )
    indicadores, _, actividades = secciones(cliente.get(url))

    assert ["Proyecto", '\'=HYPERLINK("http://malo")'] in indicadores
    fila = actividades[2]
    assert fila[2] == "'+cmd|' /C calc'!A0"
    assert fila[-1] == "'@SUM(1+1)"
    # Ninguna celda del archivo empieza con un carácter de fórmula.
    celdas = [c for bloque in (indicadores, actividades) for f in bloque for c in f]
    assert not [c for c in celdas if c[:1] in {"=", "+", "@"}]


# --- Rendimiento (RNF-02) -----------------------------------------------------------------


def test_consultas_acotadas_sin_importar_el_volumen(
    cliente,
    url,
    proyecto,  # noqa: F811
    django_assert_max_num_queries,
):
    for sprint in range(1, 31):
        actividad(proyecto, sprint)
    # Sesión, usuario, membresía, métricas y actividades: no crece con las actividades.
    with django_assert_max_num_queries(5):
        response = cliente.get(url)
    assert len(secciones(response)[2]) - 2 == 30
