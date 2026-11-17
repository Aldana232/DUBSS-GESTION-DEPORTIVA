import { Bell, CalendarClock } from "lucide-react";
import { cn } from "@/lib/utils";
import { hace } from "@/lib/notificaciones";
import type { Notificacion } from "@/types";

/** Una fila de la bandeja: el punto rojo marca lo que falta leer. */
export function ItemNotificacion({ n, onAbrir }: { n: Notificacion; onAbrir: (n: Notificacion) => void }) {
  const Icono = n.datos?.partido_id ? CalendarClock : Bell;
  return (
    <button type="button" onClick={() => onAbrir(n)}
      className={cn("flex w-full items-start gap-3 px-4 py-3 text-left transition-colors hover:bg-ink-50", !n.leida && "bg-brand-50/60")}>
      <span className={cn("mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-full", n.leida ? "bg-ink-100 text-ink-500" : "bg-brand-600 text-white")}>
        <Icono className="h-4 w-4" aria-hidden="true" />
      </span>
      <span className="min-w-0 flex-1">
        <span className="flex items-center gap-2">
          <span className={cn("truncate text-sm text-ink-900", !n.leida && "font-semibold")}>{n.titulo}</span>
          {!n.leida && <span className="h-2 w-2 shrink-0 rounded-full bg-brand-600" aria-label="Sin leer" />}
        </span>
        <span className="mt-0.5 line-clamp-2 block text-xs text-ink-600">{n.mensaje}</span>
        <span className="mt-1 block text-[11px] text-ink-400">{hace(n.creada)}</span>
      </span>
    </button>
  );
}
