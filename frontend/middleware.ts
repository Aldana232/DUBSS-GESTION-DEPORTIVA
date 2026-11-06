import { NextRequest, NextResponse } from "next/server";
import { ROLE_HOME, esRutaPublica, rolesPermitidos, type Rol } from "@/lib/auth/roles";

/**
 * Solo enruta y redirige (UX). La seguridad real la aplica la API de Django:
 * el JWT se decodifica aquí únicamente para leer `exp` y `rol`, sin verificar la firma.
 */
function leerJwt(token?: string): { exp?: number; rol?: Rol } | null {
  if (!token) return null;
  try {
    const parte = token.split(".")[1].replace(/-/g, "+").replace(/_/g, "/");
    return JSON.parse(atob(parte.padEnd(Math.ceil(parte.length / 4) * 4, "=")));
  } catch {
    return null;
  }
}

export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;
  const access = leerJwt(request.cookies.get("access_token")?.value);
  const vigente = !!access?.exp && access.exp * 1000 > Date.now();
  // Con refresh disponible se deja pasar: la primera llamada a la API renueva el access.
  const renovable = !!request.cookies.get("refresh_token")?.value;
  const autenticado = vigente || renovable;
  const rol = vigente ? access?.rol : undefined;

  // Error de tipeo frecuente al compartir el enlace ("/corporativo," o "/corporativo."): lleva al sitio, no al login.
  let ruta = pathname;
  try { ruta = decodeURIComponent(pathname); } catch { /* ruta mal codificada: se evalúa tal cual */ }
  if (/^\/corporativo[^\w/%-]+$/.test(ruta)) {
    return NextResponse.redirect(new URL("/corporativo", request.url));
  }

  if (pathname === "/login") {
    if (autenticado) return NextResponse.redirect(new URL((rol && ROLE_HOME[rol]) || "/gestion", request.url));
    return NextResponse.next();
  }
  if (esRutaPublica(pathname)) return NextResponse.next();

  if (!autenticado) {
    const url = new URL("/login", request.url);
    url.searchParams.set("redirect", pathname);
    return NextResponse.redirect(url);
  }
  // Guardia por rol (solo con el access vigente; si hay que renovar, decide RequireRole en el cliente).
  const permitidos = rolesPermitidos(pathname);
  if (rol && permitidos && !permitidos.includes(rol)) {
    return NextResponse.redirect(new URL(ROLE_HOME[rol], request.url));
  }
  return NextResponse.next();
}

export const config = {
  // Excluye API (los route handlers gestionan su propia sesión), estáticos e imágenes.
  matcher: ["/((?!api/|_next/static|_next/image|favicon.ico|sw\\.js|manifest\\.webmanifest|offline\\.html|.*\\.(?:png|jpg|jpeg|svg|webp|ico)$).*)"],
};
