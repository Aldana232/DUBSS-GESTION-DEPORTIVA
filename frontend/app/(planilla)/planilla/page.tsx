import type { Metadata } from "next";
import { PlanillaApp } from "@/components/planilla/PlanillaApp";

export const metadata: Metadata = { title: "Planilla — DUBSS" };

export default function PaginaPlanilla() {
  return <PlanillaApp />;
}
