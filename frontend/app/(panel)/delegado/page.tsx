"use client";
import Link from "next/link";
import { ArrowRight, CalendarDays, ClipboardCheck, MessageSquareWarning, Shield, type LucideIcon } from "lucide-react";
import { Badge, Card, CardBody, CardHeader, EmptyState, PageHeader, PageLoader } from "@/components/ui";
import { useAuth } from "@/lib/hooks/useAuth";
import { useApi, useMisEquipos, usePartidosDeEquipos } from "@/lib/hooks/queries";
import { inscripcionService, quejaService } from "@/lib/api/services";
import { fechaDia, hora } from "@/lib/utils";
import { Indicador } from "@/components/dashboard/Indicador";
import { ProximoPartidoDestacado } from "@/components/dashboard/PanelesInteligentes";

export default function DelegadoInicio() {
  const { usuario } = useAuth();
  const equipos = useMisEquipos();
  const ids = (equipos.data ?? []).map((e) => e.id);
  const { partidos, cargando } = usePartidosDeEquipos(ids);
  const inscripciones = useApi(["inscripciones", "mias"], () => inscripcionService.listar());
  const quejas = useApi(["quejas", "mias"], () => quejaService.mias());

  const proximos = partidos.filter((p) => p.estado === "PROGRAMADO").slice(0, 5);
  const pendientes = inscripciones.data?.results.filter((i) => i.estado === "PENDIENTE").length;
  const abiertas = quejas.data?.results.filter((q) => q.estado === "ABIERTA" || q.estado === "EN_REVISION").length;

  return (
    <>
      <PageHeader title={`Hola, ${usuario?.nombre ?? ""}`} description="Panel del delegado: tu equipo, tus inscripciones y tus partidos." />
      <ProximoPartidoDestacado partido={proximos[0]} />
      <div className="mb-8 grid grid-cols-2 gap-3 sm:gap-4 xl:grid-cols-4">
        <Indicador icono={Shield} etiqueta="Mis equipos" valor={equipos.data?.length ?? "—"} href="/delegado/equipos" />
        <Indicador icono={ClipboardCheck} etiqueta="Inscripciones pendientes" valor={pendientes ?? "—"} href="/delegado/inscripciones" />
        <Indicador icono={CalendarDays} etiqueta="Próximos partidos" valor={cargando ? "—" : proximos.length} href="/delegado/calendario" />
        <Indicador icono={MessageSquareWarning} etiqueta="Quejas en trámite" valor={abiertas ?? "—"} href="/delegado/quejas" />
      </div>
      <Card>
        <CardHeader title="Próximos partidos de mis equipos" action={<Link href="/delegado/calendario" className="inline-flex items-center gap-1 text-sm font-medium text-brand-700 hover:underline">Ver calendario<ArrowRight className="h-4 w-4" aria-hidden="true" /></Link>} />
        {cargando ? <PageLoader /> : proximos.length === 0 ? (
          <EmptyState icon={CalendarDays} title="Sin partidos programados" description="Cuando tus equipos tengan fixture, los verás aquí." className="m-5" />
        ) : (
          <ul className="divide-y divide-ink-100">
            {proximos.map((p) => (
              <li key={p.id}>
                <Link href={`/partidos/${p.id}`} className="flex items-center justify-between gap-3 px-5 py-3 text-sm transition-colors hover:bg-ink-50">
                  <span className="truncate font-medium text-ink-900">{p.local} <span className="font-normal text-ink-400">vs</span> {p.visitante}</span>
                  <span className="flex shrink-0 items-center gap-3 text-xs text-ink-500"><Badge>J{p.jornada}</Badge>{fechaDia(p.fecha_hora)} {hora(p.fecha_hora)}</span>
                </Link>
              </li>
            ))}
          </ul>
        )}
      </Card>
    </>
  );
}
