"use client";
import { useRef, useState, type KeyboardEvent } from "react";
import { cn } from "@/lib/utils";
import { MODULOS } from "@/lib/corporativo.contenido";

function Chip({ valor }: { valor: string }) {
  const [tono, texto] = valor.split(":");
  return (
    <span className={cn("rounded-full px-2 py-0.5 text-xs font-medium", tono === "ok" ? "bg-emerald-50 text-emerald-700" : "bg-amber-50 text-amber-800")}>{texto}</span>
  );
}

/** Pestañas accesibles (teclado: flechas izquierda/derecha) con vistas de ejemplo de cada módulo. */
export function ProductoModulos() {
  const [activo, setActivo] = useState(0);
  const refs = useRef<(HTMLButtonElement | null)[]>([]);

  function teclas(e: KeyboardEvent, i: number) {
    if (e.key !== "ArrowRight" && e.key !== "ArrowLeft") return;
    e.preventDefault();
    const n = (i + (e.key === "ArrowRight" ? 1 : MODULOS.length - 1)) % MODULOS.length;
    setActivo(n);
    refs.current[n]?.focus();
  }

  return (
    <div>
      <div role="tablist" aria-label="Módulos del producto" className="scroll-thin mb-5 flex gap-2 overflow-x-auto pb-1">
        {MODULOS.map((m, i) => (
          <button key={m.id} ref={(el) => { refs.current[i] = el; }} role="tab" type="button" id={`tab-${m.id}`} aria-selected={activo === i} aria-controls={`panel-${m.id}`}
            tabIndex={activo === i ? 0 : -1} onClick={() => setActivo(i)} onKeyDown={(e) => teclas(e, i)}
            className={cn("whitespace-nowrap rounded-full border px-4 py-2 text-sm font-medium transition-colors",
              activo === i ? "border-brand-600 bg-brand-600 text-white" : "border-ink-200 bg-white text-ink-700 hover:bg-ink-50")}>
            {m.etiqueta}
          </button>
        ))}
      </div>

      {MODULOS.map((m, i) => (
        <div key={m.id} role="tabpanel" id={`panel-${m.id}`} aria-labelledby={`tab-${m.id}`} hidden={activo !== i}
          className="grid min-w-0 gap-6 [&[hidden]]:hidden rounded-xl border border-ink-200 bg-white p-5 shadow-card md:grid-cols-2 md:p-6">
          <div className="min-w-0">
            <h3 className="text-lg font-semibold text-ink-900">{m.titulo}</h3>
            <p className="mt-2 text-sm leading-relaxed text-ink-600">{m.texto}</p>
            <ul className="mt-4 space-y-1.5 text-sm text-ink-700">
              {m.puntos.map((p) => (
                <li key={p} className="flex gap-2"><span aria-hidden="true" className="mt-2 h-1.5 w-1.5 shrink-0 rounded-full bg-brand-600" />{p}</li>
              ))}
            </ul>
          </div>
          <div className="min-w-0 overflow-hidden rounded-lg border border-ink-200 bg-ink-50">
            <div className="flex items-center gap-1.5 border-b border-ink-200 bg-white px-3 py-2">
              <span className="h-2.5 w-2.5 rounded-full bg-ink-200" /><span className="h-2.5 w-2.5 rounded-full bg-ink-200" /><span className="h-2.5 w-2.5 rounded-full bg-ink-200" />
              <span className="ml-2 truncate text-xs font-medium text-ink-600">{m.pantalla}</span>
            </div>
            <div className="p-3">
              {"filas" in m ? (
                <div className="overflow-x-auto">
                  <table className="w-full text-left text-xs">
                    <thead><tr className="text-ink-500">{m.cabecera.map((c) => <th key={c} scope="col" className="px-2 py-1.5 font-medium">{c}</th>)}</tr></thead>
                    <tbody>
                      {m.filas.map((f, r) => (
                        <tr key={r} className="border-t border-ink-200 text-ink-800">
                          {f.map((c, k) => <td key={k} className="px-2 py-2">{/^(ok|wn):/.test(c) ? <Chip valor={c} /> : c}</td>)}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : (
                <div className="space-y-3 py-1">
                  {m.barras.map(([nombre, pct], k) => (
                    <div key={nombre} className="grid grid-cols-[5.5rem_1fr_2.5rem] items-center gap-2 text-xs text-ink-700">
                      <span className="truncate">{nombre}</span>
                      <div className="h-2.5 overflow-hidden rounded-full bg-ink-200" role="img" aria-label={`${nombre}: ${pct} por ciento`}>
                        <div className={cn("h-full rounded-full", k === 1 ? "bg-ink-400" : "bg-brand-600")} style={{ width: `${pct}%` }} />
                      </div>
                      <b className="text-right">{pct}%</b>
                    </div>
                  ))}
                </div>
              )}
              <p className="mt-3 text-[11px] text-ink-500">{m.nota}</p>
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}
