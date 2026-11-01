"""Métricas por sprint (RF-07; SRS Anexo A; SDS 3.2).

Todos los valores son opcionales salvo el sprint. Un valor vacío (NULL) significa
"Sin datos" y es distinto de cero.
"""

from django.conf import settings
from django.db import models
from django.db.models import Q

from apps.projects.models import Project


class MetricEntry(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="metricas")
    sprint = models.PositiveIntegerField()
    defectos_encontrados = models.PositiveIntegerField(null=True, blank=True)
    defectos_corregidos = models.PositiveIntegerField(null=True, blank=True)
    horas_correccion = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    kloc = models.DecimalField(max_digits=9, decimal_places=3, null=True, blank=True)
    cobertura_pct = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    registrado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="metricas_registradas"
    )
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "métricas de un sprint"
        ordering = ["sprint"]
        constraints = [
            models.UniqueConstraint(fields=["project", "sprint"], name="metricas_una_por_sprint"),
            models.CheckConstraint(condition=Q(sprint__gte=1), name="metricas_sprint_positivo"),
            models.CheckConstraint(
                condition=Q(horas_correccion__isnull=True) | Q(horas_correccion__gte=0),
                name="metricas_horas_no_negativas",
            ),
            models.CheckConstraint(
                condition=Q(kloc__isnull=True) | Q(kloc__gte=0), name="metricas_kloc_no_negativo"
            ),
            models.CheckConstraint(
                condition=Q(cobertura_pct__isnull=True)
                | (Q(cobertura_pct__gte=0) & Q(cobertura_pct__lte=100)),
                name="metricas_cobertura_0_a_100",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.project} · sprint {self.sprint}"
