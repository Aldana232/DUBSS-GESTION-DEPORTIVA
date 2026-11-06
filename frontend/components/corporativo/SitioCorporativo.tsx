"use client";
import { useState } from "react";
import Link from "next/link";
import { ArrowRight } from "lucide-react";
import { Logo } from "@/components/layout/Logo";
import { Card } from "@/components/ui";
import { DUBSS, EMPRESA } from "@/lib/corporativo.config";
import { ROLES } from "@/lib/corporativo.contenido";
import { ChatAyuda } from "./ChatAyuda";
import { Contacto } from "./Contacto";
import { Descargas } from "./Descargas";
import { ProductoModulos } from "./ProductoModulos";
import { SeccionDubss } from "./SeccionDubss";
import { Soporte } from "./Soporte";

const ANCLAS = [["quienes", "Quiénes somos"], ["producto", "Producto"], ["dubss", "La DUBSS"], ["descargas", "Descargas"], ["soporte", "Soporte"], ["contacto", "Contacto"]];

function Seccion({ id, etiqueta, titulo, texto, children }: { id: string; etiqueta: string; titulo: string; texto?: string; children: React.ReactNode }) {
  return (
    <section id={id} aria-labelledby={`${id}-t`} className="scroll-mt-32 py-10">
      <span className="text-xs font-semibold uppercase tracking-wider text-brand-700">{etiqueta}</span>
      <h2 id={`${id}-t`} className="mt-1 max-w-3xl text-2xl font-bold tracking-tight text-ink-900 sm:text-3xl [text-wrap:balance]">{titulo}</h2>
      {texto && <p className="mt-3 max-w-3xl text-ink-600">{texto}</p>}
      <div className="mt-6">{children}</div>
    </section>
  );
}

export function SitioCorporativo() {
  const [chat, setChat] = useState(false);
  return (
    <>
      <section className="overflow-hidden rounded-2xl bg-gradient-to-br from-brand-700 via-brand-800 to-brand-900 px-6 py-10 text-white shadow-pop sm:px-10 sm:py-14">
        <div className="flex flex-col items-center gap-8 text-center md:flex-row md:text-left">
          <div className="max-w-2xl">
            <span className="text-xs font-semibold uppercase tracking-wider text-brand-200">{EMPRESA.producto}</span>
            <h1 className="mt-2 text-3xl font-bold tracking-tight sm:text-4xl [text-wrap:balance]">Gestión deportiva universitaria, de la cancha a la tabla</h1>
            <p className="mt-3 text-brand-100">
              Plataforma web para organizar campeonatos, programar partidos con optimización, registrar resultados sin conexión y consultar estadísticas. Desarrollada para la {DUBSS.nombre} (DUBSS) de la UAGRM.
            </p>
            <div className="mt-6 flex flex-wrap justify-center gap-3 md:justify-start">
              <a href="#producto" className="inline-flex h-11 items-center gap-2 rounded-lg bg-white px-5 text-sm font-semibold text-brand-800 transition-colors hover:bg-brand-50">Ver producto <ArrowRight className="h-4 w-4" aria-hidden="true" /></a>
              <a href="#descargas" className="inline-flex h-11 items-center rounded-lg border border-white/40 px-5 text-sm font-medium text-white transition-colors hover:bg-white/10">Descargar información</a>
            </div>
            <ul className="mt-6 flex flex-wrap justify-center gap-2 text-xs md:justify-start">
              {["5 roles de usuario", "Fixture con optimización", "Planilla sin conexión"].map((p) => <li key={p} className="rounded-full bg-white/10 px-3 py-1">{p}</li>)}
            </ul>
          </div>
          <Logo size={160} className="shrink-0 shadow-pop ring-8 ring-white/15 md:ml-auto" />
        </div>
      </section>

      <nav aria-label="Secciones de esta página" className="scroll-thin sticky top-16 z-20 -mx-4 mt-4 flex gap-2 overflow-x-auto border-b border-ink-200 bg-ink-50/95 px-4 py-2 backdrop-blur sm:-mx-6 sm:px-6">
        {ANCLAS.map(([id, t]) => (
          <a key={id} href={`#${id}`} className="whitespace-nowrap rounded-full px-3 py-1.5 text-sm font-medium text-ink-700 hover:bg-white hover:text-brand-700">{t}</a>
        ))}
      </nav>

      <Seccion id="quienes" etiqueta="Quiénes somos" titulo="Un equipo de ingeniería que entiende cómo se organiza un campeonato universitario"
        texto={`${EMPRESA.producto} desarrolla software para la gestión deportiva. El sistema nació como proyecto de la asignatura Ingeniería de Software II de la Facultad de Ingeniería en Ciencias de la Computación y Telecomunicaciones (FICCT) de la UAGRM, y está pensado para la DUBSS. Nuestro propósito es que la programación, el registro de resultados y la comunicación con los equipos sean transparentes, rápidos y auditables.`}>
        <div className="grid gap-4 md:grid-cols-3">
          {[["Misión", "Menos horas en hojas de cálculo", "Reemplazar la programación manual de partidos y los conteos en papel por un proceso automático y verificable."],
            ["Visión", "Estándar para el deporte universitario", "Ser la plataforma que usan las facultades para organizar sus torneos de forma justa y con datos confiables."],
            ["Principios", "Transparencia, seguridad, disponibilidad", "Todo cambio queda registrado, cada usuario ve solo lo que le corresponde y la planilla funciona aun sin conexión."]].map(([t, h, p]) => (
            <Card key={t} className="p-5"><span className="text-xs font-semibold uppercase tracking-wider text-brand-700">{t}</span><h3 className="mt-1 font-semibold text-ink-900">{h}</h3><p className="mt-2 text-sm text-ink-600">{p}</p></Card>
          ))}
        </div>
      </Seccion>

      <Seccion id="producto" etiqueta="Producto" titulo="Lo que hace el sistema, con vistas de ejemplo"
        texto="Elige un módulo para ver cómo se presenta la información. Los equipos y las cifras de estas vistas son ficticios. Para ver el sistema con datos propios, ingresa con tu cuenta.">
        <ProductoModulos />
        <div className="mt-8 grid gap-4 sm:grid-cols-2 lg:grid-cols-5">
          {ROLES.map(([t, p]) => <Card key={t} className="p-5"><h3 className="font-semibold text-ink-900">{t}</h3><p className="mt-2 text-sm text-ink-600">{p}</p></Card>)}
        </div>
        <p className="mt-4 text-sm text-ink-600">¿Ya tienes cuenta? <Link href="/login" className="font-medium text-brand-700 underline">Ingresar al sistema</Link> · <Link href="/campeonatos" className="font-medium text-brand-700 underline">Ver campeonatos y resultados públicos</Link></p>
      </Seccion>

      <Seccion id="dubss" etiqueta="Dirección usuaria" titulo="Desarrollado para la DUBSS de la UAGRM"
        texto="La Dirección Universitaria de Bienestar Social y Salud es la unidad de la UAGRM que planifica y coordina las actividades deportivas de la comunidad universitaria, entre ellas los torneos interfacultativos. El sistema se construye para su trabajo diario.">
        <SeccionDubss />
      </Seccion>

      <Seccion id="descargas" etiqueta="Descargas" titulo="Lleva la información del producto contigo" texto="Documentos para evaluar el sistema y acceso a la aplicación.">
        <Descargas />
      </Seccion>

      <Seccion id="soporte" etiqueta="Soporte técnico" titulo="Tres niveles de atención, del autoservicio al ingeniero"
        texto="Puedes resolver las dudas frecuentes con el asistente de la esquina inferior derecha. Si no alcanza, el caso sube de nivel.">
        <Soporte />
      </Seccion>

      <Seccion id="contacto" etiqueta="Contacto" titulo="Hablemos de tu campeonato" texto="Escríbenos por el canal que prefieras. Responderemos con el detalle del sistema y una demostración.">
        <Contacto onAbrirChat={() => setChat(true)} />
      </Seccion>

      <p className="border-t border-ink-200 pt-4 text-xs text-ink-500">
        {EMPRESA.nombre} (denominación provisional) · {EMPRESA.ciudad}. Proyecto desarrollado en la FICCT, UAGRM, para la DUBSS. Esta página no es un sitio oficial de la universidad ni de la DUBSS.
      </p>
      <ChatAyuda abierto={chat} setAbierto={setChat} />
    </>
  );
}
