"""Actividades SQA por sprint (RF-08; Anexo B del SRS; SDS 3.2).

Los valores de ``Estado`` y ``Resultado`` son los mismos que usa el motor de salud
(``apps/reports/salud.py``), para que el reporte los pase sin traducir.
"""

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import Q

from apps.projects.models import Project


class Tipo(models.TextChoices):
    CAMINATA = "CAMINATA", "Caminata"
    REVISION_CODIGO = "REVISION_CODIGO", "Revisión de código"
    AUDITORIA_CONFIGURACION = "AUDITORIA_CONFIGURACION", "Auditoría de configuración"
    PRUEBAS = "PRUEBAS", "Pruebas"
    OTRA = "OTRA", "Otra"


class Estado(models.TextChoices):
    PLANEADA = "PLANEADA", "Planeada"
    REALIZADA = "REALIZADA", "Realizada"


class Resultado(models.TextChoices):
    SATISFACTORIO = "SATISFACTORIO", "Satisfactorio"
    CON_HALLAZGOS = "CON_HALLAZGOS", "Con hallazgos"
    NO_SATISFACTORIO = "NO_SATISFACTORIO", "No satisfactorio"


class ActivityEntry(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="actividades")
    sprint = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    tipo = models.CharField(max_length=30, choices=Tipo.choices)
    nombre_otra = models.CharField(max_length=100, blank=True)
    estado = models.CharField(max_length=20, choices=Estado.choices)
    # NULL mientras está Planeada, igual que ``resultado=None`` en el motor de salud.
    resultado = models.CharField(  # noqa: DJ001
        max_length=20, choices=Resultado.choices, null=True, blank=True
    )
    fecha = models.DateField(null=True, blank=True)
    responsable = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="actividades_a_cargo"
    )
    descripcion = models.TextField(blank=True)
    hallazgos = models.TextField(blank=True)
    evidencia_url = models.URLField(max_length=500, blank=True)
    registrado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="actividades_registradas",
    )
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "actividad SQA"
        verbose_name_plural = "actividades SQA"
        ordering = ["sprint", "id"]
        constraints = [
            models.CheckConstraint(condition=Q(sprint__gte=1), name="actividad_sprint_valido"),
            # Anexo B: resultado obligatorio si es Realizada y prohibido si es Planeada.
            models.CheckConstraint(
                condition=Q(estado=Estado.PLANEADA, resultado__isnull=True)
                | Q(estado=Estado.REALIZADA, resultado__isnull=False),
                name="actividad_resultado_segun_estado",
            ),
            models.CheckConstraint(
                condition=~Q(tipo=Tipo.OTRA) | ~Q(nombre_otra=""),
                name="actividad_otra_con_nombre",
            ),
        ]

    def __str__(self) -> str:
        return f"Sprint {self.sprint} · {self.nombre_mostrado} · {self.get_estado_display()}"

    @property
    def nombre_mostrado(self) -> str:
        return self.nombre_otra if self.tipo == Tipo.OTRA else self.get_tipo_display()
