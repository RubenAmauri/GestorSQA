"""Validación de datos de cuentas y sesión (RF-01, HU-10)."""

from django.contrib.auth import get_user_model, password_validation
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers


def normalizar_correo(correo: str) -> str:
    return correo.strip().lower()


class UsuarioSerializer(serializers.ModelSerializer):
    class Meta:
        model = get_user_model()
        fields = ["id", "email"]


class RegistroSerializer(serializers.Serializer):
    email = serializers.EmailField(max_length=254)
    password = serializers.CharField(write_only=True, trim_whitespace=False)

    def validate_email(self, valor: str) -> str:
        return normalizar_correo(valor)

    def validate(self, datos: dict) -> dict:
        """CA-02: la contraseña pasa los validadores de Django (mínimo 8 caracteres)."""
        usuario = get_user_model()(email=datos["email"])
        try:
            password_validation.validate_password(datos["password"], usuario)
        except DjangoValidationError as error:
            raise serializers.ValidationError({"password": list(error.messages)}) from error
        return datos


class InicioSesionSerializer(serializers.Serializer):
    email = serializers.CharField()
    password = serializers.CharField(write_only=True, trim_whitespace=False)

    def validate_email(self, valor: str) -> str:
        return normalizar_correo(valor)
