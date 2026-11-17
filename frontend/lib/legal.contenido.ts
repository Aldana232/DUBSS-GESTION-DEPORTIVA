import { RESPONSABLE } from "./legal.config";

/** Contenido de los documentos legales. Cada documento es una lista de secciones con bloques de texto, listas o tablas. */
export type Bloque =
  | { tipo: "p"; texto: string }
  | { tipo: "ul"; items: string[] }
  | { tipo: "tabla"; cabecera: string[]; filas: string[][]; nota?: string };
export interface Seccion { id: string; titulo: string; bloques: Bloque[] }
export interface Documento { titulo: string; resumen: string; secciones: Seccion[] }

const R = RESPONSABLE;
const p = (texto: string): Bloque => ({ tipo: "p", texto });
const ul = (...items: string[]): Bloque => ({ tipo: "ul", items });

/* ───────────────────────────── Política de privacidad ───────────────────────────── */
export const PRIVACIDAD: Documento = {
  titulo: "Política de privacidad",
  resumen: "Qué datos personales trata el sistema de gestión deportiva de la DUBSS, para qué, con quién los comparte, cuánto tiempo los conserva y cómo puedes ejercer tus derechos.",
  secciones: [
    { id: "responsable", titulo: "1. Quién es el responsable", bloques: [
      p(`El responsable del tratamiento de tus datos personales es la ${R.nombre} de la ${R.institucion}, con domicilio en ${R.direccion}.`),
      p(`Para cualquier consulta sobre esta política o sobre tus datos puedes escribir a ${R.correo}, llamar al ${R.telefono} o acudir a las oficinas (${R.horario}).`),
      p("Este sistema es una herramienta de apoyo a la organización de los campeonatos deportivos universitarios. No es un sitio de venta ni de publicidad."),
    ] },
    { id: "datos", titulo: "2. Qué datos recogemos y para qué", bloques: [
      p("Tratamos solo los datos necesarios para organizar los campeonatos, identificar a quien usa el sistema y mantenerlo seguro."),
      { tipo: "tabla", cabecera: ["Dato", "De dónde sale", "Para qué se usa"], filas: [
        ["Nombre, apellido y correo institucional", "Los registra el administrador al crear tu cuenta", "Identificarte, iniciar sesión y enviarte avisos"],
        ["Carnet de identidad (CI)", "Tú o el administrador, en tu perfil o ficha", "Verificar tu identidad y evitar fichas duplicadas"],
        ["Teléfono y foto de perfil", "Tú, de forma voluntaria", "Contacto y reconocimiento dentro del sistema"],
        ["Número de WhatsApp y su consentimiento", "Tú, en Mi perfil (opcional)", "Enviarte avisos y responder tus consultas por WhatsApp"],
        ["Facultad, rol y equipo", "El administrador o el delegado", "Mostrarte lo que te corresponde y controlar permisos"],
        ["Ficha de jugador: nombre, CI, camiseta, posición, estadísticas y sanciones", "El delegado de tu equipo", "Inscribirte en campeonatos, registrar resultados y aplicar sanciones"],
        ["Contraseña", "Tú", "Se guarda cifrada con Argon2: nadie, ni el administrador, puede leerla"],
        ["Dirección IP y registro de acciones (bitácora)", "Se genera al usar el sistema", "Seguridad, auditoría y detección de accesos indebidos"],
        ["Token del celular (notificaciones push)", "Tu aplicación Android, con tu permiso", "Enviarte avisos aunque la aplicación esté cerrada"],
        ["Notificaciones recibidas", "Se generan por la actividad del sistema", "Que puedas releer tus avisos (campana)"],
      ], nota: "No recogemos datos de salud, biométricos ni de ubicación del dispositivo." },
    ] },
    { id: "bases", titulo: "3. Por qué podemos tratar tus datos", bloques: [
      ul(
        "Para cumplir la función institucional de la DUBSS de organizar las actividades deportivas de la comunidad universitaria (cuenta, inscripciones, calendario, resultados y sanciones).",
        "Con tu consentimiento, que puedes retirar cuando quieras, para los avisos por WhatsApp y para las preferencias opcionales de uso (ver la Política de cookies).",
        "Por seguridad: la bitácora y la dirección IP protegen el sistema y a las personas que lo usan.",
      ),
      p("Los resultados y la tabla de posiciones de los campeonatos son públicos: cualquier persona puede ver los nombres de equipos y, en las estadísticas, de jugadores, sin iniciar sesión."),
    ] },
    { id: "comparticion", titulo: "4. Con quién compartimos tus datos", bloques: [
      p("No vendemos tus datos ni los usamos para publicidad. Solo los compartimos con proveedores que hacen posible una función concreta, y únicamente los datos indicados:"),
      { tipo: "tabla", cabecera: ["Proveedor", "Función", "Datos que recibe"], filas: [
        ["Servicio de correo electrónico", "Enviar avisos y recordatorios", "Nombre, correo y texto del aviso"],
        ["Firebase Cloud Messaging (Google)", "Notificaciones push en el celular", "Token del dispositivo y texto del aviso"],
        ["WhatsApp Business (Meta), mediante n8n", "Avisos y consultas por WhatsApp, solo si lo activas", "Nombre, número de WhatsApp y texto del mensaje"],
        ["Groq", "Asistente y agente para el personal de gestión; transcripción de voz", "El texto de la consulta y, en los reportes por voz, el audio"],
        ["Open-Meteo", "Pronóstico del clima para programar partidos", "Solo las coordenadas del campus (ningún dato personal)"],
      ] },
      p("Podemos entregar información a las autoridades universitarias o judiciales cuando una norma o una orden legítima lo exija."),
    ] },
    { id: "plazos", titulo: "5. Cuánto tiempo conservamos los datos", bloques: [
      { tipo: "tabla", cabecera: ["Dato", "Plazo"], filas: [
        ["Cuenta, perfil y ficha de jugador", "Mientras la cuenta esté activa. Al cesar tu vínculo, la cuenta se desactiva y los datos se conservan solo el tiempo que exijan las normas de archivo institucional"],
        ["Resultados y estadísticas de campeonatos", "Se conservan como historial deportivo de la universidad"],
        ["Sesión iniciada (cookies)", "60 minutos la sesión activa; hasta 7 días el permiso de renovación, o hasta que cierres sesión"],
        ["Notificaciones de la campana", "Las leídas, 30 días; todas, 90 días"],
        ["Eventos enviados a n8n/WhatsApp", "Los entregados, 30 días; los fallidos, 90 días"],
        ["Bitácora de auditoría y aceptaciones de términos", "Se conservan por razones de seguridad y de prueba, mientras exista el sistema"],
      ] },
    ] },
    { id: "seguridad", titulo: "6. Cómo protegemos tus datos", bloques: [
      ul(
        "Contraseñas cifradas con Argon2 y bloqueo temporal de la cuenta tras varios intentos fallidos.",
        "La sesión usa cookies protegidas que el navegador no deja leer a los programas de la página (httpOnly).",
        "Cada persona solo ve lo que su rol permite; la API valida los permisos en cada petición.",
        "Las acciones importantes quedan registradas en la bitácora, y los cambios hechos por el asistente de IA requieren confirmación humana.",
        "Los mensajes entre el sistema y n8n van firmados para que no puedan alterarse ni repetirse.",
      ),
      p("Ningún sistema es infalible. Si detectamos un incidente que afecte tus datos personales, te lo comunicaremos por tu correo institucional."),
    ] },
    { id: "derechos", titulo: "7. Tus derechos y cómo ejercerlos", bloques: [
      p("Tienes derecho a conocer qué datos tuyos tratamos, a que se corrijan si son inexactos, a pedir que se eliminen cuando ya no sean necesarios, a oponerte a un uso y a retirar tu consentimiento. Estos derechos se apoyan en la protección de la privacidad que reconoce la Constitución Política del Estado (artículos 21 y 130)."),
      ul(
        "Ver y corregir tus datos: desde Mi perfil, tú mismo.",
        "Dejar de recibir WhatsApp: escribe BAJA al número del sistema o desactívalo en Mi perfil.",
        "Cambiar las preferencias de cookies: en Configurar cookies, en el pie de cualquier página.",
        `Pedir acceso, eliminación u oposición: escribe a ${R.correo} indicando tu nombre, tu correo institucional y qué solicitas. Respondemos en ${R.plazoRespuesta}.`,
      ),
      p("Algunos datos no pueden eliminarse mientras exista una obligación de conservarlos (por ejemplo, el historial de resultados o la bitácora de seguridad); en ese caso te explicaremos el motivo."),
      p("Si consideras que no atendimos tu solicitud, puedes acudir a las instancias de la universidad o, si corresponde, a la acción de protección de privacidad ante la autoridad judicial."),
    ] },
    { id: "jugadores", titulo: "8. Jugadores registrados por su delegado", bloques: [
      p("Los delegados de facultad inscriben a los jugadores de su equipo y cargan su nombre y CI. Al hacerlo, el delegado declara que cuenta con la autorización de cada jugador y que los datos son verdaderos."),
      p("Si apareces en una ficha sin haberlo autorizado, o los datos son incorrectos, escríbenos y los corregiremos o retiraremos."),
    ] },
    { id: "menores", titulo: "9. Menores de edad", bloques: [
      p("El sistema está pensado para la comunidad universitaria adulta. Si un equipo incluye a una persona menor de 18 años, su delegado debe contar con la autorización de su madre, padre o representante legal antes de registrarla."),
    ] },
    { id: "cambios", titulo: "10. Cambios en esta política", bloques: [
      p("Cuando cambiemos esta política publicaremos una nueva versión con su fecha. La primera vez que ingreses después del cambio te mostraremos un aviso y te pediremos que la aceptes de nuevo. Puedes ver qué aceptaste y cuándo en Mi perfil."),
    ] },
  ],
};

/* ───────────────────────────── Términos y condiciones ───────────────────────────── */
export const TERMINOS: Documento = {
  titulo: "Términos y condiciones de uso",
  resumen: "Las reglas para usar el sistema de gestión deportiva de la DUBSS: quién puede usarlo, qué se espera de cada rol y qué límites tienen las herramientas de inteligencia artificial.",
  secciones: [
    { id: "objeto", titulo: "1. Aceptación y objeto", bloques: [
      p(`Estos términos regulan el uso del sistema de gestión deportiva de la ${R.nombre} de la ${R.institucion} (en adelante, «el sistema»), que sirve para organizar campeonatos, programar partidos, registrar resultados, consultar estadísticas y comunicarse con los equipos.`),
      p("Al iniciar sesión por primera vez, y cada vez que publiquemos una nueva versión, te pedimos que confirmes que leíste estos términos y la Política de privacidad. Sin esa aceptación no podrás usar el panel. Si no estás de acuerdo, puedes cerrar sesión."),
      p("Las pantallas públicas (campeonatos, calendario y resultados) pueden consultarse sin cuenta; para ellas solo rige el uso lícito del sitio."),
    ] },
    { id: "quien", titulo: "2. Quién puede usar el sistema", bloques: [
      p("Las cuentas son personales y las crea o autoriza la administración de la DUBSS para personas con una función en las actividades deportivas universitarias. Los roles son:"),
      ul(
        "Superadministrador y Administrador DUBSS: configuran el sistema, los catálogos y los usuarios, y supervisan los campeonatos.",
        "Organizador: crea campeonatos, genera el fixture, registra resultados y atiende quejas.",
        "Delegado: representa a su facultad; inscribe equipos y jugadores, consulta su calendario y presenta quejas.",
        "Jugador: consulta su propia ficha, sanciones y partidos (solo lectura).",
      ),
    ] },
    { id: "cuenta", titulo: "3. Tu cuenta y su seguridad", bloques: [
      ul(
        "Eres responsable de la confidencialidad de tu contraseña y de lo que se haga con tu cuenta. No la compartas.",
        "Avísanos de inmediato si sospechas un acceso no autorizado.",
        "Tras varios intentos fallidos la cuenta se bloquea unos minutos para protegerla.",
        "Si usas un celular o una computadora compartidos, cierra sesión al terminar.",
      ),
    ] },
    { id: "uso", titulo: "4. Uso aceptable", bloques: [
      p("Te comprometes a usar el sistema solo para los fines deportivos institucionales y de forma lícita. Está prohibido:"),
      ul(
        "Registrar datos falsos o de personas sin su autorización.",
        "Intentar acceder a información de otras personas o a funciones que tu rol no permite.",
        "Alterar o intentar vulnerar la seguridad del sistema, o sobrecargarlo con peticiones automatizadas.",
        "Usar el sistema para acosar, difamar o enviar mensajes ajenos a las actividades deportivas.",
      ),
    ] },
    { id: "roles", titulo: "5. Responsabilidades según tu rol", bloques: [
      ul(
        "Delegados: la veracidad de la nómina de su equipo, la autorización de cada jugador para registrar sus datos y el cumplimiento de los plazos de inscripción.",
        "Organizadores: la exactitud de los resultados e incidencias que registran. Toda corrección queda en el historial.",
        "Administradores: el uso adecuado de los permisos de gestión de usuarios y catálogos.",
      ),
      p("Las acciones relevantes quedan registradas en una bitácora de auditoría con la fecha, la cuenta y la dirección IP."),
    ] },
    { id: "ia", titulo: "6. Predicciones, inteligencia artificial y asistente", bloques: [
      ul(
        "Las probabilidades de resultado, los niveles de los equipos y las alertas de resultados atípicos son una referencia estadística para planificar. No determinan resultados ni deciden sanciones.",
        "El asistente y el agente de IA pueden equivocarse. Nunca cambian datos por su cuenta: toda acción (reprogramar un partido, enviar un aviso) queda como propuesta y solo se aplica cuando una persona la confirma, tras revalidar que el calendario lo permite.",
        "Quien confirma una acción propuesta por el agente es responsable de ella como si la hubiera hecho manualmente.",
        "Tu consulta al asistente se procesa con un proveedor externo (ver la Política de privacidad). No escribas datos que no deban salir de la institución.",
      ),
    ] },
    { id: "avisos", titulo: "7. Notificaciones y WhatsApp", bloques: [
      p("Recibirás avisos del sistema en la campana, por correo y, si instalaste la aplicación Android, como notificación en el celular. Los avisos por WhatsApp son opcionales: solo se activan si das tu número y los aceptas en Mi perfil, y puedes dejar de recibirlos escribiendo BAJA."),
    ] },
    { id: "planilla", titulo: "8. Planilla móvil y uso sin conexión", bloques: [
      p("La planilla guarda en tu dispositivo lo que anotas si no hay internet y lo envía al volver la conexión. Es tu responsabilidad abrir la planilla con conexión al menos una vez antes del partido para descargar los datos y revisar, al terminar, que no queden acciones pendientes de enviar."),
    ] },
    { id: "propiedad", titulo: "9. Propiedad intelectual", bloques: [
      p("El escudo y el nombre de la DUBSS y de la UAGRM pertenecen a la universidad. El software del sistema pertenece a sus autores y se pone a disposición de la DUBSS para su uso institucional. No puedes copiar, modificar o redistribuir el sistema sin autorización."),
    ] },
    { id: "disponibilidad", titulo: "10. Disponibilidad y responsabilidad", bloques: [
      p("Hacemos lo posible por mantener el sistema disponible, pero puede haber interrupciones por mantenimiento o fallas ajenas a nuestro control. El sistema se ofrece como herramienta de apoyo: la DUBSS no responde por daños indirectos derivados de una interrupción, ni por datos incorrectos cargados por los usuarios."),
    ] },
    { id: "suspension", titulo: "11. Suspensión de cuentas", bloques: [
      p("La administración puede suspender o desactivar una cuenta si se incumplen estos términos, si hay un riesgo de seguridad o si termina el vínculo de la persona con la actividad deportiva. Conservamos el historial deportivo y la bitácora conforme a la Política de privacidad."),
    ] },
    { id: "cambios", titulo: "12. Cambios en los términos", bloques: [
      p("Podemos actualizar estos términos. Cada versión tiene una fecha; cuando cambie, te pediremos que la aceptes de nuevo en tu próximo ingreso. Puedes consultar las versiones que aceptaste en Mi perfil."),
    ] },
    { id: "ley", titulo: "13. Ley aplicable y contacto", bloques: [
      p(`Estos términos se rigen por las leyes del Estado Plurinacional de Bolivia. Para cualquier consulta escribe a ${R.correo} o acude a ${R.direccion}.`),
    ] },
  ],
};

/* ───────────────────────────── Política de cookies ───────────────────────────── */
export const COOKIES: Documento = {
  titulo: "Política de cookies",
  resumen: "Qué cookies y almacenamiento local usa el sistema, para qué sirve cada uno y cómo puedes elegir cuáles permites.",
  secciones: [
    { id: "que", titulo: "1. Qué son las cookies y el almacenamiento local", bloques: [
      p("Una cookie es un pequeño archivo que el navegador guarda en tu dispositivo. El almacenamiento local (localStorage e IndexedDB) cumple una función parecida. Los usamos para que puedas iniciar sesión, usar la planilla sin conexión y, si lo permites, recordar tus preferencias."),
      p("No usamos cookies de publicidad ni de seguimiento, no usamos herramientas de analítica de terceros y no compartimos información de tu navegación con redes publicitarias."),
    ] },
    { id: "categorias", titulo: "2. Categorías y tu elección", bloques: [
      { tipo: "tabla", cabecera: ["Categoría", "Qué incluye", "¿Puedes rechazarla?"], filas: [
        ["Necesarias", "Mantener tu sesión, recordar tu elección de cookies y permitir el uso sin conexión de la planilla", "No: sin ellas el sistema no funciona. Por eso no requieren tu permiso"],
        ["Preferencias", "Recordar cómo prefieres ver el sistema (por ejemplo, el menú lateral contraído)", "Sí. Si las rechazas, el sistema funciona igual pero no recuerda esos ajustes"],
        ["Analítica y publicidad", "No utilizamos ninguna", "No aplica"],
      ] },
      p("Tu elección se guarda en una cookie propia durante 12 meses. Puedes cambiarla cuando quieras con «Configurar cookies», en el pie de cualquier página. Si cambiamos las categorías, te volveremos a preguntar."),
    ] },
    { id: "lista", titulo: "3. Lista detallada", bloques: [
      { tipo: "tabla", cabecera: ["Nombre", "Tipo", "Categoría", "Duración", "Para qué sirve"], filas: [
        ["access_token", "Cookie propia (httpOnly)", "Necesaria", "60 minutos", "Identifica tu sesión activa"],
        ["refresh_token", "Cookie propia (httpOnly)", "Necesaria", "7 días o hasta cerrar sesión", "Renueva tu sesión sin pedirte la contraseña"],
        ["dubss_consent", "Cookie propia", "Necesaria", "12 meses", "Guarda tu elección sobre las cookies"],
        ["dubss:planilla:usuario", "localStorage", "Necesaria", "Hasta cerrar sesión", "Sabe de quién son los datos guardados para la planilla sin conexión"],
        ["dubss-planilla", "IndexedDB", "Necesaria", "Hasta cerrar sesión", "Guarda los partidos descargados y las acciones pendientes de enviar"],
        ["Caché de la aplicación", "Service worker", "Necesaria", "Hasta que se actualice la aplicación", "Guarda los archivos de la aplicación para abrirla sin conexión (nunca datos privados)"],
        ["dubss.menu.colapsado", "localStorage", "Preferencias", "Hasta que lo borres", "Recuerda si prefieres el menú lateral contraído"],
      ] },
    ] },
    { id: "como", titulo: "4. Cómo gestionarlas desde tu navegador", bloques: [
      p("Además de nuestro panel, puedes ver y borrar cookies y datos del sitio desde la configuración de tu navegador (Chrome, Edge, Firefox o Safari). Si bloqueas las necesarias, no podrás iniciar sesión."),
      p("En la aplicación Android de la DUBSS rige esta misma política: la aplicación muestra el sistema dentro de un navegador integrado. Puedes borrar los datos desde Ajustes del celular → Aplicaciones → DUBSS → Almacenamiento."),
    ] },
    { id: "cambios", titulo: "5. Cambios y contacto", bloques: [
      p(`Actualizaremos esta política si cambia el uso de cookies. Para cualquier consulta escribe a ${R.correo}.`),
    ] },
  ],
};
