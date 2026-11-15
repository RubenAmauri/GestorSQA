"""Reporte de salud de un proyecto (RF-11, RF-12; HU-07, HU-09). Rutas de la SDS 3.4."""

from django.http import HttpResponse
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.acceso import obtener_membresia

from .exportar_csv import csv_del_reporte, nombre_de_archivo
from .servicio import reporte_de

# Con BOM, Excel abre el archivo como UTF-8 y muestra bien los acentos.
BOM = "﻿"


class ReporteView(APIView):
    """GET projects/{id}/report/: cualquier miembro, incluido el Auditor (HU-07)."""

    def get(self, request: Request, proyecto_id: int) -> Response:
        membresia = obtener_membresia(request.user, proyecto_id)
        return Response(reporte_de(membresia.project))


class ReporteCsvView(APIView):
    """GET projects/{id}/report.csv: cualquier miembro, incluido el Auditor (HU-09 CA-03).

    Los errores (401, 404) siguen saliendo en JSON, como en el resto de la API.
    """

    def perform_content_negotiation(self, request: Request, force: bool = False):
        # DRF solo conoce JSON y respondería 406 a "Accept: text/csv". El CSV se entrega
        # igual, sin importar el Accept, y los errores caen en el primer renderizador (JSON).
        return super().perform_content_negotiation(request, force=True)

    def get(self, request: Request, proyecto_id: int) -> HttpResponse:
        membresia = obtener_membresia(request.user, proyecto_id)
        reporte = reporte_de(membresia.project)
        respuesta = HttpResponse(
            BOM + csv_del_reporte(reporte), content_type="text/csv; charset=utf-8"
        )
        respuesta["Content-Disposition"] = f'attachment; filename="{nombre_de_archivo(reporte)}"'
        return respuesta
