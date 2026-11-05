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
| F0-05b Eventos de usuarios | ✅ | Login, bloqueo, logout, cambio de contraseña y CRUD administrativo auditados; mensajes 429 localizados con `ThrottledES` |
| F0-05c Eventos del núcleo y 403 | ✅ | Campeonato, fixture, resultados, incidencias, exportaciones y predicciones/entrenamiento auditados; 403 autenticados registrados |
| F0-06 Invalidar tokens al cambiar contraseña | ✅ | Pone en lista negra todos los refresh previos y devuelve un par nuevo; cubierto por pruebas de refresh antiguo y nuevo |
| F0-07 Argon2 | ✅ | Hash Argon2 preferido y PBKDF2 conservado para compatibilidad; login migra hashes antiguos; probado con `PASSWORD_HASHERS` explícito |
| F0-08 Predictor | ✅ | `Q` importado y usado en el historial cara a cara; imports ML sin uso eliminados; entrenamiento cubierto con partidos finalizados |
| F0-09 Refresh token rotado | ✅ | Refresh single-flight comparte la petición; guarda access y refresh rotados, cierra sesión si falla y muestra el detalle 429 en login |
| F0-10 Configuración | ✅ | `.env` no versionado; producción fuerza `DEBUG=False`, hosts/CORS desde entorno y cookies seguras; variables de login y proxy documentadas |

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
