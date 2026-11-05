"use client";
import { CartesianGrid, Legend, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { LineChart as IconoGrafico } from "lucide-react";
import { Card, CardBody, EmptyState, PageLoader } from "@/components/ui";
import { useHistorial } from "@/lib/hooks/queries";

const COLORES = ["#d21115", "#0284c7", "#16a34a", "#d97706", "#7c3aed", "#171a23", "#db2777", "#0d9488", "#65a30d", "#9a3412"];

/** Evolución de la posición de cada equipo al cerrar cada jornada (RF13). */
export function HistorialPosiciones({ campeonato }: { campeonato: number }) {
  const { data, isLoading } = useHistorial(campeonato);
  if (isLoading) return <PageLoader />;
  if (!data || data.length === 0) {
    return <EmptyState icon={IconoGrafico} title="Sin historial todavía" description="Se genera al cerrar cada jornada, cuando todos sus partidos tienen resultado." />;
  }
  const equipos = new Map<number, string>();
  data.forEach((j) => j.posiciones.forEach((p) => equipos.set(p.equipo, p.equipo_nombre)));
  const filas = data.map((j) => {
    const fila: Record<string, number> = { jornada: j.jornada };
    j.posiciones.forEach((p) => { fila[`e${p.equipo}`] = p.posicion; });
    return fila;
  });
  const lista = Array.from(equipos.entries());

  return (
    <Card>
      <CardBody>
        <p className="mb-3 text-sm text-ink-500">Posición de cada equipo al cierre de cada jornada (1 = líder).</p>
        <div className="h-80 w-full" role="img" aria-label="Gráfico de evolución de posiciones por jornada">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={filas} margin={{ top: 8, right: 16, bottom: 8, left: -8 }}>
              <CartesianGrid stroke="#eceef2" vertical={false} />
              <XAxis dataKey="jornada" tickFormatter={(v) => `J${v}`} tick={{ fontSize: 12 }} />
              <YAxis reversed allowDecimals={false} domain={[1, lista.length]} tick={{ fontSize: 12 }} />
              <Tooltip labelFormatter={(v) => `Jornada ${v}`} />
              <Legend wrapperStyle={{ fontSize: 12 }} />
              {lista.map(([id, nombre], i) => (
                <Line key={id} type="monotone" dataKey={`e${id}`} name={nombre} stroke={COLORES[i % COLORES.length]} strokeWidth={2} dot={{ r: 3 }} />
              ))}
            </LineChart>
          </ResponsiveContainer>
        </div>
      </CardBody>
    </Card>
  );
}
