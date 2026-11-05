"use client";
import { useRef, useState } from "react";
import Image from "next/image";
import { useQueryClient } from "@tanstack/react-query";
import { Camera, KeyRound } from "lucide-react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Badge, Button, Card, CardBody, CardHeader, FormField, Input, PageHeader, PageLoader, useToast } from "@/components/ui";
import { useAccion, useErrorFormulario } from "@/lib/hooks/queries";
import { useAuth } from "@/lib/hooks/useAuth";
import { authService, perfilService } from "@/lib/api/services";
import { mensajeDeError } from "@/lib/api/errors";
import { ROL_ETIQUETA } from "@/lib/auth/roles";
import type { Usuario } from "@/types";

const esquemaDatos = z.object({
  nombre: z.string().trim().min(2, "Ingresa tu nombre."),
  apellido: z.string().trim().min(2, "Ingresa tu apellido."),
  telefono: z.string().max(20, "Máximo 20 caracteres.").optional(),
  ci: z.string().max(20, "Máximo 20 caracteres.").optional(),
});
type DatosPerfil = z.infer<typeof esquemaDatos>;

const esquemaClave = z.object({
  password_actual: z.string().min(1, "Ingresa tu contraseña actual."),
  password_nuevo: z.string().min(8, "Mínimo 8 caracteres."),
  password_nuevo2: z.string().min(1, "Confirma la nueva contraseña."),
}).refine((d) => d.password_nuevo === d.password_nuevo2, { path: ["password_nuevo2"], message: "Las contraseñas no coinciden." });
type DatosClave = z.infer<typeof esquemaClave>;

function FormularioDatos({ usuario }: { usuario: Usuario }) {
  const { register, handleSubmit, setError, formState: { errors, isDirty } } = useForm<DatosPerfil>({
    resolver: zodResolver(esquemaDatos),
    defaultValues: { nombre: usuario.nombre, apellido: usuario.apellido, telefono: usuario.telefono ?? "", ci: usuario.ci ?? "" },
  });
  const alFallar = useErrorFormulario(setError, ["nombre", "apellido", "telefono", "ci"] as const);
  const guardar = useAccion((d: DatosPerfil) => perfilService.editar(d), { invalidar: ["sesion"], exito: "Perfil actualizado." });
  return (
    <form noValidate onSubmit={handleSubmit((d) => guardar.ejecutar(d, { onError: alFallar }))} className="grid gap-4 sm:grid-cols-2">
      <FormField label="Nombre" error={errors.nombre?.message} required><Input {...register("nombre")} /></FormField>
      <FormField label="Apellido" error={errors.apellido?.message} required><Input {...register("apellido")} /></FormField>
      <FormField label="Teléfono" error={errors.telefono?.message}><Input {...register("telefono")} /></FormField>
      <FormField label="Carnet de identidad" error={errors.ci?.message}><Input {...register("ci")} /></FormField>
      <div className="sm:col-span-2"><Button type="submit" loading={guardar.pendiente} disabled={!isDirty}>Guardar cambios</Button></div>
    </form>
  );
}

function FormularioClave() {
  const toast = useToast();
  const { register, handleSubmit, reset, setError, formState: { errors, isSubmitting } } = useForm<DatosClave>({ resolver: zodResolver(esquemaClave) });
  const enviar = async (d: DatosClave) => {
    try {
      const r = await authService.cambiarPassword(d);
      if (r.ok) { toast.success("Contraseña actualizada. Tus otras sesiones se cerraron."); reset(); return; }
      const cuerpo = (await r.json().catch(() => ({}))) as Record<string, unknown>;
      const texto = (v: unknown) => (Array.isArray(v) ? v.join(" ") : String(v));
      if (cuerpo.error) setError("password_actual", { message: texto(cuerpo.error) });
      else if (cuerpo.password_nuevo) setError("password_nuevo", { message: texto(cuerpo.password_nuevo) });
      else toast.error(typeof cuerpo.detail === "string" ? cuerpo.detail : "No se pudo cambiar la contraseña.");
    } catch (e) {
      toast.error(mensajeDeError(e, "No se pudo conectar con el servidor."));
    }
  };
  return (
    <form noValidate onSubmit={handleSubmit(enviar)} className="grid gap-4 sm:grid-cols-3">
      <FormField label="Contraseña actual" error={errors.password_actual?.message} required><Input type="password" autoComplete="current-password" {...register("password_actual")} /></FormField>
      <FormField label="Contraseña nueva" error={errors.password_nuevo?.message} required><Input type="password" autoComplete="new-password" {...register("password_nuevo")} /></FormField>
      <FormField label="Confirmar contraseña nueva" error={errors.password_nuevo2?.message} required><Input type="password" autoComplete="new-password" {...register("password_nuevo2")} /></FormField>
      <div className="sm:col-span-3"><Button type="submit" variant="secondary" icon={<KeyRound className="h-4 w-4" />} loading={isSubmitting}>Cambiar contraseña</Button></div>
    </form>
  );
}

export default function Perfil() {
  const { usuario, rol, loading } = useAuth();
  const qc = useQueryClient();
  const toast = useToast();
  const entrada = useRef<HTMLInputElement>(null);
  const [subiendo, setSubiendo] = useState(false);

  if (loading || !usuario) return <PageLoader />;

  const subirFoto = async (archivo?: File) => {
    if (!archivo) return;
    if (!archivo.type.startsWith("image/")) { toast.error("Selecciona un archivo de imagen."); return; }
    if (archivo.size > 3 * 1024 * 1024) { toast.error("La imagen no debe superar los 3 MB."); return; }
    setSubiendo(true);
    try { await perfilService.subirFoto(archivo); await qc.invalidateQueries({ queryKey: ["sesion"] }); toast.success("Foto actualizada."); }
    catch (e) { toast.error(mensajeDeError(e, "No se pudo subir la foto.")); }
    finally { setSubiendo(false); if (entrada.current) entrada.current.value = ""; }
  };

  return (
    <>
      <PageHeader title="Mi perfil" description="Tus datos personales y tu contraseña. El rol y la facultad los define el administrador." />
      <div className="space-y-6">
        <Card>
          <CardBody className="flex flex-wrap items-center gap-5">
            {usuario.foto_perfil ? (
              <Image src={usuario.foto_perfil} alt="Tu foto de perfil" width={88} height={88} unoptimized className="h-22 w-22 rounded-full object-cover ring-4 ring-brand-100" />
            ) : (
              <span className="flex h-20 w-20 items-center justify-center rounded-full bg-brand-600 text-3xl font-bold text-white ring-4 ring-brand-100">{usuario.nombre.charAt(0)}</span>
            )}
            <div className="min-w-0 flex-1">
              <p className="truncate text-lg font-semibold text-ink-900">{usuario.nombre_completo}</p>
              <p className="truncate text-sm text-ink-500">{usuario.email}</p>
              <p className="mt-1">{rol && <Badge tono="brand">{ROL_ETIQUETA[rol]}</Badge>}</p>
            </div>
            <div>
              <input ref={entrada} type="file" accept="image/*" className="sr-only" id="foto" onChange={(e) => subirFoto(e.target.files?.[0])} />
              <Button variant="secondary" loading={subiendo} icon={<Camera className="h-4 w-4" />} onClick={() => entrada.current?.click()}>Cambiar foto</Button>
            </div>
          </CardBody>
        </Card>
        <Card><CardHeader title="Datos personales" /><CardBody><FormularioDatos usuario={usuario} /></CardBody></Card>
        <Card><CardHeader title="Seguridad" /><CardBody><FormularioClave /></CardBody></Card>
      </div>
    </>
  );
}
