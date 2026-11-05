"use client";
import { useState } from "react";
import { ClipboardCheck, Send } from "lucide-react";
import {
  Badge, Button, Card, CardHeader, EmptyState, FormField, Modal, PageHeader, PageLoader, Select, Table, type Columna,
} from "@/components/ui";
import { RequisitosInscripcion } from "@/components/gestion/BandejaInscripciones";
import { useAccion, useApi, useCampeonatos, useMisEquipos } from "@/lib/hooks/queries";
import { inscripcionService } from "@/lib/api/services";
import { mensajeDeError } from "@/lib/api/errors";
import { fechaCorta } from "@/lib/utils";
import type { Campeonato, Inscripcion } from "@/types";

const TONO = { PENDIENTE: "warning", APROBADA: "success", RECHAZADA: "danger" } as const;

function ModalSolicitar({ campeonato, onCerrar }: { campeonato: Campeonato; onCerrar: () => void }) {
  const equipos = useMisEquipos();
  const [equipo, setEquipo] = useState("");
  const [error, setError] = useState("");
  const solicitar = useAccion((e: number) => inscripcionService.crear({ campeonato: campeonato.id, equipo: e }), {
    invalidar: ["inscripciones", "campeonatos"], exito: "Solicitud enviada. El organizador la revisará.",
  });
  const enviar = () => {
    if (!equipo) { setError("Selecciona el equipo que quieres inscribir."); return; }
    solicitar.ejecutar(Number(equipo), { onSuccess: onCerrar, onError: (e) => setError(mensajeDeError(e)) });
  };
  return (
    <Modal open onClose={onCerrar} title="Solicitar inscripción" size="sm"
      footer={<><Button variant="secondary" onClick={onCerrar}>Cancelar</Button><Button loading={solicitar.pendiente} icon={<Send className="h-4 w-4" />} onClick={enviar}>Enviar solicitud</Button></>}>
      <p className="mb-3 text-sm text-ink-600">Campeonato: <b>{campeonato.nombre}</b>. Tu plantel debe tener entre {campeonato.min_jugadores} y {campeonato.max_jugadores} jugadores.</p>
      <FormField label="Equipo" error={error} required>
        <Select value={equipo} onChange={(e) => { setEquipo(e.target.value); setError(""); }}>
          <option value="">Selecciona...</option>
          {equipos.data?.map((e) => <option key={e.id} value={e.id}>{e.nombre} ({e.cantidad_jugadores} jugadores)</option>)}
        </Select>
      </FormField>
    </Modal>
  );
}

export default function DelegadoInscripciones() {
  const campeonatos = useCampeonatos();
  const mias = useApi(["inscripciones", "mias"], () => inscripcionService.listar({ ordering: "-fecha_inscripcion" }));
  const [solicitando, setSolicitando] = useState<Campeonato | null>(null);
  const [revisando, setRevisando] = useState<Inscripcion | null>(null);
  const abiertos = campeonatos.data?.results.filter((c) => c.estado === "INSCRIPCIONES") ?? [];

  const columnas: Columna<Inscripcion>[] = [
    { clave: "e", titulo: "Equipo", render: (i) => <b className="text-ink-900">{i.equipo_detalle.nombre}</b> },
    { clave: "c", titulo: "Campeonato", render: (i) => i.campeonato_nombre },
    { clave: "f", titulo: "Solicitada", render: (i) => fechaCorta(i.fecha_inscripcion) },
    { clave: "s", titulo: "Estado", render: (i) => <Badge tono={TONO[i.estado]}>{i.estado.charAt(0) + i.estado.slice(1).toLowerCase()}</Badge> },
    { clave: "o", titulo: "Observaciones", render: (i) => <span className="text-xs text-ink-500">{i.observaciones || "—"}</span> },
    { clave: "a", titulo: "", alinear: "right", render: (i) => i.estado === "PENDIENTE" ? <Button size="sm" variant="secondary" onClick={() => setRevisando(i)}>Ver requisitos</Button> : null },
  ];

  return (
    <>
      <PageHeader title="Inscripciones" description="Solicita la inscripción de tus equipos y revisa el estado de cada solicitud." />
      <Card className="mb-6">
        <CardHeader title="Campeonatos con inscripciones abiertas" />
        {campeonatos.isLoading ? <PageLoader /> : abiertos.length === 0 ? (
          <EmptyState icon={ClipboardCheck} title="No hay inscripciones abiertas" description="Cuando se abra un campeonato podrás solicitar tu inscripción aquí." className="m-5" />
        ) : (
          <ul className="divide-y divide-ink-100">
            {abiertos.map((c) => (
              <li key={c.id} className="flex flex-wrap items-center justify-between gap-3 px-5 py-3">
                <span className="min-w-0"><b className="block truncate text-sm text-ink-900">{c.nombre}</b><span className="text-xs text-ink-500">{c.deporte_detalle?.nombre} — {c.categoria_detalle?.nombre} · {c.total_equipos}/{c.max_equipos} equipos</span></span>
                <Button size="sm" onClick={() => setSolicitando(c)}>Solicitar inscripción</Button>
              </li>
            ))}
          </ul>
        )}
      </Card>
      <h2 className="mb-3 text-base font-semibold text-ink-900">Mis solicitudes</h2>
      {mias.isLoading ? <PageLoader /> : <Table columnas={columnas} filas={mias.data?.results ?? []} clave={(i) => i.id} vacio={{ titulo: "Aún no solicitaste ninguna inscripción" }} />}

      {solicitando && <ModalSolicitar campeonato={solicitando} onCerrar={() => setSolicitando(null)} />}
      {revisando && (
        <Modal open onClose={() => setRevisando(null)} title="Requisitos de tu equipo" size="lg" footer={<Button variant="secondary" onClick={() => setRevisando(null)}>Cerrar</Button>}>
          <p className="mb-3 text-sm text-ink-700"><b>{revisando.equipo_detalle.nombre}</b> — {revisando.campeonato_nombre}</p>
          <RequisitosInscripcion inscripcionId={revisando.id} />
        </Modal>
      )}
    </>
  );
}
