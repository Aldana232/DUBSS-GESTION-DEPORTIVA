"use client";
import { useState } from "react";
import { CheckCircle2, CircleAlert, CloudUpload, RefreshCw, Trash2, Users } from "lucide-react";
import { Button } from "@/components/ui";
import { cn } from "@/lib/utils";
import { descartar, reintentar, sincronizar, useEstadoSync } from "@/lib/offline/sincronizador";
import type { Operacion } from "@/lib/offline/db";
import type { PaquetePlanilla } from "@/types";

function Fila({ op, partido }: { op: Operacion; partido: string }) {
  const [confirmando, setConfirmando] = useState(false);
  const pendiente = op.estado === "PENDIENTE";
  return (
    <li className={cn("rounded-2xl bg-white p-3.5 shadow-card ring-1", pendiente ? "ring-ink-100" : "ring-rose-200")}>
      <div className="flex items-start gap-3">
        <span className={cn("mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-full", pendiente ? "bg-amber-100 text-amber-700" : "bg-rose-100 text-rose-700")}>
          {pendiente ? <CloudUpload className="h-4 w-4" aria-hidden="true" /> : <CircleAlert className="h-4 w-4" aria-hidden="true" />}
        </span>
        <div className="min-w-0 flex-1">
          <p className="text-sm font-semibold text-ink-900">{op.resumen}</p>
          <p className="truncate text-xs text-ink-500">{partido}</p>
          {!pendiente && <p className="mt-1 text-xs text-rose-800">{op.estado === "CONFLICTO" ? "Conflicto: " : "Rechazada: "}{op.detalle}</p>}
          {pendiente && op.intentos > 0 && <p className="mt-1 text-xs text-ink-500">Intentos: {op.intentos}. Se reintentará sola.</p>}
        </div>
      </div>
      {!pendiente && (
        <div className="mt-3 flex justify-end gap-2">
          {confirmando ? (
            <>
              <span className="mr-auto self-center text-xs text-ink-600">Se perderá esta acción. ¿Seguro?</span>
              <Button size="sm" variant="secondary" onClick={() => setConfirmando(false)}>No</Button>
              <Button size="sm" variant="danger" onClick={() => descartar(op.id!)}>Sí, descartar</Button>
            </>
          ) : (
            <>
              {op.estado === "ERROR" && <Button size="sm" variant="secondary" icon={<RefreshCw className="h-4 w-4" />} onClick={() => reintentar(op.id!)}>Reintentar</Button>}
              <Button size="sm" variant="danger" icon={<Trash2 className="h-4 w-4" />} onClick={() => setConfirmando(true)}>Descartar</Button>
            </>
          )}
        </div>
      )}
    </li>
  );
}

export function Pendientes({ ops, paquete }: { ops: Operacion[]; paquete: PaquetePlanilla | null }) {
  const s = useEstadoSync();
  const nombre = (id: number) => { const p = paquete?.partidos.find((x) => x.id === id); return p ? `${p.local.nombre} vs ${p.visitante.nombre}` : `Partido ${id}`; };
  const porEnviar = ops.filter((o) => o.estado === "PENDIENTE");
  const porRevisar = ops.filter((o) => o.estado !== "PENDIENTE");

  return (
    <div className="space-y-5">
      <div className="rounded-2xl bg-white p-4 shadow-card ring-1 ring-ink-100">
        <div className="flex items-center justify-between gap-3">
          <div className="min-w-0">
            <p className="text-sm font-bold text-ink-900">{s.enLinea ? "Conectado" : "Sin conexión"}</p>
            <p className="text-xs text-ink-500">{s.ultimaSync ? `Última sincronización: ${new Date(s.ultimaSync).toLocaleTimeString("es-BO", { hour: "2-digit", minute: "2-digit" })}` : "Aún no se sincronizó nada en esta sesión."}</p>
          </div>
          <Button size="sm" loading={s.sincronizando} disabled={!s.enLinea || porEnviar.length === 0} icon={<RefreshCw className="h-4 w-4" />} onClick={() => void sincronizar()}>Sincronizar</Button>
        </div>
        {s.sesionVencida && (
          <p role="alert" className="mt-3 rounded-xl bg-rose-50 p-3 text-xs text-rose-900">
            Tu sesión venció. No se perdió nada: <a className="font-bold underline" href="/login?redirect=/planilla">inicia sesión</a> y se enviará todo.
          </p>
        )}
      </div>

      {s.deOtrasCuentas > 0 && (
        <p className="flex gap-2 rounded-2xl bg-sky-50 p-3.5 text-xs text-sky-900"><Users className="mt-0.5 h-4 w-4 shrink-0" aria-hidden="true" />
          Hay {s.deOtrasCuentas} acción(es) de otra cuenta que usó este celular. Solo esa persona puede enviarlas, iniciando sesión con su cuenta.</p>
      )}

      {ops.length === 0 && (
        <div className="rounded-2xl bg-white p-8 text-center shadow-card ring-1 ring-ink-100">
          <CheckCircle2 className="mx-auto mb-3 h-9 w-9 text-emerald-500" aria-hidden="true" />
          <p className="text-sm font-semibold text-ink-900">Todo sincronizado</p>
          <p className="mt-1 text-xs text-ink-500">No hay acciones esperando en este celular.</p>
        </div>
      )}

      {porRevisar.length > 0 && (
        <section aria-label="Por revisar">
          <h2 className="mb-2 px-1 text-xs font-bold uppercase tracking-wider text-rose-700">Por revisar ({porRevisar.length})</h2>
          <ul className="space-y-2.5">{porRevisar.map((o) => <Fila key={o.id} op={o} partido={nombre(o.partidoId)} />)}</ul>
        </section>
      )}
      {porEnviar.length > 0 && (
        <section aria-label="Por enviar">
          <h2 className="mb-2 px-1 text-xs font-bold uppercase tracking-wider text-ink-500">Por enviar ({porEnviar.length})</h2>
          <ul className="space-y-2.5">{porEnviar.map((o) => <Fila key={o.id} op={o} partido={nombre(o.partidoId)} />)}</ul>
        </section>
      )}
    </div>
  );
}
