"""Datos de la prueba de carga PR-RNF02-01 (RNF-02; SQAP 5.1.2 e).

Por omisión crea el volumen del RNF-02: 50 usuarios de prueba y 100 proyectos con 10
sprints cada uno; cada sprint con 1 registro de métricas y 5 actividades. Todo lo que
crea se reconoce por el correo de sus usuarios (carga-NN@prueba.gestorsqa), y
``--limpiar`` borra solo eso. Guía de uso en pruebas/carga/README.md.

Exige ``--confirmar`` para que nadie lo corra por accidente en producción, y la
contraseña de los usuarios de prueba llega por argumento o por la variable de entorno
CARGA_PASSWORD, nunca desde el código.
"""

import argparse
import os
from collections import Counter
from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.db.models import ProtectedError

from apps.activities.models import ActivityEntry, Estado, Resultado, Tipo
from apps.metrics.models import MetricEntry
from apps.projects.models import Clase, Membership, Project

PREFIJO = "carga-"
DOMINIO = "@prueba.gestorsqa"
VARIABLE_PASSWORD = "CARGA_PASSWORD"
PERIODO = "Prueba de carga"
FECHA_INICIO = date(2026, 8, 10)
FECHA_FIN = date(2026, 12, 4)

TIPOS = [Tipo.CAMINATA, Tipo.REVISION_CODIGO, Tipo.AUDITORIA_CONFIGURACION, Tipo.PRUEBAS, Tipo.OTRA]
RESULTADOS = [Resultado.SATISFACTORIO, Resultado.CON_HALLAZGOS, Resultado.NO_SATISFACTORIO]

MENSAJE_SIN_CONFIRMAR = (
    "Este comando crea o borra datos de prueba en la base de datos configurada. "
    "Vuelve a correrlo con --confirmar si es lo que quieres (en producción, después "
    "de ./respaldo.sh)."
)
MENSAJE_SIN_PASSWORD = (
    f"Falta la contraseña de los usuarios de prueba: usa la variable de entorno "
    f"{VARIABLE_PASSWORD} (recomendado) o --password."
)
MENSAJE_POCOS_PROYECTOS = (
    "Se necesitan al menos tantos proyectos como usuarios, para que cada usuario sea "
    "miembro de un proyecto."
)
MENSAJE_PROTEGIDO = (
    "Un usuario de carga es responsable o autor de datos fuera de la prueba de carga; "
    "no se borró nada. Reasigna esos datos y vuelve a intentarlo."
)


def correo_de_carga(numero: int) -> str:
    return f"{PREFIJO}{numero:02d}{DOMINIO}"


def usuarios_de_carga():
    return get_user_model().objects.filter(email__startswith=PREFIJO, email__endswith=DOMINIO)


def proyectos_de_carga():
    return Project.objects.filter(creado_por__in=usuarios_de_carga())


def _positivo(texto: str) -> int:
    valor = int(texto)
    if valor < 1:
        raise argparse.ArgumentTypeError("debe ser un entero mayor que cero")
    return valor


class Command(BaseCommand):
    help = "Crea (o con --limpiar, borra) los datos de la prueba de carga PR-RNF02-01."

    def add_arguments(self, parser) -> None:
        parser.add_argument("--usuarios", type=_positivo, default=50)
        parser.add_argument("--proyectos", type=_positivo, default=100)
        parser.add_argument("--sprints", type=_positivo, default=10)
        parser.add_argument("--actividades-por-sprint", type=_positivo, default=5)
        parser.add_argument(
            "--password", help=f"Contraseña de los usuarios de prueba (mejor: {VARIABLE_PASSWORD})."
        )
        parser.add_argument("--limpiar", action="store_true", help="Borra solo los datos de carga.")
        parser.add_argument("--confirmar", action="store_true", help="Obligatorio para ejecutar.")

    def handle(self, *args, **opciones) -> None:
        if not opciones["confirmar"]:
            raise CommandError(MENSAJE_SIN_CONFIRMAR)
        if opciones["limpiar"]:
            self._resumen("Limpieza de la prueba de carga (PR-RNF02-01)", "borrad", limpiar())
            return
        if opciones["proyectos"] < opciones["usuarios"]:
            raise CommandError(MENSAJE_POCOS_PROYECTOS)
        password = opciones["password"] or os.environ.get(VARIABLE_PASSWORD)
        if not password:
            raise CommandError(MENSAJE_SIN_PASSWORD)
        creados = sembrar(
            opciones["usuarios"],
            opciones["proyectos"],
            opciones["sprints"],
            opciones["actividades_por_sprint"],
            password,
        )
        self._resumen("Sembrado de la prueba de carga (PR-RNF02-01)", "cread", creados)

    def _resumen(self, titulo: str, raiz: str, cuentas: Counter) -> None:
        """Resumen para pegar como evidencia: lo que hizo y lo que queda en la base.

        ``raiz`` es el participio sin terminación ("cread", "borrad"), para concordar
        en género con cada sustantivo.
        """
        self.stdout.write(titulo)
        for clave, etiqueta, terminacion in [
            ("usuarios", "Usuarios", "os"),
            ("proyectos", "Proyectos", "os"),
            ("metricas", "Métricas", "as"),
            ("actividades", "Actividades", "as"),
        ]:
            self.stdout.write(f"  {etiqueta} {raiz}{terminacion}: {cuentas[clave]}")
        self.stdout.write(
            f"Quedan en la base: {usuarios_de_carga().count()} usuarios de carga y "
            f"{proyectos_de_carga().count()} proyectos de carga."
        )


@transaction.atomic
def sembrar(
    usuarios: int, proyectos: int, sprints: int, actividades: int, password: str
) -> Counter:
    """Crea lo que falte; lo que ya existe no se duplica ni se modifica."""
    creados: Counter = Counter()
    cuentas = [_cuenta(numero, password, creados) for numero in range(1, usuarios + 1)]
    for numero in range(1, proyectos + 1):
        # Reparto circular: con proyectos >= usuarios, todos son miembros de algún proyecto.
        creador = cuentas[(numero - 1) % usuarios]
        proyecto = _proyecto_nuevo(numero, creador)
        if proyecto is None:
            continue
        creados["proyectos"] += 1
        metricas = [_metrica(proyecto, creador, sprint) for sprint in range(1, sprints + 1)]
        creados["metricas"] += len(MetricEntry.objects.bulk_create(metricas))
        lista = [
            _actividad(proyecto, creador, sprint, indice)
            for sprint in range(1, sprints + 1)
            for indice in range(actividades)
        ]
        creados["actividades"] += len(ActivityEntry.objects.bulk_create(lista))
    return creados


def _cuenta(numero: int, password: str, creados: Counter):
    """La contraseña solo se fija al crear la cuenta (ver el README)."""
    usuarios = get_user_model().objects
    correo = correo_de_carga(numero)
    cuenta = usuarios.filter(email=correo).first()
    if cuenta is None:
        cuenta = usuarios.create_user(correo, password)
        creados["usuarios"] += 1
    return cuenta


def _proyecto_nuevo(numero: int, creador) -> Project | None:
    nombre = f"Carga {numero:03d}"
    # Se busca por nombre entre todos los proyectos de carga, no por creador: si cambia el
    # número de usuarios, el reparto circular le asignaría otro creador y lo duplicaría.
    if proyectos_de_carga().filter(nombre=nombre).exists():
        return None
    proyecto = Project.objects.create(
        creado_por=creador,
        nombre=nombre,
        periodo_nombre=PERIODO,
        fecha_inicio=FECHA_INICIO,
        fecha_fin=FECHA_FIN,
    )
    Membership.objects.create(project=proyecto, user=creador, clase=Clase.ADMIN_CREADOR)
    return proyecto


def _metrica(proyecto: Project, creador, sprint: int) -> MetricEntry:
    """Valores deterministas y variados, para que el motor de salud calcule de todo."""
    encontrados = (proyecto.id + sprint) % 9 + 1
    return MetricEntry(
        project=proyecto,
        sprint=sprint,
        defectos_encontrados=encontrados,
        defectos_corregidos=encontrados - sprint % 2,
        horas_correccion=Decimal(encontrados * 2),
        kloc=Decimal(sprint) * Decimal("0.8") + Decimal("0.5"),
        cobertura_pct=Decimal(50 + (proyecto.id * 7 + sprint * 3) % 45),
        registrado_por=creador,
    )


def _actividad(proyecto: Project, creador, sprint: int, indice: int) -> ActivityEntry:
    """La primera actividad de cada sprint queda Planeada; las demás, Realizadas."""
    tipo = TIPOS[indice % len(TIPOS)]
    planeada = indice == 0
    return ActivityEntry(
        project=proyecto,
        sprint=sprint,
        tipo=tipo,
        nombre_otra="Inspección de carga" if tipo == Tipo.OTRA else "",
        estado=Estado.PLANEADA if planeada else Estado.REALIZADA,
        resultado=None if planeada else RESULTADOS[(proyecto.id + sprint + indice) % 3],
        responsable=creador,
        registrado_por=creador,
    )


@transaction.atomic
def limpiar() -> Counter:
    """Borra los proyectos de los usuarios de carga (con sus datos) y luego a esos usuarios."""
    cuentas = usuarios_de_carga()
    proyectos = proyectos_de_carga()
    borrados = Counter(
        usuarios=cuentas.count(),
        proyectos=proyectos.count(),
        metricas=MetricEntry.objects.filter(project__in=proyectos).count(),
        actividades=ActivityEntry.objects.filter(project__in=proyectos).count(),
    )
    try:
        proyectos.delete()
        cuentas.delete()
    except ProtectedError as error:
        raise CommandError(MENSAJE_PROTEGIDO) from error
    return borrados
