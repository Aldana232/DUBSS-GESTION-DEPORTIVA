"use client";
import { useCallback, useEffect, useRef, useState, type ReactNode } from "react";
import Image from "next/image";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { ChevronsLeft, ChevronsRight, Globe, LogOut, Menu, UserCircle, X } from "lucide-react";
import { cn } from "@/lib/utils";
import { useAuth } from "@/lib/hooks/useAuth";
import { NAV_BY_ROLE, ROLE_HOME, ROL_ETIQUETA, itemActivo } from "@/lib/auth/roles";
import { Campana } from "@/components/notificaciones/Campana";
import { PuertaLegal } from "@/components/legal/PuertaLegal";
import { BotonCookies } from "@/components/cookies/BotonCookies";
import { DOCUMENTOS_LEGALES } from "@/lib/legal.config";
import { leerConsentimiento, preferenciasPermitidas, EVENTO_CONSENTIMIENTO } from "@/lib/consentimiento";
import { RegistrarPush } from "@/components/notificaciones/RegistrarPush";
import { Logo } from "./Logo";
import { ICONOS } from "./iconos";

const LLAVE_COLAPSO = "dubss.menu.colapsado";

function Navegacion({ colapsado, onNavegar }: { colapsado: boolean; onNavegar?: () => void }) {
  const pathname = usePathname();
  const { rol } = useAuth();
  const items = rol ? NAV_BY_ROLE[rol] : [];
  return (
    <nav aria-label="Menú principal" className="flex-1 space-y-1 overflow-y-auto px-3 py-4 scroll-thin">
      {items.map((item) => {
        const Icono = ICONOS[item.icono];
        const activo = itemActivo(item, pathname);
        return (
          <Link
            key={item.href}
            href={item.href}
            onClick={onNavegar}
            aria-current={activo ? "page" : undefined}
            title={colapsado ? item.label : undefined}
            className={cn(
              "group relative flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors",
              "focus-visible:ring-offset-ink-900",
              activo ? "bg-brand-600 text-white shadow-sm" : "text-ink-300 hover:bg-white/10 hover:text-white",
              colapsado && "justify-center px-0",
            )}
          >
            <Icono className="h-5 w-5 shrink-0" aria-hidden="true" />
            <span className={cn(colapsado && "sr-only")}>{item.label}</span>
          </Link>
        );
      })}
    </nav>
  );
}

function CabeceraMarca({ colapsado }: { colapsado: boolean }) {
  const { rol } = useAuth();
  return (
    <Link href={rol ? ROLE_HOME[rol] : "/"} className={cn("flex items-center gap-3 px-4 py-4", colapsado && "justify-center px-0")} aria-label="DUBSS, ir al inicio">
      <Logo size={colapsado ? 36 : 44} />
      {!colapsado && (
        <span className="leading-tight">
          <span className="block text-base font-bold tracking-wide text-white">D.U.B.S.S.</span>
          <span className="block text-[11px] uppercase tracking-wider text-ink-400">Gestión deportiva</span>
        </span>
      )}
    </Link>
  );
}

function MenuUsuario() {
  const { usuario, rol, logout } = useAuth();
  const [abierto, setAbierto] = useState(false);
  const contenedor = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!abierto) return;
    const fuera = (e: MouseEvent) => { if (!contenedor.current?.contains(e.target as Node)) setAbierto(false); };
    const tecla = (e: KeyboardEvent) => { if (e.key === "Escape") setAbierto(false); };
    document.addEventListener("mousedown", fuera);
    document.addEventListener("keydown", tecla);
    return () => { document.removeEventListener("mousedown", fuera); document.removeEventListener("keydown", tecla); };
  }, [abierto]);

  const inicial = usuario?.nombre?.charAt(0) ?? "U";
  const foto = usuario?.foto_perfil;
  return (
    <div ref={contenedor} className="relative">
      <button
        type="button"
        aria-haspopup="menu"
        aria-expanded={abierto}
        onClick={() => setAbierto((a) => !a)}
        className="flex items-center gap-3 rounded-lg px-2 py-1.5 text-left transition-colors hover:bg-ink-100"
      >
        {foto ? (
          <Image src={foto} alt="" width={36} height={36} unoptimized className="h-9 w-9 rounded-full object-cover" />
        ) : (
          <span className="flex h-9 w-9 items-center justify-center rounded-full bg-brand-600 text-sm font-bold text-white">{inicial}</span>
        )}
        <span className="hidden min-w-0 sm:block">
          <span className="block max-w-[11rem] truncate text-sm font-semibold text-ink-900">{usuario?.nombre_completo ?? "Usuario"}</span>
          <span className="block text-xs text-ink-500">{rol ? ROL_ETIQUETA[rol] : ""}</span>
        </span>
      </button>
      {abierto && (
        <div role="menu" className="absolute right-0 z-40 mt-2 w-64 animate-fade-in rounded-xl border border-ink-200 bg-white p-2 shadow-pop">
          <div className="border-b border-ink-100 px-3 py-2">
            <p className="truncate text-sm font-semibold text-ink-900">{usuario?.nombre_completo}</p>
            <p className="truncate text-xs text-ink-500">{usuario?.email}</p>
          </div>
          <Link href="/perfil" role="menuitem" onClick={() => setAbierto(false)} className="mt-1 flex w-full items-center gap-2 rounded-lg px-3 py-2 text-sm text-ink-700 hover:bg-ink-50">
            <UserCircle className="h-4 w-4" aria-hidden="true" />
            Mi perfil
          </Link>
          <Link href="/" role="menuitem" onClick={() => setAbierto(false)} className="flex w-full items-center gap-2 rounded-lg px-3 py-2 text-sm text-ink-700 hover:bg-ink-50">
            <Globe className="h-4 w-4" aria-hidden="true" />
            Ver sitio público
          </Link>
          <button
            type="button"
            role="menuitem"
            onClick={logout}
            className="flex w-full items-center gap-2 rounded-lg px-3 py-2 text-sm text-ink-700 hover:bg-brand-50 hover:text-brand-700"
          >
            <LogOut className="h-4 w-4" aria-hidden="true" />
            Cerrar sesión
          </button>
        </div>
      )}
    </div>
  );
}

export function AppShell({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const [colapsado, setColapsado] = useState(false);
  const [movil, setMovil] = useState(false);

  // «Menú contraído» es una preferencia OPCIONAL: solo se lee y se guarda si la persona lo permitió en las cookies.
  useEffect(() => {
    const leer = () => {
      try { setColapsado(preferenciasPermitidas() && localStorage.getItem(LLAVE_COLAPSO) === "1"); } catch { /* sin almacenamiento */ }
    };
    leer();
    window.addEventListener(EVENTO_CONSENTIMIENTO, leer);
    return () => window.removeEventListener(EVENTO_CONSENTIMIENTO, leer);
  }, []);
  const alternar = () => {
    setColapsado((c) => {
      try { if (leerConsentimiento()?.preferencias) localStorage.setItem(LLAVE_COLAPSO, c ? "0" : "1"); } catch { /* sin almacenamiento */ }
      return !c;
    });
  };

  const cerrarMovil = useCallback(() => setMovil(false), []);
  useEffect(() => { cerrarMovil(); }, [pathname, cerrarMovil]);
  useEffect(() => {
    if (!movil) return;
    const tecla = (e: KeyboardEvent) => { if (e.key === "Escape") cerrarMovil(); };
    document.addEventListener("keydown", tecla);
    document.body.style.overflow = "hidden";
    return () => { document.removeEventListener("keydown", tecla); document.body.style.overflow = ""; };
  }, [movil, cerrarMovil]);

  return (
    <div className="min-h-screen bg-ink-50">
      <a href="#contenido" className="sr-only focus:not-sr-only focus:fixed focus:left-3 focus:top-3 focus:z-[70] focus:rounded-lg focus:bg-white focus:px-4 focus:py-2 focus:shadow-pop">
        Saltar al contenido
      </a>

      {/* Barra lateral de escritorio */}
      <aside
        className={cn(
          "fixed inset-y-0 left-0 z-30 hidden flex-col border-r border-white/5 bg-ink-900 transition-[width] duration-200 lg:flex",
          colapsado ? "w-[4.5rem]" : "w-64",
        )}
      >
        <CabeceraMarca colapsado={colapsado} />
        <div className="mx-3 h-px bg-white/10" />
        <Navegacion colapsado={colapsado} />
        <div className="border-t border-white/10 p-3">
          <button
            type="button"
            onClick={alternar}
            aria-label={colapsado ? "Expandir menú" : "Contraer menú"}
            aria-pressed={colapsado}
            className={cn(
              "flex w-full items-center gap-3 rounded-lg px-3 py-2 text-sm text-ink-400 transition-colors hover:bg-white/10 hover:text-white focus-visible:ring-offset-ink-900",
              colapsado && "justify-center px-0",
            )}
          >
            {colapsado ? <ChevronsRight className="h-5 w-5" aria-hidden="true" /> : <><ChevronsLeft className="h-5 w-5" aria-hidden="true" /><span>Contraer menú</span></>}
          </button>
        </div>
      </aside>

      {/* Menú móvil (cajón) */}
      {movil && (
        <div className="fixed inset-0 z-40 lg:hidden">
          <div className="absolute inset-0 animate-fade-in bg-ink-950/60" onClick={cerrarMovil} aria-hidden="true" />
          <aside role="dialog" aria-modal="true" aria-label="Menú" className="relative flex h-full w-72 max-w-[85vw] animate-fade-in flex-col bg-ink-900">
            <div className="flex items-center justify-between pr-3">
              <CabeceraMarca colapsado={false} />
              <button type="button" aria-label="Cerrar menú" onClick={cerrarMovil} className="rounded-lg p-2 text-ink-300 hover:bg-white/10 hover:text-white focus-visible:ring-offset-ink-900">
                <X className="h-5 w-5" />
              </button>
            </div>
            <div className="mx-3 h-px bg-white/10" />
            <Navegacion colapsado={false} onNavegar={cerrarMovil} />
          </aside>
        </div>
      )}

      {/* Contenido */}
      <div className={cn("transition-[padding] duration-200", colapsado ? "lg:pl-[4.5rem]" : "lg:pl-64")}>
        <header className="sticky top-0 z-20 flex h-16 items-center justify-between gap-3 border-b border-ink-200 bg-white/90 px-4 backdrop-blur sm:px-6">
          <div className="flex items-center gap-3">
            <button type="button" aria-label="Abrir menú" aria-expanded={movil} onClick={() => setMovil(true)} className="rounded-lg p-2 text-ink-700 hover:bg-ink-100 lg:hidden">
              <Menu className="h-6 w-6" />
            </button>
            <span className="flex items-center gap-2 lg:hidden">
              <Logo size={30} />
              <span className="text-sm font-bold text-ink-900">D.U.B.S.S.</span>
            </span>
            <span className="hidden text-sm font-medium text-ink-500 lg:block">Universidad Autónoma Gabriel René Moreno</span>
          </div>
          <div className="flex items-center gap-1">
            <Campana />
            <MenuUsuario />
          </div>
        </header>
        <RegistrarPush />
        <PuertaLegal />
        <main id="contenido" tabIndex={-1} className="mx-auto w-full min-w-0 max-w-6xl px-4 py-6 sm:px-6 lg:py-8">
          {children}
        </main>
        <footer className="mx-auto w-full max-w-6xl border-t border-ink-200 px-4 py-4 text-xs text-ink-500 sm:px-6">
          <nav aria-label="Información legal" className="flex flex-wrap items-center gap-x-4 gap-y-1">
            {DOCUMENTOS_LEGALES.map((d) => <Link key={d.ruta} href={d.ruta} className="font-medium text-ink-600 hover:text-brand-700 hover:underline">{d.titulo}</Link>)}
            <BotonCookies className="font-medium text-ink-600 hover:text-brand-700 hover:underline" />
          </nav>
        </footer>
      </div>
    </div>
  );
}
