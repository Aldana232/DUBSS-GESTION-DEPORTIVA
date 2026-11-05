/**
 * Base de datos local de la planilla (IndexedDB). Sin dependencias: son tres almacenes pequeños.
 *  - paquete: lo descargado del servidor (partidos de hoy con plantillas), de UNA sola cuenta.
 *  - cola:    acciones hechas en el celular que aún no llegaron al servidor.
 *  - reloj:   el cronómetro de cada partido.
 * La cola solo guarda ids y minutos (nada de nombres): si el celular se pierde, no expone datos personales.
 */
import type { PaquetePlanilla } from "@/types";

export type TipoOperacion = "incidencia" | "resultado";
/** PENDIENTE se enviará; ERROR y CONFLICTO esperan una decisión de la persona. */
export type EstadoOperacion = "PENDIENTE" | "ERROR" | "CONFLICTO";

export interface Operacion {
  id?: number;
  usuario: number;
  usuarioNombre: string;
  clave: string;                       // Idempotency-Key: identifica esta acción para siempre
  partidoId: number;
  tipo: TipoOperacion;
  cuerpo: Record<string, unknown>;
  resumen: string;                     // texto corto para la lista de pendientes
  creadaEn: number;
  liberarEn: number;                   // no se envía antes (margen para deshacer)
  estado: EstadoOperacion;
  intentos: number;
  detalle?: string;                    // por qué falló
}

export interface RelojPartido { partidoId: number; acumuladoMs: number; iniciadoEn: number | null }

const NOMBRE = "dubss-planilla";
const VERSION = 1;
const CANAL = "dubss-planilla";

let conexion: Promise<IDBDatabase> | null = null;
const oyentes = new Set<() => void>();
const canal: BroadcastChannel | null = typeof BroadcastChannel !== "undefined" ? new BroadcastChannel(CANAL) : null;
canal?.addEventListener("message", () => oyentes.forEach((f) => f()));

export function almacenamientoDisponible(): boolean {
  return typeof indexedDB !== "undefined";
}

function abrir(): Promise<IDBDatabase> {
  conexion ??= new Promise((resolver, rechazar) => {
    const pedido = indexedDB.open(NOMBRE, VERSION);
    pedido.onupgradeneeded = () => {
      const db = pedido.result;
      db.createObjectStore("paquete", { keyPath: "clave" });
      db.createObjectStore("cola", { keyPath: "id", autoIncrement: true });
      db.createObjectStore("reloj", { keyPath: "partidoId" });
    };
    pedido.onsuccess = () => resolver(pedido.result);
    pedido.onerror = () => { conexion = null; rechazar(pedido.error); };
  });
  return conexion;
}

async function operar<T>(almacen: string, modo: IDBTransactionMode, fn: (s: IDBObjectStore) => IDBRequest<T>): Promise<T> {
  const db = await abrir();
  return new Promise((resolver, rechazar) => {
    const tx = db.transaction(almacen, modo);
    const pedido = fn(tx.objectStore(almacen));
    tx.oncomplete = () => resolver(pedido.result);
    tx.onerror = () => rechazar(tx.error);
    tx.onabort = () => rechazar(tx.error);
  });
}

/** Avisa a esta pestaña y a las demás que algo cambió. */
function avisar() {
  oyentes.forEach((f) => f());
  canal?.postMessage("cambio");
}

export function suscribirCambios(fn: () => void): () => void {
  oyentes.add(fn);
  return () => { oyentes.delete(fn); };
}

export const paqueteDB = {
  async leer(): Promise<(PaquetePlanilla & { clave: string }) | undefined> {
    return operar("paquete", "readonly", (s) => s.get("actual"));
  },
  async guardar(paquete: PaquetePlanilla) {
    await operar("paquete", "readwrite", (s) => s.put({ ...paquete, clave: "actual" }));
    avisar();
  },
  async borrar() {
    await operar("paquete", "readwrite", (s) => s.delete("actual"));
    avisar();
  },
};

export const colaDB = {
  async listar(): Promise<Operacion[]> {
    const todas = await operar<Operacion[]>("cola", "readonly", (s) => s.getAll());
    return todas.sort((a, b) => (a.id ?? 0) - (b.id ?? 0));
  },
  async obtener(id: number): Promise<Operacion | undefined> {
    return operar("cola", "readonly", (s) => s.get(id));
  },
  async agregar(op: Omit<Operacion, "id">): Promise<number> {
    const id = await operar<IDBValidKey>("cola", "readwrite", (s) => s.add(op));
    avisar();
    return id as number;
  },
  async actualizar(op: Operacion) {
    await operar("cola", "readwrite", (s) => s.put(op));
    avisar();
  },
  async eliminar(id: number) {
    await operar("cola", "readwrite", (s) => s.delete(id));
    avisar();
  },
};

export const relojDB = {
  async leer(partidoId: number): Promise<RelojPartido | undefined> {
    return operar("reloj", "readonly", (s) => s.get(partidoId));
  },
  async guardar(reloj: RelojPartido) {
    await operar("reloj", "readwrite", (s) => s.put(reloj));
  },
};
