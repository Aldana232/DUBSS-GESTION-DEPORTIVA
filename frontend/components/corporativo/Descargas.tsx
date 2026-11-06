import { Download, ExternalLink, FileText, Smartphone } from "lucide-react";
import { Badge, Card } from "@/components/ui";
import { EMPRESA } from "@/lib/corporativo.config";

function Accion({ href, children, primario }: { href: string; children: React.ReactNode; primario?: boolean }) {
  const clases = "inline-flex h-10 items-center justify-center gap-2 rounded-lg px-4 text-sm font-medium transition-colors";
  if (!href) return <span aria-disabled="true" className={`${clases} cursor-not-allowed border border-ink-200 bg-ink-100 text-ink-500`}>{children}</span>;
  return (
    <a href={href} target="_blank" rel="noopener noreferrer"
      className={`${clases} ${primario ? "bg-brand-600 text-white hover:bg-brand-700" : "border border-ink-200 bg-white text-ink-800 hover:bg-ink-50"}`}>
      {children}
    </a>
  );
}

export function Descargas() {
  return (
    <div className="grid gap-4 md:grid-cols-3">
      <Card className="flex flex-col gap-3 p-5">
        <FileText className="h-6 w-6 text-brand-600" aria-hidden="true" />
        <h3 className="font-semibold text-ink-900">Ficha técnica</h3>
        <p className="flex-1 text-sm text-ink-600">Resumen de funciones, tecnologías, requisitos y seguridad del sistema.</p>
        <Badge tono="neutral">PDF · 2 páginas</Badge>
        <Accion href={EMPRESA.fichaUrl} primario><Download className="h-4 w-4" aria-hidden="true" />Abrir la ficha (PDF)</Accion>
      </Card>
      <Card className="flex flex-col gap-3 p-5">
        <FileText className="h-6 w-6 text-brand-600" aria-hidden="true" />
        <h3 className="font-semibold text-ink-900">Manual de usuario</h3>
        <p className="flex-1 text-sm text-ink-600">Guía paso a paso por rol: Superadministrador, Administrador, Organizador, Delegado y Jugador.</p>
        {!EMPRESA.manualUrl && <Badge tono="warning">Manual por publicar</Badge>}
        <Accion href={EMPRESA.manualUrl}><Download className="h-4 w-4" aria-hidden="true" />Descargar manual</Accion>
      </Card>
      <Card className="flex flex-col gap-3 p-5">
        <Smartphone className="h-6 w-6 text-brand-600" aria-hidden="true" />
        <h3 className="font-semibold text-ink-900">Aplicación web (PWA)</h3>
        <p className="flex-1 text-sm text-ink-600">Se instala desde el navegador del celular o la computadora, sin tienda de aplicaciones.</p>
        <Badge tono="success">Instalable desde el navegador</Badge>
        <Accion href={EMPRESA.appUrl || "/login"} primario><ExternalLink className="h-4 w-4" aria-hidden="true" />Abrir la plataforma</Accion>
      </Card>
    </div>
  );
}
