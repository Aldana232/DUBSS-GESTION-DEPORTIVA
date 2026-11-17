# DUBSS — Sistema Inteligente de Gestión Deportiva

Plataforma web para organizar los campeonatos deportivos de la **Dirección Universitaria de Bienestar Social y Salud (DUBSS)** de la **UAGRM**: inscripciones, fixture automático con optimización, resultados, tabla de posiciones, predicciones, planilla móvil sin conexión, avisos por correo, push y WhatsApp.

> Proyecto de la materia Taller de Grado (INF511), FICCT — UAGRM.
> Este repositorio contiene **solo el sistema** (lo que se despliega). La documentación y la app Android están en el repositorio `DUBSS-DOCS-MOVIL`.

## Qué incluye

| Módulo | Descripción |
|---|---|
| Campeonatos y fixture | Máquina de estados, optimizador (OR-Tools) sin choques de cancha/equipo, restricciones por clases y clima |
| Resultados | Tabla con desempates, sanciones, historial por jornada, W.O. |
| Inteligencia artificial | Predicción (Random Forest + Elo), niveles de equipos (K-means), resultados atípicos (Isolation Forest) |
| Asistente y agente | Consultas por texto o voz y un agente (Groq) que propone acciones que siempre requieren confirmación |
| Planilla móvil (PWA) | Instalable, funciona sin conexión y sincroniza sin duplicados |
| Notificaciones | Campana dentro de la app, correo, push (Firebase) y WhatsApp (n8n) |
| Legal | Términos, privacidad y cookies con aceptación registrada |

## Estructura

```
backend/     Django 5 + DRF + Celery (apps por dominio en backend/apps/)
frontend/    Next.js 14 + React 18 + TypeScript + Tailwind
n8n/         Flujos de n8n (avisos y consultas por WhatsApp)
deploy/      Despliegue a producción (ver deploy/README.md)
.github/     Integración continua
```

## Desarrollo local

Requisitos: Docker Desktop.

```bash
cp .env.example .env                                   # (Windows: copy .env.example .env)
docker compose -f docker-compose.dev.yml up -d --build
docker compose -f docker-compose.dev.yml exec backend python manage.py migrate
docker compose -f docker-compose.dev.yml exec backend python manage.py seed_realista   # datos de ejemplo de la UAGRM
```

| Servicio | URL |
|---|---|
| Aplicación | http://localhost:3000 |
| API | http://localhost:8000/api/v1/ |
| Documentación de la API | http://localhost:8000/api/docs/ |

Cuentas de ejemplo (contraseña `Dubss2026!`): `superadmin@uagrm.edu.bo`, `admin@uagrm.edu.bo`, `organizador@uagrm.edu.bo`, `delegado.ficct@uagrm.edu.bo`, `jugador@uagrm.edu.bo`.

**Modo rápido** (versión de producción del frontend, mucho más ágil en Windows):
`docker compose -f docker-compose.dev.yml -f docker-compose.rapido.yml up -d`

**n8n + WhatsApp (opcional):** descomenta las variables de `.env.example` y levanta `--profile n8n`.

## Pruebas

```bash
docker compose -f docker-compose.dev.yml exec backend python -m pytest --cov=apps -q     # backend
cd frontend && npm run lint && npx tsc --noEmit && npm run build                          # frontend
```

## Despliegue

Ver `deploy/README.md`.

## Equipo

Aldana Claure Brayan · Sandoval Martínez Erick Noel
