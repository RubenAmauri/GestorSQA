from django.urls import path

from . import views

urlpatterns = [
    path("auth/csrf/", views.CsrfView.as_view(), name="auth-csrf"),
    path("auth/register/", views.RegistroView.as_view(), name="auth-register"),
    path("auth/login/", views.InicioSesionView.as_view(), name="auth-login"),
    path("auth/logout/", views.CierreSesionView.as_view(), name="auth-logout"),
    path("auth/me/", views.UsuarioActualView.as_view(), name="auth-me"),
]
