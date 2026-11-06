"use client";
import { useState, type ReactNode } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { LogIn, Menu, X } from "lucide-react";
import { cn } from "@/lib/utils";
import { useAuth } from "@/lib/hooks/useAuth";
import { ROLE_HOME } from "@/lib/auth/roles";
import { Logo } from "./Logo";

const ENLACES = [
  { href: "/", label: "Inicio" },
  { href: "/campeonatos", label: "Campeonatos" },
  { href: "/corporativo", label: "Producto" },
];

/** Cabecera y pie del sitio público (sin sesión obligatoria). */
export function PublicShell({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const { rol } = useAuth();
  const [abierto, setAbierto] = useState(false);
  const activo = (href: string) => (href === "/" ? pathname === "/" : pathname.startsWith(href));

  return (
    <div className="flex min-h-screen flex-col bg-ink-50">
      <a href="#contenido" className="sr-only focus:not-sr-only focus:fixed focus:left-3 focus:top-3 focus:z-[70] focus:rounded-lg focus:bg-white focus:px-4 focus:py-2 focus:shadow-pop">
        Saltar al contenido
      </a>
      <header className="sticky top-0 z-30 border-b border-white/5 bg-ink-900 text-white">
        <div className="mx-auto flex h-16 max-w-6xl items-center justify-between gap-4 px-4 sm:px-6">
          <Link href="/" className="flex items-center gap-3" aria-label="DUBSS, ir al inicio">
            <Logo size={40} />
            <span className="leading-tight">
              <span className="block text-base font-bold tracking-wide">D.U.B.S.S.</span>
              <span className="hidden text-[11px] uppercase tracking-wider text-ink-400 sm:block">Deportes universitarios</span>
            </span>
          </Link>

          <nav aria-label="Navegación pública" className="hidden items-center gap-1 md:flex">
            {ENLACES.map((e) => (
              <Link key={e.href} href={e.href} aria-current={activo(e.href) ? "page" : undefined}
                className={cn("rounded-lg px-3 py-2 text-sm font-medium transition-colors focus-visible:ring-offset-ink-900",
                  activo(e.href) ? "bg-white/10 text-white" : "text-ink-300 hover:bg-white/10 hover:text-white")}>
                {e.label}
              </Link>
            ))}
            <Link href={rol ? ROLE_HOME[rol] : "/login"}
              className="ml-2 inline-flex h-9 items-center gap-2 rounded-lg bg-brand-600 px-4 text-sm font-medium text-white transition-colors hover:bg-brand-500 focus-visible:ring-offset-ink-900">
              <LogIn className="h-4 w-4" aria-hidden="true" />
              {rol ? "Mi panel" : "Ingresar"}
            </Link>
          </nav>

          <button type="button" aria-label={abierto ? "Cerrar menú" : "Abrir menú"} aria-expanded={abierto}
            onClick={() => setAbierto((a) => !a)} className="rounded-lg p-2 text-ink-200 hover:bg-white/10 md:hidden focus-visible:ring-offset-ink-900">
            {abierto ? <X className="h-6 w-6" /> : <Menu className="h-6 w-6" />}
          </button>
        </div>
        {abierto && (
          <nav aria-label="Navegación pública" className="space-y-1 border-t border-white/10 px-4 py-3 md:hidden">
            {[...ENLACES, { href: rol ? ROLE_HOME[rol] : "/login", label: rol ? "Mi panel" : "Ingresar" }].map((e) => (
              <Link key={e.href + e.label} href={e.href} onClick={() => setAbierto(false)}
                className="block rounded-lg px-3 py-2.5 text-sm font-medium text-ink-200 hover:bg-white/10 hover:text-white">
                {e.label}
              </Link>
            ))}
          </nav>
        )}
      </header>

      <main id="contenido" tabIndex={-1} className="mx-auto w-full max-w-6xl flex-1 px-4 py-6 sm:px-6 lg:py-8">
        {children}
      </main>

      <footer className="border-t border-ink-200 bg-white">
        <div className="mx-auto flex max-w-6xl flex-col items-center justify-between gap-2 px-4 py-5 text-xs text-ink-500 sm:flex-row sm:px-6">
          <p>Dirección Universitaria de Bienestar Social y Salud — U.A.G.R.M.</p>
          <p className="flex flex-wrap items-center justify-center gap-x-3">
            <span>Santa Cruz de la Sierra, Bolivia</span>
            <Link href="/corporativo" className="font-medium text-brand-700 underline">Sitio corporativo</Link>
          </p>
        </div>
      </footer>
    </div>
  );
}
