"use client";
import { useId, useRef, type KeyboardEvent, type ReactNode } from "react";
import { cn } from "@/lib/utils";

export interface Pestana { id: string; label: string; contenido: ReactNode }

/** Pestañas accesibles (flechas izquierda/derecha, roles ARIA). Controladas desde fuera. */
export function Tabs({ pestanas, activa, onCambiar }: { pestanas: Pestana[]; activa: string; onCambiar: (id: string) => void }) {
  const base = useId();
  const refs = useRef<Record<string, HTMLButtonElement | null>>({});
  const mover = (e: KeyboardEvent, i: number) => {
    if (e.key !== "ArrowRight" && e.key !== "ArrowLeft") return;
    const siguiente = pestanas[(i + (e.key === "ArrowRight" ? 1 : pestanas.length - 1)) % pestanas.length];
    onCambiar(siguiente.id);
    refs.current[siguiente.id]?.focus();
  };
  const actual = pestanas.find((p) => p.id === activa) ?? pestanas[0];
  return (
    <div>
      <div role="tablist" className="flex gap-1 overflow-x-auto border-b border-ink-200 scroll-thin">
        {pestanas.map((p, i) => (
          <button
            key={p.id}
            ref={(el) => { refs.current[p.id] = el; }}
            role="tab"
            type="button"
            id={`${base}-${p.id}`}
            aria-selected={p.id === actual.id}
            aria-controls={`${base}-panel`}
            tabIndex={p.id === actual.id ? 0 : -1}
            onClick={() => onCambiar(p.id)}
            onKeyDown={(e) => mover(e, i)}
            className={cn(
              "-mb-px whitespace-nowrap border-b-2 px-4 py-2.5 text-sm font-medium transition-colors",
              p.id === actual.id ? "border-brand-600 text-brand-700" : "border-transparent text-ink-500 hover:text-ink-800",
            )}
          >
            {p.label}
          </button>
        ))}
      </div>
      <div role="tabpanel" id={`${base}-panel`} aria-labelledby={`${base}-${actual.id}`} className="pt-4">
        {actual.contenido}
      </div>
    </div>
  );
}
