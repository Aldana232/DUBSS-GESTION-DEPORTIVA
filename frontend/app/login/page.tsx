"use client";
import { Suspense, useState } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { AlertCircle, ArrowRight, BrainCircuit, CalendarClock, Eye, EyeOff, FileText, Lock, Mail, ShieldCheck, Smartphone, Trophy } from "lucide-react";
import { authService } from "@/lib/api/services";
import { destinoTrasLogin, type Rol } from "@/lib/auth/roles";
import { Button, FormField, Input } from "@/components/ui";
import { Logo } from "@/components/layout/Logo";

const esquema = z.object({
  email: z.string().min(1, "Ingresa tu correo electrónico.").email("Ingresa un correo válido."),
  password: z.string().min(1, "Ingresa tu contraseña."),
});
type Datos = z.infer<typeof esquema>;

function FormularioLogin() {
  const router = useRouter();
  const params = useSearchParams();
  const [errorGeneral, setErrorGeneral] = useState("");
  const [verClave, setVerClave] = useState(false);
  const [mayusculas, setMayusculas] = useState(false);
  const { register, handleSubmit, formState: { errors, isSubmitting, isSubmitSuccessful } } = useForm<Datos>({ resolver: zodResolver(esquema) });

  const enviar = async (datos: Datos) => {
    setErrorGeneral("");
    try {
      const r = await authService.login(datos.email, datos.password);
      if (r.ok) {
        const { usuario } = (await r.json()) as { usuario: { rol: Rol } };
        router.replace(destinoTrasLogin(usuario.rol, params.get("redirect")));
        router.refresh();
        return;
      }
      const cuerpo = (await r.json().catch(() => ({}))) as { detail?: unknown };
      setErrorGeneral(
        typeof cuerpo.detail === "string" && (r.status === 429 || r.status === 502)
          ? cuerpo.detail
          : r.status === 429
            ? "Demasiados intentos de inicio de sesión. Intenta de nuevo más tarde."
            : "Credenciales incorrectas. Verifica tu correo y contraseña.",
      );
    } catch {
      setErrorGeneral("No se pudo conectar con el servidor. Revisa tu conexión.");
    }
  };

  return (
    <form onSubmit={handleSubmit(enviar)} noValidate className="space-y-5">
      {errorGeneral && (
        <div role="alert" className="flex animate-slide-up items-start gap-2 rounded-xl border border-brand-200 bg-brand-50 px-3.5 py-3 text-sm text-brand-800">
          <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" aria-hidden="true" />
          <span>{errorGeneral}</span>
        </div>
      )}
      <FormField label="Correo electrónico" error={errors.email?.message} required>
        <Input type="email" autoComplete="username" inputMode="email" placeholder="usuario@uagrm.edu.bo" leading={<Mail className="h-4 w-4" />} className="h-11" {...register("email")} />
      </FormField>
      <FormField label="Contraseña" error={errors.password?.message} required hint={mayusculas ? "Las mayúsculas están activadas." : undefined}>
        <Input
          type={verClave ? "text" : "password"} autoComplete="current-password" placeholder="Tu contraseña" leading={<Lock className="h-4 w-4" />} className="h-11"
          onKeyUp={(e) => setMayusculas(e.getModifierState("CapsLock"))}
          trailing={
            <button type="button" onClick={() => setVerClave((v) => !v)} aria-label={verClave ? "Ocultar contraseña" : "Mostrar contraseña"} aria-pressed={verClave}
              className="flex h-8 w-8 items-center justify-center rounded-lg text-ink-400 transition-colors hover:bg-ink-100 hover:text-ink-700">
              {verClave ? <EyeOff className="h-4 w-4" aria-hidden="true" /> : <Eye className="h-4 w-4" aria-hidden="true" />}
            </button>
          }
          {...register("password")}
        />
      </FormField>
      <Button type="submit" size="lg" className="group w-full bg-gradient-to-r from-brand-600 to-brand-700 shadow-pop hover:from-brand-700 hover:to-brand-800" loading={isSubmitting || isSubmitSuccessful}
        icon={isSubmitting || isSubmitSuccessful ? undefined : <ShieldCheck className="h-5 w-5" />}>
        {isSubmitting || isSubmitSuccessful ? "Ingresando..." : "Ingresar al sistema"}
      </Button>
    </form>
  );
}

const FUNCIONES = [
  { icono: Trophy, titulo: "Campeonatos y fixture inteligente", texto: "Calendarios sin choques, optimizados con IA.", tono: "bg-amber-400/20 text-amber-200" },
  { icono: BrainCircuit, titulo: "Predicciones y asistente", texto: "Pronósticos, clima y un agente que propone cambios.", tono: "bg-sky-400/20 text-sky-200" },
  { icono: Smartphone, titulo: "Planilla móvil sin conexión", texto: "Goles y tarjetas en la cancha, aun sin señal.", tono: "bg-emerald-400/20 text-emerald-200" },
  { icono: FileText, titulo: "Reportes y estadísticas", texto: "PDF y Excel por campeonato, equipo y facultad.", tono: "bg-rose-300/20 text-rose-100" },
];

export default function LoginPage() {
  return (
    <div className="grid min-h-screen lg:grid-cols-[1.1fr_1fr]">
      {/* Panel institucional */}
      <section className="relative hidden flex-col justify-between overflow-hidden bg-gradient-to-br from-ink-950 via-brand-900 to-brand-700 p-12 text-white lg:flex">
        <div className="absolute -left-28 -top-28 h-[26rem] w-[26rem] animate-float-slow rounded-full bg-brand-500/25 blur-3xl" aria-hidden="true" />
        <div className="absolute -bottom-40 right-[-6rem] h-[30rem] w-[30rem] animate-float-slow rounded-full bg-black/30 blur-3xl [animation-delay:-4s]" aria-hidden="true" />
        <div className="absolute inset-0 opacity-[0.07] [background-image:linear-gradient(white_1px,transparent_1px),linear-gradient(90deg,white_1px,transparent_1px)] [background-size:44px_44px]" aria-hidden="true" />

        <div className="relative flex items-center gap-4">
          <Logo size={64} className="shadow-pop ring-4 ring-white/20" />
          <div>
            <p className="text-lg font-extrabold tracking-wide">D.U.B.S.S.</p>
            <p className="text-xs text-brand-100">Bienestar Social y Salud · U.A.G.R.M.</p>
          </div>
        </div>

        <div className="relative max-w-xl">
          <h1 className="text-4xl font-black leading-tight tracking-tight">Gestión deportiva universitaria, <span className="text-brand-300">de la cancha a la tabla.</span></h1>
          <p className="mt-4 text-base text-brand-100">Organiza campeonatos, programa partidos, registra resultados y consulta estadísticas desde un solo lugar.</p>
          <ul className="mt-8 grid gap-3 sm:grid-cols-2">
            {FUNCIONES.map(({ icono: Icono, titulo, texto, tono }) => (
              <li key={titulo} className="rounded-2xl bg-white/10 p-4 ring-1 ring-inset ring-white/15 backdrop-blur-sm transition-transform duration-200 hover:-translate-y-0.5 hover:bg-white/[0.14]">
                <span className={`mb-3 flex h-9 w-9 items-center justify-center rounded-xl ${tono}`}><Icono className="h-5 w-5" aria-hidden="true" /></span>
                <p className="text-sm font-bold">{titulo}</p>
                <p className="mt-0.5 text-xs text-brand-100">{texto}</p>
              </li>
            ))}
          </ul>
        </div>

        <p className="relative flex items-center gap-2 text-xs text-brand-200"><CalendarClock className="h-4 w-4" aria-hidden="true" />Universidad Autónoma Gabriel René Moreno · Santa Cruz, Bolivia</p>
      </section>

      {/* Formulario */}
      <main className="relative flex flex-col bg-ink-50">
        {/* Encabezado móvil con el escudo */}
        <div className="relative overflow-hidden bg-gradient-to-br from-ink-950 via-brand-900 to-brand-700 px-6 pb-16 pt-10 text-center text-white lg:hidden">
          <div className="absolute -left-10 -top-10 h-44 w-44 animate-float-slow rounded-full bg-brand-500/30 blur-2xl" aria-hidden="true" />
          <Logo size={88} className="relative mx-auto shadow-pop ring-4 ring-white/25" />
          <p className="relative mt-3 text-lg font-extrabold tracking-wide">D.U.B.S.S.</p>
          <p className="relative text-xs text-brand-100">Sistema de Gestión Deportiva · U.A.G.R.M.</p>
        </div>

        <div className="flex flex-1 items-center justify-center px-5 pb-10 sm:px-10 lg:py-12">
          <div className="-mt-10 w-full max-w-md animate-slide-up rounded-3xl bg-white p-7 shadow-pop ring-1 ring-ink-100 sm:p-9 lg:mt-0">
            <span className="mb-4 inline-flex items-center gap-1.5 rounded-full bg-brand-50 px-3 py-1 text-xs font-semibold text-brand-700 ring-1 ring-inset ring-brand-200"><ShieldCheck className="h-3.5 w-3.5" aria-hidden="true" />Acceso seguro</span>
            <h2 className="text-2xl font-black tracking-tight text-ink-900">Iniciar sesión</h2>
            <p className="mb-6 mt-1 text-sm text-ink-500">Ingresa con la cuenta que te asignó el administrador.</p>
            <Suspense><FormularioLogin /></Suspense>
            <div className="mt-6 flex items-center gap-3 text-xs text-ink-400"><span className="h-px flex-1 bg-ink-100" />o<span className="h-px flex-1 bg-ink-100" /></div>
            <Link href="/campeonatos" className="group mt-4 flex items-center justify-center gap-2 rounded-xl border border-ink-200 py-2.5 text-sm font-semibold text-ink-700 transition-colors hover:border-brand-300 hover:bg-brand-50 hover:text-brand-700">
              Ver campeonatos y resultados públicos
              <ArrowRight className="h-4 w-4 transition-transform group-hover:translate-x-0.5" aria-hidden="true" />
            </Link>
            <p className="mt-6 text-center text-xs text-ink-400">¿Problemas para ingresar? Contacta al administrador de la DUBSS.</p>
          </div>
        </div>
      </main>
    </div>
  );
}
