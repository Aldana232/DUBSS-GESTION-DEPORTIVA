"use client";
import { useState } from "react";
import Link from "next/link";
import { CalendarClock, CalendarDays, MapPin, Wand2 } from "lucide-react";
import { Button, EmptyState, EstadoBadge, PageHeader, PageLoader, Tabs } from "@/components/ui";
import { SelectorCampeonato } from "@/components/SelectorCampeonato";
import { ListaJornadas } from "@/components/campeonatos/ListaJornadas";
import { ModalGenerarFixture } from "@/components/fixture/GenerarFixture";
import { CalidadDelFixture } from "@/components/fixture/PanelCalidad";
import { ModalReprogramar } from "@/components/fixture/ModalesPartido";
import { useCampeonato, usePartidos } from "@/lib/hooks/queries";
import { fechaDia, hora } from "@/lib/utils";
import type { PartidoResumen } from "@/types";

const SIN_CANCHA = "Sin cancha asignada";

function PorCancha({ partidos, onMover }: { partidos: PartidoResumen[]; onMover: (id: number) => void }) {
  const grupos = new Map<string, PartidoResumen[]>();
  partidos.forEach((p) => grupos.set(p.cancha || SIN_CANCHA, [...(grupos.get(p.cancha || SIN_CANCHA) ?? []), p]));
  return (
    <div className="space-y-6">
      {Array.from(grupos.entries()).sort(([a], [b]) => a.localeCompare(b)).map(([cancha, ps]) => (
        <section key={cancha} aria-label={cancha}>
          <h3 className="mb-2 flex items-center gap-2 text-sm font-semibold text-ink-900"><MapPin className="h-4 w-4 text-brand-600" aria-hidden="true" />{cancha}<span className="text-xs font-normal text-ink-500">({ps.length} partidos)</span></h3>
          <ul className="divide-y divide-ink-100 overflow-hidden rounded-xl border border-ink-200 bg-white shadow-card">
            {ps.map((p) => (
              <li key={p.id} className="flex flex-wrap items-center gap-x-4 gap-y-2 px-4 py-3 text-sm">
                <span className="w-28 shrink-0 text-xs text-ink-500">{fechaDia(p.fecha_hora)} · {hora(p.fecha_hora)}</span>
                <Link href={`/gestion/partidos/${p.id}`} className="min-w-0 flex-1 truncate font-medium text-ink-900 hover:text-brand-700">{p.local} <span className="font-normal text-ink-400">vs</span> {p.visitante}</Link>
                <EstadoBadge estado={p.estado} />
                {!["FINALIZADO", "WALKOVER"].includes(p.estado) && (
                  <Button size="sm" variant="secondary" icon={<CalendarClock className="h-4 w-4" />} onClick={() => onMover(p.id)}>Mover</Button>
                )}
              </li>
            ))}
          </ul>
        </section>
      ))}
    </div>
  );
}

export default function GestionFixture() {
  const [campeonato, setCampeonato] = useState("");
  const [vista, setVista] = useState("cancha");
  const [generar, setGenerar] = useState(false);
  const [mover, setMover] = useState<number | null>(null);
  const camp = useCampeonato(Number(campeonato));
  const partidos = usePartidos(campeonato);
  const lista = partidos.data?.results ?? [];

  return (
    <>
      <PageHeader
        title="Fixture y programación"
        description="Calendario por cancha y por jornada. Mueve un partido y el sistema te avisa si hay conflictos."
        actions={camp.data && <Button icon={<Wand2 className="h-4 w-4" />} onClick={() => setGenerar(true)} disabled={camp.data.estado !== "INSCRIPCION_CERRADA"} title={camp.data.estado !== "INSCRIPCION_CERRADA" ? "Cierra las inscripciones del campeonato para generar el fixture" : undefined}>{lista.length ? "Regenerar fixture" : "Generar fixture"}</Button>}
      />
      <div className="mb-5 max-w-xs"><SelectorCampeonato valor={campeonato} onCambiar={setCampeonato} vacio="Selecciona un campeonato" /></div>

      {!campeonato ? (
        <EmptyState icon={CalendarDays} title="Selecciona un campeonato" description="Elige un campeonato para ver y programar sus partidos." />
      ) : partidos.isLoading ? <PageLoader /> : (
        <Tabs activa={vista} onCambiar={setVista} pestanas={[
          { id: "cancha", label: "Por cancha", contenido: lista.length ? <PorCancha partidos={lista} onMover={setMover} /> : <EmptyState icon={CalendarDays} title="Todavía no hay partidos" description="Genera el fixture para programarlos." /> },
          { id: "jornada", label: "Por jornada", contenido: <ListaJornadas partidos={lista} destino={(id) => `/gestion/partidos/${id}`} vacio={<EmptyState icon={CalendarDays} title="Todavía no hay partidos" description="Genera el fixture para programarlos." />} /> },
        ]} />
      )}

      {campeonato && lista.length > 0 && <div className="mt-6"><CalidadDelFixture campeonato={Number(campeonato)} /></div>}

      {camp.data && <ModalGenerarFixture campeonato={camp.data} partidosExistentes={lista.length} abierto={generar} onCerrar={() => setGenerar(false)} />}
      {mover !== null && <ModalReprogramar partidoId={mover} abierto onCerrar={() => setMover(null)} />}
    </>
  );
}
