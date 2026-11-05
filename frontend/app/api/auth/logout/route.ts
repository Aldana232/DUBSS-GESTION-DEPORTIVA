import { NextResponse, type NextRequest } from "next/server";
import { ACCESS_COOKIE, API_URL, REFRESH_COOKIE, borrarTokens, cabecerasDeOrigen } from "@/lib/server/session";

export const dynamic = "force-dynamic";

/** Invalida el refresh en Django (lista negra) y borra las cookies. */
export async function POST(req: NextRequest) {
  const refresh = req.cookies.get(REFRESH_COOKIE)?.value;
  const access = req.cookies.get(ACCESS_COOKIE)?.value;
  if (refresh && access) {
    try {
      await fetch(`${API_URL}/auth/logout/`, {
        method: "POST",
        headers: { "Content-Type": "application/json", Authorization: `Bearer ${access}`, ...cabecerasDeOrigen(req) },
        body: JSON.stringify({ refresh }),
        cache: "no-store",
      });
    } catch {
      /* aunque Django no responda, la sesión local se cierra igual */
    }
  }
  const res = NextResponse.json({ ok: true });
  borrarTokens(res);
  return res;
}
