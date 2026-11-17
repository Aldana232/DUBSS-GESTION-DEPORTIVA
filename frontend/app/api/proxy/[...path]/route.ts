import { NextResponse, type NextRequest } from "next/server";
import {
  ACCESS_COOKIE, API_URL, REFRESH_COOKIE, borrarTokens, cabecerasDeOrigen, fijarTokens, renovarTokens,
} from "@/lib/server/session";

export const dynamic = "force-dynamic";

// Desde Next 15 los parámetros de la ruta llegan como una promesa.
type Contexto = { params: Promise<{ path: string[] }> };

/**
 * Proxy hacia Django: agrega el Bearer desde la cookie httpOnly y, si el access expiró,
 * renueva la sesión una vez y reintenta. El navegador nunca ve los tokens.
 * Si la sesión ya no sirve, las lecturas (GET) se reintentan como visitante anónimo para que
 * la parte pública del sitio siga funcionando.
 */
async function reenviar(req: NextRequest, { params }: Contexto) {
  const { path } = await params;
  const barra = req.nextUrl.pathname.endsWith("/") ? "/" : "";
  const destino = `${API_URL}/${path.join("/")}${barra}${req.nextUrl.search}`;
  const esLectura = ["GET", "HEAD"].includes(req.method);
  const cuerpo = esLectura ? undefined : await req.arrayBuffer();

  const llamar = (access?: string) => {
    const headers: Record<string, string> = { ...cabecerasDeOrigen(req) };
    const tipo = req.headers.get("content-type");
    if (tipo) headers["Content-Type"] = tipo;
    const clave = req.headers.get("idempotency-key");
    if (clave) headers["Idempotency-Key"] = clave;
    if (access) headers.Authorization = `Bearer ${access}`;
    return fetch(destino, { method: req.method, headers, body: cuerpo, cache: "no-store" });
  };

  let access = req.cookies.get(ACCESS_COOKIE)?.value;
  const refresh = req.cookies.get(REFRESH_COOKIE)?.value;
  let nuevos: { access: string; refresh: string } | null = null;
  let sesionCaida = false;
  let r: Response;
  try {
    r = await llamar(access);
    if (r.status === 401 && access) {
      nuevos = refresh ? await renovarTokens(refresh) : null;
      if (nuevos) {
        access = nuevos.access;
        r = await llamar(access);
      } else {
        sesionCaida = true;
        if (esLectura) r = await llamar(undefined);
      }
    }
  } catch {
    return NextResponse.json({ detail: "No se pudo conectar con el servidor." }, { status: 502 });
  }

  const headers = new Headers();
  for (const nombre of ["content-type", "content-disposition", "retry-after", "idempotent-replayed"]) {
    const valor = r.headers.get(nombre);
    if (valor) headers.set(nombre, valor);
  }
  const res = new NextResponse(r.status === 204 ? null : await r.arrayBuffer(), { status: r.status, headers });
  if (nuevos) fijarTokens(res, nuevos.access, nuevos.refresh);
  else if (sesionCaida) borrarTokens(res);
  return res;
}

export { reenviar as GET, reenviar as POST, reenviar as PUT, reenviar as PATCH, reenviar as DELETE };
