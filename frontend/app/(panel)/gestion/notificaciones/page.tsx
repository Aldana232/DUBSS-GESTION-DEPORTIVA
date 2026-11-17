"use client";
import { useState } from "react";
import { Mail, MessageCircle, Send, Smartphone } from "lucide-react";
import { Badge, Button, Card, CardBody, CardHeader, Checkbox, FormField, Input, PageHeader, Select, Textarea } from "@/components/ui";
import { useAccion, useApi } from "@/lib/hooks/queries";
import { useAuth } from "@/lib/hooks/useAuth";
import { ROLES_ADMIN } from "@/lib/auth/roles";
import { EstadoWhatsApp } from "@/components/integraciones/EstadoWhatsApp";
import { facultadService, notificacionService } from "@/lib/api/services";
import type { ResumenEnvio } from "@/types";

const ROLES = [
  { valor: "ADMIN_DUBSS", etiqueta: "Administradores" },
  { valor: "ORGANIZADOR", etiqueta: "Organizadores" },
  { valor: "DELEGADO", etiqueta: "Delegados" },
];

/** CU17 — Avisos manuales por correo y notificación push (F6-04). */
export default function GestionNotificaciones() {
  const { rol } = useAuth();
  const canales = useApi(["canales-notificacion"], () => notificacionService.canales());
  const facultades = useApi(["facultades"], () => facultadService.listar());
  const [titulo, setTitulo] = useState("DUBSS");
  const [mensaje, setMensaje] = useState("");
  const [todos, setTodos] = useState(false);
  const [roles, setRoles] = useState<string[]>([]);
  const [facultad, setFacultad] = useState("");
  const [resumen, setResumen] = useState<ResumenEnvio | null>(null);

  const enviar = useAccion(
    () => notificacionService.enviar({ titulo, mensaje, todos, roles, facultad: facultad ? Number(facultad) : null }),
    { error: "No se pudo enviar el aviso." },
  );
  const hayDestino = todos || roles.length > 0 || !!facultad;
  const alternar = (rol: string) => setRoles((r) => (r.includes(rol) ? r.filter((x) => x !== rol) : [...r, rol]));
  const mandar = () => enviar.ejecutar(undefined, { onSuccess: (r) => { setResumen(r); setMensaje(""); } });

  return (
    <>
      <PageHeader title="Avisos" description="Envía un mensaje a delegados y personal por correo, notificación en el celular y WhatsApp." />
      <div className="grid gap-5 lg:grid-cols-3">
        <Card className="lg:col-span-2">
          <CardHeader title="Nuevo aviso" />
          <CardBody className="space-y-4">
            <FormField label="Título" required><Input value={titulo} maxLength={100} onChange={(e) => setTitulo(e.target.value)} /></FormField>
            <FormField label="Mensaje" required hint={`${mensaje.length}/500 caracteres`}>
              <Textarea rows={4} maxLength={500} value={mensaje} onChange={(e) => setMensaje(e.target.value)} />
            </FormField>
            <fieldset className="space-y-2">
              <legend className="text-sm font-medium text-ink-700">Destinatarios</legend>
              <Checkbox label="Todos los usuarios activos" checked={todos} onChange={(e) => setTodos(e.target.checked)} />
              <div className="flex flex-wrap gap-x-5 gap-y-2">
                {ROLES.map((r) => (
                  <Checkbox key={r.valor} label={r.etiqueta} disabled={todos} checked={roles.includes(r.valor)} onChange={() => alternar(r.valor)} />
                ))}
              </div>
            </fieldset>
            <FormField label="Limitar a una facultad" hint="Opcional. Se combina con los roles elegidos.">
              <Select value={facultad} onChange={(e) => setFacultad(e.target.value)} disabled={todos}>
                <option value="">Todas</option>
                {facultades.data?.results.map((f) => <option key={f.id} value={f.id}>{f.nombre}</option>)}
              </Select>
            </FormField>
            <div className="flex justify-end">
              <Button icon={<Send className="h-4 w-4" />} loading={enviar.pendiente} disabled={!mensaje.trim() || !titulo.trim() || !hayDestino} onClick={mandar}>
                Enviar aviso
              </Button>
            </div>
          </CardBody>
        </Card>

        <div className="space-y-5">
          <Card>
            <CardHeader title="Canales disponibles" />
            <CardBody className="space-y-3 text-sm">
              <p className="flex items-center justify-between gap-2"><span className="inline-flex items-center gap-2"><Mail className="h-4 w-4 text-ink-500" aria-hidden="true" />Correo</span>
                <Badge tono={canales.data?.email ? "success" : "warning"}>{canales.data?.email ? "Configurado" : "No configurado"}</Badge></p>
              <p className="flex items-center justify-between gap-2"><span className="inline-flex items-center gap-2"><Smartphone className="h-4 w-4 text-ink-500" aria-hidden="true" />Push (celular)</span>
                <Badge tono={canales.data?.push ? "success" : "warning"}>{canales.data?.push ? "Configurado" : "No configurado"}</Badge></p>
              <p className="flex items-center justify-between gap-2"><span className="inline-flex items-center gap-2"><MessageCircle className="h-4 w-4 text-ink-500" aria-hidden="true" />WhatsApp</span>
                <Badge tono={canales.data?.whatsapp ? "success" : "warning"}>{canales.data?.whatsapp ? "Configurado" : "No configurado"}</Badge></p>
              {canales.data && (!canales.data.email || !canales.data.push || !canales.data.whatsapp) && (
                <p className="text-xs text-ink-500">Un canal no configurado no se usa: el aviso solo sale por los canales activos.</p>
              )}
            </CardBody>
          </Card>
          {rol && ROLES_ADMIN.includes(rol) && <EstadoWhatsApp />}
          {resumen && (
            <Card>
              <CardHeader title="Último envío" />
              <CardBody className="space-y-1 text-sm text-ink-700">
                <p>{resumen.mensaje}</p>
                <p>Usuarios alcanzados: <strong>{resumen.usuarios}</strong></p>
                <p>Correos enviados: <strong>{resumen.email}</strong></p>
                <p>Notificaciones push: <strong>{resumen.push}</strong></p>
                <p>Mensajes de WhatsApp en cola: <strong>{resumen.whatsapp}</strong></p>
              </CardBody>
            </Card>
          )}
        </div>
      </div>
    </>
  );
}
