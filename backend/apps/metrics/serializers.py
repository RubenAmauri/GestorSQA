"""Validación de métricas por sprint (RF-07, HU-06)."""

from decimal import Decimal

from rest_framework import serializers

from .models import MetricEntry

CERO = Decimal("0")
MENSAJE_SPRINT_NO_EDITABLE = "El sprint no se edita; viene en la ruta."


def _decimal(max_digits: int, decimal_places: int, **extra) -> serializers.DecimalField:
    return serializers.DecimalField(
        max_digits=max_digits,
        decimal_places=decimal_places,
        min_value=CERO,
        required=False,
        allow_null=True,
        coerce_to_string=False,
        **extra,
    )


class MetricaSerializer(serializers.ModelSerializer):
    """HU-06 CA-02: todo opcional salvo el sprint; un campo omitido o null queda vacío.
    HU-06 CA-03: sin negativos; la cobertura va de 0 a 100.

    Para editar (RF-09) se usa con la instancia y ``partial=True``: un campo omitido no
    cambia y uno enviado como null queda vacío. El sprint viene en la ruta y no se edita.
    """

    sprint = serializers.IntegerField(min_value=1)
    defectos_encontrados = serializers.IntegerField(min_value=0, required=False, allow_null=True)
    defectos_corregidos = serializers.IntegerField(min_value=0, required=False, allow_null=True)
    horas_correccion = _decimal(8, 2)
    kloc = _decimal(9, 3)
    cobertura_pct = _decimal(5, 2, max_value=Decimal("100"))

    class Meta:
        model = MetricEntry
        fields = [
            "sprint",
            "defectos_encontrados",
            "defectos_corregidos",
            "horas_correccion",
            "kloc",
            "cobertura_pct",
        ]

    def validate_sprint(self, sprint: int) -> int:
        if self.instance is not None and sprint != self.instance.sprint:
            raise serializers.ValidationError(MENSAJE_SPRINT_NO_EDITABLE)
        return sprint
