#!/bin/sh
# Punto de entrada del backend.
#  1) Arranca como root SOLO para dejar los volúmenes montados con dueño «dubss». Un volumen nuevo lo inicializa
#     el primer contenedor que lo monta (a veces uno de root, como el de respaldo) y, sin esto, Django no podría
#     guardar fotos ni los modelos de IA.
#  2) Baja a «dubss» y vuelve a ejecutar este mismo script.
#  3) Solo el servicio web (RUN_MIGRATIONS=1) migra la base y reúne los estáticos; Celery arranca después, con el
#     web ya sano, para no competir por migrar.
set -e

if [ "$(id -u)" = "0" ]; then
    for d in /app/mediafiles /app/staticfiles /app/apps/ml/models_trained; do
        if [ -d "$d" ] && [ "$(stat -c %U "$d")" != "dubss" ]; then
            chown -R dubss:dubss "$d"
        fi
    done
    exec gosu dubss "$0" "$@"
fi

if [ "${RUN_MIGRATIONS:-0}" = "1" ]; then
    echo "[entrada] Aplicando migraciones..."
    python manage.py migrate --noinput
    echo "[entrada] Reuniendo archivos estáticos..."
    python manage.py collectstatic --noinput --clear >/dev/null
fi

exec "$@"
