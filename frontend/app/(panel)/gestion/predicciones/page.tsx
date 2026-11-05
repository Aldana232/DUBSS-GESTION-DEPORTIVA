"use client";
import { useState } from "react";
import { PageHeader, Tabs } from "@/components/ui";
import { PanelPredicciones } from "@/components/ml/PanelPredicciones";
import { ModeloAsignacion } from "@/components/ml/ModeloAsignacion";
import { ModeloPredictor } from "@/components/ml/ModeloPredictor";
import { NivelesEquipos } from "@/components/ml/NivelesEquipos";
import { ResultadosAtipicos } from "@/components/ml/ResultadosAtipicos";

export default function GestionPredicciones() {
  const [activa, setActiva] = useState("modelos");
  return (
    <>
      <PageHeader title="Inteligencia artificial" description="Modelos, predicciones de resultados, niveles de equipos para sembrar llaves y detección de marcadores atípicos." />
      <Tabs
        activa={activa}
        onCambiar={setActiva}
        pestanas={[
          { id: "modelos", label: "Modelos", contenido: <div className="grid gap-5 pt-5 xl:grid-cols-2"><ModeloPredictor /><ModeloAsignacion /></div> },
          { id: "predicciones", label: "Predicciones", contenido: <div className="pt-5"><PanelPredicciones /></div> },
          { id: "niveles", label: "Niveles y siembra", contenido: <div className="pt-5"><NivelesEquipos /></div> },
          { id: "atipicos", label: "Resultados atípicos", contenido: <div className="pt-5"><ResultadosAtipicos /></div> },
        ]}
      />
    </>
  );
}
