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
- No resetear la base de desarrollo sin avisar: usar `seed_demo` solo cuando se confirme que no hay datos reales.

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

**F1-01 se divide:** *01a* = backend (roles, permisos, migración de datos, tests); *01b* = frontend mínimo (tipos y hook `useAuth` con los roles nuevos).

**Coincidencia útil:** el documento ya incluye `bloqueado_hasta` e `intentos_fallidos` en `usuarios_usuario` (idénticos a lo hecho en F0-04).
