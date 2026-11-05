# Datos de prueba (seed realista de la UAGRM)

Solo para desarrollo. Se cargan (y se restablecen) con:

```
docker exec dubss_backend_dev python manage.py seed_realista
```

Reemplaza al antiguo `seed_demo`. **Borra** los datos de campeonatos, equipos, partidos, instalaciones y las cuentas de ejemplo, y los crea de nuevo; conserva cualquier otra cuenta (por ejemplo la del programador). Solo corre con `DEBUG=True`. Con `--sin-ia` omite el entrenamiento de los modelos (más rápido).

> **Los resultados de la temporada 2025 son simulados.** Se generan con un modelo estadístico (goles de Poisson según la fuerza relativa de cada facultad) para que la IA tenga historial con el que trabajar. No son datos reales de la universidad. Al operar de verdad, estos datos se reemplazan por los reales.

## Acceso

- **Aplicación:** http://localhost:3000 (inicio de sesión: `/login`)
- **API y documentación:** http://localhost:8000/api/v1/ · http://localhost:8000/api/docs/
- **Contraseña de todas las cuentas de ejemplo:** `Dubss2026!`

| Rol | Correo | Qué ve |
|---|---|---|
| Superadministrador | `superadmin@uagrm.edu.bo` | Todo, incluida la bitácora y los usuarios |
| Administrador DUBSS | `admin@uagrm.edu.bo` | Gestión completa, catálogos, usuarios y bitácora |
| Organizador | `organizador@uagrm.edu.bo` | Campeonatos, fixture, resultados, IA, reportes, planilla móvil |
| Organizador (2) | `organizador2@uagrm.edu.bo` | Igual que el anterior |
| Delegado de Ingeniería en Sistemas | `delegado.ficct@uagrm.edu.bo` | Sus equipos, inscripciones, calendario, quejas y predicciones |
| Delegados de las otras facultades | `delegado.<sigla>@uagrm.edu.bo` (`fceaf`, `fpoli`, `fcet`, `fcsh`, `faud`, `fcjpsri`, `fh`, `fod`, `fca`, `fcv`, `fcfb`) | Igual, de su facultad |
| Jugador | `jugador@uagrm.edu.bo` | Su ficha (Sistemas FC): estadísticas, sanción y partidos |
| Jugador (Medicina) | `jugador.medicina@uagrm.edu.bo` | Su ficha (Medicina FC) |
| Jugador sancionado | `jugador.sancionado@uagrm.edu.bo` | Ficha con una suspensión vigente |

## Qué contiene

- **12 facultades** de la UAGRM, 4 deportes (Fútbol, Futsal, Voleibol, Baloncesto), 3 instalaciones con 7 canchas (cubiertas y al aire libre), horarios, un bloqueo de mantenimiento y restricciones por clases/prácticas.
- **44 equipos con ~560 jugadores** y un delegado por facultad.
- **Interfacultades de Fútbol Varones 2025** y **de Futsal Varones 2025**: temporadas terminadas (94 partidos con goles y tarjetas). Incluyen una goleada 9-0 que la IA señala como atípica.
- **Interfacultades de Fútbol Varones 2026 (en curso):** el fixture lo generó el propio optimizador del sistema; las jornadas 1 a 3 están jugadas (con una tarjeta roja y un jugador suspendido) y las siguientes programadas, con partidos hoy y en los próximos días para probar la planilla móvil.
- **Copa Relámpago de Futsal 2026** (eliminación directa, inscripciones cerradas): sin fixture, lista para generar con la siembra por IA.
- **Copa de Voleibol Damas 2026** con inscripciones pendientes, aprobadas y rechazada; **Baloncesto 2026** en planificación.
- Quejas en todos los estados, y los modelos de IA ya entrenados.

## Recorridos sugeridos

1. **Organizador → Inteligencia artificial → Niveles y siembra:** analiza la Copa Relámpago de Futsal; luego en el campeonato, *Fixture → Generar fixture* con «Sembrar la llave con IA».
2. **Administrador → Inteligencia artificial → Resultados atípicos:** revisa el 9-0 y márcalo como revisado.
3. **Organizador → Planilla móvil (`/planilla`):** abre un partido de hoy, anota goles y tarjetas; prueba el modo sin conexión desde las herramientas del navegador (Network → Offline).
4. **Organizador → Asistente → Agente:** «¿Qué partidos hay mañana?», «Avisa a los delegados que…». Requiere la clave de Groq en `.env`.
5. **Delegado:** panel con su próximo partido; prueba también `jugador.sancionado@uagrm.edu.bo` para ver la suspensión.

## Modo rápido para probar (recomendado)

El modo de desarrollo (`next dev`) compila cada pantalla al abrirla y vigila todos los archivos del disco compartido de Windows: es lento y usa mucha CPU. Para **probar** el sistema usa el modo rápido, que sirve la versión de producción:

```
docker compose -f docker-compose.dev.yml -f docker-compose.rapido.yml up -d frontend backend
```

La primera vez compila unos minutos (después reutiliza la compilación: los reinicios de Docker tardan segundos; para recompilar tras cambiar código, borra `frontend/.next` y reinicia el servicio); después las pantallas abren en milésimas de segundo y el inicio de sesión tarda ~0,2 s. Para **programar** con recarga en caliente vuelve al modo normal (`docker compose -f docker-compose.dev.yml up -d frontend backend`) y borra antes la carpeta `frontend/.next`.

Medición en esta máquina (4 CPU, 5 GB para Docker): frontend de 158 % de CPU y 929 MB a 0 % y 70 MB; pantallas de 0,7–9,7 s a 0,02–0,15 s; inicio de sesión de 2,3 s a 0,2 s. En desarrollo el hash de contraseñas usa Argon2 con costo reducido (`config/hashers.py`); en producción se mantiene el estándar.
