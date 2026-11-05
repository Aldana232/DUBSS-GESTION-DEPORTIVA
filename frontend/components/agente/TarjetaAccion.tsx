"use client";
import { ArrowRight, CalendarClock, Check, Send, TriangleAlert, X } from "lucide-react";
import { Badge, Button, Card, CardBody, type BadgeTono } from "@/components/ui";
import { useAccion } from "@/lib/hooks/queries";
import { agenteService } from "@/lib/api/services";
import { hora } from "@/lib/utils";
import type { AccionAgente, EstadoAccion } from "@/types";

const ESTADO: Record<EstadoAccion, { tono: BadgeTono; texto: string }> = {
  PENDIENTE: { tono: "warning", texto: "Pendiente de tu confirmación" },
  CONFIRMADA: { tono: "success", texto: "Confirmada y ejecutada" },
  CANCELADA: { tono: "neutral", texto: "Cancelada" },
  EXPIRADA: { tono: "neutral", texto: "Vencida" },
  FALLIDA: { tono: "danger", texto: "No se pudo aplicar" },
};

/** Propuesta del agente: qué cambia y a quién se avisa. Nada ocurre hasta pulsar «Confirmar». */
export function TarjetaAccion({ accion }: { accion: AccionAgente }) {
  const confirmar = useAccion(() => agenteService.confirmar(accion.id), {
    invalidar: ["agente-conv", "partidos", "partido", "tabla"], exito: "Acción confirmada y ejecutada.", error: "No se pudo confirmar la acción.",
  });
  const cancelar = useAccion(() => agenteService.cancelar(accion.id), { invalidar: ["agente-conv"], exito: "Acción cancelada.", error: "No se pudo cancelar la acción." });
  const d = accion.detalle;
  const pendiente = accion.estado === "PENDIENTE";
  const ocupado = confirmar.pendiente || cancelar.pendiente;
  const e = ESTADO[accion.estado];
  const errorFallo = accion.estado === "FALLIDA" ? String(accion.resultado.error ?? "") : "";

  return (
    <Card className="mt-3 border-ink-300">
      <CardBody className="space-y-3 text-sm">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <p className="inline-flex items-center gap-2 font-semibold text-ink-900">
            {"tipo" in d && d.tipo === "notificacion"
              ? <Send className="h-4 w-4 text-brand-600" aria-hidden="true" />
              : <CalendarClock className="h-4 w-4 text-brand-600" aria-hidden="true" />}
            {"tipo" in d && d.tipo === "notificacion" ? "Aviso a enviar" : "Reprogramación propuesta"}
          </p>
          <Badge tono={e.tono}>{e.texto}</Badge>
        </div>

        {"tipo" in d && d.tipo === "reprogramacion" && (
          <>
            <p className="text-ink-600">Motivo: {d.motivo}</p>
            <ul className="divide-y divide-ink-100 rounded-lg border border-ink-200">
              {d.cambios.map((c) => (
                <li key={`${c.partido}-${c.antes}`} className="space-y-1 p-3">
                  <p className="font-medium text-ink-900">{c.partido} <span className="font-normal text-ink-500">· {c.campeonato}, jornada {c.jornada}</span></p>
                  <p className="flex flex-wrap items-center gap-2 text-xs text-ink-700">
                    <span className="rounded bg-ink-100 px-2 py-0.5 line-through">{c.antes}</span>
                    <ArrowRight className="h-3.5 w-3.5 text-ink-400" aria-hidden="true" />
                    <span className="rounded bg-emerald-50 px-2 py-0.5 font-medium text-emerald-800">{c.despues}</span>
                    {c.clima ? <Badge tono="success">Clima {c.clima.toLowerCase()}</Badge> : <Badge tono="warning">Sin pronóstico</Badge>}
                  </p>
                </li>
              ))}
            </ul>
            {d.sin_solucion.length > 0 && (
              <div className="rounded-lg bg-amber-50 p-3 text-xs text-amber-900">
                <p className="mb-1 inline-flex items-center gap-1.5 font-semibold"><TriangleAlert className="h-3.5 w-3.5" aria-hidden="true" />Sin horario disponible</p>
                <ul className="list-disc space-y-0.5 pl-5">{d.sin_solucion.map((s) => <li key={s.partido}>{s.partido}: {s.motivo}</li>)}</ul>
              </div>
            )}
            {!d.clima_verificado && <p className="text-xs text-amber-800">No se pudo verificar el pronóstico: los nuevos horarios no se comprobaron contra el clima.</p>}
            <p className="text-ink-600">
              {d.delegados > 0
                ? `Al confirmar se avisará a ${d.delegados} delegado(s) por correo y notificación.`
                : "Estos equipos no tienen un delegado con cuenta: se reprogramará, pero no se enviará ningún aviso."}
            </p>
          </>
        )}

        {"tipo" in d && d.tipo === "notificacion" && (
          <>
            <p className="font-medium text-ink-900">{d.titulo}</p>
            <p className="whitespace-pre-wrap rounded-lg bg-ink-50 p-3 text-ink-800">{d.mensaje}</p>
            <p className="text-ink-600">Destinatarios: {d.destinatarios}{d.vista_previa.length > 0 && ` (${d.vista_previa.slice(0, 4).join(", ")}${d.destinatarios > 4 ? ", ..." : ""})`}</p>
          </>
        )}

        {errorFallo && <p role="alert" className="rounded-lg bg-rose-50 p-3 text-xs text-rose-800">{errorFallo}</p>}
        {accion.estado === "CONFIRMADA" && (
          <p className="text-xs text-ink-600">
            {"partidos_reprogramados" in accion.resultado && `${String(accion.resultado.partidos_reprogramados)} partido(s) reprogramado(s). `}
            {"destinatarios" in accion.resultado && `Aviso enviado a ${String(accion.resultado.destinatarios)} usuario(s). `}
          </p>
        )}

        {pendiente && (
          <div className="flex flex-wrap items-center justify-between gap-3 border-t border-ink-100 pt-3">
            <p className="text-xs text-ink-500">Vence a las {hora(accion.expira_en)}.</p>
            <div className="flex gap-2">
              <Button variant="secondary" size="sm" disabled={ocupado} loading={cancelar.pendiente} icon={<X className="h-4 w-4" />} onClick={() => cancelar.ejecutar(undefined)}>Cancelar</Button>
              <Button size="sm" disabled={ocupado} loading={confirmar.pendiente} icon={<Check className="h-4 w-4" />} onClick={() => confirmar.ejecutar(undefined)}>Confirmar</Button>
            </div>
          </div>
        )}
      </CardBody>
    </Card>
  );
}
