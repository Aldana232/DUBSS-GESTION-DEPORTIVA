import type { ReactNode } from "react";
import { ChevronLeft, ChevronRight, Inbox } from "lucide-react";
import { cn } from "@/lib/utils";
import { Button } from "./Button";
import { EmptyState } from "./EmptyState";

export interface Columna<T> {
  clave: string;
  titulo: string;
  render: (fila: T) => ReactNode;
  alinear?: "left" | "center" | "right";
  className?: string;
}

const ALINEAR = { left: "text-left", center: "text-center", right: "text-right" };

/** Tabla con scroll horizontal en pantallas angostas, estado vacío y paginación opcional. */
export function Table<T>({ columnas, filas, clave, vacio, resaltar, pagina }: {
  columnas: Columna<T>[];
  filas: T[];
  clave: (fila: T) => string | number;
  vacio?: { titulo: string; descripcion?: string };
  resaltar?: (fila: T, indice: number) => boolean;
  pagina?: { actual: number; total: number; onCambiar: (p: number) => void };
}) {
  if (filas.length === 0) {
    return <EmptyState icon={Inbox} title={vacio?.titulo ?? "Sin datos"} description={vacio?.descripcion} />;
  }
  return (
    <div className="overflow-hidden rounded-xl border border-ink-200 bg-white shadow-card">
      <div className="overflow-x-auto scroll-thin">
        <table className="w-full min-w-[32rem] text-sm">
          <thead>
            <tr className="bg-ink-900 text-white">
              {columnas.map((c) => (
                <th key={c.clave} scope="col" className={cn("px-3 py-3 text-xs font-semibold uppercase tracking-wide", ALINEAR[c.alinear ?? "left"], c.className)}>
                  {c.titulo}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-ink-100">
            {filas.map((fila, i) => (
              <tr key={clave(fila)} className={cn("transition-colors hover:bg-ink-50", resaltar?.(fila, i) && "bg-brand-50/60")}>
                {columnas.map((c) => (
                  <td key={c.clave} className={cn("px-3 py-2.5 text-ink-700", ALINEAR[c.alinear ?? "left"], c.className)}>
                    {c.render(fila)}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {pagina && pagina.total > 1 && (
        <div className="flex items-center justify-between border-t border-ink-100 px-4 py-3 text-sm text-ink-600">
          <span>Página {pagina.actual} de {pagina.total}</span>
          <div className="flex gap-2">
            <Button size="sm" variant="secondary" aria-label="Página anterior" disabled={pagina.actual <= 1} onClick={() => pagina.onCambiar(pagina.actual - 1)} icon={<ChevronLeft className="h-4 w-4" />} />
            <Button size="sm" variant="secondary" aria-label="Página siguiente" disabled={pagina.actual >= pagina.total} onClick={() => pagina.onCambiar(pagina.actual + 1)} icon={<ChevronRight className="h-4 w-4" />} />
          </div>
        </div>
      )}
    </div>
  );
}
