#!/usr/bin/env bash
# Despliega el Gestor SQA en el servidor (SDS 5.3).
# Uso: ./deploy.sh [rama]     (por defecto, main)
# Respalda la base de datos, trae la versión de la rama, reconstruye y espera a que la
# aplicación esté sana. Anota cada despliegue en la bitácora (SQAP 7).
set -euo pipefail
cd "$(dirname "$0")"

rama="${1:-main}"
[ -f .env ] || { echo "Falta el archivo .env (cópialo de .env.example y llénalo)."; exit 1; }

if [ -n "$(docker compose ps -q db 2>/dev/null)" ]; then
  ./respaldo.sh
else
  echo "Primera vez: no hay base de datos que respaldar."
fi

git fetch origin "$rama"
git checkout "$rama"
git pull --ff-only origin "$rama"

docker compose up -d --build

echo "Esperando a que la aplicación responda..."
estado="desconocido"
for _ in $(seq 1 40); do
  estado="$(docker inspect -f '{{.State.Health.Status}}' "$(docker compose ps -q app)" 2>/dev/null || echo iniciando)"
  [ "$estado" = "healthy" ] && break
  sleep 5
done

if [ "$estado" != "healthy" ]; then
  echo "La aplicación no quedó sana (estado: $estado). Últimos registros:"
  docker compose logs --tail=60 app
  exit 1
fi

echo "Desplegado: rama $rama, commit $(git rev-parse --short HEAD), $(date '+%Y-%m-%d %H:%M')."
echo "Anota este despliegue en docs/sqa/bitacora.md (tipo: Despliegue)."
