"""Reporte de salud de un proyecto (RF-11, HU-07). Ruta de la SDS 3.4."""

from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.acceso import obtener_membresia

from .servicio import reporte_de


class ReporteView(APIView):
    """GET projects/{id}/report/: cualquier miembro, incluido el Auditor (HU-07)."""

    def get(self, request: Request, proyecto_id: int) -> Response:
        membresia = obtener_membresia(request.user, proyecto_id)
        return Response(reporte_de(membresia.project))
