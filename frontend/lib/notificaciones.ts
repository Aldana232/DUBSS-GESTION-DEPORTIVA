import type { Notificacion } from "@/types";

/** A dónde lleva una notificación al tocarla. Solo rutas internas: nunca se sigue una dirección externa. */
export function rutaDeNotificacion(datos: Notificacion["datos"] | undefined): string {
  const url = typeof datos?.url === "string" ? datos.url : "";
  if (url.startsWith("/") && !url.startsWith("//")) return url;
  const id = Number(datos?.partido_id);
  if (Number.isInteger(id) && id > 0) return `/partidos/${id}`;     // la ficha pública del partido existe para todos los roles
  return "/notificaciones";
}

/** «hace 5 min», «ayer 18:30»… en español y sin librerías. */
export function hace(iso: string, ahora: Date = new Date()): string {
  const f = new Date(iso);
  const min = Math.floor((ahora.getTime() - f.getTime()) / 60000);
  if (min < 1) return "ahora";
  if (min < 60) return `hace ${min} min`;
  const h = Math.floor(min / 60);
  if (h < 24) return `hace ${h} h`;
  const d = Math.floor(h / 24);
  if (d === 1) return "ayer";
  if (d < 7) return `hace ${d} días`;
  return f.toLocaleDateString("es-BO", { day: "numeric", month: "short" });
}
