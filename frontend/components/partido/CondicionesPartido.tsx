"use client";
import { CloudSun, RefreshCw, Users } from "lucide-react";
import { useState } from "react";
import { Badge, Button, Card, CardBody, CardHeader, type BadgeTono } from "@/components/ui";
import { useAccion, useApi } from "@/lib/hooks/queries";
import { mlService } from "@/lib/api/services";
import { fechaCorta, hora } from "@/lib/utils";
import type { NivelRiesgo, RiesgoClima } from "@/types";

const TONO: Record<NivelRiesgo, BadgeTono> = { BAJO: "success", MEDIO: "warning", ALTO: "danger", CRITICO: "danger", SIN_DATOS: "neutral" };
const TEXTO: Record<NivelRiesgo, string> = { BAJO: "Riesgo bajo", MEDIO: "Riesgo medio", ALTO: "Riesgo alto", CRITICO: "Riesgo crítico", SIN_DATOS: "Sin pronóstico" };

/** Pronóstico del clima (Open-Meteo) y asistencia estimada de un partido (F6-02/F6-03). */
export function CondicionesPartido({ partidoId, editable }: { partidoId: number; editable: boolean }) {
  const riesgo = useApi(["riesgo", partidoId], () => mlService.riesgo(partidoId));
  const asistencia = useApi(["asistencia", partidoId], () => mlService.asistencia(partidoId));
  // Si no hay pronóstico posible (p. ej. partido a más de 16 días) el servidor no guarda nada: se muestra el motivo recibido.
  const [consultado, setConsultado] = useState<RiesgoClima | null>(null);
  const actualizar = useAccion(() => mlService.actualizarRiesgo(partidoId), {
    invalidar: ["riesgo"], exito: (r) => (r.calculado ? "Pronóstico actualizado." : "No hay pronóstico disponible todavía."),
    error: "No se pudo consultar el pronóstico del clima.",
  });
  const r = consultado && !consultado.calculado ? consultado : riesgo.data;
  const a = asistencia.data;

  return (
    <div className="grid gap-5 md:grid-cols-2">
      <Card>
        <CardHeader
          title={<span className="inline-flex items-center gap-2"><CloudSun className="h-4 w-4 text-brand-600" aria-hidden="true" />Clima del partido</span>}
          action={editable && <Button size="sm" variant="secondary" loading={actualizar.pendiente} icon={<RefreshCw className="h-4 w-4" />} onClick={() => actualizar.ejecutar(undefined, { onSuccess: setConsultado })}>Actualizar pronóstico</Button>}
        />
        <CardBody className="space-y-2 text-sm">
          {r && <Badge tono={TONO[r.nivel_riesgo]}>{TEXTO[r.nivel_riesgo]}</Badge>}
          {r?.calculado ? (
            <>
              <p className="text-ink-700">{r.descripcion}</p>
              <p className="text-xs text-ink-500">
                {r.temperatura !== null && `${r.temperatura} °C`}{r.precipitacion !== null && ` · lluvia ${r.precipitacion} mm`}{r.viento !== null && ` · viento ${r.viento} km/h`}
              </p>
              <p className="text-ink-700">{r.recomendacion}</p>
              {r.consultado_en && <p className="text-xs text-ink-500">Fuente {r.fuente_api}, consultado el {fechaCorta(r.consultado_en)} {hora(r.consultado_en)}.</p>}
            </>
          ) : (
            <p className="text-ink-600">{r?.descripcion ?? "Aún no se consultó el pronóstico. El sistema lo actualiza automáticamente cuando el partido está cerca."}</p>
          )}
        </CardBody>
      </Card>
      <Card>
        <CardHeader title={<span className="inline-flex items-center gap-2"><Users className="h-4 w-4 text-brand-600" aria-hidden="true" />Asistencia estimada</span>} />
        <CardBody className="space-y-2 text-sm">
          {a ? (
            <>
              <p className="text-2xl font-bold tabular-nums text-ink-900">{a.asistencia_predicha} <span className="text-sm font-normal text-ink-500">personas</span></p>
              <p className="text-xs text-ink-500">Rango probable: {a.rango_min} a {a.rango_max}.</p>
              <p className="text-xs text-ink-500">Es una estimación por reglas (día, hora y aforo de la cancha); aún no se registra la asistencia real para aprender de ella.</p>
            </>
          ) : <p className="text-ink-600">No hay datos suficientes para estimar la asistencia.</p>}
        </CardBody>
      </Card>
    </div>
  );
}
