"use client";
import { useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { Bell, CheckCheck } from "lucide-react";
import { cn } from "@/lib/utils";
import { useToast } from "@/components/ui";
import { Hoja } from "@/components/planilla/Hoja";
import { bandejaService } from "@/lib/api/services";
import { useBandeja } from "@/lib/hooks/useBandeja";
import type { Notificacion } from "@/types";
import { ItemNotificacion } from "./ItemNotificacion";

/**
 * Campana con la cantidad de avisos sin leer. Consulta cada 30 s solo mientras la pantalla está visible
 * (no gasta datos ni batería en segundo plano) y al volver a la app.
 * `modo="hoja"` abre la bandeja como cajón inferior (pantalla táctil de la planilla); `"menu"` como desplegable.
 */
export function Campana({ modo = "menu", oscura = false }: { modo?: "menu" | "hoja"; oscura?: boolean }) {
  const toast = useToast();
  const [abierta, setAbierta] = useState(false);
  const contenedor = useRef<HTMLDivElement>(null);
  const anterior = useRef<number | null>(null);

  const resumen = useQuery({
    queryKey: ["bandeja-resumen"], queryFn: () => bandejaService.resumen(),
    refetchInterval: 30_000, refetchIntervalInBackground: false, refetchOnWindowFocus: true, staleTime: 10_000,
  });
  const lista = useQuery({ queryKey: ["bandeja", "recientes"], queryFn: () => bandejaService.listar(), enabled: abierta });
  const pendientes = resumen.data?.no_leidas ?? 0;

  // Aviso emergente cuando llega algo nuevo mientras se usa la app (la primera lectura no cuenta).
  useEffect(() => {
    if (resumen.data === undefined) return;
    if (anterior.current !== null && pendientes > anterior.current && !abierta) {
      const nuevas = pendientes - anterior.current;
      toast.info(nuevas === 1 ? "Tienes una notificación nueva." : `Tienes ${nuevas} notificaciones nuevas.`);
    }
    anterior.current = pendientes;
  }, [pendientes, resumen.data, abierta, toast]);

  useEffect(() => {
    if (!abierta || modo !== "menu") return;
    const fuera = (e: MouseEvent) => { if (!contenedor.current?.contains(e.target as Node)) setAbierta(false); };
    const tecla = (e: KeyboardEvent) => { if (e.key === "Escape") setAbierta(false); };
    document.addEventListener("mousedown", fuera);
    document.addEventListener("keydown", tecla);
    return () => { document.removeEventListener("mousedown", fuera); document.removeEventListener("keydown", tecla); };
  }, [abierta, modo]);

  const { abrir: abrirNotificacion, marcarTodas } = useBandeja();
  const abrir = async (n: Notificacion) => {
    setAbierta(false);
    await abrirNotificacion(n);
  };

  const items = lista.data?.results ?? [];
  const contenido = (
    <>
      {lista.isLoading ? <p className="px-4 py-6 text-center text-sm text-ink-500">Cargando…</p>
        : items.length === 0 ? <p className="px-4 py-8 text-center text-sm text-ink-500">No tienes notificaciones.</p>
        : <ul className="divide-y divide-ink-100">{items.slice(0, 8).map((n) => <li key={n.id}><ItemNotificacion n={n} onAbrir={(x) => void abrir(x)} /></li>)}</ul>}
      <div className="flex items-center justify-between gap-2 border-t border-ink-100 px-4 py-2.5">
        <button type="button" onClick={() => void marcarTodas()} disabled={pendientes === 0}
          className="inline-flex items-center gap-1.5 text-xs font-medium text-ink-600 hover:text-brand-700 disabled:opacity-40">
          <CheckCheck className="h-3.5 w-3.5" aria-hidden="true" />Marcar todas como leídas
        </button>
        <Link href="/notificaciones" onClick={() => setAbierta(false)} className="text-xs font-semibold text-brand-700 hover:underline">Ver todas</Link>
      </div>
    </>
  );

  return (
    <div ref={contenedor} className="relative">
      <button type="button" onClick={() => setAbierta((a) => !a)} aria-haspopup="dialog" aria-expanded={abierta}
        aria-label={pendientes > 0 ? `Notificaciones: ${pendientes} sin leer` : "Notificaciones"}
        className={cn("relative flex h-9 w-9 items-center justify-center rounded-full transition-colors",
          oscura ? "bg-white/10 text-white ring-1 ring-inset ring-white/25 hover:bg-white/20" : "text-ink-700 hover:bg-ink-100")}>
        <Bell className="h-5 w-5" aria-hidden="true" />
        {pendientes > 0 && (
          <span className="absolute -right-0.5 -top-0.5 flex h-4 min-w-[1rem] items-center justify-center rounded-full bg-brand-600 px-1 text-[10px] font-bold leading-none text-white ring-2 ring-white">
            {pendientes > 9 ? "9+" : pendientes}
          </span>
        )}
      </button>
      {modo === "menu" && abierta && (
        <div role="dialog" aria-label="Notificaciones" className="absolute right-0 z-40 mt-2 w-[min(22rem,calc(100vw-2rem))] animate-fade-in overflow-hidden rounded-xl border border-ink-200 bg-white shadow-pop">
          <p className="border-b border-ink-100 px-4 py-3 text-sm font-semibold text-ink-900">Notificaciones</p>
          <div className="max-h-[26rem] overflow-y-auto scroll-thin">{contenido}</div>
        </div>
      )}
      {/* En un portal: dentro del encabezado quedaría atrapado en su nivel de apilamiento y la barra inferior lo taparía. */}
      {modo === "hoja" && typeof document !== "undefined" && createPortal(
        <Hoja abierta={abierta} onCerrar={() => setAbierta(false)} titulo="Notificaciones">{contenido}</Hoja>, document.body)}
    </div>
  );
}
