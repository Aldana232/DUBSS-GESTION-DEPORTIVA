"use client";
import { useState } from "react";
import { MessageSquareWarning, Plus } from "lucide-react";
import { Badge, Button, EmptyState, FormField, Modal, PageHeader, PageLoader, Select, Table, Textarea, type Columna } from "@/components/ui";
import { TONO_QUEJA } from "@/components/gestion/GestionQuejas";
import { useAccion, useApi, useMisEquipos, usePartidosDeEquipos } from "@/lib/hooks/queries";
import { quejaService } from "@/lib/api/services";
import { mensajeDeError } from "@/lib/api/errors";
import { etiqueta, fechaCorta, fechaDia } from "@/lib/utils";
import type { Queja } from "@/types";

function ModalQueja({ onCerrar }: { onCerrar: () => void }) {
  const equipos = useMisEquipos();
  const { partidos } = usePartidosDeEquipos((equipos.data ?? []).map((e) => e.id));
  const [tipo, setTipo] = useState("QUEJA");
  const [partido, setPartido] = useState("");
  const [descripcion, setDescripcion] = useState("");
  const [errores, setErrores] = useState<Record<string, string>>({});
  const crear = useAccion(
    (d: { tipo: string; descripcion: string; encuentro: number }) => quejaService.crear(d),
    { invalidar: ["quejas"], exito: "Tu solicitud fue enviada al organizador." },
  );
  const enviar = () => {
    const nuevos: Record<string, string> = {};
    if (!partido) nuevos.partido = "Selecciona el partido.";
    if (descripcion.trim().length < 10) nuevos.descripcion = "Describe el motivo (mínimo 10 caracteres).";
    setErrores(nuevos);
    if (Object.keys(nuevos).length) return;
    crear.ejecutar({ tipo, descripcion: descripcion.trim(), encuentro: Number(partido) }, {
      onSuccess: onCerrar,
      onError: (e) => setErrores({ general: mensajeDeError(e, "No se pudo enviar la solicitud.") }),
    });
  };
  return (
    <Modal open onClose={onCerrar} title="Nueva queja o apelación" size="lg"
      footer={<><Button variant="secondary" onClick={onCerrar}>Cancelar</Button><Button loading={crear.pendiente} onClick={enviar}>Enviar</Button></>}>
      <div className="space-y-4">
        {errores.general && <p role="alert" className="rounded-lg border border-brand-200 bg-brand-50 p-3 text-sm text-brand-800">{errores.general}</p>}
        <FormField label="Tipo" required>
          <Select value={tipo} onChange={(e) => setTipo(e.target.value)}><option value="QUEJA">Queja</option><option value="APELACION">Apelación</option></Select>
        </FormField>
        <FormField label="Partido" error={errores.partido} required>
          <Select value={partido} onChange={(e) => setPartido(e.target.value)}>
            <option value="">Selecciona...</option>
            {partidos.map((p) => <option key={p.id} value={p.id}>{fechaDia(p.fecha_hora)} — {p.local} vs {p.visitante}</option>)}
          </Select>
        </FormField>
        <FormField label="Descripción" error={errores.descripcion} required hint="Cuenta qué ocurrió y qué solicitas.">
          <Textarea rows={5} value={descripcion} onChange={(e) => setDescripcion(e.target.value)} />
        </FormField>
      </div>
    </Modal>
  );
}

export default function QuejasDelegado() {
  const [nueva, setNueva] = useState(false);
  const [ver, setVer] = useState<Queja | null>(null);
  const { data, isLoading } = useApi(["quejas", "mias"], () => quejaService.mias());

  const columnas: Columna<Queja>[] = [
    { clave: "t", titulo: "Tipo", render: (q) => etiqueta(q.tipo) },
    { clave: "p", titulo: "Partido", render: (q) => `${q.encuentro_detalle.local} vs ${q.encuentro_detalle.visitante}` },
    { clave: "f", titulo: "Fecha", render: (q) => fechaCorta(q.fecha_hora) },
    { clave: "e", titulo: "Estado", render: (q) => <Badge tono={TONO_QUEJA[q.estado]}>{etiqueta(q.estado)}</Badge> },
    { clave: "a", titulo: "", alinear: "right", render: (q) => <Button size="sm" variant="secondary" onClick={() => setVer(q)}>Ver</Button> },
  ];

  return (
    <>
      <PageHeader title="Quejas y apelaciones" description="Presenta una queja o apelación sobre un partido y sigue su respuesta."
        actions={<Button icon={<Plus className="h-4 w-4" />} onClick={() => setNueva(true)}>Nueva solicitud</Button>} />
      {isLoading ? <PageLoader /> : (data?.results.length ?? 0) === 0 ? (
        <EmptyState icon={MessageSquareWarning} title="No presentaste solicitudes" description="Si tienes un reclamo sobre un partido, créalo aquí." action={<Button icon={<Plus className="h-4 w-4" />} onClick={() => setNueva(true)}>Nueva solicitud</Button>} />
      ) : <Table columnas={columnas} filas={data?.results ?? []} clave={(q) => q.id} />}
      {nueva && <ModalQueja onCerrar={() => setNueva(false)} />}
      {ver && (
        <Modal open onClose={() => setVer(null)} title={`${etiqueta(ver.tipo)} #${ver.id}`} footer={<Button variant="secondary" onClick={() => setVer(null)}>Cerrar</Button>}>
          <div className="space-y-3 text-sm">
            <p className="text-ink-500">{ver.encuentro_detalle.local} vs {ver.encuentro_detalle.visitante} · {ver.encuentro_detalle.campeonato}</p>
            <p className="whitespace-pre-line rounded-lg bg-ink-50 p-3 text-ink-800">{ver.descripcion}</p>
            <p><Badge tono={TONO_QUEJA[ver.estado]}>{etiqueta(ver.estado)}</Badge></p>
            {ver.resolucion ? <div><p className="mb-1 text-xs font-semibold uppercase text-ink-500">Respuesta del organizador</p><p className="whitespace-pre-line text-ink-800">{ver.resolucion}</p></div> : <p className="text-ink-500">Aún no hay respuesta.</p>}
          </div>
        </Modal>
      )}
    </>
  );
}
