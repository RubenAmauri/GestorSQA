"""Pruebas del comando sembrar_carga, que prepara PR-RNF02-01 (RNF-02).

Usan un volumen pequeño; el volumen del RNF-02 son los valores por omisión del comando.
"""

import secrets
from io import StringIO

import pytest
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import CommandError

from apps.activities.models import ActivityEntry, Estado, Resultado, Tipo
from apps.core.management.commands.sembrar_carga import (
    correo_de_carga,
    proyectos_de_carga,
    usuarios_de_carga,
)
from apps.metrics.models import MetricEntry
from apps.projects.models import Clase, Membership, Project

pytestmark = pytest.mark.django_db

# Se generan al correr las pruebas: ninguna contraseña queda escrita en el repositorio.
CLAVE = secrets.token_urlsafe(16)
VOLUMEN = {"usuarios": 3, "proyectos": 4, "sprints": 2, "actividades_por_sprint": 3}


def sembrar(**opciones) -> str:
    salida = StringIO()
    call_command(
        "sembrar_carga", confirmar=True, password=CLAVE, stdout=salida, **{**VOLUMEN, **opciones}
    )
    return salida.getvalue()


def limpiar() -> str:
    salida = StringIO()
    call_command("sembrar_carga", limpiar=True, confirmar=True, stdout=salida)
    return salida.getvalue()


@pytest.fixture
def datos_reales(crear_usuario):
    """Un usuario y un proyecto que no son de la prueba de carga."""
    ana = crear_usuario("ana")
    proyecto = Project.objects.create(
        creado_por=ana,
        nombre="Gestor SQA",
        periodo_nombre="2026-2",
        fecha_inicio="2026-08-10",
        fecha_fin="2026-12-04",
    )
    Membership.objects.create(project=proyecto, user=ana, clase=Clase.ADMIN_CREADOR)
    MetricEntry.objects.create(project=proyecto, sprint=1, registrado_por=ana)
    ActivityEntry.objects.create(
        project=proyecto,
        sprint=1,
        tipo=Tipo.PRUEBAS,
        estado=Estado.PLANEADA,
        responsable=ana,
        registrado_por=ana,
    )
    return ana, proyecto


# --- Sembrado ---------------------------------------------------------------------------


def test_crea_el_volumen_pedido_y_lo_resume():
    salida = sembrar()

    assert usuarios_de_carga().count() == 3
    assert proyectos_de_carga().count() == 4
    assert MetricEntry.objects.count() == 4 * 2  # 1 por sprint
    assert ActivityEntry.objects.count() == 4 * 2 * 3
    assert "Usuarios creados: 3" in salida
    assert "Proyectos creados: 4" in salida
    assert "Métricas creadas: 8" in salida
    assert "Actividades creadas: 24" in salida
    assert "Quedan en la base: 3 usuarios de carga y 4 proyectos de carga." in salida


def test_cada_usuario_es_miembro_de_al_menos_un_proyecto():
    sembrar()
    for usuario in usuarios_de_carga():
        assert Membership.objects.filter(user=usuario, clase=Clase.ADMIN_CREADOR).exists()


def test_los_usuarios_tienen_correo_inconfundible_y_la_contrasena_dada():
    sembrar()
    usuario = get_user_model().objects.get(email=correo_de_carga(1))
    assert usuario.email == "carga-01@prueba.gestorsqa"
    assert usuario.check_password(CLAVE)


def test_las_actividades_cumplen_el_anexo_b():
    sembrar()
    for actividad in ActivityEntry.objects.all():
        if actividad.estado == Estado.PLANEADA:
            assert actividad.resultado is None
        else:
            assert actividad.resultado in Resultado.values
        if actividad.tipo == Tipo.OTRA:
            assert actividad.nombre_otra
    assert ActivityEntry.objects.filter(estado=Estado.PLANEADA).count() == 4 * 2


def test_es_idempotente():
    sembrar()
    salida = sembrar()

    assert "Usuarios creados: 0" in salida
    assert "Proyectos creados: 0" in salida
    assert "Actividades creadas: 0" in salida
    assert usuarios_de_carga().count() == 3
    assert ActivityEntry.objects.count() == 24


def test_completa_lo_que_falta_si_se_amplia_el_volumen():
    sembrar()
    salida = sembrar(usuarios=4, proyectos=6)
    assert "Usuarios creados: 1" in salida
    assert "Proyectos creados: 2" in salida
    assert proyectos_de_carga().count() == 6


def test_la_contrasena_puede_venir_del_entorno(monkeypatch):
    del_entorno = secrets.token_urlsafe(16)
    monkeypatch.setenv("CARGA_PASSWORD", del_entorno)
    call_command("sembrar_carga", confirmar=True, stdout=StringIO(), **VOLUMEN)
    assert get_user_model().objects.get(email=correo_de_carga(2)).check_password(del_entorno)


def test_el_reporte_de_un_proyecto_sembrado_se_calcula(cliente_de):
    sembrar()
    proyecto = proyectos_de_carga().first()
    response = cliente_de(proyecto.creado_por).get(f"/api/projects/{proyecto.id}/report/")
    assert response.status_code == 200
    assert response.json()["estado_general"] != "SIN_EVALUACION"
    assert len(response.json()["historial"]) == 2


# --- Salvaguardas -----------------------------------------------------------------------


def test_sin_confirmar_no_hace_nada():
    with pytest.raises(CommandError, match="--confirmar"):
        call_command("sembrar_carga", password=CLAVE, stdout=StringIO(), **VOLUMEN)
    with pytest.raises(CommandError, match="--confirmar"):
        call_command("sembrar_carga", limpiar=True, stdout=StringIO())
    assert not usuarios_de_carga().exists()


def test_sin_contrasena_no_hace_nada(monkeypatch):
    monkeypatch.delenv("CARGA_PASSWORD", raising=False)
    with pytest.raises(CommandError, match="CARGA_PASSWORD"):
        call_command("sembrar_carga", confirmar=True, stdout=StringIO(), **VOLUMEN)
    assert not usuarios_de_carga().exists()


def test_menos_proyectos_que_usuarios_no_se_permite():
    with pytest.raises(CommandError, match="al menos tantos proyectos"):
        sembrar(usuarios=5, proyectos=4)


def test_acepta_los_argumentos_como_en_la_terminal():
    """Los volúmenes llegan como texto desde la línea de comandos y se convierten."""
    argumentos = ["--usuarios", "2", "--proyectos", "2", "--sprints", "1"]
    argumentos += ["--actividades-por-sprint", "1", "--password", CLAVE, "--confirmar"]
    call_command("sembrar_carga", *argumentos, stdout=StringIO())
    assert proyectos_de_carga().count() == 2
    assert ActivityEntry.objects.count() == 2


@pytest.mark.parametrize("valor", ["0", "-3", "abc"])
def test_los_volumenes_deben_ser_enteros_positivos(valor):
    with pytest.raises(CommandError):
        call_command("sembrar_carga", "--confirmar", "--usuarios", valor, stdout=StringIO())


# --- Limpieza ---------------------------------------------------------------------------


def test_limpiar_borra_solo_los_datos_de_carga(datos_reales):
    ana, proyecto = datos_reales
    sembrar()
    salida = limpiar()

    assert "Usuarios borrados: 3" in salida
    assert "Proyectos borrados: 4" in salida
    assert "Métricas borradas: 8" in salida
    assert "Actividades borradas: 24" in salida
    assert "Quedan en la base: 0 usuarios de carga y 0 proyectos de carga." in salida

    assert get_user_model().objects.filter(id=ana.id).exists()
    assert Project.objects.filter(id=proyecto.id).exists()
    assert MetricEntry.objects.filter(project=proyecto).count() == 1
    assert ActivityEntry.objects.filter(project=proyecto).count() == 1


def test_limpiar_sin_datos_de_carga_no_falla(datos_reales):
    salida = limpiar()
    assert "Usuarios borrados: 0" in salida
    assert Project.objects.count() == 1


def test_limpiar_no_borra_nada_si_un_usuario_de_carga_tiene_datos_reales(datos_reales):
    ana, proyecto = datos_reales
    sembrar()
    carga = get_user_model().objects.get(email=correo_de_carga(1))
    Membership.objects.create(project=proyecto, user=carga, clase=Clase.COLABORADOR)
    ActivityEntry.objects.create(
        project=proyecto,
        sprint=2,
        tipo=Tipo.CAMINATA,
        estado=Estado.PLANEADA,
        responsable=carga,
        registrado_por=ana,
    )

    with pytest.raises(CommandError, match="no se borró nada"):
        limpiar()
    assert usuarios_de_carga().count() == 3
    assert proyectos_de_carga().count() == 4
