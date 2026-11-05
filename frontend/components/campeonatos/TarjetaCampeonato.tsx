import Link from "next/link";
import { CalendarRange, ChevronRight, Repeat, Users } from "lucide-react";
import { EstadoBadge } from "@/components/ui";
import { etiqueta, fechaCorta } from "@/lib/utils";
import type { Campeonato } from "@/types";

export function TarjetaCampeonato({ campeonato: c, href }: { campeonato: Campeonato; href: string }) {
  return (
    <Link href={href} className="group flex items-center justify-between gap-4 rounded-xl border border-ink-200 bg-white p-5 shadow-card transition-all hover:border-brand-300 hover:shadow-pop">
      <div className="min-w-0 flex-1">
        <div className="mb-1 flex flex-wrap items-center gap-2">
          <h2 className="font-semibold text-ink-900">{c.nombre}</h2>
          <EstadoBadge estado={c.estado} />
        </div>
        <p className="text-sm text-ink-500">
          {c.deporte_detalle?.nombre} — {c.categoria_detalle?.nombre} ({c.categoria_detalle?.genero})
        </p>
        <p className="mt-2 flex flex-wrap gap-x-5 gap-y-1 text-xs text-ink-500">
          <span className="inline-flex items-center gap-1.5"><CalendarRange className="h-3.5 w-3.5" aria-hidden="true" />{fechaCorta(c.fecha_inicio)} – {fechaCorta(c.fecha_fin)}</span>
          <span className="inline-flex items-center gap-1.5"><Users className="h-3.5 w-3.5" aria-hidden="true" />{c.total_equipos}/{c.max_equipos} equipos</span>
          <span className="inline-flex items-center gap-1.5"><Repeat className="h-3.5 w-3.5" aria-hidden="true" />{etiqueta(c.formato)}</span>
        </p>
      </div>
      <ChevronRight className="h-5 w-5 shrink-0 text-ink-300 transition-colors group-hover:text-brand-600" aria-hidden="true" />
    </Link>
  );
}
