"""Pruebas de proyectos y unión por código (RF-02, RF-03, RF-06). Catálogo: SQAP 5.1.2 e."""

from unittest import mock

import pytest
from django.db import IntegrityError

from apps.projects.models import (
    ALFABETO_CODIGO,
    Clase,
    Membership,
    Project,
    generar_codigo,
    normalizar,
)

pytestmark = pytest.mark.django_db

PROYECTOS = "/api/projects/"
UNIRSE = "/api/projects/join/"

DATOS = {
    "nombre": "Gestor SQA",
    "periodo_nombre": "2026-2",
    "fecha_inicio": "2026-08-10",
    "fecha_fin": "2026-12-04",
}


@pytest.fixture
def ana(crear_usuario):
    return crear_usuario("ana")


@pytest.fixture
def beto(crear_usuario):
    return crear_usuario("beto")


def crear_proyecto(cliente, **cambios):
    return cliente.post(PROYECTOS, {**DATOS, **cambios}, format="json")


# --- RF-02 · Alta de proyecto ---------------------------------------------------------


def test_pr_rf02_01_crear_proyecto_deja_al_creador_como_admin_creador(cliente_de, ana):
    """PR-RF02-01 (HU-01 CA-03)."""
    response = crear_proyecto(cliente_de(ana))
    assert response.status_code == 201
    datos = response.json()
    assert datos["nombre"] == "Gestor SQA"
    assert datos["mi_clase"] == Clase.ADMIN_CREADOR
    assert len(datos["codigo_union"]) == 10

    proyecto = Project.objects.get()
    assert proyecto.creado_por == ana
    membresia = Membership.objects.get()
    assert (membresia.user, membresia.project, membresia.clase) == (
        ana,
        proyecto,
        Clase.ADMIN_CREADOR,
    )


@pytest.mark.parametrize(
    ("nombre", "periodo"),
    [("Gestor SQA", "2026-2"), ("gestor sqa", "2026-2"), ("  Gestor   SQA ", " 2026-2 ")],
)
def test_pr_rf02_02_duplicado_del_mismo_creador_responde_409(cliente_de, ana, nombre, periodo):
    """PR-RF02-02 (HU-01 CA-02): la comparación ignora mayúsculas y espacios sobrantes."""
    cliente = cliente_de(ana)
    assert crear_proyecto(cliente).status_code == 201
    response = crear_proyecto(cliente, nombre=nombre, periodo_nombre=periodo)
    assert response.status_code == 409
    assert Project.objects.count() == 1


def test_pr_rf02_03_otro_creador_si_puede_repetir_nombre_y_periodo(cliente_de, ana, beto):
    """PR-RF02-03: la unicidad es por usuario creador (justificación en RF-02)."""
    assert crear_proyecto(cliente_de(ana)).status_code == 201
    assert crear_proyecto(cliente_de(beto)).status_code == 201
    assert Project.objects.count() == 2


def test_pr_rf02_04_fecha_fin_anterior_a_inicio_responde_400(cliente_de, ana):
    """PR-RF02-04 (HU-01 CA-01)."""
    response = crear_proyecto(cliente_de(ana), fecha_inicio="2026-12-04", fecha_fin="2026-08-10")
    assert response.status_code == 400
    assert "fecha_fin" in response.json()
    assert not Project.objects.exists()


def test_misma_fecha_de_inicio_y_fin_es_valida(cliente_de, ana):
    response = crear_proyecto(cliente_de(ana), fecha_fin=DATOS["fecha_inicio"])
    assert response.status_code == 201


@pytest.mark.parametrize("campo", ["nombre", "periodo_nombre", "fecha_inicio", "fecha_fin"])
def test_todos_los_campos_son_obligatorios(cliente_de, ana, campo):
    """HU-01 CA-01."""
    datos = {k: v for k, v in DATOS.items() if k != campo}
    response = cliente_de(ana).post(PROYECTOS, datos, format="json")
    assert response.status_code == 400
    assert campo in response.json()


def test_nombre_en_blanco_o_demasiado_largo_responde_400(cliente_de, ana):
    cliente = cliente_de(ana)
    assert crear_proyecto(cliente, nombre="   ").status_code == 400
    assert crear_proyecto(cliente, nombre="x" * 101).status_code == 400


def test_alta_simultanea_duplicada_responde_409(cliente_de, ana):
    with mock.patch(
        "apps.projects.views.Project.objects.create", side_effect=IntegrityError("duplicado")
    ):
        response = crear_proyecto(cliente_de(ana))
    assert response.status_code == 409


def test_restriccion_de_fechas_tambien_en_la_base_de_datos(ana):
    with pytest.raises(IntegrityError):
        Project.objects.create(
            creado_por=ana,
            nombre="X",
            periodo_nombre="2026-2",
            fecha_inicio="2026-12-04",
            fecha_fin="2026-08-10",
        )


# --- RF-06 · Mis proyectos ---------------------------------------------------------------


def test_listado_solo_muestra_mis_proyectos_con_mi_clase(cliente_de, ana, beto):
    crear_proyecto(cliente_de(ana))
    crear_proyecto(cliente_de(beto), nombre="Proyecto de Beto")

    listado = cliente_de(ana).get(PROYECTOS).json()
    assert [p["nombre"] for p in listado] == ["Gestor SQA"]
    assert listado[0]["mi_clase"] == Clase.ADMIN_CREADOR


def test_detalle_para_un_miembro(cliente_de, ana):
    proyecto_id = crear_proyecto(cliente_de(ana)).json()["id"]
    response = cliente_de(ana).get(f"{PROYECTOS}{proyecto_id}/")
    assert response.status_code == 200
    assert response.json()["periodo_nombre"] == "2026-2"


# --- RF-03 · Unión por código -----------------------------------------------------------


def _codigo_de(cliente):
    return crear_proyecto(cliente).json()["codigo_union"]


def test_pr_rf03_01_unirse_queda_como_colaborador(cliente_de, ana, beto):
    """PR-RF03-01 (HU-02 CA-01)."""
    codigo = _codigo_de(cliente_de(ana))
    response = cliente_de(beto).post(UNIRSE, {"codigo": f" {codigo.lower()} "}, format="json")
    assert response.status_code == 201
    datos = response.json()
    assert datos["mi_clase"] == Clase.COLABORADOR
    assert "codigo_union" not in datos  # el código solo lo ve un Admin
    assert Membership.objects.get(user=beto).clase == Clase.COLABORADOR


def test_pr_rf03_02_codigo_invalido_responde_mensaje_generico(cliente_de, ana, beto):
    """PR-RF03-02 (HU-02 CA-02): no revela si el proyecto existe."""
    _codigo_de(cliente_de(ana))
    response = cliente_de(beto).post(UNIRSE, {"codigo": "NOEXISTE00"}, format="json")
    assert response.status_code == 400
    assert response.json() == {"detail": "El código no es válido."}
    assert not Membership.objects.filter(user=beto).exists()


def test_pr_rf03_03_si_ya_es_miembro_responde_409(cliente_de, ana, beto):
    """PR-RF03-03 (HU-02 CA-03): no se crea una segunda membresía."""
    codigo = _codigo_de(cliente_de(ana))
    cliente = cliente_de(beto)
    assert cliente.post(UNIRSE, {"codigo": codigo}, format="json").status_code == 201
    response = cliente.post(UNIRSE, {"codigo": codigo}, format="json")
    assert response.status_code == 409
    assert Membership.objects.filter(user=beto).count() == 1


def test_pr_rf03_04_tras_regenerar_el_codigo_anterior_no_funciona(cliente_de, ana, beto):
    """PR-RF03-04 (HU-08 CA-03)."""
    creado = crear_proyecto(cliente_de(ana)).json()
    anterior = creado["codigo_union"]
    response = cliente_de(ana).post(f"{PROYECTOS}{creado['id']}/codigo/regenerar/")
    assert response.status_code == 200
    nuevo = response.json()["codigo_union"]
    assert nuevo != anterior

    cliente = cliente_de(beto)
    assert cliente.post(UNIRSE, {"codigo": anterior}, format="json").status_code == 400
    assert cliente.post(UNIRSE, {"codigo": nuevo}, format="json").status_code == 201


def test_solo_un_admin_regenera_el_codigo(cliente_de, ana, beto):
    """RF-03: un Colaborador recibe 403 (es miembro, pero sin permiso)."""
    creado = crear_proyecto(cliente_de(ana)).json()
    cliente_de(beto).post(UNIRSE, {"codigo": creado["codigo_union"]}, format="json")
    response = cliente_de(beto).post(f"{PROYECTOS}{creado['id']}/codigo/regenerar/")
    assert response.status_code == 403
    assert Project.objects.get().codigo_union == creado["codigo_union"]


def test_codigo_vacio_responde_400(cliente_de, beto):
    assert cliente_de(beto).post(UNIRSE, {}, format="json").status_code == 400


def test_limite_de_10_intentos_de_union_por_hora(cliente_de, beto):
    """RNF-05: el 11.º intento de unión en una hora responde 429."""
    cliente = cliente_de(beto)
    for _ in range(10):
        assert cliente.post(UNIRSE, {"codigo": "NOEXISTE00"}, format="json").status_code == 400
    assert cliente.post(UNIRSE, {"codigo": "NOEXISTE00"}, format="json").status_code == 429


# --- Modelo ---------------------------------------------------------------------------------


def test_normalizar():
    assert normalizar("  Gestor   SQA ") == "gestor sqa"


def test_codigo_generado_tiene_10_caracteres_alfanumericos():
    codigo = generar_codigo()
    assert len(codigo) == 10
    assert set(codigo) <= set(ALFABETO_CODIGO)


def test_regenerar_evita_codigos_repetidos(ana):
    proyecto = Project.objects.create(
        creado_por=ana,
        nombre="X",
        periodo_nombre="2026-2",
        fecha_inicio="2026-08-10",
        fecha_fin="2026-12-04",
    )
    anterior = proyecto.codigo_union
    with mock.patch("apps.projects.models.generar_codigo", side_effect=[anterior, "NUEVO00001"]):
        assert proyecto.regenerar_codigo() == "NUEVO00001"


def test_representacion_en_texto(ana):
    proyecto = Project.objects.create(
        creado_por=ana,
        nombre="X",
        periodo_nombre="2026-2",
        fecha_inicio="2026-08-10",
        fecha_fin="2026-12-04",
    )
    membresia = Membership.objects.create(project=proyecto, user=ana, clase=Clase.AUDITOR)
    assert str(proyecto) == "X (2026-2)"
    assert "AUDITOR" in str(membresia)
    assert not membresia.es_admin
