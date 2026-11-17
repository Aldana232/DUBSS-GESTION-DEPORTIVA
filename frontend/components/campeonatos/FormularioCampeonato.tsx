"use client";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Button, FormField, Input, Modal, Select, Textarea } from "@/components/ui";
import { useAccion, useCategorias, useErrorFormulario } from "@/lib/hooks/queries";
import { campeonatoService } from "@/lib/api/services";
import { aInputFechaHora, deInputFechaHora } from "@/lib/utils";
import type { Campeonato } from "@/types";

const entero = (min: number, max: number, texto: string) =>
  z.coerce.number({ error: "Indica un número." }).int("Debe ser un número entero.").min(min, texto).max(max, texto);

const esquema = z
  .object({
    nombre: z.string().trim().min(3, "El nombre debe tener al menos 3 caracteres.").max(200, "Máximo 200 caracteres."),
    categoria: z.coerce.number({ error: "Selecciona una categoría." }).int().positive("Selecciona una categoría."),
    formato: z.enum(["LIGA", "ELIMINACION"]),
    fecha_inicio: z.string().min(1, "Indica la fecha de inicio."),
    fecha_fin: z.string().min(1, "Indica la fecha de fin."),
    max_equipos: entero(2, 64, "Entre 2 y 64 equipos."),
    min_jugadores: entero(0, 99, "Entre 0 y 99."),
    max_jugadores: entero(1, 99, "Entre 1 y 99."),
    fecha_cierre_inscripcion: z.string().optional(),
    descripcion: z.string().max(1000, "Máximo 1000 caracteres.").optional(),
  })
  .refine((d) => !d.fecha_inicio || !d.fecha_fin || d.fecha_fin >= d.fecha_inicio, {
    path: ["fecha_fin"], message: "La fecha de fin no puede ser anterior al inicio.",
  })
  .refine((d) => d.min_jugadores <= d.max_jugadores, {
    path: ["min_jugadores"], message: "El mínimo no puede superar el máximo.",
  });
type Datos = z.output<typeof esquema>;
type Entrada = z.input<typeof esquema>;      // con zod 4 los campos «coerce» entran como `unknown`
const CAMPOS = ["nombre", "categoria", "formato", "fecha_inicio", "fecha_fin", "max_equipos", "min_jugadores", "max_jugadores", "fecha_cierre_inscripcion", "descripcion"] as const;

/** Alta y edición de campeonato. Con `campeonato` edita; sin él, crea. */
export function ModalCampeonato({ abierto, onCerrar, campeonato, onGuardado }: {
  abierto: boolean; onCerrar: () => void; campeonato?: Campeonato; onGuardado?: (id: number) => void;
}) {
  const categorias = useCategorias();
  const { register, handleSubmit, setError, reset, formState: { errors } } = useForm<Entrada, unknown, Datos>({
    resolver: zodResolver(esquema),
    defaultValues: campeonato ? {
      nombre: campeonato.nombre, categoria: campeonato.categoria, formato: campeonato.formato,
      fecha_inicio: campeonato.fecha_inicio, fecha_fin: campeonato.fecha_fin, max_equipos: campeonato.max_equipos,
      min_jugadores: campeonato.min_jugadores, max_jugadores: campeonato.max_jugadores,
      fecha_cierre_inscripcion: aInputFechaHora(campeonato.fecha_cierre_inscripcion), descripcion: campeonato.descripcion ?? "",
    } : { formato: "LIGA", max_equipos: 8, min_jugadores: 5, max_jugadores: 20 },
  });
  const alFallar = useErrorFormulario(setError, CAMPOS);
  const guardar = useAccion(
    (d: Datos) => {
      const cuerpo = { ...d, fecha_cierre_inscripcion: deInputFechaHora(d.fecha_cierre_inscripcion) };
      return campeonato ? campeonatoService.editar(campeonato.id, cuerpo) : campeonatoService.crear(cuerpo);
    },
    { invalidar: ["campeonatos", "campeonato"], exito: campeonato ? "Campeonato actualizado." : "Campeonato creado correctamente." },
  );

  const cerrar = () => { if (!campeonato) reset(); onCerrar(); };
  const enviar = (d: Datos) => guardar.ejecutar(d, { onSuccess: (c) => { cerrar(); onGuardado?.((c as Campeonato).id); }, onError: alFallar });

  return (
    <Modal open={abierto} onClose={cerrar} title={campeonato ? "Editar campeonato" : "Nuevo campeonato"} size="lg"
      footer={<>
        <Button variant="secondary" onClick={cerrar}>Cancelar</Button>
        <Button type="submit" form="form-campeonato" loading={guardar.pendiente}>{campeonato ? "Guardar cambios" : "Crear campeonato"}</Button>
      </>}>
      <form id="form-campeonato" onSubmit={handleSubmit(enviar)} noValidate className="grid gap-4 sm:grid-cols-2">
        <FormField label="Nombre" error={errors.nombre?.message} required className="sm:col-span-2">
          <Input placeholder="Ej.: Interfacultativo de Fútbol 2027" {...register("nombre")} />
        </FormField>
        <FormField label="Categoría" error={errors.categoria?.message} required>
          <Select {...register("categoria")}>
            <option value="">Selecciona...</option>
            {categorias.data?.results.map((c) => <option key={c.id} value={c.id}>{c.deporte_nombre} — {c.nombre} ({c.genero})</option>)}
          </Select>
        </FormField>
        <FormField label="Formato" error={errors.formato?.message} required>
          <Select {...register("formato")}>
            <option value="LIGA">Liga (todos contra todos)</option>
            <option value="ELIMINACION">Eliminación directa</option>
          </Select>
        </FormField>
        <FormField label="Fecha de inicio" error={errors.fecha_inicio?.message} required><Input type="date" {...register("fecha_inicio")} /></FormField>
        <FormField label="Fecha de fin" error={errors.fecha_fin?.message} required><Input type="date" {...register("fecha_fin")} /></FormField>
        <FormField label="Máximo de equipos" error={errors.max_equipos?.message} required><Input type="number" min={2} max={64} {...register("max_equipos")} /></FormField>
        <FormField label="Cierre de inscripciones" error={errors.fecha_cierre_inscripcion?.message} hint="Opcional. Debe ser anterior al inicio.">
          <Input type="datetime-local" {...register("fecha_cierre_inscripcion")} />
        </FormField>
        <FormField label="Mínimo de jugadores por equipo" error={errors.min_jugadores?.message}><Input type="number" min={0} {...register("min_jugadores")} /></FormField>
        <FormField label="Máximo de jugadores por equipo" error={errors.max_jugadores?.message}><Input type="number" min={1} {...register("max_jugadores")} /></FormField>
        <FormField label="Descripción" error={errors.descripcion?.message} className="sm:col-span-2"><Textarea {...register("descripcion")} /></FormField>
      </form>
    </Modal>
  );
}
