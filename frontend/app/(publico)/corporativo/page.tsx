import type { Metadata } from "next";
import { SitioCorporativo } from "@/components/corporativo/SitioCorporativo";

export const metadata: Metadata = {
  title: "SportTech DUBSS — Sitio corporativo",
  description: "Plataforma de gestión deportiva universitaria desarrollada para la Dirección Universitaria de Bienestar Social y Salud (UAGRM).",
};

export default function PaginaCorporativa() {
  return <SitioCorporativo />;
}
