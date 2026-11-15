"""Proyectos, unión, acceso y gestión de miembros (RF-02, RF-03, RF-04, RF-06). SDS 3.4."""

from django.db import IntegrityError, transaction
from rest_framework import status
from rest_framework.exceptions import NotFound, PermissionDenied
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.acceso import exigir_clase, obtener_membresia
from apps.core.throttling import UnionCodigoThrottle

from .models import CLASES_ADMIN, Clase, Membership, Project, normalizar
from .serializers import (
    CambioClaseSerializer,
    ProyectoEntradaSerializer,
    UnionSerializer,
    miembro_para,
    proyecto_para,
)

MENSAJE_DUPLICADO = "Ya registraste un proyecto con este nombre en este periodo."
MENSAJE_CODIGO_INVALIDO = "El código no es válido."
MENSAJE_YA_MIEMBRO = "Ya eres miembro de este proyecto."
MENSAJE_MIEMBRO_NO_ENCONTRADO = "Miembro no encontrado."
MENSAJE_ES_CREADOR = "No se puede cambiar ni expulsar al Admin Creador."
MENSAJE_ES_UNO_MISMO = "No puedes cambiar tu propia clase ni expulsarte del proyecto."


class ProyectosView(APIView):
    """GET projects/: mis proyectos con mi clase (RF-06). POST projects/: registrar (RF-02)."""

    def get(self, request: Request) -> Response:
        membresias = (
            Membership.objects.filter(user=request.user)
            .select_related("project")
            .order_by("-project__creado_en")
        )
        return Response([proyecto_para(m) for m in membresias])

    def post(self, request: Request) -> Response:
        serializer = ProyectoEntradaSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        datos = serializer.validated_data
        if _es_duplicado(request.user, datos):
            return _duplicado()
        try:
            with transaction.atomic():
                proyecto = Project.objects.create(creado_por=request.user, **datos)
                membresia = Membership.objects.create(
                    project=proyecto, user=request.user, clase=Clase.ADMIN_CREADOR
                )
        except IntegrityError:
            # Dos altas simultáneas iguales: gana la restricción única.
            return _duplicado()
        return Response(proyecto_para(membresia), status=status.HTTP_201_CREATED)


class UnionView(APIView):
    """POST projects/join/: unirse con el código como Colaborador (RF-03, HU-02)."""

    throttle_classes = [UnionCodigoThrottle]

    def post(self, request: Request) -> Response:
        serializer = UnionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        proyecto = Project.objects.filter(codigo_union=serializer.validated_data["codigo"]).first()
        if proyecto is None:
            # Mismo mensaje para un código mal escrito o inexistente (HU-02 CA-02).
            return Response({"detail": MENSAJE_CODIGO_INVALIDO}, status=status.HTTP_400_BAD_REQUEST)
        try:
            with transaction.atomic():
                membresia = Membership.objects.create(
                    project=proyecto, user=request.user, clase=Clase.COLABORADOR
                )
        except IntegrityError:
            return Response({"detail": MENSAJE_YA_MIEMBRO}, status=status.HTTP_409_CONFLICT)
        return Response(proyecto_para(membresia), status=status.HTTP_201_CREATED)


class ProyectoDetalleView(APIView):
    """GET projects/{id}/: solo para miembros; 404 para el resto (RF-06, RNF-03)."""

    def get(self, request: Request, proyecto_id: int) -> Response:
        return Response(proyecto_para(obtener_membresia(request.user, proyecto_id)))


class RegenerarCodigoView(APIView):
    """POST projects/{id}/codigo/regenerar/: solo Admin; invalida el código anterior (RF-03)."""

    def post(self, request: Request, proyecto_id: int) -> Response:
        membresia = obtener_membresia(request.user, proyecto_id)
        exigir_clase(membresia, CLASES_ADMIN)
        return Response({"codigo_union": membresia.project.regenerar_codigo()})


class MiembrosView(APIView):
    """GET projects/{id}/members/: cualquier miembro consulta los miembros (RF-04, CLU-04)."""

    def get(self, request: Request, proyecto_id: int) -> Response:
        obtener_membresia(request.user, proyecto_id)
        membresias = (
            Membership.objects.filter(project_id=proyecto_id)
            .select_related("user")
            .order_by("fecha_union", "id")
        )
        return Response([miembro_para(m) for m in membresias])


class MiembroDetalleView(APIView):
    """PATCH y DELETE projects/{id}/members/{user_id}/: solo Admin (RF-04, HU-03; SDS 3.4).

    Nadie cambia ni expulsa al Admin Creador, y nadie se cambia ni se expulsa a sí mismo.
    """

    def patch(self, request: Request, proyecto_id: int, user_id: int) -> Response:
        objetivo = _membresia_gestionable(request, proyecto_id, user_id)
        serializer = CambioClaseSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        objetivo.clase = serializer.validated_data["clase"]
        objetivo.save(update_fields=["clase"])
        return Response(miembro_para(objetivo))

    def delete(self, request: Request, proyecto_id: int, user_id: int) -> Response:
        # Al borrar la membresía, el expulsado recibe 404 en todo el proyecto (HU-03 CA-03).
        _membresia_gestionable(request, proyecto_id, user_id).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


def _membresia_gestionable(request: Request, proyecto_id: int, user_id: int) -> Membership:
    membresia = obtener_membresia(request.user, proyecto_id)
    exigir_clase(membresia, CLASES_ADMIN)
    # Se busca la membresía del usuario en ESTE proyecto: si no es miembro, 404 (RNF-03).
    objetivo = (
        Membership.objects.select_related("user")
        .filter(project_id=proyecto_id, user_id=user_id)
        .first()
    )
    if objetivo is None:
        raise NotFound(MENSAJE_MIEMBRO_NO_ENCONTRADO)
    if objetivo.clase == Clase.ADMIN_CREADOR:
        raise PermissionDenied(MENSAJE_ES_CREADOR)
    if objetivo.id == membresia.id:
        raise PermissionDenied(MENSAJE_ES_UNO_MISMO)
    return objetivo


def _es_duplicado(usuario, datos: dict) -> bool:
    return Project.objects.filter(
        creado_por=usuario,
        nombre_clave=normalizar(datos["nombre"]),
        periodo_clave=normalizar(datos["periodo_nombre"]),
    ).exists()


def _duplicado() -> Response:
    return Response({"detail": MENSAJE_DUPLICADO}, status=status.HTTP_409_CONFLICT)
