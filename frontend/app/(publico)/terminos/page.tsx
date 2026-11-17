import type { Metadata } from "next";
import { DocumentoLegal } from "@/components/legal/DocumentoLegal";
import { TERMINOS } from "@/lib/legal.contenido";

export const metadata: Metadata = {
  title: "Términos y condiciones — DUBSS",
  description: "Reglas de uso del sistema de gestión deportiva de la DUBSS: cuentas, roles, responsabilidades y límites de la inteligencia artificial.",
};

export default function PaginaTerminos() {
  return <DocumentoLegal documento={TERMINOS} ruta="/terminos" />;
}
