"use client";
import { useState } from "react";
import { KeyRound, Pencil, Plus, Search, UserX } from "lucide-react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import {
  Badge, Button, Checkbox, ConfirmDialog, FormField, Input, Modal, PageHeader, PageLoader, Select, Table, type Columna,
} from "@/components/ui";
import { useAccion, useApi, useErrorFormulario } from "@/lib/hooks/queries";
import { useAuth } from "@/lib/hooks/useAuth";
import { facultadService, usuarioService } from "@/lib/api/services";
import { ROL_ETIQUETA, type Rol } from "@/lib/auth/roles";
import { fechaCorta } from "@/lib/utils";
import type { Usuario } from "@/types";

const ROLES: Rol[] = ["SUPERADMIN", "ADMIN_DUBSS", "ORGANIZADOR", "DELEGADO"];

const base = {
  nombre: z.string().trim().min(2, "Ingresa el nombre."),
  apellido: z.string().trim().min(2, "Ingresa el apellido."),
  ci: z.string().optional(),
  telefono: z.string().optional(),
  rol: z.enum(["SUPERADMIN", "ADMIN_DUBSS", "ORGANIZADOR", "DELEGADO"]),
  facultad: z.string().optional(),
};
const conFacultad = <T extends { rol: string; facultad?: string }>(d: T, ctx: z.RefinementCtx) => {
  if (d.rol === "DELEGADO" && !d.facultad) ctx.addIssue({ code: "custom", path: ["facultad"], message: "El delegado debe tener una facultad." });
};
const esquemaAlta = z.object({
  ...base,
  email: z.string().min(1, "Ingresa el correo.").email("Ingresa un correo válido."),
  password: z.string().min(8, "Mínimo 8 caracteres."),
  password2: z.string().min(1, "Confirma la contraseña."),
}).superRefine(conFacultad).refine((d) => d.password === d.password2, { path: ["password2"], message: "Las contraseñas no coinciden." });
const esquemaEdicion = z.object({ ...base, is_active: z.boolean() }).superRefine(conFacultad);
type DatosAlta = z.infer<typeof esquemaAlta>;
type DatosEdicion = z.infer<typeof esquemaEdicion>;
const CAMPOS_ALTA = ["email", "nombre", "apellido", "ci", "telefono", "rol", "facultad", "password", "password2"] as const;

function CamposComunes({ register, errors, esSuper, facultades }: {
  register: ReturnType<typeof useForm<DatosAlta>>["register"]; errors: Record<string, { message?: string } | undefined>;
  esSuper: boolean; facultades: { id: number; nombre: string; sigla: string }[];
}) {
  return (
    <>
      <FormField label="Nombre" error={errors.nombre?.message} required><Input {...register("nombre")} /></FormField>
      <FormField label="Apellido" error={errors.apellido?.message} required><Input {...register("apellido")} /></FormField>
      <FormField label="Carnet de identidad" error={errors.ci?.message}><Input {...register("ci")} /></FormField>
      <FormField label="Teléfono" error={errors.telefono?.message}><Input {...register("telefono")} /></FormField>
      <FormField label="Rol" error={errors.rol?.message} required>
        <Select {...register("rol")}>{ROLES.filter((r) => esSuper || r !== "SUPERADMIN").map((r) => <option key={r} value={r}>{ROL_ETIQUETA[r]}</option>)}</Select>
      </FormField>
      <FormField label="Facultad" error={errors.facultad?.message} hint="Obligatoria para delegados.">
        <Select {...register("facultad")}><option value="">Sin facultad</option>{facultades.map((f) => <option key={f.id} value={f.id}>{f.sigla} — {f.nombre}</option>)}</Select>
      </FormField>
    </>
  );
}

function ModalAlta({ onCerrar, esSuper, facultades }: { onCerrar: () => void; esSuper: boolean; facultades: { id: number; nombre: string; sigla: string }[] }) {
  const { register, handleSubmit, setError, formState: { errors } } = useForm<DatosAlta>({ resolver: zodResolver(esquemaAlta), defaultValues: { rol: "ORGANIZADOR" } });
  const alFallar = useErrorFormulario(setError, CAMPOS_ALTA);
  const crear = useAccion((d: DatosAlta) => usuarioService.crear({ ...d, facultad: d.facultad ? Number(d.facultad) : null }), { invalidar: ["usuarios"], exito: "Cuenta creada correctamente." });
  return (
    <Modal open onClose={onCerrar} title="Nueva cuenta" size="lg"
      footer={<><Button variant="secondary" onClick={onCerrar}>Cancelar</Button><Button type="submit" form="form-usuario" loading={crear.pendiente}>Crear cuenta</Button></>}>
      <form id="form-usuario" noValidate onSubmit={handleSubmit((d) => crear.ejecutar(d, { onSuccess: onCerrar, onError: alFallar }))} className="grid gap-4 sm:grid-cols-2">
        <FormField label="Correo electrónico" error={errors.email?.message} required className="sm:col-span-2"><Input type="email" autoComplete="off" {...register("email")} /></FormField>
        <CamposComunes register={register} errors={errors} esSuper={esSuper} facultades={facultades} />
        <FormField label="Contraseña" error={errors.password?.message} required><Input type="password" autoComplete="new-password" {...register("password")} /></FormField>
        <FormField label="Confirmar contraseña" error={errors.password2?.message} required><Input type="password" autoComplete="new-password" {...register("password2")} /></FormField>
      </form>
    </Modal>
  );
}

function ModalEdicion({ usuario, onCerrar, esSuper, facultades }: { usuario: Usuario; onCerrar: () => void; esSuper: boolean; facultades: { id: number; nombre: string; sigla: string }[] }) {
  const { register, handleSubmit, setError, formState: { errors } } = useForm<DatosEdicion>({
    resolver: zodResolver(esquemaEdicion),
    defaultValues: { nombre: usuario.nombre, apellido: usuario.apellido, ci: usuario.ci ?? "", telefono: usuario.telefono, rol: usuario.rol as DatosEdicion["rol"], facultad: usuario.facultad ? String(usuario.facultad) : "", is_active: usuario.is_active },
  });
  const alFallar = useErrorFormulario(setError, CAMPOS_ALTA);
  const editar = useAccion((d: DatosEdicion) => usuarioService.editar(usuario.id, { ...d, facultad: d.facultad ? Number(d.facultad) : null }), { invalidar: ["usuarios"], exito: "Cuenta actualizada." });
  return (
    <Modal open onClose={onCerrar} title={`Editar a ${usuario.nombre_completo}`} size="lg"
      footer={<><Button variant="secondary" onClick={onCerrar}>Cancelar</Button><Button type="submit" form="form-usuario" loading={editar.pendiente}>Guardar cambios</Button></>}>
      <form id="form-usuario" noValidate onSubmit={handleSubmit((d) => editar.ejecutar(d, { onSuccess: onCerrar, onError: alFallar }))} className="grid gap-4 sm:grid-cols-2">
        <p className="text-sm text-ink-500 sm:col-span-2">Correo: <b className="text-ink-800">{usuario.email}</b> (no se puede cambiar).</p>
        <CamposComunes register={register as never} errors={errors as never} esSuper={esSuper} facultades={facultades} />
        <div className="sm:col-span-2"><Checkbox label="Cuenta activa" {...register("is_active")} /></div>
      </form>
    </Modal>
  );
}

function ModalPassword({ usuario, onCerrar }: { usuario: Usuario; onCerrar: () => void }) {
  const [clave, setClave] = useState("");
  const [error, setError] = useState("");
  const restablecer = useAccion((p: string) => usuarioService.restablecer(usuario.id, { password_nuevo: p }), { invalidar: ["usuarios"], exito: "Contraseña restablecida. Las sesiones anteriores quedaron cerradas." });
  const enviar = () => {
    if (clave.length < 8) { setError("Mínimo 8 caracteres."); return; }
    restablecer.ejecutar(clave, {
      onSuccess: onCerrar,
      onError: (e) => {
        const d = (e as { response?: { data?: { password_nuevo?: string[] } } }).response?.data?.password_nuevo;
        setError(d ? d.join(" ") : "No se pudo restablecer la contraseña.");
      },
    });
  };
  return (
    <Modal open onClose={onCerrar} title="Restablecer contraseña" size="sm"
      footer={<><Button variant="secondary" onClick={onCerrar}>Cancelar</Button><Button loading={restablecer.pendiente} onClick={enviar}>Restablecer</Button></>}>
      <p className="mb-3 text-sm text-ink-600">Define una contraseña nueva para <b>{usuario.nombre_completo}</b>. Se cerrarán sus sesiones abiertas.</p>
      <FormField label="Nueva contraseña" error={error} required><Input type="password" autoComplete="new-password" value={clave} onChange={(e) => { setClave(e.target.value); setError(""); }} /></FormField>
    </Modal>
  );
}

export default function GestionUsuarios() {
  const { esSuperadmin, usuario: yo } = useAuth();
  const [pagina, setPagina] = useState(1);
  const [buscar, setBuscar] = useState("");
  const [rol, setRol] = useState("");
  const [activo, setActivo] = useState("");
  const [modal, setModal] = useState<{ tipo: "alta" | "editar" | "password" | "baja"; usuario?: Usuario } | null>(null);
  const facultades = useApi(["facultades"], () => facultadService.listar());
  const { data, isLoading } = useApi(["usuarios", pagina, buscar, rol, activo], () =>
    usuarioService.listar({ page: pagina, search: buscar || undefined, rol: rol || undefined, is_active: activo || undefined }));
  const baja = useAccion((id: number) => usuarioService.baja(id), { invalidar: ["usuarios"], exito: "Cuenta dada de baja." });
  const lista = facultades.data?.results ?? [];
  const nombreFacultad = (id: number | null) => lista.find((f) => f.id === id)?.sigla ?? "—";

  const columnas: Columna<Usuario>[] = [
    { clave: "n", titulo: "Usuario", render: (u) => <span><b className="text-ink-900">{u.nombre_completo}</b><span className="block text-xs text-ink-500">{u.email}</span></span> },
    { clave: "r", titulo: "Rol", render: (u) => ROL_ETIQUETA[u.rol] },
    { clave: "f", titulo: "Facultad", render: (u) => nombreFacultad(u.facultad) },
    { clave: "a", titulo: "Estado", render: (u) => <Badge tono={u.is_active ? "success" : "neutral"}>{u.is_active ? "Activa" : "Inactiva"}</Badge> },
    { clave: "u", titulo: "Último acceso", render: (u) => fechaCorta(u.ultimo_acceso) },
    { clave: "x", titulo: "", alinear: "right", render: (u) => (
      <span className="inline-flex gap-1">
        <Button size="sm" variant="ghost" aria-label="Editar cuenta" icon={<Pencil className="h-4 w-4" />} onClick={() => setModal({ tipo: "editar", usuario: u })} />
        <Button size="sm" variant="ghost" aria-label="Restablecer contraseña" icon={<KeyRound className="h-4 w-4" />} onClick={() => setModal({ tipo: "password", usuario: u })} />
        {u.id !== yo?.id && u.is_active && <Button size="sm" variant="ghost" aria-label="Dar de baja" icon={<UserX className="h-4 w-4 text-brand-600" />} onClick={() => setModal({ tipo: "baja", usuario: u })} />}
      </span>
    ) },
  ];

  const cerrar = () => setModal(null);
  return (
    <>
      <PageHeader title="Usuarios y roles" description="Crea cuentas, asigna rol y facultad, activa o desactiva y restablece contraseñas."
        actions={<Button icon={<Plus className="h-4 w-4" />} onClick={() => setModal({ tipo: "alta" })}>Nueva cuenta</Button>} />
      <div className="mb-5 flex flex-wrap gap-3">
        <div className="w-full sm:w-72"><Input aria-label="Buscar usuario" placeholder="Buscar por nombre, correo o CI" leading={<Search className="h-4 w-4" />} value={buscar} onChange={(e) => { setBuscar(e.target.value); setPagina(1); }} /></div>
        <Select aria-label="Rol" value={rol} onChange={(e) => { setRol(e.target.value); setPagina(1); }} className="w-48">
          <option value="">Todos los roles</option>{ROLES.map((r) => <option key={r} value={r}>{ROL_ETIQUETA[r]}</option>)}
        </Select>
        <Select aria-label="Estado" value={activo} onChange={(e) => { setActivo(e.target.value); setPagina(1); }} className="w-40">
          <option value="">Todas</option><option value="true">Activas</option><option value="false">Inactivas</option>
        </Select>
      </div>
      {isLoading ? <PageLoader /> : (
        <Table columnas={columnas} filas={data?.results ?? []} clave={(u) => u.id}
          pagina={{ actual: pagina, total: Math.ceil((data?.count ?? 0) / 20), onCambiar: setPagina }}
          vacio={{ titulo: "No hay usuarios con esos filtros" }} />
      )}

      {modal?.tipo === "alta" && <ModalAlta onCerrar={cerrar} esSuper={esSuperadmin} facultades={lista} />}
      {modal?.tipo === "editar" && modal.usuario && <ModalEdicion key={modal.usuario.id} usuario={modal.usuario} onCerrar={cerrar} esSuper={esSuperadmin} facultades={lista} />}
      {modal?.tipo === "password" && modal.usuario && <ModalPassword usuario={modal.usuario} onCerrar={cerrar} />}
      <ConfirmDialog open={modal?.tipo === "baja"} onClose={cerrar} danger loading={baja.pendiente} title="Dar de baja la cuenta"
        message={`La cuenta de ${modal?.usuario?.nombre_completo ?? ""} quedará inactiva y no podrá iniciar sesión.`} confirmText="Dar de baja"
        onConfirm={() => modal?.usuario && baja.ejecutar(modal.usuario.id, { onSuccess: cerrar })} />
    </>
  );
}
