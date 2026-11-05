"use client";
import { RequireRole } from "@/components/layout/RequireRole";
import { ROLES_ADMIN } from "@/lib/auth/roles";

export default function SoloAdminLayout({ children }: { children: React.ReactNode }) {
  return <RequireRole roles={ROLES_ADMIN}>{children}</RequireRole>;
}
