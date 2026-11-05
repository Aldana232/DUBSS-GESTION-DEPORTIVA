"use client";
import { BarChart3, Goal, Shield, TrendingUp } from "lucide-react";
import { Card, CardBody, EmptyState, PageLoader, Table, type Columna } from "@/components/ui";
import { useEstadisticas } from "@/lib/hooks/queries";
import type { Estadisticas } from "@/types";

type Goleador = Estadisticas["goleadores"][number];
type Tarjeta = Estadisticas["tarjetas"][number];

const GOLEADORES: Columna<Goleador>[] = [
  { clave: "j", titulo: "Jugador", render: (f) => <span className="font-medium text-ink-900">{f.jugador}</span> },
  { clave: "e", titulo: "Equipo", render: (f) => f.equipo },
  { clave: "g", titulo: "Goles", alinear: "center", render: (f) => <span className="font-bold text-brand-700">{f.goles}</span> },
];
const TARJETAS: Columna<Tarjeta>[] = [
  { clave: "j", titulo: "Jugador", render: (f) => <span className="font-medium text-ink-900">{f.jugador}</span> },
  { clave: "e", titulo: "Equipo", render: (f) => f.equipo },
  { clave: "a", titulo: "Amarillas", alinear: "center", render: (f) => f.amarillas },
  { clave: "r", titulo: "Rojas", alinear: "center", render: (f) => f.rojas },
];

function Dato({ etiqueta, valor, detalle }: { etiqueta: string; valor: string | number; detalle?: string }) {
  return (
    <Card>
      <CardBody className="p-4">
        <p className="text-xs text-ink-500">{etiqueta}</p>
        <p className="text-2xl font-bold tabular-nums text-ink-900">{valor}</p>
        {detalle && <p className="truncate text-xs text-ink-500">{detalle}</p>}
      </CardBody>
    </Card>
  );
}

export function PanelEstadisticas({ campeonato }: { campeonato: string }) {
  const { data, isLoading } = useEstadisticas(campeonato);
  if (isLoading) return <PageLoader texto="Calculando estadísticas..." />;
  if (!data || data.resumen.partidos_jugados === 0) {
    return <EmptyState icon={BarChart3} title="Aún no hay estadísticas" description="Aparecerán cuando se registren resultados." />;
  }
  const { resumen: r } = data;
  return (
    <div className="space-y-6">
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <Dato etiqueta="Partidos jugados" valor={`${r.partidos_jugados}/${r.partidos_total}`} />
        <Dato etiqueta="Goles" valor={r.goles} detalle={`${r.promedio_goles} por partido`} />
        <Dato etiqueta="Mejor ataque" valor={data.mejor_ataque?.goles ?? "—"} detalle={data.mejor_ataque?.equipo} />
        <Dato etiqueta="Mejor defensa" valor={data.mejor_defensa?.goles ?? "—"} detalle={data.mejor_defensa ? `${data.mejor_defensa.equipo} (goles en contra)` : undefined} />
      </div>
      <Card>
        <CardBody className="flex flex-wrap items-center justify-around gap-4 text-center text-sm">
          <span><TrendingUp className="mx-auto mb-1 h-4 w-4 text-brand-600" aria-hidden="true" /><b className="text-lg">{r.victorias_local}</b><br />victorias locales</span>
          <span><Shield className="mx-auto mb-1 h-4 w-4 text-ink-400" aria-hidden="true" /><b className="text-lg">{r.empates}</b><br />empates</span>
          <span><TrendingUp className="mx-auto mb-1 h-4 w-4 text-sky-600" aria-hidden="true" /><b className="text-lg">{r.victorias_visitante}</b><br />victorias visitantes</span>
        </CardBody>
      </Card>
      <div className="grid gap-6 lg:grid-cols-2">
        <section>
          <h3 className="mb-2 flex items-center gap-2 text-sm font-semibold text-ink-900"><Goal className="h-4 w-4 text-brand-600" aria-hidden="true" />Goleadores</h3>
          <Table columnas={GOLEADORES} filas={data.goleadores} clave={(f) => f.jugador_id} vacio={{ titulo: "Sin goles identificados" }} />
        </section>
        <section>
          <h3 className="mb-2 flex items-center gap-2 text-sm font-semibold text-ink-900"><CardHeaderIcono />Tarjetas</h3>
          <Table columnas={TARJETAS} filas={data.tarjetas} clave={(f) => f.jugador_id} vacio={{ titulo: "Sin tarjetas" }} />
        </section>
      </div>
    </div>
  );
}

function CardHeaderIcono() {
  return <span className="inline-block h-4 w-3 rounded-sm bg-amber-400" aria-hidden="true" />;
}

