"use client";
import { useState } from "react";
import { Trophy } from "lucide-react";
import { EmptyState, PageHeader, PageLoader } from "@/components/ui";
import { TarjetaCampeonato } from "@/components/campeonatos/TarjetaCampeonato";
import { useCampeonatos } from "@/lib/hooks/queries";
import { cn } from "@/lib/utils";

const FILTROS = [
  { valor: "", texto: "Todos" },
  { valor: "EN_CURSO", texto: "En curso" },
  { valor: "INSCRIPCIONES", texto: "Inscripciones" },
  { valor: "INSCRIPCION_CERRADA", texto: "Por comenzar" },
  { valor: "FINALIZADO", texto: "Finalizados" },
];

export default function CampeonatosPublicos() {
  const { data, isLoading } = useCampeonatos();
  const [estado, setEstado] = useState("");
  // Planificación y cancelados no se publican: el visitante solo ve torneos abiertos, activos o terminados.
  const visibles = (data?.results ?? []).filter((c) => !["PLANIFICACION", "CANCELADO"].includes(c.estado));
  const lista = visibles.filter((c) => !estado || c.estado === estado);

  return (
    <>
      <PageHeader title="Campeonatos" description="Consulta calendarios, resultados y posiciones de cada torneo." />
      <div role="group" aria-label="Filtrar por estado" className="mb-5 flex flex-wrap gap-2">
        {FILTROS.map((f) => (
          <button key={f.valor} type="button" aria-pressed={estado === f.valor} onClick={() => setEstado(f.valor)}
            className={cn("rounded-full border px-4 py-1.5 text-sm font-medium transition-colors",
              estado === f.valor ? "border-brand-600 bg-brand-600 text-white" : "border-ink-200 bg-white text-ink-700 hover:border-ink-300")}>
            {f.texto}
          </button>
        ))}
      </div>
      {isLoading && <PageLoader />}
      <ul className="space-y-3">
        {lista.map((c) => <li key={c.id}><TarjetaCampeonato campeonato={c} href={`/campeonatos/${c.id}`} /></li>)}
      </ul>
      {!isLoading && lista.length === 0 && <EmptyState icon={Trophy} title="No hay campeonatos para mostrar" />}
    </>
  );
}
