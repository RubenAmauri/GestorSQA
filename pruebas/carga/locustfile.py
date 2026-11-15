"""Prueba de carga PR-RNF02-01 (RNF-02): 50 usuarios simultáneos consultan el reporte.

Meta: percentil 95 < 3 s en GET /api/projects/{id}/report/. Los datos se siembran con
``python manage.py sembrar_carga`` y la guía completa está en README.md.

Cada usuario virtual toma una cuenta distinta (carga-01, carga-02, ...), inicia sesión
una sola vez al empezar, respetando CSRF, y luego consulta el reporte de uno de sus
proyectos con una espera entre consultas.

El servidor permite 5 inicios de sesión por minuto por IP (RNF-05) y no se desactiva:
los usuarios entran escalonados (--spawn-rate 0.077, uno cada 13 s) y la medición se
reinicia cuando ya entraron todos (--reset-stats). Si aun así llega un 429, el usuario
espera lo que diga Retry-After y reintenta; queda registrado en el log y en los fallos
con el nombre "inicio de sesión".

Variables de entorno:
- CARGA_PASSWORD (obligatoria): la contraseña con la que se sembraron los usuarios.
- CARGA_PRIMER_USUARIO (1): número de la primera cuenta que usa este proceso; en modo
  distribuido, cada worker usa un rango distinto.
- CARGA_USUARIOS (50): cuántas cuentas hay; un usuario virtual de más se detiene.
- CARGA_ESPERA_MIN y CARGA_ESPERA_MAX (1 y 3): espera entre consultas, en segundos.
  Con 0 y 0 se mide el peor caso, sin espera.
"""

import itertools
import logging
import os
import random

import gevent
from locust import HttpUser, between, task
from locust.exception import StopUser

PASSWORD = os.environ.get("CARGA_PASSWORD", "")
PRIMER_USUARIO = int(os.environ.get("CARGA_PRIMER_USUARIO", "1"))
TOTAL_USUARIOS = int(os.environ.get("CARGA_USUARIOS", "50"))
ESPERA_MIN = float(os.environ.get("CARGA_ESPERA_MIN", "1"))
ESPERA_MAX = float(os.environ.get("CARGA_ESPERA_MAX", "3"))

# Cada usuario virtual de este proceso toma el siguiente número de cuenta.
_numeros = itertools.count(PRIMER_USUARIO)

NOMBRE_REPORTE = "/api/projects/[id]/report/"
NOMBRE_INICIO_SESION = "inicio de sesión"


def correo_de_carga(numero: int) -> str:
    """El mismo formato que usa el comando sembrar_carga."""
    return f"carga-{numero:02d}@prueba.gestorsqa"


class UsuarioDelReporte(HttpUser):
    wait_time = between(ESPERA_MIN, ESPERA_MAX)

    def on_start(self) -> None:
        if not PASSWORD:
            logging.error("Falta CARGA_PASSWORD; el usuario virtual no inicia.")
            raise StopUser()
        numero = next(_numeros)
        if numero >= PRIMER_USUARIO + TOTAL_USUARIOS:
            logging.error("No hay cuenta de carga para el usuario virtual %s.", numero)
            raise StopUser()
        self.correo = correo_de_carga(numero)
        self._iniciar_sesion()
        respuesta = self.client.get("/api/projects/", name="mis proyectos")
        self.proyectos = [p["id"] for p in respuesta.json()] if respuesta.ok else []
        if not self.proyectos:
            logging.error("%s no es miembro de ningún proyecto.", self.correo)
            raise StopUser()

    def _iniciar_sesion(self) -> None:
        """Una sola vez por usuario virtual: cookie CSRF y luego el inicio de sesión."""
        self.client.get("/api/auth/csrf/", name="csrf")
        while True:
            with self.client.post(
                "/api/auth/login/",
                json={"email": self.correo, "password": PASSWORD},
                # Django revisa el Referer en peticiones HTTPS que modifican datos.
                headers={
                    "X-CSRFToken": self.client.cookies.get("csrftoken", ""),
                    "Referer": f"{self.host}/",
                },
                name=NOMBRE_INICIO_SESION,
                catch_response=True,
            ) as respuesta:
                if respuesta.status_code == 200:
                    return
                if respuesta.status_code == 429:
                    espera = int(respuesta.headers.get("Retry-After", "60"))
                    mensaje = f"429 por el límite de intentos; se reintenta en {espera} s"
                    logging.warning("%s: %s", self.correo, mensaje)
                    respuesta.failure(mensaje)
                else:
                    respuesta.failure(f"Inicio de sesión rechazado ({respuesta.status_code})")
                    logging.error("%s no pudo iniciar sesión.", self.correo)
                    raise StopUser()
            gevent.sleep(espera)

    @task
    def consultar_reporte(self) -> None:
        proyecto = random.choice(self.proyectos)  # noqa: S311 - no es criptográfico
        self.client.get(f"/api/projects/{proyecto}/report/", name=NOMBRE_REPORTE)
