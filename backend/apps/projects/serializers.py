"""Validación y representación de proyectos (RF-02, RF-03)."""

from rest_framework import serializers

from .models import Membership

MENSAJE_FECHAS = "La fecha de fin no puede ser anterior a la fecha de inicio."


class ProyectoEntradaSerializer(serializers.Serializer):
    """Datos para registrar un proyecto (HU-01 CA-01): todos obligatorios."""

    nombre = serializers.CharField(max_length=100)
    periodo_nombre = serializers.CharField(max_length=50)
    fecha_inicio = serializers.DateField()
    fecha_fin = serializers.DateField()

    def validate(self, datos: dict) -> dict:
        if datos["fecha_fin"] < datos["fecha_inicio"]:
            raise serializers.ValidationError({"fecha_fin": [MENSAJE_FECHAS]})
        return datos


class UnionSerializer(serializers.Serializer):
    codigo = serializers.CharField(max_length=32)

    def validate_codigo(self, codigo: str) -> str:
        return codigo.strip().upper()


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
