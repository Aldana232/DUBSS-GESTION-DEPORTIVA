"use client";
import { CalendarX, CheckCircle2, ChevronRight, Clock, MapPin, RefreshCw, WifiOff } from "lucide-react";
import { Badge, Button } from "@/components/ui";
import { cn } from "@/lib/utils";
import { fechaDia, hora } from "@/lib/utils";

/** 24 horas y una sola línea: «08:00». */
const hhmm = (iso: string) => new Date(iso).toLocaleTimeString("es-BO", { hour: "2-digit", minute: "2-digit", hour12: false });
import type { Operacion } from "@/lib/offline/db";
import { eventosDe, marcadorDe, situacionDe } from "@/lib/offline/planilla";
import type { PaquetePlanilla, PartidoPlanilla } from "@/types";

function Estado({ p, ops }: { p: PartidoPlanilla; ops: Operacion[] }) {
  const sit = situacionDe(p, ops);
  const m = p.resultado ? { local: p.resultado.goles_local, visitante: p.resultado.goles_visitante } : marcadorDe(eventosDe(p, ops));
  if (sit === "CERRADO") return <Badge tono="success"><CheckCircle2 className="mr-1 h-3 w-3" aria-hidden="true" />Final {m.local}-{m.visitante}</Badge>;
  if (sit === "CERRADO_POR_ENVIAR") return <Badge tono="warning">Cierre por enviar</Badge>;
  if (sit === "CIERRE_CON_PROBLEMA") return <Badge tono="danger">Cierre con problema</Badge>;
  return m.local + m.visitante > 0 ? <Badge tono="info">En juego {m.local}-{m.visitante}</Badge> : <Badge tono="neutral">Por jugar</Badge>;
}

function Tarjeta({ p, ops, onAbrir }: { p: PartidoPlanilla; ops: Operacion[]; onAbrir: () => void }) {
  const pendientes = ops.filter((o) => o.partidoId === p.id).length;
  return (
    <li>
      <button type="button" onClick={onAbrir}
        className="group flex w-full items-center gap-3 rounded-2xl bg-white p-4 text-left shadow-card ring-1 ring-ink-100 transition active:scale-[0.99] hover:ring-brand-300">
        <div className="flex w-16 shrink-0 flex-col items-center rounded-xl bg-ink-900 py-2 text-white">
          <Clock className="mb-0.5 h-3.5 w-3.5 text-brand-300" aria-hidden="true" />
          <span className="whitespace-nowrap text-base font-bold tabular-nums">{hhmm(p.fecha_hora)}</span>
        </div>
        <div className="min-w-0 flex-1">
          <p className="truncate text-sm font-bold text-ink-900">{p.local.nombre}</p>
          <p className="truncate text-sm font-bold text-ink-900"><span className="mr-1 text-xs font-medium text-ink-400">vs</span>{p.visitante.nombre}</p>
          <p className="mt-1 flex items-center gap-1 truncate text-xs text-ink-500"><MapPin className="h-3 w-3 shrink-0" aria-hidden="true" />{p.cancha ?? "Cancha por definir"} · {p.campeonato.nombre} · J{p.jornada}</p>
        </div>
        <div className="flex shrink-0 flex-col items-end gap-1.5">
          <Estado p={p} ops={ops} />
          {pendientes > 0 && <span className="rounded-full bg-amber-100 px-2 py-0.5 text-[11px] font-semibold text-amber-800">{pendientes} por enviar</span>}
          <ChevronRight className="h-4 w-4 text-ink-300 transition-transform group-hover:translate-x-0.5" aria-hidden="true" />
        </div>
      </button>
    </li>
  );
}

export function ListaPartidos({ paquete, ops, cargando, actualizando, error, enLinea, onActualizar, onAbrir }: {
  paquete: PaquetePlanilla | null; ops: Operacion[]; cargando: boolean; actualizando: boolean; error: string | null; enLinea: boolean;
  onActualizar: () => void; onAbrir: (id: number) => void;
}) {
  const grupos = new Map<string, PartidoPlanilla[]>();
  paquete?.partidos.forEach((p) => { const k = p.fecha_hora.slice(0, 10); grupos.set(k, [...(grupos.get(k) ?? []), p]); });

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between gap-3 rounded-2xl bg-white p-3.5 shadow-card ring-1 ring-ink-100">
        <div className="min-w-0 text-xs text-ink-600">
          <p className="font-semibold text-ink-900">{paquete ? "Listo para usar sin conexión" : "Aún no hay datos en este celular"}</p>
          <p className="truncate">{paquete ? `Descargado a las ${hora(paquete.generado_en)}` : "Conéctate y descarga los partidos de hoy."}</p>
        </div>
        <Button size="sm" variant="secondary" loading={actualizando} disabled={!enLinea} icon={<RefreshCw className="h-4 w-4" />} onClick={onActualizar}>Actualizar</Button>
      </div>
      {error && <p role="alert" className="rounded-xl bg-amber-50 px-3.5 py-2.5 text-xs text-amber-900">{error}</p>}

      {cargando ? <p className="py-10 text-center text-sm text-ink-500">Cargando...</p> : !paquete ? (
        <div className="rounded-2xl bg-white p-8 text-center shadow-card ring-1 ring-ink-100">
          {enLinea ? <RefreshCw className="mx-auto mb-3 h-8 w-8 text-brand-500" aria-hidden="true" /> : <WifiOff className="mx-auto mb-3 h-8 w-8 text-amber-500" aria-hidden="true" />}
          <p className="text-sm font-semibold text-ink-900">{enLinea ? "Descarga los partidos para empezar" : "Sin conexión y sin datos guardados"}</p>
          <p className="mt-1 text-xs text-ink-500">{enLinea ? "Se guardan en este celular para que la planilla funcione aunque no haya señal." : "Abre la planilla con conexión una vez para guardar los partidos de hoy."}</p>
        </div>
      ) : paquete.partidos.length === 0 ? (
        <div className="rounded-2xl bg-white p-8 text-center shadow-card ring-1 ring-ink-100">
          <CalendarX className="mx-auto mb-3 h-8 w-8 text-ink-300" aria-hidden="true" />
          <p className="text-sm font-semibold text-ink-900">No hay partidos para hoy ni mañana</p>
          <p className="mt-1 text-xs text-ink-500">Solo aparecen partidos programados de campeonatos en curso con los dos equipos definidos.</p>
        </div>
      ) : (
        [...grupos.entries()].map(([dia, lista]) => (
          <section key={dia} aria-label={fechaDia(lista[0].fecha_hora)}>
            <h2 className={cn("mb-2 px-1 text-xs font-bold uppercase tracking-wider", "text-ink-500")}>{fechaDia(lista[0].fecha_hora)}</h2>
            <ul className="space-y-2.5">{lista.map((p) => <Tarjeta key={p.id} p={p} ops={ops} onAbrir={() => onAbrir(p.id)} />)}</ul>
          </section>
        ))
      )}
    </div>
  );
}
