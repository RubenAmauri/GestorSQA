#!/usr/bin/env bash
# Crea (o actualiza) las etiquetas que usan las plantillas de issues y el SQAP.
# Requiere GitHub CLI con sesión iniciada: gh auth login
# Uso: ./scripts/sqa/crear-etiquetas.sh
set -euo pipefail

etiqueta() { gh label create "$1" --color "$2" --description "$3" --force; }

etiqueta "tarea"                    "1d76db" "Trabajo para implementar o documentar un requisito"
etiqueta "defecto"                  "d73a4a" "Defecto del producto (SQAP 6.7)"
etiqueta "no-conformidad"           "b60205" "Incumplimiento del SQAP (SQAP 6.7)"
etiqueta "severidad:alta"           "b60205" "SQAP 6.7.1"
etiqueta "severidad:media"          "fbca04" "SQAP 6.7.1"
etiqueta "severidad:baja"           "c5def5" "SQAP 6.7.1"
etiqueta "detectado:revision"       "5319e7" "Detectado en revisión"
etiqueta "detectado:ci"             "5319e7" "Detectado por la CI"
etiqueta "detectado:prueba-manual"  "5319e7" "Detectado en prueba manual"
etiqueta "detectado:auditoria"      "5319e7" "Detectado en auditoría"
etiqueta "detectado:post-entrega"   "5319e7" "Detectado después de un punto de control"
etiqueta "documentacion"            "0e8a16" "Cambios a SRS, SDS, SQAP u otros documentos"

echo "Etiquetas listas."
