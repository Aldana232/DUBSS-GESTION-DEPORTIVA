"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import { ArrowRight, CalendarClock, CheckCircle2, CircleAlert, Info, Lightbulb, MapPin, Sparkles, Trophy } from "lucide-react";
import { Badge, Card, CardBody, CardHeader, EmptyState, PageLoader, Select } from "@/components/ui";
import { BarraApilada, BarraProgreso, BarrasHorizontales } from "@/components/dashboard/graficos";
import { useApi, useCampeonatos, useEstadisticas, useTabla } from "@/lib/hooks/queries";
import { fixtureService, mlService } from "@/lib/api/services";
import { cn, fechaDia, hora } from "@/lib/utils";
import type { AccionSugerida } from "@/types";

const PRIORIDAD: Record<AccionSugerida["prioridad"], { icono: typeof Info; clase: string; texto: string; tono: "danger" | "warning" | "info" }> = {
  ALTA: { icono: CircleAlert, clase: "bg-rose-50 text-rose-600", texto: "Urgente", tono: "danger" },
  MEDIA: { icono: Lightbulb, clase: "bg-amber-50 text-amber-600", texto: "Importante", tono: "warning" },
  BAJA: { icono: Info, clase: "bg-sky-50 text-sky-600", texto: "Informativa", tono: "info" },
};

/** Lo que conviene hacer ahora, calculado por el sistema con datos reales (clima, quejas, resultados sin registrar, inscripciones...). */
export function AccionesSugeridas() {
  const { data, isLoading } = useApi(["acciones-sugeridas"], () => mlService.acciones());
  return (
    <Card>
      <CardHeader title={<span className="inline-flex items-center gap-2"><Sparkles className="h-4 w-4 text-brand-600" aria-hidden="true" />Acciones sugeridas por la IA</span>} action={data && data.length > 0 ? <Badge tono="brand">{data.length}</Badge> : undefined} />
      {isLoading ? <PageLoader /> : !data || data.length === 0 ? (
        <EmptyState icon={CheckCircle2} title="Todo en orden" description="El sistema no detecta nada urgente por hacer." className="m-5" />
      ) : (
        <ul className="max-h-96 divide-y divide-ink-100 overflow-y-auto scroll-thin">
          {data.map((a, i) => {
            const p = PRIORIDAD[a.prioridad];
            return (
              <li key={`${a.enlace}-${i}`}>
                <Link href={a.enlace} className="group flex items-start gap-3 px-5 py-3.5 transition-colors hover:bg-ink-50">
                  <span className={cn("mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-lg", p.clase)}><p.icono className="h-4 w-4" aria-hidden="true" /></span>
                  <span className="min-w-0 flex-1"><span className="mb-0.5 block"><Badge tono={p.tono}>{p.texto}</Badge></span><span className="text-sm text-ink-800">{a.mensaje}</span></span>
                  <ArrowRight className="mt-1 h-4 w-4 shrink-0 text-ink-300 transition-transform group-hover:translate-x-0.5" aria-hidden="true" />
                </Link>
              </li>
            );
          })}
        </ul>
      )}
    </Card>
  );
}

/** Partidos de hoy en toda la competencia, con acceso a la planilla móvil. */
export function PartidosHoy() {
  const { data, isLoading } = useApi(["partidos-hoy"], () => fixtureService.hoy());
  const hoy = (data?.partidos ?? []).filter((p) => new Date(p.fecha_hora).toDateString() === new Date().toDateString());
  return (
    <Card>
      <CardHeader title={<span className="inline-flex items-center gap-2"><CalendarClock className="h-4 w-4 text-brand-600" aria-hidden="true" />Hoy en la cancha</span>}
        action={<Link href="/planilla" className="inline-flex items-center gap-1 text-sm font-medium text-brand-700 hover:underline">Planilla móvil<ArrowRight className="h-4 w-4" aria-hidden="true" /></Link>} />
      {isLoading ? <PageLoader /> : hoy.length === 0 ? (
        <EmptyState icon={CalendarClock} title="Sin partidos hoy" description="Los partidos programados para hoy aparecerán aquí." className="m-5" />
      ) : (
        <ul className="divide-y divide-ink-100">
          {hoy.map((p) => (
            <li key={p.id}>
              <Link href={`/gestion/partidos/${p.id}`} className="flex items-center gap-3 px-5 py-3 transition-colors hover:bg-ink-50">
                <span className="flex w-14 shrink-0 flex-col items-center rounded-lg bg-ink-900 py-1.5 text-white"><span className="text-sm font-bold tabular-nums">{new Date(p.fecha_hora).toLocaleTimeString("es-BO", { hour: "2-digit", minute: "2-digit", hour12: false })}</span></span>
                <span className="min-w-0 flex-1"><span className="block truncate text-sm font-semibold text-ink-900">{p.local.nombre} <span className="font-normal text-ink-400">vs</span> {p.visitante.nombre}</span>
                  <span className="flex items-center gap-1 truncate text-xs text-ink-500"><MapPin className="h-3 w-3 shrink-0" aria-hidden="true" />{p.cancha ?? "Cancha por definir"} · {p.campeonato.nombre}</span></span>
                {p.resultado ? <Badge tono="success">{p.resultado.goles_local}-{p.resultado.goles_visitante}</Badge> : <Badge>Por jugar</Badge>}
              </Link>
            </li>
          ))}
        </ul>
      )}
    </Card>
  );
}

/** Avance, goles, reparto de resultados, goleadores y clasificación del campeonato en curso. */
export function ResumenTemporada() {
  const campeonatos = useCampeonatos();
  const enCurso = (campeonatos.data?.results ?? []).filter((c) => c.estado === "EN_CURSO");
  const [elegido, setElegido] = useState("");
  useEffect(() => { if (!elegido && enCurso.length) setElegido(String(enCurso[0].id)); }, [elegido, enCurso]);
  const stats = useEstadisticas(elegido);
  const tabla = useTabla(elegido);
  const r = stats.data?.resumen;

  if (campeonatos.isLoading) return <Card><PageLoader /></Card>;
  if (enCurso.length === 0) {
    return <Card><EmptyState icon={Trophy} title="No hay campeonatos en curso" description="Cuando inicies un campeonato verás aquí su avance y sus estadísticas." className="m-5" /></Card>;
  }
  return (
    <Card>
      <CardHeader title={<span className="inline-flex items-center gap-2"><Trophy className="h-4 w-4 text-brand-600" aria-hidden="true" />Resumen de la temporada</span>}
        action={enCurso.length > 1 ? <Select aria-label="Campeonato" value={elegido} onChange={(e) => setElegido(e.target.value)} className="h-8 w-56 text-xs">{enCurso.map((c) => <option key={c.id} value={c.id}>{c.nombre}</option>)}</Select> : <span className="text-sm font-medium text-ink-600">{enCurso[0].nombre}</span>} />
      <CardBody className="space-y-6">
        {!r ? <PageLoader /> : (
          <>
            <div className="grid gap-3 sm:grid-cols-3">
              <div className="rounded-2xl bg-ink-50 p-4"><p className="text-xs text-ink-500">Avance del campeonato</p>
                <p className="mb-2 text-2xl font-black tabular-nums text-ink-900">{r.partidos_jugados}<span className="text-base font-semibold text-ink-400"> / {r.partidos_total}</span></p>
                <BarraProgreso valor={r.partidos_jugados} maximo={r.partidos_total} etiqueta="Partidos jugados" /></div>
              <div className="rounded-2xl bg-ink-50 p-4"><p className="text-xs text-ink-500">Goles</p><p className="text-2xl font-black tabular-nums text-ink-900">{r.goles}</p><p className="text-xs text-ink-500">{r.promedio_goles} por partido</p></div>
              <div className="rounded-2xl bg-ink-50 p-4"><p className="text-xs text-ink-500">Reparto de resultados</p><div className="mt-2">
                <BarraApilada titulo="Resultados" segmentos={[
                  { etiqueta: "Locales", valor: r.victorias_local, clase: "fill-brand-600", punto: "bg-brand-600" },
                  { etiqueta: "Empates", valor: r.empates, clase: "fill-amber-400", punto: "bg-amber-400" },
                  { etiqueta: "Visitantes", valor: r.victorias_visitante, clase: "fill-sky-500", punto: "bg-sky-500" },
                ]} /></div></div>
            </div>
            <div className="grid gap-6 lg:grid-cols-2">
              <div>
                <h3 className="mb-3 text-sm font-bold text-ink-900">Goleadores</h3>
                {stats.data && stats.data.goleadores.length > 0
                  ? <BarrasHorizontales datos={stats.data.goleadores.slice(0, 5).map((g) => ({ etiqueta: g.jugador, valor: g.goles, detalle: g.equipo }))} />
                  : <p className="text-sm text-ink-500">Aún no hay goles registrados.</p>}
              </div>
              <div>
                <h3 className="mb-3 text-sm font-bold text-ink-900">Clasificación</h3>
                {tabla.data && tabla.data.length > 0 ? (
                  <ol className="space-y-1.5">
                    {tabla.data.slice(0, 5).map((f) => (
                      <li key={f.id} className="flex items-center gap-3 rounded-xl px-3 py-2 text-sm odd:bg-ink-50">
                        <span className={cn("flex h-6 w-6 items-center justify-center rounded-full text-xs font-bold", f.posicion === 1 ? "bg-brand-600 text-white" : "bg-ink-200 text-ink-700")}>{f.posicion}</span>
                        <span className="min-w-0 flex-1 truncate font-medium text-ink-900">{f.equipo_detalle.nombre}</span>
                        <span className="text-xs text-ink-500 tabular-nums">{f.pj} PJ · DG {f.diferencia_goles > 0 ? "+" : ""}{f.diferencia_goles}</span>
                        <span className="w-8 text-right font-bold tabular-nums text-brand-700">{f.puntos}</span>
                      </li>
                    ))}
                  </ol>
                ) : <p className="text-sm text-ink-500">La clasificación aparecerá al registrar resultados.</p>}
              </div>
            </div>
          </>
        )}
      </CardBody>
    </Card>
  );
}

/** Próximo partido del delegado con cuenta regresiva, en una tarjeta destacada. */
export function ProximoPartidoDestacado({ partido }: { partido: { id: number; local: string; visitante: string; cancha: string; fecha_hora: string; jornada: number } | undefined }) {
  if (!partido) return null;
  const dias = Math.ceil((new Date(partido.fecha_hora).getTime() - Date.now()) / 86_400_000);
  const cuando = new Date(partido.fecha_hora).toDateString() === new Date().toDateString() ? "Hoy" : dias <= 1 ? "Mañana" : `En ${dias} días`;
  return (
    <Link href={`/partidos/${partido.id}`} className="group relative mb-8 block overflow-hidden rounded-2xl bg-gradient-to-r from-ink-900 via-ink-800 to-brand-800 p-6 text-white shadow-card transition-shadow hover:shadow-pop">
      <span className="absolute -right-8 -top-12 h-40 w-40 rounded-full bg-brand-500/25 blur-2xl" aria-hidden="true" />
      <div className="relative flex flex-wrap items-center justify-between gap-4">
        <div>
          <p className="mb-1 text-xs font-semibold uppercase tracking-wider text-brand-200">Tu próximo partido · {cuando}</p>
          <p className="text-xl font-black sm:text-2xl">{partido.local} <span className="font-medium text-brand-300">vs</span> {partido.visitante}</p>
          <p className="mt-1 flex flex-wrap items-center gap-x-4 gap-y-1 text-sm text-ink-200"><span>{fechaDia(partido.fecha_hora)} · {hora(partido.fecha_hora)}</span><span className="inline-flex items-center gap-1"><MapPin className="h-3.5 w-3.5" aria-hidden="true" />{partido.cancha || "Cancha por definir"}</span><span>Jornada {partido.jornada}</span></p>
        </div>
        <ArrowRight className="h-6 w-6 shrink-0 transition-transform group-hover:translate-x-1" aria-hidden="true" />
      </div>
    </Link>
  );
}
