from django.urls import path

from . import views

urlpatterns = [
    path(
        "projects/<int:proyecto_id>/metrics/",
        views.MetricasView.as_view(),
        name="project-metrics",
    ),
]
