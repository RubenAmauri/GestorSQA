from django.urls import path

from . import views

urlpatterns = [
    path("projects/", views.ProyectosView.as_view(), name="projects"),
    path("projects/join/", views.UnionView.as_view(), name="projects-join"),
    path("projects/<int:proyecto_id>/", views.ProyectoDetalleView.as_view(), name="project-detail"),
    path(
        "projects/<int:proyecto_id>/codigo/regenerar/",
        views.RegenerarCodigoView.as_view(),
        name="project-regenerar-codigo",
    ),
    path(
        "projects/<int:proyecto_id>/members/",
        views.MiembrosView.as_view(),
        name="project-members",
    ),
    path(
        "projects/<int:proyecto_id>/members/<int:user_id>/",
        views.MiembroDetalleView.as_view(),
        name="project-member-detail",
    ),
]
