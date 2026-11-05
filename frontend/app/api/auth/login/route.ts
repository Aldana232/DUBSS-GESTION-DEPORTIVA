import { NextResponse, type NextRequest } from "next/server";
import { API_URL, cabecerasDeOrigen, fijarTokens } from "@/lib/server/session";

export const dynamic = "force-dynamic";

/** Inicia sesión en Django y guarda los tokens en cookies httpOnly. Devuelve solo el usuario. */
export async function POST(req: NextRequest) {
  const cuerpo = await req.text();
  let r: Response;
  try {
    r = await fetch(`${API_URL}/auth/login/`, {
      method: "POST",
      headers: { "Content-Type": "application/json", ...cabecerasDeOrigen(req) },
      body: cuerpo,
      cache: "no-store",
    });
  } catch {
    return NextResponse.json({ detail: "No se pudo conectar con el servidor. Intenta de nuevo." }, { status: 502 });
  }
  const data = await r.json().catch(() => ({}));
  if (!r.ok) {
    const res = NextResponse.json(data, { status: r.status });
    const espera = r.headers.get("Retry-After");
    if (espera) res.headers.set("Retry-After", espera);
    return res;
  }
  const res = NextResponse.json({ usuario: data.usuario });
  fijarTokens(res, data.access, data.refresh);
  return res;
}
