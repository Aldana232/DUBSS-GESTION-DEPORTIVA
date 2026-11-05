"use client";
import { useEffect, useMemo, useState } from "react";
import { ArrowLeft, CheckCircle2, CircleAlert, Clock, Flag, Goal, Pause, Play, RotateCcw, Siren, Undo2 } from "lucide-react";
import { HojaAcciones } from "@/components/planilla/HojaAcciones";
import { HojaFinalizar, HojaOtro } from "@/components/planilla/HojasPartido";
import { Button } from "@/components/ui";
import { cn } from "@/lib/utils";
import type { Operacion } from "@/lib/offline/db";
import { useReloj } from "@/lib/offline/hooks";
import { ETIQUETA_TIPO, eventosDe, formatoReloj, marcadorDe, minutoSugerido, nombreCorto, operacionResultado, resumenDe, situacionDe, type EventoVista } from "@/lib/offline/planilla";
import { deshacer, encolar, MARGEN_PARA_DESHACER_MS, sincronizar } from "@/lib/offline/sincronizador";
import type { JugadorPlanilla, PartidoPlanilla, TipoIncidencia } from "@/types";

const ESTADO_EVENTO: Record<EventoVista["estado"], { texto: string; clase: string }> = {
  ENVIADO: { texto: "Enviado", clase: "bg-emerald-50 text-emerald-700" },
  PENDIENTE: { texto: "Por enviar", clase: "bg-amber-50 text-amber-800" },
  ERROR: { texto: "Rechazado", clase: "bg-rose-50 text-rose-700" },
  CONFLICTO: { texto: "Conflicto", clase: "bg-rose-50 text-rose-700" },
};

function Icono({ tipo }: { tipo: EventoVista["tipo"] }) {
  if (tipo === "GOL") return <span className="flex h-8 w-8 items-center justify-center rounded-full bg-brand-600 text-white"><Goal className="h-4 w-4" aria-hidden="true" /></span>;
  if (tipo === "TARJETA_AMARILLA") return <span className="flex h-8 w-8 items-center justify-center rounded-full bg-amber-100"><span className="h-4 w-3 rounded-sm bg-amber-400" aria-hidden="true" /></span>;
  if (tipo === "TARJETA_ROJA") return <span className="flex h-8 w-8 items-center justify-center rounded-full bg-rose-100"><span className="h-4 w-3 rounded-sm bg-rose-600" aria-hidden="true" /></span>;
  return <span className="flex h-8 w-8 items-center justify-center rounded-full bg-ink-100 text-ink-600"><Siren className="h-4 w-4" aria-hidden="true" /></span>;
}

function Insignias({ jugadorId, eventos }: { jugadorId: number; eventos: EventoVista[] }) {
  const propios = eventos.filter((e) => e.jugadorId === jugadorId && e.estado !== "ERROR" && e.estado !== "CONFLICTO");
  const goles = propios.filter((e) => e.tipo === "GOL").length;
  const amarillas = propios.filter((e) => e.tipo === "TARJETA_AMARILLA").length;
  const roja = propios.some((e) => e.tipo === "TARJETA_ROJA");
  if (!goles && !amarillas && !roja) return null;
  return (
    <span className="flex items-center gap-1" aria-label={`${goles} goles, ${amarillas} amarillas${roja ? ", expulsado" : ""}`}>
      {goles > 0 && <span className="inline-flex items-center gap-0.5 rounded-full bg-brand-600 px-1.5 py-0.5 text-[11px] font-bold text-white"><Goal className="h-3 w-3" aria-hidden="true" />{goles}</span>}
      {amarillas > 0 && <span className="inline-block h-4 w-3 rounded-sm bg-amber-400" aria-hidden="true" />}
      {roja && <span className="inline-block h-4 w-3 rounded-sm bg-rose-600" aria-hidden="true" />}
    </span>
  );
}

export function VistaPartido({ partido, ops, onVolver, onVerPendientes }: { partido: PartidoPlanilla; ops: Operacion[]; onVolver: () => void; onVerPendientes: () => void }) {
  const reloj = useReloj(partido.id);
  const [lado, setLado] = useState<"local" | "visitante">("local");
  const [jugador, setJugador] = useState<{ j: JugadorPlanilla; lado: "local" | "visitante" } | null>(null);
  const [otro, setOtro] = useState(false);
  const [finalizando, setFinalizando] = useState(false);
  const [ultimo, setUltimo] = useState<{ opId: number; texto: string; hasta: number } | null>(null);
  const [ahora, setAhora] = useState(() => Date.now());

  const eventos = useMemo(() => eventosDe(partido, ops), [partido, ops]);
  const situacion = situacionDe(partido, ops);
  const abierto = situacion === "ABIERTO";
  const cierre = operacionResultado(ops, partido.id);
  const marcador = partido.resultado ? { local: partido.resultado.goles_local, visitante: partido.resultado.goles_visitante } : marcadorDe(eventos);
  const ultimoMinuto = eventos.length ? eventos[eventos.length - 1].minuto : null;
  const minuto = minutoSugerido(reloj.ms, ultimoMinuto);
  const equipo = lado === "local" ? partido.local : partido.visitante;
  const problemasDelPartido = ops.filter((o) => o.partidoId === partido.id && o.estado !== "PENDIENTE");

  // Un temporizador solo mientras hay algo que contar: el margen para deshacer.
  const hayMargen = ops.some((o) => o.liberarEn > ahora) || (ultimo !== null && ultimo.hasta > ahora);
  useEffect(() => {
    if (!hayMargen) return;
    const id = setInterval(() => setAhora(Date.now()), 500);
    return () => clearInterval(id);
  }, [hayMargen]);

  const registrar = async (tipo: TipoIncidencia, j: JugadorPlanilla | null, min: number, descripcion?: string) => {
    const cuerpo: Record<string, unknown> = { tipo, minuto: min };
    if (j) cuerpo.jugador = j.id;
    if (descripcion) cuerpo.descripcion = descripcion;
    const opId = await encolar({ partidoId: partido.id, tipo: "incidencia", cuerpo, resumen: resumenDe(tipo, j, min) });
    setUltimo({ opId, texto: j ? `${ETIQUETA_TIPO[tipo]} de ${nombreCorto(j)} · min ${min}` : `${ETIQUETA_TIPO[tipo]} · min ${min}`, hasta: Date.now() + MARGEN_PARA_DESHACER_MS });
    setAhora(Date.now());
  };

  const finalizar = async (penales: { local: number; visitante: number } | null) => {
    const cuerpo: Record<string, unknown> = { goles_local: marcador.local, goles_visitante: marcador.visitante };
    if (penales) { cuerpo.penales_local = penales.local; cuerpo.penales_visitante = penales.visitante; }
    await encolar({ partidoId: partido.id, tipo: "resultado", cuerpo, resumen: `Resultado ${partido.local.nombre} ${marcador.local} - ${marcador.visitante} ${partido.visitante.nombre}` });
    reloj.pausar();
    setFinalizando(false);
  };

  const bloqueosCierre = [
    ...(problemasDelPartido.length ? [`Hay ${problemasDelPartido.length} acción(es) rechazadas o en conflicto. Revísalas en «Pendientes»: si falta un gol, el servidor no aceptará el marcador.`] : []),
  ];
  const avisosCierre = ops.some((o) => o.partidoId === partido.id && o.estado === "PENDIENTE" && o.tipo === "incidencia")
    ? ["Hay eventos que aún no se enviaron: saldrán primero, en orden, y luego el resultado."] : [];

  const deshacerUltimo = async () => {
    if (!ultimo) return;
    const ok = await deshacer(ultimo.opId);
    setUltimo(null);
    if (!ok) void sincronizar();
  };
  const deshacerOp = async (opId: number) => { await deshacer(opId); };

  return (
    <div className="pb-28">
      {/* Marcador */}
      <section className="relative overflow-hidden rounded-3xl bg-gradient-to-br from-ink-900 via-ink-800 to-brand-900 p-5 text-white shadow-pop" aria-label="Marcador">
        <div className="absolute -right-10 -top-10 h-40 w-40 rounded-full bg-brand-500/20 blur-2xl" aria-hidden="true" />
        <button type="button" onClick={onVolver} className="relative mb-3 inline-flex items-center gap-1 text-xs font-medium text-ink-200 hover:text-white"><ArrowLeft className="h-4 w-4" aria-hidden="true" />Partidos</button>
        <p className="relative text-center text-[11px] uppercase tracking-wider text-brand-200">{partido.campeonato.nombre} · Jornada {partido.jornada}{partido.cancha ? ` · ${partido.cancha}` : ""}</p>
        <div className="relative mt-3 grid grid-cols-[1fr_auto_1fr] items-center gap-2 text-center">
          <p className="text-sm font-bold leading-tight">{partido.local.nombre}</p>
          <p key={`${marcador.local}-${marcador.visitante}`} className="animate-pop text-5xl font-black tabular-nums">{marcador.local}<span className="mx-1.5 text-brand-300">-</span>{marcador.visitante}</p>
          <p className="text-sm font-bold leading-tight">{partido.visitante.nombre}</p>
        </div>
        <div className="relative mt-4 flex items-center justify-center gap-3">
          <span className="inline-flex items-center gap-1.5 rounded-full bg-black/30 px-3 py-1.5 text-lg font-bold tabular-nums ring-1 ring-white/15"><Clock className="h-4 w-4 text-brand-300" aria-hidden="true" />{formatoReloj(reloj.ms)}</span>
          {abierto && (
            <>
              <button type="button" onClick={reloj.corriendo ? reloj.pausar : reloj.iniciar} aria-label={reloj.corriendo ? "Pausar el cronómetro" : "Iniciar el cronómetro"}
                className={cn("flex h-11 w-11 items-center justify-center rounded-full bg-white text-brand-700 shadow-card active:scale-95", reloj.corriendo && "animate-pulse-ring")}>
                {reloj.corriendo ? <Pause className="h-5 w-5" aria-hidden="true" /> : <Play className="h-5 w-5" aria-hidden="true" />}
              </button>
              {!reloj.corriendo && reloj.ms > 0 && <button type="button" onClick={reloj.reiniciar} aria-label="Reiniciar el cronómetro" className="flex h-11 w-11 items-center justify-center rounded-full bg-white/10 ring-1 ring-white/25"><RotateCcw className="h-4 w-4" aria-hidden="true" /></button>}
            </>
          )}
        </div>
      </section>

      {/* Estado del cierre */}
      {situacion !== "ABIERTO" && (
        <div role="status" className={cn("mt-4 flex items-start gap-3 rounded-2xl p-4 text-sm", situacion === "CERRADO" ? "bg-emerald-50 text-emerald-900" : situacion === "CERRADO_POR_ENVIAR" ? "bg-amber-50 text-amber-900" : "bg-rose-50 text-rose-900")}>
          {situacion === "CERRADO" ? <CheckCircle2 className="mt-0.5 h-5 w-5 shrink-0" aria-hidden="true" /> : <CircleAlert className="mt-0.5 h-5 w-5 shrink-0" aria-hidden="true" />}
          <div className="min-w-0 flex-1">
            <p className="font-semibold">{situacion === "CERRADO" ? "Partido finalizado" : situacion === "CERRADO_POR_ENVIAR" ? "Finalizado: el resultado se enviará al volver la conexión" : "El cierre no se pudo registrar"}</p>
            {cierre?.estado !== "PENDIENTE" && cierre?.detalle && <p className="mt-0.5 text-xs">{cierre.detalle}</p>}
            {cierre && cierre.estado !== "PENDIENTE" && <button type="button" onClick={onVerPendientes} className="mt-2 text-xs font-bold underline">Revisar en Pendientes</button>}
          </div>
        </div>
      )}

      {/* Plantillas */}
      <section className="mt-5" aria-label="Plantillas">
        <div role="tablist" className="grid grid-cols-2 gap-1 rounded-2xl bg-ink-200/60 p-1">
          {(["local", "visitante"] as const).map((l) => (
            <button key={l} type="button" role="tab" aria-selected={lado === l} onClick={() => setLado(l)}
              className={cn("truncate rounded-xl px-2 py-2.5 text-sm font-bold transition-colors", lado === l ? "bg-white text-ink-900 shadow-card" : "text-ink-500")}>
              {(l === "local" ? partido.local : partido.visitante).nombre}
            </button>
          ))}
        </div>
        {equipo.jugadores.length === 0 ? (
          <p className="mt-4 rounded-2xl bg-white p-6 text-center text-sm text-ink-500 shadow-card">Este equipo no tiene jugadores activos registrados.</p>
        ) : (
          <ul className="mt-3 grid grid-cols-2 gap-2.5">
            {equipo.jugadores.map((j) => (
              <li key={j.id}>
                <button type="button" disabled={!abierto} onClick={() => setJugador({ j, lado })}
                  className={cn("flex min-h-[3.75rem] w-full items-center gap-2.5 rounded-2xl bg-white p-2.5 text-left shadow-card ring-1 ring-ink-100 transition active:scale-[0.97] disabled:opacity-60",
                    j.sancionado && "bg-rose-50 ring-rose-200")}>
                  <span className={cn("flex h-10 w-10 shrink-0 items-center justify-center rounded-full text-sm font-black text-white", lado === "local" ? "bg-brand-600" : "bg-ink-700")}>{j.numero ?? "-"}</span>
                  <span className="min-w-0 flex-1">
                    <span className="block truncate text-sm font-semibold text-ink-900">{nombreCorto(j)}</span>
                    <span className="flex items-center gap-1.5 text-[11px] text-ink-500">
                      {j.sancionado ? <b className="text-rose-700">Sancionado</b> : <span className="truncate">{j.posicion}</span>}
                      <Insignias jugadorId={j.id} eventos={eventos} />
                    </span>
                  </span>
                </button>
              </li>
            ))}
          </ul>
        )}
        {abierto && <button type="button" onClick={() => setOtro(true)} className="mt-3 w-full rounded-2xl border border-dashed border-ink-300 py-3 text-sm font-semibold text-ink-600 hover:bg-white">Anotar otro suceso</button>}
      </section>

      {/* Cronología */}
      <section className="mt-6" aria-label="Cronología">
        <h2 className="mb-2 px-1 text-xs font-bold uppercase tracking-wider text-ink-500">Cronología</h2>
        {eventos.length === 0 ? (
          <p className="rounded-2xl bg-white p-6 text-center text-sm text-ink-500 shadow-card">Aún no hay eventos. Toca un jugador para anotar un gol o una tarjeta.</p>
        ) : (
          <ol className="space-y-2">
            {eventos.map((e) => {
              const op = e.opId ? ops.find((o) => o.id === e.opId) : undefined;
              const puedeDeshacer = !!op && op.estado === "PENDIENTE" && op.liberarEn > ahora;
              return (
                <li key={e.clave} className="flex items-center gap-3 rounded-2xl bg-white p-3 shadow-card ring-1 ring-ink-100">
                  <Icono tipo={e.tipo} />
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-sm font-semibold text-ink-900">{ETIQUETA_TIPO[e.tipo]}{e.jugador ? ` · ${nombreCorto(e.jugador)}` : ""}</p>
                    <p className="truncate text-xs text-ink-500">{e.minuto != null ? `Min ${e.minuto}` : "Sin minuto"}{e.lado ? ` · ${e.lado === "local" ? partido.local.nombre : partido.visitante.nombre}` : ""}{e.descripcion ? ` · ${e.descripcion}` : ""}</p>
                    {op?.detalle && op.estado !== "PENDIENTE" && <p className="mt-0.5 text-xs text-rose-700">{op.detalle}</p>}
                  </div>
                  {puedeDeshacer
                    ? <button type="button" onClick={() => deshacerOp(op!.id!)} className="inline-flex h-9 items-center gap-1 rounded-full bg-ink-900 px-3 text-xs font-semibold text-white"><Undo2 className="h-3.5 w-3.5" aria-hidden="true" />Deshacer</button>
                    : <span className={cn("rounded-full px-2.5 py-1 text-[11px] font-semibold", ESTADO_EVENTO[e.estado].clase)}>{ESTADO_EVENTO[e.estado].texto}</span>}
                </li>
              );
            })}
          </ol>
        )}
      </section>

      {/* Aviso para deshacer lo último */}
      {ultimo && ultimo.hasta > ahora && (
        <div role="status" className="fixed inset-x-4 bottom-24 z-40 mx-auto flex max-w-md animate-slide-up items-center gap-3 rounded-2xl bg-ink-900 px-4 py-3 text-sm text-white shadow-pop">
          <span className="min-w-0 flex-1 truncate">{ultimo.texto}</span>
          <span className="text-xs tabular-nums text-ink-300">{Math.max(0, Math.ceil((ultimo.hasta - ahora) / 1000))} s</span>
          <button type="button" onClick={deshacerUltimo} className="rounded-full bg-white px-3 py-1.5 text-xs font-bold text-ink-900">Deshacer</button>
        </div>
      )}

      {/* Barra de acción */}
      {abierto && (
        <div className="fixed inset-x-0 bottom-0 z-30 border-t border-ink-200 bg-white/95 px-4 pb-[max(0.75rem,env(safe-area-inset-bottom))] pt-3 backdrop-blur">
          <Button size="lg" className="mx-auto flex w-full max-w-md" icon={<Flag className="h-5 w-5" />} onClick={() => setFinalizando(true)}>Finalizar partido</Button>
        </div>
      )}

      <HojaAcciones abierta={!!jugador} jugador={jugador?.j ?? null} equipo={jugador ? (jugador.lado === "local" ? partido.local.nombre : partido.visitante.nombre) : ""}
        minutoInicial={minuto} onCerrar={() => setJugador(null)}
        onRegistrar={(tipo, min) => { const j = jugador?.j ?? null; setJugador(null); if (j) void registrar(tipo, j, min); }} />
      <HojaOtro abierta={otro} minutoInicial={minuto} onCerrar={() => setOtro(false)} onRegistrar={(d, m) => { setOtro(false); void registrar("OTRO", null, m, d); }} />
      <HojaFinalizar abierta={finalizando} partido={partido} marcador={marcador} bloqueos={bloqueosCierre} avisos={avisosCierre} onCerrar={() => setFinalizando(false)} onConfirmar={finalizar} />
    </div>
  );
}

