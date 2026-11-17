"use client";
import { useCallback, useEffect, useState } from "react";
import { ClipboardList, ExternalLink, ListChecks, LogOut, WifiOff } from "lucide-react";
import { EstadoSync } from "@/components/planilla/EstadoSync";
import { Hoja } from "@/components/planilla/Hoja";
import { InstalarApp } from "@/components/planilla/InstalarApp";
import { ListaPartidos } from "@/components/planilla/ListaPartidos";
import { Pendientes } from "@/components/planilla/Pendientes";
import { VistaPartido } from "@/components/planilla/VistaPartido";
import { Button, PageLoader } from "@/components/ui";
import { Logo } from "@/components/layout/Logo";
import { Campana } from "@/components/notificaciones/Campana";
import { PuertaLegal } from "@/components/legal/PuertaLegal";
import { RegistrarPush } from "@/components/notificaciones/RegistrarPush";
import { cn } from "@/lib/utils";
import { authService } from "@/lib/api/services";
import { ROLE_HOME, ROLES_GESTION } from "@/lib/auth/roles";
import { almacenamientoDisponible, paqueteDB } from "@/lib/offline/db";
import { olvidarUsuarioLocal, useCola, usePaquete, useSesionLocal, type UsuarioLocal } from "@/lib/offline/hooks";
import { detenerSincronizacion, iniciarSincronizacion, useEstadoSync } from "@/lib/offline/sincronizador";

type Vista = { nombre: "partidos" } | { nombre: "pendientes" } | { nombre: "partido"; id: number };

/** La vista vive en la URL (?partido=12 / ?vista=pendientes) pero se cambia con la API de historial: no hace falta red. */
function leerVista(): Vista {
  const q = new URLSearchParams(window.location.search);
  const id = Number(q.get("partido"));
  if (id > 0) return { nombre: "partido", id };
  return q.get("vista") === "pendientes" ? { nombre: "pendientes" } : { nombre: "partidos" };
}
const urlDe = (v: Vista) => (v.nombre === "partido" ? `/planilla?partido=${v.id}` : v.nombre === "pendientes" ? "/planilla?vista=pendientes" : "/planilla");

function Planilla({ usuario, sinConexionInicial }: { usuario: UsuarioLocal; sinConexionInicial: boolean }) {
  const sync = useEstadoSync();
  const ops = useCola(usuario.id);
  const { paquete, cargando, actualizando, error, actualizar } = usePaquete(usuario.id);
  const [vista, setVista] = useState<Vista>({ nombre: "partidos" });
  const [saliendo, setSaliendo] = useState(false);
  const [cerrando, setCerrando] = useState(false);

  useEffect(() => { setVista(leerVista()); const f = () => setVista(leerVista()); window.addEventListener("popstate", f); return () => window.removeEventListener("popstate", f); }, []);
  useEffect(() => { iniciarSincronizacion({ id: usuario.id, nombre: `${usuario.nombre} ${usuario.apellido}`.trim() }); }, [usuario]);

  // Descarga automática al abrir con conexión (y no mientras se está enviando, para no mezclar versiones).
  useEffect(() => {
    if (navigator.onLine && !sinConexionInicial && !sync.sincronizando) void actualizar();
    // Solo al entrar con esta cuenta: las demás dependencias cambian continuamente.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [usuario.id]);
  // Tras sincronizar, se trae lo que el servidor ya confirmó.
  useEffect(() => {
    if (sync.enLinea && !sync.sincronizando && sync.ultimaSync) void actualizar();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sync.ultimaSync]);

  const ir = useCallback((v: Vista) => { window.history.pushState({}, "", urlDe(v)); setVista(v); window.scrollTo({ top: 0 }); }, []);
  const partido = vista.nombre === "partido" ? paquete?.partidos.find((p) => p.id === vista.id) : undefined;

  const salir = async () => {
    setCerrando(true);
    try { await authService.logout(); } catch { /* sin red: se cierra igual en este celular */ }
    detenerSincronizacion();
    olvidarUsuarioLocal();
    await paqueteDB.borrar().catch(() => undefined);      // los nombres de jugadores no quedan en un celular compartido; la cola solo guarda ids
    window.location.href = "/login";
  };
  const pedirSalir = () => (sync.pendientes + sync.problemas > 0 ? setSaliendo(true) : void salir());
  const total = sync.pendientes + sync.problemas;

  return (
    <div className="min-h-screen bg-ink-50 pb-[env(safe-area-inset-bottom)]">
      <header className="sticky top-0 z-30 bg-gradient-to-r from-ink-950 via-ink-900 to-brand-900 pt-[env(safe-area-inset-top)] text-white shadow-pop">
        <div className="mx-auto flex max-w-lg items-center gap-3 px-4 py-3">
          <Logo size={36} className="shrink-0 ring-2 ring-white/30" />
          <div className="min-w-0 flex-1">
            <p className="truncate text-sm font-extrabold leading-tight tracking-wide">Planilla DUBSS</p>
            <p className="truncate text-[11px] text-ink-300">{usuario.nombre} {usuario.apellido}</p>
          </div>
          <EstadoSync onAbrir={() => ir({ nombre: "pendientes" })} />
          <InstalarApp />
          <Campana modo="hoja" oscura />
          <button type="button" onClick={pedirSalir} aria-label="Cerrar sesión" className="flex h-9 w-9 items-center justify-center rounded-full bg-white/10 ring-1 ring-inset ring-white/25 hover:bg-white/20"><LogOut className="h-4 w-4" aria-hidden="true" /></button>
        </div>
        {!sync.enLinea && (
          <p role="status" className="flex items-center justify-center gap-2 bg-amber-400/90 px-4 py-1.5 text-xs font-semibold text-ink-900"><WifiOff className="h-3.5 w-3.5" aria-hidden="true" />Sin conexión: todo se guarda en este celular y se enviará solo.</p>
        )}
      </header>

      <RegistrarPush />
      <PuertaLegal enLinea={sync.enLinea} />
      <main className="mx-auto max-w-lg px-4 pb-32 pt-5">
        {vista.nombre === "partidos" && (
          <ListaPartidos paquete={paquete} ops={ops} cargando={cargando} actualizando={actualizando} error={error} enLinea={sync.enLinea}
            onActualizar={() => void actualizar()} onAbrir={(id) => ir({ nombre: "partido", id })} />
        )}
        {vista.nombre === "pendientes" && <Pendientes ops={ops} paquete={paquete} />}
        {vista.nombre === "partido" && (partido ? (
          <VistaPartido partido={partido} ops={ops} onVolver={() => ir({ nombre: "partidos" })} onVerPendientes={() => ir({ nombre: "pendientes" })} />
        ) : cargando ? <PageLoader texto="Cargando partido..." /> : (
          <div className="rounded-2xl bg-white p-8 text-center shadow-card ring-1 ring-ink-100">
            <p className="text-sm font-semibold text-ink-900">Este partido no está en los datos descargados</p>
            <p className="mt-1 text-xs text-ink-500">Vuelve a la lista y actualiza con conexión.</p>
            <Button className="mt-4" onClick={() => ir({ nombre: "partidos" })}>Ver partidos</Button>
          </div>
        ))}
      </main>

      {vista.nombre !== "partido" && (
        <nav aria-label="Navegación de la planilla" className="fixed inset-x-0 bottom-0 z-30 border-t border-ink-200 bg-white/95 pb-[max(0.5rem,env(safe-area-inset-bottom))] backdrop-blur">
          <div className="mx-auto grid max-w-lg grid-cols-3">
            {[
              { v: { nombre: "partidos" } as Vista, t: "Partidos", I: ClipboardList, activo: vista.nombre === "partidos", badge: 0 },
              { v: { nombre: "pendientes" } as Vista, t: "Pendientes", I: ListChecks, activo: vista.nombre === "pendientes", badge: total },
            ].map(({ v, t, I, activo, badge }) => (
              <button key={t} type="button" onClick={() => ir(v)} aria-current={activo ? "page" : undefined}
                className={cn("relative flex flex-col items-center gap-0.5 py-2.5 text-[11px] font-semibold transition-colors", activo ? "text-brand-700" : "text-ink-500")}>
                <span className="relative"><I className="h-5 w-5" aria-hidden="true" />{badge > 0 && <span className="absolute -right-2.5 -top-2 min-w-[1.1rem] rounded-full bg-brand-600 px-1 text-center text-[10px] font-bold leading-4 text-white">{badge}</span>}</span>
                {t}
                {activo && <span className="absolute inset-x-6 top-0 h-0.5 rounded-full bg-brand-600" aria-hidden="true" />}
              </button>
            ))}
            <a href={ROLE_HOME[usuario.rol]} className="flex flex-col items-center gap-0.5 py-2.5 text-[11px] font-semibold text-ink-500"><ExternalLink className="h-5 w-5" aria-hidden="true" />Panel completo</a>
          </div>
        </nav>
      )}

      <Hoja abierta={saliendo} onCerrar={() => setSaliendo(false)} titulo="Hay acciones sin enviar">
        <div className="space-y-4 pb-2 text-sm text-ink-700">
          <p>Tienes <b>{total}</b> acción(es) que aún no llegaron al servidor. <b>No se pierden</b> al cerrar sesión: quedan en este celular y se enviarán cuando vuelvas a entrar con esta misma cuenta.</p>
          <p className="text-xs text-ink-500">Por privacidad, los nombres de jugadores se borran de este celular al salir.</p>
          <div className="grid grid-cols-2 gap-3">
            <Button variant="secondary" size="lg" onClick={() => setSaliendo(false)}>Volver</Button>
            <Button size="lg" loading={cerrando} onClick={() => void salir()}>Cerrar sesión</Button>
          </div>
        </div>
      </Hoja>
    </div>
  );
}

export function PlanillaApp() {
  const sesion = useSesionLocal();
  const [sinAlmacenamiento, setSinAlmacenamiento] = useState(false);
  useEffect(() => { setSinAlmacenamiento(!almacenamientoDisponible()); }, []);

  useEffect(() => {
    if (sesion.estado === "sin_sesion") window.location.replace(`/login?redirect=${encodeURIComponent("/planilla")}`);
    if (sesion.estado === "ok" && !ROLES_GESTION.includes(sesion.usuario.rol)) window.location.replace(ROLE_HOME[sesion.usuario.rol]);
  }, [sesion]);

  if (sesion.estado === "cargando" || sesion.estado === "sin_sesion") {
    return <div className="flex min-h-screen items-center justify-center bg-ink-50"><PageLoader texto="Verificando sesión..." /></div>;
  }
  if (sesion.estado === "requiere_conexion") {
    return (
      <div className="flex min-h-screen items-center justify-center bg-ink-50 p-6 text-center">
        <div className="max-w-sm"><Logo size={72} className="mx-auto shadow-card" /><h1 className="mt-4 text-lg font-bold text-ink-900">Conéctate para empezar</h1>
          <p className="mt-1 text-sm text-ink-500">La primera vez en este celular necesitas internet para iniciar sesión y descargar los partidos. Después funcionará sin señal.</p>
          <Button className="mt-5" onClick={() => window.location.reload()}>Reintentar</Button></div>
      </div>
    );
  }
  if (!ROLES_GESTION.includes(sesion.usuario.rol)) return null;
  if (sinAlmacenamiento) {
    return <div className="flex min-h-screen items-center justify-center p-6 text-center text-sm text-ink-700">Este navegador no permite guardar datos en el celular (¿modo privado?). Abre la planilla en una ventana normal.</div>;
  }
  return <Planilla usuario={sesion.usuario} sinConexionInicial={sesion.sinConexion} />;
}
