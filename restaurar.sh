#!/usr/bin/env bash
# Restaura un respaldo creado con respaldo.sh (prueba PR-OPS-01 del SQAP).
# Uso: ./restaurar.sh respaldos/gestorsqa-AAAAMMDD-HHMMSS.sql.gz
# Reemplaza los datos actuales: úsalo en un entorno de prueba o en una emergencia.
set -euo pipefail
cd "$(dirname "$0")"

archivo="${1:?Indica el archivo de respaldo}"
[ -f "$archivo" ] || { echo "No existe $archivo"; exit 1; }

read -r -p "Esto reemplaza los datos actuales con $archivo. ¿Continuar? (s/N) " respuesta
[ "$respuesta" = "s" ] || { echo "Cancelado."; exit 0; }

gunzip -c "$archivo" | docker compose exec -T db sh -c 'mariadb -uroot -p"$MARIADB_ROOT_PASSWORD"'
docker compose restart app
echo "Restaurado desde $archivo. Verifica con: curl -fsS https://\$DOMINIO/api/health/"
