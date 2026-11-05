"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { Plus, Search, Trophy } from "lucide-react";
import { Button, EmptyState, Input, PageHeader, PageLoader, Select } from "@/components/ui";
import { ModalCampeonato } from "@/components/campeonatos/FormularioCampeonato";
import { TarjetaCampeonato } from "@/components/campeonatos/TarjetaCampeonato";
import { useCampeonatos } from "@/lib/hooks/queries";

const ESTADOS = [
  ["", "Todos los estados"], ["PLANIFICACION", "Planificación"], ["INSCRIPCIONES", "Inscripciones"], ["INSCRIPCION_CERRADA", "Inscripciones cerradas"],
  ["EN_CURSO", "En curso"], ["FINALIZADO", "Finalizado"], ["CANCELADO", "Cancelado"],
];

export default function GestionCampeonatos() {
  const router = useRouter();
  const { data, isLoading } = useCampeonatos();
  const [nuevo, setNuevo] = useState(false);
  const [estado, setEstado] = useState("");
  const [texto, setTexto] = useState("");

  const lista = (data?.results ?? []).filter(
    (c) => (!estado || c.estado === estado) && c.nombre.toLowerCase().includes(texto.trim().toLowerCase()),
  );

  return (
    <>
      <PageHeader
        title="Campeonatos"
        description="Crea y administra los torneos de la DUBSS."
        actions={<Button icon={<Plus className="h-4 w-4" />} onClick={() => setNuevo(true)}>Nuevo campeonato</Button>}
      />
      <div className="mb-5 flex flex-wrap gap-3">
        <div className="w-full sm:w-72"><Input aria-label="Buscar campeonato" placeholder="Buscar por nombre" leading={<Search className="h-4 w-4" />} value={texto} onChange={(e) => setTexto(e.target.value)} /></div>
        <Select aria-label="Estado" value={estado} onChange={(e) => setEstado(e.target.value)} className="w-48">
          {ESTADOS.map(([v, t]) => <option key={v} value={v}>{t}</option>)}
        </Select>
      </div>

      {isLoading && <PageLoader />}
      <ul className="space-y-3">
        {lista.map((c) => <li key={c.id}><TarjetaCampeonato campeonato={c} href={`/gestion/campeonatos/${c.id}`} /></li>)}
      </ul>
      {!isLoading && lista.length === 0 && (
        <EmptyState icon={Trophy} title={data?.count ? "Ningún campeonato coincide con el filtro" : "No hay campeonatos registrados"}
          description={data?.count ? "Prueba con otro estado o nombre." : "Crea el primero para empezar a inscribir equipos."}
          action={!data?.count && <Button icon={<Plus className="h-4 w-4" />} onClick={() => setNuevo(true)}>Nuevo campeonato</Button>} />
      )}
      <ModalCampeonato abierto={nuevo} onCerrar={() => setNuevo(false)} onGuardado={(id) => router.push(`/gestion/campeonatos/${id}`)} />
    </>
  );
}
