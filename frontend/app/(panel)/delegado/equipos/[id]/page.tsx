"use client";
import { useState } from "react";
import { useParams } from "next/navigation";
import { Pencil, Plus, Shield, Trash2 } from "lucide-react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Badge, Button, ConfirmDialog, EmptyState, FormField, Input, Modal, PageHeader, PageLoader, Table, type Columna } from "@/components/ui";
import { useAccion, useApi, useErrorFormulario } from "@/lib/hooks/queries";
import { equipoService, jugadorService } from "@/lib/api/services";
import type { Jugador } from "@/types";

const esquema = z.object({
  nombre: z.string().trim().min(2, "Ingresa el nombre."),
  apellido: z.string().trim().min(2, "Ingresa el apellido."),
  carnet: z.string().trim().min(5, "Ingresa el carnet de identidad."),
  registro: z.string().trim().min(1, "Ingresa el registro universitario."),
  posicion: z.string().trim().min(2, "Ingresa la posición."),
  numero_camiseta: z.preprocess((v) => (v === "" || v == null || Number.isNaN(v) ? null : v), z.coerce.number().int().min(0, "Mínimo 0.").max(99, "Máximo 99.").nullable()),
});
type Datos = z.output<typeof esquema>;
type Entrada = z.input<typeof esquema>;      // con zod 4 los campos «coerce» entran como `unknown`
const CAMPOS = ["nombre", "apellido", "carnet", "registro", "posicion", "numero_camiseta", "equipo", "detail", "non_field_errors"] as const;

function ModalJugador({ equipoId, jugador, onCerrar }: { equipoId: number; jugador?: Jugador; onCerrar: () => void }) {
  const { register, handleSubmit, setError, formState: { errors } } = useForm<Entrada, unknown, Datos>({
    resolver: zodResolver(esquema),
    defaultValues: { nombre: jugador?.nombre ?? "", apellido: jugador?.apellido ?? "", carnet: jugador?.carnet ?? "", registro: jugador?.registro ?? "", posicion: jugador?.posicion ?? "", numero_camiseta: jugador?.numero_camiseta ?? null },
  });
  const alFallar = useErrorFormulario(setError, CAMPOS);
  const guardar = useAccion(
    (d: Datos) => (jugador ? jugadorService.editar(jugador.id, d) : jugadorService.crear({ ...d, equipo: equipoId })),
    { invalidar: ["equipo", "mis-equipos", "jugadores"], exito: jugador ? "Ficha actualizada." : "Jugador agregado al plantel." },
  );
  const general = (errors as Record<string, { message?: string }>).non_field_errors?.message ?? (errors as Record<string, { message?: string }>).detail?.message;
  return (
    <Modal open onClose={onCerrar} title={jugador ? "Editar ficha" : "Nuevo jugador"} size="lg"
      footer={<><Button variant="secondary" onClick={onCerrar}>Cancelar</Button><Button type="submit" form="form-jugador" loading={guardar.pendiente}>Guardar</Button></>}>
      <form id="form-jugador" noValidate onSubmit={handleSubmit((d) => guardar.ejecutar(d, { onSuccess: onCerrar, onError: alFallar }))} className="grid gap-4 sm:grid-cols-2">
        {general && <p role="alert" className="text-sm text-brand-700 sm:col-span-2">{general}</p>}
        <FormField label="Nombre" error={errors.nombre?.message} required><Input {...register("nombre")} /></FormField>
        <FormField label="Apellido" error={errors.apellido?.message} required><Input {...register("apellido")} /></FormField>
        <FormField label="Carnet de identidad" error={errors.carnet?.message} required><Input {...register("carnet")} /></FormField>
        <FormField label="Registro universitario" error={errors.registro?.message} required><Input {...register("registro")} /></FormField>
        <FormField label="Posición" error={errors.posicion?.message} required><Input placeholder="Ej.: Delantero" {...register("posicion")} /></FormField>
        <FormField label="Número de camiseta" error={errors.numero_camiseta?.message}><Input type="number" min={0} max={99} {...register("numero_camiseta")} /></FormField>
      </form>
    </Modal>
  );
}

export default function PlantelEquipo() {
  const id = Number(useParams<{ id: string }>().id);
  const equipo = useApi(["equipo", id], () => equipoService.obtener(id));
  const [modal, setModal] = useState<{ jugador?: Jugador } | null>(null);
  const [borrar, setBorrar] = useState<Jugador | null>(null);
  const eliminar = useAccion((j: number) => jugadorService.eliminar(j), { invalidar: ["equipo", "mis-equipos", "jugadores"], exito: "Jugador retirado del plantel." });

  if (equipo.isLoading) return <PageLoader />;
  const e = equipo.data;
  if (!e) return <EmptyState icon={Shield} title="Equipo no encontrado" description="No existe o no pertenece a tu facultad." />;

  const columnas: Columna<Jugador>[] = [
    { clave: "n", titulo: "N°", alinear: "center", render: (j) => <b className="text-ink-900">{j.numero_camiseta ?? "—"}</b> },
    { clave: "j", titulo: "Jugador", render: (j) => <span><b className="text-ink-900">{j.nombre} {j.apellido}</b><span className="block text-xs text-ink-500">CI {j.carnet}</span></span> },
    { clave: "p", titulo: "Posición", render: (j) => j.posicion },
    { clave: "s", titulo: "Sanción", render: (j) => j.partidos_sancion_restantes > 0 ? <Badge tono="danger">{j.partidos_sancion_restantes} partido(s)</Badge> : <Badge tono="success">Habilitado</Badge> },
    { clave: "a", titulo: "", alinear: "right", render: (j) => (
      <span className="inline-flex gap-1">
        <Button size="sm" variant="ghost" aria-label={`Editar a ${j.nombre}`} icon={<Pencil className="h-4 w-4" />} onClick={() => setModal({ jugador: j })} />
        <Button size="sm" variant="ghost" aria-label={`Retirar a ${j.nombre}`} icon={<Trash2 className="h-4 w-4 text-brand-600" />} onClick={() => setBorrar(j)} />
      </span>
    ) },
  ];

  return (
    <>
      <PageHeader breadcrumb={[{ label: "Mis equipos", href: "/delegado/equipos" }, { label: e.nombre }]} title={e.nombre}
        description={`${e.facultad_nombre} · ${e.jugadores?.length ?? 0} jugadores en el plantel. Los jugadores son solo fichas: no tienen cuenta.`}
        actions={<Button icon={<Plus className="h-4 w-4" />} onClick={() => setModal({})}>Nuevo jugador</Button>} />
      <Table columnas={columnas} filas={e.jugadores ?? []} clave={(j) => j.id} vacio={{ titulo: "El plantel está vacío", descripcion: "Agrega a los jugadores de tu equipo para poder inscribirlo." }} />
      {modal && <ModalJugador key={modal.jugador?.id ?? "nuevo"} equipoId={id} jugador={modal.jugador} onCerrar={() => setModal(null)} />}
      <ConfirmDialog open={!!borrar} onClose={() => setBorrar(null)} danger loading={eliminar.pendiente} title="Retirar jugador"
        message={`Se eliminará la ficha de ${borrar?.nombre ?? ""} ${borrar?.apellido ?? ""}.`} confirmText="Retirar"
        onConfirm={() => borrar && eliminar.ejecutar(borrar.id, { onSuccess: () => setBorrar(null) })} />
    </>
  );
}
