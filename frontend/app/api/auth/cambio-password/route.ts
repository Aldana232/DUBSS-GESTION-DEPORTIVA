import { NextResponse, type NextRequest } from "next/server";
import { ACCESS_COOKIE, API_URL, cabecerasDeOrigen, fijarTokens } from "@/lib/server/session";

export const dynamic = "force-dynamic";

/**
 * Cambia la contraseña. Django invalida todos los tokens anteriores y devuelve un par nuevo:
 * se guarda en las cookies httpOnly para que la sesión actual siga viva.
 */
export async function POST(req: NextRequest) {
  const access = req.cookies.get(ACCESS_COOKIE)?.value;
  if (!access) return NextResponse.json({ detail: "Tu sesión expiró. Inicia sesión de nuevo." }, { status: 401 });
  let r: Response;
  try {
    r = await fetch(`${API_URL}/auth/cambio-password/`, {
      method: "POST",
      headers: { "Content-Type": "application/json", Authorization: `Bearer ${access}`, ...cabecerasDeOrigen(req) },
      body: await req.text(),
      cache: "no-store",
    });
  } catch {
    return NextResponse.json({ detail: "No se pudo conectar con el servidor." }, { status: 502 });
  }
  const data = await r.json().catch(() => ({}));
  if (!r.ok) return NextResponse.json(data, { status: r.status });
  const res = NextResponse.json({ mensaje: data.mensaje });
  fijarTokens(res, data.access, data.refresh);
  return res;
}
