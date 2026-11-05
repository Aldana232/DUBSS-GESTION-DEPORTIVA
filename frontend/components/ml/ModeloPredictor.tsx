"use client";
import { LineChart, RefreshCw } from "lucide-react";
import { Badge, Button, Card, CardBody, CardHeader, PageLoader } from "@/components/ui";
import { useAccion, useApi } from "@/lib/hooks/queries";
import { useAuth } from "@/lib/hooks/useAuth";
import { mlService } from "@/lib/api/services";
import { fechaCorta, hora } from "@/lib/utils";
import type { MetricasPrediccion } from "@/types";

const pct = (v: number) => `${(v * 100).toFixed(1)}%`;

function Fila({ nombre, m, destacado }: { nombre: string; m?: MetricasPrediccion; destacado?: boolean }) {
  if (!m) return null;
  return (
    <tr className={destacado ? "bg-brand-50/50 font-semibold" : ""}>
      <td className="px-3 py-2">{nombre}</td>
      <td className="px-3 py-2 tabular-nums">{pct(m.accuracy)}</td>
      <td className="px-3 py-2 tabular-nums">{m.log_loss.toFixed(3)}</td>
      <td className="px-3 py-2 tabular-nums">{m.brier.toFixed(3)}</td>
      <td className="px-3 py-2 tabular-nums">{m.ece.toFixed(3)}</td>
    </tr>
  );
}

/** Estado del predictor de resultados: método en uso, validación contra líneas base y entrenamiento (F6-01). */
export function ModeloPredictor() {
  const { esAdmin } = useAuth();
  const { data, isLoading } = useApi(["modelo-predictor"], () => mlService.informePredictor());
  const entrenar = useAccion(() => mlService.entrenarPredictor(), {
    invalidar: ["modelo-predictor", "tablero"],
    exito: (r) => (r.es_activo ? "Modelo entrenado y activado." : "Modelo entrenado, pero no supera la línea base: se mantiene el método Elo."),
    error: "No se pudo entrenar el modelo.",
  });
  if (isLoading) return <PageLoader />;
  if (!data) return null;
  const faltan = Math.max(0, data.minimo - data.partidos_disponibles);

  return (
    <Card>
      <CardHeader
        title={<span className="inline-flex items-center gap-2"><LineChart className="h-4 w-4 text-brand-600" aria-hidden="true" />Predictor de resultados</span>}
        action={esAdmin && <Button size="sm" variant="secondary" loading={entrenar.pendiente} disabled={faltan > 0} icon={<RefreshCw className="h-4 w-4" />} onClick={() => entrenar.ejecutar(undefined)}>Entrenar</Button>}
      />
      <CardBody className="space-y-4 text-sm">
        <div className="flex flex-wrap items-center gap-2 text-xs text-ink-500">
          <Badge tono={data.es_activo ? "success" : "warning"}>{data.es_activo ? "Modelo entrenado en uso" : "Método Elo en uso"}</Badge>
          <span>{data.partidos_disponibles} partidos finalizados disponibles</span>
          {data.fecha_entrenamiento && <span>· entrenado el {fechaCorta(data.fecha_entrenamiento)} {hora(data.fecha_entrenamiento)}</span>}
        </div>
        {faltan > 0 && (
          <p className="text-ink-600">
            Faltan {faltan} partidos jugados (mínimo {data.minimo}) para entrenar. Mientras tanto las predicciones usan el método Elo y se marcan con confianza baja.
          </p>
        )}
        {data.modelo && (
          <>
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead className="text-ink-500"><tr><th className="px-3 py-2">Método</th><th className="px-3 py-2">Acierto</th><th className="px-3 py-2">Log-loss</th><th className="px-3 py-2">Brier</th><th className="px-3 py-2">Calibración (ECE)</th></tr></thead>
                <tbody className="divide-y divide-ink-100">
                  <Fila nombre="Random Forest" m={data.modelo} destacado />
                  <Fila nombre="Elo" m={data.linea_base_elo} />
                  <Fila nombre="Frecuencia histórica" m={data.linea_base_frecuencia} />
                </tbody>
              </table>
            </div>
            <p className="text-xs text-ink-500">
              {data.conclusion} Validado con {data.partidos_validacion} partidos futuros ({data.cortes_walk_forward} cortes en el tiempo). En log-loss, Brier y ECE, menor es mejor.
            </p>
          </>
        )}
      </CardBody>
    </Card>
  );
}
