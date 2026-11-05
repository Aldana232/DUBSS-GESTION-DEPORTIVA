"use client";
import { useParams } from "next/navigation";
import { CalendarDays } from "lucide-react";
import { EmptyState, PageHeader, PageLoader } from "@/components/ui";
import { ListaIncidencias, MarcadorPartido, ResultadoOficial } from "@/components/partido/DetallePartido";
import { usePartido } from "@/lib/hooks/queries";

export default function PartidoPublico() {
  const id = Number(useParams<{ id: string }>().id);
  const { data: p, isLoading } = usePartido(id);

  if (isLoading) return <PageLoader />;
  if (!p) return <EmptyState icon={CalendarDays} title="Partido no encontrado" />;
  return (
    <>
      <PageHeader
        breadcrumb={[{ label: "Campeonatos", href: "/campeonatos" }, { label: "Campeonato", href: `/campeonatos/${p.campeonato}` }, { label: `Partido ${p.id}` }]}
        title={`Jornada ${p.jornada} · ${p.fase}`}
      />
      <div className="space-y-5">
        <MarcadorPartido partido={p} />
        <ResultadoOficial partido={p} />
        <ListaIncidencias incidencias={p.incidencias} local={p.equipo_local} />
      </div>
    </>
  );
}
