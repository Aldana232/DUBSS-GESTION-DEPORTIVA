/**
 * Datos del sitio web corporativo (/corporativo). Edita SOLO este archivo para completar
 * los datos de la empresa: lo que quede vacío se muestra como "Por confirmar".
 */
export const EMPRESA = {
  nombre: "SPORTECH-DUBSS S.R.L.", // denominación provisional: cambiar por la razón social definitiva
  producto: "SportTech DUBSS",
  ciudad: "Santa Cruz de la Sierra, Bolivia",
  whatsapp: "", // solo dígitos con código de país, ej.: 5917XXXXXXX
  email: "", // correo de contacto de la empresa
  horarioCorreo: "", // ej.: "Lunes a viernes, 08:00 a 18:00"
  horarioWhatsapp: "",
  respuestaCorreo: "", // ej.: "Máximo 8 horas hábiles"
  respuestaWhatsapp: "",
  appUrl: "", // dirección pública de la plataforma (cuando esté desplegada)
  manualUrl: "", // enlace al manual de usuario (PDF)
  fichaUrl: "/corporativo/ficha-tecnica-sporttech-dubss.pdf",
} as const;

/** Dirección usuaria. Datos públicos de la DUBSS, usados con su autorización para este proyecto. */
export const DUBSS = {
  nombre: "Dirección Universitaria de Bienestar Social y Salud",
  sigla: "D.U.B.S.S.",
  direccion: "Av. Busch, Ciudad Universitaria (lado comedor universitario, Mod. 292), Santa Cruz de la Sierra, Bolivia",
  telefono: "60040944",
  correo: "dubss@uagrm.edu.bo",
  horario: "9:00 a 16:00 (oficinas)",
  redes: [
    { etiqueta: "Facebook", href: "https://www.facebook.com/DireccionUniversitariaDeBienestarSocial" },
    { etiqueta: "Instagram", href: "https://www.instagram.com/dubs_uagrm" },
    { etiqueta: "TikTok", href: "https://www.tiktok.com/@dubs.oficial.uagrm" },
    { etiqueta: "Linktree", href: "https://linktr.ee/dubssoficial" },
  ],
} as const;

export const POR_CONFIRMAR = "Por confirmar";
