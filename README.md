# Gestor SQA

Plataforma web para monitorear las actividades de aseguramiento de la calidad (SQA) de proyectos de software: registro de proyectos por periodo, métricas y actividades SQA por sprint, y reporte del estado de salud (Óptimo, Advertencia o Crítico).

Proyecto de la materia Calidad del Software. La construcción sigue el Plan de Aseguramiento de la Calidad (SQAP) del equipo.

## Estructura

| Carpeta | Contenido |
|---|---|
| `backend/` | API REST con Django y Django REST Framework (`apps/`: accounts, projects, metrics, activities, reports, core) |
| `frontend/` | Interfaz web con React y Vite |
| `docs/sqa/` | Evidencia de SQA: bitácora, revisiones, auditorías, resultados de pruebas y reportes |
| `scripts/sqa/` | Scripts de apoyo para SQA |
| `.github/` | Integración continua y plantillas de PR e issues |

## Desarrollo local

Requisito: Docker con Docker Compose.

```bash
cp .env.example .env    # la primera vez; cambia las contraseñas
docker compose -f compose.dev.yml up --build
```

- Interfaz: http://localhost:5173
- API: http://localhost:8000/api/health/

### Sin Docker (solo para pruebas rápidas)

```bash
# Backend (usa SQLite en lugar de MariaDB)
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt   # requiere el cliente de MariaDB/MySQL para mysqlclient
export DB_ENGINE=sqlite DJANGO_DEBUG=1
python manage.py migrate && python manage.py createcachetable
pytest --cov

# Frontend
cd frontend
npm install
npm run lint && npm test
```

## Verificaciones de calidad

Cada pull request a `main` ejecuta la integración continua (`.github/workflows/ci.yml`):

| Etapa | Verificaciones |
|---|---|
| Backend | ruff (estilo y análisis estático), Bandit (seguridad), radon (complejidad ≤ 10), migraciones al día, pytest con cobertura ≥ 75 %, `check --deploy` |
| Frontend | ESLint, Vitest, compilación |
| Imagen | Construcción de la imagen de Docker de producción |

## Cómo contribuir

1. Crea un issue con la plantilla **Tarea** (o **Defecto o no conformidad**).
2. Crea una rama `<requisito>-<descripcion>`, por ejemplo `rf07-captura-metricas`.
3. Escribe el código y sus pruebas, identificadas con el ID del catálogo (por ejemplo `PR-RF07-01`).
4. Abre un pull request y llena la plantilla.
5. Otro integrante revisa y aprueba. **Nadie aprueba su propio PR.**
6. Con la CI en verde y la aprobación, se hace merge.

La primera vez, crea las etiquetas del repositorio con `./scripts/sqa/crear-etiquetas.sh` (requiere GitHub CLI con sesión iniciada).

## Documentos del proyecto

SRS v1.1, SDS v0.4, SQAP v1.0, modelo C4 y wireframes v1.
