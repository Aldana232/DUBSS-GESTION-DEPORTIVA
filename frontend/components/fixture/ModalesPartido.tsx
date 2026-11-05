"use client";
import { useState } from "react";
import { AlertTriangle } from "lucide-react";
import axios from "axios";
import { Button, FormField, Input, Modal, Select, Textarea, useToast } from "@/components/ui";
import { RECURSOS_PARTIDO, useAccion, useApi } from "@/lib/hooks/queries";
import { canchaService, fixtureService, jugadorService } from "@/lib/api/services";
import { mensajeDeError } from "@/lib/api/errors";
import { aInputFechaHora, deInputFechaHora, etiqueta } from "@/lib/utils";
import type { PartidoDetalle } from "@/types";

/* ── Eliminar resultado (con motivo) ─────────────────────────────────────────────────────── */
export function ModalEliminarResultado({ partido, abierto, onCerrar }: { partido: PartidoDetalle; abierto: boolean; onCerrar: () => void }) {
  const [motivo, setMotivo] = useState("");
  const [error, setError] = useState("");
  const eliminar = useAccion((m: string) => fixtureService.eliminarResultado(partido.id, m), {
    invalidar: RECURSOS_PARTIDO, exito: "Resultado eliminado. El partido vuelve a estar programado.",
  });
  const confirmar = () => {
    if (!motivo.trim()) { setError("Indica el motivo de la eliminación."); return; }
    eliminar.ejecutar(motivo.trim(), { onSuccess: () => { setMotivo(""); onCerrar(); }, onError: (e) => setError(mensajeDeError(e)) });
  };
  return (
    <Modal open={abierto} onClose={onCerrar} title="Eliminar resultado" size="sm"
      footer={<><Button variant="secondary" onClick={onCerrar}>Cancelar</Button><Button variant="danger" loading={eliminar.pendiente} onClick={confirmar}>Eliminar resultado</Button></>}>
      <p className="mb-3 text-sm text-ink-600">El partido volverá a «Programado» y la tabla de posiciones se recalculará.</p>
      <FormField label="Motivo" error={error} required>
        <Textarea rows={2} value={motivo} onChange={(e) => { setMotivo(e.target.value); setError(""); }} />
      </FormField>
    </Modal>
  );
}

/* ── Registrar incidencia ───────────────────────────────────────────────────────────────── */
const TIPOS = ["GOL", "TARJETA_AMARILLA", "TARJETA_ROJA", "LESION", "SUSTITUCION", "OTRO"];
const CON_JUGADOR = ["GOL", "TARJETA_AMARILLA", "TARJETA_ROJA", "LESION"];

export function ModalIncidencia({ partido, abierto, onCerrar }: { partido: PartidoDetalle; abierto: boolean; onCerrar: () => void }) {
  const toast = useToast();
  const [tipo, setTipo] = useState("GOL");
  const [equipo, setEquipo] = useState(String(partido.equipo_local ?? ""));
  const [jugador, setJugador] = useState("");
  const [minuto, setMinuto] = useState("");
  const [descripcion, setDescripcion] = useState("");
  const [errores, setErrores] = useState<Record<string, string>>({});

  const plantel = useApi(["jugadores", equipo], () => jugadorService.listar({ equipo }), !!equipo && abierto);
  const registrar = useAccion(
    (d: Parameters<typeof fixtureService.registrarIncidencia>[1]) => fixtureService.registrarIncidencia(partido.id, d),
    { invalidar: [...RECURSOS_PARTIDO, "jugadores"] },
  );

  const requiereJugador = CON_JUGADOR.includes(tipo);
  const enviar = () => {
    const nuevos: Record<string, string> = {};
    if (requiereJugador && !jugador) nuevos.jugador = "Selecciona el jugador.";
    if (minuto && (Number(minuto) < 0 || Number(minuto) > 150)) nuevos.minuto = "Minuto entre 0 y 150.";
    setErrores(nuevos);
    if (Object.keys(nuevos).length) return;
    registrar.ejecutar(
      { tipo, jugador: requiereJugador || jugador ? Number(jugador) || null : null, minuto: minuto ? Number(minuto) : null, descripcion },
      {
        onSuccess: (r) => {
          toast.success(r.partidos_sancion > 0 ? `Incidencia registrada. El jugador queda sancionado ${r.partidos_sancion} partido(s).` : "Incidencia registrada.");
          setJugador(""); setMinuto(""); setDescripcion("");
          onCerrar();
        },
        onError: (e) => {
          if (axios.isAxiosError(e) && e.response?.status === 400 && typeof e.response.data === "object") {
            const d = e.response.data as Record<string, unknown>;
            const texto = (v: unknown) => (Array.isArray(v) ? v.join(" ") : String(v));
            setErrores(Object.fromEntries(Object.entries(d).map(([k, v]) => [k === "non_field_errors" ? "general" : k, texto(v)])));
          } else toast.error(mensajeDeError(e));
        },
      },
    );
  };

  const local = partido.equipo_local_detalle?.nombre ?? "Local";
  const visitante = partido.equipo_visitante_detalle?.nombre ?? "Visitante";
  return (
    <Modal open={abierto} onClose={onCerrar} title="Registrar incidencia"
      footer={<><Button variant="secondary" onClick={onCerrar}>Cancelar</Button><Button loading={registrar.pendiente} onClick={enviar}>Registrar</Button></>}>
      <div className="grid gap-4 sm:grid-cols-2">
        {errores.general && <p role="alert" className="text-sm text-brand-700 sm:col-span-2">{errores.general}</p>}
        <FormField label="Tipo" required>
          <Select value={tipo} onChange={(e) => setTipo(e.target.value)}>{TIPOS.map((t) => <option key={t} value={t}>{etiqueta(t)}</option>)}</Select>
        </FormField>
        <FormField label="Minuto" error={errores.minuto}>
          <Input type="number" min={0} max={150} value={minuto} onChange={(e) => setMinuto(e.target.value)} />
        </FormField>
        <FormField label="Equipo" required>
          <Select value={equipo} onChange={(e) => { setEquipo(e.target.value); setJugador(""); }}>
            <option value={partido.equipo_local ?? ""}>{local} (local)</option>
            <option value={partido.equipo_visitante ?? ""}>{visitante} (visitante)</option>
          </Select>
        </FormField>
        <FormField label="Jugador" error={errores.jugador} required={requiereJugador}>
          <Select value={jugador} onChange={(e) => setJugador(e.target.value)}>
            <option value="">{requiereJugador ? "Selecciona..." : "Ninguno"}</option>
            {plantel.data?.results.map((j) => (
              <option key={j.id} value={j.id} disabled={j.partidos_sancion_restantes > 0}>
                {j.numero_camiseta != null ? `#${j.numero_camiseta} ` : ""}{j.nombre} {j.apellido}{j.partidos_sancion_restantes > 0 ? " (sancionado)" : ""}
              </option>
            ))}
          </Select>
        </FormField>
        <FormField label="Descripción" className="sm:col-span-2" error={errores.descripcion}>
          <Textarea rows={2} value={descripcion} onChange={(e) => setDescripcion(e.target.value)} />
        </FormField>
      </div>
    </Modal>
  );
}

/* ── Reprogramar (detecta conflictos: 409) ──────────────────────────────────────────────── */
export function ModalReprogramar({ partidoId, abierto, onCerrar }: { partidoId: number; abierto: boolean; onCerrar: () => void }) {
  const detalle = useApi(["partido", partidoId], () => fixtureService.partido(partidoId), abierto);
  const p = detalle.data;
  const canchas = useApi(["canchas"], () => canchaService.listar({ activa: true }), abierto);
  const [fecha, setFecha] = useState<string | null>(null);
  const [cancha, setCancha] = useState<string | null>(null);
  const [conflictos, setConflictos] = useState<string[]>([]);
  const [error, setError] = useState("");

  const guardar = useAccion(
    (d: { fecha_hora: string; cancha: number | null }) => fixtureService.reprogramar(partidoId, d),
    { invalidar: RECURSOS_PARTIDO, exito: "Partido reprogramado. Se avisó a los delegados por correo." },
  );
  const valorFecha = fecha ?? aInputFechaHora(p?.fecha_hora);
  const valorCancha = cancha ?? String(p?.cancha ?? "");

  const enviar = () => {
    setConflictos([]); setError("");
    const iso = deInputFechaHora(valorFecha);
    if (!iso) { setError("Indica la fecha y hora."); return; }
    guardar.ejecutar({ fecha_hora: iso, cancha: valorCancha ? Number(valorCancha) : null }, {
      onSuccess: () => { setFecha(null); setCancha(null); onCerrar(); },
      onError: (e) => {
        if (axios.isAxiosError(e) && e.response?.status === 409) {
          const lista = (e.response.data as { conflictos?: string[] }).conflictos;
          setConflictos(lista?.length ? lista : [mensajeDeError(e)]);
        } else setError(mensajeDeError(e));
      },
    });
  };

  return (
    <Modal open={abierto} onClose={onCerrar} title="Reprogramar partido"
      footer={<><Button variant="secondary" onClick={onCerrar}>Cancelar</Button><Button loading={guardar.pendiente} onClick={enviar}>Reprogramar</Button></>}>
      <div className="space-y-4">
        {p && <p className="text-sm text-ink-600">{p.equipo_local_detalle?.nombre ?? "Por definir"} vs {p.equipo_visitante_detalle?.nombre ?? "Por definir"}</p>}
        <FormField label="Fecha y hora" required error={error}>
          <Input type="datetime-local" value={valorFecha} onChange={(e) => setFecha(e.target.value)} />
        </FormField>
        <FormField label="Cancha">
          <Select value={valorCancha} onChange={(e) => setCancha(e.target.value)}>
            <option value="">Sin cancha</option>
            {canchas.data?.results.map((c) => <option key={c.id} value={c.id}>{c.instalacion_nombre} — {c.nombre} ({c.deporte_nombre})</option>)}
          </Select>
        </FormField>
        {conflictos.length > 0 && (
          <div role="alert" className="rounded-lg border border-brand-200 bg-brand-50 p-3 text-sm text-brand-800">
            <p className="mb-1 flex items-center gap-2 font-semibold"><AlertTriangle className="h-4 w-4" aria-hidden="true" />No se puede programar ahí</p>
            <ul className="list-disc space-y-1 pl-5">{conflictos.map((c) => <li key={c}>{c}</li>)}</ul>
          </div>
        )}
      </div>
    </Modal>
  );
}
