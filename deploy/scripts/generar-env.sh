#!/usr/bin/env bash
# Crea deploy/.env con contraseñas y claves ALEATORIAS (a partir de .env.production.example).
#
#   ./scripts/generar-env.sh                       pregunta lo necesario
#   DOMINIO=dubss.ejemplo.bo N8N=no ./scripts/generar-env.sh      sin preguntas (útil para automatizar)
#   ./scripts/generar-env.sh --forzar              sobrescribe un .env existente (¡se pierden las claves anteriores!)
set -euo pipefail

DIR="$(cd "$(dirname "$0")/.." && pwd)"
ENV="$DIR/.env"
EJEMPLO="$DIR/.env.production.example"

if [ -f "$ENV" ] && [ "${1:-}" != "--forzar" ]; then
    echo "Ya existe $ENV. No lo toco: cambiar las claves de una base ya creada la dejaría inaccesible."
    echo "Si de verdad quieres empezar de cero:  $0 --forzar"
    exit 1
fi
command -v openssl >/dev/null || { echo "Falta openssl (sudo apt-get install -y openssl)."; exit 1; }

aleatorio() { openssl rand -hex "$1"; }

poner() {   # poner CLAVE VALOR  -> reemplaza la línea CLAVE=... del archivo
    local archivo="$1" clave="$2" valor="$3" tmp
    tmp="$(mktemp)"
    awk -v k="$clave" -v v="$valor" 'BEGIN{FS=OFS="="} $1==k {print k "=" v; next} {print}' "$archivo" > "$tmp"
    cat "$tmp" > "$archivo"; rm -f "$tmp"
}

preguntar() {   # preguntar VARIABLE "texto" "valor por defecto"
    local var="$1" texto="$2" defecto="$3" resp
    if [ -n "${!var:-}" ]; then return; fi
    read -r -p "$texto [$defecto]: " resp || true
    printf -v "$var" '%s' "${resp:-$defecto}"
}

echo "== Configuración de producción de la DUBSS =="
preguntar DOMINIO "Dominio público (sin https://; localhost solo para probar en tu PC)" "dubss.ejemplo.bo"
if [ "$DOMINIO" = "localhost" ]; then
    ESQUEMA="${ESQUEMA:-http}"; USAR_HTTPS="${USAR_HTTPS:-false}"
else
    ESQUEMA="${ESQUEMA:-https}"; USAR_HTTPS="${USAR_HTTPS:-true}"
fi
preguntar N8N "¿Activar los avisos por WhatsApp con n8n? (si/no)" "no"

cp "$EJEMPLO" "$ENV"
poner "$ENV" DOMINIO "$DOMINIO"
poner "$ENV" ESQUEMA "$ESQUEMA"
poner "$ENV" USAR_HTTPS "$USAR_HTTPS"
poner "$ENV" ADMIN_URL "panel-$(aleatorio 4)/"
poner "$ENV" DJANGO_SECRET_KEY "$(aleatorio 50)"
poner "$ENV" POSTGRES_PASSWORD "$(aleatorio 24)"
if [ "$N8N" = "si" ] || [ "$N8N" = "sí" ]; then
    poner "$ENV" N8N_URL_EVENTOS "http://n8n:5678/webhook/dubss-eventos"
    poner "$ENV" N8N_SECRETO "$(aleatorio 32)"
    poner "$ENV" N8N_ENCRYPTION_KEY "$(aleatorio 32)"
fi
chmod 600 "$ENV"

echo
echo "Listo: $ENV (solo tú puedes leerlo)."
echo "  Dominio ........ $ESQUEMA://$DOMINIO"
echo "  Panel Django ... $ESQUEMA://$DOMINIO/$(grep '^ADMIN_URL=' "$ENV" | cut -d= -f2)"
echo
echo "Pendiente de tu parte (edita el archivo con nano):"
echo "  - EMAIL_HOST_USER y EMAIL_HOST_PASSWORD  (para enviar correos)"
echo "  - GROQ_API_KEY                            (opcional: asistente y agente de IA)"
echo "GUARDA una copia del .env en un lugar seguro (gestor de contraseñas): sin él no puedes restaurar el sistema."
