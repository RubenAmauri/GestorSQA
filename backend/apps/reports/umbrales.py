"""Umbrales del estado de salud.

Fuente de verdad: SRS v1.1, Anexo C. Todo cambio de umbral se hace en el Anexo C
y en este archivo en la misma versión (ADR-07).
"""

from decimal import Decimal

# Densidad de defectos (defectos acumulados / KLOC). Decisión del equipo, calibrable.
DENSIDAD_OPTIMO_MAX = Decimal("5")
DENSIDAD_ADVERTENCIA_MAX = Decimal("10")

# Cobertura de pruebas (%). Guía de Google: 60 aceptable, 75 encomiable.
COBERTURA_OPTIMO_MIN = Decimal("75")
COBERTURA_ADVERTENCIA_MIN = Decimal("60")

# Tiempo promedio de corrección (horas por defecto corregido). Medio día y un día.
TIEMPO_OPTIMO_MAX = Decimal("4")
TIEMPO_ADVERTENCIA_MAX = Decimal("8")

# Actividades SQA realizadas en el sprint.
ACTIVIDADES_OPTIMO_MIN = 2
