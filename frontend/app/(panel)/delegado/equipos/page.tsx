"use client";
import { useState } from "react";
import Link from "next/link";
import { ChevronRight, Pencil, Plus, Shield, Users } from "lucide-react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Button, EmptyState, FormField, Input, Modal, PageHeader, PageLoader } from "@/components/ui";
import { useAccion, useErrorFormulario, useMisEquipos } from "@/lib/hooks/queries";
import { useAuth } from "@/lib/hooks/useAuth";
import { equipoService } from "@/lib/api/services";
import type { Equipo } from "@/types";

const esquema = z.object({
  nombre: z.string().trim().min(2, "El nombre debe tener al menos 2 caracteres.").max(150, "Máximo 150 caracteres."),
  color: z.string().regex(/^#[0-9a-fA-F]{6}$/, "Elige un color válido."),
});
type Datos = z.infer<typeof esquema>;
const CAMPOS = ["nombre", "color", "facultad", "detail", "non_field_errors"] as const;

function ModalEquipo({ equipo, facultad, onCerrar }: { equipo?: Equipo; facultad: number | null; onCerrar: () => void }) {
  const { register, handleSubmit, setError, formState: { errors } } = useForm<Datos>({
    resolver: zodResolver(esquema), defaultValues: { nombre: equipo?.nombre ?? "", color: equipo?.color ?? "#d21115" },
  });
  const alFallar = useErrorFormulario(setError, CAMPOS);
  const guardar = useAccion(
    (d: Datos) => (equipo ? equipoService.editar(equipo.id, d) : equipoService.crear({ ...d, facultad: facultad ?? 0 })),
    { invalidar: ["mis-equipos", "equipos"], exito: equipo ? "Equipo actualizado." : "Equipo creado." },
  );
  return (
    <Modal open onClose={onCerrar} title={equipo ? "Editar equipo" : "Nuevo equipo"} size="sm"
      footer={<><Button variant="secondary" onClick={onCerrar}>Cancelar</Button><Button type="submit" form="form-equipo" loading={guardar.pendiente}>Guardar</Button></>}>
      <form id="form-equipo" noValidate onSubmit={handleSubmit((d) => guardar.ejecutar(d, { onSuccess: onCerrar, onError: alFallar }))} className="space-y-4">
        {(errors.root?.message || (errors as Record<string, { message?: string }>).detail?.message) && (
          <p role="alert" className="text-sm text-brand-700">{(errors as Record<string, { message?: string }>).detail?.message}</p>
        )}
        <FormField label="Nombre del equipo" error={errors.nombre?.message} required><Input placeholder="Ej.: Ingeniería Fútbol" {...register("nombre")} /></FormField>
        <FormField label="Color del equipo" error={errors.color?.message}><Input type="color" className="h-10 w-20 p-1" {...register("color")} /></FormField>
      </form>
    </Modal>
  );
}

export default function MisEquipos() {
  const { facultad } = useAuth();
  const { data, isLoading } = useMisEquipos();
  const [modal, setModal] = useState<{ equipo?: Equipo } | null>(null);

  return (
    <>
      <PageHeader title="Mis equipos" description="Equipos de tu facultad. Entra a uno para administrar su plantel."
        actions={<Button icon={<Plus className="h-4 w-4" />} onClick={() => setModal({})}>Nuevo equipo</Button>} />
      {isLoading && <PageLoader />}
      <ul className="grid gap-4 md:grid-cols-2">
        {data?.map((e) => (
          <li key={e.id} className="flex items-center gap-4 rounded-xl border border-ink-200 bg-white p-5 shadow-card">
            <span className="flex h-12 w-12 shrink-0 items-center justify-center rounded-full bg-ink-900 text-lg font-bold text-white ring-4 ring-brand-100">{e.nombre.charAt(0)}</span>
            <div className="min-w-0 flex-1">
              <p className="truncate font-semibold text-ink-900">{e.nombre}</p>
              <p className="flex items-center gap-1.5 text-xs text-ink-500"><Users className="h-3.5 w-3.5" aria-hidden="true" />{e.cantidad_jugadores} jugadores · {e.facultad_nombre}</p>
            </div>
            <Button size="sm" variant="ghost" aria-label={`Editar ${e.nombre}`} icon={<Pencil className="h-4 w-4" />} onClick={() => setModal({ equipo: e })} />
            <Link href={`/delegado/equipos/${e.id}`} aria-label={`Plantel de ${e.nombre}`} className="rounded-lg p-2 text-ink-400 hover:bg-ink-100 hover:text-brand-700"><ChevronRight className="h-5 w-5" /></Link>
          </li>
        ))}
      </ul>
      {!isLoading && data?.length === 0 && (
        <EmptyState icon={Shield} title="Aún no tienes equipos" description="Crea el primero para registrar jugadores e inscribirlo en un campeonato."
          action={<Button icon={<Plus className="h-4 w-4" />} onClick={() => setModal({})}>Nuevo equipo</Button>} />
      )}
      {modal && <ModalEquipo key={modal.equipo?.id ?? "nuevo"} equipo={modal.equipo} facultad={facultad} onCerrar={() => setModal(null)} />}
    </>
  );
}
