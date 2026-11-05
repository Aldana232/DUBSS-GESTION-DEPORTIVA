"use client";
import { useState } from "react";
import { Check, ScanSearch, ShieldCheck, TriangleAlert } from "lucide-react";
import { Badge, Button, Card, CardBody, CardHeader, Checkbox, EmptyState, PageLoader } from "@/components/ui";
import { BarraProgreso } from "@/components/dashboard/graficos";
import { useAccion, useApi } from "@/lib/hooks/queries";
import { useAuth } from "@/lib/hooks/useAuth";
import { mlService } from "@/lib/api/services";
import { fechaCorta } from "@/lib/utils";

/** F7-08 — Marcadores raros según Isolation Forest, con la explicación de por qué. Son alertas para revisar, no correcciones. */
export function ResultadosAtipicos() {
  const { esAdmin } = useAuth();
  const [verRevisados, setVerRevisados] = useState(false);
  const { data, isLoading } = useApi(["atipicos", verRevisados], () => mlService.atipicos(verRevisados ? undefined : false));
  const buscar = useAccion(() => mlService.buscarAtipicos(), {
    invalidar: ["atipicos"], exito: (r) => (r.nuevos ? `Se encontraron ${r.nuevos} resultado(s) atípico(s) nuevo(s).` : "No hay resultados atípicos nuevos."), error: "No se pudo analizar los resultados.",
  });
  const revisar = useAccion((id: number) => mlService.revisarAtipico(id), { invalidar: ["atipicos"], exito: "Alerta marcada como revisada.", error: "No se pudo marcar como revisada." });

  return (
    <Card>
      <CardHeader
        title={<span className="inline-flex items-center gap-2"><ScanSearch className="h-4 w-4 text-brand-600" aria-hidden="true" />Resultados atípicos{data && data.pendientes > 0 && <Badge tono="danger">{data.pendientes} por revisar</Badge>}</span>}
        action={esAdmin && <Button size="sm" variant="secondary" loading={buscar.pendiente} icon={<ScanSearch className="h-4 w-4" />} onClick={() => buscar.ejecutar(undefined)}>Buscar ahora</Button>}
      />
      <CardBody className="space-y-4">
        <p className="text-sm text-ink-600">
          El sistema aprende cómo son los marcadores habituales de cada deporte y señala los que se salen mucho (por ejemplo, un error de digitación). Solo avisa cuando puede explicarlo; la revisión siempre es humana.
        </p>
        <Checkbox label="Mostrar también las ya revisadas" checked={verRevisados} onChange={(e) => setVerRevisados(e.target.checked)} />
        {isLoading ? <PageLoader /> : !data || data.resultados.length === 0 ? (
          <EmptyState icon={ShieldCheck} title="Sin resultados atípicos" description="Todos los marcadores registrados están dentro de lo habitual." />
        ) : (
          <ul className="space-y-3">
            {data.resultados.map((a) => (
              <li key={a.id} className="flex flex-col gap-4 rounded-2xl border border-ink-200 p-4 sm:flex-row sm:items-center">
                <div className="flex shrink-0 flex-col items-center rounded-xl bg-ink-900 px-5 py-3 text-white">
                  <span className="text-2xl font-black tabular-nums">{a.marcador}</span>
                  <span className="text-[11px] uppercase tracking-wider text-ink-300">marcador</span>
                </div>
                <div className="min-w-0 flex-1 space-y-1.5">
                  <p className="font-semibold text-ink-900">{a.partido}</p>
                  <p className="text-xs text-ink-500">{a.campeonato} · {fechaCorta(a.fecha)}</p>
                  <p className="flex items-start gap-1.5 text-sm text-ink-700"><TriangleAlert className="mt-0.5 h-4 w-4 shrink-0 text-amber-600" aria-hidden="true" />{a.motivo}</p>
                  <div className="flex items-center gap-2 pt-1 text-xs text-ink-500"><span>Índice de anomalía</span><div className="w-32"><BarraProgreso valor={Math.round(a.puntaje * 100)} maximo={100} etiqueta="Índice de anomalía" clase="fill-amber-500" /></div><span className="tabular-nums font-semibold text-ink-700">{Math.round(a.puntaje * 100)}</span></div>
                </div>
                {a.revisado ? <Badge tono="success"><Check className="mr-1 h-3 w-3" aria-hidden="true" />Revisado</Badge>
                  : <Button size="sm" variant="secondary" loading={revisar.pendiente} icon={<Check className="h-4 w-4" />} onClick={() => revisar.ejecutar(a.id)}>Marcar revisado</Button>}
              </li>
            ))}
          </ul>
        )}
      </CardBody>
    </Card>
  );
}
