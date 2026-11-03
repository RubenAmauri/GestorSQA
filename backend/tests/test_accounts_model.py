"""Pruebas del modelo de usuario (RF-01, RNF-05)."""

import pytest
from django.contrib.auth import get_user_model

pytestmark = pytest.mark.django_db


def test_pr_rnf05_01_password_se_guarda_con_hash():
    """PR-RNF05-01: en la base de datos no hay contraseñas en texto plano."""
    user = get_user_model().objects.create_user("ana@correo.com", "secreta123")
    assert user.password != "secreta123"
    assert user.password.startswith("pbkdf2_sha256$")
    assert user.check_password("secreta123")


def test_correo_es_el_identificador_y_se_normaliza():
    user = get_user_model().objects.create_user("Ana@Correo.COM", "secreta123")
    assert user.email == "ana@correo.com"
    assert str(user) == "ana@correo.com"
    assert get_user_model().USERNAME_FIELD == "email"


def test_correo_obligatorio():
    with pytest.raises(ValueError):
        get_user_model().objects.create_user("", "secreta123")


def test_superusuario_tiene_permisos_de_administracion():
    admin = get_user_model().objects.create_superuser("admin@correo.com", "secreta123")
    assert admin.is_staff and admin.is_superuser
