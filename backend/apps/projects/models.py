"""Proyectos y membresías (RF-02, RF-03; SDS 3.2)."""

import secrets
import string

from django.conf import settings
from django.db import models
from django.db.models import F, Q

ALFABETO_CODIGO = string.ascii_uppercase + string.digits
LONGITUD_CODIGO = 10


def normalizar(texto: str) -> str:
    """Clave de comparación: sin espacios sobrantes y en minúsculas (RF-02).

    " Gestor  SQA " y "gestor sqa" producen la misma clave.
    """
    return " ".join(texto.split()).lower()


def generar_codigo() -> str:
    """Código de unión de 10 caracteres alfanuméricos con generador criptográfico (SDS 3.3.2)."""
    return "".join(secrets.choice(ALFABETO_CODIGO) for _ in range(LONGITUD_CODIGO))


class Clase(models.TextChoices):
    ADMIN_CREADOR = "ADMIN_CREADOR", "Admin Creador"
    ADMIN_NORMAL = "ADMIN_NORMAL", "Admin Normal"
    COLABORADOR = "COLABORADOR", "Colaborador"
    AUDITOR = "AUDITOR", "Auditor"


CLASES_ADMIN = frozenset({Clase.ADMIN_CREADOR, Clase.ADMIN_NORMAL})


class Project(models.Model):
    nombre = models.CharField(max_length=100)
    nombre_clave = models.CharField(max_length=100, editable=False)
    periodo_nombre = models.CharField(max_length=50)
    periodo_clave = models.CharField(max_length=50, editable=False)
    fecha_inicio = models.DateField()
    fecha_fin = models.DateField()
    codigo_union = models.CharField(max_length=LONGITUD_CODIGO, unique=True, editable=False)
    creado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="proyectos_creados"
    )
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "proyecto"
        constraints = [
            models.UniqueConstraint(
                fields=["creado_por", "nombre_clave", "periodo_clave"],
                name="proyecto_unico_por_creador",
            ),
            models.CheckConstraint(
                condition=Q(fecha_fin__gte=F("fecha_inicio")), name="proyecto_fechas_validas"
            ),
        ]

    def __str__(self) -> str:
        return f"{self.nombre} ({self.periodo_nombre})"

    def save(self, *args, **kwargs) -> None:
        self.nombre_clave = normalizar(self.nombre)
        self.periodo_clave = normalizar(self.periodo_nombre)
        if not self.codigo_union:
            self.codigo_union = self._codigo_libre()
        super().save(*args, **kwargs)

    def regenerar_codigo(self) -> str:
        """Asigna un código nuevo; el anterior deja de funcionar (RF-03)."""
        self.codigo_union = self._codigo_libre()
        self.save(update_fields=["codigo_union"])
        return self.codigo_union

    def _codigo_libre(self) -> str:
        while True:
            codigo = generar_codigo()
            if (
                codigo != self.codigo_union
                and not Project.objects.filter(codigo_union=codigo).exists()
            ):
                return codigo


class Membership(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="membresias")
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="membresias"
    )
    clase = models.CharField(max_length=20, choices=Clase.choices)
    fecha_union = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "membresía"
        constraints = [
            models.UniqueConstraint(fields=["project", "user"], name="membresia_unica"),
        ]

    def __str__(self) -> str:
        return f"{self.user} · {self.project} · {self.clase}"

    @property
    def es_admin(self) -> bool:
        return self.clase in CLASES_ADMIN
