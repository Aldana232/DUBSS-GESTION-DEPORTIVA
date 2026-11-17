/**
 * Consentimiento de cookies. La elección se guarda en una cookie propia («dubss_consent», 12 meses) con la versión
 * de la política: si las categorías cambian (COOKIES_VERSION), la elección anterior deja de valer y se vuelve a preguntar.
 *
 * Categorías: «necesarias» (no requieren permiso) y «preferencias» (opcionales). No hay analítica ni publicidad.
 * Mientras la persona no elija, NO se guarda ninguna preferencia opcional.
 */
import { COOKIES_VERSION } from "./legal.config";

export const COOKIE_CONSENTIMIENTO = "dubss_consent";
export const EVENTO_CONSENTIMIENTO = "dubss:consentimiento";
export const EVENTO_ABRIR_PANEL = "dubss:cookies-abrir";
const MESES = 12;

/** Claves de almacenamiento local de la categoría «preferencias»: se borran si se rechaza. */
export const CLAVES_PREFERENCIAS = ["dubss.menu.colapsado"];

export interface Consentimiento { v: string; preferencias: boolean; t: number }

function leerCookie(nombre: string): string | null {
  if (typeof document === "undefined") return null;
  const par = document.cookie.split("; ").find((c) => c.startsWith(nombre + "="));
  return par ? par.slice(nombre.length + 1) : null;
}

/** La elección vigente, o null si nunca eligió, está vencida o es de una versión anterior de la política. */
export function leerConsentimiento(): Consentimiento | null {
  try {
    const bruto = leerCookie(COOKIE_CONSENTIMIENTO);
    if (!bruto) return null;
    const c = JSON.parse(decodeURIComponent(bruto)) as Consentimiento;
    if (c.v !== COOKIES_VERSION || typeof c.preferencias !== "boolean") return null;
    if (Date.now() - c.t > MESES * 31 * 86400_000) return null;
    return c;
  } catch {
    return null;
  }
}

export function guardarConsentimiento(preferencias: boolean): Consentimiento {
  const c: Consentimiento = { v: COOKIES_VERSION, preferencias, t: Date.now() };
  const seguro = typeof location !== "undefined" && location.protocol === "https:" ? "; Secure" : "";
  document.cookie = `${COOKIE_CONSENTIMIENTO}=${encodeURIComponent(JSON.stringify(c))}; Max-Age=${MESES * 30 * 86400}; Path=/; SameSite=Lax${seguro}`;
  if (!preferencias) borrarPreferencias();
  window.dispatchEvent(new Event(EVENTO_CONSENTIMIENTO));
  return c;
}

export function borrarPreferencias(): void {
  try { CLAVES_PREFERENCIAS.forEach((k) => localStorage.removeItem(k)); } catch { /* sin almacenamiento */ }
}

/** ¿Se pueden guardar preferencias opcionales? Solo si la persona lo permitió expresamente. */
export const preferenciasPermitidas = (): boolean => leerConsentimiento()?.preferencias === true;

export const abrirPanelCookies = (): void => { window.dispatchEvent(new Event(EVENTO_ABRIR_PANEL)); };
