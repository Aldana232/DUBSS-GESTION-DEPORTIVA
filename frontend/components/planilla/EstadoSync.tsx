"use client";
import { CheckCircle2, CircleAlert, CloudUpload, RefreshCw, WifiOff } from "lucide-react";
import { cn } from "@/lib/utils";
import { useEstadoSync } from "@/lib/offline/sincronizador";

/** Indicador permanente: en qué estado está lo que se anotó en este celular. Al tocarlo abre la lista de pendientes. */
export function EstadoSync({ onAbrir }: { onAbrir: () => void }) {
  const s = useEstadoSync();
  let tono = "bg-emerald-500/15 text-emerald-100 ring-emerald-400/40";
  let Icono = CheckCircle2;
  let texto = "Sincronizado";
  let girar = false;

  if (s.sesionVencida) { tono = "bg-rose-500/25 text-rose-50 ring-rose-300/50"; Icono = CircleAlert; texto = "Inicia sesión"; }
  else if (s.problemas > 0) { tono = "bg-rose-500/25 text-rose-50 ring-rose-300/50"; Icono = CircleAlert; texto = `${s.problemas} por revisar`; }
  else if (!s.enLinea) { tono = "bg-amber-400/20 text-amber-50 ring-amber-300/50"; Icono = WifiOff; texto = s.pendientes ? `Sin conexión · ${s.pendientes}` : "Sin conexión"; }
  else if (s.sincronizando) { tono = "bg-sky-400/20 text-sky-50 ring-sky-300/50"; Icono = RefreshCw; texto = "Sincronizando"; girar = true; }
  else if (s.pendientes > 0) { tono = "bg-amber-400/20 text-amber-50 ring-amber-300/50"; Icono = CloudUpload; texto = `${s.pendientes} por enviar`; }

  return (
    <button type="button" onClick={onAbrir} aria-live="polite"
      className={cn("inline-flex h-9 items-center gap-1.5 rounded-full px-3 text-xs font-semibold ring-1 ring-inset transition-colors", tono)}>
      <Icono className={cn("h-4 w-4", girar && "animate-spin")} aria-hidden="true" />
      {texto}
    </button>
  );
}
