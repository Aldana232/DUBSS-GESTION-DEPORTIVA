"use client";
import { Ban, CalendarClock, Goal, MapPin, ShieldCheck, Trophy, UserRound } from "lucide-react";
import { Badge, Card, CardBody, CardHeader, EmptyState, PageHeader, PageLoader } from "@/components/ui";
import { cn, fechaDia, hora } from "@/lib/utils";
import { jugadorPanelService } from "@/lib/api/services";
import { useApi } from "@/lib/hooks/queries";
import type { FichaPropia } from "@/types";

const RESULTADO = {
  G: { texto: "Ganado", clase: "bg-emerald-600 text-white" },
  E: { texto: "Empatado", clase: "bg-amber-400 text-ink-900" },
  P: { texto: "Perdido", clase: "bg-rose-600 text-white" },
} as const;

function Indicador({ etiqueta, valor, icono: Icono, clase }: { etiqueta: string; valor: number; icono: React.ReactNode; clase: string }) {
  return (
    <Card><CardBody className="flex items-center gap-4 p-4 sm:p-5">
      <span className={cn("flex h-12 w-12 items-center justify-center rounded-xl", clase)}>{Icono}</span>
      <div><p className="text-sm text-ink-500">{etiqueta}</p><p className="text-2xl font-bold tabular-nums text-ink-900">{valor}</p></div>
    </CardBody></Card>
  );
}

function Ficha({ f }: { f: FichaPropia }) {
  const e = f.estadisticas;
  return (
    <section className="space-y-5" aria-label={`Ficha en ${f.equipo.nombre}`}>
      <div className="relative overflow-hidden rounded-3xl bg-gradient-to-br from-ink-950 via-ink-900 to-brand-800 p-6 text-white shadow-pop sm:p-8">
        <div className="absolute -right-10 -top-12 h-48 w-48 rounded-full bg-brand-500/25 blur-3xl" aria-hidden="true" />
        <div className="relative flex flex-wrap items-center gap-5">
          <span className="flex h-20 w-20 items-center justify-center rounded-2xl bg-white/10 text-4xl font-black tabular-nums ring-1 ring-inset ring-white/25">{f.numero ?? "-"}</span>
          <div className="min-w-0 flex-1">
            <p className="text-xs uppercase tracking-wider text-brand-200">{f.equipo.facultad}</p>
            <h2 className="text-2xl font-black tracking-tight sm:text-3xl">{f.nombre} {f.apellido}</h2>
            <p className="mt-1 text-sm text-ink-200">{f.equipo.nombre} · {f.posicion}</p>
          </div>
          {f.sancion.partidos_restantes > 0 ? <Badge tono="danger">Suspendido</Badge> : <Badge tono="success">Habilitado para jugar</Badge>}
        </div>
      </div>

      {f.sancion.mensaje && (
        <p role="alert" className="flex gap-3 rounded-2xl border border-rose-200 bg-rose-50 p-4 text-sm text-rose-900"><Ban className="mt-0.5 h-5 w-5 shrink-0" aria-hidden="true" />{f.sancion.mensaje}</p>
      )}

      <div className="grid gap-3 sm:grid-cols-3">
        <Indicador etiqueta="Goles" valor={e.goles} icono={<Goal className="h-6 w-6" aria-hidden="true" />} clase="bg-brand-50 text-brand-600" />
        <Indicador etiqueta="Tarjetas amarillas" valor={e.amarillas} icono={<span className="h-6 w-4 rounded-sm bg-amber-400" aria-hidden="true" />} clase="bg-amber-50" />
        <Indicador etiqueta="Tarjetas rojas" valor={e.rojas} icono={<span className="h-6 w-4 rounded-sm bg-rose-600" aria-hidden="true" />} clase="bg-rose-50" />
      </div>

      <div className="grid gap-5 lg:grid-cols-2">
        <Card>
          <CardHeader title={<span className="inline-flex items-center gap-2"><CalendarClock className="h-4 w-4 text-brand-600" aria-hidden="true" />Próximos partidos de mi equipo</span>} />
          {f.proximos_partidos.length === 0 ? <EmptyState icon={CalendarClock} title="Sin partidos programados" description="Cuando el torneo publique el fixture, aparecerán aquí." className="m-5" /> : (
            <ul className="divide-y divide-ink-100">
              {f.proximos_partidos.map((p) => (
                <li key={p.id} className="px-5 py-3.5">
                  <p className="text-sm font-semibold text-ink-900">{p.es_local ? "Local" : "Visitante"} vs {p.rival}</p>
                  <p className="mt-0.5 flex flex-wrap items-center gap-x-3 text-xs text-ink-500"><span>{fechaDia(p.fecha_hora)} · {hora(p.fecha_hora)}</span><span className="inline-flex items-center gap-1"><MapPin className="h-3 w-3" aria-hidden="true" />{p.cancha ?? "Cancha por definir"}</span><span>{p.campeonato} · J{p.jornada}</span></p>
                </li>
              ))}
            </ul>
          )}
        </Card>
        <Card>
          <CardHeader title={<span className="inline-flex items-center gap-2"><Trophy className="h-4 w-4 text-brand-600" aria-hidden="true" />Últimos resultados</span>} />
          {f.ultimos_resultados.length === 0 ? <EmptyState icon={Trophy} title="Aún no hay resultados" className="m-5" /> : (
            <ul className="divide-y divide-ink-100">
              {f.ultimos_resultados.map((r) => (
                <li key={r.id} className="flex items-center gap-3 px-5 py-3.5">
                  <span className={cn("flex h-9 w-9 shrink-0 items-center justify-center rounded-full text-sm font-black", RESULTADO[r.resultado].clase)} title={RESULTADO[r.resultado].texto}>{r.resultado}</span>
                  <div className="min-w-0 flex-1"><p className="truncate text-sm font-semibold text-ink-900">vs {r.rival}</p><p className="truncate text-xs text-ink-500">{r.campeonato} · {fechaDia(r.fecha_hora)}</p></div>
                  <span className="text-lg font-black tabular-nums text-ink-900">{r.marcador}</span>
                </li>
              ))}
            </ul>
          )}
        </Card>
      </div>
    </section>
  );
}

/** F7-10 — Panel del jugador con cuenta: solo lectura de su ficha, estadísticas, sanción y partidos. */
export function PanelJugador() {
  const { data, isLoading } = useApi(["mi-ficha"], () => jugadorPanelService.miFicha());
  return (
    <>
      <PageHeader title="Mi ficha de jugador" description="Tus estadísticas, tu estado de habilitación y los partidos de tu equipo. Es de solo lectura." />
      {isLoading ? <PageLoader /> : !data || data.length === 0 ? (
        <EmptyState icon={UserRound} title="Tu cuenta aún no está vinculada a una ficha" description="Pídele a tu delegado que vincule tu ficha de jugador a tu cuenta para ver aquí tus estadísticas." />
      ) : (
        <div className="space-y-10">{data.map((f) => <Ficha key={f.id} f={f} />)}</div>
      )}
      <p className="mt-8 flex items-center gap-2 text-xs text-ink-400"><ShieldCheck className="h-4 w-4" aria-hidden="true" />Solo ves tu propia información.</p>
    </>
  );
}
