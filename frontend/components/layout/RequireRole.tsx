"use client";
import type { ReactNode } from "react";
import { ShieldAlert } from "lucide-react";
import { useAuth } from "@/lib/hooks/useAuth";
import type { Rol } from "@/lib/auth/roles";
import { EmptyState, PageLoader } from "@/components/ui";

/**
 * Muestra el contenido solo a los roles indicados. Es una ayuda de experiencia de usuario:
 * la API sigue rechazando con 403 a quien no corresponda.
 */
export function RequireRole({ roles, children, fallback }: { roles: Rol[]; children: ReactNode; fallback?: ReactNode }) {
  const { rol, loading } = useAuth();
  if (loading) return <PageLoader />;
  if (!rol || !roles.includes(rol)) {
    return <>{fallback ?? (
      <EmptyState icon={ShieldAlert} title="Acceso restringido" description="Tu rol no tiene permiso para ver esta sección." />
    )}</>;
  }
  return <>{children}</>;
}
