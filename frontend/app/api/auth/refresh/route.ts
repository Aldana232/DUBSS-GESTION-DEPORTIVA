import { NextResponse, type NextRequest } from "next/server";
import { REFRESH_COOKIE, borrarTokens, fijarTokens, renovarTokens } from "@/lib/server/session";

export const dynamic = "force-dynamic";

/** Renueva la sesión con el refresh guardado en cookie (rotación incluida). */
export async function POST(req: NextRequest) {
  const refresh = req.cookies.get(REFRESH_COOKIE)?.value;
  const nuevos = refresh ? await renovarTokens(refresh) : null;
  if (!nuevos) {
    const res = NextResponse.json({ detail: "La sesión expiró. Inicia sesión de nuevo." }, { status: 401 });
    borrarTokens(res);
    return res;
  }
  const res = NextResponse.json({ ok: true });
  fijarTokens(res, nuevos.access, nuevos.refresh);
  return res;
}
