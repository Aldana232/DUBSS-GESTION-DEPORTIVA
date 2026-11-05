/** La planilla móvil tiene su propio marco (sin barra lateral): es una app táctil de pantalla completa. */
export default function PlanillaLayout({ children }: { children: React.ReactNode }) {
  return <div className="min-h-screen bg-ink-50">{children}</div>;
}
