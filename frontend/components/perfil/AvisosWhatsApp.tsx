"use client";
import { useState } from "react";
import { MessageCircle } from "lucide-react";
import { Badge, Button, Card, CardBody, CardHeader, Checkbox, FormField, Input } from "@/components/ui";
import { useAccion } from "@/lib/hooks/queries";
import { perfilService } from "@/lib/api/services";
import type { Usuario } from "@/types";

/** Número y consentimiento para recibir avisos por WhatsApp. El consentimiento es de la propia persona. */
export function AvisosWhatsApp({ usuario }: { usuario: Usuario }) {
  const [numero, setNumero] = useState(usuario.whatsapp ?? "");
  const [acepta, setAcepta] = useState(usuario.acepta_whatsapp ?? false);
  const [error, setError] = useState("");

  const guardar = useAccion(
    () => perfilService.editar({ whatsapp: numero.trim(), acepta_whatsapp: acepta && numero.trim() !== "" }),
    { invalidar: ["sesion"], exito: "Preferencias de WhatsApp guardadas." },
  );
  const cambios = numero.trim() !== (usuario.whatsapp ?? "") || acepta !== (usuario.acepta_whatsapp ?? false);

  const enviar = () => {
    if (acepta && !numero.trim()) { setError("Escribe tu número para activar los avisos."); return; }
    setError("");
    guardar.ejecutar(undefined, {
      onError: (e: unknown) => {
        const datos = (e as { response?: { data?: { whatsapp?: string[] | string } } })?.response?.data;
        const msg = datos?.whatsapp;
        setError(Array.isArray(msg) ? msg.join(" ") : msg ?? "No se pudo guardar. Revisa el número.");
      },
    });
  };

  return (
    <Card>
      <CardHeader title="Avisos por WhatsApp" action={usuario.acepta_whatsapp ? <Badge tono="success">Activos</Badge> : <Badge tono="neutral">Desactivados</Badge>} />
      <CardBody className="space-y-4">
        <p className="text-sm text-ink-600">
          Recibe en tu WhatsApp los recordatorios de partidos, reprogramaciones y avisos de la DUBSS. Puedes consultar tus partidos escribiendo
          <strong> PARTIDOS</strong> o <strong>RESULTADOS</strong>, y dejar de recibir avisos en cualquier momento escribiendo <strong>BAJA</strong>.
        </p>
        <div className="grid gap-4 sm:grid-cols-2">
          <FormField label="Número de WhatsApp" error={error} hint="Con código de país, por ejemplo 59170012345. Sin código se asume Bolivia (+591).">
            <Input inputMode="tel" autoComplete="tel" placeholder="59170012345" value={numero} maxLength={20}
              onChange={(e) => { setNumero(e.target.value); setError(""); }} />
          </FormField>
        </div>
        <Checkbox label="Acepto recibir avisos de la DUBSS por WhatsApp en este número" checked={acepta} onChange={(e) => { setAcepta(e.target.checked); setError(""); }} />
        <p className="text-xs text-ink-500">
          Solo se comparte tu nombre y tu número con el servicio de mensajería. Si cambias de número, debes volver a aceptar.
        </p>
        <Button icon={<MessageCircle className="h-4 w-4" />} loading={guardar.pendiente} disabled={!cambios} onClick={enviar}>Guardar preferencias</Button>
      </CardBody>
    </Card>
  );
}
