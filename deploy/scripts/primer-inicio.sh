#!/usr/bin/env bash
# Primer inicio de una instalación NUEVA: catálogos base (12 facultades, deportes, categorías) y el primer
# superadministrador. NO carga datos de ejemplo (equipos, partidos, usuarios de prueba): el sistema arranca vacío.
#   ./scripts/primer-inicio.sh
#   ADMIN_EMAIL=ana@uagrm.edu.bo ADMIN_NOMBRE=Ana ADMIN_APELLIDO=Pérez DUBSS_ADMIN_PASSWORD='...' ./scripts/primer-inicio.sh   (sin preguntas)
set -euo pipefail

DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$DIR"
DC=(docker compose)
manage() { "${DC[@]}" exec "$@"; }

echo "== 1/2 Catálogos base =="
"${DC[@]}" exec -T backend python manage.py cargar_catalogos

echo
echo "== 2/2 Primer superadministrador =="
if [ -z "${ADMIN_EMAIL:-}" ]; then
    read -r -p "Correo del administrador: " ADMIN_EMAIL
    read -r -p "Nombre: " ADMIN_NOMBRE
    read -r -p "Apellido: " ADMIN_APELLIDO
fi
ARGS=(--email "$ADMIN_EMAIL" --nombre "${ADMIN_NOMBRE:?falta el nombre}" --apellido "${ADMIN_APELLIDO:?falta el apellido}")
if [ -n "${DUBSS_ADMIN_PASSWORD:-}" ]; then
    "${DC[@]}" exec -T -e DUBSS_ADMIN_PASSWORD="$DUBSS_ADMIN_PASSWORD" backend python manage.py crear_superadmin "${ARGS[@]}"
else
    "${DC[@]}" exec backend python manage.py crear_superadmin "${ARGS[@]}"      # pide la contraseña por teclado
fi

ESQUEMA="$(grep '^ESQUEMA=' .env | cut -d= -f2 | cut -d' ' -f1)"; DOMINIO="$(grep '^DOMINIO=' .env | cut -d= -f2 | cut -d' ' -f1)"
echo
echo "Listo. Entra en ${ESQUEMA}://${DOMINIO}/login con ese correo."
echo "Tu primer paso: crea las instalaciones y canchas (Catálogos) y las cuentas de organizadores y delegados (Usuarios)."
