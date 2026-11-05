"use client";
import { CalendarDays } from "lucide-react";
import { EmptyState, PageHeader, PageLoader } from "@/components/ui";
import { ListaJornadas } from "@/components/campeonatos/ListaJornadas";
import { useMisEquipos, usePartidosDeEquipos } from "@/lib/hooks/queries";

export default function CalendarioDelegado() {
  const equipos = useMisEquipos();
  const { partidos, cargando } = usePartidosDeEquipos((equipos.data ?? []).map((e) => e.id));
  return (
    <>
      <PageHeader title="Calendario de mis equipos" description="Todos los partidos de tus equipos, agrupados por jornada." />
      {equipos.isLoading || cargando ? <PageLoader /> : (
        <ListaJornadas partidos={partidos}
          vacio={<EmptyState icon={CalendarDays} title="Sin partidos todavía" description={(equipos.data?.length ?? 0) === 0 ? "Crea un equipo e inscríbelo en un campeonato." : "Tus equipos aún no tienen fixture."} />} />
      )}
    </>
  );
}
