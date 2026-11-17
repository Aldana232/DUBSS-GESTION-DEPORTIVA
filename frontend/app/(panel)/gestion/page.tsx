"use client";
import Link from "next/link";
import { ArrowRight, CalendarDays, ClipboardCheck, MessageSquareWarning, Smartphone, Trophy, type LucideIcon } from "lucide-react";
import { Badge, Card, CardBody, CardHeader, EmptyState, PageHeader, PageLoader } from "@/components/ui";
import { useAuth } from "@/lib/hooks/useAuth";
import { useApi, useCampeonatos, usePartidos } from "@/lib/hooks/queries";
import { inscripcionService, quejaService } from "@/lib/api/services";
import { fechaDia, hora } from "@/lib/utils";
import { Indicador, saludo } from "@/components/dashboard/Indicador";
import { AccionesSugeridas, PartidosHoy, ResumenTemporada } from "@/components/dashboard/PanelesInteligentes";


export default function GestionInicio() {
  const { usuario } = useAuth();
  const campeonatos = useCampeonatos();
  const pendientes = useApi(["inscripciones", "PENDIENTE", ""], () => inscripcionService.listar({ estado: "PENDIENTE", page_size: 5 }));
  const quejas = useApi(["quejas", "ABIERTA"], () => quejaService.listar({ estado: "ABIERTA", page_size: 5 }));
  const proximos = usePartidos("", "", { estado: "PROGRAMADO", ordering: "fecha_hora", page_size: "5" });
  const enCurso = campeonatos.data?.results.filter((c) => c.estado === "EN_CURSO").length;

  return (
    <>
      <PageHeader title={`${saludo()}${usuario ? `, ${usuario.nombre}` : ""}`} description="Resumen operativo del sistema de gestión deportiva." />
      <div className="mb-8 grid grid-cols-2 gap-3 sm:gap-4 xl:grid-cols-4">
        <Indicador icono={Trophy} etiqueta="Campeonatos en curso" valor={enCurso ?? "—"} href="/gestion/campeonatos" />
        <Indicador icono={ClipboardCheck} etiqueta="Inscripciones pendientes" valor={pendientes.data?.count ?? "—"} href="/gestion/inscripciones" />
        <Indicador icono={MessageSquareWarning} etiqueta="Quejas abiertas" valor={quejas.data?.count ?? "—"} href="/gestion/quejas" />
        <Indicador icono={CalendarDays} etiqueta="Partidos programados" valor={proximos.data?.count ?? "—"} href="/gestion/fixture" />
      </div>

      <Link href="/planilla" className="group relative mb-8 flex items-center gap-4 overflow-hidden rounded-2xl bg-gradient-to-r from-ink-900 via-ink-800 to-brand-800 p-5 text-white shadow-card transition-shadow hover:shadow-pop">
        <span className="absolute -right-8 -top-10 h-32 w-32 rounded-full bg-brand-500/25 blur-2xl" aria-hidden="true" />
        <span className="relative flex h-12 w-12 shrink-0 items-center justify-center rounded-xl bg-white/10 ring-1 ring-inset ring-white/20"><Smartphone className="h-6 w-6" aria-hidden="true" /></span>
        <span className="relative min-w-0 flex-1">
          <span className="block text-base font-bold">Planilla móvil</span>
          <span className="block text-sm text-ink-200">Goles y tarjetas desde la cancha, también sin conexión. Instálala en tu celular.</span>
        </span>
        <ArrowRight className="relative h-5 w-5 shrink-0 transition-transform group-hover:translate-x-1" aria-hidden="true" />
      </Link>

      <div className="mb-6 grid gap-6 lg:grid-cols-2">
        <AccionesSugeridas />
        <PartidosHoy />
      </div>
      <div className="mb-6"><ResumenTemporada /></div>

      <div className="grid gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader title="Solicitudes por revisar" action={<Link href="/gestion/inscripciones" className="inline-flex items-center gap-1 text-sm font-medium text-brand-700 hover:underline">Ver bandeja<ArrowRight className="h-4 w-4" aria-hidden="true" /></Link>} />
          {pendientes.isLoading ? <PageLoader /> : (pendientes.data?.results.length ?? 0) === 0 ? (
            <EmptyState icon={ClipboardCheck} title="Todo al día" description="No hay inscripciones pendientes." className="m-5" />
          ) : (
            <ul className="divide-y divide-ink-100">
              {pendientes.data?.results.map((i) => (
                <li key={i.id} className="flex items-center justify-between gap-3 px-5 py-3 text-sm">
                  <span className="min-w-0"><b className="block truncate text-ink-900">{i.equipo_detalle.nombre}</b><span className="block truncate text-xs text-ink-500">{i.campeonato_nombre}</span></span>
                  <Badge tono="warning">Pendiente</Badge>
                </li>
              ))}
            </ul>
          )}
        </Card>
        <Card>
          <CardHeader title="Próximos partidos" action={<Link href="/gestion/fixture" className="inline-flex items-center gap-1 text-sm font-medium text-brand-700 hover:underline">Ver fixture<ArrowRight className="h-4 w-4" aria-hidden="true" /></Link>} />
          {proximos.isLoading ? <PageLoader /> : (proximos.data?.results.length ?? 0) === 0 ? (
            <EmptyState icon={CalendarDays} title="No hay partidos programados" className="m-5" />
          ) : (
            <ul className="divide-y divide-ink-100">
              {proximos.data?.results.map((p) => (
                <li key={p.id}>
                  <Link href={`/gestion/partidos/${p.id}`} className="flex items-center justify-between gap-3 px-5 py-3 text-sm transition-colors hover:bg-ink-50">
                    <span className="truncate font-medium text-ink-900">{p.local} <span className="font-normal text-ink-400">vs</span> {p.visitante}</span>
                    <span className="shrink-0 text-right text-xs text-ink-500">{fechaDia(p.fecha_hora)} {hora(p.fecha_hora)}</span>
                  </Link>
                </li>
              ))}
            </ul>
          )}
        </Card>
      </div>
    </>
  );
}
