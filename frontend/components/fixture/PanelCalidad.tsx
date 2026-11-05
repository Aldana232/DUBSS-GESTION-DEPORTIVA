"use client";
import { BrainCircuit, CheckCircle2, ShieldAlert } from "lucide-react";
import { Badge, Card, CardBody, CardHeader, PageLoader } from "@/components/ui";
import { useApi } from "@/lib/hooks/queries";
import { fixtureService } from "@/lib/api/services";
import type { CalidadFixture, ResumenGeneracion } from "@/types";

function Metrica({ titulo, valor, detalle }: { titulo: string; valor: string; detalle?: string }) {
  return (
    <div className="rounded-lg bg-ink-50 p-3">
      <p className="text-xs text-ink-500">{titulo}</p>
      <p className="text-lg font-bold tabular-nums text-ink-900">{valor}</p>
      {detalle && <p className="text-[11px] leading-tight text-ink-500">{detalle}</p>}
    </div>
  );
}

const dias = (v: number | null) => (v === null ? "—" : `${v} d`);
const pct = (v: number | null) => (v === null ? "—" : `${v}%`);

/** Métricas de calidad del fixture: conflictos, descanso, franja ideal, equidad y (si aplica) puntaje del ML. */
export function PanelCalidad({ calidad, ml }: { calidad: CalidadFixture; ml?: ResumenGeneracion["ml"] }) {
  const sinConflictos = calidad.conflictos === 0;
  return (
    <div className="space-y-3">
      <p className={`flex items-center gap-2 text-sm font-medium ${sinConflictos ? "text-emerald-700" : "text-brand-700"}`}>
        {sinConflictos
          ? <><CheckCircle2 className="h-4 w-4" aria-hidden="true" />Sin conflictos de cancha ni de equipo</>
          : <><ShieldAlert className="h-4 w-4" aria-hidden="true" />{calidad.conflictos} conflicto(s) de programación</>}
      </p>
      <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
        <Metrica titulo="Descanso promedio" valor={dias(calidad.descanso_promedio_dias)} detalle={`mínimo ${dias(calidad.descanso_minimo_dias)}`} />
        <Metrica titulo="En franja ideal" valor={pct(calidad.en_franja_ideal_pct)} detalle="10:00 a 17:59" />
        <Metrica titulo="Equidad" valor={pct(calidad.equidad_pct)} detalle="reparto de horarios entre equipos" />
        {ml ? <Metrica titulo="Puntaje del modelo" valor={`${Math.round(ml.puntaje_medio * 100)}%`} detalle={`resuelto en ${ml.segundos} s`} />
            : <Metrica titulo="Partidos" valor={String(calidad.partidos)} />}
      </div>
      {ml && <p className="text-xs text-ink-500">Modelo {ml.modelo_version} · {ml.jornadas} jornadas optimizadas.</p>}
    </div>
  );
}

/** Calidad del fixture ya guardado de un campeonato (para el organizador). */
export function CalidadDelFixture({ campeonato }: { campeonato: number }) {
  const { data, isLoading } = useApi(["calidad", campeonato], () => fixtureService.calidad(campeonato));
  if (isLoading) return <PageLoader />;
  if (!data || data.partidos === 0) return null;
  return (
    <Card>
      <CardHeader
        title="Calidad del fixture"
        action={data.generado_por_ml
          ? <Badge tono="brand"><BrainCircuit className="mr-1 h-3 w-3" aria-hidden="true" />Optimizado con ML</Badge>
          : <Badge>Método base</Badge>}
      />
      <CardBody><PanelCalidad calidad={data} /></CardBody>
    </Card>
  );
}
