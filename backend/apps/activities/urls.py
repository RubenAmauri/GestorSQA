from django.urls import path

from . import views

urlpatterns = [
    path(
        "projects/<int:proyecto_id>/activities/",
        views.ActividadesView.as_view(),
        name="project-activities",
    ),
]
