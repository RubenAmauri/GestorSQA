# Imagen de producción del Gestor SQA (ADR-08, SDS 5.1).
# Etapa 1: compila la SPA de React. Etapa 2: empaqueta Django con la SPA compilada.

FROM node:22-alpine AS frontend
WORKDIR /frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY frontend/ ./
RUN npm run build

FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1
RUN apt-get update \
    && apt-get install -y --no-install-recommends pkg-config gcc libmariadb-dev curl \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /app/backend
COPY backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/ ./
COPY --from=frontend /frontend/dist /app/frontend/dist
RUN DJANGO_DEBUG=1 DB_ENGINE=sqlite python manage.py collectstatic --noinput \
    && useradd --create-home app \
    && chown -R app /app
USER app
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD curl -fsS http://localhost:8000/api/health/ || exit 1
CMD ["sh", "-c", "python manage.py migrate --noinput && gunicorn config.wsgi -b 0.0.0.0:8000 -w ${GUNICORN_WORKERS:-3}"]
