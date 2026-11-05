"use client";
import Link from "next/link";
import { ArrowRight, CalendarDays, Trophy } from "lucide-react";
import { Button, Card, CardHeader, EmptyState, PageLoader } from "@/components/ui";
import { Logo } from "@/components/layout/Logo";
import { TarjetaCampeonato } from "@/components/campeonatos/TarjetaCampeonato";
import { TarjetaPartido } from "@/components/TarjetaPartido";
import { useCampeonatos, usePartidos } from "@/lib/hooks/queries";

export default function InicioPublico() {
  const campeonatos = useCampeonatos();
  const proximos = usePartidos("", "", { estado: "PROGRAMADO", ordering: "fecha_hora", page_size: "6" });
  const resultados = usePartidos("", "", { estado: "FINALIZADO", ordering: "-fecha_hora", page_size: "6" });
  const vigentes = campeonatos.data?.results.filter((c) => ["EN_CURSO", "INSCRIPCIONES", "INSCRIPCION_CERRADA"].includes(c.estado)) ?? [];

  return (
    <>
      <section className="mb-10 overflow-hidden rounded-2xl bg-gradient-to-br from-brand-700 via-brand-800 to-brand-900 px-6 py-10 text-white shadow-pop sm:px-10 sm:py-14">
        <div className="flex flex-col items-center gap-8 text-center md:flex-row md:text-left">
          <Logo size={128} className="shrink-0 shadow-pop ring-8 ring-white/15" />
          <div>
            <h1 className="text-3xl font-bold tracking-tight sm:text-4xl">Deporte universitario U.A.G.R.M.</h1>
            <p className="mt-3 max-w-xl text-brand-100">
              Sigue los campeonatos de la Dirección Universitaria de Bienestar Social y Salud: calendarios, resultados,
              tabla de posiciones y estadísticas, sin necesidad de iniciar sesión.
            </p>
            <div className="mt-6 flex flex-wrap justify-center gap-3 md:justify-start">
              <Link href="/campeonatos" className="inline-flex h-11 items-center gap-2 rounded-lg bg-white px-5 text-sm font-semibold text-brand-800 transition-colors hover:bg-brand-50">
                Ver campeonatos <ArrowRight className="h-4 w-4" aria-hidden="true" />
              </Link>
              <Link href="/login" className="inline-flex h-11 items-center rounded-lg border border-white/40 px-5 text-sm font-medium text-white transition-colors hover:bg-white/10">
                Acceso para organizadores y delegados
              </Link>
            </div>
          </div>
        </div>
      </section>

      <section aria-labelledby="vigentes" className="mb-10">
        <h2 id="vigentes" className="mb-3 text-lg font-semibold text-ink-900">Campeonatos vigentes</h2>
        {campeonatos.isLoading ? <PageLoader /> : vigentes.length === 0 ? (
          <EmptyState icon={Trophy} title="No hay campeonatos vigentes" description="Cuando se abra una inscripción o comience un torneo lo verás aquí."
            action={<Link href="/campeonatos"><Button variant="secondary">Ver todos los campeonatos</Button></Link>} />
        ) : (
          <ul className="space-y-3">
            {vigentes.map((c) => <li key={c.id}><TarjetaCampeonato campeonato={c} href={`/campeonatos/${c.id}`} /></li>)}
          </ul>
        )}
      </section>

      <div className="grid gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader title="Próximos partidos" />
          <div className="space-y-2 p-4">
            {proximos.isLoading ? <PageLoader /> : (proximos.data?.results.length ?? 0) === 0 ? (
              <EmptyState icon={CalendarDays} title="No hay partidos programados" className="border-0" />
            ) : proximos.data?.results.map((p) => <TarjetaPartido key={p.id} partido={p} />)}
          </div>
        </Card>
        <Card>
          <CardHeader title="Últimos resultados" />
          <div className="space-y-2 p-4">
            {resultados.isLoading ? <PageLoader /> : (resultados.data?.results.length ?? 0) === 0 ? (
              <EmptyState icon={CalendarDays} title="Aún no hay resultados" className="border-0" />
            ) : resultados.data?.results.map((p) => <TarjetaPartido key={p.id} partido={p} />)}
          </div>
        </Card>
      </div>
    </>
  );
}
