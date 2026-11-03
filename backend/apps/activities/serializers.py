"""Validación y representación de actividades SQA (RF-08, HU-04, HU-05; Anexo B)."""

from rest_framework import serializers

from apps.projects.models import Membership

from .models import ActivityEntry, Estado, Resultado, Tipo

MENSAJE_RESULTADO_OBLIGATORIO = "Una actividad Realizada necesita un resultado."
MENSAJE_RESULTADO_PROHIBIDO = "Una actividad Planeada no puede tener resultado."
MENSAJE_NOMBRE_OTRA = "Escribe el nombre de la actividad cuando el tipo es Otra."
MENSAJE_RESPONSABLE = "El responsable debe ser miembro del proyecto."


class ActividadEntradaSerializer(serializers.Serializer):
    """Datos para registrar una actividad. El proyecto llega en el contexto."""

    sprint = serializers.IntegerField(min_value=1)
    tipo = serializers.ChoiceField(choices=Tipo.choices)
    nombre_otra = serializers.CharField(max_length=100, required=False, allow_blank=True)
    estado = serializers.ChoiceField(choices=Estado.choices)
    resultado = serializers.ChoiceField(
        choices=Resultado.choices, required=False, allow_null=True, allow_blank=True
    )
    fecha = serializers.DateField(required=False, allow_null=True)
    # Id del usuario. Un id inexistente y uno que no es miembro dan el mismo error,
    # para no revelar qué cuentas existen.
    responsable = serializers.IntegerField()
    descripcion = serializers.CharField(required=False, allow_blank=True)
    hallazgos = serializers.CharField(required=False, allow_blank=True)
    evidencia_url = serializers.URLField(max_length=500, required=False, allow_blank=True)

    def validate_responsable(self, usuario_id: int) -> int:
        """HU-04 CA-03: el responsable es miembro del proyecto."""
        proyecto = self.context["proyecto"]
        if not Membership.objects.filter(project=proyecto, user_id=usuario_id).exists():
            raise serializers.ValidationError(MENSAJE_RESPONSABLE)
        return usuario_id

    def validate(self, datos: dict) -> dict:
        datos["resultado"] = datos.get("resultado") or None
        datos["nombre_otra"] = _validar_nombre_otra(datos["tipo"], datos.get("nombre_otra", ""))
        _validar_resultado(datos["estado"], datos["resultado"])
        return datos


def _validar_nombre_otra(tipo: str, nombre: str) -> str:
    """HU-04 CA-01: "Otra" exige nombre; en los demás tipos el nombre no se guarda."""
    nombre = nombre.strip()
    if tipo != Tipo.OTRA:
        return ""
    if not nombre:
        raise serializers.ValidationError({"nombre_otra": [MENSAJE_NOMBRE_OTRA]})
    return nombre


def _validar_resultado(estado: str, resultado: str | None) -> None:
    """HU-04 CA-02: Realizada exige resultado; Planeada no lo admite."""
    if estado == Estado.REALIZADA and resultado is None:
        raise serializers.ValidationError({"resultado": [MENSAJE_RESULTADO_OBLIGATORIO]})
    if estado == Estado.PLANEADA and resultado is not None:
        raise serializers.ValidationError({"resultado": [MENSAJE_RESULTADO_PROHIBIDO]})


class FiltroActividadesSerializer(serializers.Serializer):
    """Filtros de HU-05 CA-02: ?sprint=N&estado=X. Un valor inválido da 400."""

    sprint = serializers.IntegerField(min_value=1, required=False)
    estado = serializers.ChoiceField(choices=Estado.choices, required=False)


def _usuario(usuario) -> dict:
    return {"id": usuario.id, "email": usuario.email}


def actividad_para_respuesta(actividad: ActivityEntry) -> dict:
    """HU-05 CA-01: tipo, sprint, estado, responsable y resultado, más el detalle."""
    return {
        "id": actividad.id,
        "sprint": actividad.sprint,
        "tipo": actividad.tipo,
        "nombre_otra": actividad.nombre_otra,
        "nombre": actividad.nombre_mostrado,
        "estado": actividad.estado,
        "resultado": actividad.resultado,
        "fecha": actividad.fecha.isoformat() if actividad.fecha else None,
        "responsable": _usuario(actividad.responsable),
        "descripcion": actividad.descripcion,
        "hallazgos": actividad.hallazgos,
        "evidencia_url": actividad.evidencia_url,
        "registrado_por": _usuario(actividad.registrado_por),
        "creado_en": actividad.creado_en.isoformat(),
        "actualizado_en": actividad.actualizado_en.isoformat(),
    }
