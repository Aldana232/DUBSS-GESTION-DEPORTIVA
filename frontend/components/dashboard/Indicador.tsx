import Link from "next/link";
import type { LucideIcon } from "lucide-react";
import { Card, CardBody } from "@/components/ui";

/** Tarjeta de cifra con ícono que lleva a su pantalla (inicios de gestión y de delegado). */
export function Indicador({ icono: Icono, etiqueta, valor, href }: { icono: LucideIcon; etiqueta: string; valor: number | string; href: string }) {
  return (
    <Link href={href} className="block rounded-xl focus-visible:ring-offset-ink-50">
      <Card className="transition-shadow hover:shadow-pop">
        <CardBody className="flex flex-col items-start gap-3 p-4 sm:flex-row sm:items-center sm:gap-4 sm:p-5">
          <span className="flex h-12 w-12 items-center justify-center rounded-xl bg-brand-50 text-brand-600"><Icono className="h-6 w-6" aria-hidden="true" /></span>
          <div><p className="text-sm text-ink-500">{etiqueta}</p><p className="text-2xl font-bold tabular-nums text-ink-900">{valor}</p></div>
        </CardBody>
      </Card>
    </Link>
  );
}

export const saludo = () => { const h = new Date().getHours(); return h < 12 ? "Buenos días" : h < 19 ? "Buenas tardes" : "Buenas noches"; };
