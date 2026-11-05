/*
 * Service worker de la DUBSS (F7-05).
 *
 * Qué guarda: SOLO el "esqueleto" de la aplicación (HTML de /planilla, scripts, estilos, fuentes e íconos) para que
 * abra sin conexión. Los datos de partidos y personas NO pasan por aquí: la propia app los guarda en IndexedDB.
 *
 * Qué NO guarda nunca: nada de /api/ (ni datos ni sesión), ni respuestas POST, ni páginas del panel con datos.
 * Estrategias: scripts/estilos/íconos -> caché primero; /planilla -> red primero con respaldo en caché;
 * cualquier otra navegación -> red, y si no hay red, la página "sin conexión".
 */
const VERSION = "v1";
const CACHE_APP = `dubss-app-${VERSION}`;
const CACHE_ESTATICOS = `dubss-estaticos-${VERSION}`;
const PAGINA_SIN_CONEXION = "/offline.html";
const CLAVE_PLANILLA = "/planilla";
const MAX_ESTATICOS = 200;

self.addEventListener("install", (evento) => {
  evento.waitUntil(
    caches.open(CACHE_APP).then((c) => c.addAll([PAGINA_SIN_CONEXION, "/logo-dubss.png", "/icons/icon-192.png"])).then(() => self.skipWaiting()),
  );
});

self.addEventListener("activate", (evento) => {
  evento.waitUntil(
    caches.keys()
      .then((nombres) => Promise.all(nombres.filter((n) => ![CACHE_APP, CACHE_ESTATICOS].includes(n)).map((n) => caches.delete(n))))
      .then(() => self.clients.claim()),
  );
});

async function recortar(cache) {
  const claves = await cache.keys();
  if (claves.length > MAX_ESTATICOS) await Promise.all(claves.slice(0, claves.length - MAX_ESTATICOS).map((c) => cache.delete(c)));
}

async function cachePrimero(peticion) {
  const cache = await caches.open(CACHE_ESTATICOS);
  const guardada = await cache.match(peticion);
  if (guardada) return guardada;
  const respuesta = await fetch(peticion);
  if (respuesta.ok) {
    cache.put(peticion, respuesta.clone());
    recortar(cache);
  }
  return respuesta;
}

async function navegacion(peticion, url) {
  const esPlanilla = url.pathname === CLAVE_PLANILLA;
  try {
    const respuesta = await fetch(peticion);
    // Solo se guarda el esqueleto de la planilla, y solo si se sirvió de verdad (no una redirección al login).
    if (esPlanilla && respuesta.ok && !respuesta.redirected) (await caches.open(CACHE_APP)).put(CLAVE_PLANILLA, respuesta.clone());
    return respuesta;
  } catch {
    if (esPlanilla) {
      const guardada = await (await caches.open(CACHE_APP)).match(CLAVE_PLANILLA);
      if (guardada) return guardada;
    }
    return (await (await caches.open(CACHE_APP)).match(PAGINA_SIN_CONEXION)) || Response.error();
  }
}

self.addEventListener("fetch", (evento) => {
  const peticion = evento.request;
  if (peticion.method !== "GET") return;
  const url = new URL(peticion.url);
  if (url.origin !== self.location.origin) return;
  if (url.pathname.startsWith("/api/")) return;                                // datos y sesión: jamás por la caché

  if (peticion.mode === "navigate") {
    evento.respondWith(navegacion(peticion, url));
    return;
  }
  if (url.pathname.startsWith("/_next/static/") || url.pathname.startsWith("/icons/") || /\.(?:png|svg|ico|webp|woff2?)$/.test(url.pathname)) {
    evento.respondWith(cachePrimero(peticion));
  }
});

/*
 * La primera visita no pasa por el service worker (aún no controlaba la página). Para que la planilla abra sin
 * conexión desde la segunda vez, la página le pide guardar lo que ya cargó (solo /_next/static) y el HTML de /planilla.
 */
async function precargar(urls) {
  const estaticos = await caches.open(CACHE_ESTATICOS);
  await Promise.all(urls.filter((u) => u.startsWith("/_next/static/")).map(async (u) => {
    try { if (!(await estaticos.match(u))) { const r = await fetch(u); if (r.ok) await estaticos.put(u, r); } } catch { /* sin red: se guardará luego */ }
  }));
  if (urls.includes(CLAVE_PLANILLA)) {
    try {
      const r = await fetch(CLAVE_PLANILLA, { credentials: "same-origin" });
      if (r.ok && !r.redirected) await (await caches.open(CACHE_APP)).put(CLAVE_PLANILLA, r);
    } catch { /* sin red */ }
  }
}

self.addEventListener("message", (evento) => {
  if (evento.data === "SALTAR_ESPERA") self.skipWaiting();
  if (evento.data && evento.data.tipo === "PRECARGAR" && Array.isArray(evento.data.urls)) evento.waitUntil(precargar(evento.data.urls));
});
