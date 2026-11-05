"use client";
import { PageHeader, PageLoader } from "@/components/ui";
import { PanelPredicciones } from "@/components/ml/PanelPredicciones";
import { useMisEquipos } from "@/lib/hooks/queries";

export default function PrediccionesDelegado() {
  const equipos = useMisEquipos();
  if (equipos.isLoading) return <PageLoader />;
  return (
    <>
      <PageHeader title="Predicciones" description="Probabilidades de resultado de los próximos partidos de tus equipos." />
      <PanelPredicciones soloEquipos={(equipos.data ?? []).map((e) => e.nombre)} />
    </>
  );
}
