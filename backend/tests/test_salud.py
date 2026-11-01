"""Pruebas del motor de salud (RF-10, RF-11). Catálogo: SQAP 5.1.2 e.

Funciones puras: no usan base de datos.
"""

from decimal import Decimal

import pytest

from apps.reports.salud import (
    ESTADO_SIN_EVALUACION,
    ActividadSprint,
    EstadoActividad,
    Nivel,
    Resultado,
    combinar_niveles,
    evaluar_actividades,
    evaluar_cobertura,
    evaluar_densidad,
    evaluar_proyecto,
    evaluar_sprint,
    evaluar_tiempo_correccion,
)
from apps.reports.salud import MetricaSprint as M

REALIZADA = EstadoActividad.REALIZADA
PLANEADA = EstadoActividad.PLANEADA


def act(sprint, estado=REALIZADA, resultado=Resultado.SATISFACTORIO):
    return ActividadSprint(sprint, estado, resultado if estado == REALIZADA else None)


# PR-RF10-01 · Límites de densidad -------------------------------------------------


@pytest.mark.parametrize(
    ("defectos", "kloc", "esperado"),
    [
        (5, 1, Nivel.OPTIMO),  # 5.00
        (501, 100, Nivel.ADVERTENCIA),  # 5.01
        (10, 1, Nivel.ADVERTENCIA),  # 10.00
        (1001, 100, Nivel.CRITICO),  # 10.01
    ],
)
def test_pr_rf10_01_limites_de_densidad(defectos, kloc, esperado):
    indicador = evaluar_densidad(1, [M(1, defectos_encontrados=defectos, kloc=kloc)])
    assert indicador.nivel == esperado


def test_pr_rf10_01_densidad_sin_error_de_redondeo():
    """7 / 0.7 es exactamente 10 (Advertencia); en punto flotante daría 10.000000000000002."""
    indicador = evaluar_densidad(1, [M(1, defectos_encontrados=7, kloc=0.7)])
    assert indicador.valor == Decimal("10")
    assert indicador.nivel == Nivel.ADVERTENCIA


# PR-RF10-02 · Límites de cobertura ------------------------------------------------


@pytest.mark.parametrize(
    ("cobertura", "esperado"),
    [
        ("59.9", Nivel.CRITICO),
        ("60", Nivel.ADVERTENCIA),
        ("74.9", Nivel.ADVERTENCIA),
        ("75", Nivel.OPTIMO),
    ],
)
def test_pr_rf10_02_limites_de_cobertura(cobertura, esperado):
    assert evaluar_cobertura(M(1, cobertura_pct=Decimal(cobertura))).nivel == esperado


# PR-RF10-03 · Límites de tiempo de corrección --------------------------------------


@pytest.mark.parametrize(
    ("horas", "corregidos", "esperado"),
    [
        (4, 1, Nivel.OPTIMO),  # 4.00
        ("4.01", 1, Nivel.ADVERTENCIA),
        (8, 1, Nivel.ADVERTENCIA),  # 8.00
        ("8.01", 1, Nivel.CRITICO),
    ],
)
def test_pr_rf10_03_limites_de_tiempo(horas, corregidos, esperado):
    metrica = M(1, horas_correccion=Decimal(str(horas)), defectos_corregidos=corregidos)
    assert evaluar_tiempo_correccion(metrica).nivel == esperado


def test_pr_rf10_03_tiempo_es_promedio_por_defecto():
    indicador = evaluar_tiempo_correccion(M(1, horas_correccion=14, defectos_corregidos=4))
    assert indicador.valor == Decimal("3.5")


# PR-RF10-04 · Número de actividades realizadas -------------------------------------


@pytest.mark.parametrize(
    ("cantidad", "esperado"),
    [(0, Nivel.CRITICO), (1, Nivel.ADVERTENCIA), (2, Nivel.OPTIMO), (3, Nivel.OPTIMO)],
)
def test_pr_rf10_04_actividades_0_1_2(cantidad, esperado):
    actividades = [act(1) for _ in range(cantidad)]
    assert evaluar_actividades(1, actividades).nivel == esperado


# PR-RF10-05 · Actividades "No satisfactorio" ----------------------------------------


@pytest.mark.parametrize(
    ("resultados", "esperado"),
    [
        # alguna, pero no más de la mitad
        ([Resultado.NO_SATISFACTORIO, Resultado.SATISFACTORIO], Nivel.ADVERTENCIA),
        ([Resultado.NO_SATISFACTORIO] + [Resultado.SATISFACTORIO] * 2, Nivel.ADVERTENCIA),
        # más de la mitad
        ([Resultado.NO_SATISFACTORIO] * 2 + [Resultado.SATISFACTORIO], Nivel.CRITICO),
        ([Resultado.NO_SATISFACTORIO], Nivel.CRITICO),
    ],
)
def test_pr_rf10_05_no_satisfactorio(resultados, esperado):
    actividades = [act(1, resultado=r) for r in resultados]
    assert evaluar_actividades(1, actividades).nivel == esperado


# PR-RF10-06 · "Con hallazgos" no penaliza -------------------------------------------


def test_pr_rf10_06_con_hallazgos_no_penaliza():
    actividades = [act(1, resultado=Resultado.CON_HALLAZGOS)] * 2
    assert evaluar_actividades(1, actividades).nivel == Nivel.OPTIMO


# PR-RF10-07 · Las actividades Planeadas no cuentan ----------------------------------


def test_pr_rf10_07_planeadas_no_cuentan():
    actividades = [act(1), act(1, PLANEADA), act(1, PLANEADA)]
    indicador = evaluar_actividades(1, actividades)
    assert indicador.valor == Decimal(1)
    assert indicador.nivel == Nivel.ADVERTENCIA


def test_actividades_de_otros_sprints_no_cuentan():
    assert evaluar_actividades(2, [act(1), act(1)]).nivel == Nivel.CRITICO


# PR-RF10-08 · Sin datos cuenta como Advertencia --------------------------------------


def test_pr_rf10_08_indicadores_sin_datos():
    vacia = M(1)
    assert evaluar_densidad(1, [vacia]).nivel == Nivel.SIN_DATOS
    assert evaluar_cobertura(vacia).nivel == Nivel.SIN_DATOS
    assert evaluar_tiempo_correccion(vacia).nivel == Nivel.SIN_DATOS
    assert evaluar_cobertura(None).nivel == Nivel.SIN_DATOS
    assert evaluar_tiempo_correccion(None).nivel == Nivel.SIN_DATOS
    assert evaluar_densidad(1, []).nivel == Nivel.SIN_DATOS


def test_pr_rf10_08_sin_datos_lleva_el_sprint_a_advertencia():
    metrica = M(1, defectos_encontrados=1, kloc=1, horas_correccion=2, defectos_corregidos=1)
    evaluacion = evaluar_sprint(1, [metrica], [act(1), act(1)])  # sin cobertura
    assert evaluacion.cobertura.nivel == Nivel.SIN_DATOS
    assert evaluacion.nivel == Nivel.ADVERTENCIA


def test_tiempo_sin_datos_si_falta_un_campo():
    assert evaluar_tiempo_correccion(M(1, defectos_corregidos=2)).nivel == Nivel.SIN_DATOS
    assert evaluar_tiempo_correccion(M(1, horas_correccion=3)).nivel == Nivel.SIN_DATOS


# PR-RF10-09 · No aplica no se considera ---------------------------------------------


def test_pr_rf10_09_no_aplica_si_no_hubo_correcciones():
    metrica = M(1, defectos_corregidos=0, horas_correccion=5)
    assert evaluar_tiempo_correccion(metrica).nivel == Nivel.NO_APLICA


def test_pr_rf10_09_no_aplica_no_afecta_el_estado():
    metrica = M(1, defectos_encontrados=1, kloc=1, cobertura_pct=80, defectos_corregidos=0)
    evaluacion = evaluar_sprint(1, [metrica], [act(1), act(1)])
    assert evaluacion.tiempo_correccion.nivel == Nivel.NO_APLICA
    assert evaluacion.nivel == Nivel.OPTIMO


# PR-RF10-10 · KLOC en 0 ---------------------------------------------------------------


def test_pr_rf10_10_kloc_cero_es_sin_datos():
    assert evaluar_densidad(1, [M(1, defectos_encontrados=3, kloc=0)]).nivel == Nivel.SIN_DATOS


# PR-RF10-11 · Densidad acumulada con sprints sin dato -------------------------------


def test_pr_rf10_11_densidad_acumulada():
    metricas = [
        M(1, defectos_encontrados=10, kloc="0.88"),
        M(2, defectos_encontrados=8, kloc="2.28"),
        M(3, defectos_encontrados=4, kloc="3.6"),
    ]
    assert evaluar_densidad(3, metricas).valor == Decimal(22) / Decimal("3.6")
    assert evaluar_densidad(2, metricas).valor == Decimal(18) / Decimal("2.28")


def test_pr_rf10_11_sprints_anteriores_sin_dato_cuentan_como_cero():
    metricas = [M(1, kloc=1), M(2), M(3, defectos_encontrados=4, kloc=2)]
    assert evaluar_densidad(3, metricas).valor == Decimal(2)


def test_densidad_no_suma_sprints_posteriores():
    metricas = [M(1, defectos_encontrados=2, kloc=1), M(2, defectos_encontrados=50, kloc=1)]
    assert evaluar_densidad(1, metricas).valor == Decimal(2)


# PR-RF10-12 · Estado general con combinaciones ---------------------------------------


@pytest.mark.parametrize(
    ("niveles", "esperado"),
    [
        ([Nivel.OPTIMO] * 4, Nivel.OPTIMO),
        ([Nivel.OPTIMO, Nivel.ADVERTENCIA, Nivel.OPTIMO, Nivel.OPTIMO], Nivel.ADVERTENCIA),
        ([Nivel.OPTIMO, Nivel.SIN_DATOS, Nivel.OPTIMO, Nivel.OPTIMO], Nivel.ADVERTENCIA),
        ([Nivel.ADVERTENCIA, Nivel.CRITICO, Nivel.SIN_DATOS, Nivel.OPTIMO], Nivel.CRITICO),
        ([Nivel.OPTIMO, Nivel.NO_APLICA, Nivel.OPTIMO, Nivel.OPTIMO], Nivel.OPTIMO),
        ([Nivel.NO_APLICA, Nivel.CRITICO], Nivel.CRITICO),
    ],
)
def test_pr_rf10_12_combinaciones(niveles, esperado):
    assert combinar_niveles(niveles) == esperado


def test_pr_rf10_12_ejemplo_de_los_wireframes():
    """Datos de ejemplo de las láminas 06 y 07: sprints 1 a 3."""
    metricas = [
        M(1, 10, 5, 30, "0.88", None),
        M(2, 8, 6, 27, "2.28", 66),
        M(3, 4, 4, 14, "3.6", 78),
    ]
    actividades = [
        act(1),
        act(1, PLANEADA),
        *[act(2) for _ in range(3)],
        act(3),
        act(3, resultado=Resultado.CON_HALLAZGOS),
    ]
    resultado = evaluar_proyecto(metricas, actividades)
    niveles = [e.nivel for e in resultado.historial]
    assert niveles == [Nivel.CRITICO, Nivel.ADVERTENCIA, Nivel.ADVERTENCIA]
    assert resultado.sprint_referencia == 3
    assert resultado.estado_general == "ADVERTENCIA"


# PR-RF11 · Historial y sprint de referencia -----------------------------------------


def test_pr_rf11_01_historial_con_hueco():
    metricas = [M(1, cobertura_pct=80), M(3, cobertura_pct=80)]
    resultado = evaluar_proyecto(metricas, [])
    assert [e.sprint for e in resultado.historial] == [1, 3]
    assert resultado.sprint_referencia == 3


def test_pr_rf11_02_sin_evaluacion():
    resultado = evaluar_proyecto([], [])
    assert resultado.estado_general == ESTADO_SIN_EVALUACION
    assert resultado.sprint_referencia is None
    assert resultado.historial == []


def test_pr_rf11_02_solo_planeadas_sigue_sin_evaluacion():
    resultado = evaluar_proyecto([], [act(1, PLANEADA)])
    assert resultado.estado_general == ESTADO_SIN_EVALUACION


def test_pr_rf11_03_planeadas_no_definen_el_sprint_de_referencia():
    resultado = evaluar_proyecto([M(2, cobertura_pct=80)], [act(2), act(5, PLANEADA)])
    assert resultado.sprint_referencia == 2


def test_pr_rf11_03_actividad_realizada_si_hace_evaluable_el_sprint():
    resultado = evaluar_proyecto([M(1, cobertura_pct=80)], [act(4)])
    assert resultado.sprint_referencia == 4


def test_pr_rf11_04_planeadas_contra_realizadas():
    actividades = [act(1), act(1, PLANEADA), act(1, PLANEADA)]
    evaluacion = evaluar_sprint(1, [], actividades)
    assert evaluacion.actividades_planeadas == 3
    assert evaluacion.actividades_realizadas == 1
