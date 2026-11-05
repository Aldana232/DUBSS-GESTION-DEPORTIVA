"use client";
import { BrainCircuit, RefreshCw } from "lucide-react";
import { Badge, Button, Card, CardBody, CardHeader, PageLoader } from "@/components/ui";
import { useAccion, useApi } from "@/lib/hooks/queries";
import { useAuth } from "@/lib/hooks/useAuth";
import { mlService } from "@/lib/api/services";
import { fechaCorta, hora } from "@/lib/utils";

const NOMBRE_VARIABLE: Record<string, string> = {
  franja_horaria: "Hora del partido", dia_semana: "Día de la semana", es_fin_de_semana: "Fin de semana",
  dias_desde_ultimo_local: "Descanso del local", dias_desde_ultimo_visit: "Descanso del visitante",
  descanso_minimo: "Descanso mínimo", instalacion_disponible: "Instalación disponible",
  conflictos_horario: "Conflictos en el recinto", holgura_facultad_min: "Holgura con la facultad",
};

/** Estado del modelo Random Forest que puntúa los horarios del fixture (versión, métricas y reentrenamiento). */
export function ModeloAsignacion() {
  const { esAdmin } = useAuth();
  const { data, isLoading } = useApi(["modelo-asignacion"], () => mlService.modeloAsignacion());
  const reentrenar = useAccion(() => mlService.reentrenarAsignacion(), {
    invalidar: ["modelo-asignacion"], exito: "Modelo reentrenado con el historial disponible.", error: "No se pudo reentrenar el modelo.",
  });
  if (isLoading) return <PageLoader />;
  if (!data) return null;
  const importancias = Object.entries(data.importancias ?? {}).sort((a, b) => b[1] - a[1]).slice(0, 5);

  return (
    <Card>
      <CardHeader
        title={<span className="inline-flex items-center gap-2"><BrainCircuit className="h-4 w-4 text-brand-600" aria-hidden="true" />Modelo de programación del fixture</span>}
        action={esAdmin && <Button size="sm" variant="secondary" loading={reentrenar.pendiente} icon={<RefreshCw className="h-4 w-4" />} onClick={() => reentrenar.ejecutar(undefined)}>Reentrenar</Button>}
      />
      <CardBody className="space-y-4 text-sm">
        {!data.entrenado ? (
          <p className="text-ink-600">Aún no hay un modelo entrenado. Se entrena automáticamente la primera vez que generas un fixture con ML.</p>
        ) : (
          <>
            <div className="flex flex-wrap items-center gap-2 text-xs text-ink-500">
              <Badge tono="brand">{data.version}</Badge>
              <span>entrenado el {fechaCorta(data.entrenado_en)} {hora(data.entrenado_en)}</span>
              <Badge tono={(data.muestras_reales ?? 0) > 0 ? "success" : "warning"}>{data.etiquetado}</Badge>
            </div>
            <dl className="grid grid-cols-2 gap-3 sm:grid-cols-4">
              {([["Exactitud", data.exactitud], ["Precisión", data.precision], ["Sensibilidad", data.sensibilidad], ["F1", data.f1]] as const).map(([t, v]) => (
                <div key={t} className="rounded-lg bg-ink-50 p-3"><dt className="text-xs text-ink-500">{t}</dt><dd className="text-lg font-bold tabular-nums text-ink-900">{v !== undefined ? `${Math.round(v * 100)}%` : "—"}</dd></div>
              ))}
            </dl>
            <p className="text-xs text-ink-500">
              {data.muestras} muestras ({data.muestras_reales} de partidos reales). Mientras no haya historial real, las métricas miden cuánto aprendió
              el modelo de las reglas de arranque, no la calidad real de un torneo; mejora al reentrenar con partidos jugados.
            </p>
            <div>
              <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-ink-500">Variables que más pesan</p>
              <ul className="space-y-1.5">
                {importancias.map(([nombre, valor]) => (
                  <li key={nombre} className="flex items-center gap-3 text-xs">
                    <span className="w-44 shrink-0 text-ink-700">{NOMBRE_VARIABLE[nombre] ?? nombre}</span>
                    <svg className="h-1.5 flex-1" role="img" aria-label={`${NOMBRE_VARIABLE[nombre] ?? nombre}: ${Math.round(valor * 100)}%`}>
                      <rect width="100%" height="100%" rx="3" className="fill-ink-100" />
                      <rect width={`${Math.max(2, Math.round(valor * 100))}%`} height="100%" rx="3" className="fill-brand-600" />
                    </svg>
                    <span className="w-9 text-right tabular-nums text-ink-600">{Math.round(valor * 100)}%</span>
                  </li>
                ))}
              </ul>
            </div>
          </>
        )}
      </CardBody>
    </Card>
  );
}
