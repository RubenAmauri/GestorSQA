"""Validación y representación de proyectos (RF-02, RF-03, RF-09)."""

from rest_framework import serializers

from .models import Clase, Membership

MENSAJE_FECHAS = "La fecha de fin no puede ser anterior a la fecha de inicio."
MENSAJE_CLASE_ASIGNABLE = "Solo puedes asignar Admin Normal, Colaborador o Auditor."

# El Admin Creador no se asigna: solo lo es quien registró el proyecto (HU-03 CA-01).
CLASES_ASIGNABLES = [Clase.ADMIN_NORMAL, Clase.COLABORADOR, Clase.AUDITOR]


def valor_final(serializer: serializers.Serializer, datos: dict, campo: str):
    """Valor que tendrá el campo después de guardar.

    En una edición parcial (RF-09) es el enviado o, si no se envió, el guardado; así las
    validaciones entre campos se aplican sobre el resultado final y no solo sobre lo enviado.
    """
    if campo in datos or serializer.instance is None:
        return datos.get(campo)
    return getattr(serializer.instance, campo)


class ProyectoEntradaSerializer(serializers.Serializer):
    """Datos para registrar un proyecto (HU-01 CA-01): todos obligatorios.

    Para editarlo (RF-09) se usa con la instancia y ``partial=True``. Solo estos campos se
    aceptan: el código de unión cambia únicamente al regenerarlo (RF-03).
    """

    nombre = serializers.CharField(max_length=100)
    periodo_nombre = serializers.CharField(max_length=50)
    fecha_inicio = serializers.DateField()
    fecha_fin = serializers.DateField()

    def validate(self, datos: dict) -> dict:
        if valor_final(self, datos, "fecha_fin") < valor_final(self, datos, "fecha_inicio"):
            raise serializers.ValidationError({"fecha_fin": [MENSAJE_FECHAS]})
        return datos


class UnionSerializer(serializers.Serializer):
    codigo = serializers.CharField(max_length=32)

    def validate_codigo(self, codigo: str) -> str:
        return codigo.strip().upper()


class CambioClaseSerializer(serializers.Serializer):
    """Nueva clase de un miembro (RF-04, HU-03 CA-01)."""

    clase = serializers.ChoiceField(
        choices=CLASES_ASIGNABLES,
        error_messages={"invalid_choice": MENSAJE_CLASE_ASIGNABLE},
    )


def proyecto_para(membresia: Membership) -> dict:
    """Representación de un proyecto para un miembro concreto.

    Incluye la clase del usuario en el proyecto, y el código de unión solo si es Admin
    (lo comparte desde Configuración, SDS 3.5).
    """
    proyecto = membresia.project
    datos = {
        "id": proyecto.id,
        "nombre": proyecto.nombre,
        "periodo_nombre": proyecto.periodo_nombre,
        "fecha_inicio": proyecto.fecha_inicio.isoformat(),
        "fecha_fin": proyecto.fecha_fin.isoformat(),
        "mi_clase": membresia.clase,
    }
    if membresia.es_admin:
        datos["codigo_union"] = proyecto.codigo_union
    return datos


def miembro_para(membresia: Membership) -> dict:
    """Representación de un miembro del proyecto (RF-04, CLU-04).

    Incluye el id del usuario, que es el que identifica al miembro en la API (SDS 3.4).
    """
    return {
        "usuario_id": membresia.user_id,
        "correo": membresia.user.email,
        "clase": membresia.clase,
    }
