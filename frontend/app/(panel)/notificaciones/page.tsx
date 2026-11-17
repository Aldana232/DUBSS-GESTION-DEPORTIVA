"use client";
import { useState } from "react";
import { Bell, CheckCheck } from "lucide-react";
import { Button, Card, EmptyState, PageHeader, PageLoader } from "@/components/ui";
import { ItemNotificacion } from "@/components/notificaciones/ItemNotificacion";
import { useApi } from "@/lib/hooks/queries";
import { bandejaService } from "@/lib/api/services";
import { useBandeja } from "@/lib/hooks/useBandeja";

/** Bandeja completa de notificaciones del usuario (todos los roles). */
export default function PaginaNotificaciones() {
  const [soloNuevas, setSoloNuevas] = useState(false);
  const [pagina, setPagina] = useState(1);
  const datos = useApi(["bandeja", "pagina", soloNuevas, pagina], () => bandejaService.listar({ no_leidas: soloNuevas, page: pagina }));
  const { abrir, marcarTodas } = useBandeja();
  const filtro = (nuevas: boolean) => { setSoloNuevas(nuevas); setPagina(1); };
  const total = datos.data?.count ?? 0;
  const paginas = Math.max(1, Math.ceil(total / 20));

  return (
    <>
      <PageHeader title="Notificaciones" description="Recordatorios de partidos, cambios del calendario y avisos de la DUBSS."
        actions={<Button variant="secondary" icon={<CheckCheck className="h-4 w-4" />} onClick={() => void marcarTodas()}>Marcar todas como leídas</Button>} />
      <div className="mb-4 flex gap-2" role="tablist" aria-label="Filtro">
        {([["Todas", false], ["Sin leer", true]] as const).map(([t, v]) => (
          <button key={t} role="tab" type="button" aria-selected={soloNuevas === v} onClick={() => filtro(v)}
            className={`rounded-full border px-4 py-1.5 text-sm font-medium ${soloNuevas === v ? "border-brand-600 bg-brand-600 text-white" : "border-ink-200 bg-white text-ink-700 hover:bg-ink-50"}`}>{t}</button>
        ))}
      </div>
      {datos.isLoading ? <PageLoader /> : (datos.data?.results.length ?? 0) === 0 ? (
        <EmptyState icon={Bell} title={soloNuevas ? "No tienes notificaciones sin leer" : "Aún no tienes notificaciones"} description="Cuando haya un recordatorio o un cambio en tus partidos aparecerá aquí." />
      ) : (
        <Card className="overflow-hidden">
          <ul className="divide-y divide-ink-100">{datos.data?.results.map((n) => <li key={n.id}><ItemNotificacion n={n} onAbrir={(x) => void abrir(x)} /></li>)}</ul>
          {paginas > 1 && (
            <div className="flex items-center justify-between border-t border-ink-100 px-4 py-3 text-sm text-ink-600">
              <Button size="sm" variant="secondary" disabled={pagina <= 1} onClick={() => setPagina((p) => p - 1)}>Anterior</Button>
              <span>Página {pagina} de {paginas}</span>
              <Button size="sm" variant="secondary" disabled={pagina >= paginas} onClick={() => setPagina((p) => p + 1)}>Siguiente</Button>
            </div>
          )}
        </Card>
      )}
    </>
  );
}
