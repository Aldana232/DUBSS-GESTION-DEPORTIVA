/**
 * Sincronizador de la planilla (F7-06).
 *
 * Reglas:
 *  - Las acciones se guardan primero en el celular y se envían en el orden en que se hicieron.
 *  - Cada acción lleva su propia Idempotency-Key: reenviarla jamás la duplica en el servidor.
 *  - Sin red / servidor caído / 429: se reintenta más tarde (la acción sigue PENDIENTE).
 *  - 401 (sesión vencida): se pausa y se pide iniciar sesión; no se pierde nada.
 *  - 409 (otra persona ya cerró el partido): CONFLICTO, esperando decisión de la persona.
 *  - Otro 4xx (dato inválido, jugador sancionado...): ERROR, con el motivo que dio el servidor.
 *  - Tras un envío exitoso, el paquete local se actualiza con la respuesta del servidor.
 */
import { useSyncExternalStore } from "react";
import { colaDB, paqueteDB, suscribirCambios, type Operacion, type TipoOperacion } from "@/lib/offline/db";

export const MARGEN_PARA_DESHACER_MS = 5000;
const INTERVALO_REINTENTO_MS = 30_000;
const TIEMPO_MAXIMO_MS = 20_000;

export interface EstadoSync {
  enLinea: boolean;
  sincronizando: boolean;
  pendientes: number;          // se enviarán solas
  problemas: number;           // requieren decisión (ERROR o CONFLICTO)
  deOtrasCuentas: number;      // acciones de otra persona que usó este celular
  sesionVencida: boolean;
  ultimaSync: number | null;
}

let estado: EstadoSync = {
  enLinea: typeof navigator === "undefined" ? true : navigator.onLine,
  sincronizando: false, pendientes: 0, problemas: 0, deOtrasCuentas: 0, sesionVencida: false, ultimaSync: null,
};
const oyentes = new Set<() => void>();
let usuario: { id: number; nombre: string } | null = null;
let iniciado = false;
let temporizador: ReturnType<typeof setTimeout> | null = null;

function fijar(parcial: Partial<EstadoSync>) {
  estado = { ...estado, ...parcial };
  oyentes.forEach((f) => f());
}

export async function refrescarContadores() {
  try {
    const todas = await colaDB.listar();
    const mias = usuario ? todas.filter((o) => o.usuario === usuario!.id) : [];
    fijar({
      pendientes: mias.filter((o) => o.estado === "PENDIENTE").length,
      problemas: mias.filter((o) => o.estado !== "PENDIENTE").length,
      deOtrasCuentas: todas.length - mias.length,
    });
  } catch { /* sin almacenamiento local: los contadores quedan en cero */ }
}

/** Mensaje legible a partir de la respuesta de error del servidor. */
function motivoDe(cuerpo: unknown, porDefecto: string): string {
  if (cuerpo && typeof cuerpo === "object") {
    const c = cuerpo as Record<string, unknown>;
    if (typeof c.detail === "string") return c.detail;
    const textos = Object.values(c).flatMap((v) => (Array.isArray(v) ? v : [v])).filter((v): v is string => typeof v === "string");
    if (textos.length) return textos.join(" ");
  }
  return porDefecto;
}

type Resultado =
  | { tipo: "ok"; datos: Record<string, unknown> }
  | { tipo: "reintentar" }
  | { tipo: "sesion" }
  | { tipo: "conflicto"; motivo: string }
  | { tipo: "error"; motivo: string };

async function enviar(op: Operacion): Promise<Resultado> {
  const ruta = op.tipo === "incidencia" ? "incidencia" : "resultado";
  const control = new AbortController();
  const corte = setTimeout(() => control.abort(), TIEMPO_MAXIMO_MS);
  try {
    const r = await fetch(`/api/proxy/fixture/partidos/${op.partidoId}/${ruta}/`, {
      method: "POST", headers: { "Content-Type": "application/json", "Idempotency-Key": op.clave },
      body: JSON.stringify(op.cuerpo), signal: control.signal, cache: "no-store",
    });
    if (r.ok) return { tipo: "ok", datos: (await r.json().catch(() => ({}))) as Record<string, unknown> };
    if (r.status === 401) return { tipo: "sesion" };
    if (r.status === 408 || r.status === 425 || r.status === 429 || r.status >= 500) return { tipo: "reintentar" };
    const cuerpo = await r.json().catch(() => null);
    if (r.status === 409) {
      // El servidor dice «usa PATCH»: para quien está en la cancha eso no significa nada, se explica en sus términos.
      const motivo = op.tipo === "resultado"
        ? "Otra persona ya registró el resultado de este partido y no se sobrescribió. Si el marcador es otro, corrígelo desde el panel completo."
        : motivoDe(cuerpo, "Otra persona ya modificó este partido.");
      return { tipo: "conflicto", motivo };
    }
    return { tipo: "error", motivo: motivoDe(cuerpo, "El servidor rechazó esta acción.") };
  } catch {
    return { tipo: "reintentar" };            // sin red o tiempo agotado: la acción sigue pendiente
  } finally {
    clearTimeout(corte);
  }
}

/** Refleja en el paquete local lo que el servidor acaba de aceptar, para no duplicarlo con la cola. */
async function aplicarAlPaquete(op: Operacion, datos: Record<string, unknown>) {
  const paquete = await paqueteDB.leer();
  const partido = paquete?.partidos.find((p) => p.id === op.partidoId);
  if (!paquete || !partido) return;
  if (op.tipo === "incidencia" && typeof datos.id === "number" && !partido.incidencias.some((i) => i.id === datos.id)) {
    partido.incidencias.push({
      id: datos.id as number, tipo: datos.tipo as never, jugador: (datos.jugador as number | null) ?? null,
      minuto: (datos.minuto as number | null) ?? null, descripcion: (datos.descripcion as string) ?? "",
    });
  }
  if (op.tipo === "resultado") {
    partido.estado = "FINALIZADO";
    partido.resultado = {
      goles_local: Number(datos.goles_local), goles_visitante: Number(datos.goles_visitante),
      penales_local: (datos.penales_local as number | null) ?? null, penales_visitante: (datos.penales_visitante as number | null) ?? null,
    };
  }
  await paqueteDB.guardar(paquete);
}

async function procesar() {
  if (!usuario) return;
  const ahora = Date.now();
  const cola = (await colaDB.listar()).filter((o) => o.usuario === usuario!.id && o.estado === "PENDIENTE");
  for (const op of cola) {
    if (op.liberarEn > ahora) continue;                       // aún dentro del margen para deshacer
    const r = await enviar(op);
    if (r.tipo === "ok") {
      await aplicarAlPaquete(op, r.datos);
      await colaDB.eliminar(op.id!);
      fijar({ ultimaSync: Date.now(), sesionVencida: false });
    } else if (r.tipo === "sesion") {
      fijar({ sesionVencida: true });
      return;
    } else if (r.tipo === "reintentar") {
      await colaDB.actualizar({ ...op, intentos: op.intentos + 1 });
      return;                                                  // seguimos sin red: no tiene sentido probar las demás ahora
    } else {
      await colaDB.actualizar({ ...op, estado: r.tipo === "conflicto" ? "CONFLICTO" : "ERROR", detalle: r.motivo, intentos: op.intentos + 1 });
    }
  }
}

/** Envía lo pendiente. Un solo envío a la vez, también entre pestañas (Web Locks cuando existe). */
export async function sincronizar() {
  if (!usuario || estado.sincronizando) return;
  const correr = async () => {
    fijar({ sincronizando: true });
    try { await procesar(); } finally { fijar({ sincronizando: false }); await refrescarContadores(); programar(); }
  };
  if (typeof navigator !== "undefined" && navigator.locks) await navigator.locks.request("dubss-sincronizar", { ifAvailable: true }, async (candado) => { if (candado) await correr(); });
  else await correr();
}

/** Vuelve a intentar más tarde mientras queden acciones pendientes (y justo cuando venza el margen para deshacer). */
function programar() {
  if (temporizador) clearTimeout(temporizador);
  temporizador = null;
  colaDB.listar().then((cola) => {
    const mias = cola.filter((o) => usuario && o.usuario === usuario.id && o.estado === "PENDIENTE");
    if (!mias.length) return;
    const proxima = Math.min(...mias.map((o) => Math.max(o.liberarEn - Date.now(), 0)));
    temporizador = setTimeout(sincronizar, proxima > 0 ? proxima + 150 : INTERVALO_REINTENTO_MS);
  }).catch(() => undefined);
}

export function iniciarSincronizacion(u: { id: number; nombre: string }) {
  usuario = u;
  void refrescarContadores().then(() => { if (navigator.onLine) void sincronizar(); });
  if (iniciado) return;
  iniciado = true;
  window.addEventListener("online", () => { fijar({ enLinea: true }); void sincronizar(); });
  window.addEventListener("offline", () => fijar({ enLinea: false }));
  document.addEventListener("visibilitychange", () => { if (document.visibilityState === "visible" && navigator.onLine) void sincronizar(); });
  suscribirCambios(() => void refrescarContadores());
}

export function detenerSincronizacion() {
  usuario = null;
  if (temporizador) clearTimeout(temporizador);
  fijar({ pendientes: 0, problemas: 0, deOtrasCuentas: 0, sesionVencida: false });
}

function nuevaClave(): string {
  return typeof crypto !== "undefined" && "randomUUID" in crypto ? crypto.randomUUID() : `${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 12)}`;
}

/** Guarda una acción en el celular y la manda a enviar tras el margen para deshacer. */
export async function encolar(datos: { partidoId: number; tipo: TipoOperacion; cuerpo: Record<string, unknown>; resumen: string }): Promise<number> {
  if (!usuario) throw new Error("No hay una sesión activa.");
  const ahora = Date.now();
  const id = await colaDB.agregar({
    usuario: usuario.id, usuarioNombre: usuario.nombre, clave: nuevaClave(), partidoId: datos.partidoId, tipo: datos.tipo,
    cuerpo: datos.cuerpo, resumen: datos.resumen, creadaEn: ahora, liberarEn: ahora + MARGEN_PARA_DESHACER_MS, estado: "PENDIENTE", intentos: 0,
  });
  programar();
  return id;
}

/** Quita una acción que todavía no salió del celular. Devuelve false si ya se estaba enviando. */
export async function deshacer(id: number): Promise<boolean> {
  const op = await colaDB.obtener(id);
  if (!op || op.estado !== "PENDIENTE" || op.liberarEn <= Date.now()) return false;
  await colaDB.eliminar(id);
  return true;
}

export async function reintentar(id: number) {
  const op = await colaDB.obtener(id);
  if (op) await colaDB.actualizar({ ...op, estado: "PENDIENTE", liberarEn: 0, detalle: undefined });
  void sincronizar();
}

export async function descartar(id: number) {
  await colaDB.eliminar(id);
}

export function useEstadoSync(): EstadoSync {
  return useSyncExternalStore(
    (cb) => { oyentes.add(cb); return () => { oyentes.delete(cb); }; },
    () => estado,
    () => estado,
  );
}
