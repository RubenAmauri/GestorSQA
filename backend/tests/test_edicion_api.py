"""Pruebas de edición de proyecto, métricas y actividades (RF-09, HU-08). Catálogo: SQAP 5.1.2 e."""

from decimal import Decimal
from unittest import mock

import pytest
from django.db import IntegrityError

from apps.activities.models import ActivityEntry, Estado, Resultado, Tipo
from apps.metrics.models import MetricEntry
from apps.projects.models import Clase, Membership, Project

pytestmark = pytest.mark.django_db

PROYECTO = "/api/projects/{id}/"
METRICA = "/api/projects/{id}/metrics/{sprint}/"
ACTIVIDAD = "/api/projects/{id}/activities/{actividad}/"

FECHAS = {"fecha_inicio": "2026-08-10", "fecha_fin": "2026-12-04"}


def nuevo_proyecto(creador, nombre="Gestor SQA", periodo="2026-2") -> Project:
    proyecto = Project.objects.create(
        creado_por=creador, nombre=nombre, periodo_nombre=periodo, **FECHAS
    )
    Membership.objects.create(project=proyecto, user=creador, clase=Clase.ADMIN_CREADOR)
    return proyecto


@pytest.fixture
def admin(crear_usuario):
    return crear_usuario("ana")


@pytest.fixture
def proyecto(admin):
    return nuevo_proyecto(admin)


@pytest.fixture
def miembro(proyecto, crear_usuario):
    """miembro(Clase.COLABORADOR) crea un usuario con esa clase en el proyecto."""

    def _miembro(clase: str, nombre: str | None = None):
        usuario = crear_usuario(nombre or clase.lower())
        Membership.objects.create(project=proyecto, user=usuario, clase=clase)
        return usuario

    return _miembro


@pytest.fixture
def metrica(proyecto, admin):
    return MetricEntry.objects.create(
        project=proyecto,
        sprint=1,
        defectos_encontrados=4,
        defectos_corregidos=4,
        horas_correccion=Decimal("14"),
        kloc=Decimal("3.6"),
        cobertura_pct=Decimal("78"),
        registrado_por=admin,
    )


@pytest.fixture
def actividad(proyecto, admin):
    return ActivityEntry.objects.create(
        project=proyecto,
        sprint=1,
        tipo=Tipo.REVISION_CODIGO,
        estado=Estado.REALIZADA,
        resultado=Resultado.SATISFACTORIO,
        responsable=admin,
        registrado_por=admin,
    )


def editar_metrica(cliente, proyecto, sprint, datos):
    return cliente.patch(METRICA.format(id=proyecto.id, sprint=sprint), datos, format="json")


def editar_actividad(cliente, proyecto, actividad, datos):
    ruta = ACTIVIDAD.format(id=proyecto.id, actividad=actividad.id)
    return cliente.patch(ruta, datos, format="json")


def borrar_actividad(cliente, proyecto, actividad):
    return cliente.delete(ACTIVIDAD.format(id=proyecto.id, actividad=actividad.id))


def editar_proyecto(cliente, proyecto, datos):
    return cliente.patch(PROYECTO.format(id=proyecto.id), datos, format="json")


# --- PR-RF09-01 · Admin y Colaborador editan métricas y actividades (HU-08 CA-01) -------


@pytest.mark.parametrize("clase", [Clase.ADMIN_CREADOR, Clase.ADMIN_NORMAL, Clase.COLABORADOR])
def test_pr_rf09_01_editar_metricas(cliente_de, proyecto, admin, miembro, metrica, clase):
    """PR-RF09-01: el cambio queda guardado y lo omitido no cambia."""
    usuario = admin if clase == Clase.ADMIN_CREADOR else miembro(clase)
    response = editar_metrica(cliente_de(usuario), proyecto, 1, {"cobertura_pct": 85})
    assert response.status_code == 200
    assert response.json()["cobertura_pct"] == 85

    metrica.refresh_from_db()
    assert metrica.cobertura_pct == Decimal("85")
    assert metrica.defectos_encontrados == 4
    assert metrica.registrado_por == admin  # quien la registró no cambia al editar


@pytest.mark.parametrize("clase", [Clase.ADMIN_CREADOR, Clase.ADMIN_NORMAL, Clase.COLABORADOR])
def test_pr_rf09_01_editar_actividades(cliente_de, proyecto, admin, miembro, actividad, clase):
    """PR-RF09-01."""
    usuario = admin if clase == Clase.ADMIN_CREADOR else miembro(clase)
    carla = miembro(Clase.COLABORADOR, "carla")
    datos = {
        "resultado": Resultado.CON_HALLAZGOS,
        "hallazgos": "Dos defectos",
        "responsable": carla.id,
    }

    response = editar_actividad(cliente_de(usuario), proyecto, actividad, datos)
    assert response.status_code == 200
    assert response.json()["responsable"] == {"id": carla.id, "email": "carla@correo.com"}

    actividad.refresh_from_db()
    assert actividad.resultado == Resultado.CON_HALLAZGOS
    assert actividad.hallazgos == "Dos defectos"
    assert actividad.responsable == carla
    assert actividad.tipo == Tipo.REVISION_CODIGO
    assert actividad.registrado_por == admin


def test_null_vacia_una_metrica_y_es_distinto_de_cero(cliente_de, proyecto, admin, metrica):
    """Anexo A: vacío (NULL) ≠ 0, también al editar."""
    cliente = cliente_de(admin)
    assert editar_metrica(cliente, proyecto, 1, {"kloc": None}).status_code == 200
    assert editar_metrica(cliente, proyecto, 1, {"defectos_encontrados": 0}).status_code == 200
    metrica.refresh_from_db()
    assert metrica.kloc is None
    assert metrica.defectos_encontrados == 0


@pytest.mark.parametrize(
    "datos",
    [{"cobertura_pct": 101}, {"cobertura_pct": -1}, {"horas_correccion": -2}, {"kloc": "abc"}],
)
def test_metrica_invalida_responde_400(cliente_de, proyecto, admin, metrica, datos):
    response = editar_metrica(cliente_de(admin), proyecto, 1, datos)
    assert response.status_code == 400
    metrica.refresh_from_db()
    assert metrica.cobertura_pct == Decimal("78")


def test_el_sprint_no_se_edita(cliente_de, proyecto, admin, metrica):
    cliente = cliente_de(admin)
    response = editar_metrica(cliente, proyecto, 1, {"sprint": 2, "kloc": "4"})
    assert response.status_code == 400
    assert response.json() == {"sprint": ["El sprint no se edita; viene en la ruta."]}

    # El mismo sprint de la ruta sí se acepta.
    assert editar_metrica(cliente, proyecto, 1, {"sprint": 1, "kloc": "4"}).status_code == 200
    metrica.refresh_from_db()
    assert (metrica.sprint, metrica.kloc) == (1, Decimal("4"))


def test_editar_un_sprint_sin_metricas_responde_404(cliente_de, proyecto, admin, metrica):
    response = editar_metrica(cliente_de(admin), proyecto, 7, {"kloc": "4"})
    assert response.status_code == 404
    assert response.json() == {"detail": "Sprint sin métricas registradas."}


def test_editar_metricas_de_otro_proyecto_responde_404(cliente_de, proyecto, admin, crear_usuario):
    beto = crear_usuario("beto")
    otro = nuevo_proyecto(beto, nombre="Otro")
    MetricEntry.objects.create(project=otro, sprint=1, kloc=Decimal("1"), registrado_por=beto)
    # Ana es Admin de su proyecto, pero el sprint 1 solo existe en el de Beto.
    assert editar_metrica(cliente_de(admin), proyecto, 1, {"kloc": "9"}).status_code == 404
    assert MetricEntry.objects.get(project=otro).kloc == Decimal("1")


def test_editar_una_metrica_cambia_el_reporte(cliente_de, proyecto, admin, metrica):
    """El reporte de salud refleja la edición (RF-11 sobre datos de RF-09)."""
    cliente = cliente_de(admin)
    reporte = f"/api/projects/{proyecto.id}/report/"
    assert cliente.get(reporte).json()["indicadores"]["cobertura"]["valor"] == 78.0

    assert editar_metrica(cliente, proyecto, 1, {"cobertura_pct": 40}).status_code == 200

    assert cliente.get(reporte).json()["indicadores"]["cobertura"]["valor"] == 40.0


# --- Validaciones de actividades sobre el resultado final -------------------------------


def test_pasar_a_planeada_sin_quitar_el_resultado_responde_400(
    cliente_de, proyecto, admin, actividad
):
    response = editar_actividad(cliente_de(admin), proyecto, actividad, {"estado": Estado.PLANEADA})
    assert response.status_code == 400
    assert response.json() == {"resultado": ["Una actividad Planeada no puede tener resultado."]}
    actividad.refresh_from_db()
    assert actividad.estado == Estado.REALIZADA


def test_pasar_a_planeada_quitando_el_resultado_es_valido(cliente_de, proyecto, admin, actividad):
    datos = {"estado": Estado.PLANEADA, "resultado": None}
    assert editar_actividad(cliente_de(admin), proyecto, actividad, datos).status_code == 200
    actividad.refresh_from_db()
    assert (actividad.estado, actividad.resultado) == (Estado.PLANEADA, None)


def test_quitar_el_resultado_de_una_realizada_responde_400(cliente_de, proyecto, admin, actividad):
    response = editar_actividad(cliente_de(admin), proyecto, actividad, {"resultado": None})
    assert response.status_code == 400
    assert "resultado" in response.json()


def test_cambiar_a_otra_exige_nombre(cliente_de, proyecto, admin, actividad):
    cliente = cliente_de(admin)
    response = editar_actividad(cliente, proyecto, actividad, {"tipo": Tipo.OTRA})
    assert response.status_code == 400
    assert "nombre_otra" in response.json()

    datos = {"tipo": Tipo.OTRA, "nombre_otra": "Inspección"}
    assert editar_actividad(cliente, proyecto, actividad, datos).status_code == 200
    actividad.refresh_from_db()
    assert actividad.nombre_mostrado == "Inspección"

    # Al dejar de ser Otra, el nombre no se guarda, igual que en el alta.
    assert editar_actividad(cliente, proyecto, actividad, {"tipo": Tipo.PRUEBAS}).status_code == 200
    actividad.refresh_from_db()
    assert actividad.nombre_otra == ""


def test_responsable_que_no_es_miembro_responde_400(
    cliente_de, proyecto, admin, actividad, crear_usuario
):
    externo = crear_usuario("externo")
    response = editar_actividad(cliente_de(admin), proyecto, actividad, {"responsable": externo.id})
    assert response.status_code == 400
    assert response.json() == {"responsable": ["El responsable debe ser miembro del proyecto."]}
    actividad.refresh_from_db()
    assert actividad.responsable == admin


def test_con_responsable_expulsado_se_editan_los_demas_campos(
    cliente_de, proyecto, admin, miembro, actividad
):
    """El responsable solo se valida si se envía en el cuerpo."""
    carla = miembro(Clase.COLABORADOR, "carla")
    actividad.responsable = carla
    actividad.save()
    Membership.objects.filter(project=proyecto, user=carla).delete()

    datos = {"descripcion": "Revisión del módulo de reportes"}
    assert editar_actividad(cliente_de(admin), proyecto, actividad, datos).status_code == 200
    actividad.refresh_from_db()
    assert actividad.descripcion == "Revisión del módulo de reportes"
    assert actividad.responsable == carla


def test_una_actividad_no_cambia_de_proyecto_por_el_cuerpo(
    cliente_de, proyecto, admin, actividad, crear_usuario
):
    otro = nuevo_proyecto(crear_usuario("beto"), nombre="Otro")
    datos = {"project": otro.id, "proyecto": otro.id, "project_id": otro.id, "sprint": 2}
    assert editar_actividad(cliente_de(admin), proyecto, actividad, datos).status_code == 200
    actividad.refresh_from_db()
    assert actividad.project == proyecto
    assert actividad.sprint == 2


def test_actividad_de_otro_proyecto_responde_404(cliente_de, proyecto, admin, crear_usuario):
    beto = crear_usuario("beto")
    otro = nuevo_proyecto(beto, nombre="Otro")
    ajena = ActivityEntry.objects.create(
        project=otro,
        sprint=1,
        tipo=Tipo.PRUEBAS,
        estado=Estado.PLANEADA,
        responsable=beto,
        registrado_por=beto,
    )
    cliente = cliente_de(admin)

    response = editar_actividad(cliente, proyecto, ajena, {"sprint": 5})
    assert response.status_code == 404
    assert response.json() == {"detail": "Actividad no encontrada."}
    assert borrar_actividad(cliente, proyecto, ajena).status_code == 404
    ajena.refresh_from_db()
    assert ajena.sprint == 1


# --- PR-RF09-02 · Solo un Admin elimina actividades (HU-08 CA-02) ------------------------


def test_pr_rf09_02_colaborador_no_borra_y_admin_si(
    cliente_de, proyecto, admin, miembro, actividad
):
    """PR-RF09-02."""
    colaborador = cliente_de(miembro(Clase.COLABORADOR))
    response = borrar_actividad(colaborador, proyecto, actividad)
    assert response.status_code == 403
    assert ActivityEntry.objects.filter(id=actividad.id).exists()

    assert borrar_actividad(cliente_de(admin), proyecto, actividad).status_code == 204
    assert not ActivityEntry.objects.filter(id=actividad.id).exists()


def test_un_admin_normal_tambien_borra(cliente_de, proyecto, miembro, actividad):
    response = borrar_actividad(cliente_de(miembro(Clase.ADMIN_NORMAL)), proyecto, actividad)
    assert response.status_code == 204


# --- PR-RF09-03 · Solo un Admin edita el proyecto (HU-08 CA-02) --------------------------


@pytest.mark.parametrize("clase", [Clase.ADMIN_CREADOR, Clase.ADMIN_NORMAL])
def test_pr_rf09_03_un_admin_edita_el_proyecto(cliente_de, proyecto, admin, miembro, clase):
    """PR-RF09-03: PATCH parcial; lo omitido no cambia."""
    usuario = admin if clase == Clase.ADMIN_CREADOR else miembro(clase)
    response = editar_proyecto(cliente_de(usuario), proyecto, {"nombre": "Gestor SQA v2"})
    assert response.status_code == 200
    assert response.json()["nombre"] == "Gestor SQA v2"

    proyecto.refresh_from_db()
    assert proyecto.nombre == "Gestor SQA v2"
    assert proyecto.nombre_clave == "gestor sqa v2"
    assert proyecto.periodo_nombre == "2026-2"


def test_pr_rf09_03_un_colaborador_no_edita_el_proyecto(cliente_de, proyecto, miembro):
    """PR-RF09-03."""
    response = editar_proyecto(cliente_de(miembro(Clase.COLABORADOR)), proyecto, {"nombre": "X"})
    assert response.status_code == 403
    proyecto.refresh_from_db()
    assert proyecto.nombre == "Gestor SQA"


@pytest.mark.parametrize("clase", [Clase.ADMIN_CREADOR, Clase.ADMIN_NORMAL])
def test_pr_rf09_03_duplicado_del_mismo_creador_responde_409(
    cliente_de, proyecto, admin, miembro, clase
):
    """PR-RF09-03: la unicidad es por creador, aunque edite un Admin Normal."""
    nuevo_proyecto(admin, nombre="Otro de Ana")
    usuario = admin if clase == Clase.ADMIN_CREADOR else miembro(clase)
    response = editar_proyecto(cliente_de(usuario), proyecto, {"nombre": "  otro DE ana "})
    assert response.status_code == 409
    proyecto.refresh_from_db()
    assert proyecto.nombre == "Gestor SQA"


def test_edicion_simultanea_duplicada_responde_409(cliente_de, proyecto, admin):
    """Si otra petición gana la restricción única entre la revisión y el guardado."""
    with mock.patch.object(Project, "save", side_effect=IntegrityError("duplicado")):
        response = editar_proyecto(cliente_de(admin), proyecto, {"nombre": "Nuevo"})
    assert response.status_code == 409


def test_proyecto_de_otro_creador_con_el_mismo_nombre_no_es_duplicado(
    cliente_de, proyecto, admin, crear_usuario
):
    nuevo_proyecto(crear_usuario("beto"), nombre="Compartido")
    assert editar_proyecto(cliente_de(admin), proyecto, {"nombre": "Compartido"}).status_code == 200


def test_renombrar_al_mismo_nombre_normalizado_no_es_duplicado(cliente_de, proyecto, admin):
    response = editar_proyecto(cliente_de(admin), proyecto, {"nombre": "  GESTOR   sqa "})
    assert response.status_code == 200


@pytest.mark.parametrize(
    "datos",
    [
        {"fecha_fin": "2026-08-01"},
        {"fecha_inicio": "2026-12-05"},
        {"fecha_inicio": "2026-12-04", "fecha_fin": "2026-08-10"},
    ],
)
def test_pr_rf09_03_fechas_invertidas_responden_400(cliente_de, proyecto, admin, datos):
    """PR-RF09-03: fin ≥ inicio se valida contra el resultado final."""
    response = editar_proyecto(cliente_de(admin), proyecto, datos)
    assert response.status_code == 400
    assert "fecha_fin" in response.json()
    proyecto.refresh_from_db()
    assert proyecto.fecha_fin.isoformat() == "2026-12-04"


@pytest.mark.parametrize("datos", [{"nombre": "   "}, {"periodo_nombre": "x" * 51}])
def test_datos_de_proyecto_invalidos_responden_400(cliente_de, proyecto, admin, datos):
    assert editar_proyecto(cliente_de(admin), proyecto, datos).status_code == 400


def test_campos_no_editables_del_proyecto_se_ignoran(cliente_de, proyecto, admin, crear_usuario):
    """El código solo cambia al regenerarlo (RF-03); id y creador no cambian por esta vía."""
    codigo = proyecto.codigo_union
    datos = {
        "codigo_union": "AAAAAAAAAA",
        "creado_por": crear_usuario("beto").id,
        "id": proyecto.id + 100,
        "nombre": "Renombrado",
    }
    response = editar_proyecto(cliente_de(admin), proyecto, datos)
    assert response.status_code == 200
    assert response.json()["codigo_union"] == codigo

    proyecto.refresh_from_db()
    assert (proyecto.nombre, proyecto.codigo_union, proyecto.creado_por) == (
        "Renombrado",
        codigo,
        admin,
    )
    assert not Project.objects.filter(id=proyecto.id + 100).exists()
