"""Rutas del Gestor SQA.

Todo lo que empieza con /api/ es la API REST. Cualquier otra ruta devuelve la
SPA de React, que resuelve su propia navegación (SDS 3.5).
"""

from django.urls import include, path, re_path

from apps.core.views import spa_index

urlpatterns = [
    path("api/", include("apps.core.urls")),
    re_path(r"^(?!api/|static/).*$", spa_index, name="spa"),
]
