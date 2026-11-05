"use client";
import { useState } from "react";
import { BrainCircuit, CalendarDays, Target } from "lucide-react";
import { Badge, Card, CardBody, EmptyState, PageLoader } from "@/components/ui";
import { SelectorCampeonato } from "@/components/SelectorCampeonato";
import { useTablero } from "@/lib/hooks/queries";
import { fechaDia } from "@/lib/utils";
import type { Prediccion } from "@/types";

const RESULTADO = {
  local: { texto: "Victoria local", tono: "success" },
  empate: { texto: "Empate", tono: "neutral" },
  visitante: { texto: "Victoria visitante", tono: "info" },
} as const;

function Barra({ etiqueta, valor, clase }: { etiqueta: string; valor: number; clase: string }) {
  return (
    <div>
      <div className="mb-1 flex justify-between text-xs">
        <span className="truncate text-ink-600">{etiqueta}</span>
        <span className="ml-2 font-semibold tabular-nums text-ink-900">{valor}%</span>
      </div>
      <svg className="h-1.5 w-full" role="img" aria-label={`${etiqueta}: ${valor}%`}>
        <rect width="100%" height="100%" rx="3" className="fill-ink-100" />
        <rect width={`${valor}%`} height="100%" rx="3" className={clase} />
      </svg>
    </div>
  );
}

function TarjetaPrediccion({ p }: { p: Prediccion }) {
  const r = RESULTADO[p.resultado_probable];
  return (
    <Card>
      <CardBody className="space-y-3">
        <div className="flex items-center justify-between gap-2 text-sm font-semibold text-ink-900">
          <span className="min-w-0 flex-1 truncate">{p.local}</span>
          <span className="text-xs font-normal text-ink-400">vs</span>
          <span className="min-w-0 flex-1 truncate text-right">{p.visitante}</span>
        </div>
        <p className="flex items-center gap-1.5 text-xs text-ink-500"><CalendarDays className="h-3.5 w-3.5" aria-hidden="true" />{fechaDia(p.fecha_hora)}</p>
        <Barra etiqueta={p.local} valor={p.prob_local} clase="fill-emerald-500" />
        <Barra etiqueta="Empate" valor={p.prob_empate} clase="fill-ink-400" />
        <Barra etiqueta={p.visitante} valor={p.prob_visitante} clase="fill-sky-500" />
        <div className="flex items-center justify-between pt-1">
          <Badge tono={r.tono}><Target className="mr-1 h-3 w-3" aria-hidden="true" />{r.texto}</Badge>
          <span className="text-xs text-ink-500">{p.datos_suficientes ? `Confianza ${p.confianza}%` : "Pocos datos: estimación básica"}</span>
        </div>
      </CardBody>
    </Card>
  );
}

/** Tablero de predicciones; `soloEquipos` limita a los partidos de esos equipos (panel del delegado). */
export function PanelPredicciones({ soloEquipos }: { soloEquipos?: string[] }) {
  const [campeonato, setCampeonato] = useState("");
  const { data, isLoading } = useTablero(campeonato);
  const lista = (data ?? []).filter((p) => !soloEquipos || soloEquipos.includes(p.local) || soloEquipos.includes(p.visitante));

  return (
    <>
      <div className="mb-5 max-w-xs"><SelectorCampeonato valor={campeonato} onCambiar={setCampeonato} vacio="Selecciona un campeonato" /></div>
      {!campeonato && <EmptyState icon={BrainCircuit} title="Selecciona un campeonato" description="Elige un campeonato para ver las predicciones de sus próximos partidos." />}
      {campeonato && isLoading && <PageLoader texto="Calculando predicciones..." />}
      {campeonato && !isLoading && lista.length === 0 && <EmptyState icon={BrainCircuit} title="Sin partidos para predecir" description="No hay partidos programados con equipos definidos." />}
      <div className="grid gap-4 md:grid-cols-2">{lista.map((p) => <TarjetaPrediccion key={p.partido_id} p={p} />)}</div>
    </>
  );
}
