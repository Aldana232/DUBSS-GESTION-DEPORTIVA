/**
 * Datos de los documentos legales (/terminos, /privacidad, /cookies).
 * LEGAL_VERSION debe coincidir con LEGAL_VERSION del backend (config/settings/base.py): al cambiarla en los DOS
 * lugares, todas las personas vuelven a ver el cuadro de aceptación en su próximo ingreso.
 */
export const LEGAL_VERSION = "2026-11-15";
export const LEGAL_VIGENTE_DESDE = "15 de noviembre de 2026";
export const COOKIES_VERSION = "1";          // sube al cambiar las categorías de cookies: se vuelve a pedir la elección

/** Responsable del tratamiento de los datos personales. */
export const RESPONSABLE = {
  nombre: "Dirección Universitaria de Bienestar Social y Salud (D.U.B.S.S.)",
  institucion: "Universidad Autónoma Gabriel René Moreno (UAGRM)",
  direccion: "Av. Busch, Ciudad Universitaria (lado comedor universitario, Mod. 292), Santa Cruz de la Sierra, Bolivia",
  correo: "dubss@uagrm.edu.bo",
  telefono: "60040944",
  horario: "lunes a viernes, de 9:00 a 16:00",
  plazoRespuesta: "diez (10) días hábiles",
} as const;

export const DOCUMENTOS_LEGALES = [
  { ruta: "/privacidad", titulo: "Política de privacidad" },
  { ruta: "/terminos", titulo: "Términos y condiciones" },
  { ruta: "/cookies", titulo: "Política de cookies" },
] as const;
