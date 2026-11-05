"use client";
import { useCallback } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { authService } from "@/lib/api/services";
import { PERMISOS_POR_ROL, type Permiso } from "@/lib/auth/roles";

/** Sesión actual. El usuario viene de /api/auth/session (los tokens viven en cookies httpOnly). */
export function useAuth() {
  const qc = useQueryClient();
  const { data: usuario = null, isLoading } = useQuery({
    queryKey: ["sesion"],
    queryFn: authService.sesion,
    staleTime: 60_000,
    retry: false,
  });

  const rol = usuario?.rol ?? null;
  const can = useCallback(
    (permiso: Permiso) => (rol ? PERMISOS_POR_ROL[rol].includes(permiso) : false),
    [rol],
  );

  const logout = useCallback(async () => {
    await authService.logout();
    qc.clear();
    window.location.href = "/login";
  }, [qc]);

  const esSuperadmin = rol === "SUPERADMIN";
  const esAdmin = rol === "ADMIN_DUBSS" || esSuperadmin;
  const esOrganizador = rol === "ORGANIZADOR";

  return {
    usuario,
    rol,
    facultad: usuario?.facultad ?? null,
    loading: isLoading,
    can,
    logout,
    esSuperadmin,
    esAdmin,
    esOrganizador,
    esDelegado: rol === "DELEGADO",
    esGestion: esAdmin || esOrganizador,
  };
}
