"use client";
import { RequireRole } from "@/components/layout/RequireRole";
import { ROLES_GESTION } from "@/lib/auth/roles";

export default function GestionLayout({ children }: { children: React.ReactNode }) {
  return <RequireRole roles={ROLES_GESTION}>{children}</RequireRole>;
}
