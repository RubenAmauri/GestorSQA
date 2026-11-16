"""Límites de intentos de la API (RNF-05, SDS 3.4)."""

from django.db import transaction
from rest_framework.throttling import SimpleRateThrottle

from .models import HistorialDeIntentos


class LimiteAtomico(SimpleRateThrottle):
    """Límite de ventana deslizante que se respeta con peticiones simultáneas (#41).

    ``SimpleRateThrottle`` lee el historial de la caché, decide y escribe sin bloqueo:
    las peticiones concurrentes leían el mismo historial y todas pasaban. Aquí el
    historial vive en ``HistorialDeIntentos`` y se lee y escribe con la fila bloqueada
    (SELECT ... FOR UPDATE), así que las peticiones de una misma clave esperan su turno.
    La tasa, la ventana y el encabezado Retry-After son los de DRF.
    """

    def allow_request(self, request, view) -> bool:
        if self.rate is None:
            return True
        self.key = self.get_cache_key(request, view)
        if self.key is None:
            return True
        # La fila se crea antes y fuera del bloqueo: si dos peticiones la crean a la vez,
        # get_or_create absorbe el IntegrityError de la restricción única y lee la que
        # ganó, y el bloqueo de abajo siempre recae sobre una fila que ya existe.
        HistorialDeIntentos.objects.get_or_create(clave=self.key)
        with transaction.atomic():
            fila = HistorialDeIntentos.objects.select_for_update().get(clave=self.key)
            self.now = self.timer()
            # Al guardar se descartan las marcas fuera de la ventana: la fila no crece.
            self.history = [marca for marca in fila.marcas if marca > self.now - self.duration]
            permitido = len(self.history) < self.num_requests
            if permitido:
                self.history.insert(0, self.now)
            fila.marcas = self.history
            fila.save(update_fields=["marcas"])
        return permitido


class InicioSesionThrottle(LimiteAtomico):
    """Inicio de sesión: 5 intentos por minuto por IP, con o sin sesión.

    Cuenta todos los intentos, correctos o no. La tasa vive en
    ``REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"]["inicio_sesion"]`` y el historial en
    ``HistorialDeIntentos``, que comparten todos los workers de gunicorn. La IP se toma
    de ``X-Forwarded-For`` según ``NUM_PROXIES`` (Caddy delante).
    """

    scope = "inicio_sesion"

    def get_cache_key(self, request, view) -> str:
        return self.cache_format % {"scope": self.scope, "ident": self.get_ident(request)}


class UnionCodigoThrottle(LimiteAtomico):
    """Unión por código: 10 intentos por hora por usuario, contra la adivinación de códigos.

    La tasa vive en ``REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"]["union_codigo"]``. La vista
    exige sesión, así que siempre hay un usuario autenticado.
    """

    scope = "union_codigo"

    def get_cache_key(self, request, view) -> str:
        return self.cache_format % {"scope": self.scope, "ident": request.user.pk}
