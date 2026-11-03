from django.urls import path

from . import views

urlpatterns = [
    path("projects/<int:proyecto_id>/report/", views.ReporteView.as_view(), name="project-report"),
]
