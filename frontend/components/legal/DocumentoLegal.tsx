import Link from "next/link";
import { FileText, Printer } from "lucide-react";
import { cn } from "@/lib/utils";
import { DOCUMENTOS_LEGALES, LEGAL_VERSION, LEGAL_VIGENTE_DESDE, RESPONSABLE } from "@/lib/legal.config";
import type { Bloque, Documento } from "@/lib/legal.contenido";
import { BotonCookies } from "@/components/cookies/BotonCookies";

function Contenido({ b }: { b: Bloque }) {
  if (b.tipo === "p") return <p className="leading-relaxed text-ink-700">{b.texto}</p>;
  if (b.tipo === "ul") {
    return (
      <ul className="space-y-2 text-ink-700">
        {b.items.map((i) => <li key={i} className="flex gap-2.5 leading-relaxed"><span aria-hidden="true" className="mt-2.5 h-1.5 w-1.5 shrink-0 rounded-full bg-brand-600" />{i}</li>)}
      </ul>
    );
  }
  return (
    <div>
      <div className="overflow-x-auto rounded-xl border border-ink-200 bg-white">
        <table className="w-full min-w-[32rem] text-left text-sm">
          <thead className="bg-ink-50 text-xs uppercase tracking-wide text-ink-500">
            <tr>{b.cabecera.map((c) => <th key={c} scope="col" className="px-4 py-3 font-medium">{c}</th>)}</tr>
          </thead>
          <tbody>
            {b.filas.map((f, i) => (
              <tr key={i} className="border-t border-ink-100 align-top">
                {f.map((c, k) => k === 0
                  ? <th key={k} scope="row" className="px-4 py-3 font-medium text-ink-900">{c}</th>
                  : <td key={k} className="px-4 py-3 text-ink-700">{c}</td>)}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {b.nota && <p className="mt-2 text-xs text-ink-500">{b.nota}</p>}
    </div>
  );
}

/** Página de un documento legal: encabezado con versión, índice lateral y secciones numeradas. */
export function DocumentoLegal({ documento, ruta }: { documento: Documento; ruta: string }) {
  return (
    <article className="mx-auto max-w-5xl">
      <header className="rounded-2xl bg-gradient-to-br from-ink-900 via-ink-900 to-brand-900 px-6 py-8 text-white shadow-pop sm:px-10">
        <span className="inline-flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-brand-200"><FileText className="h-4 w-4" aria-hidden="true" />Documento legal</span>
        <h1 className="mt-2 text-3xl font-bold tracking-tight sm:text-4xl">{documento.titulo}</h1>
        <p className="mt-3 max-w-2xl text-ink-200">{documento.resumen}</p>
        <p className="mt-4 flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-ink-300">
          <span>Versión {LEGAL_VERSION}</span><span aria-hidden="true">·</span><span>Vigente desde el {LEGAL_VIGENTE_DESDE}</span>
        </p>
      </header>

      <nav aria-label="Otros documentos legales" className="mt-4 flex flex-wrap items-center gap-2 text-sm">
        {DOCUMENTOS_LEGALES.map((d) => (
          <Link key={d.ruta} href={d.ruta} aria-current={d.ruta === ruta ? "page" : undefined}
            className={cn("rounded-full border px-3.5 py-1.5 font-medium transition-colors", d.ruta === ruta ? "border-brand-600 bg-brand-600 text-white" : "border-ink-200 bg-white text-ink-700 hover:bg-ink-50")}>{d.titulo}</Link>
        ))}
        <BotonCookies className="rounded-full border border-ink-200 bg-white px-3.5 py-1.5 font-medium text-ink-700 transition-colors hover:bg-ink-50" />
      </nav>

      <div className="mt-6 grid gap-8 lg:grid-cols-[14rem_1fr]">
        <aside className="lg:sticky lg:top-24 lg:self-start">
          <nav aria-label="Contenido del documento" className="rounded-xl border border-ink-200 bg-white p-3">
            <p className="px-2 pb-2 text-xs font-semibold uppercase tracking-wide text-ink-500">Contenido</p>
            <ol className="space-y-0.5 text-sm">
              {documento.secciones.map((s) => (
                <li key={s.id}><a href={`#${s.id}`} className="block rounded-lg px-2 py-1.5 text-ink-700 hover:bg-ink-50 hover:text-brand-700">{s.titulo}</a></li>
              ))}
            </ol>
          </nav>
        </aside>

        <div className="min-w-0 space-y-10">
          {documento.secciones.map((s) => (
            <section key={s.id} id={s.id} aria-labelledby={`${s.id}-t`} className="scroll-mt-24">
              <h2 id={`${s.id}-t`} className="text-xl font-bold tracking-tight text-ink-900">{s.titulo}</h2>
              <div className="mt-3 space-y-4">{s.bloques.map((b, i) => <Contenido key={i} b={b} />)}</div>
            </section>
          ))}

          <footer className="space-y-3 border-t border-ink-200 pt-6 text-sm text-ink-600">
            <p><b className="text-ink-800">¿Dudas sobre este documento?</b> Escribe a <a href={`mailto:${RESPONSABLE.correo}`} className="font-medium text-brand-700 underline">{RESPONSABLE.correo}</a> o llama al {RESPONSABLE.telefono} ({RESPONSABLE.horario}).</p>
            <p className="text-xs text-ink-500">Versión {LEGAL_VERSION}, vigente desde el {LEGAL_VIGENTE_DESDE}. Texto de referencia pendiente de revisión por la Asesoría Jurídica de la UAGRM; cualquier ajuste se publicará como una nueva versión.</p>
            <p className="print:hidden"><span className="inline-flex items-center gap-1.5 text-xs text-ink-500"><Printer className="h-3.5 w-3.5" aria-hidden="true" />Puedes imprimir o guardar esta página en PDF desde el menú de tu navegador (Ctrl + P).</span></p>
          </footer>
        </div>
      </div>
    </article>
  );
}
