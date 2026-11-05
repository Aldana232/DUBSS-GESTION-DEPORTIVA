"use client";
import { useState } from "react";
import { AlertTriangle, BrainCircuit, CheckCircle2, Layers } from "lucide-react";
import { Button, Checkbox, FormField, Input, Modal } from "@/components/ui";
import { PanelCalidad } from "@/components/fixture/PanelCalidad";
import { useAccion } from "@/lib/hooks/queries";
import { fixtureService } from "@/lib/api/services";
import { mensajeDeError } from "@/lib/api/errors";
import type { Campeonato, ResumenGeneracion } from "@/types";

const RECURSOS = ["partidos", "partido", "tabla", "historial", "campeonato", "estadisticas", "calidad"];

/** Confirmación + parámetros para generar el fixture (con o sin ML); al terminar muestra la calidad obtenida. */
export function ModalGenerarFixture({ campeonato, partidosExistentes, abierto, onCerrar }: {
  campeonato: Campeonato; partidosExistentes: number; abierto: boolean; onCerrar: () => void;
}) {
  const [horaInicio, setHoraInicio] = useState("08:00");
  const [dias, setDias] = useState("7");
  const [dobleVuelta, setDobleVuelta] = useState(false);
  const [usarMl, setUsarMl] = useState(true);
  const [sembrar, setSembrar] = useState(true);
  const [error, setError] = useState("");
  const [resumen, setResumen] = useState<ResumenGeneracion | null>(null);
  const generar = useAccion(
    () => fixtureService.generar(campeonato.id, {
      hora_inicio: horaInicio, dias_entre_jornadas: Number(dias) || 7, usar_ml: usarMl,
      doble_vuelta: campeonato.formato === "LIGA" ? dobleVuelta : undefined,
      sembrar_con_ml: campeonato.formato === "ELIMINACION" ? sembrar : undefined,
    }),
    { invalidar: RECURSOS, exito: (r) => `Fixture generado: ${r.total_partidos} partidos${r.generado_por_ml ? " (optimizado con ML)" : ""}.` },
  );
  const confirmar = () => {
    setError("");
    generar.ejecutar(undefined, { onSuccess: setResumen, onError: (e) => setError(mensajeDeError(e, "No se pudo generar el fixture.")) });
  };
  const cerrar = () => { setResumen(null); setError(""); onCerrar(); };

  if (resumen) {
    return (
      <Modal open={abierto} onClose={cerrar} title="Fixture generado" size="md" footer={<Button onClick={cerrar}>Revisar el fixture</Button>}>
        <div className="space-y-4">
          <p className="flex items-start gap-2 text-sm text-ink-700">
            <CheckCircle2 className="mt-0.5 h-5 w-5 shrink-0 text-emerald-600" aria-hidden="true" />
            Se programaron {resumen.total_partidos} partidos
            {resumen.generado_por_ml ? " con el optimizador de ML." : " con el método base."} Revísalos y, si están bien, inicia el campeonato para publicarlos.
          </p>
          {resumen.aviso && (
            <p role="alert" className="flex gap-2 rounded-lg border border-amber-200 bg-amber-50 p-3 text-sm text-amber-900">
              <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" aria-hidden="true" />{resumen.aviso}
            </p>
          )}
          {resumen.siembra && (
            <div className={resumen.siembra.aplicada ? "rounded-lg border border-emerald-200 bg-emerald-50 p-3 text-sm text-emerald-900" : "rounded-lg border border-amber-200 bg-amber-50 p-3 text-sm text-amber-900"}>
              <p className="flex items-start gap-2 font-semibold"><Layers className="mt-0.5 h-4 w-4 shrink-0" aria-hidden="true" />{resumen.siembra.aplicada ? "Llave sembrada con IA por nivel de rendimiento" : "Siembra con IA no aplicada"}</p>
              <p className="mt-1 text-xs">{resumen.siembra.motivo}</p>
              {resumen.siembra.aplicada && resumen.siembra.orden && (
                <ol className="mt-2 grid gap-x-4 gap-y-0.5 text-xs sm:grid-cols-2">{resumen.siembra.orden.map((o) => <li key={o.semilla}><b className="tabular-nums">{o.semilla}.</b> {o.equipo}</li>)}</ol>
              )}
            </div>
          )}
          {resumen.calidad && <PanelCalidad calidad={resumen.calidad} ml={resumen.ml} />}
        </div>
      </Modal>
    );
  }

  return (
    <Modal open={abierto} onClose={cerrar} title="Generar fixture" size="sm"
      footer={<><Button variant="secondary" onClick={cerrar}>Cancelar</Button><Button loading={generar.pendiente} onClick={confirmar}>{partidosExistentes ? "Regenerar fixture" : "Generar fixture"}</Button></>}>
      <div className="space-y-4">
        <p className="text-sm text-ink-600">Se programan los partidos con los equipos de inscripción aprobada, respetando canchas, horarios, bloqueos y restricciones de facultad.</p>
        {partidosExistentes > 0 && (
          <p className="flex gap-2 rounded-lg border border-amber-200 bg-amber-50 p-3 text-sm text-amber-900">
            <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" aria-hidden="true" />
            Se reemplazarán los {partidosExistentes} partidos actuales. Si alguno ya tiene resultado, el sistema no lo permitirá.
          </p>
        )}
        <label className="flex cursor-pointer items-start gap-3 rounded-lg border border-brand-200 bg-brand-50/50 p-3">
          <input type="checkbox" checked={usarMl} onChange={(e) => setUsarMl(e.target.checked)} className="mt-1 h-4 w-4 rounded border-ink-300 accent-brand-600" />
          <span className="text-sm">
            <span className="flex items-center gap-1.5 font-semibold text-ink-900"><BrainCircuit className="h-4 w-4 text-brand-600" aria-hidden="true" />Optimizar con Machine Learning</span>
            <span className="text-ink-600">Un modelo Random Forest puntúa cada horario y el optimizador elige los mejores sin conflictos. Si no encuentra solución, usa el método base y te avisa.</span>
          </span>
        </label>
        {campeonato.formato === "ELIMINACION" && (
          <label className="flex cursor-pointer items-start gap-3 rounded-lg border border-sky-200 bg-sky-50/60 p-3">
            <input type="checkbox" checked={sembrar} onChange={(e) => setSembrar(e.target.checked)} className="mt-1 h-4 w-4 rounded border-ink-300 accent-brand-600" />
            <span className="text-sm">
              <span className="flex items-center gap-1.5 font-semibold text-ink-900"><Layers className="h-4 w-4 text-sky-700" aria-hidden="true" />Sembrar la llave con IA</span>
              <span className="text-ink-600">Agrupa a los equipos por rendimiento real para que los mejores no se crucen en las primeras rondas. Sin historial suficiente se usa el orden de inscripción y se avisa.</span>
            </span>
          </label>
        )}
        <FormField label="Hora del primer partido del día"><Input type="time" value={horaInicio} onChange={(e) => setHoraInicio(e.target.value)} /></FormField>
        <FormField label="Días entre jornadas"><Input type="number" min={1} value={dias} onChange={(e) => setDias(e.target.value)} /></FormField>
        {campeonato.formato === "LIGA" && <Checkbox label="Doble vuelta (ida y vuelta)" checked={dobleVuelta} onChange={(e) => setDobleVuelta(e.target.checked)} />}
        {error && <p role="alert" className="rounded-lg border border-brand-200 bg-brand-50 p-3 text-sm text-brand-800">{error}</p>}
      </div>
    </Modal>
  );
}
