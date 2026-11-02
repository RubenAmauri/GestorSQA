#!/usr/bin/env bash
# Respaldo de la base de datos (SDS 5.3, SQAP 5.1.4).
# Uso: ./respaldo.sh
# Deja un archivo comprimido en respaldos/. Cópialo fuera de la VM, por ejemplo:
#   scp usuario@servidor:GestorSQA/respaldos/<archivo> .
set -euo pipefail
cd "$(dirname "$0")"

mkdir -p respaldos
archivo="respaldos/gestorsqa-$(date +%Y%m%d-%H%M%S).sql.gz"

# Las variables se expanden dentro del contenedor, donde MariaDB ya las tiene.
docker compose exec -T db sh -c \
  'mariadb-dump -uroot -p"$MARIADB_ROOT_PASSWORD" --single-transaction --databases "$MARIADB_DATABASE"' \
  | gzip > "$archivo"

echo "Respaldo creado: $archivo ($(du -h "$archivo" | cut -f1))"
