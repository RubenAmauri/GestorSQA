# CLAUDE.md – Gestor SQA

Guía para Claude Code en este repositorio. Léela completa antes de cambiar código.

## Contexto

- Proyecto de equipo (5 integrantes) de la materia **Calidad del Software**. Lo que más se evalúa es la **evidencia de aseguramiento de calidad**: cada cambio debe ser trazable (requisito → diseño → issue → prueba) y verificable.
- El producto es una plataforma web que monitorea las actividades de SQA de **otros** proyectos: registro de proyectos por periodo, métricas y actividades SQA por sprint, y reporte de estado de salud (Óptimo / Advertencia / Crítico).
- Fechas (enunciado de trabajo): Versión Beta el **martes 3 de noviembre de 2026**; Entrega Final el **jueves 19 de noviembre de 2026** (producto desplegado, repositorio documentado y bitácora de SQA).
- Habla con el equipo en **español**, en tono casual. Código: identificadores del dominio en español (`evaluar_densidad`, `ActividadSprint`); lo propio del framework, como venga.

## Documentos de referencia

Fuente de verdad, en este orden: **enunciado de trabajo** > SRS v1.1 > SDS v0.4 > SQAP v1.0. Si dos documentos se contradicen, se decide contra el enunciado; lo que el enunciado no cubra lo decide el equipo y se registra en la bitácora. **No inventes requisitos**: si algo no está definido, pregunta y anótalo como pendiente.

Los documentos completos todavía no están en el repo; lo esencial está resumido abajo.

## Arquitectura (SDS)

- Monolito modular: SPA de React (Vite, React Router, Vitest, CSS propio responsivo) + API REST con Django 5.2 y Django REST Framework + MariaDB 11.4 (utf8mb4).
- Autenticación por sesión con cookie y CSRF; sin JWT, sin CORS (mismo dominio), sin correo electrónico.
- Django sirve la SPA compilada (WhiteNoise) en toda ruta fuera de `/api/`.
- Despliegue: Docker Compose con tres servicios (Caddy con HTTPS, app con gunicorn, MariaDB sin puerto publicado) en una VM de Azure.

| Ruta | Contenido |
|---|---|
| `backend/apps/accounts` | Usuario con correo como identificador (RF-01) |
| `backend/apps/projects` | Proyectos, código de unión, membresías, clases (RF-02 a RF-04, RF-09) |
| `backend/apps/metrics` | Métricas por sprint (RF-07) |
| `backend/apps/activities` | Actividades SQA (RF-08) |
| `backend/apps/reports` | `salud.py` y `umbrales.py` (motor de salud, funciones puras), reporte y CSV (RF-10 a RF-12) |
| `backend/apps/core` | Permisos, filtro por membresía, límites de intentos, healthcheck (RF-05, RF-06, RNF-03, RNF-05) |
| `frontend/src` | SPA |
| `docs/sqa/` | Evidencia de SQA (bitácora, revisiones, auditorías, pruebas, reportes) |

## Reglas de negocio clave

**Clases de usuario.** Admin Creador, Admin Normal, Colaborador, Auditor. "Admin" = Creador o Normal.
- Ver todo y descargar el reporte: las 4 clases.
- Registrar y editar métricas y actividades: Admin y Colaborador.
- Eliminar actividades, editar el proyecto y regenerar el código: solo Admin.
- Gestionar miembros (cambiar clase, incluido promover a Admin Normal, o expulsar): un Admin, **excepto sobre el Admin Creador y sobre sí mismo**.
- Auditor: solo lectura. No hay eliminación de proyectos en esta versión.

**Proyecto.** Nombre, nombre del periodo, fecha de inicio y fecha de fin, todos obligatorios; fin ≥ inicio. Único por `(creado_por, nombre normalizado, periodo normalizado)`; normalizar = recortar espacios, colapsar espacios internos y pasar a minúsculas. Quien lo crea queda como Admin Creador en la misma transacción.

**Unión.** Un código por proyecto (10 caracteres alfanuméricos, generado con `secrets`) que une como **Colaborador**; un Admin puede regenerarlo y el anterior deja de funcionar. Código inválido → mensaje genérico.

**Métricas** (SRS Anexo A). Un registro por proyecto y sprint: defectos encontrados, defectos corregidos, horas de corrección, KLOC (tamaño total al cierre del sprint), cobertura %. Todo opcional salvo el sprint; **vacío (NULL) ≠ 0**. Sin negativos; cobertura 0–100.

**Actividades** (Anexo B). Tipo: Caminata, Revisión de código, Auditoría de configuración, Pruebas, Otra (exige nombre). Estado: Planeada o Realizada. Resultado (Satisfactorio, Con hallazgos, No satisfactorio) **obligatorio si es Realizada y prohibido si es Planeada**. El responsable debe ser miembro.

**Estado de salud** (Anexo C). Implementado y probado en `backend/apps/reports/salud.py`; los umbrales viven en `umbrales.py`. **Cambiar un umbral exige cambiar también el Anexo C del SRS.** No dupliques esta lógica en otro lugar: la API y el CSV deben llamar a `evaluar_proyecto`.

## Convenciones de la API (SDS 3.4)

- Todo bajo `/api/`. Respuestas: 400 validación (y credenciales incorrectas, con mensaje genérico) · 401 sin sesión · 403 miembro sin permiso · **404 si no es miembro** (no revelar que el proyecto existe) · 409 duplicado · 429 límite de intentos.
- La autorización se valida **siempre en el servidor**, con una clase de permisos y un filtro por membresía centralizados en `core`. Ocultar botones en el frontend no es seguridad.
- Límites de intentos: inicio de sesión 5 por minuto por IP; unión por código 10 por hora por usuario.

## Calidad: reglas obligatorias (SQAP v1.0)

1. **Todo cambio entra por pull request** a partir de un issue. Rama: `<requisito>-<descripcion>` (p. ej. `rf07-captura-metricas`). Llena la plantilla del PR.
2. **Pruebas con ID del catálogo** en el nombre o docstring: `PR-<requisito>-<nn>` (p. ej. `test_pr_rf07_02_sprint_repetido`). Cada PR agrega al menos una prueba de su requisito.
3. **Definición de terminado:** issue con requisito, PR aprobado por un integrante **distinto del autor**, CI en verde, prueba con ID y documentos actualizados si cambió un requisito o el diseño.
4. **Metas de la CI:** ruff sin errores y con formato, Bandit sin severidad alta, complejidad ciclomática ≤ 10 por función, cobertura del backend ≥ 75 %, y ≥ 90 % en `apps/reports/salud.py`, `umbrales.py` y `apps/core/`.
5. **Ningún secreto en el repo:** contraseñas y claves van en `.env` (basado en `.env.example`) o se generan en la CI.
6. **Integridad de la evidencia:** nunca reescribas historial publicado (`push --force`, `rebase` de ramas compartidas), nunca cambies fechas y nunca edites entradas viejas de `docs/sqa/bitacora.md`: solo se agregan al final, con la fecha real. No inventes revisiones, métricas ni resultados.
7. Un defecto encontrado se registra como issue con la plantilla **Defecto o no conformidad** y se corrige con un commit que diga `Corrige #<n>`, más una prueba de regresión.

## Comandos

```bash
# Backend: desde backend/
pip install -r requirements-dev.txt
export DB_ENGINE=sqlite DJANGO_DEBUG=1          # rápido, sin MariaDB
ruff check . && ruff format --check .
bandit -r . -c pyproject.toml -lll
radon cc apps config -n C -s                     # no debe imprimir nada
python manage.py makemigrations --check --dry-run
pytest --cov --cov-fail-under=75
coverage report --fail-under=90 --include="apps/reports/salud.py,apps/reports/umbrales.py,apps/core/*"

# Frontend: desde frontend/
npm ci && npm run lint && npm test && npm run build

# Todo con MariaDB
cp .env.example .env && docker compose -f compose.dev.yml up --build
```

Corre las verificaciones antes de abrir un PR; la CI ejecuta las mismas.

## Trabajo en paralelo

Puede haber varias sesiones (personas o Claude Code) trabajando a la vez. Trabaja solo en tu rama y en el requisito de tu issue; no empujes a ramas de otras sesiones. Los mensajes de commit van en español, en modo imperativo, explicando el qué y el porqué, y cerrando el issue (`Cierra #<n>`).

## Estado del proyecto

| Requisito | Estado |
|---|---|
| Esqueleto, CI, plantillas | PR #1 |
| RF-10, RF-11 (motor de salud, cálculo) | PR #4 |
| RF-01 cuentas y sesión, RNF-05 límites | Pendiente (Beta) |
| RF-02, RF-03, RF-06 proyectos, unión, acceso + batería RNF-03 | Pendiente (Beta) |
| RF-07 métricas, RF-08 actividades | Pendiente (Beta) |
| RF-11 endpoint del reporte y pantalla | Pendiente (Beta) |
| RF-04, RF-05, RF-09, RF-12 | Pendiente (Entrega Final) |
| Despliegue en Azure (compose de producción, Caddy, deploy.sh, respaldo.sh) | Pendiente |

Actualiza esta tabla en el PR que cambie el estado de un requisito.
