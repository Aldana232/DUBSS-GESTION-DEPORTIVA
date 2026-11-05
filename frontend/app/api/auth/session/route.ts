import { NextResponse, type NextRequest } from "next/server";
import {
  ACCESS_COOKIE, API_URL, REFRESH_COOKIE, borrarTokens, fijarTokens, renovarTokens,
} from "@/lib/server/session";

export const dynamic = "force-dynamic";

const consultar = (access: string) =>
  fetch(`${API_URL}/me/`, { headers: { Authorization: `Bearer ${access}` }, cache: "no-store" });

/** Devuelve el usuario de la sesión (rol y facultad frescos desde la API), renovando el token si hace falta. */
export async function GET(req: NextRequest) {
  let access = req.cookies.get(ACCESS_COOKIE)?.value;
  const refresh = req.cookies.get(REFRESH_COOKIE)?.value;
  let nuevos: { access: string; refresh: string } | null = null;

  let r = access ? await consultar(access).catch(() => null) : null;
  if ((!r || r.status === 401) && refresh) {
    nuevos = await renovarTokens(refresh);
    if (nuevos) {
      access = nuevos.access;
      r = await consultar(access).catch(() => null);
    }
  }
  if (!r || !r.ok) {
    // 200 con usuario nulo: el visitante anónimo es un caso normal, no un error.
    const res = NextResponse.json({ usuario: null });
    if (r?.status === 401 || !access) borrarTokens(res);
    return res;
  }
  const res = NextResponse.json({ usuario: await r.json() });
  if (nuevos) fijarTokens(res, nuevos.access, nuevos.refresh);
  return res;
}
