#!/bin/sh
# Respaldo de la base de datos (pg_dump) y de las subidas (fotos/logos), todos los días a HORA_RESPALDO.
#   Corre dentro del contenedor «backup» (postgres:16-alpine). Los archivos quedan en el volumen «backups_data»:
#     bd-AAAAMMDD-HHMMSS.dump        (restaurable con deploy/scripts/restaurar.sh)
#     media-AAAAMMDD-HHMMSS.tar.gz
#   Se borran los de más de RETENCION_DIAS días. Para un respaldo inmediato: ver deploy/scripts/respaldar-ahora.sh
set -eu

DESTINO=/backups
RETENCION_DIAS="${RETENCION_DIAS:-14}"
HORA="${HORA_RESPALDO:-03:15}"

respaldar() {
    fecha=$(date +%Y%m%d-%H%M%S)
    echo "[respaldo] $(date '+%F %T') iniciando..."
    # Se escribe con extensión temporal y se renombra al final: un respaldo a medias nunca parece válido.
    if pg_dump -h db -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc -f "$DESTINO/bd-$fecha.dump.tmp"; then
        mv "$DESTINO/bd-$fecha.dump.tmp" "$DESTINO/bd-$fecha.dump"
        echo "[respaldo] base de datos: bd-$fecha.dump ($(du -h "$DESTINO/bd-$fecha.dump" | cut -f1))"
    else
        rm -f "$DESTINO/bd-$fecha.dump.tmp"
        echo "[respaldo] ERROR: falló pg_dump" >&2
        return 1
    fi
    if [ -d /media ] && tar -czf "$DESTINO/media-$fecha.tar.gz.tmp" -C /media . 2>/dev/null; then
        mv "$DESTINO/media-$fecha.tar.gz.tmp" "$DESTINO/media-$fecha.tar.gz"
        echo "[respaldo] subidas: media-$fecha.tar.gz"
    else
        rm -f "$DESTINO/media-$fecha.tar.gz.tmp"
    fi
    find "$DESTINO" -type f \( -name 'bd-*.dump' -o -name 'media-*.tar.gz' \) -mtime +"$RETENCION_DIAS" -delete
    echo "[respaldo] listo. Respaldos guardados: $(ls "$DESTINO"/bd-*.dump 2>/dev/null | wc -l)"
}

# Uso manual: backup.sh ahora
if [ "${1:-}" = "ahora" ]; then
    respaldar
    exit $?
fi

echo "[respaldo] servicio activo: cada día a las $HORA (hora de Bolivia), se conservan $RETENCION_DIAS días."
ultimo_dia=""
while true; do
    hoy=$(date +%F)
    if [ "$(date +%H:%M)" = "$HORA" ] && [ "$hoy" != "$ultimo_dia" ]; then
        respaldar || true
        ultimo_dia="$hoy"
    fi
    sleep 30
done
