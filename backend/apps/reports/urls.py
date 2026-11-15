from django.urls import path

from . import views

urlpatterns = [
    path("projects/<int:proyecto_id>/report/", views.ReporteView.as_view(), name="project-report"),
    # Sin / final, como en la SDS 3.4.
    path(
        "projects/<int:proyecto_id>/report.csv",
        views.ReporteCsvView.as_view(),
        name="project-report-csv",
    ),
]
