#!/usr/bin/env bash
# Resumen del estado: servicios, salud, disco, memoria y último respaldo.
set -uo pipefail
cd "$(cd "$(dirname "$0")/.." && pwd)"

echo "== Servicios =="
docker compose --profile n8n ps --format 'table {{.Service}}\t{{.Status}}' 2>/dev/null || docker compose ps
echo
echo "== Reinicios (deben ser 0: más de 0 indica un servicio que falla y se reinicia) =="
docker inspect -f '{{.Name}}  reinicios={{.RestartCount}}' $(docker compose ps -q) 2>/dev/null
echo
echo "== Salud del backend =="
docker compose exec -T backend curl -fsS http://localhost:8000/api/health/ 2>/dev/null && echo || echo "NO responde"
echo "== Uso de recursos =="
docker stats --no-stream --format 'table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}' 2>/dev/null
echo
echo "== Disco del servidor =="
df -h / | tail -n 1
docker system df 2>/dev/null | head -n 5
echo
echo "== Último respaldo =="
docker compose exec -T backup sh -c 'ls -1t /backups/bd-*.dump 2>/dev/null | head -1 | xargs -r ls -lh' 2>/dev/null || echo "(ninguno)"
