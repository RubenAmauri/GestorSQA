"""Límites de intentos de la API (RNF-05, SDS 3.4)."""

from rest_framework.throttling import SimpleRateThrottle


class InicioSesionThrottle(SimpleRateThrottle):
    """Inicio de sesión: 5 intentos por minuto por IP, con o sin sesión.

    Cuenta todos los intentos, correctos o no. La tasa vive en
    ``REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"]["inicio_sesion"]`` y el contador en
    la caché en base de datos, que comparten todos los workers de gunicorn. La IP
    se toma de ``X-Forwarded-For`` según ``NUM_PROXIES`` (Caddy delante).
    """

    scope = "inicio_sesion"

    def get_cache_key(self, request, view) -> str:
        return self.cache_format % {"scope": self.scope, "ident": self.get_ident(request)}


class UnionCodigoThrottle(SimpleRateThrottle):
    """Unión por código: 10 intentos por hora por usuario, contra la adivinación de códigos.

    La tasa vive en ``REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"]["union_codigo"]``. La vista
    exige sesión, así que siempre hay un usuario autenticado.
    """

    scope = "union_codigo"

    def get_cache_key(self, request, view) -> str:
        return self.cache_format % {"scope": self.scope, "ident": request.user.pk}
