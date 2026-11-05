"use client";
import { useState } from "react";
import { useParams } from "next/navigation";
import { CalendarDays, Download, FileSpreadsheet, Pencil, Trophy, Wand2 } from "lucide-react";
import { Button, Card, CardBody, CardHeader, ConfirmDialog, EmptyState, EstadoBadge, PageHeader, PageLoader, Tabs } from "@/components/ui";
import { ModalCampeonato } from "@/components/campeonatos/FormularioCampeonato";
import { PanelEstadisticas } from "@/components/campeonatos/Estadisticas";
import { HistorialPosiciones } from "@/components/campeonatos/HistorialPosiciones";
import { ListaJornadas } from "@/components/campeonatos/ListaJornadas";
import { ModalGenerarFixture } from "@/components/fixture/GenerarFixture";
import { CalidadDelFixture } from "@/components/fixture/PanelCalidad";
import { BandejaInscripciones } from "@/components/gestion/BandejaInscripciones";
import { TablaPosiciones } from "@/components/TablaPosiciones";
import { useAccion, useCampeonato, usePartidos } from "@/lib/hooks/queries";
import { campeonatoService, reporteService } from "@/lib/api/services";
import { mensajeDeError } from "@/lib/api/errors";
import { useToast } from "@/components/ui";
import { etiqueta, fechaCorta, aInputFechaHora } from "@/lib/utils";

const ESTADO_TEXTO: Record<string, string> = {
  PLANIFICACION: "Planificación", INSCRIPCIONES: "Inscripciones", INSCRIPCION_CERRADA: "Inscripciones cerradas",
  EN_CURSO: "En curso", FINALIZADO: "Finalizado", CANCELADO: "Cancelado",
};
const ACCION_TEXTO: Record<string, string> = {
  PLANIFICACION: "Volver a planificación", INSCRIPCIONES: "Abrir inscripciones", INSCRIPCION_CERRADA: "Cerrar inscripciones",
  EN_CURSO: "Iniciar y publicar campeonato",
  FINALIZADO: "Finalizar campeonato", CANCELADO: "Cancelar campeonato",
};

function Dato({ titulo, valor }: { titulo: string; valor: string | number }) {
  return <div><dt className="text-xs text-ink-500">{titulo}</dt><dd className="text-sm font-medium text-ink-900">{valor}</dd></div>;
}

export default function GestionCampeonatoDetalle() {
  const id = Number(useParams<{ id: string }>().id);
  const toast = useToast();
  const camp = useCampeonato(id);
  const partidos = usePartidos(String(id));
  const [pestana, setPestana] = useState("resumen");
  const [editar, setEditar] = useState(false);
  const [generar, setGenerar] = useState(false);
  const [nuevoEstado, setNuevoEstado] = useState<string | null>(null);
  const [descargando, setDescargando] = useState<"pdf" | "excel" | null>(null);

  const cambiarEstado = useAccion((estado: string) => campeonatoService.cambiarEstado(id, estado), {
    invalidar: ["campeonato", "campeonatos"], exito: (_, e) => `Estado actualizado a «${ESTADO_TEXTO[e]}».`,
  });

  if (camp.isLoading) return <PageLoader />;
  if (!camp.data) return <EmptyState icon={Trophy} title="Campeonato no encontrado" description="Puede que haya sido eliminado." />;
  const c = camp.data;
  const lista = partidos.data?.results ?? [];

  const descargar = async (formato: "pdf" | "excel") => {
    setDescargando(formato);
    try { await reporteService.descargar("campeonato", id, formato); toast.success("Reporte descargado."); }
    catch (e) { toast.error(mensajeDeError(e, "No se pudo descargar el reporte.")); }
    finally { setDescargando(null); }
  };
  const confirmarEstado = () => {
    if (!nuevoEstado) return;
    cambiarEstado.ejecutar(nuevoEstado, {
      onSuccess: () => setNuevoEstado(null),
      onError: (e) => { toast.error(mensajeDeError(e, "No se pudo cambiar el estado.")); setNuevoEstado(null); },
    });
  };

  return (
    <>
      <PageHeader
        breadcrumb={[{ label: "Campeonatos", href: "/gestion/campeonatos" }, { label: c.nombre }]}
        title={<span className="flex flex-wrap items-center gap-3">{c.nombre}<EstadoBadge estado={c.estado} /></span>}
        description={`${c.deporte_detalle?.nombre ?? ""} — ${c.categoria_detalle?.nombre ?? ""} (${c.categoria_detalle?.genero ?? ""})`}
        actions={<>
          <Button variant="secondary" size="sm" loading={descargando === "pdf"} icon={<Download className="h-4 w-4" />} onClick={() => descargar("pdf")}>PDF</Button>
          <Button variant="secondary" size="sm" loading={descargando === "excel"} icon={<FileSpreadsheet className="h-4 w-4" />} onClick={() => descargar("excel")}>Excel</Button>
          <Button variant="secondary" size="sm" icon={<Pencil className="h-4 w-4" />} onClick={() => setEditar(true)}>Editar</Button>
        </>}
      />

      <Tabs activa={pestana} onCambiar={setPestana} pestanas={[
        {
          id: "resumen", label: "Resumen",
          contenido: (
            <div className="grid gap-5 lg:grid-cols-3">
              <Card className="lg:col-span-2">
                <CardHeader title="Datos del campeonato" />
                <CardBody>
                  <dl className="grid grid-cols-2 gap-4 sm:grid-cols-3">
                    <Dato titulo="Formato" valor={etiqueta(c.formato)} />
                    <Dato titulo="Inicio" valor={fechaCorta(c.fecha_inicio)} />
                    <Dato titulo="Fin" valor={fechaCorta(c.fecha_fin)} />
                    <Dato titulo="Equipos aprobados" valor={`${c.total_equipos} de ${c.max_equipos}`} />
                    <Dato titulo="Jugadores por equipo" valor={`${c.min_jugadores} a ${c.max_jugadores}`} />
                    <Dato titulo="Cierre de inscripciones" valor={c.fecha_cierre_inscripcion ? aInputFechaHora(c.fecha_cierre_inscripcion).replace("T", " ") : "Sin definir"} />
                  </dl>
                  {c.descripcion && <p className="mt-4 text-sm text-ink-600">{c.descripcion}</p>}
                </CardBody>
              </Card>
              <Card>
                <CardHeader title="Estado" />
                <CardBody className="space-y-2">
                  {c.transiciones_permitidas.length === 0 ? (
                    <p className="text-sm text-ink-500">Este estado es final: no admite más cambios.</p>
                  ) : c.transiciones_permitidas.map((e) => (
                    <Button key={e} variant={e === "CANCELADO" ? "danger" : "secondary"} className="w-full" onClick={() => setNuevoEstado(e)}>{ACCION_TEXTO[e]}</Button>
                  ))}
                </CardBody>
              </Card>
            </div>
          ),
        },
        { id: "inscripciones", label: "Inscripciones", contenido: <BandejaInscripciones campeonato={id} /> },
        {
          id: "fixture", label: "Fixture",
          contenido: (
            <div className="space-y-4">
              {c.estado !== "INSCRIPCION_CERRADA" && lista.length === 0 && (
                <p className="rounded-lg border border-amber-200 bg-amber-50 p-3 text-sm text-amber-900">
                  Para generar el fixture, primero cierra las inscripciones desde la pestaña «Resumen».
                </p>
              )}
              {c.estado === "INSCRIPCION_CERRADA" && lista.length > 0 && (
                <p className="rounded-lg border border-sky-200 bg-sky-50 p-3 text-sm text-sky-900">
                  Este fixture es un borrador: solo lo ves tú. Revísalo y, si está bien, inicia el campeonato para publicarlo.
                </p>
              )}
              <div className="flex justify-end">
                <Button size="sm" icon={<Wand2 className="h-4 w-4" />} onClick={() => setGenerar(true)} disabled={c.estado !== "INSCRIPCION_CERRADA"}>
                  {lista.length ? "Regenerar fixture" : "Generar fixture"}
                </Button>
              </div>
              {partidos.isLoading ? <PageLoader /> : (
                <>
                {lista.length > 0 && <CalidadDelFixture campeonato={id} />}
                <ListaJornadas partidos={lista} destino={(pid) => `/gestion/partidos/${pid}`}
                  vacio={<EmptyState icon={CalendarDays} title="Todavía no hay partidos" description="Aprueba al menos 2 equipos y genera el fixture." />} />
                </>
              )}
            </div>
          ),
        },
        { id: "tabla", label: "Tabla", contenido: <TablaPosiciones campeonato={String(id)} /> },
        {
          id: "estadisticas", label: "Estadísticas",
          contenido: <div className="space-y-6"><PanelEstadisticas campeonato={String(id)} /><HistorialPosiciones campeonato={id} /></div>,
        },
      ]} />

      <ModalCampeonato key={c.actualizado_en ?? c.id} abierto={editar} onCerrar={() => setEditar(false)} campeonato={c} />
      <ModalGenerarFixture campeonato={c} partidosExistentes={lista.length} abierto={generar} onCerrar={() => setGenerar(false)} />
      <ConfirmDialog
        open={!!nuevoEstado}
        onClose={() => setNuevoEstado(null)}
        onConfirm={confirmarEstado}
        loading={cambiarEstado.pendiente}
        danger={nuevoEstado === "CANCELADO"}
        title={nuevoEstado ? ACCION_TEXTO[nuevoEstado] : ""}
        message={nuevoEstado === "CANCELADO" ? "El campeonato quedará cancelado y no podrá reactivarse." : `El campeonato pasará a «${nuevoEstado ? ESTADO_TEXTO[nuevoEstado] : ""}».`}
        confirmText="Confirmar"
      />
    </>
  );
}
