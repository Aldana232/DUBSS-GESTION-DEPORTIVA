"use client";
import { useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { Workflow } from "lucide-react";
import { Badge, Button, Card, CardBody, CardHeader, useToast } from "@/components/ui";
import { useApi } from "@/lib/hooks/queries";
import { integracionService } from "@/lib/api/services";
import { fechaDia, hora } from "@/lib/utils";
import type { EventoIntegracion, ResultadoPruebaIntegracion } from "@/types";

const TONO = { PENDIENTE: "warning", ENTREGADO: "success", FALLIDO: "danger" } as const;
const ETIQUETA = { PENDIENTE: "En cola", ENTREGADO: "Entregado", FALLIDO: "Falló" } as const;

/** Estado de la integración con n8n/WhatsApp y prueba de conexión (solo administradores). */
export function EstadoWhatsApp() {
  const qc = useQueryClient();
  const toast = useToast();
  const estado = useApi(["integracion-estado"], () => integracionService.estado());
  const [probando, setProbando] = useState(false);

  const probar = async () => {
    setProbando(true);
    try {
      const r: ResultadoPruebaIntegracion = await integracionService.probar();
      toast.success(r.recibira_whatsapp ? "n8n recibió la prueba. Revisa tu WhatsApp." : "n8n recibió la prueba. Activa WhatsApp en tu perfil para recibir el mensaje.");
    } catch (e) {
      const cuerpo = (e as { response?: { data?: { error?: string; detail?: string } } })?.response?.data;
      toast.error(cuerpo?.error || cuerpo?.detail || "No se pudo contactar con n8n.");
    } finally {
      setProbando(false);
      qc.invalidateQueries({ queryKey: ["integracion-estado"] });
    }
  };

  const d = estado.data;
  return (
    <Card>
      <CardHeader title="WhatsApp (n8n)" action={d && <Badge tono={d.configurado ? "success" : "warning"}>{d.configurado ? "Conectado" : "Sin configurar"}</Badge>} />
      <CardBody className="space-y-3 text-sm">
        {!d ? <p className="text-ink-500">Consultando estado…</p> : !d.configurado ? (
          <p className="text-ink-600">La integración está apagada: faltan <code>N8N_URL_EVENTOS</code> y <code>N8N_SECRETO</code> en el servidor. Consulta la guía de despliegue (n8n y WhatsApp).</p>
        ) : (
          <>
            <dl className="grid grid-cols-2 gap-2 text-ink-700">
              <div><dt className="text-xs text-ink-500">Destino</dt><dd className="truncate font-medium">{d.destino}</dd></div>
              <div><dt className="text-xs text-ink-500">Personas con WhatsApp</dt><dd className="font-medium">{d.usuarios_con_whatsapp}</dd></div>
              <div><dt className="text-xs text-ink-500">En cola / entregados 24 h</dt><dd className="font-medium">{d.pendientes} / {d.entregados_24h}</dd></div>
              <div><dt className="text-xs text-ink-500">Fallidos</dt><dd className={d.fallidos ? "font-medium text-brand-700" : "font-medium"}>{d.fallidos}</dd></div>
            </dl>
            {d.ultimos.length > 0 && (
              <ul className="divide-y divide-ink-100 rounded-lg border border-ink-200">
                {d.ultimos.slice(0, 5).map((ev: EventoIntegracion) => (
                  <li key={ev.id} className="flex flex-wrap items-center justify-between gap-2 px-3 py-2">
                    <span className="min-w-0"><span className="font-medium text-ink-800">{ev.tipo}</span> <span className="text-xs text-ink-500">{fechaDia(ev.creado)} {hora(ev.creado)}</span>
                      {ev.error && <span className="block truncate text-xs text-brand-700">{ev.error}</span>}</span>
                    <Badge tono={TONO[ev.estado]}>{ETIQUETA[ev.estado]}</Badge>
                  </li>
                ))}
              </ul>
            )}
            <Button variant="secondary" size="sm" icon={<Workflow className="h-4 w-4" />} loading={probando} onClick={probar}>Enviar prueba a n8n</Button>
          </>
        )}
      </CardBody>
    </Card>
  );
}
