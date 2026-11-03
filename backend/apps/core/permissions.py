"""Permisos transversales de la API."""

from rest_framework.authentication import SessionAuthentication
from rest_framework.permissions import BasePermission


class CsrfObligatorio(BasePermission):
    """Exige el token CSRF aunque no haya sesión.

    DRF solo revisa CSRF a usuarios con sesión. Las rutas públicas que crean o
    inician una sesión (registro e inicio de sesión) también deben exigirlo para
    evitar que otro sitio inicie una sesión a nombre del visitante (ADR-05).
    """

    def has_permission(self, request, view) -> bool:
        SessionAuthentication().enforce_csrf(request)
        return True
