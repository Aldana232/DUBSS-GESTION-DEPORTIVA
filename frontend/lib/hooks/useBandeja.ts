"use client";
import { useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { bandejaService } from "@/lib/api/services";
import { rutaDeNotificacion } from "@/lib/notificaciones";
import type { Notificacion } from "@/types";

/** Acciones de la bandeja compartidas por la campana y la pantalla Notificaciones. */
export function useBandeja() {
  const qc = useQueryClient();
  const router = useRouter();

  const refrescar = () => {
    void qc.invalidateQueries({ queryKey: ["bandeja"] });
    void qc.invalidateQueries({ queryKey: ["bandeja-resumen"] });
  };
  /** Marca como leída (si falta) y abre el destino. Si marcar falla, igual se abre. */
  const abrir = async (n: Notificacion) => {
    if (!n.leida) {
      try { await bandejaService.leer(n.id); } catch { /* se abre igual */ }
      refrescar();
    }
    router.push(rutaDeNotificacion(n.datos));
  };
  const marcarTodas = async () => {
    try { await bandejaService.leerTodas(); } finally { refrescar(); }
  };
  return { refrescar, abrir, marcarTodas };
}
