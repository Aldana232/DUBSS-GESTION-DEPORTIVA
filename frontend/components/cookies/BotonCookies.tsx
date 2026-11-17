"use client";
import { abrirPanelCookies } from "@/lib/consentimiento";

/** Enlace del pie «Configurar cookies»: reabre el panel para cambiar la elección en cualquier momento. */
export function BotonCookies({ className }: { className?: string }) {
  return <button type="button" onClick={abrirPanelCookies} className={className}>Configurar cookies</button>;
}
