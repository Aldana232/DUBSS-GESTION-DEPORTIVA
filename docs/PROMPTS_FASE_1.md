# Fase 1 — Guía paso a paso y prompts listos

Todo en **PowerShell**, dentro de la carpeta del proyecto (`DUBSS-GESTION-DEPORTIVA`).

---

## PARTE A — Preparación (una sola vez, ~10 minutos, la haces tú)

### A1. Arreglar el nombre repetido (rama y etiqueta se llaman igual)

```powershell
git switch -c fase-1-datos-y-roles
git branch -d fase-0-cerrada
git log --oneline -3 --decorate
```

Resultado esperado: la última línea muestra `Fase 0 cerrada` con la etiqueta `tag: fase-0-cerrada`, y estás en la rama `fase-1-datos-y-roles`. La etiqueta queda como punto de retorno.

### A2. Respaldar la base de desarrollo (OBLIGATORIO antes de F1-01a)

La Fase 1 cambia los roles de los usuarios que ya existen. **No uses `>` de PowerShell para el volcado**: en Windows PowerShell guarda el archivo en UTF-16 y queda inservible. Usa este método:

```powershell
docker compose -f docker-compose.dev.yml up -d
docker compose -f docker-compose.dev.yml exec db sh -c 'pg_dump -U "$POSTGRES_USER" "$POSTGRES_DB" > /tmp/respaldo_pre_fase1.sql'
docker cp dubss_db_dev:/tmp/respaldo_pre_fase1.sql ..\respaldo_pre_fase1.sql
Get-Item ..\respaldo_pre_fase1.sql | Select-Object Name, Length
```

Guarda el archivo **fuera** del repositorio (la línea `..\` lo deja en la carpeta de arriba) para no subirlo por accidente: contiene datos reales. Debe pesar más de unos pocos KB.

### A3. Verificar que los archivos están en su lugar

```powershell
Get-ChildItem docs, .github
```

Debes ver: `docs\PLAN_FASES_DUBSS.md`, `docs\ANEXO_PLAN_FASES.md`, `docs\CAP7_DDL_DOCUMENTO.sql` y `.github\copilot-instructions.md`.
**Importante:** usa las versiones más recientes (descárgalas otra vez si dudas). El anexo correcto contiene la frase **"FASE 0 CERRADA"** y el `copilot-instructions.md` correcto menciona `CAP7_DDL_DOCUMENTO.sql`. Comprueba:

```powershell
Select-String -Path docs\ANEXO_PLAN_FASES.md -Pattern "FASE 0 CERRADA"
Select-String -Path .github\copilot-instructions.md -Pattern "CAP7_DDL"
```

Luego guarda esto como commit propio (local, sin push): `git add -A` y `git commit -m "Docs de la Fase 1"`.

---

## PARTE B — Cómo trabajar con Copilot en cada tarea

1. Abre **Copilot Chat** en VS Code (`Ctrl+Alt+I`).
2. Arriba del cuadro de chat, cambia el modo a **Agent** (no "Ask" ni "Edit"): solo el modo Agente puede ejecutar comandos y correr tests.
3. Pulsa **New Chat** (ícono `+`). **Un chat nuevo por tarea**: si arrastras la conversación anterior, Copilot se confunde.
4. Adjunta contexto: escribe `#file:` y elige, o usa el clip, estos archivos:
   `docs/PLAN_FASES_DUBSS.md`, `docs/ANEXO_PLAN_FASES.md` y `docs/CAP7_DDL_DOCUMENTO.sql`.
5. Pega el prompt de la tarea (más abajo) y envíalo.
6. Cuando Copilot pida permiso para ejecutar un comando, **léelo antes de aceptar**. Rechaza cualquiera que contenga `git commit`, `git push`, `git add`, `drop`, `reset` o `rm`/`Remove-Item` de datos.
7. Al terminar, revisa en el panel **Source Control** (`Ctrl+Shift+G`) qué archivos cambió y haz clic en cada uno para ver el diff. Comprueba que no tocó archivos que la tarea no necesitaba.
8. Si todo está bien: `git add -A` y `git commit -m "F1-01a roles backend"` (tú, local). Así cada tarea queda separada y puedes volver atrás.

**Si algo sale mal en una tarea:** descarta lo que hizo con `git restore .` y `git clean -fd` (esto vuelve al último commit; no toca tu base de datos). Si además migró la base de desarrollo, restaura el respaldo de A2 (avísame y te doy el comando).

**Qué me mandas para revisión** (solo en las tareas marcadas ⚠️): el **reporte final** de Copilot, completo.

---

## PARTE C — Orden de la Fase 1

| # | Tarea | Prompt | Revisión |
|---|---|---|---|
| 1 | **F1-01a** Roles finales (backend) | C1 | ⚠️ obligatoria |
| 2 | **F1-01b** Roles en el frontend | C2 | normal |
| 3 | F1-02 Facultad | Plantilla C3 | ⚠️ |
| 4 | F1-07 Deporte y Categoría | Plantilla C3 | normal |
| 5 | F1-03 Equipo reutilizable | Plantilla C3 | ⚠️ |
| 6 | F1-04 Inscripción | Plantilla C3 | ⚠️ |
| 7 | F1-05 Ficha de jugador | Plantilla C3 | ⚠️ |
| 8 | F1-06 Campeonato | Plantilla C3 | ⚠️ |
| 9 | F1-08 Instalaciones y horarios | Plantilla C3 | normal |
| 10 | F1-09 Restricciones de participación | Plantilla C3 | normal |
| 11 | F1-10 Quejas | Plantilla C3 | normal |
| 12 | F1-11 Partido: constraints | Plantilla C3 | ⚠️ |
| 13 | F1-13 Marcador vs. incidencias | Plantilla C3 | normal |
| 14 | F1-14 Bitácora alineada al documento | Plantilla C3 | normal |
| 15 | F1-12 `seed_demo` | Plantilla C3 | normal |

---

## PARTE D — Prompts

### C1 — F1-01a: roles finales (backend)

```
Lee docs/PLAN_FASES_DUBSS.md, docs/ANEXO_PLAN_FASES.md (secciones 2, 3 y 6), docs/CAP7_DDL_DOCUMENTO.sql y .github/copilot-instructions.md.
Ejecuta SOLO la tarea F1-01a: roles finales en el backend (la parte de frontend es F1-01b, NO la hagas).

REGLAS: NO ejecutes git commit/push/add. No borres la base de datos. Se permite una migración NUEVA de esquema y una de datos
en apps/users/migrations; no modifiques migraciones existentes. No toques el frontend. Mensajes al usuario en español.

ANTES DE EDITAR
1. Muéstrame cuántos usuarios hay por cada valor de rol en la base de desarrollo (y cuántos son is_superuser).
2. Lista dónde se usan hoy EsAdminDUBSS, EsCoordinadorOAdmin, EsArbitroOAdmin y EsDeportistaPropioOAdmin (archivo, vista y qué hace la vista).

QUÉ HACER
1. Modelo (apps/users/models.py): Usuario.Rol pasa a SUPERADMIN, ADMIN_DUBSS, ORGANIZADOR, DELEGADO y JUGADOR.
   JUGADOR es un valor RESERVADO sin ningún permiso (documéntalo en un comentario: aloja cuentas antiguas y el futuro panel F7-10).
   El rol por defecto del modelo pasa a DELEGADO. create_superuser asigna SUPERADMIN. Elimina las propiedades es_coordinador y es_arbitro
   y deja es_admin, es_organizador, es_delegado (delegando en roles.py).
2. Helpers (apps/users/roles.py): es_superadmin (rol SUPERADMIN o is_superuser), es_admin (rol ADMIN_DUBSS o SUPERADMIN, o is_superuser),
   es_organizador (rol ORGANIZADOR), es_delegado (rol DELEGADO). Elimina es_arbitro. Todos devuelven False con None/anónimo.
3. Permisos (apps/users/permissions.py): crea EsSuperadmin, EsAdmin, EsAdminUOrganizador y EsAdminOrganizadorODelegado
   (esta última es TEMPORAL: en la fase F2 se limitará por facultad; añade un comentario TODO F2). Reemplaza TODOS los usos así:
   - EsAdminDUBSS -> EsAdmin.
   - EsCoordinadorOAdmin -> EsAdminUOrganizador en vistas de competición (campeonatos, partidos, fixture, cambio de estado, notificaciones);
     -> EsAdminOrganizadorODelegado en vistas de equipos y fichas de jugador (dominio del delegado). Si dudas de una vista, no adivines: dímelo.
   - EsArbitroOAdmin (registrar resultado e incidencia) -> EsAdminUOrganizador (el documento asigna RF12/RF14 al Organizador).
   - EsDeportistaPropioOAdmin: elimínala junto con sus tests (no se usa).
   Elimina las clases viejas. No cambies EsLecturaPublica.
4. Reglas de seguridad en los serializers de administración (UsuarioAdminCreateSerializer y UsuarioAdminSerializer):
   solo un usuario que cumpla es_superadmin puede asignar el rol SUPERADMIN, y solo un superadmin puede editar o dar de baja una cuenta
   cuyo rol sea SUPERADMIN. Un ADMIN_DUBSS que lo intente recibe 403 con un mensaje claro. Mantén las reglas existentes
   (un admin no cambia su propio rol ni se da de baja).
5. Migraciones: (a) la de esquema que genere Django (choices y default) y (b) una de DATOS con RunPython, en este orden de mapeo:
   is_superuser=True -> SUPERADMIN; COORDINADOR -> DELEGADO; ARBITRO -> ORGANIZADOR; DEPORTISTA y PUBLICO -> JUGADOR con is_active=False;
   ADMIN_DUBSS queda igual. La migración imprime cuántas filas cambió por cada mapeo. Reversa: función inversa de mejor esfuerzo o noop documentado.
6. Otros usos del rol: revisa apps/notificaciones (filtro por rol de destinatarios), apps/ml/views.py (usa el rol en un prompt),
   apps/auditoria y apps/users/admin.py; ajusta los valores nuevos. No cambies su lógica.
7. Tests: actualiza todos los tests que usen COORDINADOR, ARBITRO, DEPORTISTA o PUBLICO (test_auth, test_roles, test_login_*, test_auditoria_*,
   test_eventos_nucleo, etc.). Agrega: helpers y permisos con los 4 roles + JUGADOR + superusuario + anónimo; ADMIN_DUBSS no puede crear un SUPERADMIN (403);
   SUPERADMIN sí puede; ADMIN_DUBSS no puede editar ni dar de baja a un SUPERADMIN; el rol JUGADOR no accede a ningún endpoint de escritura;
   y un test de la migración de datos (crea usuarios con los roles viejos, ejecuta el mapeo y verifica el resultado).

VERIFICACIÓN
- pytest -q (suite completa), pyflakes de las apps tocadas, makemigrations --check, git status --short.
- grep -rn -E "COORDINADOR|ARBITRO|DEPORTISTA|PUBLICO" backend --include=*.py  (solo deben quedar en migraciones antiguas y en la migración de datos nueva).
- grep de los mismos valores en frontend/app y frontend/lib: SOLO repórtalos, no los cambies.

REPORTE FINAL
1) Conteo de usuarios por rol antes de migrar y cuántas filas cambió cada mapeo. 2) Dónde se usaban las 4 clases de permiso y cómo quedó cada una.
3) Archivos modificados/creados (1 línea cada uno) y nombres de las migraciones. 4) Tests nuevos. 5) Resultados de pytest, pyflakes, makemigrations --check,
git status y los greps. 6) Cualquier vista donde dudaste el permiso, y cualquier cosa fuera de lo pedido.
```

### C2 — F1-01b: roles en el frontend

```
Lee docs/ANEXO_PLAN_FASES.md (secciones 2, 3 y 6) y .github/copilot-instructions.md.
Ejecuta SOLO la tarea F1-01b: adaptar el frontend a los roles nuevos del backend (SUPERADMIN, ADMIN_DUBSS, ORGANIZADOR, DELEGADO, JUGADOR).
No es un rediseño: es el cambio mínimo para que nada se rompa.

REGLAS: NO ejecutes git commit/push/add. No toques el backend. No agregues páginas ni cambies el diseño.
Mensajes en español. Para el build, detén primero el contenedor del frontend (docker compose -f docker-compose.dev.yml stop frontend)
porque comparte la carpeta .next con "next dev"; al terminar, vuélvelo a levantar.

QUÉ HACER
1. Busca en frontend/app y frontend/lib todos los usos de ADMIN_DUBSS, COORDINADOR, ARBITRO, DEPORTISTA, PUBLICO, esAdmin, esCoord y .rol. Lístalos antes de editar.
2. Actualiza el tipo de Usuario (rol) a la unión de los 5 valores nuevos.
3. En lib/hooks/useAuth.ts define: esSuperadmin (SUPERADMIN), esAdmin (ADMIN_DUBSS o SUPERADMIN), esOrganizador (ORGANIZADOR),
   esDelegado (DELEGADO) y esGestion = esAdmin || esOrganizador. Elimina esCoord y esArbitro (si existen).
4. Reemplaza los usos: lo que antes era "esAdmin o esCoord" para campeonatos, fixture, estados y partidos pasa a esGestion.
   El formulario de resultado del partido (puedeRegistrar) pasa a esGestion (coincide con el backend: Admin y Organizador).
5. No cambies la navegación ni el diseño. Solo corrige referencias.

VERIFICACIÓN
- npm run lint y npm run build (sin errores nuevos).
- Prueba manual: inicia sesión como administrador y como organizador y confirma que ven los botones "Generar fixture", cambiar estado y el formulario de resultado.
  Un usuario DELEGADO no debe verlos.

REPORTE FINAL
1) Lista de usos encontrados y cómo quedó cada uno. 2) Archivos modificados (1 línea cada uno). 3) Resultado de lint y build.
4) Qué probaste manualmente. 5) Cualquier cosa fuera de lo pedido o cualquier duda.
```

### C3 — Plantilla para el resto de la Fase 1 (cambia solo `<ID>`)

Úsala para F1-02, F1-07, F1-03, F1-04, F1-05, F1-06, F1-08, F1-09, F1-10, F1-11, F1-13, F1-14 y F1-12.

```
Lee docs/PLAN_FASES_DUBSS.md, docs/ANEXO_PLAN_FASES.md (sección 6 manda sobre el plan), docs/CAP7_DDL_DOCUMENTO.sql y .github/copilot-instructions.md.
Ejecuta SOLO la tarea <ID> de la Fase 1.

REGLAS (obligatorias)
- NO ejecutes git commit, git push ni git add. Deja los cambios sin commitear.
- No borres la base de datos ni datos. Las migraciones NUEVAS están permitidas; nunca modifiques migraciones existentes.
- No toques archivos que la tarea no necesite. Todo mensaje al usuario va en español.
- El esquema oficial es docs/CAP7_DDL_DOCUMENTO.sql: compara cada campo, tipo, nulabilidad y restricción única del modelo afectado con la tabla
  correspondiente. Si difieren, sigue el esquema, EXCEPTO las "ampliaciones" que indica la sección 6 del anexo. Lista las diferencias antes de editar.

MÉTODO
1. ANTES de editar, lee el código real relacionado y muéstrame: (a) qué hay hoy, (b) las diferencias con el esquema del documento, (c) cuántas filas
   de datos afectaría una migración (si hay datos en la base de desarrollo).
2. Si una instrucción choca con la realidad o con otra regla, DETENTE y explícalo en vez de improvisar.
3. Implementa: modelo, migración (con migración de datos si hace falta, mostrando conteos), serializers, vistas/permisos afectados, y TESTS nuevos
   para cada comportamiento (casos felices, de error y de permisos).
4. Actualiza tests y código existentes que dependan de lo cambiado.
5. Ejecuta: pytest -q (SUITE COMPLETA), python -m pyflakes <apps tocadas>, python manage.py makemigrations --check, git status --short.
6. No marques la tarea como terminada si falla algún test.

REPORTE FINAL (exactamente este formato)
1) Diferencias encontradas entre el código y el esquema del documento, y cómo quedaron. 2) Archivos creados/modificados (1 línea cada uno); migraciones.
3) Tests nuevos. 4) Resultado de pytest (suite completa), pyflakes, makemigrations --check y git status --short.
5) Datos afectados por migraciones (conteos). 6) Discrepancias con el plan y cualquier cosa fuera de lo pedido o duda.
```

Tras cada tarea: revisa el diff en Source Control, haz tu commit local (`git add -A` y `git commit -m "<ID> ..."`) y pasa a la siguiente.
