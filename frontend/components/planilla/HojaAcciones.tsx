"use client";
import { useEffect, useState } from "react";
import { Ban, Goal, Minus, Plus, TriangleAlert } from "lucide-react";
import { Hoja } from "@/components/planilla/Hoja";
import { cn } from "@/lib/utils";
import { nombreCorto } from "@/lib/offline/planilla";
import type { JugadorPlanilla, TipoIncidencia } from "@/types";

const ACCIONES: { tipo: TipoIncidencia; texto: string; clase: string; icono: React.ReactNode }[] = [
  { tipo: "GOL", texto: "Gol", clase: "bg-brand-600 text-white active:bg-brand-700", icono: <Goal className="h-6 w-6" aria-hidden="true" /> },
  { tipo: "TARJETA_AMARILLA", texto: "Amarilla", clase: "bg-amber-400 text-ink-900 active:bg-amber-500", icono: <span className="h-6 w-4 rounded-sm bg-amber-100 ring-2 ring-amber-700/40" aria-hidden="true" /> },
  { tipo: "TARJETA_ROJA", texto: "Roja", clase: "bg-rose-700 text-white active:bg-rose-800", icono: <span className="h-6 w-4 rounded-sm bg-rose-200 ring-2 ring-white/50" aria-hidden="true" /> },
  { tipo: "LESION", texto: "Lesión", clase: "bg-ink-800 text-white active:bg-ink-900", icono: <Plus className="h-6 w-6 rotate-0" aria-hidden="true" /> },
];

/** Qué le pasó al jugador. El minuto se puede corregir antes de elegir: tocar la acción la registra. */
export function HojaAcciones({ abierta, jugador, equipo, minutoInicial, onCerrar, onRegistrar }: {
  abierta: boolean; jugador: JugadorPlanilla | null; equipo: string; minutoInicial: number;
  onCerrar: () => void; onRegistrar: (tipo: TipoIncidencia, minuto: number) => void;
}) {
  const [minuto, setMinuto] = useState(minutoInicial);
  useEffect(() => { if (abierta) setMinuto(minutoInicial); }, [abierta, minutoInicial]);
  if (!jugador) return null;
  const mover = (d: number) => setMinuto((m) => Math.max(0, Math.min(200, m + d)));

  return (
    <Hoja abierta={abierta} onCerrar={onCerrar} titulo={`${jugador.numero != null ? `#${jugador.numero} ` : ""}${nombreCorto(jugador)}`}>
      <p className="-mt-1 mb-4 text-xs text-ink-500">{equipo}{jugador.posicion ? ` · ${jugador.posicion}` : ""}</p>
      {jugador.sancionado ? (
        <div className="mb-3 flex gap-3 rounded-2xl bg-rose-50 p-4 text-sm text-rose-900" role="alert">
          <Ban className="mt-0.5 h-5 w-5 shrink-0" aria-hidden="true" />
          <p><b>Jugador sancionado.</b> Le quedan {jugador.partidos_sancion} partido(s) de suspensión: el sistema no permite registrarle incidencias.</p>
        </div>
      ) : (
        <>
          <div className="mb-4 flex items-center justify-between rounded-2xl bg-ink-50 p-2">
            <button type="button" onClick={() => mover(-1)} aria-label="Restar un minuto" className="flex h-12 w-12 items-center justify-center rounded-xl bg-white text-ink-700 shadow-card active:scale-95"><Minus className="h-5 w-5" aria-hidden="true" /></button>
            <div className="text-center"><p className="text-3xl font-black tabular-nums text-ink-900">{minuto}&apos;</p><p className="text-[11px] uppercase tracking-wider text-ink-500">minuto</p></div>
            <button type="button" onClick={() => mover(1)} aria-label="Sumar un minuto" className="flex h-12 w-12 items-center justify-center rounded-xl bg-white text-ink-700 shadow-card active:scale-95"><Plus className="h-5 w-5" aria-hidden="true" /></button>
          </div>
          <div className="grid grid-cols-2 gap-3 pb-2">
            {ACCIONES.map((a) => (
              <button key={a.tipo} type="button" onClick={() => onRegistrar(a.tipo, minuto)}
                className={cn("flex h-20 flex-col items-center justify-center gap-1.5 rounded-2xl text-sm font-bold shadow-card transition active:scale-95", a.clase)}>
                {a.icono}{a.texto}
              </button>
            ))}
          </div>
          <p className="flex items-start gap-1.5 pb-1 text-[11px] text-ink-500"><TriangleAlert className="mt-0.5 h-3 w-3 shrink-0" aria-hidden="true" />Tendrás unos segundos para deshacer antes de que se envíe.</p>
        </>
      )}
    </Hoja>
  );
}
