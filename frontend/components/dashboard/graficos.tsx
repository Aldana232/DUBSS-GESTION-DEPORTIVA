import { cn } from "@/lib/utils";

/** Gráficos mínimos en SVG (sin librerías): accesibles, con etiqueta de texto y colores del sistema. */

export function BarraProgreso({ valor, maximo, etiqueta, clase = "fill-brand-600", alto = "h-2" }: { valor: number; maximo: number; etiqueta: string; clase?: string; alto?: string }) {
  const pct = maximo > 0 ? Math.max(0, Math.min(100, (valor / maximo) * 100)) : 0;
  return (
    <svg className={cn("w-full", alto)} role="img" aria-label={`${etiqueta}: ${valor} de ${maximo}`}>
      <rect width="100%" height="100%" rx="4" className="fill-ink-100" />
      {pct > 0 && <rect width={`${Math.max(pct, 2)}%`} height="100%" rx="4" className={clase} />}
    </svg>
  );
}

export interface Segmento { etiqueta: string; valor: number; clase: string; punto: string }

/** Barra dividida en partes (p. ej. victorias locales, empates y visitantes) con leyenda. */
export function BarraApilada({ segmentos, titulo }: { segmentos: Segmento[]; titulo: string }) {
  const total = segmentos.reduce((s, x) => s + x.valor, 0);
  let acumulado = 0;
  return (
    <div>
      <svg className="h-3 w-full" role="img" aria-label={`${titulo}: ${segmentos.map((s) => `${s.etiqueta} ${s.valor}`).join(", ")}`}>
        <rect width="100%" height="100%" rx="6" className="fill-ink-100" />
        {total > 0 && segmentos.map((s) => {
          const inicio = acumulado;
          acumulado += (s.valor / total) * 100;
          return s.valor > 0 ? <rect key={s.etiqueta} x={`${inicio}%`} width={`${(s.valor / total) * 100}%`} height="100%" className={s.clase} /> : null;
        })}
      </svg>
      <ul className="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-xs text-ink-600">
        {segmentos.map((s) => (
          <li key={s.etiqueta} className="inline-flex items-center gap-1.5"><span className={cn("h-2.5 w-2.5 rounded-full", s.punto)} aria-hidden="true" />{s.etiqueta} <b className="tabular-nums text-ink-900">{s.valor}</b></li>
        ))}
      </ul>
    </div>
  );
}

/** Ranking horizontal: la barra más larga es el máximo de la lista. */
export function BarrasHorizontales({ datos, clase = "fill-brand-600", unidad = "" }: { datos: { etiqueta: string; valor: number; detalle?: string }[]; clase?: string; unidad?: string }) {
  const maximo = Math.max(1, ...datos.map((d) => d.valor));
  return (
    <ul className="space-y-2.5">
      {datos.map((d) => (
        <li key={d.etiqueta + (d.detalle ?? "")} className="text-sm">
          <div className="mb-1 flex items-baseline justify-between gap-3">
            <span className="min-w-0 truncate font-medium text-ink-800">{d.etiqueta}{d.detalle && <span className="ml-1.5 text-xs font-normal text-ink-500">{d.detalle}</span>}</span>
            <span className="shrink-0 font-bold tabular-nums text-ink-900">{d.valor}{unidad}</span>
          </div>
          <BarraProgreso valor={d.valor} maximo={maximo} etiqueta={d.etiqueta} clase={clase} />
        </li>
      ))}
    </ul>
  );
}
