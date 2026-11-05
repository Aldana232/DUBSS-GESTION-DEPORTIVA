"use client";
import { useCallback, useEffect, useRef, useState } from "react";
import api from "@/lib/api/client";
import { authService } from "@/lib/api/services";
import { colaDB, paqueteDB, relojDB, suscribirCambios, type Operacion, type RelojPartido } from "@/lib/offline/db";
import type { PaquetePlanilla } from "@/types";
import type { Rol } from "@/lib/auth/roles";

/* ── Sesión que sobrevive a la falta de red ───────────────────────────────────────────────── */

export interface UsuarioLocal { id: number; nombre: string; apellido: string; rol: Rol }
const CLAVE_USUARIO = "dubss:planilla:usuario";

export function leerUsuarioLocal(): UsuarioLocal | null {
  try { return JSON.parse(localStorage.getItem(CLAVE_USUARIO) ?? "null") as UsuarioLocal | null; } catch { return null; }
}
export function olvidarUsuarioLocal() {
  try { localStorage.removeItem(CLAVE_USUARIO); } catch { /* almacenamiento bloqueado */ }
}

export type Sesion =
  | { estado: "cargando" }
  | { estado: "ok"; usuario: UsuarioLocal; sinConexion: boolean }
  | { estado: "sin_sesion" }                   // el servidor dijo que no hay sesión: hay que iniciar sesión
  | { estado: "requiere_conexion" };           // primera vez en este celular y sin red

/**
 * Usa la sesión del servidor; si no hay red, la última conocida en este celular. La seguridad real sigue en la API:
 * esto solo evita que la planilla se expulse al perder la señal en la cancha.
 */
export function useSesionLocal(): Sesion {
  const [sesion, setSesion] = useState<Sesion>({ estado: "cargando" });
  useEffect(() => {
    let vivo = true;
    const guardado = leerUsuarioLocal();
    if (guardado) setSesion({ estado: "ok", usuario: guardado, sinConexion: !navigator.onLine });
    authService.sesion()
      .then((u) => {
        if (!vivo) return;
        if (!u) { olvidarUsuarioLocal(); setSesion({ estado: "sin_sesion" }); return; }
        const local: UsuarioLocal = { id: u.id, nombre: u.nombre, apellido: u.apellido, rol: u.rol };
        try { localStorage.setItem(CLAVE_USUARIO, JSON.stringify(local)); } catch { /* sin almacenamiento */ }
        setSesion({ estado: "ok", usuario: local, sinConexion: false });
      })
      .catch(() => {                              // sin red: se sigue con la última sesión conocida
        if (vivo) setSesion(guardado ? { estado: "ok", usuario: guardado, sinConexion: true } : { estado: "requiere_conexion" });
      });
    return () => { vivo = false; };
  }, []);
  return sesion;
}

/* ── Paquete de partidos ─────────────────────────────────────────────────────────────────── */

export function usePaquete(usuarioId: number | null) {
  const [paquete, setPaquete] = useState<PaquetePlanilla | null>(null);
  const [cargando, setCargando] = useState(true);
  const [actualizando, setActualizando] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const leer = useCallback(async () => {
    try {
      const guardado = await paqueteDB.leer();
      // El paquete es de UNA cuenta: si otra persona entró en este celular, no se muestra.
      setPaquete(guardado && guardado.usuario === usuarioId ? guardado : null);
    } catch { setPaquete(null); } finally { setCargando(false); }
  }, [usuarioId]);

  useEffect(() => {
    if (usuarioId === null) return;
    void leer();
    return suscribirCambios(() => void leer());
  }, [usuarioId, leer]);

  const actualizar = useCallback(async () => {
    if (usuarioId === null) return false;
    setActualizando(true);
    setError(null);
    try {
      const r = await api.get<PaquetePlanilla>("/fixture/planilla/paquete/", { params: { dias: 2 } });
      await paqueteDB.guardar(r.data);
      return true;
    } catch {
      setError(navigator.onLine ? "No se pudieron descargar los partidos. Intenta de nuevo." : "Sin conexión: se muestra lo último que descargaste.");
      return false;
    } finally { setActualizando(false); }
  }, [usuarioId]);

  return { paquete, cargando, actualizando, error, actualizar };
}

/* ── Cola de acciones ────────────────────────────────────────────────────────────────────── */

export function useCola(usuarioId: number | null): Operacion[] {
  const [cola, setCola] = useState<Operacion[]>([]);
  useEffect(() => {
    if (usuarioId === null) return;
    const leer = () => colaDB.listar().then((t) => setCola(t.filter((o) => o.usuario === usuarioId))).catch(() => setCola([]));
    void leer();
    return suscribirCambios(() => void leer());
  }, [usuarioId]);
  return cola;
}

/* ── Cronómetro del partido ──────────────────────────────────────────────────────────────── */

export function useReloj(partidoId: number) {
  const [reloj, setReloj] = useState<RelojPartido>({ partidoId, acumuladoMs: 0, iniciadoEn: null });
  const [ahora, setAhora] = useState(() => Date.now());
  const listo = useRef(false);

  useEffect(() => {
    listo.current = false;
    relojDB.leer(partidoId).then((r) => { if (r) setReloj(r); listo.current = true; }).catch(() => { listo.current = true; });
  }, [partidoId]);

  useEffect(() => {
    if (reloj.iniciadoEn === null) return;
    const id = setInterval(() => setAhora(Date.now()), 1000);
    return () => clearInterval(id);
  }, [reloj.iniciadoEn]);

  const cambiar = useCallback((siguiente: RelojPartido) => { setReloj(siguiente); setAhora(Date.now()); void relojDB.guardar(siguiente).catch(() => undefined); }, []);
  const ms = reloj.acumuladoMs + (reloj.iniciadoEn ? ahora - reloj.iniciadoEn : 0);
  return {
    ms, corriendo: reloj.iniciadoEn !== null,
    iniciar: () => cambiar({ ...reloj, iniciadoEn: Date.now() }),
    pausar: () => cambiar({ ...reloj, acumuladoMs: ms, iniciadoEn: null }),
    reiniciar: () => cambiar({ partidoId, acumuladoMs: 0, iniciadoEn: null }),
  };
}
