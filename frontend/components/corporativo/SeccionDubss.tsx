import { Clock, Mail, MapPin, Phone } from "lucide-react";
import { Logo } from "@/components/layout/Logo";
import { DUBSS } from "@/lib/corporativo.config";
import { CopiarBoton } from "./CopiarBoton";

function Fila({ icono, etiqueta, children, accion }: { icono: React.ReactNode; etiqueta: string; children: React.ReactNode; accion?: React.ReactNode }) {
  return (
    <div className="flex flex-wrap items-center justify-between gap-3 rounded-lg border border-ink-200 border-l-4 border-l-[#03662C] bg-white px-4 py-3">
      <div className="flex min-w-0 items-start gap-3">
        <span className="mt-0.5 text-[#03662C]" aria-hidden="true">{icono}</span>
        <div className="min-w-0">
          <span className="block text-xs font-medium uppercase tracking-wide text-ink-500">{etiqueta}</span>
          <span className="block break-words text-sm font-medium text-ink-900">{children}</span>
        </div>
      </div>
      {accion}
    </div>
  );
}

/** Dirección usuaria: datos públicos de la DUBSS, con su autorización para este proyecto. */
export function SeccionDubss() {
  return (
    <div className="grid gap-8 md:grid-cols-[18rem_1fr] md:items-start">
      <div className="flex flex-col items-center gap-3 text-center">
        <Logo size={200} className="shadow-pop ring-8 ring-brand-100" />
        <p className="text-sm font-semibold text-ink-900">{DUBSS.sigla} · UAGRM</p>
      </div>
      <div className="min-w-0 space-y-3">
        <Fila icono={<MapPin className="h-4 w-4" />} etiqueta="Dirección">{DUBSS.direccion}</Fila>
        <Fila icono={<Phone className="h-4 w-4" />} etiqueta="Teléfono" accion={<CopiarBoton texto={DUBSS.telefono} />}>{DUBSS.telefono}</Fila>
        <Fila icono={<Mail className="h-4 w-4" />} etiqueta="Correo" accion={<CopiarBoton texto={DUBSS.correo} />}>{DUBSS.correo}</Fila>
        <Fila icono={<Clock className="h-4 w-4" />} etiqueta="Horario de atención">{DUBSS.horario}</Fila>
        <div className="flex flex-wrap items-center gap-2 pt-1">
          <span className="mr-1 text-xs font-medium uppercase tracking-wide text-ink-500">Redes de la DUBSS</span>
          {DUBSS.redes.map((r) => (
            <a key={r.etiqueta} href={r.href} target="_blank" rel="noopener noreferrer"
              className="inline-flex h-8 items-center rounded-lg border border-ink-200 bg-white px-3 text-xs font-medium text-ink-800 transition-colors hover:bg-ink-50">
              {r.etiqueta}
            </a>
          ))}
        </div>
        <p className="text-xs text-ink-500">
          Datos y escudo usados con autorización de la DUBSS para este proyecto. Este sitio lo mantiene el proveedor del sistema y no es el sitio oficial de la DUBSS ni de la UAGRM.
        </p>
      </div>
    </div>
  );
}
