"""Datos transversales de la API."""

from django.db import models


class HistorialDeIntentos(models.Model):
    """Intentos recientes de una clave de límite (RNF-05; defecto #41).

    Una fila por clave: el ámbito del límite más la IP (inicio de sesión) o el usuario
    (unión por código). ``marcas`` guarda las marcas de tiempo de los intentos dentro de
    la ventana, de la más nueva a la más vieja, como ``history`` de DRF.

    Tamaño esperado: al guardar se descartan las marcas fuera de la ventana, así que cada
    fila tiene como mucho tantas marcas como intentos permite su límite (5 o 10 números).
    Las filas sin marcas no se borran: queda una fila pequeña por IP o usuario que haya
    intentado alguna vez, y se reutiliza en su siguiente intento.
    """

    clave = models.CharField(max_length=200, unique=True)
    marcas = models.JSONField(default=list)

    class Meta:
        verbose_name = "historial de intentos"
        verbose_name_plural = "historiales de intentos"

    def __str__(self) -> str:
        return f"{self.clave} ({len(self.marcas)} intentos en la ventana)"
