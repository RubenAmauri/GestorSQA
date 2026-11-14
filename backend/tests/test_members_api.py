"""Pruebas de gestión de miembros y solo lectura del Auditor (RF-04, RF-05, HU-03, CLU-04).

Catálogo: SQAP 5.1.2 e.
"""

import pytest

from apps.activities.models import ActivityEntry, Estado, Resultado, Tipo
from apps.metrics.models import MetricEntry
from apps.projects.models import Clase, Membership, Project

pytestmark = pytest.mark.django_db

MIEMBROS = "/api/projects/{id}/members/"
MIEMBRO = "/api/projects/{id}/members/{miembro}/"


@pytest.fixture
def proyecto(crear_usuario):
    ana = crear_usuario("ana")
    proyecto = Project.objects.create(
        creado_por=ana,
        nombre="Gestor SQA",
        periodo_nombre="2026-2",
        fecha_inicio="2026-08-10",
        fecha_fin="2026-12-04",
    )
    Membership.objects.create(project=proyecto, user=ana, clase=Clase.ADMIN_CREADOR)
    return proyecto


@pytest.fixture
def creador(proyecto):
    return Membership.objects.get(project=proyecto, clase=Clase.ADMIN_CREADOR)


@pytest.fixture
def miembro(proyecto, crear_usuario):
    """miembro(Clase.AUDITOR) crea un usuario con esa clase y devuelve su membresía."""

    def _miembro(clase: str, nombre: str | None = None) -> Membership:
        usuario = crear_usuario(nombre or clase.lower())
        return Membership.objects.create(project=proyecto, user=usuario, clase=clase)

    return _miembro


def cambiar_clase(cliente, proyecto, objetivo, clase):
    ruta = MIEMBRO.format(id=proyecto.id, miembro=objetivo.id)
    return cliente.patch(ruta, {"clase": clase}, format="json")


def expulsar(cliente, proyecto, objetivo):
    return cliente.delete(MIEMBRO.format(id=proyecto.id, miembro=objetivo.id))


def clase_actual(membresia: Membership) -> str:
    membresia.refresh_from_db()
    return membresia.clase


# --- Consulta de miembros (CLU-04) ------------------------------------------------------


@pytest.mark.parametrize("clase", [Clase.ADMIN_NORMAL, Clase.COLABORADOR, Clase.AUDITOR])
def test_cualquier_miembro_consulta_la_lista(cliente_de, proyecto, creador, miembro, clase):
    yo = miembro(clase)
    response = cliente_de(yo.user).get(MIEMBROS.format(id=proyecto.id))
    assert response.status_code == 200
    assert response.json() == [
        {"id": creador.id, "correo": "ana@correo.com", "clase": Clase.ADMIN_CREADOR},
        {"id": yo.id, "correo": yo.user.email, "clase": clase},
    ]


def test_la_lista_no_incluye_miembros_de_otros_proyectos(
    cliente_de, proyecto, creador, crear_usuario
):
    beto = crear_usuario("beto")
    otro = Project.objects.create(
        creado_por=beto,
        nombre="Otro",
        periodo_nombre="2026-2",
        fecha_inicio="2026-08-10",
        fecha_fin="2026-12-04",
    )
    Membership.objects.create(project=otro, user=beto, clase=Clase.ADMIN_CREADOR)

    listado = cliente_de(creador.user).get(MIEMBROS.format(id=proyecto.id)).json()
    assert [m["correo"] for m in listado] == ["ana@correo.com"]


def test_la_lista_no_hace_una_consulta_por_miembro(
    cliente_de, proyecto, creador, miembro, django_assert_max_num_queries
):
    for numero in range(10):
        miembro(Clase.COLABORADOR, f"colaborador{numero}")
    cliente = cliente_de(creador.user)
    # Sesión, usuario, membresía propia y la lista: no crece con el número de miembros.
    with django_assert_max_num_queries(4):
        response = cliente.get(MIEMBROS.format(id=proyecto.id))
    assert len(response.json()) == 11


# --- RF-04 · Gestión de miembros (HU-03) ------------------------------------------------


@pytest.mark.parametrize("gestor", [Clase.ADMIN_CREADOR, Clase.ADMIN_NORMAL])
def test_pr_rf04_01_un_admin_cambia_clases_y_promueve(
    cliente_de, proyecto, creador, miembro, gestor
):
    """PR-RF04-01 (HU-03 CA-01): el Admin Creador y un Admin Normal pueden gestionar."""
    yo = creador if gestor == Clase.ADMIN_CREADOR else miembro(Clase.ADMIN_NORMAL, "gestor")
    cliente = cliente_de(yo.user)
    objetivo = miembro(Clase.COLABORADOR, "carla")

    response = cambiar_clase(cliente, proyecto, objetivo, Clase.ADMIN_NORMAL)
    assert response.status_code == 200
    assert response.json() == {
        "id": objetivo.id,
        "correo": "carla@correo.com",
        "clase": Clase.ADMIN_NORMAL,
    }
    assert clase_actual(objetivo) == Clase.ADMIN_NORMAL

    for clase in (Clase.AUDITOR, Clase.COLABORADOR):
        assert cambiar_clase(cliente, proyecto, objetivo, clase).status_code == 200
        assert clase_actual(objetivo) == clase


@pytest.mark.parametrize("gestor", [Clase.ADMIN_CREADOR, Clase.ADMIN_NORMAL])
def test_un_admin_expulsa_a_un_miembro(cliente_de, proyecto, creador, miembro, gestor):
    yo = creador if gestor == Clase.ADMIN_CREADOR else miembro(Clase.ADMIN_NORMAL, "gestor")
    objetivo = miembro(Clase.AUDITOR, "dario")
    response = expulsar(cliente_de(yo.user), proyecto, objetivo)
    assert response.status_code == 204
    assert not Membership.objects.filter(id=objetivo.id).exists()


def test_pr_rf04_02_nadie_modifica_ni_expulsa_al_admin_creador(
    cliente_de, proyecto, creador, miembro
):
    """PR-RF04-02 (HU-03 CA-02): ni siquiera un Admin Normal."""
    cliente = cliente_de(miembro(Clase.ADMIN_NORMAL).user)

    response = cambiar_clase(cliente, proyecto, creador, Clase.COLABORADOR)
    assert response.status_code == 403
    assert response.json() == {"detail": "No se puede cambiar ni expulsar al Admin Creador."}
    assert expulsar(cliente, proyecto, creador).status_code == 403
    assert clase_actual(creador) == Clase.ADMIN_CREADOR


@pytest.mark.parametrize("gestor", [Clase.ADMIN_CREADOR, Clase.ADMIN_NORMAL])
def test_pr_rf04_03_un_admin_no_se_modifica_ni_se_expulsa_a_si_mismo(
    cliente_de, creador, miembro, proyecto, gestor
):
    """PR-RF04-03 (HU-03 CA-02)."""
    yo = creador if gestor == Clase.ADMIN_CREADOR else miembro(Clase.ADMIN_NORMAL, "gestor")
    cliente = cliente_de(yo.user)

    response = cambiar_clase(cliente, proyecto, yo, Clase.AUDITOR)
    assert response.status_code == 403
    assert expulsar(cliente, proyecto, yo).status_code == 403
    assert clase_actual(yo) == gestor
    if gestor == Clase.ADMIN_NORMAL:
        # Para el Admin Creador gana la regla de PR-RF04-02, con su propio mensaje.
        mensaje = response.json()["detail"]
        assert mensaje == "No puedes cambiar tu propia clase ni expulsarte del proyecto."


def test_pr_rf04_04_un_colaborador_no_gestiona_miembros(cliente_de, proyecto, miembro):
    """PR-RF04-04."""
    cliente = cliente_de(miembro(Clase.COLABORADOR, "carla").user)
    objetivo = miembro(Clase.AUDITOR, "dario")

    response = cambiar_clase(cliente, proyecto, objetivo, Clase.ADMIN_NORMAL)
    assert response.status_code == 403
    assert response.json() == {"detail": "Tu clase en este proyecto no permite esta acción."}
    assert expulsar(cliente, proyecto, objetivo).status_code == 403
    assert clase_actual(objetivo) == Clase.AUDITOR


def test_pr_rf04_05_un_expulsado_pierde_el_acceso(cliente_de, proyecto, creador, miembro):
    """PR-RF04-05 (HU-03 CA-03): 404 en el detalle del proyecto y en el reporte."""
    expulsado = miembro(Clase.COLABORADOR, "carla")
    cliente_expulsado = cliente_de(expulsado.user)
    assert cliente_expulsado.get(f"/api/projects/{proyecto.id}/").status_code == 200

    assert expulsar(cliente_de(creador.user), proyecto, expulsado).status_code == 204

    assert cliente_expulsado.get(f"/api/projects/{proyecto.id}/").status_code == 404
    assert cliente_expulsado.get(f"/api/projects/{proyecto.id}/report/").status_code == 404


@pytest.mark.parametrize("clase", ["DIOS", "", "admin_normal", None])
def test_clase_invalida_responde_400(cliente_de, proyecto, creador, miembro, clase):
    objetivo = miembro(Clase.COLABORADOR, "carla")
    response = cambiar_clase(cliente_de(creador.user), proyecto, objetivo, clase)
    assert response.status_code == 400
    assert "clase" in response.json()
    assert clase_actual(objetivo) == Clase.COLABORADOR


def test_sin_clase_responde_400(cliente_de, proyecto, creador, miembro):
    objetivo = miembro(Clase.COLABORADOR, "carla")
    ruta = MIEMBRO.format(id=proyecto.id, miembro=objetivo.id)
    response = cliente_de(creador.user).patch(ruta, {}, format="json")
    assert response.status_code == 400
    assert "clase" in response.json()


def test_asignar_admin_creador_responde_400(cliente_de, proyecto, creador, miembro):
    """HU-03 CA-01: el Admin Creador no se asigna."""
    objetivo = miembro(Clase.ADMIN_NORMAL, "beto")
    response = cambiar_clase(cliente_de(creador.user), proyecto, objetivo, Clase.ADMIN_CREADOR)
    assert response.status_code == 400
    assert response.json() == {
        "clase": ["Solo puedes asignar Admin Normal, Colaborador o Auditor."]
    }
    assert clase_actual(objetivo) == Clase.ADMIN_NORMAL


def test_membresia_de_otro_proyecto_responde_404(cliente_de, proyecto, creador, crear_usuario):
    """No se revela ni se toca una membresía ajena, aunque quien pregunta sea Admin."""
    beto = crear_usuario("beto")
    otro = Project.objects.create(
        creado_por=beto,
        nombre="Otro",
        periodo_nombre="2026-2",
        fecha_inicio="2026-08-10",
        fecha_fin="2026-12-04",
    )
    Membership.objects.create(project=otro, user=beto, clase=Clase.ADMIN_CREADOR)
    ajena = Membership.objects.create(
        project=otro, user=crear_usuario("carla"), clase=Clase.COLABORADOR
    )
    cliente = cliente_de(creador.user)

    response = cambiar_clase(cliente, proyecto, ajena, Clase.AUDITOR)
    assert response.status_code == 404
    assert response.json() == {"detail": "Miembro no encontrado."}
    assert expulsar(cliente, proyecto, ajena).status_code == 404
    assert clase_actual(ajena) == Clase.COLABORADOR


def test_membresia_inexistente_responde_404(cliente_de, proyecto, creador):
    ruta = MIEMBRO.format(id=proyecto.id, miembro=999999)
    assert cliente_de(creador.user).delete(ruta).status_code == 404


# --- RF-05 · El Auditor solo lee --------------------------------------------------------

# Toda escritura del proyecto. Cada caso recibe el contexto y devuelve la ruta y un cuerpo
# válido, para que el 403 no lo tape un error de validación.
# RF-09: agregar aquí editar el proyecto y eliminar actividades cuando existan.
ESCRITURAS_DEL_PROYECTO = [
    pytest.param(
        "post",
        lambda c: ("/api/projects/{id}/metrics/", {"sprint": 1, "cobertura_pct": 80}),
        id="crear-metrica",
    ),
    pytest.param(
        "post",
        lambda c: (
            "/api/projects/{id}/activities/",
            {
                "sprint": 1,
                "tipo": Tipo.REVISION_CODIGO,
                "estado": Estado.REALIZADA,
                "resultado": Resultado.SATISFACTORIO,
                "responsable": c["auditor"].user_id,
            },
        ),
        id="crear-actividad",
    ),
    pytest.param(
        "post",
        lambda c: ("/api/projects/{id}/codigo/regenerar/", {}),
        id="regenerar-codigo",
    ),
    pytest.param(
        "patch",
        lambda c: (f"/api/projects/{{id}}/members/{c['otro'].id}/", {"clase": Clase.AUDITOR}),
        id="cambiar-clase",
    ),
    pytest.param(
        "delete",
        lambda c: (f"/api/projects/{{id}}/members/{c['otro'].id}/", None),
        id="expulsar",
    ),
]


def estado_del_proyecto(proyecto: Project) -> tuple:
    proyecto.refresh_from_db()
    return (
        proyecto.codigo_union,
        MetricEntry.objects.filter(project=proyecto).count(),
        ActivityEntry.objects.filter(project=proyecto).count(),
        sorted(Membership.objects.filter(project=proyecto).values_list("id", "clase")),
    )


@pytest.mark.parametrize(("metodo", "caso"), ESCRITURAS_DEL_PROYECTO)
def test_pr_rf05_01_el_auditor_no_escribe(cliente_de, proyecto, miembro, metodo, caso):
    """PR-RF05-01: el Auditor recibe 403 en toda escritura y no cambia nada."""
    contexto = {"auditor": miembro(Clase.AUDITOR), "otro": miembro(Clase.COLABORADOR)}
    ruta, cuerpo = caso(contexto)
    antes = estado_del_proyecto(proyecto)

    cliente = cliente_de(contexto["auditor"].user)
    response = getattr(cliente, metodo)(ruta.format(id=proyecto.id), cuerpo, format="json")

    assert response.status_code == 403
    assert estado_del_proyecto(proyecto) == antes


def test_pr_rf05_01_el_auditor_si_consulta_los_miembros(cliente_de, proyecto, miembro):
    """PR-RF05-01 y CLU-04: el Auditor puede leer la lista de miembros."""
    auditor = miembro(Clase.AUDITOR)
    response = cliente_de(auditor.user).get(MIEMBROS.format(id=proyecto.id))
    assert response.status_code == 200
    assert len(response.json()) == 2
