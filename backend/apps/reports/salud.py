"""Motor de salud del Gestor SQA (RF-10, RF-11).

Implementa las fórmulas del Anexo A y las reglas del Anexo C del SRS v1.1.
Son funciones puras: no consultan la base de datos (ADR-07, SDS 3.3.5), así que
se prueban de forma aislada con valores límite.

Los cálculos usan Decimal para que los umbrales se comparen sin errores de
redondeo de punto flotante (por ejemplo, 7 / 0.7 da exactamente 10).
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum

from . import umbrales

ESTADO_SIN_EVALUACION = "SIN_EVALUACION"


class Nivel(StrEnum):
    OPTIMO = "OPTIMO"
    ADVERTENCIA = "ADVERTENCIA"
    CRITICO = "CRITICO"
    SIN_DATOS = "SIN_DATOS"
    NO_APLICA = "NO_APLICA"


class EstadoActividad(StrEnum):
    PLANEADA = "PLANEADA"
    REALIZADA = "REALIZADA"


class Resultado(StrEnum):
    SATISFACTORIO = "SATISFACTORIO"
    CON_HALLAZGOS = "CON_HALLAZGOS"
    NO_SATISFACTORIO = "NO_SATISFACTORIO"


Numero = int | float | Decimal


@dataclass(frozen=True)
class MetricaSprint:
    """Registro de métricas de un sprint (Anexo A). None significa "Sin datos"."""

    sprint: int
    defectos_encontrados: int | None = None
    defectos_corregidos: int | None = None
    horas_correccion: Numero | None = None
    kloc: Numero | None = None
    cobertura_pct: Numero | None = None


@dataclass(frozen=True)
class ActividadSprint:
    sprint: int
    estado: EstadoActividad
    resultado: Resultado | None = None


@dataclass(frozen=True)
class Indicador:
    nivel: Nivel
    valor: Decimal | None = None


@dataclass(frozen=True)
class EvaluacionSprint:
    sprint: int
    densidad: Indicador
    cobertura: Indicador
    tiempo_correccion: Indicador
    actividades: Indicador
    nivel: Nivel
    actividades_planeadas: int
    actividades_realizadas: int


@dataclass(frozen=True)
class EvaluacionProyecto:
    estado_general: str
    sprint_referencia: int | None
    historial: list[EvaluacionSprint]


def _decimal(valor: Numero) -> Decimal:
    return valor if isinstance(valor, Decimal) else Decimal(str(valor))


def _nivel_menor_es_mejor(valor: Decimal, optimo_max: Decimal, advertencia_max: Decimal) -> Nivel:
    if valor <= optimo_max:
        return Nivel.OPTIMO
    if valor <= advertencia_max:
        return Nivel.ADVERTENCIA
    return Nivel.CRITICO


def evaluar_densidad(sprint: int, metricas: Iterable[MetricaSprint]) -> Indicador:
    """Defectos encontrados del sprint 1 al N entre los KLOC del sprint N (Anexo A).

    Es "Sin datos" si el sprint N no tiene KLOC (o es 0) o no tiene defectos encontrados.
    En la suma, los sprints anteriores sin dato cuentan como 0.
    """
    metricas = list(metricas)
    actual = next((m for m in metricas if m.sprint == sprint), None)
    if actual is None or not actual.kloc or actual.defectos_encontrados is None:
        return Indicador(Nivel.SIN_DATOS)
    acumulados = sum(m.defectos_encontrados or 0 for m in metricas if m.sprint <= sprint)
    valor = Decimal(acumulados) / _decimal(actual.kloc)
    nivel = _nivel_menor_es_mejor(
        valor, umbrales.DENSIDAD_OPTIMO_MAX, umbrales.DENSIDAD_ADVERTENCIA_MAX
    )
    return Indicador(nivel, valor)


def evaluar_cobertura(metrica: MetricaSprint | None) -> Indicador:
    if metrica is None or metrica.cobertura_pct is None:
        return Indicador(Nivel.SIN_DATOS)
    valor = _decimal(metrica.cobertura_pct)
    if valor >= umbrales.COBERTURA_OPTIMO_MIN:
        return Indicador(Nivel.OPTIMO, valor)
    if valor >= umbrales.COBERTURA_ADVERTENCIA_MIN:
        return Indicador(Nivel.ADVERTENCIA, valor)
    return Indicador(Nivel.CRITICO, valor)


def evaluar_tiempo_correccion(metrica: MetricaSprint | None) -> Indicador:
    """Horas de corrección entre defectos corregidos del mismo sprint (Anexo A).

    "No aplica" si no se corrigió ningún defecto: no hay tiempo que medir.
    "Sin datos" si falta alguno de los dos campos.
    """
    if metrica is None:
        return Indicador(Nivel.SIN_DATOS)
    if metrica.defectos_corregidos == 0:
        return Indicador(Nivel.NO_APLICA)
    if metrica.defectos_corregidos is None or metrica.horas_correccion is None:
        return Indicador(Nivel.SIN_DATOS)
    valor = _decimal(metrica.horas_correccion) / Decimal(metrica.defectos_corregidos)
    nivel = _nivel_menor_es_mejor(
        valor, umbrales.TIEMPO_OPTIMO_MAX, umbrales.TIEMPO_ADVERTENCIA_MAX
    )
    return Indicador(nivel, valor)


def _realizadas_del_sprint(
    sprint: int, actividades: Iterable[ActividadSprint]
) -> list[ActividadSprint]:
    return [a for a in actividades if a.sprint == sprint and a.estado == EstadoActividad.REALIZADA]


def evaluar_actividades(sprint: int, actividades: Iterable[ActividadSprint]) -> Indicador:
    """Solo cuentan las actividades Realizadas del sprint (Anexo C, regla 2).

    "Con hallazgos" no penaliza; "No satisfactorio" sí.
    """
    realizadas = _realizadas_del_sprint(sprint, actividades)
    total = len(realizadas)
    no_satisfactorias = sum(1 for a in realizadas if a.resultado == Resultado.NO_SATISFACTORIO)
    if total == 0 or no_satisfactorias * 2 > total:
        nivel = Nivel.CRITICO
    elif total < umbrales.ACTIVIDADES_OPTIMO_MIN or no_satisfactorias > 0:
        nivel = Nivel.ADVERTENCIA
    else:
        nivel = Nivel.OPTIMO
    return Indicador(nivel, Decimal(total))


def combinar_niveles(niveles: Iterable[Nivel]) -> Nivel:
    """Estado de un sprint a partir de sus indicadores (Anexo C, reglas 3 y 4).

    Crítico si alguno es Crítico; si no, Advertencia si alguno es Advertencia o
    Sin datos; si no, Óptimo. "No aplica" no se considera.
    """
    considerados = [n for n in niveles if n != Nivel.NO_APLICA]
    if Nivel.CRITICO in considerados:
        return Nivel.CRITICO
    if Nivel.ADVERTENCIA in considerados or Nivel.SIN_DATOS in considerados:
        return Nivel.ADVERTENCIA
    return Nivel.OPTIMO


def evaluar_sprint(
    sprint: int,
    metricas: Iterable[MetricaSprint],
    actividades: Iterable[ActividadSprint],
) -> EvaluacionSprint:
    metricas = list(metricas)
    actividades = list(actividades)
    actual = next((m for m in metricas if m.sprint == sprint), None)
    densidad = evaluar_densidad(sprint, metricas)
    cobertura = evaluar_cobertura(actual)
    tiempo = evaluar_tiempo_correccion(actual)
    indicador_actividades = evaluar_actividades(sprint, actividades)
    del_sprint = [a for a in actividades if a.sprint == sprint]
    return EvaluacionSprint(
        sprint=sprint,
        densidad=densidad,
        cobertura=cobertura,
        tiempo_correccion=tiempo,
        actividades=indicador_actividades,
        nivel=combinar_niveles(
            [densidad.nivel, cobertura.nivel, tiempo.nivel, indicador_actividades.nivel]
        ),
        # Toda actividad del sprint se planeó; las Realizadas son las que se ejecutaron.
        actividades_planeadas=len(del_sprint),
        actividades_realizadas=len(_realizadas_del_sprint(sprint, del_sprint)),
    )


def sprints_evaluables(
    metricas: Iterable[MetricaSprint], actividades: Iterable[ActividadSprint]
) -> list[int]:
    """Sprints con algún registro de métricas o alguna actividad Realizada (Anexo C, regla 5).

    Las actividades Planeadas no hacen evaluable un sprint (Anexo C, regla 1).
    """
    sprints = {m.sprint for m in metricas}
    sprints |= {a.sprint for a in actividades if a.estado == EstadoActividad.REALIZADA}
    return sorted(sprints)


def evaluar_proyecto(
    metricas: Iterable[MetricaSprint], actividades: Iterable[ActividadSprint]
) -> EvaluacionProyecto:
    """Estado general, sprint de referencia e historial por sprint (RF-10, RF-11)."""
    metricas = list(metricas)
    actividades = list(actividades)
    sprints = sprints_evaluables(metricas, actividades)
    if not sprints:
        return EvaluacionProyecto(ESTADO_SIN_EVALUACION, None, [])
    historial = [evaluar_sprint(s, metricas, actividades) for s in sprints]
    referencia = historial[-1]
    return EvaluacionProyecto(str(referencia.nivel), referencia.sprint, historial)
