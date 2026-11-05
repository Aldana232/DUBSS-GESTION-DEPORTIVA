"use client";
import { ListOrdered } from "lucide-react";
import { Table, type Columna, PageLoader, EmptyState } from "@/components/ui";
import { useTabla } from "@/lib/hooks/queries";
import { cn } from "@/lib/utils";
import type { FilaPosicion } from "@/types";

const COLUMNAS: Columna<FilaPosicion>[] = [
  { clave: "pos", titulo: "#", alinear: "center", render: (f) => <span className="font-bold text-ink-400">{f.posicion}</span> },
  {
    clave: "equipo", titulo: "Equipo",
    render: (f) => (
      <span className="font-semibold text-ink-900">
        {f.equipo_detalle.nombre}
        <span className="ml-1.5 text-xs font-normal text-ink-400">{f.equipo_detalle.facultad}</span>
      </span>
    ),
  },
  ...(["pj", "pg", "pe", "pp", "gf", "gc"] as const).map((k): Columna<FilaPosicion> => ({
    clave: k, titulo: k.toUpperCase(), alinear: "center", render: (f) => f[k],
  })),
  {
    clave: "dg", titulo: "DG", alinear: "center",
    render: (f) => (
      <span className={cn("font-semibold", f.diferencia_goles > 0 && "text-emerald-600", f.diferencia_goles < 0 && "text-brand-600")}>
        {f.diferencia_goles > 0 ? "+" : ""}{f.diferencia_goles}
      </span>
    ),
  },
  { clave: "pts", titulo: "Pts", alinear: "center", render: (f) => <span className="text-base font-bold text-brand-700">{f.puntos}</span> },
];

export function TablaPosiciones({ campeonato }: { campeonato: string }) {
  const { data, isLoading } = useTabla(campeonato);
  if (!campeonato) return <EmptyState icon={ListOrdered} title="Selecciona un campeonato" description="Elige un campeonato para ver su clasificación." />;
  if (isLoading) return <PageLoader texto="Cargando tabla..." />;
  return (
    <Table
      columnas={COLUMNAS}
      filas={data ?? []}
      clave={(f) => f.id}
      resaltar={(_, i) => i === 0}
      vacio={{ titulo: "Aún no hay clasificación", descripcion: "Se genera al aprobar equipos y registrar resultados." }}
    />
  );
}
