# Plan de trabajo DUBSS — Fases de implementación (para ejecutar con Copilot)

> Proyecto: Sistema Inteligente de Gestión Deportiva y Programación Automática de Encuentros (DUBSS, UAGRM).
> Base: código `DUBSS-GESTION-DEPORTIVA` (Django 5 + DRF + PostgreSQL / Next.js 14) y documento `Sistema_deportivo_para_la_DUBSS.docx`.
> Fecha de este plan: 23/10/2026. Hito de control H4 (sistema funcional): **21/11/2026**.

---

## 0. Cómo usar este documento con Copilot

1. Trabajar **en orden**. Cada tarea tiene un ID (`F0-01`, `F1-03`…). No empezar una fase sin cerrar la anterior (salvo las marcadas como "en paralelo").
2. **Una tarea = un commit/PR pequeño**, con sus migraciones y sus tests.
3. Prompt base para pegar en Copilot Chat:

   ```
   Lee docs/PLAN_FASES_DUBSS.md y las secciones "Decisiones tomadas" y "Reglas para Copilot".
   Ejecuta SOLO la tarea <ID>. No modifiques nada fuera de los archivos indicados
   salvo que sea imprescindible, y explica qué cambiaste. Incluye tests y migraciones.
   ```
4. Al terminar cada tarea marcar `[x]` y correr: `python manage.py makemigrations --check`, los tests del backend y `npm run lint && npm run build` en el frontend.

---

## 1. Decisiones tomadas (NO cambiar sin consultar)

| #   | Decisión                                                                                                                                                                                                                                                                 |
| --- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| D1  | **Roles con login (4), iguales al documento:** `SUPERADMIN`, `ADMIN_DUBSS`, `ORGANIZADOR`, `DELEGADO`. Los diagramas del documento no se rehacen: el código se adapta al documento.                                                                        |
| D2  | **Jugador = solo ficha** (sin cuenta de usuario por ahora). El acceso con cuenta para jugador (RF1/RF20) queda para una fase posterior.                                                                                                                             |
| D3  | **Espectador = visitante anónimo** (sin cuenta). Es la vista pública (RF19 / RNF08).                                                                                                                                                                              |
| D4  | **Se elimina el rol `ARBITRO`.** El documento no lo define; quien registra resultados e incidencias es el `ORGANIZADOR` (RF12, RF14). `Partido.arbitro` queda como dato opcional sin permisos.                                                                |
| D5  | **Se eliminan `COORDINADOR`, `DEPORTISTA` y `PUBLICO`.** Mapeo: `COORDINADOR→DELEGADO`, `ARBITRO→ORGANIZADOR`, `DEPORTISTA/PUBLICO→` cuenta desactivada (la ficha del jugador se conserva).                                                          |
| D6  | **Se cierra el registro público.** Las cuentas las crea el Administrador (RF2). `rol` y `facultad` nunca se aceptan desde un endpoint que use el propio usuario.                                                                                               |
| D7  | **Un equipo se reutiliza entre campeonatos.** `Equipo` ya no depende de `Campeonato`; la participación es la entidad `Inscripcion` (en el documento: `CampeonatoEquipo`).                                                                                  |
| D8  | **La seguridad real vive en la API.** Ocultar menús o rutas en el frontend es solo experiencia de usuario.                                                                                                                                                         |
| D9  | **Random Forest no "genera" el fixture solo.** Enfoque híbrido: un optimizador (OR-Tools CP-SAT) genera candidatos y Random Forest puntúa la calidad de cada asignación (`MuestraAsignacion` del documento). Random Forest también predice resultados (RF15). |
| D10 | **No se parte en microservicios.** Monolito modular Django. Si hace falta, un único servicio extra de IA (Whisper/LLM local) como contenedor aparte.                                                                                                               |
| D11 | **TensorFlow/PyTorch no son necesarios** para el núcleo. Solo un experimento opcional documentado (F7-09).                                                                                                                                                         |

---

## 2. Reglas para Copilot (convenciones del proyecto)

**Backend**

- Python/Django, nombres de modelos y campos **en español**, como el código existente.
- Los roles se consultan **solo mediante helpers** (`apps/users/roles.py`: `es_superadmin(u)`, `es_admin(u)`, `es_organizador(u)`, `es_delegado(u)`), nunca comparando strings sueltos. Así el renombre de roles es un único cambio.
- **Nunca** exponer `rol`, `is_staff`, `is_superuser`, `facultad` como campos escribibles en serializers de uso propio (registro/perfil).
- Toda vista nueva declara `permission_classes` explícitos. Prohibido dejar el valor por defecto en endpoints que escriben.
- Las validaciones de negocio van en **serializers/servicios** (no solo en `Model.clean()`, que DRF no invoca) y, cuando sea posible, también como **constraints de base de datos**.
- Toda acción crítica llama a `auditoria.registrar(...)` (ver F0-05).
- Lógica de negocio en `services/` (módulos puros, testeables); las vistas solo orquestan.
- Sin `GET` que escriban en la base de datos.
- Fechas siempre **timezone-aware** (`timezone.make_aware`, `USE_TZ=True`).

**Frontend**

- Next.js 14 (App Router) + TypeScript + Tailwind + React Query.
- **Prohibido** agregar `style={{ ... }}` nuevos y `alert()`. Usar componentes de `components/ui/` y toasts.
- Todas las llamadas a la API pasan por `lib/api/services.ts` y hooks de React Query; nunca `fetch`/`axios` suelto en una página.
- Formularios con `react-hook-form` + `zod`.
- URLs de la API desde `NEXT_PUBLIC_API_URL`; **nunca** `http://localhost:8000` escrito a mano.

**General**

- No subir `.env` ni secretos. Solo `.env.example`.
- Mensajes de error descriptivos para el usuario (RNF09).
- Cada tarea incluye tests; no se mezcla refactor con funcionalidad nueva en el mismo commit.

---

## 3. Definición de "terminado" para un requisito funcional (RF)

Un RF se marca terminado **solo si** cumple todo:

1. Modelo y migración en base de datos.
2. Endpoint(s) de API con serializer y validaciones.
3. Permisos por rol (y por objeto/facultad cuando aplique) con test.
4. Pantalla en el frontend para los roles que lo usan.
5. Registro en bitácora de las acciones críticas.
6. Tests automáticos (unitarios + API) en verde.
7. Aparece correctamente en Swagger (`drf-spectacular`).

---

## 4. Cronograma resumen

| Fase         | Nombre                                                       | Fechas                     | Cierra principalmente                      |
| ------------ | ------------------------------------------------------------ | -------------------------- | ------------------------------------------ |
| F0           | Seguridad y errores críticos                                | 23–27 oct                 | RF1, RF18, base RF2/RF20, RNF15, RNF17–19 |
| F1           | Datos y roles                                                | 28 oct – 6 nov            | Modelos RF2–RF8, RF21                     |
| F2           | Permisos por rol/objeto y pruebas                            | 3–10 nov                  | RF2, RF6, RF7, RF12, RF20, RNF16           |
| F3           | Núcleo deportivo                                            | 5–14 nov                  | RF8–RF14                                  |
| F4           | Frontend: base de diseño (**en paralelo con F1–F3**) | 3–10 nov                  | RNF06, RNF07, RNF09, RNF12, RF17           |
| F5           | Frontend: paneles por rol                                    | 10–21 nov                 | RF3–RF7, RF9, RF14, RF16, RF19–RF21      |
| F5b          | RF11 con ML (versión mínima)                               | 14–21 nov (si hay tiempo) | RF11                                       |
| **H4** | **Prueba completa por rol**                            | **21 nov**           | RF1–RF21 base                             |
| F6           | IA central y automatización                                 | 24 nov – 20 dic           | RF11, RF15, RF16 (avanzado), RF22, RF25    |
| F7           | Agente, móvil y experimentos                                | ene – feb                 | RF23, RF24                                 |
| F8           | Calidad, despliegue y documento                              | mar – abr                 | RNF01–05, 10, 13, 14, 20–27, OE5         |

---

# FASE 0 — Seguridad y errores críticos (23–27 oct)

**Objetivo:** cerrar los agujeros que permiten escalar privilegios y los errores que rompen funciones ya implementadas. Esta fase usa los **nombres de rol actuales**; los helpers de `roles.py` hacen que F1 sea un cambio de una sola línea.

- [ ] **F0-01 — Helpers de rol.** Crear `backend/apps/users/roles.py` con `es_admin(user)`, `es_organizador(user)`, `es_delegado(user)`, `es_superadmin(user)` (hoy: admin = `ADMIN_DUBSS` o `is_superuser`; organizador = `COORDINADOR`; delegado = `COORDINADOR`). Reemplazar las comparaciones de strings en `users/permissions.py` y vistas por estos helpers.
  *Aceptación:* `grep -rn "Rol\.\|rol ==" backend/apps` solo aparece en `roles.py` y en el modelo.
- [ ] **F0-02 — Cerrar escalada de rol en registro (crítico).** `users/serializers.py`: quitar `rol` de `UsuarioRegistroSerializer.fields`. `users/views/auth_views.py`: `RegistroView` deja de ser `AllowAny`; solo `ADMIN_DUBSS`/superusuario puede crear cuentas (D6). El rol se asigna únicamente desde un serializer de administración (`UsuarioAdminSerializer`).
  *Aceptación:* test — un anónimo recibe 401/403 en el registro; un admin crea un usuario con rol; un usuario normal no puede.
- [ ] **F0-03 — Cerrar escalada de rol en perfil (crítico).** `users/serializers.py`: en el serializer usado por `MiPerfilView`, agregar `rol`, `facultad`, `is_active` a `read_only_fields`. Crear `UsuarioAdminSerializer` (escribible) solo para vistas de administración.
  *Aceptación:* test — `PATCH /api/auth/perfil/ {"rol":"ADMIN_DUBSS"}` no cambia el rol (el valor se ignora o devuelve 400).
- [ ] **F0-04 — Bloqueo por intentos fallidos (RNF18).** Agregar a `Usuario`: `intentos_fallidos` (int, default 0) y `bloqueado_hasta` (datetime null). Serializer de login propio (subclase de `TokenObtainPairSerializer`): al 5.º intento fallido consecutivo, `bloqueado_hasta = ahora + 15 min`; mientras esté bloqueado responder **429** con mensaje descriptivo (“Cuenta bloqueada temporalmente hasta HH:MM”); un login correcto reinicia el contador. Agregar throttle DRF al login (`10/min` por IP).
  *Aceptación:* tests — 5 fallos bloquean 15 min; el correcto no entra durante el bloqueo; tras el plazo entra; contador se reinicia.
- [ ] **F0-05 — Bitácora operativa (RF18, RNF19).** Crear app `backend/apps/auditoria/` con modelo `Bitacora(usuario null, accion, entidad, entidad_id, detalle JSON, ip, resultado [OK|DENEGADO|ERROR], fecha)` y función `registrar(request_o_usuario, accion, entidad=None, entidad_id=None, detalle=None, resultado="OK")`. Migrar los datos del `Bitacora` actual de la app `ml` (o eliminarlo si está vacío) y mover su vista de consulta (solo `ADMIN_DUBSS`/`SUPERADMIN`). Llamar `registrar` en: login OK/fallido/bloqueo, logout, cambio de contraseña, creación/edición/baja de usuarios, **cambio de rol**, cambio de estado de campeonato, generar/eliminar fixture, registrar/corregir resultado, registrar incidencia. Agregar un *exception handler* DRF que registre cada `403` como `DENEGADO` (accesos no autorizados, ver 6.1 del documento).
  *Aceptación:* tests que verifican una fila de bitácora por cada acción listada y por un 403.
- [ ] **F0-06 — Invalidar tokens al cambiar contraseña.** `users/views/auth_views.py` (`CambioPasswordView`): al cambiar la contraseña, poner en lista negra todos los `OutstandingToken` del usuario (app `token_blacklist`) y devolver tokens nuevos.
  *Aceptación:* test — el refresh anterior deja de funcionar tras el cambio.
- [ ] **F0-07 — Hash Argon2 (RNF15).** Agregar `argon2-cffi` a `requirements.txt`; en `config/settings/base.py` definir `PASSWORD_HASHERS` con `Argon2PasswordHasher` primero y `PBKDF2PasswordHasher` después (los hashes viejos se actualizan al iniciar sesión).
  *Aceptación:* test — una contraseña nueva queda guardada con prefijo `argon2$`.
- [ ] **F0-08 — Arreglar el predictor roto.** `ml/services/predictor.py` líneas ~58–59 usan `models.Q` sin importar `models`. Importar `from django.db.models import Q` al inicio y reemplazar `models.Q` por `Q`. (La corrección de fondo —fuga de datos, validación— es F6-01.)
  *Aceptación:* `python -m pyflakes backend/apps` sin “undefined name”; test que ejecuta `entrenar()` con datos de prueba sin excepción.
- [ ] **F0-09 — Refresh token rotado en el frontend.** `frontend/lib/api/client.ts`: el backend rota y bloquea el refresh anterior (`ROTATE_REFRESH_TOKENS` + `BLACKLIST_AFTER_ROTATION`), pero el interceptor ignora el `refresh` nuevo. Guardar `data.refresh` además de `data.access`. Implementar *single-flight* (una sola petición de refresh compartida por todas las peticiones que reciben 401 a la vez); si el refresh falla, cerrar sesión y redirigir a `/login`.
  *Aceptación:* con 3 peticiones simultáneas expiradas, solo se hace 1 refresh y la sesión sigue activa tras 2 refrescos consecutivos.
- [ ] **F0-10 — Higiene de configuración.** Excluir `.env` del zip/repositorio (`.gitignore` ya lo tiene; verificar que no está versionado). `config/settings/production.py`: `DEBUG=False`, `ALLOWED_HOSTS` desde entorno, CORS restringido, cookies `Secure`. Ejecutar `python manage.py check --deploy` y corregir advertencias.
  *Aceptación:* `check --deploy` sin errores críticos.

**Salida de F0:** nadie puede ascender de rol; hay bloqueo, bitácora y Argon2; el predictor no lanza `NameError`; la sesión del frontend no se cae al refrescar.

---

# FASE 1 — Datos y roles (28 oct – 6 nov)

**Objetivo:** dejar el modelo de datos igual a los diagramas del documento (Cap. 7) y sin redundancia. **Antes de cada modelo, contrastar con el diagrama de clases / tabla de datos del documento; si difieren, manda el documento.**

> Si ya hay datos reales cargados: escribir migraciones de datos. Si no: se puede resetear la base y usar `seed_demo` (F1-12).

- [ ] **F1-01 — Roles finales (D1, D5).** `users/models.py`: `Rol` = `SUPERADMIN`, `ADMIN_DUBSS`, `ORGANIZADOR`, `DELEGADO`. Migración de datos: `COORDINADOR→DELEGADO`, `ARBITRO→ORGANIZADOR`, `DEPORTISTA`/`PUBLICO` → `is_active=False`. Actualizar `roles.py` y `users/permissions.py` (eliminar `EsArbitroOAdmin`, `EsLecturaPublica` mal usado, `EsDeportistaPropioOAdmin`). Crear: `EsSuperadmin`, `EsAdmin` (incluye superadmin), `EsAdminUOrganizador`, `EsDelegado`.
  *Aceptación:* no queda ninguna referencia a `COORDINADOR`, `ARBITRO`, `DEPORTISTA`, `PUBLICO` en backend ni frontend.
- [ ] **F1-02 — Modelo `Facultad`.** Nueva tabla `Facultad(nombre único, sigla, activo)` en `deportes` (o app de recursos). `Usuario.facultad` pasa de texto a `ForeignKey(Facultad, null=True)`; **obligatoria si rol = DELEGADO** (validar en serializer). Migrar el texto existente a filas de `Facultad` (normalizar mayúsculas/espacios).
  *Aceptación:* no hay campo `facultad` de texto libre en `Usuario` ni en `Equipo`.
- [ ] **F1-03 — `Equipo` reutilizable (D7).** `deportes/models.py`: quitar `Equipo.campeonato`; agregar `facultad` (FK), `categoria` (FK; el deporte se deriva de la categoría), `delegado` (FK a `Usuario`, rol DELEGADO de esa facultad). Constraint único `(facultad, categoria, nombre)`.
  *Aceptación:* un mismo equipo puede participar en 2 campeonatos sin duplicar sus datos.
- [ ] **F1-04 — `Inscripcion` (documento: `CampeonatoEquipo`).** `Inscripcion(campeonato, equipo, estado [PENDIENTE|APROBADA|RECHAZADA], fecha_solicitud, validado_por null, fecha_validacion null, observaciones)`; constraint único `(campeonato, equipo)`. `Partido`, `TablaPosiciones` y cualquier referencia equipo-campeonato pasan a apoyarse en inscripciones aprobadas.
  *Aceptación:* no se puede programar un partido con un equipo sin inscripción `APROBADA` en ese campeonato.
- [ ] **F1-05 — `FichaJugador` sin cuenta obligatoria (D2).** `usuario` pasa a `OneToOneField(null=True, blank=True)`. Agregar: `nombre`, `apellido`, `carnet` (único), `registro_universitario`, `fecha_nacimiento`, `facultad` (FK), `partidos_sancion_restantes` (int, 0), `sancion_origen` (FK a `Incidencia`, null). Mantener `equipo` FK y `numero_camiseta` con constraint único `(equipo, numero_camiseta)`.
  *Aceptación:* un delegado puede crear una ficha sin crear un usuario.
- [ ] **F1-06 — `Campeonato` sin redundancia.** Quitar el FK `deporte` (se obtiene por `categoria.deporte`) o, si se mantiene, validar que coincida. Alinear `formato` con el documento: **`LIGA` (todos contra todos) y `ELIMINACION`** (quitar `GRUPOS` si no se implementará). Agregar `min_jugadores`, `max_jugadores`, `fecha_cierre_inscripcion`, `puntos_victoria/empate/derrota` (defaults 3/1/0).
  *Aceptación:* es imposible crear un campeonato con categoría de un deporte y deporte distinto.
- [ ] **F1-07 — `Deporte` y `Categoria` alineados (RF3, RF4).** Agregar `Deporte.cantidad_jugadores`. Revisar los campos de `Categoria` contra la tabla del documento (rango de edad, género, etc.) y corregir diferencias.
  *Aceptación:* campos de ambas tablas coinciden con el Cap. 7 del documento.
- [ ] **F1-08 — Instalaciones: disponibilidad y mantenimiento (RF5).** Agregar `HorarioCancha(cancha, dia_semana, hora_inicio, hora_fin)` (franjas habilitadas) y `BloqueoCancha.tipo [MANTENIMIENTO|EVENTO|OTRO]`. Una cancha solo es reservable dentro de sus franjas y fuera de bloqueos.
  *Aceptación:* servicio `canchas_disponibles(fecha_hora, duracion)` con tests.
- [ ] **F1-09 — Restricciones de participación (RF8).** Modelo `RestriccionHorarioFacultad(facultad, dia_semana, hora_inicio, hora_fin, motivo)` (para el optimizador) y servicio `validar_elegibilidad(ficha, inscripcion)` que devuelve motivos de rechazo: ficha duplicada en otro equipo del mismo campeonato, sanción vigente, equipo fuera de `min/max_jugadores`, inscripción cerrada (`fecha_cierre_inscripcion`).
  *Aceptación:* tests de cada motivo de rechazo.
- [ ] **F1-10 — Quejas y apelaciones (RF21).** Modelo `Queja(autor, tipo [QUEJA|APELACION], campeonato null, partido null, asunto, descripcion, estado [ABIERTA|EN_REVISION|RESUELTA|RECHAZADA], respuesta, resuelto_por null, fechas)`. API completa (permisos en F2-05).
  *Aceptación:* CRUD básico con tests.
- [ ] **F1-11 — Constraints de integridad en `Partido`.** `CheckConstraint(local != visitante)`, `UniqueConstraint(campeonato, local, visitante, jornada)`; agregar `duracion_min` (default 90) y `fecha_hora_fin`; **`ExclusionConstraint`** de PostgreSQL para que una misma cancha no tenga dos partidos solapados (requiere extensión `btree_gist`: migración `BtreeGistExtension`).
  *Aceptación:* test — insertar dos partidos solapados en la misma cancha lanza `IntegrityError`.
- [ ] **F1-12 — Datos de prueba.** Comando idempotente `python manage.py seed_demo`: facultades, un usuario por cada rol, deportes, categorías, instalaciones con horarios, equipos, fichas, un campeonato con inscripciones. Si más adelante se necesita historial para ML (F6), crear `seed_historial` que marque los datos como **sintéticos** (campo/flag) para poder excluirlos y declararlo en el documento.
  *Aceptación:* `seed_demo` se puede ejecutar dos veces sin duplicar.
- [ ] **F1-13 — Resultado vs. incidencias de gol.** Evitar dos fuentes de verdad: al registrar un resultado, si hay incidencias `GOL`, validar que la suma coincida con el marcador; o derivar el marcador de las incidencias. Documentar la regla elegida.
  *Aceptación:* test de coincidencia/discrepancia.

**Salida de F1:** `python manage.py makemigrations --check` limpio; el esquema coincide con el Cap. 7; no hay `facultad` en texto; equipos reutilizables; fichas sin cuenta.

---

# FASE 2 — Permisos por rol/objeto y pruebas base (3–10 nov)

**Objetivo:** que cada rol haga exactamente lo que el documento le asigna, y que eso esté protegido por tests.

**Matriz de permisos objetivo (sale de "Usuarios" e "Iniciador" de cada RF):**

| Recurso / RF                                   | SUPERADMIN | ADMIN_DUBSS | ORGANIZADOR   | DELEGADO                        | Anónimo |
| ---------------------------------------------- | ---------- | ----------- | ------------- | ------------------------------- | -------- |
| Usuarios y roles (RF2)                         | CRUD       | CRUD        | –            | –                              | –       |
| Bitácora (RF18)                               | leer       | leer        | –            | –                              | –       |
| Deportes, categorías, instalaciones (RF3–5)  | CRUD       | CRUD        | leer          | –                              | –       |
| Equipos y fichas (RF6–7)                      | todo       | todo        | leer          | CRUD **solo su facultad** | –       |
| Inscripciones (RF6/RF8)                        | todo       | validar     | validar       | crear/ver las de su facultad    | –       |
| Campeonatos, estados, fixture (RF9–11)        | todo       | todo        | todo          | leer                            | leer     |
| Partidos, resultados, incidencias (RF12, RF14) | todo       | todo        | todo (inicia) | leer                            | leer     |
| Tabla de posiciones (RF13)                     | leer       | leer        | leer          | leer                            | leer     |
| Predicciones (RF15)                            | todo       | todo        | todo          | consultar                       | –       |
| Reportes y PDF/Excel (RF16–17)                | todo       | todo        | todo          | –                              | –       |
| Quejas (RF21)                                  | todo       | resolver    | resolver      | crear/ver las propias           | –       |
| Notificaciones                                 | enviar     | enviar      | enviar        | –                              | –       |
| Perfil propio (RF20)                           | sí        | sí         | sí           | sí                             | –       |

- [ ] **F2-01 — Permisos DRF por rol.** Implementar en `users/permissions.py`: `EsSuperadmin`, `EsAdmin`, `EsAdminUOrganizador`, `EsDelegado`, `SoloLecturaPublica` (GET/HEAD/OPTIONS sin login), `DelegadoDeSuFacultad` (a nivel de objeto: `obj.facultad == user.facultad` o `obj.equipo.facultad == user.facultad`). Aplicar la matriz anterior a **todas** las vistas (`deportes`, `fixture`, `instalaciones`, `ml`, `reportes`, `notificaciones`, `users`).
  *Aceptación:* ninguna vista de escritura queda con permisos por defecto.
- [ ] **F2-02 — Filtrado de `queryset` por facultad.** Para `DELEGADO`: `get_queryset()` devuelve solo equipos, fichas e inscripciones de su facultad y solo las quejas propias. Para anónimos, solo datos públicos (campeonatos, partidos, resultados, tabla).
  *Aceptación:* test — un delegado de la facultad A no ve ni modifica datos de la B (404, no 403, para no revelar existencia).
- [ ] **F2-03 — Endpoints por rol.** `POST/GET/PATCH /api/usuarios/` (admin: crear cuenta, asignar rol, activar/desactivar, restablecer contraseña; bitácora en cada acción — RF2). `GET /api/mi-equipo/` (delegado), `GET /api/mis-quejas/`, `GET /api/me/` (rol + facultad + pantalla de inicio).
  *Aceptación:* Swagger documenta cada uno con ejemplos.
- [ ] **F2-04 — GET sin efectos secundarios.** Los endpoints de predicción/asistencia que hoy escriben en la base en un `GET` pasan a `POST` (o calculan sin persistir). Requieren autenticación (roles de RF15).
  *Aceptación:* test — un `GET` nunca crea ni modifica filas.
- [ ] **F2-05 — Permisos de `Queja`.** El delegado crea y ve las suyas; admin/organizador listan todas y resuelven (cambian estado y responden) con bitácora.
  *Aceptación:* tests por rol.
- [ ] **F2-06 — Reportes restringidos (RF16/17).** Solo `ADMIN_DUBSS`, `ORGANIZADOR`, `SUPERADMIN`. (La tabla de posiciones y el fixture ya son públicos como datos; los PDF/Excel de reportes no.)
- [ ] **F2-07 — Test de matriz de permisos.** Test parametrizado: para cada endpoint × rol (incluido anónimo) verificar el código HTTP esperado (200/201/204/401/403/404). Usar `pytest.mark.parametrize` o `APITestCase` según lo que ya use el proyecto.
  *Aceptación:* la matriz de arriba queda codificada y en verde.
- [ ] **F2-08 — Integración continua.** Workflow de GitHub Actions que ejecuta backend (tests + `makemigrations --check` + `pyflakes`) y frontend (`lint` + `build`) en cada PR. Medir cobertura con `coverage`; el umbral `--fail-under=70` (RNF26) se activa en F8.

**Salida de F2:** matriz de permisos con tests; ningún rol puede salirse de su alcance.

---

# FASE 3 — Núcleo deportivo (5–14 nov)

**Objetivo:** que un torneo completo funcione correctamente de punta a punta (RF8–RF14). Esta fase cierra los errores de lógica detectados.

- [ ] **F3-01 — Creación y estados de campeonato (RF9, RF10).** Validaciones: fechas coherentes, categoría activa, mínimo de equipos, `fecha_cierre_inscripcion` anterior al inicio. **Máquina de estados** con transiciones válidas (copiar la tabla de RF10 del documento; propuesta: `BORRADOR → INSCRIPCIONES → PROGRAMADO → EN_CURSO → FINALIZADO`, y `CANCELADO` desde cualquiera excepto `FINALIZADO`). Rechazar transiciones inválidas con 400 y registrar en bitácora.
  *Aceptación:* tests de cada transición válida e inválida.
- [ ] **F3-02 — Flujo de inscripciones (RF6/RF8).** Delegado solicita; admin/organizador aprueban o rechazan (con observación). Solo equipos con inscripción `APROBADA` entran al fixture. Al aprobar, ejecutar `validar_elegibilidad` (F1-09).
  *Aceptación:* test de punta a punta del flujo.
- [ ] **F3-03 — Generador de fixture robusto (RF11 base).** Reescribir `fixture/services/fixture_generator.py`:

  - Todo dentro de `transaction.atomic()`, **incluido el borrado previo**.
  - **No borrar partidos con resultado**: si existe algún partido `FINALIZADO`, solo permitir regenerar los pendientes (o devolver error claro).
  - Programar **en paralelo por cancha** usando `canchas_disponibles()` (horarios, bloqueos y partidos de **otros campeonatos**), sin pasar de medianoche.
  - **Sin bucle infinito**: límite de intentos y error descriptivo si no hay disponibilidad.
  - Fechas timezone-aware; equipo impar con descanso (BYE); opción `doble_vuelta`.
  - `generado_por_ml` queda en `False` hasta que el optimizador exista (F5b/F6). Eliminar el `try/except ImportError` que oculta el `FixtureOptimizer` inexistente.
    *Aceptación:* tests con 4, 5, 8 y 20 equipos: cero solapes por cancha, cero equipos jugando dos veces a la vez, 20 equipos en < 10 s (RNF04).
- [ ] **F3-04 — Formato eliminación directa.** Generar llaves con cabezas de serie (por defecto, orden de inscripción; más adelante clustering F7-07), `BYE` cuando no es potencia de 2, rondas posteriores como partidos "placeholder" enlazados (`ronda`, `partido_origen_local`, `partido_origen_visitante`). Al finalizar un partido el ganador avanza automáticamente. Empate → campos `penales_local/penales_visitante` en `Resultado`.
  *Aceptación:* test de un torneo de 6 equipos hasta la final.
- [ ] **F3-05 — Resultados corregibles (RF12).** `registrar_resultado` crea; `PATCH` permite **corregir** (admin/organizador) exigiendo `motivo` y registrando valores anterior/nuevo en bitácora. Soporte de `WALKOVER` (resultado administrativo configurable). Validación de coherencia con incidencias (F1-13). Quitar la restricción que rechaza resultados en partidos `FINALIZADO` para el caso de corrección autorizada.
  *Aceptación:* test — corregir un resultado deja la tabla correcta.
- [ ] **F3-06 — Tabla de posiciones recalculable (RF13).** `fixture/services/tabla.py::recalcular(campeonato)`: reconstruye toda la tabla desde los `Resultado` (idempotente), usando `puntos_victoria/empate/derrota` del campeonato. Desempate: puntos, diferencia de goles, goles a favor, enfrentamiento directo, nombre. Se invoca con `transaction.on_commit` tras registrar/corregir resultados (< 5 s, RNF03). Eliminar el método incremental `actualizar_con_resultado`.
  *Aceptación:* test — registrar, corregir y borrar un resultado produce siempre la misma tabla que recalcular desde cero.
- [ ] **F3-07 — Historial de posiciones (RF13).** Modelo `PosicionHistorial(campeonato, jornada, equipo, posicion, puntos, pj, gf, gc)`; se guarda un snapshot al cerrar cada jornada. Endpoint `GET /api/campeonatos/{id}/historial/`.
  *Aceptación:* test — evolución de posiciones por jornada.
- [ ] **F3-08 — Incidencias y sanciones (RF14, RF8).** Tipos `GOL`, `AMARILLA`, `ROJA`, `LESION`, `OTRO`; el jugador debe pertenecer al equipo local o visitante del partido. Una `ROJA` (o acumulación de amarillas configurable) asigna `partidos_sancion_restantes` a la ficha; al finalizar cada partido del equipo se descuenta. La elegibilidad (F1-09) bloquea alinear a un sancionado.
  *Aceptación:* test del ciclo roja → sanción → cumplimiento.
- [ ] **F3-09 — Programación manual y reprogramación.** `PATCH` de partido (fecha, cancha) validando disponibilidad, bloqueos y solapes; si falla, mensaje claro con el conflicto. Registra en bitácora y notifica a los delegados afectados.
  *Aceptación:* test — mover un partido a una cancha ocupada devuelve 409 con detalle.

**Salida de F3:** un campeonato completo (liga y eliminación) se crea, se inscribe, se programa, se juega, se corrige y se clasifica sin errores.

---

# FASE 4 — Frontend: base de diseño (3–10 nov, en paralelo con F1–F3)

**Objetivo:** tener las piezas reutilizables antes de construir muchas pantallas (RNF06, RNF07, RNF09, RNF12).

- [ ] **F4-01 — Tokens y Tailwind.** Definir paleta institucional, tipografía y espaciados en `tailwind.config.js` y `globals.css`. Regla: **no más `style={{}}`** en código nuevo.
- [ ] **F4-02 — Librería de componentes `components/ui/`.** `Button`, `Input`, `Select`, `Textarea`, `Checkbox`, `Card`, `Badge`, `Table` (con paginación y estado vacío), `Modal`, `ConfirmDialog`, `Tabs`, `Toast`, `Spinner`, `EmptyState`, `PageHeader`, `FormField`. Íconos con `lucide-react` (reemplaza los emojis).
  *Aceptación:* una página de ejemplo `/_ui` (solo desarrollo) muestra todos los componentes.
- [ ] **F4-03 — Capa de datos tipada.** Usar `lib/api/services.ts` (hoy sin uso) con funciones por recurso y hooks de React Query (`useCampeonatos`, `usePartidos`, …). Tipos TypeScript en `types/` alineados con los serializers. Cliente de API único que lee `NEXT_PUBLIC_API_URL`.
  *Aceptación:* ninguna página importa `axios`/`api` directamente.
- [ ] **F4-04 — Formularios y errores.** `react-hook-form` + `zod` (ya instalados) con un `FormField`. Mapear errores de DRF (400) a campos. Reemplazar todos los `alert()` por toasts con mensajes descriptivos (RNF09).
- [ ] **F4-05 — Sesión segura.** Los tokens salen de cookies legibles por JS y pasan a cookies `httpOnly` mediante route handlers de Next (`app/api/auth/login|refresh|logout/route.ts`) que actúan de proxy hacia Django. El `middleware.ts` decodifica el JWT (exp + rol) **solo para enrutar y redirigir** (la seguridad real es de la API, D8) y deja pasar las rutas públicas.
  *Aceptación:* `document.cookie` no muestra tokens; sesión sobrevive 2 refrescos.
- [ ] **F4-06 — Layout responsivo (RNF06).** Barra lateral colapsable y menú móvil; tablas con scroll horizontal; probar en 360 px, 768 px y 1280 px. Accesibilidad básica (foco visible, `aria-label`, contraste).
- [ ] **F4-07 — Configuración de roles.** Crear `lib/auth/roles.ts` con `ROLE_HOME` (pantalla de inicio por rol), `NAV_BY_ROLE` (menú por rol) y un componente `<RequireRole roles={[...]}>`; hook `useAuth` expone `rol`, `facultad`, `can(permiso)`.
- [ ] **F4-08 — Descargas autenticadas (RF17).** Botones de PDF/Excel que descargan vía cliente de API como `blob` (sin enlaces a `localhost`).

---

# FASE 5 — Frontend: paneles por rol (10–21 nov)

**Objetivo:** que cada rol complete sus casos de uso de punta a punta. Un solo proyecto Next.js con **grupos de rutas** y menú según el rol (ver `lib/auth/roles.ts`, F4-07).

**Estructura de rutas**

| Grupo          | Ruta base                                      | Roles                                | Pantalla de inicio                |
| -------------- | ---------------------------------------------- | ------------------------------------ | --------------------------------- |
| `(publico)`  | `/`, `/campeonatos`, `/campeonatos/[id]` | Anónimo y todos                     | Landing con campeonatos activos   |
| Auth           | `/login`                                     | –                                   | Redirige según rol tras el login |
| `(gestion)`  | `/gestion/...`                               | SUPERADMIN, ADMIN_DUBSS, ORGANIZADOR | `/gestion`                      |
| `(delegado)` | `/delegado/...`                              | DELEGADO                             | `/delegado`                     |
| Perfil         | `/perfil`                                    | Todos con cuenta                     | –                                |

El panel `(gestion)` es **uno solo**: el Organizador ve lo operativo; el Administrador ve además usuarios, catálogos y bitácora (el menú se filtra por rol y el guard evita entrar por URL).

- [ ] **F5-01 — Vista pública (RF19, RNF08).** *Primero, por ser rápida y visible.* Campeonatos, fixture por jornada, resultados, tabla de posiciones, historial y estadísticas. Sin login. El `middleware.ts` ya no redirige estas rutas.
  *Aceptación:* un navegador sin sesión navega todo lo público.
- [ ] **F5-02 — Login y redirección por rol.** `/login` → `ROLE_HOME[rol]`. Cierre de sesión limpio. Mensajes claros de bloqueo (F0-04).
- [ ] **F5-03 — Gestión: campeonatos (RF9, RF10).** Listado con filtros, crear/editar con validación, cambiar estado (solo transiciones válidas), detalle con pestañas: Resumen · Inscripciones · Fixture · Tabla · Estadísticas.
- [ ] **F5-04 — Gestión: inscripciones (RF6, RF8).** Bandeja de solicitudes con aprobar/rechazar y motivos de elegibilidad visibles.
- [ ] **F5-05 — Gestión: fixture y programación (RF11).** Botón "Generar fixture" (con confirmación y resumen de conflictos), calendario por cancha, mover partidos con detección de conflicto (F3-09).
- [ ] **F5-06 — Gestión: resultados e incidencias (RF12, RF14).** Planilla del partido: marcador, goles, tarjetas, lesiones; **corregi**
- [ ] **r** resultado con motivo (F3-05). Visible para `ORGANIZADOR` y `ADMIN_DUBSS`.
- [ ] **F5-07 — Gestión: catálogos (RF3–RF5)** *(solo ADMIN/SUPERADMIN)*. Deportes, categorías, instalaciones, canchas, horarios y bloqueos de mantenimiento.
- [ ] **F5-08 — Gestión: usuarios y roles (RF2)** *(solo ADMIN/SUPERADMIN)*. Crear cuentas, asignar rol y facultad, activar/desactivar, restablecer contraseña.
- [ ] **F5-09 — Gestión: bitácora (RF18)** *(solo ADMIN/SUPERADMIN)*. Tabla filtrable por usuario, acción, entidad, fecha y resultado (OK/DENEGADO).
- [ ] **F5-10 — Gestión: quejas y apelaciones (RF21).** Bandeja, responder, cambiar estado.
- [ ] **F5-11 — Gestión: reportes (RF16, RF17).** Reporte por campeonato, equipo y jugador; descarga PDF/Excel autenticada.
- [ ] **F5-12 — Delegado: mi equipo y plantel (RF6, RF7).** Crear/editar equipos de su facultad; fichas de jugadores (sin crear cuentas); número de camiseta; sanciones visibles.
- [ ] **F5-13 — Delegado: inscripción y calendario (RF8).** Solicitar inscripción a campeonatos abiertos; ver motivos si hay jugadores no elegibles; calendario de sus partidos.
- [ ] **F5-14 — Delegado: quejas (RF21) y predicciones (RF15).** Presentar queja o apelación; ver predicciones de sus partidos.
- [ ] **F5-15 — Perfil (RF20).** Datos propios, foto, cambio de contraseña. **Sin** campos de rol ni facultad editables.

**Salida de F5:** prueba manual completa con los 4 roles + anónimo siguiendo la matriz de F2.

---

# FASE 5b — RF11 con ML, versión mínima (14–21 nov, si hay tiempo)

**Objetivo:** que el requisito esencial RF11 tenga ML real antes de H4. Si no alcanza, pasa íntegro a F6-02 sin perder trabajo.

- [ ] **F5b-01 — `MuestraAsignacion` (documento).** Modelo con las características de una asignación (franja horaria, día de la semana, días desde el último partido de cada equipo, disponibilidad de instalación, conflictos de horario) y etiqueta de `calidad`. Comando de arranque en frío que etiqueta con reglas explícitas (documentadas) mientras no hay historial.
- [ ] **F5b-02 — Puntuador de asignaciones.** `ml/services/asignacion_scorer.py`: `RandomForestClassifier` que entrena con las muestras y devuelve `puntuar(asignacion) → probabilidad de "buena asignación"`. Guardar versión y métricas (F6-01 formaliza el registro de modelos).
- [ ] **F5b-03 — Optimizador.** `fixture/services/fixture_optimizer.py` con **OR-Tools CP-SAT**: variables partido → (cancha, franja); restricciones duras (sin solapes de cancha, sin dos partidos a la vez para un equipo, descanso mínimo, horarios de `HorarioCancha`, `BloqueoCancha` y `RestriccionHorarioFacultad`); objetivo = maximizar la suma de puntuaciones del `asignacion_scorer`. `max_time_in_seconds` configurable (RNF04: 20 equipos en < 10 s).
- [ ] **F5b-04 — Integración.** `generar_fixture(..., usar_ml=True)` llama al optimizador y solo entonces marca `generado_por_ml=True`; si el solver no encuentra solución, cae al generador base (F3-03) avisando al usuario. Mostrar en la UI métricas de calidad del fixture (conflictos = 0, descanso promedio, equidad).
  *Aceptación:* test con 20 equipos < 10 s y cero conflictos.

---

# FASE 6 — IA central y automatización (24 nov – 20 dic)

**Objetivo:** dejar el módulo de ML correcto y honesto, y automatizar tareas con Celery.

- [ ] **F6-01 — Predictor corregido (RF15, OE3).** Reescribir `ml/services/predictor.py`:

  - Características calculadas **a la fecha del partido** (nada de la tabla final → sin fuga de datos): forma reciente, goles a favor/en contra, rating Elo, enfrentamientos previos, días de descanso, local/visitante.
  - **Validación temporal** (entrenar con el pasado, evaluar con el futuro) y *walk-forward*; comparación con líneas base (siempre local, Elo).
  - Métricas: accuracy, log-loss, Brier; calibración de probabilidades.
  - Modelo `ModeloML(nombre, version, metricas JSON, fecha_entrenamiento, hash_datos, ruta_artefacto, activo)` y comando `train_model`.
  - Inferencia con el modelo cacheado en memoria (< 5 s, RNF05); respuesta honesta cuando hay pocos partidos ("datos insuficientes", baja confianza).
  - Botón "Entrenar" solo para `ADMIN_DUBSS`/`SUPERADMIN`.
    *Aceptación:* informe de métricas reproducible; el modelo supera (o se documenta que no supera) la línea base.
- [ ] **F6-02 — Fixture asistido por ML completo (RF11).** Si no se hizo en F5b: ejecutar F5b-01…04. Agregar reentrenamiento del puntuador con partidos reales.
- [ ] **F6-03 — Celery + Redis.** Agregar a `docker-compose*.yml` los servicios `redis`, `celery_worker`, `celery_beat`. Tareas idempotentes: recordatorio de partido (24 h y 2 h antes), actualización de riesgo climático, reentrenamiento programado, snapshot de historial al cerrar jornada.
- [ ] **F6-04 — Notificaciones push con FCM HTTP v1 (RF25).** Reemplazar la API legada (`/fcm/send` con server key) por HTTP v1 (cuenta de servicio, `firebase-admin` o `google-auth`); limpiar tokens inválidos; envío por facultad/tema; solo admin/organizador pueden enviar; bitácora.
- [ ] **F6-05 — Estadísticas completas (RF16).** Endpoints y reportes por **jugador, equipo, facultad y torneo** (goles, tarjetas, rendimiento, asistencia). Exportación PDF/Excel.
- [ ] **F6-06 — Reportes por voz (RF22 nuevo).**

  1. `POST /api/asistente/transcribir/` (audio) → texto con **faster-whisper** (`WHISPER_MODEL=small|base|medium`, idioma `es`; ejecutar como tarea Celery y consultar el resultado por polling si el audio es largo).
  2. `POST /api/asistente/interpretar/` (texto) → un LLM (`LLM_PROVIDER=groq|ollama`) devuelve **JSON con una intención de una lista blanca** (`reporte_campeonato`, `tabla_posiciones`, `estadisticas_jugador`, `estadisticas_equipo`, `proximos_partidos`, `resumen_torneo`) y sus parámetros, validados con serializers. **El LLM nunca escribe SQL.**
  3. La interfaz muestra la transcripción editable y pide confirmar antes de ejecutar; reutiliza los generadores de PDF/Excel existentes.
  4. Solo `ADMIN_DUBSS`, `ORGANIZADOR`, `SUPERADMIN`; cada uso va a bitácora.
  5. Frontend: botón "pulsar para hablar" (`MediaRecorder`) y campo de texto como alternativa.
     *Aceptación:* 10 frases de prueba en español → intención y parámetros correctos; frases ambiguas piden aclaración.
- [ ] **F6-07 — Clima y asistencia sin efectos laterales.** Mantener `RiesgoClimatico` y `PrediccionAsistencia`, pero calculados por tarea programada (F6-03) y consultados por `GET` sin escritura. Sustituir el modelo de Groq obsoleto por uno configurable por variable de entorno.

---

# FASE 7 — Agente, móvil y experimentos (ene – feb)

**Objetivo:** el valor diferencial del proyecto. **Antes de programar, agregar los requisitos RF23 y RF24 al documento.**

## F7-A. Agente "Asistente del Organizador" (RF23 nuevo)

No es un chatbot: **decide qué herramientas usar, actúa sobre el sistema y pide confirmación antes de cambiar algo.** Un LLM con *function calling* (Ollama con un modelo con soporte de herramientas, o Groq como respaldo) más un registro de herramientas tipadas.

Ejemplo objetivo: *"Hay lluvia el sábado, reprograma lo necesario."* → consulta clima → lista partidos afectados → el optimizador propone nuevos horarios sin choques → **muestra la propuesta y espera confirmación** → aplica cambios → notifica a delegados → bitácora.

- [ ] **F7-01 — App `agente` y registro de herramientas.**

| Herramienta                                                                 | Tipo      | Confirmación     |
| --------------------------------------------------------------------------- | --------- | ----------------- |
| `consultar_tabla`, `listar_partidos`, `ver_clima`                     | Lectura   | No                |
| `predecir_partido`, `generar_reporte`                                   | Lectura   | No                |
| `proponer_reprogramacion` (usa el optimizador F5b-03 en modo reparación) | Cálculo  | No (solo propone) |
| `aplicar_reprogramacion`                                                  | Escritura | **Sí**     |
| `enviar_notificacion`                                                     | Escritura | **Sí**     |

  Reglas: cada herramienta usa los **mismos permisos del usuario** que habla con el agente; parámetros validados por serializers; **sin SQL libre**; máximo 5 pasos por petición; tiempo límite; límite de uso por usuario; todo a bitácora. Los resultados de herramientas se tratan como datos, nunca como instrucciones (defensa ante inyección de prompts).

- [ ] **F7-02 — Acciones pendientes con confirmación.** Modelo `AccionPendiente(usuario, herramienta, propuesta JSON, estado [PENDIENTE|CONFIRMADA|CANCELADA|EXPIRADA], expira_en)` y endpoints `confirmar` / `cancelar`. Solo al confirmar se ejecuta, dentro de `transaction.atomic()`.
- [ ] **F7-03 — Interfaz del agente.** Panel de conversación en `/gestion/asistente` con tarjeta de propuesta (qué cambia, a quién notifica) y botones Confirmar / Cancelar. Disponible para `ADMIN_DUBSS`, `ORGANIZADOR`, `SUPERADMIN`.
- [ ] **F7-04 — Evaluación del agente.** Script con 15–20 escenarios (entrada → herramientas esperadas) que mide aciertos, pasos y rechazos correctos por permiso. Se documenta el resultado en el informe. *Un agente no se "entrena": se evalúa y se ajustan prompts y descripciones de herramientas.*

## F7-B. Móvil y planilla sin conexión (RF24 nuevo)

- [ ] **F7-05 — PWA.** `manifest`, *service worker* (Serwist/next-pwa), instalable en el móvil. Planilla digital para el Organizador (marcador e incidencias).
- [ ] **F7-06 — Sincronización idempotente.** Cola local con IndexedDB (Dexie); cabecera `Idempotency-Key` en `POST` de resultado/incidencia; el backend guarda `OperacionIdempotente` para no duplicar; política de conflicto: si el partido ya fue finalizado por otro, se rechaza y se avisa. Indicador de estado de sincronización en la UI.
  *Aceptación:* registrar 5 incidencias sin red y sincronizar sin duplicados.

## F7-C. Análisis avanzado

- [ ] **F7-07 — Clustering de equipos (K-means).** `POST /api/ml/cabezas-de-serie/`: agrupa por rendimiento para sembrar llaves de eliminación y armar grupos equilibrados.
- [ ] **F7-08 — Detección de resultados atípicos** (Isolation Forest, opcional): alerta a administradores de marcadores o patrones raros.
- [ ] **F7-09 — Experimento de red neuronal (opcional, D11).** Cuaderno documentado: red pequeña (PyTorch o `MLPClassifier`) frente a Random Forest con las mismas métricas. Solo si el docente exige *deep learning* explícito.
- [ ] **F7-10 — Panel de jugador con cuenta (opcional, posterior).** Cumple RF1/RF20 para jugador; solo lectura de su ficha, estadísticas y sanciones.

---

# FASE 8 — Calidad, despliegue y documento (mar – abr)

**Objetivo:** cumplir los requisitos no funcionales y la validación del Objetivo Específico 5 (pruebas funcionales, de integración, **rendimiento y usabilidad**). *Los puntos de infraestructura (F8-05 a F8-07) pueden adelantarse si se despliega antes.*

- [ ] **F8-01 — Cobertura (RNF26).** Activar `--cov-fail-under=70` en CI. Completar tests de servicios (fixture, tabla, elegibilidad, optimizador, predictor) y de la matriz de permisos.
- [ ] **F8-02 — Pruebas E2E.** Playwright: un flujo por rol (admin crea campeonato → delegado inscribe → organizador genera fixture y carga resultados → público ve la tabla).
- [ ] **F8-03 — Pruebas de rendimiento (RNF01–RNF05).** k6 o Locust con umbrales automáticos: respuestas de consulta, registro de resultado + recálculo (< 5 s), fixture de 20 equipos (< 10 s), predicción (< 5 s), carga concurrente según el documento. Informe con resultados.
- [ ] **F8-04 — Pruebas de usabilidad (OE5).** Sesiones con 5 usuarios por rol (delegado y organizador como mínimo), tareas guiadas y cuestionario SUS; registrar hallazgos y correcciones.
- [ ] **F8-05 — HTTPS/TLS (RNF14).** Configurar nginx con certificado (Let's Encrypt/certbot), redirección 80→443, HSTS, cabeceras de seguridad, cookies `Secure`.
- [ ] **F8-06 — Respaldos (RNF13).** Servicio/cron con `pg_dump` diario, retención de 30 días, copia fuera del servidor y **prueba de restauración** documentada.
- [ ] **F8-07 — Procedimiento de actualización y reversión (RNF27).** Documento y scripts: respaldo previo, `docker compose pull/up`, migraciones, verificación (*healthcheck*), reversión a la imagen anterior. Imágenes etiquetadas por versión.
- [ ] **F8-08 — Seguridad.** `pip-audit` y `npm audit`; revisión de CORS, throttles y cabeceras; revisión de datos personales según lo indicado en el documento.
- [ ] **F8-09 — Calidad de código (RNF23–RNF25).** Docstrings en servicios, Swagger con ejemplos, README actualizado, tabla de correspondencia **módulo del documento ↔ app de Django** (el documento dice 5 módulos y el código tiene más apps).
- [ ] **F8-10 — Documento sincronizado.** Aplicar la sección siguiente.

---

# DOCUMENTO — Cambios necesarios (hacer en paralelo, cerrar en F8-10)

Son cambios de **texto**; no obligan a rehacer diagramas (se mantienen los 6 actores y el rol Organizador).

| #  | Dónde                                 | Cambio                                                                                                                                                                                                                                                                                                                                                                                                                                                             |
| -- | -------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| 1  | Objetivo general, 6.3 y justificación | Random Forest no "genera" el fixture solo: redactar como **enfoque híbrido** (optimizador por restricciones genera candidatos; Random Forest evalúa la calidad de cada asignación, tabla `MuestraAsignacion`). Quitar la afirmación de que Random Forest es "superior para optimización combinatoria". **Verificar la cita Bunker y Thabtah (2019):** por lo que recuerdo trata de predicción de resultados, no de programación de encuentros |
| 2  | 6.3 y RF15                             | Unificar: Random Forest se usa en dos funciones (calidad de asignación para RF11 y predicción de resultados para RF15)                                                                                                                                                                                                                                                                                                                                           |
| 3  | 6.1                                    | La lista de roles (4) no coincide con la tabla 001 (6). Alinear con la tabla; retirar la mención a "árbitros" (RF12 dice Organizador)                                                                                                                                                                                                                                                                                                                            |
| 4  | Tabla 001                              | Corregir la tabla partida con encabezado repetido                                                                                                                                                                                                                                                                                                                                                                                                                  |
| 5  | Numeración RNF                        | Uniformar (RNF05, RNF13 sin guion)                                                                                                                                                                                                                                                                                                                                                                                                                                 |
| 6  | Cronograma H5                          | La fecha 10/06/2026 es anterior a H4; parece error de año                                                                                                                                                                                                                                                                                                                                                                                                         |
| 7  | RF1 / RF20                             | Jugador pasa a "ficha sin cuenta" en esta versión; el acceso con cuenta queda como fase posterior (F7-10)                                                                                                                                                                                                                                                                                                                                                         |
| 8  | 6.3 conectividad y RNF21               | Matizar con la PWA con soporte sin conexión (F7-05) y ampliar los servicios del sistema (Redis, Celery, IA)                                                                                                                                                                                                                                                                                                                                                       |
| 9  | Cap. 7 (3FN)                           | Agregar nota: `TablaPosiciones` e `PosicionHistorial` son **desnormalización controlada** recalculable desde `Resultado`                                                                                                                                                                                                                                                                                                                              |
| 10 | RNF15                                  | Mantener "Argon2" (ya implementado en F0-07)                                                                                                                                                                                                                                                                                                                                                                                                                       |
| 11 | Cap. 5                                 | Alinear la numeración de casos de uso con los comentarios del código (hoy no coinciden)                                                                                                                                                                                                                                                                                                                                                                          |
| 12 | 6.1 módulo 1                          | "Registro de usuarios" → "Alta de cuentas por el administrador" (no hay autorregistro)                                                                                                                                                                                                                                                                                                                                                                            |
| 13 | Requisitos nuevos                      | Agregar **RF22** Reportes por voz, **RF23** Asistente del Organizador (agente), **RF24** Planilla digital sin conexión, **RF25** Notificaciones push y automatizaciones (clima, recordatorios) con sus casos de uso                                                                                                                                                                                                                       |
| 14 | Cap. 2                                 | Marco teórico de las tecnologías nuevas: OR-Tools (CP-SAT), Whisper, LLM con *function calling*, Celery, PWA                                                                                                                                                                                                                                                                                                                                                   |
| 15 | Cap. 7                                 | Agregar tablas nuevas: `Facultad`, `Inscripcion`, `HorarioCancha`, `RestriccionHorarioFacultad`, `PosicionHistorial`, `ModeloML`, `AccionPendiente`, `OperacionIdempotente`; documentar que `Cancha` y `BloqueoCancha` existen en el código                                                                                                                                                                                                   |
| 16 | Datos sintéticos                      | Si se usa `seed_historial` para arrancar el ML, declararlo explícitamente                                                                                                                                                                                                                                                                                                                                                                                       |

---

# TRAZABILIDAD

## RF → fase donde se cierra

| RF         | Requisito                                     | Fases                                 |
| ---------- | --------------------------------------------- | ------------------------------------- |
| RF1        | Autenticación                                | F0, F5-02                             |
| RF2        | Roles y permisos                              | F1-01, F2-01/03, F5-08                |
| RF3        | Deportes                                      | F1-07, F5-07                          |
| RF4        | Categorías                                   | F1-07, F5-07                          |
| RF5        | Instalaciones                                 | F1-08, F5-07                          |
| RF6        | Equipos                                       | F1-03/04, F2, F3-02, F5-12            |
| RF7        | Jugadores y fichas                            | F1-05, F5-12                          |
| RF8        | Restricciones de participación               | F1-09, F3-02/08, F5-04/13             |
| RF9        | Creación de campeonatos                      | F1-06, F3-01, F5-03                   |
| RF10       | Estados del campeonato                        | F3-01, F5-03                          |
| RF11       | Fixture con ML                                | F3-03/04, **F5b**, F6-02, F5-05 |
| RF12       | Resultados                                    | F3-05, F5-06                          |
| RF13       | Tablas e historial                            | F3-06/07, F5-01                       |
| RF14       | Incidencias                                   | F3-08, F5-06                          |
| RF15       | Predicción                                   | F0-08, F6-01, F5-14                   |
| RF16       | Reportes y estadísticas                      | F6-05, F5-11                          |
| RF17       | Exportar PDF                                  | F4-08, F5-11                          |
| RF18       | Auditoría y bitácora                        | F0-05, F5-09                          |
| RF19       | Visualización pública                       | F5-01                                 |
| RF20       | Perfil                                        | F0-03, F5-15                          |
| RF21       | Quejas y apelaciones                          | F1-10, F2-05, F5-10/14                |
| RF22–RF25 | Nuevos (voz, agente, offline, notificaciones) | F6-04/06, F7                          |

## RNF → fase

| RNF       | Tema                                                         | Fase                                     |
| --------- | ------------------------------------------------------------ | ---------------------------------------- |
| RNF01–05 | Rendimiento (fixture < 10 s, predicción < 5 s, tabla < 5 s) | F3-03/06, F5b-03, F6-01, **F8-03** |
| RNF06–07 | Responsivo y usabilidad                                      | F4-06, **F8-04**                   |
| RNF08     | Consulta pública                                            | F5-01                                    |
| RNF09     | Mensajes de error claros                                     | F0-04, F4-04                             |
| RNF10–11 | Disponibilidad y reinicio                                    | F8-05/06 (reinicio ya cumple)            |
| RNF13     | Respaldos                                                    | **F8-06**                          |
| RNF14     | HTTPS/TLS                                                    | **F8-05**                          |
| RNF15     | Hash Argon2                                                  | **F0-07**                          |
| RNF16–17 | Autorización y tokens                                       | F2, F0-09                                |
| RNF18     | Bloqueo por intentos                                         | **F0-04**                          |
| RNF19     | Bitácora                                                    | **F0-05**                          |
| RNF21     | Servicios del sistema                                        | F6-03, F8-10                             |
| RNF23–25 | Código, Swagger, módulos                                   | F8-09                                    |
| RNF26     | Cobertura 70%                                                | F2-08, **F8-01**                   |
| RNF27     | Procedimiento de actualización                              | **F8-07**                          |

---

# HALLAZGOS INICIALES CUBIERTOS POR ESTE PLAN

| Hallazgo                                                                                                                | Tarea              |
| ----------------------------------------------------------------------------------------------------------------------- | ------------------ |
| Registro público acepta `rol` (escalada a admin)                                                                     | F0-02              |
| Perfil permite cambiar `rol`/`facultad`                                                                             | F0-03              |
| Sin bloqueo por intentos                                                                                                | F0-04              |
| Cambio de contraseña no invalida tokens                                                                                | F0-06              |
| Bitácora nunca se escribe                                                                                              | F0-05              |
| `models.Q` sin importar en el predictor                                                                               | F0-08              |
| Refresh rotado no guardado en el frontend                                                                               | F0-09              |
| Hash PBKDF2 en lugar de Argon2                                                                                          | F0-07              |
| Equipo duplicado por campeonato                                                                                         | F1-03/04           |
| `facultad` en texto libre                                                                                             | F1-02              |
| `deporte` y `categoria` redundantes en `Campeonato`                                                               | F1-06              |
| Marcador e incidencias contradictorios                                                                                  | F1-13              |
| Validaciones solo en `clean()` y sin constraints                                                                      | F1-11              |
| Roles distintos al documento; permiso inconsistente del formulario de resultados                                        | F1-01, F2          |
| Fixture sin ML y marcado como ML; generador con bucle infinito, borrado de partidos jugados y horarios secuenciales     | F3-03, F5b         |
| Solo formato liga                                                                                                       | F3-04              |
| Tabla incremental, no corregible                                                                                        | F3-05/06           |
| GET que escriben en base de datos                                                                                       | F2-04              |
| Reportes públicos                                                                                                      | F2-06              |
| FCM API legada                                                                                                          | F6-04              |
| Celery sin tareas ni servicio                                                                                           | F6-03              |
| Frontend: estilos en línea, librerías sin uso, `alert()`, `localhost` fijo, sin guard por rol, sin vista pública | F4, F5             |
| Falta de TLS, respaldos y procedimiento de actualización                                                               | F8-05/06/07        |
| Pruebas: solo 8 tests de autenticación                                                                                 | F2-07/08, F8-01/02 |
