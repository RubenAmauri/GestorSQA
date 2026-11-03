"""Arma el reporte de salud de un proyecto (RF-10, RF-11; SDS 3.3.5 y 3.4).

Lee las métricas y actividades del proyecto en dos consultas (sin N+1, RNF-02), las
convierte a las estructuras puras del motor de salud y calcula todo con
``evaluar_proyecto``. La regla del Anexo C vive solo en ``salud.py``.
"""

from decimal import ROUND_HALF_UP, Decimal

from apps.activities.models import ActivityEntry
from apps.metrics.models import MetricEntry
from apps.projects.models import Project

from .salud import (
    ActividadSprint,
    EstadoActividad,
    EvaluacionSprint,
    Indicador,
    MetricaSprint,
    Resultado,
    evaluar_proyecto,
)

DOS_DECIMALES = Decimal("0.01")


def _metricas(proyecto: Project) -> list[MetricaSprint]:
    return [
        MetricaSprint(
            sprint=m.sprint,
            defectos_encontrados=m.defectos_encontrados,
            defectos_corregidos=m.defectos_corregidos,
            horas_correccion=m.horas_correccion,
            kloc=m.kloc,
            cobertura_pct=m.cobertura_pct,
        )
        for m in MetricEntry.objects.filter(project=proyecto)
    ]


def _actividad_para_salud(actividad: ActivityEntry) -> ActividadSprint:
    resultado = Resultado(actividad.resultado) if actividad.resultado else None
    return ActividadSprint(actividad.sprint, EstadoActividad(actividad.estado), resultado)


def _indicador(indicador: Indicador) -> dict:
    valor = None
    if indicador.valor is not None:
        valor = float(indicador.valor.quantize(DOS_DECIMALES, rounding=ROUND_HALF_UP))
    return {"nivel": str(indicador.nivel), "valor": valor}


def _sprint(evaluacion: EvaluacionSprint) -> dict:
    return {
        "sprint": evaluacion.sprint,
        "nivel": str(evaluacion.nivel),
        "densidad": _indicador(evaluacion.densidad),
        "cobertura": _indicador(evaluacion.cobertura),
        "tiempo_correccion": _indicador(evaluacion.tiempo_correccion),
        "actividades": _indicador(evaluacion.actividades),
        "actividades_planeadas": evaluacion.actividades_planeadas,
        "actividades_realizadas": evaluacion.actividades_realizadas,
    }


def _actividad(actividad: ActivityEntry) -> dict:
    return {
        "id": actividad.id,
        "sprint": actividad.sprint,
        "tipo": actividad.tipo,
        "nombre": actividad.nombre_mostrado,
        "estado": actividad.estado,
        "resultado": actividad.resultado,
        "responsable": actividad.responsable.email,
        "fecha": actividad.fecha.isoformat() if actividad.fecha else None,
    }


def reporte_de(proyecto: Project) -> dict:
    """Contenido del reporte según la SDS 3.4.

    Encabezado, estado general, indicadores del sprint de referencia, historial por
    sprint (con actividades planeadas contra realizadas) y la lista de actividades.
    """
    actividades = list(ActivityEntry.objects.filter(project=proyecto).select_related("responsable"))
    evaluacion = evaluar_proyecto(
        _metricas(proyecto), [_actividad_para_salud(a) for a in actividades]
    )
    historial = [_sprint(e) for e in evaluacion.historial]
    return {
        "proyecto": {
            "id": proyecto.id,
            "nombre": proyecto.nombre,
            "periodo_nombre": proyecto.periodo_nombre,
            "fecha_inicio": proyecto.fecha_inicio.isoformat(),
            "fecha_fin": proyecto.fecha_fin.isoformat(),
        },
        "estado_general": evaluacion.estado_general,
        "sprint_referencia": evaluacion.sprint_referencia,
        "indicadores": historial[-1] if historial else None,
        "historial": historial,
        "actividades": [_actividad(a) for a in actividades],
    }
