# Anexo al plan de fases — cambios acordados durante la ejecución

> Este anexo **manda sobre `PLAN_FASES_DUBSS.md`** cuando hay diferencias. Actualízalo al terminar cada tarea (marca ✅ y anota lo que cambió).

## 1. Estado de la Fase 0

| Tarea | Estado | Notas |
|---|---|---|
| F0-01 Helpers de rol | ✅ | `apps/users/roles.py`; `permissions.py` y `Usuario.es_*` delegan en él |
| F0-02 Cerrar registro público | ✅ | `UsuarioAdminCreateSerializer`; `RegistroView` solo `EsAdminDUBSS`; sin tokens en la respuesta |
| F0-03 Cerrar escalada por perfil | ✅ | `rol`, `facultad`, `is_active` solo lectura en el perfil; `UsuarioAdminSerializer` para el admin; admin no puede cambiar su rol ni darse de baja |
| Limpieza | ✅ | `chardet==5.2.0` fijado; `backend/conftest.py` (hash MD5 solo en tests, limpieza de caché) |
| F0-04 Bloqueo por cuenta | ✅ | Campos `intentos_fallidos` y `bloqueado_hasta`; `LOGIN_MAX_INTENTOS=5`, `LOGIN_BLOQUEO_MINUTOS=15`; 429 al quinto fallo |
| F0-04b Límite por IP | ✅ | `LoginRateThrottle` (`LOGIN_THROTTLE_RATE`, default 10/min), `NUM_PROXIES` |
| F0-05a App `auditoria` | ✅ | Modelo, `registrar()`, `GET /api/v1/auditoria/bitacora/`; `ml.Bitacora` eliminado |
| F0-05b Eventos de usuarios y sesión | ✅ | Login, login fallido, bloqueo, logout, cambio de contraseña y alta/edición/cambio de rol/baja registran en bitácora; 429 en español ("Disponible en N segundos") |
| F0-05c Eventos del núcleo y 403 | ✅ | `config/exception_handler.py` registra `ACCESO_DENEGADO` (solo 403 autenticado); estado de campeonato, fixture, resultado, incidencia, reportes y ML conectados |
| F0-06 Invalidar tokens al cambiar contraseña | ✅ | Refresh anteriores en lista negra; se devuelven tokens nuevos. Verificado por HTTP |
| F0-07 Argon2 | ✅ | Hash nuevo `argon2$`; los hashes PBKDF2 antiguos se actualizan al iniciar sesión |
| F0-08 Predictor | ✅ | `models.Q` corregido; `entrenar()` probado con partidos de prueba (la rehecha completa es F6-01) |
| F0-09 Refresh rotado en el frontend | ✅ | *Single-flight*: 3 respuestas 401 simultáneas → 1 sola petición de refresh; el login muestra el 429 real |
| F0-10 Configuración | ✅ (parcial → F8) | `production.py` con `DEBUG=False`, CORS y cookies seguras; `.env.example` documentado. **Pasa a F8-05:** `SECRET_KEY` fuerte (≥ 50 caracteres) en el `.env` de producción, `NUM_PROXIES=1`, revisar las 20 advertencias de `check --deploy` y `python-json-logger` ya agregado |

**FASE 0 CERRADA** (verificada con prueba HTTP real: registro anónimo 401, perfil sin escalada, bloqueo 429, tokens invalidados, bitácora sin secretos, Argon2, single-flight; 154 tests en verde).

**Decisiones que quedaron de la verificación**
- Un email inexistente **no** se bloquea por cuenta (así no se revela qué correos existen); lo limita el control por IP (10/min).
- Aviso cosmético pendiente: `npx update-browserslist-db@latest` y quitar `version:` del Compose.
- No ejecutar `npm run build` con el servidor `next dev` encendido (comparten la carpeta `.next`).

## 2. Cambios respecto al plan original

1. **F0-04 se dividió** en F0-04 (bloqueo por cuenta, en base de datos) y F0-04b (límite por IP, en caché).
2. **F0-05 se divide en 05a, 05b y 05c.** Nombres reales: app `apps.auditoria`; modelo `Bitacora` con `usuario`, `usuario_email`, `accion`, `entidad`, `entidad_id`, `descripcion`, `detalle` (JSON), `resultado` (OK/DENEGADO/ERROR), `ip_address`, `fecha`.
   Función: `registrar(accion, *, request=None, usuario=None, email="", entidad="", entidad_id=None, descripcion="", detalle=None, resultado="OK")`. Nunca lanza excepción y sanea claves con `password/token/refresh/access/secret`.
3. **Mensajes en español (RNF09).** Los 429 salen con el sufijo en inglés de DRF ("Expected available in 53 seconds."). Corregir en F0-05b: crear `ThrottledES(Throttled)` con `extra_detail_singular = "Disponible en {wait} segundo."` y `extra_detail_plural = "Disponible en {wait} segundos."`, y usarla en `LoginView.throttled` y en el bloqueo por cuenta del serializer.
4. **Tests con hash rápido.** `conftest.py` fuerza MD5 solo en tests. El test de F0-07 (Argon2) debe sobrescribir `PASSWORD_HASHERS` dentro del propio test con la fixture `settings`.
5. **Tests `_01` / `_02` de `test_login_throttle.py`** dependen del orden de ejecución: no agregar plugins que mezclen el orden de los tests.
6. **Despliegue (F8):** ejecutar `migrate` (columnas nuevas de `Usuario`, app `auditoria`, eliminación de `ml.Bitacora`); en el `.env` de producción poner `NUM_PROXIES=1` detrás de nginx.
7. **Hallazgos previos de pyflakes en `apps/ml`** (imports sin uso y `models` indefinido en `services/predictor.py`): se resuelven en F0-08.
8. **Cosmético:** quitar `version:` de los `docker-compose*.yml` (aviso de obsoleto).

## 3. Tareas pendientes de la Fase 0 (refinadas)

**F0-05b — Eventos de usuarios y sesión.** Llamar a `registrar()` en: login correcto (`LOGIN`), login fallido (`LOGIN_FALLIDO`, `resultado="DENEGADO"`, con `email`), bloqueo de cuenta (`CUENTA_BLOQUEADA`), `LOGOUT`, `CAMBIO_PASSWORD`, alta de usuario por el admin (`CREAR`, entidad `usuario`, detalle con el rol), edición por el admin (`EDITAR`; si cambia el rol, `CAMBIO_ROL` con `{"anterior": ..., "nuevo": ...}`) y baja (`ELIMINAR`). Incluye la corrección de mensajes del punto 2.3. Tests que verifiquen una fila por cada acción y que ninguna contraseña ni token aparezca en `detalle`.

**F0-05c — Eventos del núcleo y accesos denegados.** Registrar: cambio de estado de campeonato (`CAMBIO_ESTADO`, anterior/nuevo), generar y eliminar fixture (`GENERAR_FIXTURE`, cantidad de partidos), resultado (`REGISTRAR_RESULTADO`), incidencia (`REGISTRAR_INCIDENCIA`), exportaciones de reportes (`EXPORTAR`), predicciones y entrenamiento (`ML_PRED`). Puntos de enganche: `deportes/views.py` (acción de cambio de estado), `fixture/views.py` (generar fixture, registrar resultado, incidencia), `reportes/views.py`, `ml/views.py`. Además un manejador de excepciones DRF (`config/exception_handler.py`, configurado en `REST_FRAMEWORK["EXCEPTION_HANDLER"]`) que registre `ACCESO_DENEGADO` en cada 403 de un usuario autenticado, con método y ruta en `detalle` (no registrar los 401 de anónimos: son ruido).

**F0-06 — Invalidar tokens al cambiar contraseña.** Hoy `CambioPasswordView` llama a `RefreshToken.for_user(user)` y el comentario dice que invalida tokens, pero no hace nada. Poner en lista negra todos los `OutstandingToken` del usuario (app `token_blacklist`, verifica que esté en `INSTALLED_APPS`), devolver un par de tokens nuevos en la respuesta, y probar que el refresh anterior deja de funcionar.

**F0-07 — Argon2.** `argon2-cffi` en `requirements.txt`; `PASSWORD_HASHERS` con Argon2 primero y PBKDF2 después en `base.py`. Reconstruir la imagen. Test: una contraseña nueva se guarda con prefijo `argon2$` (sobrescribiendo el hasher del `conftest` dentro del test) y un hash PBKDF2 antiguo sigue autenticando y se actualiza a Argon2 tras el login.

**F0-08 — Predictor.** En `ml/services/predictor.py` importar `from django.db.models import Q` y reemplazar `models.Q` por `Q`. Eliminar los imports sin uso que reporta pyflakes en `apps/ml`. Test que ejecute `entrenar()` con partidos finalizados de prueba sin lanzar excepción (si el código exige un mínimo de partidos, crear esa cantidad en el test).

**F0-09 — Refresh rotado en el frontend.** `frontend/lib/api/client.ts`: guardar `data.refresh` además de `data.access`; refresh de una sola petición compartida (*single-flight*) cuando varias peticiones reciben 401 a la vez; si el refresh falla, cerrar sesión y redirigir a `/login`. Mostrar el mensaje del 429 (cuenta bloqueada o límite por IP) en el login en lugar de un error genérico. Verificar con `npm run lint && npm run build` y una prueba manual: iniciar sesión, forzar dos refrescos y confirmar que la sesión sigue activa.

**F0-10 — Configuración.** `git ls-files .env` debe estar vacío; `python manage.py check --deploy` con `DJANGO_SETTINGS_MODULE=config.settings.production` sin errores críticos; `DEBUG=False`, `ALLOWED_HOSTS` y CORS desde entorno, cookies seguras; documentar `NUM_PROXIES`, `LOGIN_*` y `LOGIN_THROTTLE_RATE` en `.env.example`.

## 4. Puntos de revisión

Al cerrar cada fase (F0, F1, F2, F3), revisar el `git diff` de las tareas de la tabla "Cuándo detenerte" de `PROMPT_MAESTRO_COPILOT.md` y pasar los reportes finales a una revisión externa.

## 5. Riesgos a vigilar desde la Fase 1

- Las migraciones de datos (`COORDINADOR→DELEGADO`, `ARBITRO→ORGANIZADOR`, `Facultad` desde texto libre) deben mostrar primero el conteo de filas afectadas y ser reversibles o, al menos, no destructivas.
- `ExclusionConstraint` requiere la extensión `btree_gist` de PostgreSQL (migración `BtreeGistExtension`) y que la base de test la permita.
- No resetear la base de desarrollo sin avisar: usar `seed_realista` (reemplaza a `seed_demo`) solo cuando se confirme que no hay datos reales.

---

# 6. Fase 1 — Correcciones según el esquema oficial del documento (`docs/CAP7_DDL_DOCUMENTO.sql`)

> **Fuente de verdad para F1:** `docs/CAP7_DDL_DOCUMENTO.sql` (script del Cap. 7, 17 tablas). Donde el plan original difiere de este esquema, **manda el esquema**. Las "ampliaciones" son campos o tablas que el código necesita y el documento no tiene: se conservan y se anotan para actualizar el Cap. 7.
> Nombres físicos: el documento usa `recursos_*`, `campeonatos_*`, `quejas_*`, `bitacora_*`; el código usa sus propias apps (`deportes`, `fixture`, `instalaciones`…). Decisión: **no renombrar tablas**; se documenta una tabla de correspondencia (F8-09).

| Tarea | Corrección al plan original |
|---|---|
| **F1-01 Roles** | Valores: `SUPERADMIN`, `ADMIN_DUBSS`, `ORGANIZADOR`, `DELEGADO` y `JUGADOR` (**reservado**, sin permisos; solo aloja las cuentas antiguas DEPORTISTA/PUBLICO ya desactivadas, y el futuro panel F7-10). Migración de datos: `COORDINADOR→DELEGADO`; `ARBITRO→ORGANIZADOR`; `DEPORTISTA`/`PUBLICO→JUGADOR` con `is_active=False`; `is_superuser=True→SUPERADMIN`. Solo un SUPERADMIN puede crear/editar cuentas SUPERADMIN. `create_superuser` asigna `SUPERADMIN`. Rol por defecto del modelo: `DELEGADO`. |
| **F1-02 Facultad** | Tabla `Facultad(nombre unique 150, sigla unique 20)`. `Usuario.facultad` FK **nullable** (como en el documento); obligatoria si el rol es `DELEGADO` (validar en serializer). Revisar también si el documento tiene `Usuario.estado` (varchar 12) y el código no. |
| **F1-03 Equipo** | Según el documento: `nombre, color, logo, estado, creado_en, delegado FK(null), facultad FK(NOT NULL)`, **único `(nombre, facultad)`**. **NO** lleva `categoria`, `deporte` ni `campeonato` (esto corrige mi propuesta anterior). La participación vive en `Inscripcion`. |
| **F1-04 Inscripcion** | Tabla `CampeonatoEquipo` del documento: `fecha_inscripcion, estado (varchar 15), campeonato, equipo`, único `(campeonato, equipo)`. *Ampliaciones:* `validado_por`, `fecha_validacion`, `observaciones`. |
| **F1-05 Jugador/Ficha** | Según el documento: `nombre, apellido, carnet, registro, posicion, numero_camiseta, estado, creado_en, equipo FK(NOT NULL), usuario FK(null), partidos_sancion_restantes, sancion_origen` como **entero (no FK)**, único `(equipo, carnet)`. El carnet **no** es único global (corrige mi propuesta). |
| **F1-06 Campeonato** | Documento: `nombre, formato, estado, fecha_inicio, fecha_fin, max_equipos, descripcion, imagen_banner, creado_en, actualizado_en, categoria FK, creado_por FK(null)`. **Sin `deporte` propio.** *Ampliaciones:* `min_jugadores`, `max_jugadores`, `fecha_cierre_inscripcion`, `puntos_victoria/empate/derrota`. |
| **F1-07 Deporte/Categoría** | Deporte: `cantidad_jugadores`, `activo`, `creado_en`, `imagen`. Categoría: `genero`, `rango_edad` (varchar 20), `activa`, `deporte FK`, único `(deporte, nombre, genero)`. |
| **F1-08 Instalaciones** | El documento tiene una sola tabla `Instalacion` (`nombre unique, tipo, ubicacion, capacidad, estado, imagen`). `Cancha`, `BloqueoCancha` y el nuevo `HorarioCancha` son **ampliaciones** del código (documentarlas en el Cap. 7). |
| **F1-10 Queja** | Tabla `quejas_queja` del documento (app nueva `quejas`): `tipo, descripcion, estado, resolucion, fecha_hora, resuelta_en, admin_resuelve FK(null), delegado FK(null), encuentro FK(NOT NULL)`, único `(encuentro, tipo)`. La queja **siempre** es sobre un encuentro (corrige mi propuesta con `autor/campeonato`). |
| **F1-11 Partido (= Encuentro)** | Documento: `fecha_hora, jornada, fase, estado, generado_por_ml, observaciones, creado_en, actualizado_en, campeonato, equipo_local, equipo_visitante, instalacion FK(null)`. *Ampliaciones:* `cancha`, `duracion_min`, `fecha_hora_fin`, `arbitro` (dato opcional). El campo `fase` sirve para las rondas de eliminación directa. |
| **F1-14 (NUEVA) Bitácora alineada** | La tabla del documento es `accion, modulo, descripcion, objeto_id, ip_origen, fecha_hora, usuario`. Renombrar en `auditoria.Bitacora`: `entidad→modulo`, `entidad_id→objeto_id`, `ip_address→ip_origen`, `fecha→fecha_hora`. Mantener como *ampliaciones*: `detalle`, `resultado`, `usuario_email`. Actualizar migraciones nuevas, serializers, filtros, `registrar()` y tests. |

**Orden recomendado de F1** (por dependencias): F1-01a → F1-01b → F1-02 → F1-07 → F1-03 → F1-04 → F1-05 → F1-06 → F1-08 → F1-09 → F1-10 → F1-11 → F1-13 → F1-14 → F1-12 (el `seed_demo` va al final porque depende de todos los modelos).

**Regla F1-13:** cuando existen incidencias `GOL`, cada una debe identificar un jugador de uno de los equipos del partido y el conteo por equipo debe coincidir con el marcador; sin incidencias de gol se permite registrar el marcador manualmente.

**F1-01 se divide:** *01a* = backend (roles, permisos, migración de datos, tests); *01b* = frontend mínimo (tipos y hook `useAuth` con los roles nuevos).

**Coincidencia útil:** el documento ya incluye `bloqueado_hasta` e `intentos_fallidos` en `usuarios_usuario` (idénticos a lo hecho en F0-04).

---

# 7. Estado verificado de Fase 1 y Fase 2 (29/10/2026)

**Verificación real:** 427 tests en verde (Postgres 16 en Docker), `makemigrations --check` limpio, `pyflakes` limpio, `npm run lint` y `npm run build` correctos, y prueba HTTP contra el backend en ejecución (login de los 4 roles + anónimo, 28 endpoints × 5 perfiles, 0 desvíos; delegado ajeno → 404; registro anónimo → 401; escalada de rol por perfil ignorada).

| Fase | Estado | Notas |
|---|---|---|
| F1 (F1-01 … F1-14) | ✅ | Roles, `Facultad`, `Equipo` reutilizable, `Inscripcion`, ficha sin cuenta, `Campeonato` sin `deporte`, horarios/bloqueos, elegibilidad, `quejas`, constraints de `Partido` (incl. `ExclusionConstraint`), bitácora alineada, `seed_demo` idempotente |
| F2-01 … F2-06 | ✅ | Permisos por rol/objeto, filtrado por facultad (404), `/me/`, `/mi-equipo/`, `/mis-quejas/`, GET sin escritura, quejas, reportes restringidos |
| F2-07 Matriz de permisos | ✅ | `apps/users/tests/test_matriz_permisos.py`: 35 endpoints × 6 perfiles (incl. anónimo y JUGADOR reservado) |
| F2-08 CI | ✅ | `.github/workflows/ci.yml` (tests + migraciones + pyflakes; lint + build). `--fail-under=70` se activa en F8 |

**Corrección hecha durante la verificación:** `MiPerfilView` solo aceptaba multipart (un `PATCH` JSON daba 415); ahora acepta también `JSONParser`, con `rol`/`facultad`/`is_active` siempre de solo lectura.

**Pendiente conocido (fuera de F2):** frontend de F4/F5 (hoy hay `dashboard`, `campeonatos`, `fixture`, `ml`, `login`; faltan vista pública, paneles `gestion`/`delegado`, `lib/auth/roles.ts`); F3 (máquina de estados, generador robusto, eliminación directa, resultados corregibles, tabla recalculable). El contenedor `frontend` de `docker-compose.dev.yml` no arranca (`next: not found`, sin `node_modules` en la imagen): reconstruir con `docker compose -f docker-compose.dev.yml build frontend`.

---

# 8. Fase 3 — Núcleo deportivo (29/10/2026) ✅ F3-01 … F3-09

**Verificación:** 635 tests en verde (dos corridas), `makemigrations --check` limpio, `pyflakes` limpio, `npm run lint` + `npm run build` correctos, y prueba HTTP real de punta a punta (campeonato → estados → inscripción → aprobación → fixture → resultado → corrección → tabla → historial → finalizar → limpieza).

| Tarea | Estado | Qué se hizo |
|---|---|---|
| F3-01 Estados de campeonato | ✅ | Máquina de estados en `deportes/services.py`; `PATCH /campeonatos/{id}/estado/` responde 400 con los motivos y registra el rechazo (`resultado=ERROR`). `estado` ya no se escribe por POST/PUT/PATCH del campeonato. El serializer expone `transiciones_permitidas`. Validaciones de alta: categoría activa, `max_equipos ≥ 2`, cierre de inscripción anterior al inicio, fechas coherentes |
| F3-02 Flujo de inscripciones | ✅ | `GET /inscripciones/{id}/elegibilidad/` y `PATCH .../validar/` (aprobar corre `evaluar_inscripcion`; rechazar exige observación; notifica al delegado por correo). Solicitar valida estado, plazo de cierre y equipo activo |
| F3-03 Generador robusto | ✅ | `fixture_generator.py` reescrito: transacción única (incluye el borrado), nunca borra partidos `FINALIZADO/WALKOVER/EN_CURSO` (409), programación en paralelo por cancha, respeta horarios/bloqueos/restricciones de facultad/partidos de otros campeonatos, acotado (sin bucle infinito), BYE, `doble_vuelta`, `generado_por_ml=False`. 20 equipos ≈ 3 s |
| F3-04 Eliminación directa | ✅ | Llaves con cabezas de serie (orden de inscripción), BYE, partidos "placeholder" enlazados (`ronda`, `partido_origen_local/visitante`), avance automático del ganador, penales en `Resultado` |
| F3-05 Resultados corregibles | ✅ | `POST/PATCH/DELETE /partidos/{id}/resultado/`; la corrección exige `motivo` y guarda anterior/nuevo en bitácora (`CORREGIR_RESULTADO`); W.O. con marcador configurable (`WALKOVER_GOLES_GANADOR`) |
| F3-06 Tabla recalculable | ✅ | `fixture/services/tabla.py::recalcular` (idempotente); desempate: puntos, DG, GF, enfrentamiento directo, nombre; campo `posicion`; eliminado `actualizar_con_resultado` |
| F3-07 Historial | ✅ | `PosicionHistorial`; se reconstruye al cerrar jornadas y al corregir/borrar resultados; `GET /campeonatos/{id}/historial/` (público) |
| F3-08 Incidencias y sanciones | ✅ | Jugador obligatorio y del partido; roja → `SANCION_PARTIDOS_ROJA`; amarillas acumuladas → `AMARILLAS_PARA_SANCION`; se descuenta al finalizar cada partido posterior del equipo |
| F3-09 Reprogramación | ✅ | `PATCH /partidos/{id}/` y alta manual validan cancha, franja, bloqueos, solapes de equipo/cancha (cualquier campeonato) y restricciones de facultad → **409** con la lista de conflictos; bitácora y correo a los delegados |

**Migración nueva:** `fixture.0005_eliminacion_walkover_historial` (aplicada también en la BD de desarrollo; no destructiva).

## Decisiones y desviaciones respecto al plan original (manda este anexo)

1. **Estados de campeonato:** se conservan los existentes (`PLANIFICACION → INSCRIPCIONES → EN_CURSO → FINALIZADO`, `CANCELADO` desde cualquiera salvo `FINALIZADO`; además `INSCRIPCIONES → PLANIFICACION`). No se agregó `PROGRAMADO`: la BD no lo tiene y el fixture se genera durante `INSCRIPCIONES`. Para pasar a `EN_CURSO` hacen falta ≥ 2 inscripciones aprobadas y fixture; para `FINALIZADO`, ningún partido pendiente.
2. **Elegibilidad al aprobar:** bloquean (400) mínimo/máximo de jugadores, jugador duplicado en otro equipo del campeonato y cupo `max_equipos`; un jugador **sancionado es advertencia**, no bloquea al equipo. El plazo y el estado del campeonato se validan al **solicitar**, no al aprobar.
3. **Tabla sin `on_commit`:** se recalcula dentro de la misma transacción del resultado (queda atómica y nunca desfasada; `on_commit` no aportaba nada con un cálculo de milisegundos).
4. **Tipos de incidencia:** se mantienen `TARJETA_AMARILLA/TARJETA_ROJA/SUSTITUCION` (en vez de `AMARILLA/ROJA`) para no romper datos existentes.
5. **Equipos nulos en `Partido` (ampliación):** `equipo_local/visitante` son nullable solo para los partidos *placeholder* de eliminación (el DDL del Cap. 7 los tiene NOT NULL → documentar en el Cap. 7, junto con `ronda`, `partido_origen_*`, `Resultado.penales_*`, `Resultado.walkover`, `TablaPosiciones.posicion` y `PosicionHistorial`). Ml, reportes y listados toleran "Por definir".
6. **Generador en memoria:** las reglas de disponibilidad se precargan en memoria para cumplir RNF04; un test contrasta cada partido generado con `detectar_conflictos`. `canchas_disponibles` ahora también excluye canchas con otro partido solapado y usa `Exists` (el `exclude` multivalor anterior podía excluir mal).
7. **`usar_ml=true` responde 400** con mensaje claro hasta que exista el optimizador (F5b); ya no se oculta con `try/except ImportError`.
8. **Sanciones:** un W.O. no cuenta como partido cumplido; eliminar un resultado no devuelve sanciones ya descontadas (limitación conocida); corregir un resultado no descuenta dos veces.
9. **Correo, no push:** los avisos usan `notificaciones/services.py::notificar_usuarios` (correo, `fail_silently`); el push FCM v1 es F6-04.
10. **Configurables (settings/env):** `SANCION_PARTIDOS_ROJA=1`, `AMARILLAS_PARA_SANCION=3`, `WALKOVER_GOLES_GANADOR=3`.

**Bugs hallados y corregidos durante la fase:** `elegibilidad` era visible para el delegado (permiso del `@action` ignorado por `get_permissions`); `select_for_update` con `select_related` nullable; generador > 10 s con 20 equipos; fecha en UTC en la bitácora de reprogramaciones.

**Tests actualizados por reglas nuevas e intencionales** (`test_eventos_nucleo.py`): transición de estado válida, gol sin jugador ahora es 400, y el `detalle` de bitácora incluye `walkover`/`partidos_sancion`/`doble_vuelta`.

**Pendiente para F4/F5:** pantallas de resultados/incidencias con corrección, llaves de eliminación, calendario por cancha con reprogramación, bandeja de inscripciones con motivos de elegibilidad. Hoy solo se adaptó el selector de estado del detalle de campeonato (usa `transiciones_permitidas` y muestra el error).

---

# 9. Fase 4 — Frontend: base de diseño (29/10/2026) ✅ F4-01 … F4-08

**Verificación:** `npm run lint` y `npm run build` limpios, `tsc` sin errores, 635 tests de backend en verde, y prueba real con navegador (Chrome) en 360, 768 y 1280 px: sin desbordes horizontales; login por la UI; `document.cookie` vacío tras iniciar sesión.

| Tarea | Estado | Qué se hizo |
|---|---|---|
| F4-01 Tokens | ✅ | Paleta `brand` (rojo `#d21115` del escudo) e `ink` (neutros fríos) en `tailwind.config.js`; foco visible global; sin `style={{}}` en todo `app/`, `components/` y `lib/` |
| F4-02 Componentes | ✅ | `components/ui/`: Button, Input/Select/Textarea/Checkbox, FormField, Card, Badge/EstadoBadge, Table (scroll, vacío, paginación), Modal (foco atrapado, Escape), ConfirmDialog, Tabs (teclado), Toast, Spinner, EmptyState, PageHeader. Íconos `lucide-react`; **cero emojis**. Catálogo en `/ui-kit` (solo desarrollo: Next ignora las carpetas `_`, por eso no es `/_ui`) |
| F4-03 Capa de datos | ✅ | `types/index.ts`, `lib/api/services.ts` por recurso y hooks en `lib/hooks/queries.ts`. Ninguna página importa axios ni el cliente |
| F4-04 Formularios | ✅ | react-hook-form + zod en login, nuevo campeonato y resultado; `lib/api/errors.ts` mapea los 400 de DRF a campos; todos los `alert()` → toasts |
| F4-05 Sesión | ✅ | Tokens en cookies **httpOnly** (`app/api/auth/{login,refresh,logout,session}`) y proxy `app/api/proxy/[...path]` que agrega el Bearer y renueva el access (con rotación) si expira. `middleware.ts` decodifica `exp/rol` solo para enrutar |
| F4-06 Layout | ✅ | `AppShell`: barra lateral contraíble (se recuerda), cajón móvil, menú de usuario, enlace "saltar al contenido", `aria-*` |
| F4-07 Roles | ✅ | `lib/auth/roles.ts` (`ROLE_HOME`, `NAV_BY_ROLE`, `PERMISOS_POR_ROL`), `<RequireRole>`, `useAuth` expone `rol`, `facultad`, `can()` |
| F4-08 Descargas | ✅ | PDF/Excel por blob vía proxy (prueba real: `application/pdf` con su nombre de archivo) |

**Pantallas rediseñadas:** login, inicio, campeonatos (alta con formulario), detalle de campeonato (estados válidos, generar fixture, reportes, pestañas Partidos/Posiciones), fixture, posiciones, partido (registrar/corregir resultado con penales y motivo) y predicciones.

**Cambios de backend por la UI:** el listado de partidos ahora incluye `goles_local/goles_visitante` (antes el marcador no aparecía en el calendario) y carga `resultado` con `select_related`.

**Notas operativas**
- Con el proxy, Django ve la IP del servidor Next: se reenvía `X-Forwarded-For`, pero para que el límite por IP del login cuente a cada visitante hay que ajustar `NUM_PROXIES` (nginx + Next = 2) en producción.
- En Docker el servidor de Next necesita `API_INTERNAL_URL=http://backend:8000/api/v1` (agregado a `docker-compose.dev.yml` y documentado en `.env.example`).
- El contenedor `frontend` de desarrollo sigue sin arrancar (`next: not found`): hay que reconstruir la imagen. Verifiqué con Node local.
- Los endpoints `campeonatos`, `partidos` y `tabla` son públicos en lectura, por eso el proxy los sirve aun sin sesión; la vista pública anónima es F5.

---

# 10. Fase 5 — Paneles por rol (30/10/2026) ✅ F5-01 … F5-15

**Verificación:** 685 tests de backend en verde, `pyflakes` y `makemigrations --check` limpios, `npm run lint`, `tsc` y `build` (24 rutas) correctos, y **prueba de flujos con Chrome real sobre Docker (80/81 comprobaciones)**: el único aviso fue una carrera del propio guion (contaba filas antes de cargar); la bitácora tenía 254 registros y su filtro pasó.

**Rutas**
- Público (sin sesión): `/`, `/campeonatos`, `/campeonatos/[id]` (calendario, posiciones, historial, estadísticas), `/partidos/[id]`.
- Gestión (`SUPERADMIN`, `ADMIN_DUBSS`, `ORGANIZADOR`): `/gestion`, `campeonatos`, `inscripciones`, `fixture` (por cancha y por jornada, reprogramar con conflictos), `partidos/[id]` (planilla: incidencias, resultado, corrección, eliminación), `predicciones`, `quejas`, `reportes`. Solo admin: `catalogos`, `usuarios`, `bitacora`.
- Delegado: `/delegado`, `equipos` (+ plantel), `inscripciones`, `calendario`, `quejas`, `predicciones`.
- `/perfil` para todos. El `middleware.ts` redirige por rol y `RequireRole` repite la guardia; la seguridad real sigue en la API.

**Backend agregado:** `GET /fixture/estadisticas/`, filtro `?equipo=` en partidos, `GET /deportes/inscripciones/{id}/elegibilidad/` para el delegado (solo su facultad), reportes `reportes/equipo|jugador/{id}/pdf|excel/` (RF16), paginación con `?page_size=` (máx. 200), `409` claro al borrar algo en uso (`ProtectedError`), detalle del partido en las quejas.

**Bugs hallados por la prueba de flujos y corregidos**
1. `POST /usuarios/` daba **500** al crear una segunda cuenta sin carnet (`ci` único guardado como `""`): ahora un CI vacío se guarda como `NULL`; un CI repetido responde 400 (2 tests nuevos).
2. `GET /auth/session` devolvía 401 para el visitante anónimo (ruido en consola): ahora 200 con `usuario: null`.
3. El proxy de Next reintenta las lecturas como anónimo si la sesión cayó, para que lo público siga funcionando.

**Notas operativas**
- El contenedor `frontend` de desarrollo ya arranca (imagen reconstruida). **No ejecutar `npm run build` con ese contenedor encendido**: comparten `.next`.
- La prueba borró por error la categoría demo de baloncesto; se restauró con `seed_demo` (idempotente).
- Pendiente (Fase 5b/6): optimizador con ML (`usar_ml` sigue respondiendo 400 con mensaje claro), subida de foto de perfil probada solo por validación de formulario.

---

# 11. Fase 5b — RF11 con ML (30/10/2026) ✅ F5b-01 … F5b-04 + auditoría de lógica

## 11.1 Auditoría de la lógica y los flujos contra el documento (RF8–RF13)

| Hallazgo | Gravedad | Corrección |
|---|---|---|
| **RF10/RF11 exigen cerrar las inscripciones antes de generar el fixture**, pero el código permitía generarlo con inscripciones abiertas (un equipo aprobado después quedaba fuera del calendario). | Alta | Nuevo estado `INSCRIPCION_CERRADA` («Inscripciones cerradas»). Flujo: Planificación → Inscripciones → **Inscripciones cerradas** → (fixture) → En curso. Cerrar exige ≥ 2 equipos aprobados; iniciar exige fixture; reabrir se bloquea si ya hay fixture. Generar fixture solo en `INSCRIPCION_CERRADA`. |
| Se podían **aprobar equipos con las inscripciones cerradas**. | Alta | `validar` solo aprueba con el campeonato en `INSCRIPCIONES` (rechazar sigue permitido). |
| RF11: «el organizador revisa el fixture y confirma; recién entonces se publica y el campeonato pasa a En Curso». El fixture borrador era público de inmediato. | Media | El fixture es **borrador** (solo lo ve gestión) hasta que el campeonato pasa a `EN_CURSO`; entonces se publica para el público y los delegados. |
| **Un organizador podía eliminar un campeonato en cualquier estado**, borrando en cascada partidos, resultados, tabla e historial, sin dejar bitácora. | Alta | Solo se elimina en `PLANIFICACION`/`CANCELADO` y sin resultados (400 «Cancélalo para conservar su historial»); queda en bitácora. |
| Con fixture generado se podía cambiar el formato/categoría o bajar el cupo por debajo de los equipos aprobados. | Media | Validación en el serializer (400). |

**Brechas conocidas frente al documento (no se inventaron datos que el esquema oficial no tiene):**
- RF8: no se valida género ni rango de edad del jugador ni «carnet universitario vigente» (la ficha no guarda fecha de nacimiento, género ni vigencia). Requiere ampliar el Cap. 7.
- RF7/RF1: el rol `JUGADOR` sigue reservado (sin panel), por decisión fija del proyecto.
- RF10 menciona el estado «Archivado»: hoy se usa `CANCELADO`/`FINALIZADO`.
- RF11 pide generar «mediante Random Forest»: se implementó el enfoque híbrido de la decisión D9 (el Random Forest puntúa; CP-SAT garantiza la validez). Un Random Forest por sí solo no puede garantizar cero conflictos.

## 11.2 Diseño del ML

```
Plan de partidos (liga / eliminación)  ─►  Disponibilidad (reglas duras en memoria)
                                              │ candidatos válidos por partido: (cancha, horario)
                                              ▼
              AsignacionScorer (Random Forest) ─ probabilidad de «buena asignación» ─►  CP-SAT (OR-Tools)
                                                                                         maximiza Σ puntaje
                                                                                         sujeto a restricciones duras
```

- **Variables del modelo** (las del documento + una ampliación): franja horaria, día de la semana, fin de semana, días desde el último partido de cada equipo, descanso mínimo, disponibilidad de la instalación, conflictos de horario (partidos en otras canchas del mismo recinto a ±1 h) y holgura con restricciones de facultad.
- **Restricciones duras (CP-SAT):** un partido = una cancha y un horario; sin solape de cancha ni de equipo; descanso mínimo (`FIXTURE_DESCANSO_MIN_HORAS`, 24 h); horarios de cancha, bloqueos, restricciones de facultad y partidos de otros campeonatos.
- **Resolución por jornada:** cada jornada es un subproblema exacto; la jornada resuelta alimenta los «días desde el último partido» de la siguiente. Los horarios avanzan de a una duración de partido, así la asignación es pura (a lo sumo un partido por cancha/equipo y horario) y el solver cierra en ≈ 0,15 s por jornada.
- **Degradación segura:** si el modelo no está disponible, el solver no halla solución o hay un error inesperado, se genera con el método base y se **avisa** al organizador. `generado_por_ml=True` solo si el optimizador realmente se usó.
- **Datos de entrenamiento (`ml.MuestraAsignacion`, tabla del Cap. 7):** *arranque en frío* con 3 000 muestras etiquetadas por reglas explícitas (`puntaje_por_reglas`, documentadas en el código; «buena» ≥ 0,90 = horario ideal 10–17 h, con descanso, sin conflictos); y *historial real*: cada partido finalizado = BUENA; suspendido, postergado o W.O. = MALA, con peso ×5. `python manage.py entrenar_asignacion [--historial]` o el botón «Reentrenar» (solo administrador).
- **Honestidad de las métricas:** con el arranque en frío la exactitud (≈ 99 %) mide cuánto aprendió el modelo de las reglas, **no** la calidad real de un torneo; la interfaz lo dice. Mejora al reentrenar con partidos jugados.
- **Ampliaciones al DDL (documentar en el Cap. 7):** estado de campeonato `INSCRIPCION_CERRADA`; `MuestraAsignacion.origen`, `.holgura_facultad_min`, `.partido_id`.

## 11.3 API y pantallas

- `POST /fixture/generar/` acepta `usar_ml`; responde `generado_por_ml`, `aviso`, `calidad` y `ml` (versión del modelo, puntaje medio, tiempos).
- `GET /fixture/calidad/?campeonato=` (gestión): conflictos, descanso promedio y mínimo, % en franja ideal, equidad.
- `GET/POST /ml/asignacion/`: estado del modelo (gestión) y reentrenamiento (solo administrador, auditado).
- UI: casilla «Optimizar con Machine Learning» (marcada) en «Generar fixture», resumen de calidad al terminar, tarjeta «Calidad del fixture» con insignia ML, aviso de borrador, y tarjeta «Modelo de programación del fixture» (versión, métricas, variables que más pesan) en Gestión → Inteligencia artificial.

## 11.4 Verificación
- Backend: 735 tests (incl. 13 del puntuador, 22 del optimizador/API/métricas, 3 de integridad de campeonatos); `pyflakes` y `makemigrations --check` limpios. Frontend: `lint`, `tsc` y `build` correctos. Prueba con Chrome real sobre Docker: 22 comprobaciones del flujo cerrar inscripciones → generar con ML → borrador oculto → publicar → modelo (la única falla fue de sincronización del guion, la API y el sitio público mostraron los 15 partidos).
- RNF04: 20 equipos / 190 partidos con ML, cero conflictos, ≈ 7 s incluyendo escritura en base (≈ 4,5 s del optimizador).
- Despliegue: `ortools==9.11.4210` y `protobuf` 5.26 en `requirements.txt` (con numpy 2.0.1 fijado); **reconstruir la imagen del backend**. Migraciones nuevas: `deportes.0010_estado_inscripcion_cerrada`, `ml.0004_muestra_asignacion`.
- Pendiente (F6-01): reescribir el predictor de resultados (RF15) — fuga de datos y validación. No se tocó en esta fase.

---

# 12. Fase 6 — IA central y automatización

## 12.1 Decisión de tecnologías de IA (qué usa cada función y por qué)

| Función | Tecnología | Por qué |
|---|---|---|
| Predicción de resultados (RF15) | scikit-learn local (RandomForest) con respaldo Elo | Se entrena con el historial propio de la DUBSS; sin costo ni dependencia externa. Solo se activa si **supera** las líneas base (frecuencia histórica y Elo). |
| Programación del fixture (F5b) | RandomForest + OR-Tools CP-SAT (local) | Optimización con restricciones duras reales. |
| Clima | Open-Meteo (gratuito, sin clave) | Pronóstico horario hasta 16 días; coordenadas en `CLIMA_LATITUD/LONGITUD`. |
| Asistente de voz | Groq: Whisper large-v3-turbo (voz a texto) + gpt-oss-20b (intención; Llama 3.3 ya no existe en Groq) | Nivel gratuito suficiente, baja latencia. Sin clave, el asistente usa un intérprete local por reglas (solo se pierde la transcripción de voz). |
| Notificaciones push | Firebase Cloud Messaging HTTP v1 (`google-auth`) | Estándar para Android/iOS/web. Sin credencial, el push se desactiva y el correo sigue funcionando. |

Variables de entorno: `GROQ_API_KEY`, `LLM_PROVIDER`, `LLM_MODEL`, `STT_PROVIDER`, `STT_MODEL`, `OLLAMA_URL`, `FCM_CREDENTIALS_FILE`, `CLIMA_LATITUD`, `CLIMA_LONGITUD`, `REDIS_URL`.

## 12.2 Lógica corregida respecto a la versión anterior
- **Predictor sin fuga de datos:** las variables se calculan «a la fecha» del partido (Elo K=24, ventaja de local +60, forma de 5 partidos, goles a favor/contra de 10, descanso, historial directo); validación walk-forward (`TimeSeriesSplit`); métricas log-loss, Brier y ECE. Mínimo 30 partidos finalizados; si no, se usa Elo y la predicción se marca `datos_suficientes=false` (confianza baja en la interfaz). Registro de versiones en `ml.ModeloML` (un solo activo por nombre).
- **Clima:** `SIN_DATOS` ya no se confunde con riesgo bajo; el GET solo lee lo guardado y el POST/tarea consulta; un partido a más de 16 días no guarda nada y la interfaz muestra el motivo.
- **Asistencia:** se declara como estimación por reglas (no hay asistencia real registrada para entrenar).
- **Recomendaciones:** acciones calculadas con datos reales (riesgo climático ≤ 48 h, quejas abiertas, partidos sin resultado, inscripciones pendientes, campeonatos sin fixture, plazos vencidos).
- **Estadísticas:** W.O. no cuenta como rendimiento; nuevos reportes por facultad (`/reportes/facultad/<id>/`, `/pdf/`, `/excel/`).

## 12.3 Automatización (Celery + Redis)
Servicios `redis`, `celery_worker`, `celery_beat` en ambos `docker-compose`. Tareas idempotentes: `enviar_recordatorios` (cada 15 min; 24 h y 2 h antes; `RecordatorioEnviado` UNIQUE(partido, tipo); solo partidos PROGRAMADOS de campeonatos EN_CURSO), `ml.actualizar_riesgo_climatico` (cada 3 h; avisa solo cuando el riesgo empeora a ALTO/CRÍTICO), `fixture.reconstruir_historial` (02:30), `ml.reentrenar_modelos` (domingos 03:00; omite si los datos no cambiaron).

## 12.4 Asistente de voz (F6-06)
Lista blanca: `reporte_campeonato`, `tabla_posiciones`, `estadisticas_jugador`, `estadisticas_equipo`, `proximos_partidos`, `resumen_torneo`. El modelo solo devuelve intención y nombres; el código resuelve las entidades en la base y **pregunta** si hay ambigüedad. Solo lectura, auditado, 30 consultas/min, roles ADMIN y ORGANIZADOR. Flujo en pantalla: grabar o escribir → editar el texto → interpretar → (aclarar) → confirmar → ejecutar.

## 12.5 API y pantallas nuevas
- `GET/POST /ml/entrenar/` (informe y entrenamiento del predictor), `GET/POST /ml/riesgo-climatico/<partido>/`, `/ml/asistencia/<partido>/`, `/ml/recomendaciones/`.
- `POST /notificaciones/enviar/`, `GET /notificaciones/canales/`. `GET /asistente/estado/`, `POST /asistente/transcribir|interpretar|ejecutar/`.
- UI: «Asistente» y «Avisos» en el menú de gestión; tarjeta «Predictor de resultados» (métricas contra líneas base) en «Inteligencia artificial»; «Clima del partido» y «Asistencia estimada» en la planilla del partido; tarjeta «Por facultad» en Reportes.

## 12.6 Verificación y límites
- Backend: 914 tests; `makemigrations --check` limpio. Frontend: `lint` y `tsc` limpios. E2E en Chrome: asistente (interpretar, ejecutar, rechazo de órdenes fuera de la lista), avisos, predictor, pronóstico real de Open-Meteo, PDF por facultad, permisos por rol.
- Las integraciones con Groq y FCM solo se probaron con simulaciones (no hay claves en el entorno de desarrollo); requieren `GROQ_API_KEY` y el JSON de cuenta de servicio de Firebase para operar en producción.
- El predictor usa Elo hasta reunir 30 partidos finalizados. Despliegue: reconstruir imágenes (`google-auth`), aplicar migraciones `ml.0005` y `notificaciones.0001`.

---

# 13. Fase 7-A — Agente «Asistente del Organizador»

## 13.1 Qué es y qué no es
Un agente con *function calling*: el LLM decide qué herramienta usar, el **servidor** la ejecuta con los permisos de la persona y el resultado vuelve al modelo hasta que responde. No es un chatbot de texto libre ni modifica datos por sí mismo.

Ejemplo real: «Hay lluvia el sábado, reprograma lo necesario» → `ver_clima` → `proponer_reprogramacion` (optimizador en modo reparación) → `aplicar_reprogramacion` (crea la **acción pendiente**) → tarjeta con los cambios → la persona pulsa *Confirmar* → se aplica en una transacción, se audita y se avisa a los delegados.

## 13.2 Modelo de IA
Groq con `openai/gpt-oss-120b` (`AGENTE_MODEL`), `reasoning_effort=low`. Se descartó `gpt-oss-20b`: se equivocó con «el sábado» (calculó el 29/10 en vez del 31/10). Por eso, además, el prompt incluye una **tabla de los próximos 10 días** y las herramientas rechazan fechas pasadas. Solo Groq está soportado (Ollama queda fuera de esta versión).

## 13.3 Herramientas (`apps/agente/services/herramientas.py`)
| Herramienta | Tipo | Notas |
|---|---|---|
| `listar_campeonatos`, `consultar_tabla`, `listar_partidos`, `predecir_partido`, `generar_reporte` | Lectura | Nombres o ids; si un nombre es ambiguo, el error pide preguntar al usuario. |
| `ver_clima` | Lectura | Una sola consulta de pronóstico (Open-Meteo) para todos los partidos del día; las canchas techadas no sufren la lluvia. |
| `proponer_reprogramacion` | Cálculo | Solo propone; la propuesta se guarda en el servidor (`PropuestaAgente`) y el modelo recibe un id. |
| `aplicar_reprogramacion`, `enviar_notificacion` | Escritura | **No ejecutan**: crean una `AccionPendiente`. |

Reglas: mismos permisos de la persona (ADMIN/ORGANIZADOR); parámetros validados con serializers (el JSON Schema se genera del mismo serializer); sin SQL libre; máximo 5 vueltas y 8 herramientas por petición; 60 s por petición; 20 mensajes/min y 60/hora por usuario; todo a la bitácora (acción `AGENTE`, sin secretos). El texto que viene de la base se limpia (sin saltos ni caracteres de control, acotado) y se entrega como dato, con instrucción de no obedecerlo.

## 13.4 Optimizador en modo reparación (`fixture/services/reparacion.py`)
Reubica solo los partidos afectados con CP-SAT + puntaje del Random Forest:
* Duras: sin solape de cancha ni de equipo (también entre los partidos que se mueven a la vez), descanso mínimo de 24 h del equipo, franjas y bloqueos de la cancha, restricciones de facultad, partidos que no se mueven (de cualquier campeonato), antelación mínima de 2 h.
* Clima: descarta horarios al aire libre con riesgo ALTO/CRÍTICO; si no hay pronóstico lo dice y penaliza esa opción.
* Preferencias (en orden): colocar todos, moverlos lo mínimo (días de diferencia y luego hora del día: «mismo horario otro día» gana a «la mañana siguiente»), conservar la cancha, puntaje del modelo.
* Si no cabe un partido, devuelve el motivo en vez de inventar un horario.

## 13.5 Acciones pendientes (`acciones.py`)
Estados `PENDIENTE → CONFIRMADA | CANCELADA | EXPIRADA | FALLIDA`. Vigencia 30 min (`AGENTE_ACCION_MINUTOS`), tarea Celery cada 10 min. Al confirmar: bloqueo de la fila (dos clics no ejecutan dos veces), **revalidación completa contra el calendario real** (si otro organizador movió un partido o se ocupó la cancha → `FALLIDA`, no se aplica nada), aplicación en dos fases para permitir intercambios de cancha, bitácora por partido y avisos a los delegados al terminar. Solo la persona dueña de la acción puede confirmarla o cancelarla.

## 13.6 Evaluación (F7-04) — `python manage.py evaluar_agente`
18 escenarios sobre un calendario sintético (se descarta con *rollback*) y el LLM real: lectura, clima, predicción, reporte, reprogramación, avisos, ambigüedad y seguridad (fuera de tema, «borra todos los partidos», aviso de phishing con enlace). Mide aciertos, vueltas al modelo, tiempo y el invariante central: **el calendario no cambia nunca sin confirmación**.
* Corrida completa tras aislar el mundo y afinar el prompt: **15/18 (83 %)**, 2,1 vueltas y 22,5 s en promedio, calendario intacto en 18/18, rechazos por permiso correctos.
* Los 3 fallos eran de la herramienta y del prompt, no del modelo: el resultado de `proponer_reprogramacion` incluía «si está de acuerdo, llama a aplicar…» y el agente se detenía a preguntar; la descripción de `todos` en `enviar_notificacion` era ambigua; y una validación mía exigía un «?». Se corrigieron y los escenarios A1 (el principal), A2, N1 y D1 se repitieron y pasaron.
* **No se pudo repetir la corrida completa**: el plan gratuito de Groq (8 000 tokens/min y un tope diario por modelo) se agotó tras varias evaluaciones. Los 18 escenarios pasaron entre la corrida completa y las repeticiones, pero no en una sola corrida final.
* Hallazgo operativo: cada petición consume ~1 400 tokens solo en definiciones; con el plan gratuito una conversación larga espera por el límite por minuto (el cliente espera hasta 25 s y reintenta). Para uso real continuo se necesita el plan de pago de Groq.

## 13.7 API y pantallas
* `GET /agente/estado/`, `GET /agente/conversaciones/`, `GET|DELETE /agente/conversaciones/<id>/`, `POST /agente/mensajes/`, `GET /agente/acciones/<id>/`, `POST /agente/acciones/<id>/confirmar|cancelar/`.
* UI en `/gestion/asistente`: pestaña **Agente** (conversación, pasos consultados, botones de descarga, tarjeta de propuesta con Confirmar/Cancelar, historial, voz) y **Consultas rápidas** (el asistente de la Fase 6).
* Migraciones: `agente.0001`, `auditoria.0004` (acción `AGENTE`). Variables: `AGENTE_PROVIDER`, `AGENTE_MODEL`, `AGENTE_MAX_PASOS`, `AGENTE_MAX_HERRAMIENTAS`, `AGENTE_TIMEOUT_SEG`, `AGENTE_MENSAJES_HORA`, `AGENTE_ACCION_MINUTOS`, `AGENTE_ANTELACION_HORAS`.

## 13.8 Verificación y límites
* Backend: 1 018 pruebas (62 del agente, con LLM guionado); `makemigrations --check` limpio. Frontend: `lint`, `tsc` y `build` correctos. E2E en Chrome: propuesta → sin cambios antes de confirmar → confirmar → partidos movidos; aviso → cancelar; historial; móvil sin scroll horizontal.
* Límites: solo Groq; el aviso a delegados requiere que los equipos tengan delegado con cuenta; no hay aún `aplicar` para cancelar o suspender partidos (solo reubicar y avisar).

---

# 14. Fase 7-B — Planilla móvil sin conexión (PWA)

## 14.1 Qué es y quién la usa
La misma aplicación web, instalable en el celular (PWA), con una **planilla digital** para registrar goles, tarjetas y el resultado en la cancha, aunque no haya señal. No es una app nativa ni tiene rol nuevo: la usan **Organizador, Administrador y Superadministrador** (quienes ya registran resultados e incidencias). El Delegado no entra (la ruta `/planilla` exige rol de gestión y la API sigue aplicando sus propios permisos).

## 14.2 Diseño
* **Sesión:** el mismo login de siempre (cookies httpOnly). La sesión dura 7 días y el acceso se renueva solo con señal. Sin red, la planilla sigue con la última sesión conocida en ese celular (solo `id`, nombre y rol); la seguridad real continúa en la API.
* **Esqueleto sin conexión (`public/sw.js`):** guarda solo scripts, estilos, fuentes, íconos y el HTML de `/planilla`. **Nunca** guarda `/api/` ni datos de personas. `/planilla` es una página estática con vistas internas (lista, partido, pendientes) que no necesitan red para navegar.
* **Datos sin conexión (IndexedDB, `lib/offline/db.ts`):** el paquete de partidos de hoy y mañana (con plantillas y lo ya registrado), la cola de acciones y el cronómetro de cada partido. El paquete es de una sola cuenta y se borra al cerrar sesión; la cola solo guarda ids y minutos.
* **Paquete (`GET /fixture/planilla/paquete/`):** una consulta con partidos programados de campeonatos en curso, ambos equipos, jugadores activos (marca a los **sancionados**: el sistema no les permite incidencias) e incidencias existentes.
* **Cola y sincronizador (`lib/offline/sincronizador.ts`):** cada acción se guarda primero en el celular y se envía en orden con su propia `Idempotency-Key`. Hay **5 s para deshacer** antes de enviarla. Sin red, 5xx o 429: se reintenta sola (al volver la red, al abrir la app y cada 30 s). 401: se pausa y pide iniciar sesión, sin perder nada. 409: **conflicto**. Otro 4xx: **rechazada**, con el motivo. Un candado entre pestañas evita envíos dobles.
* **Orden y coherencia:** las incidencias salen antes que el resultado, porque el servidor exige que el marcador coincida con los goles. El marcador de la planilla se calcula de los goles anotados.

## 14.3 Idempotencia (`apps/fixture/idempotencia.py`, modelo `OperacionIdempotente`)
* `POST` de incidencia y de resultado aceptan la cabecera `Idempotency-Key` (8–64 caracteres). Sin cabecera, todo funciona como antes.
* Misma clave y mismo contenido: se devuelve la respuesta guardada (`Idempotent-Replayed: true`) sin volver a ejecutar. Misma clave con otro contenido o ruta: 422. La clave es por usuario.
* El registro de la clave y la operación comparten transacción: solo se guardan las operaciones **exitosas**; si fallan, la clave queda libre. Dos envíos simultáneos con la misma clave crean una sola incidencia (índice único de PostgreSQL; probado con hilos).
* Purga diaria de claves de más de 7 días (`fixture.purgar_operaciones_idempotentes`).
* **Conflicto:** `POST` de resultado en un partido que ya lo tiene responde ahora **409** (antes 400), para que la planilla distinga «otra persona ya cerró el partido» de «dato inválido». No se sobrescribe nada; la acción queda en «Por revisar» con un mensaje en lenguaje claro.

## 14.4 Pantallas
`/planilla` (pantalla completa, sin barra lateral): cabecera con indicador permanente (Sincronizado / Sin conexión · N / N por enviar / N por revisar / Inicia sesión) e instalación; lista de partidos; planilla del partido (marcador, cronómetro, plantillas con insignias de goles y tarjetas, cronología con estado de envío, «Anotar otro suceso», «Finalizar partido» con penales en eliminación directa); y «Pendientes» (reintentar, descartar, sincronizar). Cerrar sesión con pendientes avisa que no se pierden. Acceso desde el menú («Planilla móvil») y desde el inicio del panel.
El **login** se rediseñó (escudo, panel institucional con funciones, formulario con ver/ocultar contraseña y aviso de mayúsculas, enlace a la parte pública).

## 14.5 Verificación
* Backend: 1 043 pruebas (19 nuevas de idempotencia, conflicto 409, hilos simultáneos, purga y paquete); `makemigrations --check` y `pyflakes` limpios. Migración `fixture.0006`.
* Frontend: `lint`, `tsc` y `build` correctos.
* E2E en Chrome sobre el **build de producción** (puerto 3001), 32 comprobaciones: manifest instalable; service worker activo con `/planilla` guardada; la app **abre y funciona sin conexión**; **5 incidencias sin red, persistentes tras recargar, y sincronizadas sin duplicados** al volver la red (el servidor tenía 0 antes y exactamente 5 después); deshacer; repetición de una clave a través del proxy sin duplicar; finalizar con resultado 2-1; **conflicto** al cerrar otra persona el partido (no se sobrescribe; se puede descartar); cierre de sesión con pendientes; el delegado es redirigido.
* Límites: instalar en un celular real requiere **HTTPS** (en `localhost` funciona sin él). En iPhone (Safari) no hay sincronización en segundo plano: se sincroniza al abrir la app o al volver la red. No se guarda la hora exacta del suceso, solo el minuto marcado. La planilla no cambia el estado del partido a «en curso»; solo registra incidencias y el resultado.

---

# 15. Fase 7-C — Análisis avanzado, panel del jugador, seed realista y paneles inteligentes

## 15.1 F7-07 — Niveles de equipos y siembra (K-means)
`POST /ml/cabezas-de-serie/ {campeonato_id, grupos?}` (`apps/ml/services/niveles.py`).
* Cada equipo se describe con su rendimiento **real** en el mismo deporte (todos los campeonatos finalizados, sin walkover): puntos por partido, diferencia de goles por partido y forma de los últimos 5. K-means (semilla fija, `k` entre 2 y 4 según la **silueta**) los agrupa en niveles; el nivel 1 es el más fuerte. Un índice de fuerza (0–100) ordena dentro de cada nivel.
* Resultado: niveles, **orden de siembra**, **cabezas de serie** y **grupos equilibrados** con reparto en serpiente (con la diferencia máxima de fuerza entre grupos).
* Honestidad: con menos de 4 equipos con 3 o más partidos **no se inventa un orden**: se conserva el de inscripción y se explica por qué. Un equipo sin historial se siembra al final y se marca. Es determinista y no modifica nada.
* Integración: `POST /fixture/generar/` acepta `sembrar_con_ml` (eliminación directa). La llave se arma con ese orden (1 vs último, etc.) y la respuesta incluye la `siembra`. En la pantalla: casilla «Sembrar la llave con IA» (marcada) y, al terminar, el orden obtenido.
* UI: Inteligencia artificial → «Niveles y siembra» (niveles, barras de fuerza, tabla de siembra y grupos).

## 15.2 F7-08 — Resultados atípicos (Isolation Forest)
`GET /ml/atipicos/`, `POST /ml/atipicos/` (buscar ahora, solo administración), `POST /ml/atipicos/<id>/revisar/` (`apps/ml/services/atipicos.py`, modelo `ml.ResultadoAtipico`).
* Por deporte (mínimo 20 partidos), el Isolation Forest aprende cómo son los marcadores habituales (goles totales, diferencia, goles de cada lado). Para evitar falsas alarmas, un marcador solo se reporta si **además** se desvía de forma clara en términos simples (z robusto con mediana y MAD ≥ 3,5) y la alerta **explica por qué** («9 goles en total; lo habitual es 2»). Un 3-3 no es atípico; un 9-0 sí.
* Una alerta por partido (idempotente). La tarea `ml.revisar_resultados_atipicos` (cada hora) avisa a la administración solo de las nuevas. La revisión es siempre humana: nada se corrige solo.

## 15.3 F7-09 — Experimento de red neuronal
`python manage.py experimento_red_neuronal --salida docs/EXPERIMENTO_RED_NEURONAL.md` compara un `MLPClassifier` regularizado y calibrado con el Random Forest y las líneas base, con el mismo dataset «a la fecha» y la misma validación walk-forward. Con los datos de ejemplo (112 partidos) **la red neuronal es peor** (log-loss 1,79 frente a 1,04 de Elo) y el Random Forest tampoco supera a Elo: con tan poco historial los modelos simples ganan, y el sistema **sigue usando Elo** hasta que el Random Forest demuestre mejorarlo. La decisión D11 se mantiene. Informe en `docs/EXPERIMENTO_RED_NEURONAL.md`.

## 15.4 F7-10 — Panel del jugador con cuenta
El rol `JUGADOR` deja de ser «reservado»: ahora tiene **solo lectura de su propia ficha**. `GET /deportes/mi-ficha/` devuelve sus fichas (vinculadas por `FichaJugador.usuario`): equipo, número y posición, goles y tarjetas, **sanción vigente**, próximos partidos y últimos resultados de su equipo. No tiene ningún otro permiso (la matriz de permisos lo verifica). Pantalla `/jugador`; un jugador sin ficha vinculada ve cómo pedirla a su delegado.

## 15.5 Seed realista de la UAGRM (`seed_realista`, reemplaza a `seed_demo`)
Ver `docs/DATOS_DE_PRUEBA.md`. Crea 12 facultades, 4 deportes, 3 instalaciones con 7 canchas, ~560 jugadores en 44 equipos, las temporadas 2025 de Fútbol y Futsal (simuladas, declaradas como tales), un Fútbol 2026 en curso **cuyo fixture genera el propio optimizador**, una copa de eliminación lista para sembrar, inscripciones en todos los estados, quejas, cuentas de todos los roles, y entrena los modelos. Es repetible y solo corre con `DEBUG=True`.

## 15.6 Paneles inteligentes
* **Inicio de gestión:** acciones sugeridas por la IA (clima, quejas, inscripciones, fixtures pendientes), «Hoy en la cancha» con acceso a la planilla móvil y resumen de la temporada (avance, goles, reparto de resultados, goleadores y clasificación con gráficos SVG accesibles).
* **Inicio del delegado:** tarjeta destacada con el próximo partido y cuenta regresiva.
* **Inteligencia artificial:** ahora en pestañas (Modelos, Predicciones, Niveles y siembra, Resultados atípicos).
* Se corrigió una consulta innecesaria (`/campeonatos/0/`) en la pantalla de Fixture, y se verificó que no haya emojis en la interfaz (solo íconos).

## 15.7 Verificación
Migraciones nuevas: `ml.0006`, `users.0006` (solo etiqueta del rol). Recorrido automático en Chrome con cada rol (público, administrador, organizador, delegado, jugador, jugador sancionado, superadministrador y celular): todas las pantallas cargan sin errores de API ni de JavaScript y sin emojis; las rutas protegidas redirigen según el rol.
Límites: los datos de 2025 son simulados; con ese historial el predictor aún no supera a Elo (es el comportamiento correcto y se explica en pantalla).

## 15.8 Resultado de la verificación final (Fase 7-C)
* Backend: **1 096 pruebas** correctas (nuevas: 17 de niveles/atípicos, 4 del panel del jugador, 9 del seed, y ajustes de la matriz de permisos); `pyflakes` y `makemigrations --check` limpios.
* Frontend: `lint`, `tsc` y `build` de producción correctos.
* Recorrido automático en Chrome por rol sobre los datos del seed: 0 problemas de navegación, sin errores de API ni de JavaScript, sin emojis y sin desbordamiento horizontal en el celular.
* Hallazgos corregidos durante la verificación: el endpoint `/me/` no admitía al rol jugador (su panel no cargaba), tarjetas en cuadrículas sin `min-w-0` que desbordaban en pantallas angostas, una consulta `GET /campeonatos/0/` innecesaria, la tilde de «Eliminación directa» y la contaminación entre pruebas del seed (ahora se ejecuta dentro de una transacción que se revierte).
