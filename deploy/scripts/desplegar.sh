#!/usr/bin/env bash
# Despliega o ACTUALIZA el sistema: baja los cambios de Git, reconstruye las imágenes y reinicia lo necesario.
#   ./scripts/desplegar.sh                 normal
#   ./scripts/desplegar.sh --sin-git       solo reconstruye (útil si ya copiaste el código)
set -euo pipefail

DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$DIR"
[ -f .env ] || { echo "Falta deploy/.env. Créalo primero:  ./scripts/generar-env.sh"; exit 1; }
grep -q 'CAMBIAME' .env && { echo "El .env todavía tiene valores «CAMBIAME». Genera uno nuevo con ./scripts/generar-env.sh"; exit 1; }

PERFIL=()
if grep -qE '^N8N_SECRETO=.+' .env; then PERFIL=(--profile n8n); fi
DC=(docker compose "${PERFIL[@]}")

if [ "${1:-}" != "--sin-git" ]; then
    echo "== Descargando la última versión =="
    git -C "$DIR/.." pull --ff-only
fi

echo "== Construyendo imágenes (la primera vez tarda varios minutos) =="
"${DC[@]}" build --pull

echo "== Iniciando servicios =="
"${DC[@]}" up -d --remove-orphans

echo "== Esperando a que el sistema esté sano =="
for servicio in backend frontend celery_worker; do
    id="$("${DC[@]}" ps -q "$servicio")"
    for _ in $(seq 1 90); do
        estado="$(docker inspect -f '{{if .State.Health}}{{.State.Health.Status}}{{else}}{{.State.Status}}{{end}}' "$id" 2>/dev/null || echo desconocido)"
        [ "$estado" = "healthy" ] && break
        sleep 5
    done
    echo "  $servicio: $estado"
    if [ "$estado" != "healthy" ]; then
        echo "  No quedó sano. Revisa:  docker compose logs --tail 80 $servicio"; exit 1
    fi
done

"${DC[@]}" ps
ESQUEMA="$(grep '^ESQUEMA=' .env | cut -d= -f2 | cut -d' ' -f1)"; DOMINIO="$(grep '^DOMINIO=' .env | cut -d= -f2 | cut -d' ' -f1)"
echo
echo "Sistema en línea: ${ESQUEMA}://${DOMINIO}"
echo "Si es la PRIMERA vez:  ./scripts/primer-inicio.sh"
