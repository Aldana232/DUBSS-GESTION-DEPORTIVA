#!/usr/bin/env bash
# Restaura la base de datos desde un respaldo (.dump). ¡REEMPLAZA los datos actuales!
#   ./scripts/restaurar.sh                      lista los respaldos disponibles
#   ./scripts/restaurar.sh bd-20261115-031500.dump
#   ./scripts/restaurar.sh /ruta/en/el/servidor/mi-respaldo.dump     (un archivo que trajiste de otro lugar)
set -euo pipefail
cd "$(cd "$(dirname "$0")/.." && pwd)"

if [ $# -eq 0 ]; then
    echo "Respaldos disponibles:"
    docker compose exec -T backup sh -c 'ls -lht /backups/bd-*.dump 2>/dev/null || echo "  (no hay ninguno todavía)"' </dev/null
    echo; echo "Uso:  $0 NOMBRE_DEL_ARCHIVO.dump"; exit 0
fi

ARCHIVO="${1:-}"
[ -n "$ARCHIVO" ] || { echo "Indica el nombre del respaldo."; exit 1; }
if [ -f "$ARCHIVO" ]; then          # archivo local: se copia al volumen de respaldos
    docker compose cp "$ARCHIVO" "backup:/backups/$(basename "$ARCHIVO")"
    ARCHIVO="$(basename "$ARCHIVO")"
fi
case "$ARCHIVO" in *.dump) ;; *) echo "Debe ser un archivo .dump (los respaldos de la base de datos)."; exit 1;; esac
docker compose exec -T backup sh -c "test -f /backups/$ARCHIVO && test -s /backups/$ARCHIVO" </dev/null || { echo "No encuentro /backups/$ARCHIVO. Mira cuáles hay con:  $0"; exit 1; }

echo "Se va a REEMPLAZAR toda la base de datos actual por: $ARCHIVO"
read -r -p "Escribe RESTAURAR para continuar: " confirmacion
[ "$confirmacion" = "RESTAURAR" ] || { echo "Cancelado."; exit 1; }

echo "== Deteniendo la aplicación =="
docker compose stop caddy frontend celery_worker celery_beat backend
echo "== Restaurando =="
docker compose exec -T backup sh -c "pg_restore -h db -U \$POSTGRES_USER -d \$POSTGRES_DB --clean --if-exists --no-owner --exit-on-error /backups/$ARCHIVO" </dev/null
echo "== Iniciando de nuevo =="
docker compose up -d
echo "Restauración terminada. Comprueba el sistema con ./scripts/estado.sh"
