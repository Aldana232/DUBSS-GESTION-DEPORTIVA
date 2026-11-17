"use client";
import { useEffect, useRef, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { ExternalLink, LogOut, ShieldCheck } from "lucide-react";
import { Button } from "@/components/ui";
import { Logo } from "@/components/layout/Logo";
import { useAuth } from "@/lib/hooks/useAuth";
import { legalService } from "@/lib/api/services";
import { LEGAL_VERSION, LEGAL_VIGENTE_DESDE } from "@/lib/legal.config";

/**
 * Cuadro de aceptación de los Términos y la Política de Privacidad. Se muestra en el primer ingreso y cada vez que
 * cambia la versión de los documentos. Bloquea el panel hasta aceptar (o cerrar sesión). Nada viene marcado de antemano:
 * hay que marcar la casilla de forma expresa. La aceptación queda registrada en el servidor (versión, fecha e IP).
 *
 * `enLinea=false` (planilla móvil sin conexión) no bloquea: quien ya tenía la planilla descargada puede seguir
 * anotando el partido y el cuadro aparece al volver la conexión.
 */
export function PuertaLegal({ enLinea = true }: { enLinea?: boolean }) {
  const { usuario, logout } = useAuth();
  const qc = useQueryClient();
  const [acepto, setAcepto] = useState(false);
  const [enviando, setEnviando] = useState(false);
  const [error, setError] = useState("");
  const primero = useRef<HTMLAnchorElement>(null);
  const visible = !!usuario?.legal_pendiente && enLinea;

  useEffect(() => {
    if (!visible) return;
    const overflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    primero.current?.focus();
    return () => { document.body.style.overflow = overflow; };
  }, [visible]);

  if (!visible) return null;

  const aceptar = async () => {
    setEnviando(true); setError("");
    try {
      await legalService.aceptar(LEGAL_VERSION);
      await qc.invalidateQueries({ queryKey: ["sesion"] });
    } catch (e) {
      const estado = (e as { response?: { status?: number } })?.response?.status;
      setError(estado === 409
        ? "Los documentos se actualizaron mientras leías. Recarga la página para ver la versión vigente."
        : "No se pudo registrar tu aceptación. Revisa tu conexión e inténtalo de nuevo.");
    } finally {
      setEnviando(false);
    }
  };

  return (
    <div className="fixed inset-0 z-[80] flex items-end justify-center bg-ink-950/70 p-0 backdrop-blur-sm sm:items-center sm:p-4">
      <div role="dialog" aria-modal="true" aria-labelledby="legal-titulo" aria-describedby="legal-desc"
        className="max-h-[100dvh] w-full max-w-lg overflow-y-auto rounded-t-3xl bg-white p-6 shadow-pop sm:rounded-3xl sm:p-8">
        <div className="flex items-center gap-3">
          <Logo size={44} className="shrink-0 ring-2 ring-brand-100" />
          <div>
            <p className="text-xs font-semibold uppercase tracking-wider text-brand-700">Antes de continuar</p>
            <h2 id="legal-titulo" className="text-xl font-bold leading-tight text-ink-900">Términos y privacidad</h2>
          </div>
        </div>

        <p id="legal-desc" className="mt-4 text-sm text-ink-600">
          Hola, {usuario?.nombre}. Para usar el sistema de la DUBSS necesitamos que conozcas y aceptes cómo funciona y cómo tratamos tus datos.
        </p>

        <ul className="mt-4 space-y-2.5 rounded-xl bg-ink-50 p-4 text-sm text-ink-700">
          <li className="flex gap-2.5"><ShieldCheck className="mt-0.5 h-4 w-4 shrink-0 text-brand-700" aria-hidden="true" /><span>Tus datos se usan <b>solo</b> para organizar los campeonatos y mantener el sistema seguro. No se venden ni se usan para publicidad.</span></li>
          <li className="flex gap-2.5"><ShieldCheck className="mt-0.5 h-4 w-4 shrink-0 text-brand-700" aria-hidden="true" /><span>Tu cuenta es personal y eres responsable de lo que se haga con ella. Las acciones importantes quedan en una bitácora.</span></li>
          <li className="flex gap-2.5"><ShieldCheck className="mt-0.5 h-4 w-4 shrink-0 text-brand-700" aria-hidden="true" /><span>Puedes ver, corregir o pedir la eliminación de tus datos, y retirar tus consentimientos, cuando quieras.</span></li>
        </ul>

        <p className="mt-4 text-sm text-ink-700">Lee los documentos completos (se abren en una pestaña nueva):</p>
        <div className="mt-2 flex flex-wrap gap-2">
          <a ref={primero} href="/terminos" target="_blank" rel="noopener noreferrer" className="inline-flex items-center gap-1.5 rounded-lg border border-ink-200 px-3 py-2 text-sm font-medium text-brand-700 hover:bg-brand-50">Términos y condiciones <ExternalLink className="h-3.5 w-3.5" aria-hidden="true" /></a>
          <a href="/privacidad" target="_blank" rel="noopener noreferrer" className="inline-flex items-center gap-1.5 rounded-lg border border-ink-200 px-3 py-2 text-sm font-medium text-brand-700 hover:bg-brand-50">Política de privacidad <ExternalLink className="h-3.5 w-3.5" aria-hidden="true" /></a>
        </div>

        <label className="mt-5 flex cursor-pointer items-start gap-3 rounded-xl border border-ink-200 p-3 text-sm text-ink-800 hover:bg-ink-50">
          <input type="checkbox" checked={acepto} onChange={(e) => { setAcepto(e.target.checked); setError(""); }} className="mt-0.5 h-5 w-5 shrink-0 rounded border-ink-300 text-brand-600" />
          <span>He leído y acepto los <b>Términos y condiciones</b> y la <b>Política de privacidad</b> (versión {LEGAL_VERSION}, vigente desde el {LEGAL_VIGENTE_DESDE}).</span>
        </label>

        {error && <p role="alert" className="mt-3 text-sm font-medium text-brand-700">{error}</p>}

        <div className="mt-5 flex flex-col-reverse gap-3 sm:flex-row sm:items-center sm:justify-between">
          <button type="button" onClick={() => void logout()} className="inline-flex items-center justify-center gap-2 rounded-lg px-3 py-2 text-sm font-medium text-ink-600 hover:bg-ink-100"><LogOut className="h-4 w-4" aria-hidden="true" />No acepto, cerrar sesión</button>
          <Button size="lg" disabled={!acepto} loading={enviando} onClick={() => void aceptar()}>Aceptar y continuar</Button>
        </div>
      </div>
    </div>
  );
}
