"use client";
import { useState } from "react";
import { AlertTriangle, CheckCircle2, XCircle } from "lucide-react";
import { Badge, Button, FormField, Modal, PageLoader, Select, Table, Textarea, type Columna } from "@/components/ui";
import { useAccion, useApi, useCampeonatos } from "@/lib/hooks/queries";
import { inscripcionService } from "@/lib/api/services";
import { mensajeDeError } from "@/lib/api/errors";
import { fechaCorta } from "@/lib/utils";
import type { Inscripcion } from "@/types";

const TONO = { PENDIENTE: "warning", APROBADA: "success", RECHAZADA: "danger" } as const;

/** Resultado de revisar los requisitos de una inscripción (bloqueantes y advertencias). */
export function RequisitosInscripcion({ inscripcionId }: { inscripcionId: number }) {
  const { data, isLoading } = useApi(["elegibilidad", inscripcionId], () => inscripcionService.elegibilidad(inscripcionId));
  if (isLoading) return <PageLoader texto="Revisando requisitos..." />;
  if (!data) return <p className="text-sm text-ink-500">No se pudieron consultar los requisitos.</p>;
  return (
    <div className="space-y-3 text-sm">
      {data.bloqueantes.length === 0 && data.advertencias.length === 0 && (
        <p className="flex items-center gap-2 rounded-lg bg-emerald-50 p-3 text-emerald-800"><CheckCircle2 className="h-4 w-4" aria-hidden="true" />El equipo cumple todos los requisitos.</p>
      )}
      {data.bloqueantes.length > 0 && (
        <div className="rounded-lg border border-brand-200 bg-brand-50 p-3 text-brand-800">
          <p className="mb-1 flex items-center gap-2 font-semibold"><XCircle className="h-4 w-4" aria-hidden="true" />Impiden la aprobación</p>
          <ul className="list-disc space-y-1 pl-5">{data.bloqueantes.map((m) => <li key={m}>{m}</li>)}</ul>
        </div>
      )}
      {data.advertencias.length > 0 && (
        <div className="rounded-lg border border-amber-200 bg-amber-50 p-3 text-amber-900">
          <p className="mb-1 flex items-center gap-2 font-semibold"><AlertTriangle className="h-4 w-4" aria-hidden="true" />Advertencias</p>
          <ul className="list-disc space-y-1 pl-5">{data.advertencias.map((m) => <li key={m}>{m}</li>)}</ul>
        </div>
      )}
    </div>
  );
}

function ModalRevision({ inscripcion, onCerrar }: { inscripcion: Inscripcion; onCerrar: () => void }) {
  const [motivo, setMotivo] = useState("");
  const [error, setError] = useState("");
  const validar = useAccion(
    (a: { estado: "APROBADA" | "RECHAZADA"; observaciones?: string }) => inscripcionService.validar(inscripcion.id, a.estado, a.observaciones),
    {
      invalidar: ["inscripciones", "campeonatos", "campeonato", "elegibilidad"],
      exito: (_, a) => (a.estado === "APROBADA" ? "Inscripción aprobada. Se avisó al delegado." : "Inscripción rechazada. Se avisó al delegado."),
    },
  );
  const aprobar = () => validar.ejecutar({ estado: "APROBADA" }, { onSuccess: onCerrar, onError: (e) => setError(mensajeDeError(e)) });
  const rechazar = () => {
    if (!motivo.trim()) { setError("Indica el motivo del rechazo."); return; }
    validar.ejecutar({ estado: "RECHAZADA", observaciones: motivo.trim() }, { onSuccess: onCerrar, onError: (e) => setError(mensajeDeError(e)) });
  };
  const pendiente = inscripcion.estado === "PENDIENTE";
  return (
    <Modal open onClose={onCerrar} title={pendiente ? "Revisar inscripción" : "Requisitos del equipo"} size="lg"
      footer={<>
        <Button variant="secondary" onClick={onCerrar}>Cerrar</Button>
        {pendiente && <Button variant="danger" loading={validar.pendiente} onClick={rechazar}>Rechazar</Button>}
        {pendiente && <Button loading={validar.pendiente} onClick={aprobar}>Aprobar</Button>}
      </>}>
      <div className="space-y-4">
        <p className="text-sm text-ink-700"><b>{inscripcion.equipo_detalle.nombre}</b> ({inscripcion.equipo_detalle.facultad}) — {inscripcion.campeonato_nombre}</p>
        <RequisitosInscripcion inscripcionId={inscripcion.id} />
        {pendiente && (
          <FormField label="Motivo (obligatorio para rechazar)" error={error}>
            <Textarea rows={2} value={motivo} onChange={(e) => { setMotivo(e.target.value); setError(""); }} />
          </FormField>
        )}
      </div>
    </Modal>
  );
}

/** Bandeja de solicitudes: aprobar/rechazar con los motivos de elegibilidad a la vista (RF6, RF8). */
export function BandejaInscripciones({ campeonato }: { campeonato?: number }) {
  const campeonatos = useCampeonatos();
  const [estado, setEstado] = useState("PENDIENTE");
  const [filtroCamp, setFiltroCamp] = useState("");
  const [seleccionada, setSeleccionada] = useState<Inscripcion | null>(null);
  const idCamp = campeonato ? String(campeonato) : filtroCamp;
  const { data, isLoading } = useApi(["inscripciones", estado, idCamp], () =>
    inscripcionService.listar({ estado: estado || undefined, campeonato: idCamp || undefined, ordering: "-fecha_inscripcion" }));

  const columnas: Columna<Inscripcion>[] = [
    { clave: "e", titulo: "Equipo", render: (i) => <span><b className="text-ink-900">{i.equipo_detalle.nombre}</b><span className="block text-xs text-ink-500">{i.equipo_detalle.facultad}</span></span> },
    ...(campeonato ? [] : [{ clave: "c", titulo: "Campeonato", render: (i: Inscripcion) => i.campeonato_nombre }]),
    { clave: "f", titulo: "Solicitada", render: (i) => fechaCorta(i.fecha_inscripcion) },
    { clave: "s", titulo: "Estado", render: (i) => <Badge tono={TONO[i.estado]}>{i.estado.charAt(0) + i.estado.slice(1).toLowerCase()}</Badge> },
    { clave: "o", titulo: "Observaciones", render: (i) => <span className="text-xs text-ink-500">{i.observaciones || "—"}</span> },
    { clave: "a", titulo: "", alinear: "right", render: (i) => (
      <Button size="sm" variant={i.estado === "PENDIENTE" ? "primary" : "secondary"} onClick={() => setSeleccionada(i)}>{i.estado === "PENDIENTE" ? "Revisar" : "Ver requisitos"}</Button>
    ) },
  ];

  return (
    <>
      <div className="mb-4 flex flex-wrap gap-3">
        <Select aria-label="Estado" value={estado} onChange={(e) => setEstado(e.target.value)} className="w-44">
          <option value="">Todos los estados</option>
          <option value="PENDIENTE">Pendientes</option>
          <option value="APROBADA">Aprobadas</option>
          <option value="RECHAZADA">Rechazadas</option>
        </Select>
        {!campeonato && (
          <Select aria-label="Campeonato" value={filtroCamp} onChange={(e) => setFiltroCamp(e.target.value)} className="w-64">
            <option value="">Todos los campeonatos</option>
            {campeonatos.data?.results.map((c) => <option key={c.id} value={c.id}>{c.nombre}</option>)}
          </Select>
        )}
      </div>
      {isLoading ? <PageLoader /> : (
        <Table columnas={columnas} filas={data?.results ?? []} clave={(i) => i.id}
          vacio={{ titulo: estado === "PENDIENTE" ? "No hay solicitudes pendientes" : "No hay inscripciones", descripcion: "Las solicitudes de los delegados aparecerán aquí." }} />
      )}
      {seleccionada && <ModalRevision key={seleccionada.id} inscripcion={seleccionada} onCerrar={() => setSeleccionada(null)} />}
    </>
  );
}
