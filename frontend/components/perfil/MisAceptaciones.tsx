"use client";
import Link from "next/link";
import { FileCheck2 } from "lucide-react";
import { Badge, Card, CardBody, CardHeader } from "@/components/ui";
import { useApi } from "@/lib/hooks/queries";
import { legalService } from "@/lib/api/services";
import { fechaDia, hora } from "@/lib/utils";
import { LEGAL_VERSION } from "@/lib/legal.config";
import { BotonCookies } from "@/components/cookies/BotonCookies";

/** Transparencia: qué documentos aceptó la persona, en qué versión y cuándo. */
export function MisAceptaciones() {
  const historial = useApi(["legal-historial"], () => legalService.historial());
  const filas = historial.data ?? [];
  return (
    <Card>
      <CardHeader title="Privacidad y términos" action={<FileCheck2 className="h-5 w-5 text-ink-400" aria-hidden="true" />} />
      <CardBody className="space-y-4 text-sm text-ink-700">
        {filas.length === 0 ? (
          <p className="text-ink-500">Todavía no aceptaste los documentos vigentes.</p>
        ) : (
          <ul className="divide-y divide-ink-100 rounded-lg border border-ink-200">
            {filas.map((f) => (
              <li key={`${f.documento}-${f.version}`} className="flex flex-wrap items-center justify-between gap-2 px-3 py-2.5">
                <span className="font-medium text-ink-900">{f.documento_nombre}</span>
                <span className="flex items-center gap-2 text-xs text-ink-500">
                  versión {f.version} · {fechaDia(f.aceptado_en)} {hora(f.aceptado_en)}
                  {f.version === LEGAL_VERSION && <Badge tono="success">Vigente</Badge>}
                </span>
              </li>
            ))}
          </ul>
        )}
        <p className="flex flex-wrap items-center gap-x-4 gap-y-1 text-xs">
          <Link href="/terminos" className="font-medium text-brand-700 underline">Términos y condiciones</Link>
          <Link href="/privacidad" className="font-medium text-brand-700 underline">Política de privacidad</Link>
          <Link href="/cookies" className="font-medium text-brand-700 underline">Política de cookies</Link>
          <BotonCookies className="font-medium text-brand-700 underline" />
        </p>
        <p className="text-xs text-ink-500">Para pedir acceso, corrección o eliminación de tus datos, escribe a dubss@uagrm.edu.bo (ver la Política de privacidad).</p>
      </CardBody>
    </Card>
  );
}
