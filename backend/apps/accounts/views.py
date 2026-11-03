"""Cuentas y sesión (RF-01, HU-10, RNF-05). Rutas de la SDS 3.4."""

from django.contrib.auth import authenticate, get_user_model, login, logout
from django.db import IntegrityError, transaction
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import ensure_csrf_cookie
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.permissions import CsrfObligatorio
from apps.core.throttling import InicioSesionThrottle

from .serializers import InicioSesionSerializer, RegistroSerializer, UsuarioSerializer

MENSAJE_CORREO_DUPLICADO = "Ya existe una cuenta con este correo."
MENSAJE_CREDENCIALES = "Correo o contraseña incorrectos."


@method_decorator(ensure_csrf_cookie, name="dispatch")
class CsrfView(APIView):
    """GET auth/csrf/: establece la cookie ``csrftoken`` para la SPA."""

    permission_classes = [AllowAny]

    def get(self, request: Request) -> Response:
        return Response(status=status.HTTP_204_NO_CONTENT)


class RegistroView(APIView):
    """POST auth/register/: crea la cuenta y deja la sesión iniciada (CA-01, CA-02)."""

    permission_classes = [AllowAny, CsrfObligatorio]

    def post(self, request: Request) -> Response:
        serializer = RegistroSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        datos = serializer.validated_data
        usuarios = get_user_model().objects
        if usuarios.filter(email=datos["email"]).exists():
            return _correo_duplicado()
        try:
            with transaction.atomic():
                usuario = usuarios.create_user(datos["email"], datos["password"])
        except IntegrityError:
            # Dos registros simultáneos con el mismo correo: gana la restricción única.
            return _correo_duplicado()
        login(request, usuario)
        return Response(UsuarioSerializer(usuario).data, status=status.HTTP_201_CREATED)


class InicioSesionView(APIView):
    """POST auth/login/: inicia sesión; 5 intentos por minuto por IP (CA-03, RNF-05)."""

    permission_classes = [AllowAny, CsrfObligatorio]
    throttle_classes = [InicioSesionThrottle]

    def post(self, request: Request) -> Response:
        serializer = InicioSesionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        datos = serializer.validated_data
        usuario = authenticate(request, username=datos["email"], password=datos["password"])
        if usuario is None:
            return Response({"detail": MENSAJE_CREDENCIALES}, status=status.HTTP_400_BAD_REQUEST)
        login(request, usuario)
        return Response(UsuarioSerializer(usuario).data)


class CierreSesionView(APIView):
    """POST auth/logout/: cierra la sesión (CA-04)."""

    def post(self, request: Request) -> Response:
        logout(request)
        return Response(status=status.HTTP_204_NO_CONTENT)


class UsuarioActualView(APIView):
    """GET auth/me/: usuario de la sesión; 401 sin sesión."""

    def get(self, request: Request) -> Response:
        return Response(UsuarioSerializer(request.user).data)


def _correo_duplicado() -> Response:
    return Response({"email": [MENSAJE_CORREO_DUPLICADO]}, status=status.HTTP_409_CONFLICT)
