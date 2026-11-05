import type { ReactNode } from "react";
import { cn } from "@/lib/utils";

export type BadgeTono = "neutral" | "brand" | "success" | "info" | "warning" | "danger";

const TONOS: Record<BadgeTono, string> = {
  neutral: "bg-ink-100 text-ink-700 ring-ink-200",
  brand:   "bg-brand-50 text-brand-700 ring-brand-200",
  success: "bg-emerald-50 text-emerald-700 ring-emerald-200",
  info:    "bg-sky-50 text-sky-700 ring-sky-200",
  warning: "bg-amber-50 text-amber-800 ring-amber-200",
  danger:  "bg-rose-50 text-rose-700 ring-rose-200",
};

export function Badge({ tono = "neutral", children, className }: { tono?: BadgeTono; children: ReactNode; className?: string }) {
  return (
    <span className={cn("inline-flex items-center whitespace-nowrap rounded-full px-2.5 py-0.5 text-xs font-medium ring-1 ring-inset", TONOS[tono], className)}>
      {children}
    </span>
  );
}

const ESTADOS: Record<string, { tono: BadgeTono; texto: string }> = {
  PLANIFICACION: { tono: "neutral", texto: "Planificación" },
  INSCRIPCIONES: { tono: "info", texto: "Inscripciones" },
  INSCRIPCION_CERRADA: { tono: "warning", texto: "Inscripciones cerradas" },
  EN_CURSO:      { tono: "success", texto: "En curso" },
  FINALIZADO:    { tono: "neutral", texto: "Finalizado" },
  CANCELADO:     { tono: "danger", texto: "Cancelado" },
  PROGRAMADO:    { tono: "info", texto: "Programado" },
  SUSPENDIDO:    { tono: "danger", texto: "Suspendido" },
  POSTERGADO:    { tono: "warning", texto: "Postergado" },
  WALKOVER:      { tono: "warning", texto: "W.O." },
};

/** Badge con el color y el texto estándar de cada estado de campeonato o partido. */
export function EstadoBadge({ estado }: { estado: string }) {
  const e = ESTADOS[estado] ?? { tono: "neutral" as BadgeTono, texto: estado };
  return <Badge tono={e.tono}>{e.texto}</Badge>;
}
