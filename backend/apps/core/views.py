"""Vistas transversales: estado del servicio y entrega de la SPA."""

from django.db import connection
from django.http import HttpResponse
from django.template import TemplateDoesNotExist
from django.template.loader import render_to_string
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response


@api_view(["GET"])
@permission_classes([AllowAny])
def health(request: Request) -> Response:
    """Estado del servicio para el healthcheck del contenedor (SDS 5.1)."""
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        database = "ok"
    except Exception:  # noqa: BLE001 - cualquier fallo de BD se reporta igual
        database = "error"
    status_code = 200 if database == "ok" else 503
    return Response(
        {"status": "ok" if database == "ok" else "error", "database": database}, status=status_code
    )


def spa_index(request) -> HttpResponse:
    """Devuelve la SPA compilada para toda ruta fuera de /api/ (SDS 3.5)."""
    try:
        return HttpResponse(render_to_string("index.html", request=request))
    except TemplateDoesNotExist:
        return HttpResponse(
            "La interfaz no está compilada. En desarrollo usa el servidor de Vite "
            "(http://localhost:5173).",
            status=503,
            content_type="text/plain; charset=utf-8",
        )
