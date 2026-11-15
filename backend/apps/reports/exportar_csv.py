"""Reporte de salud en CSV (RF-12, HU-09; SDS 3.4).

Solo da formato al contenido que arma ``reporte_de``: el cálculo vive en el motor de
salud. Tres secciones separadas por una línea vacía: indicadores del sprint de
referencia (con el estado general), historial por sprint y actividades.
"""

import csv
import io

from django.utils import timezone
from django.utils.text import slugify

# Una celda que empieza así la interpreta Excel como fórmula (inyección CSV, OWASP).
PREFIJOS_DE_FORMULA = ("=", "+", "-", "@", "\t", "\r")

INDICADORES = [
    ("densidad", "Densidad de defectos (def/KLOC)"),
    ("cobertura", "Cobertura de pruebas (%)"),
    ("tiempo_correccion", "Tiempo promedio de corrección (h)"),
    ("actividades", "Actividades realizadas"),
]

# Por cada indicador, su valor y su nivel; al final, planeadas contra realizadas.
COLUMNAS_HISTORIAL = [
    "Sprint",
    "Nivel",
    *[columna for _, etiqueta in INDICADORES for columna in (etiqueta, f"Nivel · {etiqueta}")],
    "Planeadas",
    "Realizadas",
]

COLUMNAS_ACTIVIDADES = [
    "Sprint",
    "Tipo",
    "Nombre",
    "Estado",
    "Resultado",
    "Responsable",
    "Fecha",
    "Hallazgos",
]


def texto_seguro(texto: str) -> str:
    """Neutraliza una fórmula anteponiendo un apóstrofo; Excel la muestra como texto."""
    return f"'{texto}" if texto.startswith(PREFIJOS_DE_FORMULA) else texto


def _celda(valor):
    if valor is None:
        return ""
    if isinstance(valor, str):
        return texto_seguro(valor)
    if isinstance(valor, float) and valor.is_integer():
        return int(valor)
    return valor


def csv_del_reporte(reporte: dict) -> str:
    salida = io.StringIO()
    escritor = csv.writer(salida)

    def fila(*celdas) -> None:
        escritor.writerow([_celda(c) for c in celdas])

    _seccion_indicadores(fila, reporte)
    fila()
    _seccion_historial(fila, reporte["historial"])
    fila()
    _seccion_actividades(fila, reporte["actividades"])
    return salida.getvalue()


def _seccion_indicadores(fila, reporte: dict) -> None:
    proyecto = reporte["proyecto"]
    fila("Reporte de salud")
    fila("Proyecto", proyecto["nombre"])
    fila("Periodo", proyecto["periodo_nombre"])
    fila("Fecha de inicio", proyecto["fecha_inicio"])
    fila("Fecha de fin", proyecto["fecha_fin"])
    fila("Estado general", reporte["estado_general"])
    fila("Sprint de referencia", reporte["sprint_referencia"])
    fila("Indicador", "Valor", "Nivel")
    indicadores = reporte["indicadores"]
    if indicadores is None:  # Sin evaluación: la tabla queda vacía.
        return
    for clave, etiqueta in INDICADORES:
        fila(etiqueta, indicadores[clave]["valor"], indicadores[clave]["nivel"])


def _seccion_historial(fila, historial: list[dict]) -> None:
    fila("Historial por sprint")
    fila(*COLUMNAS_HISTORIAL)
    for sprint in historial:
        celdas = [sprint["sprint"], sprint["nivel"]]
        for clave, _ in INDICADORES:
            celdas += [sprint[clave]["valor"], sprint[clave]["nivel"]]
        fila(*celdas, sprint["actividades_planeadas"], sprint["actividades_realizadas"])


def _seccion_actividades(fila, actividades: list[dict]) -> None:
    fila("Actividades")
    fila(*COLUMNAS_ACTIVIDADES)
    for a in actividades:
        fila(
            a["sprint"],
            a["tipo"],
            a["nombre"],
            a["estado"],
            a["resultado"],
            a["responsable"],
            a["fecha"],
            a["hallazgos"],
        )


def nombre_de_archivo(reporte: dict) -> str:
    """reporte-<nombre sin acentos ni espacios>-<fecha de hoy>.csv"""
    proyecto = reporte["proyecto"]
    nombre = slugify(proyecto["nombre"]) or f"proyecto-{proyecto['id']}"
    return f"reporte-{nombre}-{timezone.localdate().isoformat()}.csv"
