"use client";
import { useState } from "react";
import { useParams } from "next/navigation";
import { CalendarClock, CalendarDays, ClipboardList, Pencil, Plus, Trash2 } from "lucide-react";
import { Button, EmptyState, PageHeader, PageLoader } from "@/components/ui";
import { ListaIncidencias, MarcadorPartido, ResultadoOficial } from "@/components/partido/DetallePartido";
import { CondicionesPartido } from "@/components/partido/CondicionesPartido";
import { ModalResultado } from "@/components/fixture/FormularioResultado";
import { ModalEliminarResultado, ModalIncidencia, ModalReprogramar } from "@/components/fixture/ModalesPartido";
import { useCampeonato, usePartido } from "@/lib/hooks/queries";

/** Planilla del partido: resultado, corrección, incidencias y reprogramación (RF12, RF14). */
export default function PlanillaPartido() {
  const id = Number(useParams<{ id: string }>().id);
  const partido = usePartido(id);
  const campeonato = useCampeonato(partido.data?.campeonato ?? NaN);
  const [modal, setModal] = useState<"resultado" | "eliminar" | "incidencia" | "mover" | null>(null);

  if (partido.isLoading) return <PageLoader />;
  const p = partido.data;
  if (!p) return <EmptyState icon={CalendarDays} title="Partido no encontrado" />;

  const completo = !!p.equipo_local_detalle && !!p.equipo_visitante_detalle;
  const jugado = !!p.resultado;
  const goles = p.incidencias.filter((i) => i.tipo === "GOL");
  const golesIncidencias = {
    local: goles.filter((i) => i.equipo_id === p.equipo_local).length,
    visitante: goles.filter((i) => i.equipo_id === p.equipo_visitante).length,
  };
  const cerrar = () => setModal(null);

  return (
    <>
      <PageHeader
        breadcrumb={[{ label: "Fixture", href: "/gestion/fixture" }, { label: campeonato.data?.nombre ?? "Campeonato", href: `/gestion/campeonatos/${p.campeonato}` }, { label: `Partido ${p.id}` }]}
        title={`Jornada ${p.jornada} · ${p.fase}`}
        description={completo ? undefined : "Este partido espera a los ganadores de la ronda anterior."}
        actions={completo && <>
          {!jugado && <Button variant="secondary" icon={<CalendarClock className="h-4 w-4" />} onClick={() => setModal("mover")}>Reprogramar</Button>}
          {jugado && <Button variant="danger" icon={<Trash2 className="h-4 w-4" />} onClick={() => setModal("eliminar")}>Eliminar resultado</Button>}
          <Button icon={jugado ? <Pencil className="h-4 w-4" /> : <ClipboardList className="h-4 w-4" />} onClick={() => setModal("resultado")}>{jugado ? "Corregir resultado" : "Registrar resultado"}</Button>
        </>}
      />

      <div className="space-y-5">
        <MarcadorPartido partido={p} />
        <ResultadoOficial partido={p} />
        {completo && !jugado && <CondicionesPartido partidoId={p.id} editable />}
        {completo && p.estado !== "WALKOVER" && (
          <div className="flex justify-end"><Button variant="secondary" size="sm" icon={<Plus className="h-4 w-4" />} onClick={() => setModal("incidencia")}>Registrar incidencia</Button></div>
        )}
        <ListaIncidencias incidencias={p.incidencias} local={p.equipo_local} />
      </div>

      {completo && modal === "resultado" && (
        <ModalResultado key={`${p.resultado?.id ?? "nuevo"}`} partido={p} eliminacion={campeonato.data?.formato === "ELIMINACION"} golesIncidencias={golesIncidencias} abierto onCerrar={cerrar} />
      )}
      {modal === "eliminar" && <ModalEliminarResultado partido={p} abierto onCerrar={cerrar} />}
      {modal === "incidencia" && <ModalIncidencia partido={p} abierto onCerrar={cerrar} />}
      {modal === "mover" && <ModalReprogramar partidoId={p.id} abierto onCerrar={cerrar} />}
    </>
  );
}
