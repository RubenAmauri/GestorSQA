"""Pruebas de actividades SQA (RF-08, HU-04, HU-05; Anexo B). Catálogo: SQAP 5.1.2 e."""

import pytest
from django.db import IntegrityError, transaction

from apps.activities.models import ActivityEntry, Estado, Resultado, Tipo
from apps.projects.models import Clase, Membership, Project
from apps.reports import salud

pytestmark = pytest.mark.django_db

RUTA = "/api/projects/{id}/activities/"


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
def miembro(proyecto, crear_usuario):
    """miembro(Clase.AUDITOR) crea un usuario con esa clase en el proyecto."""

    def _miembro(clase: str, nombre: str | None = None):
        usuario = crear_usuario(nombre or clase.lower())
        Membership.objects.create(project=proyecto, user=usuario, clase=clase)
        return usuario

    return _miembro


@pytest.fixture
def admin(proyecto):
    return proyecto.creado_por


@pytest.fixture
def cliente_admin(cliente_de, admin):
    return cliente_de(admin)


def datos_validos(responsable, **cambios) -> dict:
    return {
        "sprint": 1,
        "tipo": Tipo.REVISION_CODIGO,
        "estado": Estado.REALIZADA,
        "resultado": Resultado.SATISFACTORIO,
        "responsable": responsable.id,
        **cambios,
    }


def registrar(cliente, proyecto, datos):
    return cliente.post(RUTA.format(id=proyecto.id), datos, format="json")


# --- Registro válido y permisos (HU-04) ----------------------------------------------


def test_registro_valido_responde_201(cliente_admin, proyecto, admin, miembro):
    responsable = miembro(Clase.COLABORADOR, "carla")
    response = registrar(
        cliente_admin,
        proyecto,
        datos_validos(
            responsable,
            fecha="2026-09-01",
            descripcion="Revisión del módulo de cuentas",
            hallazgos="Dos nombres poco claros",
            evidencia_url="https://github.com/RubenAmauri/GestorSQA/pull/8",
            resultado=Resultado.CON_HALLAZGOS,
        ),
    )
    assert response.status_code == 201
    datos = response.json()
    assert datos["tipo"] == "REVISION_CODIGO"
    assert datos["nombre"] == "Revisión de código"
    assert datos["estado"] == "REALIZADA"
    assert datos["resultado"] == "CON_HALLAZGOS"
    assert datos["fecha"] == "2026-09-01"
    assert datos["responsable"] == {"id": responsable.id, "email": "carla@correo.com"}
    assert datos["registrado_por"] == {"id": admin.id, "email": admin.email}

    actividad = ActivityEntry.objects.get()
    assert actividad.project == proyecto
    assert actividad.registrado_por == admin
    assert str(actividad) == "Sprint 1 · Revisión de código · Realizada"


def test_planeada_sin_resultado_se_guarda_con_resultado_nulo(cliente_admin, proyecto, admin):
    response = registrar(
        cliente_admin,
        proyecto,
        datos_validos(admin, estado=Estado.PLANEADA, resultado="", tipo=Tipo.PRUEBAS),
    )
    assert response.status_code == 201
    assert response.json()["resultado"] is None
    assert ActivityEntry.objects.get().resultado is None


@pytest.mark.parametrize("clase", [Clase.ADMIN_NORMAL, Clase.COLABORADOR])
def test_admin_normal_y_colaborador_pueden_registrar(cliente_de, proyecto, miembro, clase):
    usuario = miembro(clase)
    response = registrar(cliente_de(usuario), proyecto, datos_validos(usuario))
    assert response.status_code == 201


def test_auditor_recibe_403_al_registrar(cliente_de, proyecto, miembro):
    """HU-04: el Auditor solo consulta (SDS 3.4, 403 miembro sin permiso)."""
    auditor = miembro(Clase.AUDITOR)
    response = registrar(cliente_de(auditor), proyecto, datos_validos(auditor))
    assert response.status_code == 403
    assert not ActivityEntry.objects.exists()


# --- Validaciones del Anexo B (PR-RF08-01 a 04) ---------------------------------------


def test_pr_rf08_01_realizada_sin_resultado_responde_400(cliente_admin, proyecto, admin):
    """PR-RF08-01 (HU-04 CA-02)."""
    datos = datos_validos(admin)
    del datos["resultado"]
    response = registrar(cliente_admin, proyecto, datos)
    assert response.status_code == 400
    assert "resultado" in response.json()
    assert not ActivityEntry.objects.exists()


def test_pr_rf08_02_planeada_con_resultado_responde_400(cliente_admin, proyecto, admin):
    """PR-RF08-02 (HU-04 CA-02)."""
    response = registrar(
        cliente_admin,
        proyecto,
        datos_validos(admin, estado=Estado.PLANEADA, resultado=Resultado.SATISFACTORIO),
    )
    assert response.status_code == 400
    assert "resultado" in response.json()
    assert not ActivityEntry.objects.exists()


@pytest.mark.parametrize("nombre", [None, "", "   "])
def test_pr_rf08_03_otra_sin_nombre_responde_400(cliente_admin, proyecto, admin, nombre):
    """PR-RF08-03 (HU-04 CA-01): sin nombre, vacío o solo espacios."""
    datos = datos_validos(admin, tipo=Tipo.OTRA)
    if nombre is not None:
        datos["nombre_otra"] = nombre
    response = registrar(cliente_admin, proyecto, datos)
    assert response.status_code == 400
    assert "nombre_otra" in response.json()


def test_otra_con_nombre_es_valida(cliente_admin, proyecto, admin):
    response = registrar(
        cliente_admin, proyecto, datos_validos(admin, tipo=Tipo.OTRA, nombre_otra="  Retro  ")
    )
    assert response.status_code == 201
    assert response.json()["nombre"] == "Retro"


def test_nombre_otra_no_se_guarda_si_el_tipo_no_es_otra(cliente_admin, proyecto, admin):
    response = registrar(cliente_admin, proyecto, datos_validos(admin, nombre_otra="Sobra"))
    assert response.status_code == 201
    assert response.json()["nombre_otra"] == ""


def test_pr_rf08_04_responsable_que_no_es_miembro_responde_400(
    cliente_admin, proyecto, admin, crear_usuario
):
    """PR-RF08-04 (HU-04 CA-03): un usuario ajeno y un id inexistente dan el mismo error."""
    ajeno = crear_usuario("ajeno")
    con_ajeno = registrar(cliente_admin, proyecto, datos_validos(ajeno))
    inexistente = {**datos_validos(admin), "responsable": 999999}
    con_inexistente = registrar(cliente_admin, proyecto, inexistente)
    assert con_ajeno.status_code == 400
    assert con_inexistente.status_code == 400
    assert con_ajeno.json() == con_inexistente.json()
    assert "responsable" in con_ajeno.json()
    assert not ActivityEntry.objects.exists()


def test_responsable_de_otro_proyecto_no_es_valido(cliente_admin, proyecto, admin, crear_usuario):
    """Ser miembro de otro proyecto no basta: debe serlo de este."""
    beto = crear_usuario("beto")
    otro = Project.objects.create(
        creado_por=beto,
        nombre="Otro",
        periodo_nombre="2026-2",
        fecha_inicio="2026-08-10",
        fecha_fin="2026-12-04",
    )
    Membership.objects.create(project=otro, user=beto, clase=Clase.ADMIN_CREADOR)
    assert registrar(cliente_admin, proyecto, datos_validos(beto)).status_code == 400


@pytest.mark.parametrize(
    "cambios",
    [
        {"sprint": 0},
        {"sprint": -1},
        {"sprint": "uno"},
        {"tipo": "INVENTADA"},
        {"estado": "EN_CURSO"},
        {"resultado": "REGULAR"},
        {"evidencia_url": "no-es-url"},
        {"fecha": "31/12/2026"},
    ],
)
def test_datos_invalidos_responden_400(cliente_admin, proyecto, admin, cambios):
    """Sprint < 1 (HU-04 CA-03) y valores fuera del catálogo (HU-04 CA-01)."""
    response = registrar(cliente_admin, proyecto, datos_validos(admin, **cambios))
    assert response.status_code == 400
    assert set(cambios) <= set(response.json())


@pytest.mark.parametrize("campo", ["sprint", "tipo", "estado", "responsable"])
def test_campos_obligatorios(cliente_admin, proyecto, admin, campo):
    datos = datos_validos(admin)
    del datos[campo]
    assert registrar(cliente_admin, proyecto, datos).status_code == 400


# --- Consulta y filtros (HU-05, PR-RF08-05) -------------------------------------------


@pytest.fixture
def varias_actividades(proyecto, admin):
    def crear(sprint, estado, resultado=None):
        return ActivityEntry.objects.create(
            project=proyecto,
            sprint=sprint,
            tipo=Tipo.PRUEBAS,
            estado=estado,
            resultado=resultado,
            responsable=admin,
            registrado_por=admin,
        )

    return [
        crear(1, Estado.REALIZADA, Resultado.SATISFACTORIO),
        crear(1, Estado.PLANEADA),
        crear(2, Estado.REALIZADA, Resultado.NO_SATISFACTORIO),
        crear(2, Estado.PLANEADA),
        crear(3, Estado.PLANEADA),
    ]


def ids(response) -> list[int]:
    return [a["id"] for a in response.json()]


def test_cualquier_miembro_ve_todas_las_actividades(
    cliente_de, proyecto, miembro, varias_actividades
):
    """HU-05 CA-01: el Auditor también consulta; cada actividad trae los campos de la tabla."""
    response = cliente_de(miembro(Clase.AUDITOR)).get(RUTA.format(id=proyecto.id))
    assert response.status_code == 200
    assert ids(response) == [a.id for a in varias_actividades]
    primera = response.json()[0]
    assert {"tipo", "sprint", "estado", "responsable", "resultado"} <= set(primera)


def test_pr_rf08_05_filtros_por_sprint_y_por_estado(cliente_admin, proyecto, varias_actividades):
    """PR-RF08-05 (HU-05 CA-02): por sprint, por estado y ambos a la vez."""
    a = varias_actividades
    ruta = RUTA.format(id=proyecto.id)
    assert ids(cliente_admin.get(ruta, {"sprint": 2})) == [a[2].id, a[3].id]
    assert ids(cliente_admin.get(ruta, {"estado": "PLANEADA"})) == [a[1].id, a[3].id, a[4].id]
    assert ids(cliente_admin.get(ruta, {"sprint": 1, "estado": "REALIZADA"})) == [a[0].id]
    assert cliente_admin.get(ruta, {"sprint": 9}).json() == []


@pytest.mark.parametrize("filtros", [{"sprint": "dos"}, {"sprint": 0}, {"estado": "HECHA"}])
def test_filtro_invalido_responde_400(cliente_admin, proyecto, filtros):
    assert cliente_admin.get(RUTA.format(id=proyecto.id), filtros).status_code == 400


def test_no_se_ven_actividades_de_otros_proyectos(
    cliente_de, crear_usuario, proyecto, varias_actividades
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
    response = cliente_de(beto).get(RUTA.format(id=otro.id))
    assert response.status_code == 200
    assert response.json() == []


# --- Integridad en la base de datos y compatibilidad con el motor de salud -------------


@pytest.mark.parametrize(
    "campos",
    [
        {"sprint": 0},
        {"estado": Estado.REALIZADA, "resultado": None},
        {"estado": Estado.PLANEADA, "resultado": Resultado.SATISFACTORIO},
        {"tipo": Tipo.OTRA, "nombre_otra": ""},
    ],
)
def test_la_base_de_datos_rechaza_actividades_invalidas(proyecto, admin, campos):
    """Las reglas del Anexo B también son restricciones de la tabla, no solo de la API."""
    base = {"sprint": 1, "tipo": Tipo.PRUEBAS, "estado": Estado.PLANEADA, "resultado": None}
    with pytest.raises(IntegrityError), transaction.atomic():
        ActivityEntry.objects.create(
            project=proyecto, responsable=admin, registrado_por=admin, **{**base, **campos}
        )


def test_valores_iguales_a_los_del_motor_de_salud():
    """El reporte pasa estado y resultado a salud.py sin traducir."""
    assert set(Estado.values) == {e.value for e in salud.EstadoActividad}
    assert set(Resultado.values) == {r.value for r in salud.Resultado}
    assert set(Tipo.values) == {
        "CAMINATA",
        "REVISION_CODIGO",
        "AUDITORIA_CONFIGURACION",
        "PRUEBAS",
        "OTRA",
    }
