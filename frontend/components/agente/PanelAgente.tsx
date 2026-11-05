"use client";
import { useEffect, useRef, useState, type KeyboardEvent } from "react";
import { Bot, CheckCircle2, Download, Mic, Plus, SendHorizontal, Square, XCircle } from "lucide-react";
import { Badge, Button, Card, CardBody, CardHeader, Select, Spinner, Textarea, useToast } from "@/components/ui";
import { TarjetaAccion } from "@/components/agente/TarjetaAccion";
import { useAccion, useApi } from "@/lib/hooks/queries";
import { useGrabadora } from "@/lib/hooks/useGrabadora";
import { agenteService, asistenteService, reporteService } from "@/lib/api/services";
import { mensajeDeError } from "@/lib/api/errors";
import { fechaCorta, hora } from "@/lib/utils";
import type { MensajeAgente } from "@/types";

const EJEMPLOS = [
  "Hay lluvia el sábado, reprograma lo necesario",
  "¿Qué partidos hay mañana?",
  "Avisa a los delegados que mañana se suspende la jornada",
  "Prepara el reporte en PDF del campeonato",
];

/** El texto del agente se muestra tal cual: se quitan marcas de formato que el modelo pueda haber dejado. */
const sinFormato = (t: string) => t.replace(/\*\*/g, "").replace(/^#+\s*/gm, "");

function Pasos({ pasos }: { pasos: MensajeAgente["pasos"] }) {
  if (!pasos.length) return null;
  return (
    <ul className="mb-2 flex flex-wrap gap-1.5" aria-label="Consultas que hizo el agente">
      {pasos.map((p, i) => {
        const arg = p.argumentos ? Object.values(p.argumentos).filter(Boolean).slice(0, 2).join(" · ") : "";
        return (
          <li key={`${p.herramienta}-${i}`}>
            <Badge tono={p.ok ? "neutral" : "danger"} className="gap-1">
              {p.ok ? <CheckCircle2 className="h-3 w-3" aria-hidden="true" /> : <XCircle className="h-3 w-3" aria-hidden="true" />}
              {p.etiqueta}{arg && ` · ${arg}`}
            </Badge>
          </li>
        );
      })}
    </ul>
  );
}

function Descargas({ descargas }: { descargas: MensajeAgente["descargas"] }) {
  const toast = useToast();
  const [bajando, setBajando] = useState<string | null>(null);
  if (!descargas.length) return null;
  const bajar = async (d: MensajeAgente["descargas"][number]) => {
    const clave = `${d.recurso}-${d.id}-${d.formato}`;
    setBajando(clave);
    try { await reporteService.descargar(d.recurso, d.id, d.formato); toast.success("Reporte descargado."); }
    catch (e) { toast.error(mensajeDeError(e, "No se pudo descargar el reporte.")); }
    finally { setBajando(null); }
  };
  return (
    <div className="mt-3 flex flex-wrap gap-2">
      {descargas.map((d) => (
        <Button key={`${d.recurso}-${d.id}-${d.formato}`} size="sm" variant="secondary" icon={<Download className="h-4 w-4" />}
          loading={bajando === `${d.recurso}-${d.id}-${d.formato}`} onClick={() => bajar(d)}>
          {d.nombre} ({d.formato === "pdf" ? "PDF" : "Excel"})
        </Button>
      ))}
    </div>
  );
}

function Burbuja({ m }: { m: MensajeAgente }) {
  if (m.rol === "USUARIO") {
    return <div className="flex justify-end"><p className="max-w-[85%] whitespace-pre-wrap rounded-2xl rounded-br-sm bg-brand-600 px-4 py-2.5 text-sm text-white">{m.contenido}</p></div>;
  }
  return (
    <div className="flex gap-3">
      <span className="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-ink-900 text-white"><Bot className="h-4 w-4" aria-hidden="true" /></span>
      <div className="min-w-0 max-w-[90%] flex-1">
        <Pasos pasos={m.pasos} />
        <p className="whitespace-pre-wrap rounded-2xl rounded-tl-sm bg-ink-50 px-4 py-2.5 text-sm text-ink-900">{sinFormato(m.contenido)}</p>
        <Descargas descargas={m.descargas} />
        {m.acciones.map((a) => <TarjetaAccion key={a.id} accion={a} />)}
      </div>
    </div>
  );
}

/** Conversación con el agente del organizador (F7-03): consulta, calcula y propone; los cambios se confirman con un botón. */
export function PanelAgente() {
  const toast = useToast();
  const estado = useApi(["agente-estado"], () => agenteService.estado());
  const voz = useApi(["asistente-estado"], () => asistenteService.estado());
  const historial = useApi(["agente-conversaciones"], () => agenteService.conversaciones());
  const [conversacion, setConversacion] = useState<number | null>(null);
  const detalle = useApi(["agente-conv", conversacion], () => agenteService.conversacion(conversacion as number), conversacion !== null);
  const [texto, setTexto] = useState("");
  const [enviado, setEnviado] = useState<string | null>(null);      // mensaje en vuelo, se muestra mientras el agente trabaja
  const fin = useRef<HTMLDivElement>(null);

  const grabadora = useGrabadora((t) => setTexto((previo) => (previo ? `${previo} ${t}` : t)));
  const enviar = useAccion((t: string) => agenteService.enviar(t, conversacion), { invalidar: ["agente-conv", "agente-conversaciones"] });

  const mensajes = detalle.data?.mensajes ?? [];
  useEffect(() => { fin.current?.scrollIntoView({ block: "end" }); }, [mensajes.length, enviado]);

  const mandar = (contenido = texto) => {
    const limpio = contenido.trim();
    if (limpio.length < 2 || enviar.pendiente) return;
    setEnviado(limpio);
    setTexto("");
    enviar.ejecutar(limpio, {
      onSuccess: (r) => { setConversacion(r.conversacion); setEnviado(null); },
      onError: (e) => { setEnviado(null); setTexto(limpio); toast.error(mensajeDeError(e, "El agente no pudo responder.")); },
    });
  };
  const alTeclear = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); mandar(); }
  };
  const nueva = () => { setConversacion(null); setTexto(""); setEnviado(null); };

  const apagado = estado.data && !estado.data.disponible;

  return (
    <Card>
      <CardHeader
        title={<span className="inline-flex items-center gap-2"><Bot className="h-4 w-4 text-brand-600" aria-hidden="true" />Agente del organizador</span>}
        action={
          <div className="flex items-center gap-2">
            {(historial.data?.length ?? 0) > 0 && (
              <Select aria-label="Conversaciones anteriores" className="h-8 w-48 text-xs" value={conversacion ?? ""} onChange={(e) => setConversacion(e.target.value ? Number(e.target.value) : null)}>
                <option value="">Conversaciones anteriores</option>
                {historial.data?.map((c) => <option key={c.id} value={c.id}>{c.titulo || `Conversación ${c.id}`} · {fechaCorta(c.actualizado_en)}</option>)}
              </Select>
            )}
            <Button size="sm" variant="secondary" icon={<Plus className="h-4 w-4" />} onClick={nueva}>Nueva</Button>
          </div>
        }
      />
      <CardBody className="space-y-4">
        {apagado && <p role="status" className="rounded-lg bg-amber-50 p-3 text-sm text-amber-900">El agente no está configurado en el servidor (falta la clave del modelo de IA). Mientras tanto puedes usar las consultas rápidas.</p>}

        <div className="max-h-[60vh] min-h-[16rem] space-y-4 overflow-y-auto pr-1 scroll-thin" aria-live="polite">
          {mensajes.length === 0 && !enviado && (
            <div className="space-y-3 py-6 text-center">
              <p className="text-sm text-ink-600">Pídeme información o que prepare cambios. Yo calculo y propongo; tú confirmas.</p>
              <div className="flex flex-wrap justify-center gap-2">
                {EJEMPLOS.map((e) => <button key={e} type="button" disabled={!!apagado} className="rounded-full border border-ink-200 px-3 py-1 text-xs text-ink-600 hover:bg-ink-50 disabled:opacity-50" onClick={() => setTexto(e)}>{e}</button>)}
              </div>
            </div>
          )}
          {mensajes.map((m) => <Burbuja key={m.id} m={m} />)}
          {enviado && (
            <>
              <div className="flex justify-end"><p className="max-w-[85%] whitespace-pre-wrap rounded-2xl rounded-br-sm bg-brand-600 px-4 py-2.5 text-sm text-white">{enviado}</p></div>
              <div className="flex items-center gap-3 text-sm text-ink-500"><Spinner label="El agente está trabajando" />El agente está trabajando, puede tardar unos segundos...</div>
            </>
          )}
          <div ref={fin} />
        </div>

        <div className="space-y-2 border-t border-ink-100 pt-4">
          <Textarea rows={2} maxLength={1000} value={texto} disabled={!!apagado} aria-label="Mensaje para el agente" placeholder="Escribe tu petición (Enter envía, Shift+Enter salto de línea)"
            onChange={(e) => setTexto(e.target.value)} onKeyDown={alTeclear} />
          <div className="flex flex-wrap items-center justify-between gap-2">
            <p className="text-xs text-ink-500">{estado.data ? `Máximo ${estado.data.limite_por_hora} mensajes por hora. Las acciones vencen a los ${estado.data.vigencia_minutos} minutos.` : ""}{enviado ? "" : mensajes.length > 0 && ` Última respuesta ${hora(mensajes[mensajes.length - 1].creado_en)}.`}</p>
            <div className="flex gap-2">
              {grabadora.grabando ? (
                <Button size="sm" variant="danger" icon={<Square className="h-4 w-4" />} onClick={grabadora.detener}>Detener</Button>
              ) : (
                <Button size="sm" variant="secondary" disabled={!voz.data?.voz || !!apagado} loading={grabadora.transcribiendo} icon={<Mic className="h-4 w-4" />} onClick={grabadora.iniciar}>Voz</Button>
              )}
              <Button size="sm" disabled={texto.trim().length < 2 || !!apagado} loading={enviar.pendiente} icon={<SendHorizontal className="h-4 w-4" />} onClick={() => mandar()}>Enviar</Button>
            </div>
          </div>
        </div>
      </CardBody>
    </Card>
  );
}
