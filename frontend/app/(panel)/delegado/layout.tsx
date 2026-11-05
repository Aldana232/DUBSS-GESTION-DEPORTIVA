"use client";
import { RequireRole } from "@/components/layout/RequireRole";

export default function DelegadoLayout({ children }: { children: React.ReactNode }) {
  return <RequireRole roles={["DELEGADO"]}>{children}</RequireRole>;
}
