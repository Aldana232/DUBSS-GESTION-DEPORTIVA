"use client";
import { useEffect, useRef, type ReactNode } from "react";
import { X } from "lucide-react";

/** Hoja inferior táctil (patrón de apps móviles): se cierra con Esc, tocando fuera o con la X. */
export function Hoja({ abierta, onCerrar, titulo, children }: { abierta: boolean; onCerrar: () => void; titulo: string; children: ReactNode }) {
  const panel = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (!abierta) return;
    const previo = document.activeElement as HTMLElement | null;
    panel.current?.focus();
    const tecla = (e: KeyboardEvent) => { if (e.key === "Escape") onCerrar(); };
    document.addEventListener("keydown", tecla);
    document.body.classList.add("overflow-hidden");
    return () => {
      document.removeEventListener("keydown", tecla);
      document.body.classList.remove("overflow-hidden");
      previo?.focus?.();
    };
  }, [abierta, onCerrar]);
  if (!abierta) return null;
  return (
    <div className="fixed inset-0 z-50 flex items-end justify-center sm:items-center">
      <button type="button" aria-label="Cerrar" tabIndex={-1} className="absolute inset-0 animate-fade-in bg-ink-950/60 backdrop-blur-sm" onClick={onCerrar} />
      <div ref={panel} role="dialog" aria-modal="true" aria-label={titulo} tabIndex={-1}
        className="relative z-10 max-h-[90vh] w-full max-w-lg animate-sheet-up overflow-y-auto rounded-t-3xl bg-white pb-[max(1.25rem,env(safe-area-inset-bottom))] shadow-pop sm:rounded-3xl">
        <div className="sticky top-0 z-10 flex items-center justify-between bg-white/95 px-5 pb-2 pt-4 backdrop-blur">
          <span className="absolute left-1/2 top-2 h-1 w-10 -translate-x-1/2 rounded-full bg-ink-200 sm:hidden" aria-hidden="true" />
          <h2 className="text-base font-bold text-ink-900">{titulo}</h2>
          <button type="button" onClick={onCerrar} aria-label="Cerrar" className="flex h-9 w-9 items-center justify-center rounded-full text-ink-500 hover:bg-ink-100">
            <X className="h-5 w-5" aria-hidden="true" />
          </button>
        </div>
        <div className="px-5 pb-1 pt-2">{children}</div>
      </div>
    </div>
  );
}
