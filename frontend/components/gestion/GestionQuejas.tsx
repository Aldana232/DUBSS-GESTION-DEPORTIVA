"use client";
import { useState } from "react";
import Link from "next/link";
import { Badge, Button, FormField, Modal, PageLoader, Select, Table, Textarea, type BadgeTono, type Columna } from "@/components/ui";
import { useAccion, useApi } from "@/lib/hooks/queries";
import { quejaService } from "@/lib/api/services";
import { mensajeDeError } from "@/lib/api/errors";
import { etiqueta, fechaCorta } from "@/lib/utils";
import type { Queja } from "@/types";

export const TONO_QUEJA: Record<string, BadgeTono> = { ABIERTA: "warning", EN_REVISION: "info", RESUELTA: "success", RECHAZADA: "danger" };

function ModalResolver({ queja, onCerrar }: { queja: Queja; onCerrar: () => void }) {
  const [estado, setEstado] = useState<string>(queja.estado === "ABIERTA" ? "EN_REVISION" : queja.estado);
  const [resolucion, setResolucion] = useState(queja.resolucion ?? "");
  const [error, setError] = useState("");
  const resolver = useAccion((a: { estado: string; resolucion: string }) => quejaService.resolver(queja.id, a.estado, a.resolucion), {
    invalidar: ["quejas"], exito: "Queja actualizada.",
  });
  const cerrada = ["RESUELTA", "RECHAZADA"].includes(estado);
  const guardar = () => {
    if (cerrada && !resolucion.trim()) { setError("La resolución es obligatoria para cerrar una queja."); return; }
    resolver.ejecutar({ estado, resolucion: resolucion.trim() }, { onSuccess: onCerrar, onError: (e) => setError(mensajeDeError(e)) });
  };
  const d = queja.encuentro_detalle;
  return (
    <Modal open onClose={onCerrar} title={`${etiqueta(queja.tipo)} #${queja.id}`} size="lg"
      footer={<><Button variant="secondary" onClick={onCerrar}>Cancelar</Button><Button loading={resolver.pendiente} onClick={guardar}>Guardar</Button></>}>
      <div className="space-y-4 text-sm">
        <p className="text-ink-600">Presentada por <b>{queja.delegado_nombre ?? "—"}</b> el {fechaCorta(queja.fecha_hora)} sobre{" "}
          <Link href={`/gestion/partidos/${d.id}`} className="font-medium text-brand-700 hover:underline">{d.local} vs {d.visitante}</Link> ({d.campeonato}).</p>
        <p className="whitespace-pre-line rounded-lg bg-ink-50 p-3 text-ink-800">{queja.descripcion}</p>
        <FormField label="Estado">
          <Select value={estado} onChange={(e) => { setEstado(e.target.value); setError(""); }}>
            <option value="EN_REVISION">En revisión</option>
            <option value="RESUELTA">Resuelta</option>
            <option value="RECHAZADA">Rechazada</option>
          </Select>
        </FormField>
        <FormField label="Respuesta / resolución" error={error} required={cerrada}>
          <Textarea rows={4} value={resolucion} onChange={(e) => { setResolucion(e.target.value); setError(""); }} />
        </FormField>
      </div>
    </Modal>
  );
}

/** Bandeja de quejas y apelaciones (RF21): filtrar, responder y cambiar de estado. */
export function GestionQuejas() {
  const [estado, setEstado] = useState("");
  const [tipo, setTipo] = useState("");
  const [abierta, setAbierta] = useState<Queja | null>(null);
  const { data, isLoading } = useApi(["quejas", estado, tipo], () => quejaService.listar({ estado: estado || undefined, tipo: tipo || undefined }));

  const columnas: Columna<Queja>[] = [
    { clave: "t", titulo: "Tipo", render: (q) => etiqueta(q.tipo) },
    { clave: "p", titulo: "Partido", render: (q) => <span><b className="text-ink-900">{q.encuentro_detalle.local} vs {q.encuentro_detalle.visitante}</b><span className="block text-xs text-ink-500">{q.encuentro_detalle.campeonato}</span></span> },
    { clave: "d", titulo: "Delegado", render: (q) => q.delegado_nombre ?? "—" },
    { clave: "f", titulo: "Fecha", render: (q) => fechaCorta(q.fecha_hora) },
    { clave: "e", titulo: "Estado", render: (q) => <Badge tono={TONO_QUEJA[q.estado]}>{etiqueta(q.estado)}</Badge> },
    { clave: "a", titulo: "", alinear: "right", render: (q) => <Button size="sm" variant={q.estado === "ABIERTA" ? "primary" : "secondary"} onClick={() => setAbierta(q)}>{["RESUELTA", "RECHAZADA"].includes(q.estado) ? "Ver" : "Responder"}</Button> },
  ];

  return (
    <>
      <div className="mb-4 flex flex-wrap gap-3">
        <Select aria-label="Estado" value={estado} onChange={(e) => setEstado(e.target.value)} className="w-48">
          <option value="">Todos los estados</option><option value="ABIERTA">Abiertas</option><option value="EN_REVISION">En revisión</option>
          <option value="RESUELTA">Resueltas</option><option value="RECHAZADA">Rechazadas</option>
        </Select>
        <Select aria-label="Tipo" value={tipo} onChange={(e) => setTipo(e.target.value)} className="w-44">
          <option value="">Quejas y apelaciones</option><option value="QUEJA">Quejas</option><option value="APELACION">Apelaciones</option>
        </Select>
      </div>
      {isLoading ? <PageLoader /> : <Table columnas={columnas} filas={data?.results ?? []} clave={(q) => q.id} vacio={{ titulo: "No hay quejas ni apelaciones", descripcion: "Las presentadas por los delegados aparecerán aquí." }} />}
      {abierta && <ModalResolver key={abierta.id} queja={abierta} onCerrar={() => setAbierta(null)} />}
    </>
  );
}
