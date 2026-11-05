"use client";
import { useEffect, useState } from "react";
import { Flag, Minus, Plus, TriangleAlert } from "lucide-react";
import { Hoja } from "@/components/planilla/Hoja";
import { Button, Textarea } from "@/components/ui";
import type { PartidoPlanilla } from "@/types";

/** Un suceso que no es de un jugador (p. ej. interrupción por lluvia). */
export function HojaOtro({ abierta, minutoInicial, onCerrar, onRegistrar }: {
  abierta: boolean; minutoInicial: number; onCerrar: () => void; onRegistrar: (descripcion: string, minuto: number) => void;
}) {
  const [texto, setTexto] = useState("");
  const [minuto, setMinuto] = useState(minutoInicial);
  useEffect(() => { if (abierta) { setTexto(""); setMinuto(minutoInicial); } }, [abierta, minutoInicial]);
  return (
    <Hoja abierta={abierta} onCerrar={onCerrar} titulo="Otro suceso">
      <div className="space-y-4 pb-2">
        <Textarea rows={3} maxLength={200} value={texto} aria-label="Descripción del suceso" placeholder="Ej.: Se interrumpió el partido por lluvia" onChange={(e) => setTexto(e.target.value)} />
        <div className="flex items-center justify-between rounded-2xl bg-ink-50 p-2">
          <button type="button" aria-label="Restar un minuto" onClick={() => setMinuto((m) => Math.max(0, m - 1))} className="flex h-11 w-11 items-center justify-center rounded-xl bg-white shadow-card"><Minus className="h-5 w-5" aria-hidden="true" /></button>
          <p className="text-2xl font-black tabular-nums">{minuto}&apos;</p>
          <button type="button" aria-label="Sumar un minuto" onClick={() => setMinuto((m) => Math.min(200, m + 1))} className="flex h-11 w-11 items-center justify-center rounded-xl bg-white shadow-card"><Plus className="h-5 w-5" aria-hidden="true" /></button>
        </div>
        <Button size="lg" className="w-full" disabled={texto.trim().length < 3} onClick={() => onRegistrar(texto.trim(), minuto)}>Registrar suceso</Button>
      </div>
    </Hoja>
  );
}

/** Cierre del partido: el marcador sale de los goles anotados; en eliminación directa un empate exige penales. */
export function HojaFinalizar({ abierta, partido, marcador, bloqueos, avisos, onCerrar, onConfirmar }: {
  abierta: boolean; partido: PartidoPlanilla; marcador: { local: number; visitante: number }; bloqueos: string[]; avisos: string[];
  onCerrar: () => void; onConfirmar: (penales: { local: number; visitante: number } | null) => void;
}) {
  const empate = marcador.local === marcador.visitante;
  const eliminacion = partido.campeonato.formato === "ELIMINACION";
  const necesitaPenales = eliminacion && empate;
  const [pl, setPl] = useState("");
  const [pv, setPv] = useState("");
  useEffect(() => { if (abierta) { setPl(""); setPv(""); } }, [abierta]);
  const penalesOk = !necesitaPenales || (pl !== "" && pv !== "" && Number(pl) !== Number(pv) && Number(pl) >= 0 && Number(pv) >= 0);
  const lista = bloqueos.length === 0 && penalesOk;

  return (
    <Hoja abierta={abierta} onCerrar={onCerrar} titulo="Finalizar partido">
      <div className="space-y-4 pb-2">
        <div className="rounded-2xl bg-gradient-to-br from-ink-900 to-brand-900 p-5 text-center text-white">
          <p className="text-xs uppercase tracking-wider text-brand-200">Marcador final</p>
          <p className="mt-1 text-5xl font-black tabular-nums">{marcador.local} <span className="text-brand-300">-</span> {marcador.visitante}</p>
          <p className="mt-2 text-xs text-ink-200">{partido.local.nombre} vs {partido.visitante.nombre}</p>
        </div>
        {necesitaPenales && (
          <fieldset className="rounded-2xl border border-ink-200 p-4">
            <legend className="px-2 text-xs font-semibold text-ink-600">Empate en eliminación directa: tanda de penales</legend>
            <div className="grid grid-cols-2 gap-3">
              <label className="text-xs text-ink-600">{partido.local.nombre}
                <input inputMode="numeric" pattern="[0-9]*" value={pl} onChange={(e) => setPl(e.target.value.replace(/\D/g, "").slice(0, 2))} aria-label={`Penales de ${partido.local.nombre}`}
                  className="mt-1 h-12 w-full rounded-xl border border-ink-200 text-center text-2xl font-bold tabular-nums" />
              </label>
              <label className="text-xs text-ink-600">{partido.visitante.nombre}
                <input inputMode="numeric" pattern="[0-9]*" value={pv} onChange={(e) => setPv(e.target.value.replace(/\D/g, "").slice(0, 2))} aria-label={`Penales de ${partido.visitante.nombre}`}
                  className="mt-1 h-12 w-full rounded-xl border border-ink-200 text-center text-2xl font-bold tabular-nums" />
              </label>
            </div>
            {pl !== "" && pv !== "" && Number(pl) === Number(pv) && <p role="alert" className="mt-2 text-xs text-rose-700">La tanda de penales no puede terminar empatada.</p>}
          </fieldset>
        )}
        {bloqueos.map((b) => <p key={b} role="alert" className="flex gap-2 rounded-xl bg-rose-50 p-3 text-xs text-rose-900"><TriangleAlert className="mt-0.5 h-4 w-4 shrink-0" aria-hidden="true" />{b}</p>)}
        {avisos.map((a) => <p key={a} className="flex gap-2 rounded-xl bg-amber-50 p-3 text-xs text-amber-900"><TriangleAlert className="mt-0.5 h-4 w-4 shrink-0" aria-hidden="true" />{a}</p>)}
        <p className="text-xs text-ink-500">El marcador se calcula con los goles anotados. Al confirmar no podrás seguir anotando; si hay conexión, se envía enseguida.</p>
        <Button size="lg" className="w-full" disabled={!lista} icon={<Flag className="h-5 w-5" />}
          onClick={() => onConfirmar(necesitaPenales ? { local: Number(pl), visitante: Number(pv) } : null)}>Confirmar resultado</Button>
      </div>
    </Hoja>
  );
}
