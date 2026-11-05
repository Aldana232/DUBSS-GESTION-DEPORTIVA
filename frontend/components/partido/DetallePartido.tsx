"use client";
import { CalendarDays, Handshake, MapPin, Trophy, Zap } from "lucide-react";
import { Badge, Card, CardBody, CardHeader, EstadoBadge } from "@/components/ui";
import { etiqueta, fechaLarga, hora } from "@/lib/utils";
import type { EquipoResumen, Incidencia, PartidoDetalle } from "@/types";

function Equipo({ equipo }: { equipo: EquipoResumen | null }) {
  const nombre = equipo?.nombre ?? "Por definir";
  return (
    <div className="flex min-w-0 flex-1 flex-col items-center text-center">
      <span className="mb-2 flex h-14 w-14 items-center justify-center rounded-full bg-ink-900 text-xl font-bold text-white ring-4 ring-brand-100">
        {nombre.charAt(0)}
      </span>
      <p className="w-full truncate text-sm font-bold text-ink-900 sm:text-base">{nombre}</p>
      <p className="w-full truncate text-xs text-ink-500">{equipo?.facultad ?? ""}</p>
    </div>
  );
}

/** Marcador del partido: equipos, resultado u hora, estado, fecha y cancha. */
export function MarcadorPartido({ partido: p }: { partido: PartidoDetalle }) {
  const r = p.resultado;
  return (
    <Card>
      <CardBody className="p-6 sm:p-8">
        <div className="flex items-center justify-between gap-3">
          <Equipo equipo={p.equipo_local_detalle} />
          <div className="shrink-0 text-center">
            {r ? (
              <p className="text-4xl font-extrabold tabular-nums text-ink-900 sm:text-5xl">{r.goles_local} – {r.goles_visitante}</p>
            ) : (
              <>
                <p className="text-2xl font-bold text-ink-300">vs</p>
                <p className="mt-1 text-lg font-bold text-brand-700">{hora(p.fecha_hora)}</p>
              </>
            )}
            {r?.penales_local != null && (
              <p className="mt-1 text-xs font-medium text-ink-500">Penales {r.penales_local} – {r.penales_visitante}</p>
            )}
            <div className="mt-2"><EstadoBadge estado={p.estado} /></div>
          </div>
          <Equipo equipo={p.equipo_visitante_detalle} />
        </div>
        <div className="mt-6 flex flex-wrap items-center justify-center gap-x-6 gap-y-1 border-t border-ink-100 pt-4 text-xs text-ink-500">
          <span className="inline-flex items-center gap-1.5"><CalendarDays className="h-3.5 w-3.5" aria-hidden="true" />{fechaLarga(p.fecha_hora)}</span>
          {p.cancha_detalle && <span className="inline-flex items-center gap-1.5"><MapPin className="h-3.5 w-3.5" aria-hidden="true" />{p.cancha_detalle.nombre}</span>}
        </div>
      </CardBody>
    </Card>
  );
}

export function ResultadoOficial({ partido: p }: { partido: PartidoDetalle }) {
  const r = p.resultado;
  if (!r) return null;
  return (
    <Card>
      <CardHeader title="Resultado oficial" />
      <CardBody className="flex flex-wrap items-center gap-3">
        {r.ganador ? (
          <Badge tono="success"><Trophy className="mr-1 h-3.5 w-3.5" aria-hidden="true" />Ganador: {r.ganador.nombre}</Badge>
        ) : (
          <Badge tono="neutral"><Handshake className="mr-1 h-3.5 w-3.5" aria-hidden="true" />Empate</Badge>
        )}
        {r.walkover && <Badge tono="warning">Resuelto por W.O.</Badge>}
        {r.observaciones && <p className="w-full text-sm text-ink-600">{r.observaciones}</p>}
      </CardBody>
    </Card>
  );
}

const TONO_TIPO: Record<string, "success" | "warning" | "danger" | "neutral"> = {
  GOL: "success", TARJETA_AMARILLA: "warning", TARJETA_ROJA: "danger",
};

export function ListaIncidencias({ incidencias, local }: { incidencias: Incidencia[]; local?: number | null }) {
  if (incidencias.length === 0) return null;
  return (
    <Card>
      <CardHeader title={<span className="inline-flex items-center gap-2"><Zap className="h-4 w-4 text-brand-600" aria-hidden="true" />Incidencias</span>} />
      <ul className="divide-y divide-ink-100">
        {incidencias.map((i) => (
          <li key={i.id} className="flex flex-wrap items-center gap-x-4 gap-y-1 px-5 py-3 text-sm">
            <span className="w-10 shrink-0 text-right font-semibold tabular-nums text-ink-400">{i.minuto != null ? `${i.minuto}'` : "—"}</span>
            <Badge tono={TONO_TIPO[i.tipo] ?? "neutral"}>{etiqueta(i.tipo)}</Badge>
            {i.jugador_nombre && (
              <span className="font-medium text-ink-800">
                {i.jugador_nombre}
                {local != null && <span className="ml-1.5 text-xs font-normal text-ink-400">{i.equipo_id === local ? "Local" : "Visitante"}</span>}
              </span>
            )}
            {i.descripcion && <span className="text-ink-500">{i.descripcion}</span>}
          </li>
        ))}
      </ul>
    </Card>
  );
}
