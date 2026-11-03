"""Registro y consulta de actividades SQA (RF-08, HU-04, HU-05). SDS 3.4.

Editar y eliminar actividades es RF-09 (Entrega Final) y no está aquí.
"""

from rest_framework import status
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
