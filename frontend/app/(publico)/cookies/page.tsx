import type { Metadata } from "next";
import { DocumentoLegal } from "@/components/legal/DocumentoLegal";
import { COOKIES } from "@/lib/legal.contenido";

export const metadata: Metadata = {
  title: "Política de cookies — DUBSS",
  description: "Qué cookies y almacenamiento local usa el sistema de la DUBSS, para qué sirve cada uno y cómo elegir.",
};

export default function PaginaCookies() {
  return <DocumentoLegal documento={COOKIES} ruta="/cookies" />;
}
