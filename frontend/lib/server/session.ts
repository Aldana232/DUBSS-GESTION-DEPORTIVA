/**
 * Utilidades de servidor para la sesión con cookies httpOnly (F4-05).
 * Solo se importa desde route handlers: los tokens nunca llegan al JavaScript del navegador.
 */
import { NextResponse, type NextRequest } from "next/server";

export const ACCESS_COOKIE = "access_token";
export const REFRESH_COOKIE = "refresh_token";

/** URL de Django vista desde el servidor de Next (en Docker puede ser http://backend:8000/api/v1). */
export const API_URL = (
  process.env.API_INTERNAL_URL ?? process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1"
).replace(/\/$/, "");

const REFRESH_DIAS = 7;
const ACCESS_MINUTOS_MAX = 60;

const baseCookie = {
  httpOnly: true,
  sameSite: "lax" as const,
  // «Secure» solo viaja por https. En producción real siempre; para probar la app Android por http (red local) se
  // apaga con COOKIE_SECURE=false (docker-compose.rapido.yml lo hace). Nunca apagarlo en un servidor público.
  secure: process.env.COOKIE_SECURE ? process.env.COOKIE_SECURE === "true" : process.env.NODE_ENV === "production",
  path: "/",
};

export function fijarTokens(res: NextResponse, access: string, refresh?: string) {
  res.cookies.set(ACCESS_COOKIE, access, { ...baseCookie, maxAge: ACCESS_MINUTOS_MAX * 60 });
  if (refresh) res.cookies.set(REFRESH_COOKIE, refresh, { ...baseCookie, maxAge: REFRESH_DIAS * 86400 });
}

export function borrarTokens(res: NextResponse) {
  res.cookies.set(ACCESS_COOKIE, "", { ...baseCookie, maxAge: 0 });
  res.cookies.set(REFRESH_COOKIE, "", { ...baseCookie, maxAge: 0 });
}

/**
 * Datos del visitante que Django necesita aunque la llamada salga de Next por la red interna:
 *  - IP real, para que el límite de intentos de acceso no cuente a todos como una sola.
 *  - Host y protocolo PÚBLICOS, para que Django arme bien las URLs absolutas (fotos y logos) en lugar de
 *    «http://backend:8000/...», que el navegador no puede abrir.
 * Detrás de Caddy llegan en X-Forwarded-*; Caddy descarta lo que mande el cliente. Next 15 quitó `req.ip`.
 */
export function cabecerasDeOrigen(req: NextRequest): Record<string, string> {
  const cab: Record<string, string> = {};
  const ip = req.headers.get("x-forwarded-for")?.split(",")[0]?.trim() ?? req.headers.get("x-real-ip");
  if (ip) cab["X-Forwarded-For"] = ip;
  const host = req.headers.get("x-forwarded-host") ?? req.headers.get("host");
  if (host) cab["X-Forwarded-Host"] = host;
  const proto = req.headers.get("x-forwarded-proto") ?? req.nextUrl.protocol.replace(":", "");
  if (proto) cab["X-Forwarded-Proto"] = proto;
  return cab;
}

export async function renovarTokens(refresh: string): Promise<{ access: string; refresh: string } | null> {
  try {
    const r = await fetch(`${API_URL}/auth/token/refresh/`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refresh }),
      cache: "no-store",
    });
    if (!r.ok) return null;
    const data = (await r.json()) as { access: string; refresh?: string };
    return { access: data.access, refresh: data.refresh ?? refresh };
  } catch {
    return null;
  }
}
