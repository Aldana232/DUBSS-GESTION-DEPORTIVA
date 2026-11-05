"use client";
import { useEffect } from "react";
import { usePathname, useRouter } from "next/navigation";
import { AppShell } from "@/components/layout/AppShell";
import { PageLoader } from "@/components/ui";
import { useAuth } from "@/lib/hooks/useAuth";

/** Todo lo que cuelga de este grupo exige sesión (gestión, delegado y perfil). */
export default function PanelLayout({ children }: { children: React.ReactNode }) {
  const { usuario, loading } = useAuth();
  const router = useRouter();
  const pathname = usePathname();

  useEffect(() => {
    if (!loading && !usuario) router.replace(`/login?redirect=${encodeURIComponent(pathname)}`);
  }, [loading, usuario, router, pathname]);

  if (loading || !usuario) {
    return <div className="flex min-h-screen items-center justify-center bg-ink-50"><PageLoader texto="Verificando sesión..." /></div>;
  }
  return <AppShell>{children}</AppShell>;
}
