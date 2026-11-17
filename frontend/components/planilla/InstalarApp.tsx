"use client";
import { useEffect, useState } from "react";
import { Download, Share } from "lucide-react";
import { Hoja } from "@/components/planilla/Hoja";
import { esAppNativa } from "@/lib/nativo";

interface EventoInstalacion extends Event { prompt: () => Promise<void>; userChoice: Promise<{ outcome: "accepted" | "dismissed" }> }

/** Botón «Instalar»: usa el aviso nativo de Chrome/Edge/Android; en iPhone explica cómo agregarla a la pantalla de inicio. */
export function InstalarApp() {
  const [evento, setEvento] = useState<EventoInstalacion | null>(null);
  const [instalada, setInstalada] = useState(false);
  const [esIos, setEsIos] = useState(false);
  const [ayuda, setAyuda] = useState(false);

  useEffect(() => {
    // Dentro de la app Android ya está «instalada»: no se ofrece instalarla otra vez.
    setInstalada(esAppNativa() || window.matchMedia("(display-mode: standalone)").matches || (navigator as Navigator & { standalone?: boolean }).standalone === true);
    setEsIos(/iphone|ipad|ipod/i.test(navigator.userAgent));
    const antes = (e: Event) => { e.preventDefault(); setEvento(e as EventoInstalacion); };
    const hecha = () => { setInstalada(true); setEvento(null); };
    window.addEventListener("beforeinstallprompt", antes);
    window.addEventListener("appinstalled", hecha);
    return () => { window.removeEventListener("beforeinstallprompt", antes); window.removeEventListener("appinstalled", hecha); };
  }, []);

  if (instalada || (!evento && !esIos)) return null;
  const instalar = async () => {
    if (!evento) { setAyuda(true); return; }
    await evento.prompt();
    await evento.userChoice;
    setEvento(null);
  };
  return (
    <>
      <button type="button" onClick={instalar} aria-label="Instalar la aplicación"
        className="flex h-9 w-9 items-center justify-center rounded-full bg-white/10 text-white ring-1 ring-inset ring-white/25 hover:bg-white/20">
        <Download className="h-4 w-4" aria-hidden="true" />
      </button>
      <Hoja abierta={ayuda} onCerrar={() => setAyuda(false)} titulo="Instalar en iPhone">
        <ol className="space-y-3 pb-3 text-sm text-ink-700">
          <li className="flex gap-3"><span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-brand-600 text-xs font-bold text-white">1</span><span>Abre esta página en <b>Safari</b>.</span></li>
          <li className="flex gap-3"><span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-brand-600 text-xs font-bold text-white">2</span><span>Toca el botón <Share className="inline h-4 w-4 align-text-bottom" aria-label="Compartir" /> <b>Compartir</b> de la barra inferior.</span></li>
          <li className="flex gap-3"><span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-brand-600 text-xs font-bold text-white">3</span><span>Elige <b>Añadir a pantalla de inicio</b> y confirma.</span></li>
        </ol>
      </Hoja>
    </>
  );
}
