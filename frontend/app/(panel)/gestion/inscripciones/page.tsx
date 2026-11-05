"use client";
import { PageHeader } from "@/components/ui";
import { BandejaInscripciones } from "@/components/gestion/BandejaInscripciones";

export default function GestionInscripciones() {
  return (
    <>
      <PageHeader title="Inscripciones" description="Revisa las solicitudes de los delegados: aprueba o rechaza según los requisitos del campeonato." />
      <BandejaInscripciones />
    </>
  );
}
