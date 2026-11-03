"""Autenticación por sesión de la API (ADR-05, SDS 3.4)."""

from rest_framework.authentication import SessionAuthentication


class SesionAuthentication(SessionAuthentication):
    """Sesión con cookie que responde 401, y no 403, cuando no hay sesión.

    DRF responde 403 a una petición sin autenticar si la primera clase de
    autenticación no define el encabezado ``WWW-Authenticate``. La convención de
    la API (SDS 3.4) separa 401 (sin sesión) de 403 (miembro sin permiso).
    """

    def authenticate_header(self, request) -> str:
        return 'Session realm="api"'
