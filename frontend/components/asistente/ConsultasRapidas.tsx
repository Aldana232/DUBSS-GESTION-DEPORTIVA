"use client";
import { useState } from "react";
import { Check, Download, Mic, Search, Square } from "lucide-react";
import { Badge, Button, Card, CardBody, CardHeader, FormField, Textarea, useToast } from "@/components/ui";
import { useAccion, useApi } from "@/lib/hooks/queries";
import { useGrabadora } from "@/lib/hooks/useGrabadora";
import { asistenteService, reporteService } from "@/lib/api/services";
import { mensajeDeError } from "@/lib/api/errors";
import { fechaCorta, hora } from "@/lib/utils";
import type { Interpretacion, OpcionAsistente, ResultadoAsistente } from "@/types";

const ETIQUETA_INTENCION: Record<string, string> = {
  reporte_campeonato: "Reporte del campeonato", tabla_posiciones: "Tabla de posiciones", estadisticas_jugador: "Estadísticas del jugador",
  estadisticas_equipo: "Estadísticas del equipo", proximos_partidos: "Próximos partidos", resumen_torneo: "Resumen del torneo",
};
const EJEMPLOS = [
  "Dame el reporte en PDF del campeonato de fútbol",
  "Tabla de posiciones del campeonato",
  "Próximos partidos de Ingeniería",
  "Resumen del torneo",
];

function Resultado({ r }: { r: ResultadoAsistente }) {
  const toast = useToast();
  const [bajando, setBajando] = useState(false);
  if (r.tipo === "descarga") {
    const bajar = async () => {
      setBajando(true);
      try { await reporteService.descargar(r.recurso, r.id, r.formato); toast.success("Reporte descargado."); }
      catch (e) { toast.error(mensajeDeError(e, "No se pudo descargar el reporte.")); }
      finally { setBajando(false); }
    };
    return (
      <div className="flex flex-wrap items-center justify-between gap-3">
        <p className="text-sm text-ink-700">Reporte listo: <strong>{r.nombre}</strong> ({r.formato === "pdf" ? "PDF" : "Excel"})</p>
        <Button loading={bajando} icon={<Download className="h-4 w-4" />} onClick={bajar}>Descargar</Button>
      </div>
    );
  }
  if (r.tipo === "tabla") {
    return (
      <div className="space-y-2">
        <p className="text-sm font-semibold text-ink-900">{r.campeonato}</p>
        {r.filas.length === 0 ? <p className="text-sm text-ink-500">Aún no hay posiciones.</p> : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead><tr className="text-left text-xs text-ink-500"><th className="py-1 pr-3">#</th><th className="pr-3">Equipo</th><th className="pr-3">PJ</th><th className="pr-3">G</th><th className="pr-3">E</th><th className="pr-3">P</th><th className="pr-3">GF</th><th className="pr-3">GC</th><th>Pts</th></tr></thead>
              <tbody>{r.filas.map((f) => (
                <tr key={f.equipo} className="border-t border-ink-100 tabular-nums"><td className="py-1 pr-3">{f.posicion}</td><td className="pr-3 font-medium">{f.equipo}</td><td className="pr-3">{f.pj}</td><td className="pr-3">{f.pg}</td><td className="pr-3">{f.pe}</td><td className="pr-3">{f.pp}</td><td className="pr-3">{f.gf}</td><td className="pr-3">{f.gc}</td><td className="font-bold">{f.puntos}</td></tr>
              ))}</tbody>
            </table>
          </div>
        )}
      </div>
    );
  }
  if (r.tipo === "partidos") {
    return r.partidos.length === 0 ? <p className="text-sm text-ink-500">No hay partidos programados próximos.</p> : (
      <ul className="divide-y divide-ink-100 text-sm">
        {r.partidos.map((p) => (
          <li key={p.id} className="py-2">
            <p className="font-medium text-ink-900">{p.local} vs {p.visitante}</p>
            <p className="text-xs text-ink-500">{fechaCorta(p.fecha_hora)} {hora(p.fecha_hora)} · {p.cancha ?? "Cancha por definir"} · Jornada {p.jornada} · {p.campeonato}</p>
          </li>
        ))}
      </ul>
    );
  }
  if (r.tipo === "resumen") {
    return (
      <dl className="grid gap-3 text-sm sm:grid-cols-2">
        <div><dt className="text-xs text-ink-500">Campeonato</dt><dd className="font-semibold">{r.campeonato} ({r.estado})</dd></div>
        <div><dt className="text-xs text-ink-500">Equipos</dt><dd className="font-semibold">{r.equipos}</dd></div>
        <div><dt className="text-xs text-ink-500">Partidos jugados</dt><dd className="font-semibold">{r.partidos_jugados} de {r.partidos_total}</dd></div>
        <div><dt className="text-xs text-ink-500">Goles</dt><dd className="font-semibold">{r.goles}</dd></div>
        <div><dt className="text-xs text-ink-500">Líder</dt><dd className="font-semibold">{r.lider ?? "Sin partidos jugados"}</dd></div>
        <div><dt className="text-xs text-ink-500">Goleador</dt><dd className="font-semibold">{r.goleador ? `${r.goleador.jugador} (${r.goleador.equipo}) · ${r.goleador.goles}` : "—"}</dd></div>
        <div className="sm:col-span-2"><dt className="text-xs text-ink-500">Próximo partido</dt><dd className="font-semibold">{r.proximo_partido ?? "—"}</dd></div>
      </dl>
    );
  }
  if (r.tipo === "estadisticas_equipo") {
    const d = r.datos;
    return (
      <dl className="grid grid-cols-2 gap-3 text-sm sm:grid-cols-4">
        <div className="col-span-full"><dt className="text-xs text-ink-500">Equipo</dt><dd className="font-semibold">{d.equipo} · {d.facultad}</dd></div>
        {([["PJ", d.pj], ["Ganados", d.pg], ["Empates", d.pe], ["Perdidos", d.pp], ["GF", d.gf], ["GC", d.gc], ["Puntos", d.puntos]] as const).map(([t, v]) => (
          <div key={t} className="rounded-lg bg-ink-50 p-3"><dt className="text-xs text-ink-500">{t}</dt><dd className="text-lg font-bold tabular-nums">{v}</dd></div>
        ))}
      </dl>
    );
  }
  const d = r.datos;
  return (
    <dl className="grid grid-cols-2 gap-3 text-sm sm:grid-cols-4">
      <div className="col-span-full"><dt className="text-xs text-ink-500">Jugador</dt><dd className="font-semibold">{d.jugador} · {d.equipo} · {d.facultad}</dd></div>
      {([["Goles", d.goles], ["Amarillas", d.amarillas], ["Rojas", d.rojas], ["Sanción pendiente", d.sancion_pendiente]] as const).map(([t, v]) => (
        <div key={t} className="rounded-lg bg-ink-50 p-3"><dt className="text-xs text-ink-500">{t}</dt><dd className="text-lg font-bold tabular-nums">{v}</dd></div>
      ))}
    </dl>
  );
}

/** Asistente por voz o texto: transcribe, interpreta (lista blanca de consultas) y ejecuta solo lecturas tras confirmar (F6-06). */
export function ConsultasRapidas() {
  const toast = useToast();
  const estado = useApi(["asistente-estado"], () => asistenteService.estado());
  const [texto, setTexto] = useState("");
  const [interp, setInterp] = useState<Interpretacion | null>(null);
  const [resultado, setResultado] = useState<ResultadoAsistente | null>(null);
  const grabadora = useGrabadora((t) => { setTexto(t); toast.success("Audio transcrito. Revisa el texto antes de continuar."); });
  const interpretar = useAccion(
    (a: { texto: string; previo?: Interpretacion; seleccion?: Record<string, number> }) =>
      asistenteService.interpretar(a.texto, a.previo?.intencion ? { intencion: a.previo.intencion, formato: a.previo.formato, proveedor: a.previo.proveedor } : undefined, a.seleccion),
    { error: "No se pudo interpretar la orden." },
  );
  const ejecutar = useAccion((i: Interpretacion) => asistenteService.ejecutar({
    intencion: i.intencion as string, formato: i.formato,
    campeonato: i.parametros.campeonato?.id, equipo: i.parametros.equipo?.id, jugador: i.parametros.jugador?.id,
  }), { error: "No se pudo ejecutar la consulta." });

  const enviar = (previo?: Interpretacion, seleccion?: Record<string, number>) => {
    setResultado(null);
    interpretar.ejecutar({ texto: previo?.texto ?? texto, previo, seleccion }, { onSuccess: setInterp });
  };
  const elegir = (op: OpcionAsistente) => {
    if (!interp?.aclaracion) return;
    // El servidor no recuerda lo ya elegido: se reenvían los ids acumulados junto con la nueva elección.
    const previas = Object.fromEntries(Object.entries(interp.parametros).map(([campo, p]) => [campo, p.id]));
    enviar(interp, { ...previas, [interp.aclaracion.campo]: op.id });
  };
  const confirmar = () => {
    if (interp) ejecutar.ejecutar(interp, { onSuccess: setResultado });
  };
  const nueva = () => { setTexto(""); setInterp(null); setResultado(null); };

  const vozLista = !!estado.data?.voz;

  return (
    <>
      <div className="grid gap-5 lg:grid-cols-3">
        <Card className="lg:col-span-2">
          <CardHeader title="Tu orden" />
          <CardBody className="space-y-4">
            <FormField label="Orden" hint="Puedes grabarla con el micrófono o escribirla. Revísala antes de continuar.">
              <Textarea rows={3} maxLength={500} value={texto} onChange={(e) => setTexto(e.target.value)} placeholder="Ejemplo: tabla de posiciones del campeonato" />
            </FormField>
            <div className="flex flex-wrap gap-2">
              {grabadora.grabando ? (
                <Button variant="danger" icon={<Square className="h-4 w-4" />} onClick={grabadora.detener}>Detener grabación</Button>
              ) : (
                <Button variant="secondary" disabled={!vozLista} loading={grabadora.transcribiendo} icon={<Mic className="h-4 w-4" />} onClick={grabadora.iniciar}>Grabar con voz</Button>
              )}
              <Button disabled={!texto.trim()} loading={interpretar.pendiente} icon={<Search className="h-4 w-4" />} onClick={() => enviar()}>Interpretar</Button>
              {(interp || texto) && <Button variant="ghost" onClick={nueva}>Limpiar</Button>}
            </div>
            {!vozLista && estado.data && <p className="text-xs text-ink-500">La transcripción por voz no está configurada en el servidor; escribe la orden.</p>}
            <div className="flex flex-wrap gap-2">
              {EJEMPLOS.map((e) => <button key={e} type="button" className="rounded-full border border-ink-200 px-3 py-1 text-xs text-ink-600 hover:bg-ink-50" onClick={() => setTexto(e)}>{e}</button>)}
            </div>

            {interp && (
              <div className="space-y-3 rounded-lg border border-ink-200 bg-ink-50 p-4" aria-live="polite">
                {interp.estado === "no_entendido" && <p className="text-sm text-ink-700">{interp.mensaje}</p>}
                {interp.estado === "aclaracion" && interp.aclaracion && (
                  <div className="space-y-2">
                    <p className="text-sm font-medium text-ink-900">{interp.aclaracion.pregunta}</p>
                    <div className="flex flex-wrap gap-2">
                      {interp.aclaracion.opciones.map((o) => <Button key={o.id} size="sm" variant="secondary" loading={interpretar.pendiente} onClick={() => elegir(o)}>{o.nombre}</Button>)}
                    </div>
                  </div>
                )}
                {interp.estado === "ok" && interp.intencion && (
                  <div className="space-y-3">
                    <div className="flex flex-wrap items-center gap-2 text-sm">
                      <Badge tono="brand">{ETIQUETA_INTENCION[interp.intencion]}</Badge>
                      {interp.formato && <Badge tono="info">{interp.formato === "pdf" ? "PDF" : "Excel"}</Badge>}
                      {Object.values(interp.parametros).map((p) => <Badge key={p.id} tono="neutral">{p.nombre}</Badge>)}
                    </div>
                    {interp.supuestos.map((s) => <p key={s} className="text-xs text-ink-500">{s}</p>)}
                    <Button loading={ejecutar.pendiente} icon={<Check className="h-4 w-4" />} onClick={confirmar}>Confirmar y ejecutar</Button>
                  </div>
                )}
              </div>
            )}
          </CardBody>
        </Card>

        <Card>
          <CardHeader title="Capacidades" />
          <CardBody className="space-y-3 text-sm">
            <p className="flex items-center justify-between gap-2"><span>Voz a texto</span><Badge tono={estado.data?.voz ? "success" : "warning"}>{estado.data?.voz ? "Disponible" : "No configurado"}</Badge></p>
            <p className="flex items-center justify-between gap-2"><span>Comprensión avanzada (IA)</span><Badge tono={estado.data?.llm ? "success" : "neutral"}>{estado.data?.llm ? estado.data.proveedor_llm : "Reglas locales"}</Badge></p>
            <p className="text-xs text-ink-500">Sin IA externa, el asistente entiende las consultas habituales con reglas locales. Siempre pide confirmación antes de ejecutar.</p>
          </CardBody>
        </Card>

        {resultado && (
          <Card className="lg:col-span-3">
            <CardHeader title="Resultado" />
            <CardBody><Resultado r={resultado} /></CardBody>
          </Card>
        )}
      </div>
    </>
  );
}
