# Instrucciones para Copilot — Proyecto DUBSS

Sistema de gestión deportiva de la DUBSS (UAGRM). Backend: Django 5 + DRF + PostgreSQL. Frontend: Next.js 14 (App Router) + TypeScript + Tailwind + React Query.

El plan de trabajo está en `docs/PLAN_FASES_DUBSS.md`. La documentación oficial está en `docs/Sistema_deportivo_para_la_DUBSS.docx`: **si el código y el documento difieren, manda el documento**.

## Fuentes de verdad (en este orden)
1. `docs/CAP7_DDL_DOCUMENTO.sql`: esquema de datos oficial del documento. Si el código difiere, manda este esquema, salvo las "ampliaciones" listadas en `docs/ANEXO_PLAN_FASES.md`.
2. `docs/ANEXO_PLAN_FASES.md`: cambios acordados y estado de las tareas. Manda sobre `docs/PLAN_FASES_DUBSS.md`.
3. `docs/PLAN_FASES_DUBSS.md`: plan general por fases.
La Fase 0 (seguridad) está CERRADA: no la rehagas ni cambies sus decisiones.

## Reglas generales
- Ejecutar **solo la tarea que se pide** (por ID, por ejemplo `F0-02`). No adelantar otras tareas.
- Cada tarea incluye **migraciones y tests**. Antes de terminar: `python manage.py makemigrations --check`, tests del backend, y en el frontend `npm run lint && npm run build`.
- Nombres de modelos y campos **en español**, como el código existente.
- Antes de editar, lee el código real. Si una instrucción choca con la realidad, **detente y repórtalo** en vez de improvisar.
- Nunca modifiques migraciones ya existentes; solo crea migraciones nuevas. Si una migración cambia datos, muestra antes cuántas filas afecta.
- Todo mensaje al usuario va en español, incluidos los de DRF.
- No subir `.env` ni secretos.

## Decisiones fijas (no cambiar)
- Roles con login: `SUPERADMIN`, `ADMIN_DUBSS`, `ORGANIZADOR`, `DELEGADO`. Se eliminan `ARBITRO`, `COORDINADOR`, `DEPORTISTA`, `PUBLICO`. `JUGADOR` queda como valor reservado sin permisos (cuentas antiguas y futuro panel).
- El jugador es **solo una ficha** (sin cuenta). El espectador es un visitante anónimo.
- El registro público está cerrado: las cuentas las crea el administrador.
- Un equipo se reutiliza entre campeonatos; la participación es `Inscripcion`.
- El fixture se genera con un optimizador (OR-Tools); Random Forest puntúa la calidad de las asignaciones y predice resultados.
- Monolito modular Django; no microservicios.

## Backend
- Los roles se consultan **solo con helpers** de `apps/users/roles.py`, nunca con strings sueltos.
- `rol`, `facultad`, `is_staff` e `is_superuser` **nunca** son escribibles en serializers de uso propio (registro, perfil).
- Toda vista de escritura declara `permission_classes` explícitos.
- Validaciones de negocio en serializers/servicios (DRF no llama a `Model.clean()`) y, si se puede, también como constraints de base de datos.
- Lógica de negocio en `services/`; las vistas solo orquestan.
- Ningún `GET` escribe en la base de datos.
- Fechas siempre con zona horaria (`timezone.make_aware`).
- Toda acción crítica se registra en la bitácora (`auditoria.registrar`).

## Frontend
- Prohibido agregar `style={{ ... }}` y `alert()`. Usar componentes de `components/ui/` y toasts.
- Las llamadas a la API pasan por `lib/api/services.ts` y hooks de React Query; nunca `fetch`/`axios` suelto en una página.
- Formularios con `react-hook-form` + `zod`.
- La URL de la API sale de `NEXT_PUBLIC_API_URL`; nunca escribir `http://localhost:8000`.
- Ocultar menús o rutas por rol es solo experiencia de usuario: la seguridad real la hace la API.

## Un requisito está "terminado" solo si tiene
Modelo y migración, API con validaciones, permisos por rol con test, pantalla para los roles que lo usan, registro en bitácora y tests en verde.
