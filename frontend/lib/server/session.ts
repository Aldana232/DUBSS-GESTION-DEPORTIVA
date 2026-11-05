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
  secure: process.env.NODE_ENV === "production",
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

/** IP del visitante para que el límite de intentos de Django no cuente a todos como una sola. */
export function cabecerasDeOrigen(req: NextRequest): Record<string, string> {
  const previa = req.headers.get("x-forwarded-for");
  const ip = req.ip ?? previa?.split(",")[0]?.trim();
  return ip ? { "X-Forwarded-For": ip } : {};
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
