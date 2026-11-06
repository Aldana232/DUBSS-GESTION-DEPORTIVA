"use client";
import { useState, type FormEvent } from "react";
import { Mail, MessageCircle } from "lucide-react";
import { Button } from "@/components/ui";
import { EMPRESA, POR_CONFIRMAR } from "@/lib/corporativo.config";
import { CopiarBoton } from "./CopiarBoton";

const MOTIVOS = ["Quiero una demostración", "Consulta sobre el producto", "Necesito soporte técnico", "Otro"];
const campo = "mt-1 w-full rounded-lg border border-ink-200 bg-white px-3 py-2 text-sm text-ink-900 placeholder:text-ink-400";

/**
 * El formulario NO envía nada por sí mismo: arma el mensaje y ofrece abrirlo en el correo o en
 * WhatsApp (si están configurados en corporativo.config.ts) o copiarlo.
 */
export function Contacto({ onAbrirChat }: { onAbrirChat: () => void }) {
  const [nombre, setNombre] = useState("");
  const [org, setOrg] = useState("");
  const [motivo, setMotivo] = useState(MOTIVOS[0]);
  const [mensaje, setMensaje] = useState("");
  const [listo, setListo] = useState<string | null>(null);
  const [error, setError] = useState("");

  function preparar(e: FormEvent) {
    e.preventDefault();
    if (!nombre.trim() || !mensaje.trim()) { setError("Escribe tu nombre y tu mensaje."); setListo(null); return; }
    setError("");
    setListo(`Hola, soy ${nombre.trim()}${org.trim() ? ` (${org.trim()})` : ""}.\nMotivo: ${motivo}.\n\n${mensaje.trim()}`);
  }

  const urlCorreo = EMPRESA.email && listo ? `mailto:${EMPRESA.email}?subject=${encodeURIComponent(`${EMPRESA.producto}: ${motivo}`)}&body=${encodeURIComponent(listo)}` : "";
  const urlWa = EMPRESA.whatsapp && listo ? `https://wa.me/${EMPRESA.whatsapp}?text=${encodeURIComponent(listo)}` : "";

  return (
    <div className="grid gap-8 lg:grid-cols-2">
      <div className="min-w-0 space-y-3">
        <div className="rounded-lg border border-ink-200 bg-white px-4 py-3">
          <span className="block text-xs font-medium uppercase tracking-wide text-ink-500">Correo</span>
          <div className="flex flex-wrap items-center justify-between gap-2">
            <span className="break-all text-sm font-medium text-ink-900">{EMPRESA.email || POR_CONFIRMAR}</span>
            {EMPRESA.email && <CopiarBoton texto={EMPRESA.email} />}
          </div>
        </div>
        <div className="rounded-lg border border-ink-200 bg-white px-4 py-3">
          <span className="block text-xs font-medium uppercase tracking-wide text-ink-500">WhatsApp</span>
          <div className="flex flex-wrap items-center justify-between gap-2">
            <span className="text-sm font-medium text-ink-900">{EMPRESA.whatsapp ? `+${EMPRESA.whatsapp}` : POR_CONFIRMAR}</span>
            {EMPRESA.whatsapp && <CopiarBoton texto={`+${EMPRESA.whatsapp}`} />}
          </div>
        </div>
        <div className="flex flex-wrap items-center justify-between gap-2 rounded-lg border border-ink-200 bg-white px-4 py-3">
          <div>
            <span className="block text-xs font-medium uppercase tracking-wide text-ink-500">Chat de ayuda</span>
            <span className="text-sm font-medium text-ink-900">Asistente en esta página</span>
          </div>
          <Button variant="secondary" size="sm" onClick={onAbrirChat}>Abrir chat</Button>
        </div>
      </div>

      <form onSubmit={preparar} noValidate className="min-w-0 space-y-3 rounded-xl border border-ink-200 bg-white p-5 shadow-card">
        <label className="block text-sm font-medium text-ink-800" htmlFor="c-nombre">Nombre
          <input id="c-nombre" className={campo} value={nombre} onChange={(e) => setNombre(e.target.value)} autoComplete="name" placeholder="Tu nombre" aria-invalid={!!error && !nombre.trim()} />
        </label>
        <label className="block text-sm font-medium text-ink-800" htmlFor="c-org">Facultad o institución
          <input id="c-org" className={campo} value={org} onChange={(e) => setOrg(e.target.value)} placeholder="Ej.: Facultad de Ingeniería" />
        </label>
        <label className="block text-sm font-medium text-ink-800" htmlFor="c-motivo">Motivo
          <select id="c-motivo" className={campo} value={motivo} onChange={(e) => setMotivo(e.target.value)}>
            {MOTIVOS.map((m) => <option key={m}>{m}</option>)}
          </select>
        </label>
        <label className="block text-sm font-medium text-ink-800" htmlFor="c-mensaje">Mensaje
          <textarea id="c-mensaje" className={`${campo} min-h-[7rem]`} value={mensaje} onChange={(e) => setMensaje(e.target.value)} placeholder="Cuéntanos qué necesitas" aria-invalid={!!error && !mensaje.trim()} />
        </label>
        <Button type="submit">Preparar mensaje</Button>
        {error && <p role="alert" className="text-sm font-medium text-brand-700">{error}</p>}
        {listo && (
          <div role="status" className="space-y-3 rounded-lg border border-ink-200 bg-ink-50 p-3">
            <p className="text-sm font-medium text-ink-800">Mensaje listo. Este formulario no lo envía por sí mismo: cópialo o ábrelo en tu correo o WhatsApp.</p>
            <pre className="whitespace-pre-wrap break-words rounded-md bg-white p-3 text-xs text-ink-700">{listo}</pre>
            <div className="flex flex-wrap gap-2">
              <CopiarBoton texto={listo} etiqueta="Copiar mensaje" />
              {urlCorreo && <a href={urlCorreo} className="inline-flex h-8 items-center gap-1.5 rounded-lg border border-ink-200 bg-white px-3 text-xs font-medium text-ink-800 hover:bg-ink-50"><Mail className="h-3.5 w-3.5" aria-hidden="true" />Abrir en correo</a>}
              {urlWa && <a href={urlWa} target="_blank" rel="noopener noreferrer" className="inline-flex h-8 items-center gap-1.5 rounded-lg border border-ink-200 bg-white px-3 text-xs font-medium text-ink-800 hover:bg-ink-50"><MessageCircle className="h-3.5 w-3.5" aria-hidden="true" />Abrir en WhatsApp</a>}
            </div>
            {!urlCorreo && !urlWa && <p className="text-xs text-ink-500">El correo y el WhatsApp de la empresa aún no están configurados ({POR_CONFIRMAR}); por ahora solo puedes copiar el mensaje.</p>}
          </div>
        )}
      </form>
    </div>
  );
}
