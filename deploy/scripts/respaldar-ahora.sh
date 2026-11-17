#!/usr/bin/env bash
# Hace un respaldo inmediato (además del diario automático) y lista los que hay.
#   ./scripts/respaldar-ahora.sh
#   Para llevarte uno a tu PC:  scp usuario@servidor:/tmp/bd-....dump .   (después de ./scripts/respaldar-ahora.sh --copiar)
set -euo pipefail
cd "$(cd "$(dirname "$0")/.." && pwd)"

docker compose exec -T backup sh /backup.sh ahora
echo
echo "Respaldos guardados en el servidor:"
docker compose exec -T backup sh -c 'ls -lh /backups | tail -n +2'

if [ "${1:-}" = "--copiar" ]; then
    ultimo="$(docker compose exec -T backup sh -c 'ls -1t /backups/bd-*.dump | head -1' | tr -d '\r')"
    docker compose cp "backup:$ultimo" "/tmp/$(basename "$ultimo")"
    echo "Copiado a /tmp/$(basename "$ultimo"). Descárgalo con scp y guárdalo FUERA del servidor."
fi
