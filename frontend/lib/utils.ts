import clsx, { type ClassValue } from "clsx";

export const cn = (...inputs: ClassValue[]) => clsx(inputs);

const LOCALE = "es-BO";

export const fechaCorta = (iso?: string | null) =>
  iso ? new Date(iso).toLocaleDateString(LOCALE, { day: "2-digit", month: "short", year: "numeric" }) : "—";

export const fechaDia = (iso?: string | null) =>
  iso ? new Date(iso).toLocaleDateString(LOCALE, { day: "numeric", month: "short" }) : "—";

export const fechaLarga = (iso?: string | null) =>
  iso ? new Date(iso).toLocaleDateString(LOCALE, { weekday: "long", day: "numeric", month: "long" }) : "—";

export const hora = (iso?: string | null) =>
  iso ? new Date(iso).toLocaleTimeString(LOCALE, { hour: "2-digit", minute: "2-digit" }) : "—";

/** Códigos de la API con tilde o redacción propia; el resto se convierte automáticamente (ABIERTA → Abierta). */
const ETIQUETAS: Record<string, string> = {
  ELIMINACION: "Eliminación directa", LIGA: "Liga", INSCRIPCION_CERRADA: "Inscripciones cerradas", PLANIFICACION: "Planificación",
  EN_REVISION: "En revisión", APELACION: "Apelación", LESION: "Lesión", SUSTITUCION: "Sustitución", ADMIN_DUBSS: "Administrador DUBSS",
};

export const etiqueta = (valor?: string | null) =>
  valor ? (ETIQUETAS[valor] ?? valor.replace(/_/g, " ").toLowerCase().replace(/^\w/, (c) => c.toUpperCase())) : "—";

/** ISO → valor de <input type="datetime-local"> en la hora local del navegador. */
export const aInputFechaHora = (iso?: string | null) => {
  if (!iso) return "";
  const d = new Date(iso);
  const dos = (n: number) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${dos(d.getMonth() + 1)}-${dos(d.getDate())}T${dos(d.getHours())}:${dos(d.getMinutes())}`;
};

/** Valor de <input type="datetime-local"> → ISO con zona horaria (la API exige fechas con zona). */
export const deInputFechaHora = (valor?: string | null) => (valor ? new Date(valor).toISOString() : null);

export const DIAS_SEMANA = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"];
