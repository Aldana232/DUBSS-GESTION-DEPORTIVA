"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import { Cookie } from "lucide-react";
import { EVENTO_ABRIR_PANEL, EVENTO_CONSENTIMIENTO, guardarConsentimiento, leerConsentimiento } from "@/lib/consentimiento";
import { PanelCookies } from "./PanelCookies";

const BOTON = "inline-flex h-10 flex-1 items-center justify-center rounded-lg border border-ink-300 bg-white px-4 text-sm font-semibold text-ink-900 transition-colors hover:bg-ink-50 sm:flex-none";

/**
 * Aviso de cookies de la primera visita. «Aceptar» y «Rechazar» tienen el MISMO peso visual (rechazar no debe ser
 * más difícil que aceptar). No bloquea la página: se puede seguir leyendo. Mientras no se elija, no se guarda nada opcional.
 */
export function AvisoCookies() {
  const [montado, setMontado] = useState(false);
  const [eligio, setEligio] = useState(true);       // por defecto «ya eligió» para no parpadear en el servidor
  const [panel, setPanel] = useState(false);

  useEffect(() => {
    setMontado(true);
    const revisar = () => setEligio(leerConsentimiento() !== null);
    const abrir = () => setPanel(true);
    revisar();
    window.addEventListener(EVENTO_CONSENTIMIENTO, revisar);
    window.addEventListener(EVENTO_ABRIR_PANEL, abrir);
    return () => { window.removeEventListener(EVENTO_CONSENTIMIENTO, revisar); window.removeEventListener(EVENTO_ABRIR_PANEL, abrir); };
  }, []);

  if (!montado) return null;
  return (
    <>
      {!eligio && (
        <section role="region" aria-label="Aviso de cookies"
          className="fixed inset-x-0 bottom-0 z-[70] p-3 pb-[max(0.75rem,env(safe-area-inset-bottom))] sm:p-4">
          <div className="mx-auto max-w-3xl rounded-2xl border border-ink-200 bg-white p-4 shadow-pop sm:p-5">
            <div className="flex items-start gap-3">
              <span className="mt-0.5 flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-brand-50 text-brand-700"><Cookie className="h-5 w-5" aria-hidden="true" /></span>
              <div className="min-w-0 text-sm text-ink-700">
                <p className="font-semibold text-ink-900">Tu privacidad en el sistema de la DUBSS</p>
                <p className="mt-1">
                  Usamos las cookies y el almacenamiento local <b>necesarios</b> para iniciar sesión y usar la planilla sin conexión: no requieren tu permiso.
                  Con tu autorización también guardamos <b>preferencias</b> de uso (por ejemplo, el menú contraído). No usamos cookies de publicidad ni de seguimiento.
                  Lee la <Link href="/cookies" className="font-medium text-brand-700 underline">Política de cookies</Link> y la <Link href="/privacidad" className="font-medium text-brand-700 underline">Política de privacidad</Link>.
                </p>
              </div>
            </div>
            <div className="mt-4 flex flex-wrap items-center justify-end gap-2">
              <button type="button" onClick={() => setPanel(true)} className="h-10 px-2 text-sm font-medium text-ink-600 underline hover:text-ink-900">Configurar</button>
              <button type="button" className={BOTON} onClick={() => guardarConsentimiento(false)}>Rechazar opcionales</button>
              <button type="button" className={BOTON} onClick={() => guardarConsentimiento(true)}>Aceptar todas</button>
            </div>
          </div>
        </section>
      )}
      <PanelCookies abierto={panel} onCerrar={() => setPanel(false)} />
    </>
  );
}
