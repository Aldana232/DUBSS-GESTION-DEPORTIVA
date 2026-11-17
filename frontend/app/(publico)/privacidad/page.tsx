import type { Metadata } from "next";
import { DocumentoLegal } from "@/components/legal/DocumentoLegal";
import { PRIVACIDAD } from "@/lib/legal.contenido";

export const metadata: Metadata = {
  title: "Política de privacidad — DUBSS",
  description: "Qué datos personales trata el sistema de gestión deportiva de la DUBSS, para qué y cómo ejercer tus derechos.",
};

export default function PaginaPrivacidad() {
  return <DocumentoLegal documento={PRIVACIDAD} ruta="/privacidad" />;
}
