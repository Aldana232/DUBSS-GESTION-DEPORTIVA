/**
 * Lógica pura de la planilla: junta lo que ya está en el servidor con lo que espera en la cola del celular y
 * calcula marcador y estado. Sin acceso a red ni a la base local: es fácil de razonar y de probar.
 */
import type { IncidenciaPlanilla, JugadorPlanilla, PartidoPlanilla, TipoIncidencia } from "@/types";
import type { Operacion } from "@/lib/offline/db";

export type EstadoEvento = "ENVIADO" | "PENDIENTE" | "ERROR" | "CONFLICTO";
export interface EventoVista {
  clave: string;
  opId?: number;
  tipo: TipoIncidencia;
  jugadorId: number | null;
  jugador: JugadorPlanilla | null;
  lado: "local" | "visitante" | null;
  minuto: number | null;
  descripcion: string;
  estado: EstadoEvento;
  orden: number;
}

export const ETIQUETA_TIPO: Record<TipoIncidencia, string> = {
  GOL: "Gol", TARJETA_AMARILLA: "Tarjeta amarilla", TARJETA_ROJA: "Tarjeta roja", LESION: "Lesión", SUSTITUCION: "Sustitución", OTRO: "Otro suceso",
};

export function jugadoresDe(p: PartidoPlanilla): Map<number, { jugador: JugadorPlanilla; lado: "local" | "visitante" }> {
  const mapa = new Map<number, { jugador: JugadorPlanilla; lado: "local" | "visitante" }>();
  p.local.jugadores.forEach((j) => mapa.set(j.id, { jugador: j, lado: "local" }));
  p.visitante.jugadores.forEach((j) => mapa.set(j.id, { jugador: j, lado: "visitante" }));
  return mapa;
}

export function nombreCorto(j: JugadorPlanilla | null): string {
  return j ? `${j.nombre.split(" ")[0]} ${j.apellido.split(" ")[0]}`.trim() : "Sin jugador";
}

/** Incidencias ya guardadas en el servidor + las que esperan en la cola, en orden de minuto. */
export function eventosDe(p: PartidoPlanilla, ops: Operacion[]): EventoVista[] {
  const jugadores = jugadoresDe(p);
  const desdeServidor = (i: IncidenciaPlanilla, n: number): EventoVista => {
    const j = i.jugador !== null ? jugadores.get(i.jugador) : undefined;
    return { clave: `s${i.id}`, tipo: i.tipo, jugadorId: i.jugador, jugador: j?.jugador ?? null, lado: j?.lado ?? null,
      minuto: i.minuto, descripcion: i.descripcion, estado: "ENVIADO", orden: n };
  };
  const desdeCola = (o: Operacion): EventoVista => {
    const c = o.cuerpo as { tipo: TipoIncidencia; jugador?: number | null; minuto?: number | null; descripcion?: string };
    const j = c.jugador != null ? jugadores.get(c.jugador) : undefined;
    return { clave: `c${o.id}`, opId: o.id, tipo: c.tipo, jugadorId: c.jugador ?? null, jugador: j?.jugador ?? null, lado: j?.lado ?? null,
      minuto: c.minuto ?? null, descripcion: c.descripcion ?? "", estado: o.estado === "PENDIENTE" ? "PENDIENTE" : o.estado, orden: 100_000 + (o.id ?? 0) };
  };
  const eventos = [
    ...p.incidencias.map(desdeServidor),
    ...ops.filter((o) => o.partidoId === p.id && o.tipo === "incidencia").map(desdeCola),
  ];
  return eventos.sort((a, b) => (a.minuto ?? 999) - (b.minuto ?? 999) || a.orden - b.orden);
}

/** El marcador sale de los goles anotados (así lo exige el servidor al cerrar el partido). */
export function marcadorDe(eventos: EventoVista[]): { local: number; visitante: number } {
  const goles = eventos.filter((e) => e.tipo === "GOL" && e.estado !== "ERROR" && e.estado !== "CONFLICTO");
  return { local: goles.filter((e) => e.lado === "local").length, visitante: goles.filter((e) => e.lado === "visitante").length };
}

export function operacionResultado(ops: Operacion[], partidoId: number): Operacion | undefined {
  return ops.find((o) => o.partidoId === partidoId && o.tipo === "resultado");
}

export type SituacionPartido = "ABIERTO" | "CERRADO" | "CERRADO_POR_ENVIAR" | "CIERRE_CON_PROBLEMA";

/** Qué se puede hacer con el partido ahora mismo. */
export function situacionDe(p: PartidoPlanilla, ops: Operacion[]): SituacionPartido {
  if (p.resultado || p.estado === "FINALIZADO") return "CERRADO";
  const cierre = operacionResultado(ops, p.id);
  if (!cierre) return "ABIERTO";
  return cierre.estado === "PENDIENTE" ? "CERRADO_POR_ENVIAR" : "CIERRE_CON_PROBLEMA";
}

export function minutoSugerido(ms: number, ultimoMinuto: number | null): number {
  if (ms > 0) return Math.min(200, Math.floor(ms / 60_000) + 1);
  return ultimoMinuto ?? 1;
}

export function formatoReloj(ms: number): string {
  const total = Math.floor(ms / 1000);
  return `${String(Math.floor(total / 60)).padStart(2, "0")}:${String(total % 60).padStart(2, "0")}`;
}

/** Texto corto de una acción para la lista de pendientes. */
export function resumenDe(tipo: TipoIncidencia, jugador: JugadorPlanilla | null, minuto: number | null): string {
  return `${ETIQUETA_TIPO[tipo]}${jugador ? ` · ${nombreCorto(jugador)}` : ""}${minuto != null ? ` · min ${minuto}` : ""}`;
}
