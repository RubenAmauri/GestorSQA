"""Acceso a los datos de un proyecto por membresía (RF-05, RF-06, RNF-03; ADR-06).

Toda vista que reciba el id de un proyecto debe pasar por ``obtener_membresia``:
- quien no es miembro recibe 404, para no revelar que el proyecto existe;
- un miembro sin permiso recibe 403 con ``exigir_clase``.
"""

from collections.abc import Iterable

from rest_framework.exceptions import NotFound, PermissionDenied

from apps.projects.models import Membership

MENSAJE_NO_ENCONTRADO = "Proyecto no encontrado."
MENSAJE_SIN_PERMISO = "Tu clase en este proyecto no permite esta acción."


def obtener_membresia(usuario, proyecto_id: int) -> Membership:
    try:
        return Membership.objects.select_related("project").get(
            project_id=proyecto_id, user=usuario
        )
    except Membership.DoesNotExist as error:
        raise NotFound(MENSAJE_NO_ENCONTRADO) from error


def exigir_clase(membresia: Membership, clases: Iterable[str]) -> None:
    if membresia.clase not in set(clases):
        raise PermissionDenied(MENSAJE_SIN_PERMISO)
