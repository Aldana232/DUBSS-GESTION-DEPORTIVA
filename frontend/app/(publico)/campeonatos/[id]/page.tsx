"use client";
import { useState } from "react";
import { useParams } from "next/navigation";
import { CalendarRange, Repeat, Trophy, Users } from "lucide-react";
import { Card, CardBody, EmptyState, EstadoBadge, PageHeader, PageLoader, Tabs } from "@/components/ui";
import { ListaJornadas } from "@/components/campeonatos/ListaJornadas";
import { PanelEstadisticas } from "@/components/campeonatos/Estadisticas";
import { HistorialPosiciones } from "@/components/campeonatos/HistorialPosiciones";
import { TablaPosiciones } from "@/components/TablaPosiciones";
import { useCampeonato, usePartidos } from "@/lib/hooks/queries";
import { etiqueta, fechaCorta } from "@/lib/utils";

export default function CampeonatoPublico() {
  const id = Number(useParams<{ id: string }>().id);
  const camp = useCampeonato(id);
  const partidos = usePartidos(String(id));
  const [pestana, setPestana] = useState("calendario");

  if (camp.isLoading) return <PageLoader />;
  if (!camp.data) return <EmptyState icon={Trophy} title="Campeonato no encontrado" description="Puede que el enlace sea incorrecto." />;
  const c = camp.data;
  const lista = partidos.data?.results ?? [];

  return (
    <>
      <PageHeader
        breadcrumb={[{ label: "Campeonatos", href: "/campeonatos" }, { label: c.nombre }]}
        title={<span className="flex flex-wrap items-center gap-3">{c.nombre}<EstadoBadge estado={c.estado} /></span>}
        description={`${c.deporte_detalle?.nombre ?? ""} — ${c.categoria_detalle?.nombre ?? ""} (${c.categoria_detalle?.genero ?? ""})`}
      />
      <div className="mb-6 grid grid-cols-2 gap-3 lg:grid-cols-4">
        {[
          { icono: Users, titulo: "Equipos", valor: `${c.total_equipos}/${c.max_equipos}` },
          { icono: CalendarRange, titulo: "Fechas", valor: `${fechaCorta(c.fecha_inicio)} – ${fechaCorta(c.fecha_fin)}` },
          { icono: Repeat, titulo: "Formato", valor: etiqueta(c.formato) },
          { icono: Trophy, titulo: "Partidos jugados", valor: `${lista.filter((p) => p.goles_local !== null).length}/${lista.length}` },
        ].map(({ icono: Icono, titulo, valor }) => (
          <Card key={titulo}>
            <CardBody className="flex items-center gap-3 p-4">
              <Icono className="h-5 w-5 shrink-0 text-brand-600" aria-hidden="true" />
              <div className="min-w-0"><p className="text-xs text-ink-500">{titulo}</p><p className="truncate text-sm font-semibold text-ink-900">{valor}</p></div>
            </CardBody>
          </Card>
        ))}
      </div>
      <Tabs
        activa={pestana}
        onCambiar={setPestana}
        pestanas={[
          { id: "calendario", label: "Calendario y resultados", contenido: partidos.isLoading ? <PageLoader /> : <ListaJornadas partidos={lista} /> },
          { id: "posiciones", label: "Posiciones", contenido: <TablaPosiciones campeonato={String(id)} /> },
          { id: "historial", label: "Historial", contenido: <HistorialPosiciones campeonato={id} /> },
          { id: "estadisticas", label: "Estadísticas", contenido: <PanelEstadisticas campeonato={String(id)} /> },
        ]}
      />
    </>
  );
}
