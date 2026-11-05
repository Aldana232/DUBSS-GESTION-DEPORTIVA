"use client";
import { useEffect, useState } from "react";
import { Layers, Network, Sparkles, TriangleAlert } from "lucide-react";
import { Badge, Button, Card, CardBody, CardHeader, EmptyState, FormField, Select } from "@/components/ui";
import { BarraProgreso } from "@/components/dashboard/graficos";
import { SelectorCampeonato } from "@/components/SelectorCampeonato";
import { useAccion, useCampeonatos } from "@/lib/hooks/queries";
import { mlService } from "@/lib/api/services";
import { cn } from "@/lib/utils";
import type { AnalisisNiveles, EquipoNivel } from "@/types";

const TONOS = [
  { barra: "fill-brand-600", chip: "bg-brand-50 text-brand-700 ring-brand-200", punto: "bg-brand-600" },
  { barra: "fill-amber-500", chip: "bg-amber-50 text-amber-800 ring-amber-200", punto: "bg-amber-500" },
  { barra: "fill-sky-500", chip: "bg-sky-50 text-sky-700 ring-sky-200", punto: "bg-sky-500" },
  { barra: "fill-ink-400", chip: "bg-ink-100 text-ink-700 ring-ink-200", punto: "bg-ink-400" },
];
const tono = (nivel: number | null) => TONOS[Math.min((nivel ?? 4) - 1, 3)];

function FilaEquipo({ e, esCabeza, etiquetaNivel }: { e: EquipoNivel; esCabeza: boolean; etiquetaNivel?: string }) {
  const t = tono(e.nivel);
  return (
    <tr className="border-t border-ink-100">
      <td className="py-2.5 pl-3 pr-2 text-center"><span className={cn("inline-flex h-7 w-7 items-center justify-center rounded-full text-xs font-bold", esCabeza ? "bg-ink-900 text-white" : "bg-ink-100 text-ink-700")}>{e.semilla}</span></td>
      <td className="py-2.5 pr-3"><p className="font-semibold text-ink-900">{e.nombre}</p><p className="text-xs text-ink-500">{e.sigla}</p></td>
      <td className="py-2.5 pr-3">
        {e.nivel ? <span className={cn("inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ring-1 ring-inset", t.chip)}>{etiquetaNivel ?? `Nivel ${e.nivel}`}</span> : <Badge tono="warning">Sin historial</Badge>}
      </td>
      <td className="hidden w-44 py-2.5 pr-3 sm:table-cell">{e.fuerza !== null ? (<div className="flex items-center gap-2"><div className="flex-1"><BarraProgreso valor={e.fuerza} maximo={100} etiqueta={`Fuerza de ${e.nombre}`} clase={t.barra} /></div><span className="w-8 text-right text-xs font-bold tabular-nums text-ink-700">{Math.round(e.fuerza)}</span></div>) : <span className="text-xs text-ink-400">—</span>}</td>
      <td className="hidden py-2.5 pr-3 text-right tabular-nums text-ink-600 md:table-cell">{e.partidos}</td>
      <td className="hidden py-2.5 pr-3 text-right tabular-nums text-ink-600 md:table-cell">{e.ppp ?? "—"}</td>
      <td className="hidden py-2.5 pr-3 text-right tabular-nums text-ink-600 md:table-cell">{e.dg_pp !== null ? (e.dg_pp > 0 ? `+${e.dg_pp}` : e.dg_pp) : "—"}</td>
    </tr>
  );
}

/** F7-07 — Agrupa a los equipos por rendimiento real (K-means) y propone siembra, cabezas de serie y grupos equilibrados. */
export function NivelesEquipos() {
  const campeonatos = useCampeonatos();
  const [campeonato, setCampeonato] = useState("");
  const [grupos, setGrupos] = useState("");
  const [analisis, setAnalisis] = useState<AnalisisNiveles | null>(null);

  useEffect(() => {
    if (campeonato || !campeonatos.data) return;
    const sugerido = campeonatos.data.results.find((c) => c.formato === "ELIMINACION" && c.estado === "INSCRIPCION_CERRADA") ?? campeonatos.data.results[0];
    if (sugerido) setCampeonato(String(sugerido.id));
  }, [campeonato, campeonatos.data]);

  const analizar = useAccion(() => mlService.cabezasDeSerie(Number(campeonato), grupos ? Number(grupos) : undefined), { error: "No se pudo analizar el campeonato." });
  const nombres = new Map(analisis?.equipos.map((e) => [e.equipo_id, e]) ?? []);

  return (
    <div className="space-y-5">
      <Card>
        <CardHeader title={<span className="inline-flex items-center gap-2"><Layers className="h-4 w-4 text-brand-600" aria-hidden="true" />Niveles y siembra de equipos</span>} />
        <CardBody className="space-y-4">
          <p className="text-sm text-ink-600">
            La IA agrupa a los equipos inscritos según su rendimiento real (puntos por partido, diferencia de goles y forma reciente) para sembrar la llave de eliminación directa y armar grupos parejos.
            No modifica nada: al generar el fixture puedes activar la siembra con IA.
          </p>
          <div className="flex flex-wrap items-end gap-3">
            <FormField label="Campeonato"><SelectorCampeonato valor={campeonato} onCambiar={(v) => { setCampeonato(v); setAnalisis(null); }} vacio="Selecciona..." /></FormField>
            <FormField label="Grupos a proponer">
              <Select value={grupos} onChange={(e) => setGrupos(e.target.value)} className="w-40">
                <option value="">Automático</option>{[2, 3, 4, 6, 8].map((n) => <option key={n} value={n}>{n} grupos</option>)}
              </Select>
            </FormField>
            <Button disabled={!campeonato} loading={analizar.pendiente} icon={<Sparkles className="h-4 w-4" />} onClick={() => analizar.ejecutar(undefined, { onSuccess: setAnalisis })}>Analizar equipos</Button>
          </div>
        </CardBody>
      </Card>

      {!analisis ? (
        <EmptyState icon={Network} title="Elige un campeonato y analiza" description="Verás los niveles de rendimiento, el orden de siembra y la propuesta de grupos." />
      ) : (
        <>
          <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
            {[
              ["Equipos", String(analisis.equipos_total)],
              ["Método", analisis.metodo === "kmeans" ? "K-means" : "Orden de inscripción"],
              ["Niveles", analisis.k ? String(analisis.k) : "—"],
              ["Calidad del agrupamiento", analisis.silueta !== null ? `${analisis.silueta.toFixed(2)} (silueta)` : "—"],
            ].map(([t, v]) => (
              <Card key={t}><CardBody className="p-4"><p className="text-xs text-ink-500">{t}</p><p className="text-xl font-bold text-ink-900">{v}</p></CardBody></Card>
            ))}
          </div>

          <p role="status" className={cn("flex items-start gap-2 rounded-xl p-3.5 text-sm", analisis.datos_suficientes ? "bg-emerald-50 text-emerald-900" : "bg-amber-50 text-amber-900")}>
            {analisis.datos_suficientes ? <Sparkles className="mt-0.5 h-4 w-4 shrink-0" aria-hidden="true" /> : <TriangleAlert className="mt-0.5 h-4 w-4 shrink-0" aria-hidden="true" />}
            {analisis.motivo}
          </p>

          {analisis.niveles.length > 0 && (
            <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
              {analisis.niveles.map((n) => (
                <Card key={n.nivel}>
                  <CardBody className="space-y-2 p-4">
                    <div className="flex items-center justify-between"><span className={cn("inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold ring-1 ring-inset", tono(n.nivel).chip)}>{n.etiqueta}</span><span className="text-xs text-ink-500">Fuerza media {Math.round(n.fuerza_media)}</span></div>
                    <ul className="space-y-1 text-sm text-ink-800">{n.equipos.map((id) => <li key={id} className="flex items-center gap-2"><span className={cn("h-2 w-2 rounded-full", tono(n.nivel).punto)} aria-hidden="true" />{nombres.get(id)?.nombre}</li>)}</ul>
                  </CardBody>
                </Card>
              ))}
            </div>
          )}

          <Card>
            <CardHeader title={`Orden de siembra${analisis.cabezas_de_serie.length ? ` · ${analisis.cabezas_de_serie.length} cabezas de serie` : ""}`} />
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm">
                <thead className="text-xs text-ink-500"><tr>
                  <th className="px-3 py-2 text-center">Semilla</th><th className="py-2 pr-3">Equipo</th><th className="py-2 pr-3">Nivel</th>
                  <th className="hidden py-2 pr-3 sm:table-cell">Fuerza</th><th className="hidden py-2 pr-3 text-right md:table-cell">PJ</th>
                  <th className="hidden py-2 pr-3 text-right md:table-cell">Pts/PJ</th><th className="hidden py-2 pr-3 text-right md:table-cell">DG/PJ</th>
                </tr></thead>
                <tbody>{analisis.equipos.map((e) => <FilaEquipo key={e.equipo_id} e={e} esCabeza={analisis.cabezas_de_serie.includes(e.equipo_id)} etiquetaNivel={analisis.niveles.find((n) => n.nivel === e.nivel)?.etiqueta} />)}</tbody>
              </table>
            </div>
          </Card>

          {analisis.grupos.length > 1 && (
            <section aria-label="Grupos equilibrados">
              <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
                <h3 className="text-sm font-bold text-ink-900">Grupos equilibrados (reparto en serpiente)</h3>
                {analisis.balance && <Badge tono={analisis.balance.diferencia_max <= 10 ? "success" : "warning"}>Diferencia máxima de fuerza: {analisis.balance.diferencia_max}</Badge>}
              </div>
              <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
                {analisis.grupos.map((g) => (
                  <Card key={g.nombre}><CardBody className="space-y-2 p-4">
                    <div className="flex items-center justify-between"><p className="font-bold text-ink-900">{g.nombre}</p>{g.fuerza_media !== null && <span className="text-xs text-ink-500">Fuerza media {Math.round(g.fuerza_media)}</span>}</div>
                    <ul className="space-y-1 text-sm text-ink-700">{g.equipos.map((id) => <li key={id} className="flex items-center gap-2"><span className={cn("h-2 w-2 rounded-full", tono(nombres.get(id)?.nivel ?? null).punto)} aria-hidden="true" />{nombres.get(id)?.nombre}</li>)}</ul>
                  </CardBody></Card>
                ))}
              </div>
            </section>
          )}
        </>
      )}
    </div>
  );
}
