"""Métricas por sprint de un proyecto (RF-07, HU-06). Rutas de la SDS 3.4."""

from django.db import IntegrityError, transaction
from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.acceso import exigir_clase, obtener_membresia
from apps.projects.models import CLASES_ADMIN, Clase

from .models import MetricEntry
from .serializers import MetricaSerializer

CLASES_QUE_CAPTURAN = CLASES_ADMIN | {Clase.COLABORADOR}


class MetricasView(APIView):
    """GET: cualquier miembro. POST: Admin o Colaborador; el Auditor recibe 403 (RF-05)."""

    def get(self, request: Request, proyecto_id: int) -> Response:
        membresia = obtener_membresia(request.user, proyecto_id)
        metricas = MetricEntry.objects.filter(project=membresia.project)
        return Response(MetricaSerializer(metricas, many=True).data)

    def post(self, request: Request, proyecto_id: int) -> Response:
        membresia = obtener_membresia(request.user, proyecto_id)
        exigir_clase(membresia, CLASES_QUE_CAPTURAN)
        serializer = MetricaSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        sprint = serializer.validated_data["sprint"]
        if MetricEntry.objects.filter(project=membresia.project, sprint=sprint).exists():
            return _sprint_repetido(sprint)
        try:
            with transaction.atomic():
                metrica = serializer.save(project=membresia.project, registrado_por=request.user)
        except IntegrityError:
            # Dos capturas simultáneas del mismo sprint: gana la restricción única.
            return _sprint_repetido(sprint)
        return Response(MetricaSerializer(metrica).data, status=status.HTTP_201_CREATED)


def _sprint_repetido(sprint: int) -> Response:
    """HU-06 CA-01: un solo registro de métricas por sprint."""
    return Response(
        {"sprint": [f"El sprint {sprint} ya tiene métricas registradas; usa Editar."]},
        status=status.HTTP_409_CONFLICT,
    )
