"use client";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Button, Checkbox, FormField, Input, Modal, Select, Textarea } from "@/components/ui";
import { RECURSOS_PARTIDO, useAccion, useErrorFormulario } from "@/lib/hooks/queries";
import { fixtureService } from "@/lib/api/services";
import type { DatosResultado, PartidoDetalle } from "@/types";

const numero = z.coerce.number({ error: "Ingresa un número." }).int("Debe ser entero.").min(0, "No puede ser negativo.").max(99, "Máximo 99.");
const opcional = z.preprocess((v) => (v === "" || v === null || Number.isNaN(v) ? undefined : v), numero.optional());

const esquema = z.object({
  goles_local: numero,
  goles_visitante: numero,
  penales_local: opcional,
  penales_visitante: opcional,
  walkover: z.boolean(),
  ganador_walkover: z.enum(["LOCAL", "VISITANTE"]).optional(),
  observaciones: z.string().max(500, "Máximo 500 caracteres.").optional(),
  motivo: z.string().optional(),
});
type Datos = z.output<typeof esquema>;
type Entrada = z.input<typeof esquema>;      // con zod 4 los campos «coerce» entran como `unknown`
const CAMPOS = ["goles_local", "goles_visitante", "penales_local", "penales_visitante", "ganador_walkover", "observaciones", "motivo", "detail", "non_field_errors"] as const;

export function ModalResultado({ partido, eliminacion, golesIncidencias, abierto, onCerrar }: {
  partido: PartidoDetalle;
  eliminacion: boolean;
  /** Goles por equipo según las incidencias ya registradas (el marcador debe coincidir). */
  golesIncidencias?: { local: number; visitante: number } | null;
  abierto: boolean;
  onCerrar: () => void;
}) {
  const r = partido.resultado;
  const corregir = !!r;
  const { register, handleSubmit, setError, watch, formState: { errors } } = useForm<Entrada, unknown, Datos>({
    resolver: zodResolver(esquema.superRefine((d, ctx) => {
      if (corregir && !d.motivo?.trim()) ctx.addIssue({ code: "custom", path: ["motivo"], message: "Indica el motivo de la corrección." });
      if (d.walkover && !d.ganador_walkover) ctx.addIssue({ code: "custom", path: ["ganador_walkover"], message: "Indica quién gana por W.O." });
    })),
    defaultValues: {
      goles_local: r?.goles_local ?? golesIncidencias?.local ?? 0,
      goles_visitante: r?.goles_visitante ?? golesIncidencias?.visitante ?? 0,
      penales_local: r?.penales_local ?? undefined,
      penales_visitante: r?.penales_visitante ?? undefined,
      walkover: r?.walkover ?? false,
      observaciones: r?.observaciones ?? "",
    },
  });
  const alFallar = useErrorFormulario(setError, CAMPOS);
  const guardar = useAccion(
    (d: DatosResultado) => (corregir ? fixtureService.corregirResultado(partido.id, d) : fixtureService.registrarResultado(partido.id, d)),
    { invalidar: RECURSOS_PARTIDO, exito: corregir ? "Resultado corregido." : "Resultado registrado." },
  );

  const wo = watch("walkover");
  const empate = Number(watch("goles_local")) === Number(watch("goles_visitante"));
  const local = partido.equipo_local_detalle?.nombre ?? "Local";
  const visitante = partido.equipo_visitante_detalle?.nombre ?? "Visitante";

  const enviar = (d: Datos) => {
    const base = { observaciones: d.observaciones, motivo: d.motivo };
    const datos: DatosResultado = d.walkover
      ? { ...base, walkover: true, ganador_walkover: d.ganador_walkover }
      : {
          ...base, walkover: false, goles_local: d.goles_local, goles_visitante: d.goles_visitante,
          ...(eliminacion && empate ? { penales_local: d.penales_local, penales_visitante: d.penales_visitante } : { penales_local: null, penales_visitante: null }),
        };
    guardar.ejecutar(datos, { onSuccess: onCerrar, onError: alFallar });
  };

  return (
    <Modal open={abierto} onClose={onCerrar} title={corregir ? "Corregir resultado" : "Registrar resultado"}
      footer={<>
        <Button variant="secondary" onClick={onCerrar}>Cancelar</Button>
        <Button type="submit" form="form-resultado" loading={guardar.pendiente}>{corregir ? "Guardar corrección" : "Confirmar resultado"}</Button>
      </>}>
      <form id="form-resultado" onSubmit={handleSubmit(enviar)} noValidate className="space-y-4">
        {errors.root?.message && <p role="alert" className="text-sm text-brand-700">{errors.root.message}</p>}
        <Checkbox label="Resultado administrativo (W.O.)" {...register("walkover")} />
        {wo ? (
          <FormField label="Equipo ganador por W.O." error={errors.ganador_walkover?.message} required>
            <Select {...register("ganador_walkover")} defaultValue="">
              <option value="" disabled>Selecciona...</option>
              <option value="LOCAL">{local}</option>
              <option value="VISITANTE">{visitante}</option>
            </Select>
          </FormField>
        ) : (
          <>
            {golesIncidencias && (golesIncidencias.local + golesIncidencias.visitante > 0) && (
              <p className="rounded-lg bg-ink-50 px-3 py-2 text-xs text-ink-600">
                Hay goles registrados en la planilla ({golesIncidencias.local} – {golesIncidencias.visitante}). El marcador debe coincidir con ellos.
              </p>
            )}
            <div className="grid grid-cols-2 gap-4">
              <FormField label={`Goles — ${local}`} error={errors.goles_local?.message}>
                <Input type="number" min={0} max={99} inputMode="numeric" className="h-14 text-center text-2xl font-bold" {...register("goles_local")} />
              </FormField>
              <FormField label={`Goles — ${visitante}`} error={errors.goles_visitante?.message}>
                <Input type="number" min={0} max={99} inputMode="numeric" className="h-14 text-center text-2xl font-bold" {...register("goles_visitante")} />
              </FormField>
            </div>
            {eliminacion && empate && (
              <div className="grid grid-cols-2 gap-4 rounded-lg bg-ink-50 p-3">
                <p className="col-span-2 text-xs text-ink-600">En eliminación directa el empate se define por penales.</p>
                <FormField label="Penales local" error={errors.penales_local?.message}><Input type="number" min={0} max={99} {...register("penales_local")} /></FormField>
                <FormField label="Penales visitante" error={errors.penales_visitante?.message}><Input type="number" min={0} max={99} {...register("penales_visitante")} /></FormField>
              </div>
            )}
          </>
        )}
        {corregir && (
          <FormField label="Motivo de la corrección" error={errors.motivo?.message} hint="Queda registrado en la bitácora." required>
            <Textarea rows={2} placeholder="Ej.: Error al transcribir el acta." {...register("motivo")} />
          </FormField>
        )}
        <FormField label="Observaciones" error={errors.observaciones?.message}>
          <Textarea rows={2} placeholder="Observaciones del partido (opcional)" {...register("observaciones")} />
        </FormField>
      </form>
    </Modal>
  );
}
