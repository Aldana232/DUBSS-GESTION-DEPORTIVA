"use client";
import { createContext, useCallback, useContext, useMemo, useState, type ReactNode } from "react";
import { AlertCircle, CheckCircle2, Info, X } from "lucide-react";
import { cn } from "@/lib/utils";

type Tipo = "success" | "error" | "info";
interface Aviso { id: number; tipo: Tipo; mensaje: string }
interface ToastApi { success: (m: string) => void; error: (m: string) => void; info: (m: string) => void }

const ToastContext = createContext<ToastApi | null>(null);

const ESTILO: Record<Tipo, { clase: string; Icono: typeof Info }> = {
  success: { clase: "border-emerald-200 text-emerald-700", Icono: CheckCircle2 },
  error:   { clase: "border-brand-200 text-brand-700", Icono: AlertCircle },
  info:    { clase: "border-sky-200 text-sky-700", Icono: Info },
};

let siguienteId = 1;

export function ToastProvider({ children }: { children: ReactNode }) {
  const [avisos, setAvisos] = useState<Aviso[]>([]);
  const quitar = useCallback((id: number) => setAvisos((a) => a.filter((x) => x.id !== id)), []);
  const agregar = useCallback((tipo: Tipo, mensaje: string) => {
    const id = siguienteId++;
    setAvisos((a) => [...a.slice(-3), { id, tipo, mensaje }]);
    setTimeout(() => quitar(id), tipo === "error" ? 8000 : 4500);
  }, [quitar]);

  const api = useMemo<ToastApi>(() => ({
    success: (m) => agregar("success", m),
    error: (m) => agregar("error", m),
    info: (m) => agregar("info", m),
  }), [agregar]);

  return (
    <ToastContext.Provider value={api}>
      {children}
      <div className="pointer-events-none fixed inset-x-0 bottom-0 z-[60] flex flex-col items-center gap-2 p-4 sm:items-end" aria-live="polite">
        {avisos.map((a) => {
          const { clase, Icono } = ESTILO[a.tipo];
          return (
            <div key={a.id} role={a.tipo === "error" ? "alert" : "status"}
              className={cn("pointer-events-auto flex w-full max-w-sm animate-slide-up items-start gap-3 rounded-xl border bg-white p-3 shadow-pop", clase)}>
              <Icono className="mt-0.5 h-5 w-5 shrink-0" aria-hidden="true" />
              <p className="flex-1 text-sm text-ink-800">{a.mensaje}</p>
              <button type="button" aria-label="Cerrar aviso" onClick={() => quitar(a.id)} className="rounded p-0.5 text-ink-400 hover:text-ink-700">
                <X className="h-4 w-4" />
              </button>
            </div>
          );
        })}
      </div>
    </ToastContext.Provider>
  );
}

export function useToast(): ToastApi {
  const ctx = useContext(ToastContext);
  if (!ctx) throw new Error("useToast debe usarse dentro de <ToastProvider>.");
  return ctx;
}
