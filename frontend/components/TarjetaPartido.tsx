import Link from "next/link";
import { ChevronRight } from "lucide-react";
import { EstadoBadge } from "@/components/ui";
import { fechaDia, hora } from "@/lib/utils";
import type { PartidoResumen } from "@/types";

/** Fila de partido para calendarios: local, marcador u hora, visitante y estado. */
export function TarjetaPartido({ partido: p, destino = (id) => `/partidos/${id}` }: {
  partido: PartidoResumen; destino?: (id: number) => string;
}) {
  const jugado = p.goles_local !== null && p.goles_visitante !== null;
  return (
    <Link
      href={destino(p.id)}
      className="group flex items-center gap-3 rounded-xl border border-ink-200 bg-white px-4 py-3 shadow-card transition-shadow hover:shadow-pop sm:gap-5"
    >
      <p className="min-w-0 flex-1 truncate text-right text-sm font-semibold text-ink-900">{p.local}</p>
      <div className="w-28 shrink-0 text-center sm:w-36">
        {jugado ? (
          <p className="text-xl font-bold tabular-nums text-ink-900">{p.goles_local} – {p.goles_visitante}</p>
        ) : (
          <>
            <p className="text-xs text-ink-500">{fechaDia(p.fecha_hora)}</p>
            <p className="text-sm font-bold text-ink-900">{hora(p.fecha_hora)}</p>
          </>
        )}
        <div className="mt-1"><EstadoBadge estado={p.estado} /></div>
      </div>
      <p className="min-w-0 flex-1 truncate text-sm font-semibold text-ink-900">{p.visitante}</p>
      <ChevronRight className="hidden h-4 w-4 shrink-0 text-ink-300 transition-colors group-hover:text-brand-600 sm:block" aria-hidden="true" />
    </Link>
  );
}
