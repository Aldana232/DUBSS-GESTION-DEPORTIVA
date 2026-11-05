"use client";
import { PageHeader } from "@/components/ui";
import { GestionQuejas } from "@/components/gestion/GestionQuejas";

export default function QuejasGestion() {
  return (
    <>
      <PageHeader title="Quejas y apelaciones" description="Responde las solicitudes de los delegados y cambia su estado." />
      <GestionQuejas />
    </>
  );
}
