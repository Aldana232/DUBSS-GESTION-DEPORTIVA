import type { ReactNode } from "react";
import { CalendarDays } from "lucide-react";
import { EmptyState } from "@/components/ui";
import { TarjetaPartido } from "@/components/TarjetaPartido";
import type { PartidoResumen } from "@/types";

/** Partidos agrupados por jornada (o por ronda en eliminación directa). */
export function ListaJornadas({ partidos, vacio, destino, accion }: {
  partidos: PartidoResumen[];
  vacio?: ReactNode;
  destino?: (id: number) => string;
  accion?: (p: PartidoResumen) => ReactNode;
}) {
  if (partidos.length === 0) {
    return <>{vacio ?? <EmptyState icon={CalendarDays} title="No hay partidos" description="El calendario se publicará pronto." />}</>;
  }
  const grupos = new Map<number, PartidoResumen[]>();
  partidos.forEach((p) => grupos.set(p.jornada, [...(grupos.get(p.jornada) ?? []), p]));
  return (
    <div className="space-y-6">
      {Array.from(grupos.entries()).map(([j, ps]) => (
        <section key={j}>
          <h3 className="mb-2 text-xs font-semibold uppercase tracking-wider text-ink-500">{ps[0].ronda ? ps[0].fase : `Jornada ${j}`}</h3>
          <div className="space-y-2">
            {ps.map((p) => (
              <div key={p.id} className="flex items-center gap-2">
                <div className="min-w-0 flex-1"><TarjetaPartido partido={p} destino={destino} /></div>
                {accion?.(p)}
              </div>
            ))}
          </div>
        </section>
      ))}
    </div>
  );
}
