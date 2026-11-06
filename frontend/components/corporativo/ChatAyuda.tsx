"use client";
import { useEffect, useRef, useState, type FormEvent } from "react";
import { Bot, Send, X } from "lucide-react";
import { AYUDA, AYUDA_SIN_RESPUESTA, PREGUNTAS_RAPIDAS, type RespuestaAyuda } from "@/lib/corporativo.contenido";

type Mensaje = { de: "yo" | "bot"; texto: string; enlace?: RespuestaAyuda["enlace"] };

function responder(pregunta: string): RespuestaAyuda {
  const s = pregunta.toLowerCase();
  return AYUDA.find((r) => r.claves.some((k) => s.includes(k))) ?? AYUDA_SIN_RESPUESTA;
}

/** Asistente de preguntas frecuentes por reglas (no es una persona ni usa IA ni servicios externos). */
export function ChatAyuda({ abierto, setAbierto }: { abierto: boolean; setAbierto: (v: boolean) => void }) {
  const [mensajes, setMensajes] = useState<Mensaje[]>([{ de: "bot", texto: "Hola. Soy un asistente automático con respuestas sobre el producto. ¿En qué te ayudo?" }]);
  const [texto, setTexto] = useState("");
  const fin = useRef<HTMLDivElement>(null);
  const entrada = useRef<HTMLInputElement>(null);

  useEffect(() => { fin.current?.scrollIntoView({ block: "end" }); }, [mensajes]);
  useEffect(() => { if (abierto) entrada.current?.focus(); }, [abierto]);

  function preguntar(p: string) {
    const r = responder(p);
    setMensajes((m) => [...m, { de: "yo", texto: p }, { de: "bot", texto: r.texto, enlace: r.enlace }]);
  }
  function enviar(e: FormEvent) {
    e.preventDefault();
    const p = texto.trim();
    if (!p) return;
    setTexto("");
    preguntar(p);
  }

  return (
    <>
      <button type="button" aria-expanded={abierto} aria-controls="chat-ayuda" onClick={() => setAbierto(!abierto)}
        className="fixed bottom-4 right-4 z-40 inline-flex h-12 items-center gap-2 rounded-full bg-brand-600 px-5 text-sm font-semibold text-white shadow-pop transition-colors hover:bg-brand-700">
        <Bot className="h-5 w-5" aria-hidden="true" />Chat de ayuda
      </button>
      {abierto && (
        <aside id="chat-ayuda" aria-label="Chat de ayuda"
          className="fixed bottom-20 right-4 z-40 flex max-h-[min(32rem,calc(100vh-7rem))] w-[min(22rem,calc(100vw-2rem))] flex-col overflow-hidden rounded-xl border border-ink-200 bg-white shadow-pop animate-slide-up">
          <header className="flex items-start justify-between gap-2 bg-ink-900 px-4 py-3 text-white">
            <div><b className="block text-sm">Asistente SportTech</b><small className="text-xs text-ink-300">Respuestas automáticas · no es una persona</small></div>
            <button type="button" onClick={() => setAbierto(false)} aria-label="Cerrar chat" className="rounded p-1 text-ink-200 hover:bg-white/10"><X className="h-4 w-4" /></button>
          </header>
          <div className="scroll-thin flex-1 space-y-2 overflow-y-auto bg-ink-50 p-3" aria-live="polite">
            {mensajes.map((m, i) => (
              <div key={i} className={m.de === "yo" ? "ml-auto max-w-[85%] rounded-xl rounded-br-sm bg-brand-600 px-3 py-2 text-sm text-white" : "mr-auto max-w-[90%] rounded-xl rounded-bl-sm border border-ink-200 bg-white px-3 py-2 text-sm text-ink-800"}>
                {m.texto}
                {m.enlace && <a href={m.enlace.href} onClick={() => setAbierto(false)} className="mt-1 block font-medium text-brand-700 underline">{m.enlace.etiqueta}</a>}
              </div>
            ))}
            <div ref={fin} />
          </div>
          <div className="flex flex-wrap gap-1.5 border-t border-ink-100 bg-white px-3 py-2">
            {PREGUNTAS_RAPIDAS.map((q) => (
              <button key={q} type="button" onClick={() => preguntar(q)} className="rounded-full border border-ink-200 px-2.5 py-1 text-xs text-ink-700 hover:bg-ink-50">{q}</button>
            ))}
          </div>
          <form onSubmit={enviar} className="flex gap-2 border-t border-ink-100 bg-white p-3">
            <input ref={entrada} value={texto} onChange={(e) => setTexto(e.target.value)} placeholder="Escribe tu pregunta" autoComplete="off" aria-label="Tu pregunta"
              className="min-w-0 flex-1 rounded-lg border border-ink-200 px-3 text-sm" />
            <button type="submit" className="inline-flex h-9 items-center gap-1.5 rounded-lg bg-brand-600 px-3 text-sm font-medium text-white hover:bg-brand-700"><Send className="h-4 w-4" aria-hidden="true" /><span className="sr-only">Enviar</span></button>
          </form>
        </aside>
      )}
    </>
  );
}
