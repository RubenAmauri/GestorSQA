"""Registro, consulta, edición y eliminación de actividades SQA (RF-08, RF-09). SDS 3.4."""

from rest_framework import status
from rest_framework.exceptions import NotFound
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.acceso import exigir_clase, obtener_membresia
from apps.projects.models import CLASES_ADMIN, Clase

from .models import ActivityEntry
from .serializers import (
    ActividadEntradaSerializer,
    FiltroActividadesSerializer,
    actividad_para_respuesta,
)

# Registran actividades los Admin y los Colaboradores; el Auditor solo consulta.
CLASES_QUE_REGISTRAN = CLASES_ADMIN | {Clase.COLABORADOR}
MENSAJE_ACTIVIDAD_NO_ENCONTRADA = "Actividad no encontrada."


class ActividadesView(APIView):
    """GET y POST projects/{id}/activities/."""

    def get(self, request: Request, proyecto_id: int) -> Response:
        """Cualquier miembro. Filtros opcionales ?sprint=N&estado=X (HU-05)."""
        membresia = obtener_membresia(request.user, proyecto_id)
        filtros = FiltroActividadesSerializer(data=request.query_params)
        filtros.is_valid(raise_exception=True)
        actividades = ActivityEntry.objects.filter(
            project=membresia.project, **filtros.validated_data
        ).select_related("responsable", "registrado_por")
        return Response([actividad_para_respuesta(a) for a in actividades])

    def post(self, request: Request, proyecto_id: int) -> Response:
        """Admin o Colaborador; el Auditor recibe 403 (HU-04)."""
        membresia = obtener_membresia(request.user, proyecto_id)
        exigir_clase(membresia, CLASES_QUE_REGISTRAN)
        serializer = ActividadEntradaSerializer(
            data=request.data, context={"proyecto": membresia.project}
        )
        serializer.is_valid(raise_exception=True)
        datos = serializer.validated_data
        actividad = ActivityEntry.objects.create(
            project=membresia.project,
            registrado_por=request.user,
            responsable_id=datos.pop("responsable"),
            **datos,
        )
        return Response(actividad_para_respuesta(actividad), status=status.HTTP_201_CREATED)


class ActividadDetalleView(APIView):
    """PATCH y DELETE projects/{id}/activities/{actividad_id}/ (RF-09, HU-08)."""

    def patch(self, request: Request, proyecto_id: int, actividad_id: int) -> Response:
        """Admin o Colaborador (HU-08 CA-01)."""
        membresia = obtener_membresia(request.user, proyecto_id)
        exigir_clase(membresia, CLASES_QUE_REGISTRAN)
        actividad = _actividad_de(membresia.project, actividad_id)
        serializer = ActividadEntradaSerializer(
            actividad, data=request.data, partial=True, context={"proyecto": membresia.project}
        )
        serializer.is_valid(raise_exception=True)
        datos = serializer.validated_data
        if "responsable" in datos:
            actividad.responsable_id = datos.pop("responsable")
        for campo, valor in datos.items():
            setattr(actividad, campo, valor)
        actividad.save()
        return Response(actividad_para_respuesta(actividad))

    def delete(self, request: Request, proyecto_id: int, actividad_id: int) -> Response:
        """Solo Admin (HU-08 CA-02)."""
        membresia = obtener_membresia(request.user, proyecto_id)
        exigir_clase(membresia, CLASES_ADMIN)
        _actividad_de(membresia.project, actividad_id).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


def _actividad_de(proyecto, actividad_id: int) -> ActivityEntry:
    """La actividad de ESTE proyecto; una de otro proyecto no se revela (RNF-03)."""
    actividad = (
        ActivityEntry.objects.select_related("responsable", "registrado_por")
        .filter(project=proyecto, id=actividad_id)
        .first()
    )
    if actividad is None:
        raise NotFound(MENSAJE_ACTIVIDAD_NO_ENCONTRADA)
    return actividad
