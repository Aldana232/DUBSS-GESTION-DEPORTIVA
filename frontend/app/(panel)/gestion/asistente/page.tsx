"use client";
import { useState } from "react";
import { PageHeader, Tabs } from "@/components/ui";
import { PanelAgente } from "@/components/agente/PanelAgente";
import { ConsultasRapidas } from "@/components/asistente/ConsultasRapidas";

/** Agente (conversa, calcula y propone cambios que se confirman) y consultas rápidas por voz o texto (solo lectura). */
export default function GestionAsistente() {
  const [activa, setActiva] = useState("agente");
  return (
    <>
      <PageHeader title="Asistente" description="El agente propone y tú confirmas: nunca cambia nada sin tu aprobación." />
      <Tabs
        activa={activa}
        onCambiar={setActiva}
        pestanas={[
          { id: "agente", label: "Agente", contenido: <div className="pt-5"><PanelAgente /></div> },
          { id: "consultas", label: "Consultas rápidas", contenido: <div className="pt-5"><ConsultasRapidas /></div> },
        ]}
      />
    </>
  );
}
