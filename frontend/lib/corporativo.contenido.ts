/** Textos del sitio corporativo. Los equipos y cifras de las vistas de ejemplo son ficticios. */

export const MODULOS = [
  {
    id: "fixture", etiqueta: "Fixture automático",
    titulo: "Fixture que respeta canchas, horarios y clases",
    texto: "El organizador define el campeonato y el sistema propone el calendario completo. Un optimizador evita choques de cancha, descansos cortos y partidos en horarios de clases, y un modelo de aprendizaje automático asigna los mejores horarios según el clima.",
    puntos: ["Sin partidos superpuestos en la misma cancha", "Restricciones por horario de clases", "Riesgo climático con pronóstico de Open-Meteo", "Cambios con confirmación antes de publicarse"],
    pantalla: "Fixture · Jornada 4",
    cabecera: ["Hora", "Cancha", "Partido", "Clima"],
    filas: [["18:30", "1", "Ingeniería vs Medicina", "ok:Bajo"], ["19:30", "2", "Derecho vs Economía", "ok:Bajo"], ["20:30", "1", "Humanidades vs Tecnología", "wn:Medio"]],
    nota: "Vista de ejemplo con datos ficticios.",
  },
  {
    id: "posiciones", etiqueta: "Tabla de posiciones",
    titulo: "Posiciones que se actualizan al registrar el resultado",
    texto: "Cada resultado cargado recalcula la tabla con los criterios del reglamento del campeonato. También se guarda el historial de posiciones por jornada y se avisa de los resultados atípicos para que se revisen.",
    puntos: ["Puntos, diferencia de goles y desempates", "Historial por jornada", "Detección de resultados atípicos", "Consulta pública sin iniciar sesión"],
    pantalla: "Posiciones · Grupo A",
    cabecera: ["#", "Equipo", "PJ", "DG", "Pts"],
    filas: [["1", "Ingeniería", "4", "+6", "10"], ["2", "Derecho", "4", "+3", "8"], ["3", "Medicina", "4", "0", "5"], ["4", "Economía", "4", "-4", "3"]],
    nota: "Vista de ejemplo con datos ficticios.",
  },
  {
    id: "prediccion", etiqueta: "Predicción de resultados",
    titulo: "Probabilidades antes del partido",
    texto: "Un modelo Random Forest, combinado con un puntaje Elo de cada equipo, calcula la probabilidad de victoria, empate o derrota a partir del historial. Sirve para planificar y para animar el campeonato, no para decidir resultados.",
    puntos: ["Entrenamiento con el historial de partidos", "Reentrenamiento semanal automático", "Agrupamiento de equipos por nivel"],
    pantalla: "Predicción · Ingeniería vs Medicina",
    barras: [["Ingeniería", 52], ["Empate", 21], ["Medicina", 27]],
    nota: "Vista de ejemplo con datos ficticios.",
  },
  {
    id: "planilla", etiqueta: "Planilla sin conexión",
    titulo: "La planilla se llena aunque se corte el internet",
    texto: "El organizador registra goles y tarjetas desde el celular. Si no hay conexión, los datos quedan guardados en el dispositivo y se envían solos al volver la señal, sin duplicarse. Además, un asistente por voz permite dictar el reporte del partido.",
    puntos: ["Aplicación web instalable (PWA)", "Envío seguro sin duplicados al reconectar", "Reportes por voz", "Notificaciones y recordatorios de partidos"],
    pantalla: "Planilla · Derecho vs Economía",
    cabecera: ["Min.", "Evento", "Jugador", "Estado"],
    filas: [["12'", "Gol", "J. Rojas", "ok:Enviado"], ["34'", "Tarjeta amarilla", "M. Vaca", "wn:En espera"], ["58'", "Gol", "L. Suárez", "wn:En espera"]],
    nota: "Sin conexión: 2 eventos se enviarán al reconectar. Datos ficticios.",
  },
] as const;

export const ROLES = [
  ["Superadministrador", "Configura el sistema, gestiona usuarios y roles y revisa la bitácora de auditoría."],
  ["Administrador DUBSS", "Administra facultades, deportes, instalaciones y supervisa los campeonatos."],
  ["Organizador", "Crea campeonatos, genera el fixture, registra resultados, resuelve quejas y usa la planilla móvil."],
  ["Delegado", "Inscribe a su equipo y jugadores, consulta su calendario, presenta quejas y ve predicciones."],
  ["Jugador", "Consulta su ficha: estadísticas, sanciones vigentes y próximos partidos (solo lectura)."],
] as const;

export const NIVELES = [
  ["Nivel 1", "Asistente y preguntas frecuentes", "Respuestas inmediatas sobre el uso del sistema, la instalación y los roles."],
  ["Nivel 2", "Soporte funcional", "Atención por correo o WhatsApp para dudas de uso, cuentas y datos de un campeonato."],
  ["Nivel 3", "Ingeniería", "Fallas de la aplicación, la base de datos, el optimizador o los modelos de predicción. La infraestructura se coordina con el área de tecnología de la universidad cuando el sistema esté alojado allí."],
] as const;

export interface RespuestaAyuda { claves: string[]; texto: string; enlace?: { href: string; etiqueta: string } }

/** Base del asistente de ayuda: reglas por palabra clave, sin inteligencia artificial ni servicios externos. */
export const AYUDA: RespuestaAyuda[] = [
  { claves: ["ubicación", "ubicacion", "dónde", "donde", "sede", "teléfono", "telefono", "dirección de la dubss"], texto: "La DUBSS está en la Av. Busch, Ciudad Universitaria (lado comedor universitario, Mod. 292), Santa Cruz de la Sierra. Teléfono 60040944 y correo dubss@uagrm.edu.bo. Atiende en oficinas de 9:00 a 16:00.", enlace: { href: "#dubss", etiqueta: "Ver datos de la DUBSS" } },
  { claves: ["precio", "costo", "cuánto", "cuanto", "licencia", "cobr"], texto: "El precio y el modelo de licencia se acuerdan con cada institución. Escríbenos desde Contacto y te enviamos una propuesta.", enlace: { href: "#contacto", etiqueta: "Ir a Contacto" } },
  { claves: ["qué es", "que es", "sistema", "plataforma", "sporttech", "dubss", "para qué"], texto: "SportTech DUBSS es una plataforma web para organizar campeonatos deportivos universitarios: arma el fixture, calcula posiciones, predice resultados y permite llenar la planilla del partido sin conexión." },
  { claves: ["fixture", "calendario", "programar", "programación", "horario", "cancha"], texto: "El fixture se genera con un optimizador que evita choques de cancha, descansos cortos y horarios de clases, y usa un modelo de aprendizaje automático para elegir los mejores horarios. El organizador revisa y confirma antes de publicarlo." },
  { claves: ["predic", "probabilidad", "machine", "inteligencia", "modelo"], texto: "Un modelo Random Forest con puntaje Elo estima la probabilidad de victoria, empate o derrota de cada equipo. Se reentrena cada semana con el historial. Es una referencia, no decide resultados." },
  { claves: ["internet", "conexión", "conexion", "offline", "sin red", "planilla"], texto: "La planilla funciona sin internet: los eventos quedan guardados en el dispositivo y se envían solos, sin duplicarse, cuando vuelve la conexión." },
  { claves: ["voz", "dictar", "asistente"], texto: "El asistente por voz permite dictar el reporte de un partido. Toda acción que cambia datos pide confirmación antes de aplicarse." },
  { claves: ["rol", "usuario", "perfil", "permiso", "delegado", "organizador", "administrador", "jugador"], texto: "Hay cinco roles: Superadministrador, Administrador DUBSS, Organizador, Delegado y Jugador. Cada uno ve solo las funciones que le corresponden." },
  { claves: ["instal", "app", "celular", "móvil", "movil", "pwa", "descargar"], texto: "Es una aplicación web instalable (PWA): se instala desde el navegador, sin tienda de aplicaciones. En Descargas está la ficha técnica en PDF.", enlace: { href: "#descargas", etiqueta: "Ir a Descargas" } },
  { claves: ["seguridad", "datos", "privacidad", "contraseña", "contrasena"], texto: "Las contraseñas se guardan con Argon2, la cuenta se bloquea 15 minutos tras 5 intentos fallidos, cada acción queda en una bitácora y cada usuario accede solo a lo que su rol permite." },
  { claves: ["soporte", "ayuda", "problema", "error", "falla"], texto: "Si el asistente no resuelve tu problema, escríbenos por correo o WhatsApp desde Contacto e indica qué estabas haciendo y qué mensaje apareció.", enlace: { href: "#soporte", etiqueta: "Ver niveles de soporte" } },
  { claves: ["contacto", "correo", "email", "whatsapp", "llamar", "hablar", "persona"], texto: "Puedes escribirnos por correo o WhatsApp desde la sección Contacto.", enlace: { href: "#contacto", etiqueta: "Ir a Contacto" } },
];
export const AYUDA_SIN_RESPUESTA: RespuestaAyuda = { claves: [], texto: "No tengo una respuesta para eso. Puedes escribirnos desde Contacto y una persona del equipo te responde.", enlace: { href: "#contacto", etiqueta: "Ir a Contacto" } };
export const PREGUNTAS_RAPIDAS = ["¿Qué es SportTech?", "¿Cómo funciona el fixture?", "¿Funciona sin internet?", "¿Cuánto cuesta?"];
