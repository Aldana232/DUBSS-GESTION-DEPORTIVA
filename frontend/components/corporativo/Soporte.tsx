import { EMPRESA, POR_CONFIRMAR } from "@/lib/corporativo.config";
import { NIVELES } from "@/lib/corporativo.contenido";
import { Card } from "@/components/ui";

const o = (v: string) => v || POR_CONFIRMAR;

export function Soporte() {
  const canales = [
    ["Asistente de ayuda", "Preguntas frecuentes sobre el producto", "Siempre", "Inmediata"],
    ["Correo electrónico", "Consultas, solicitudes y reportes de errores", o(EMPRESA.horarioCorreo), o(EMPRESA.respuestaCorreo)],
    ["WhatsApp", "Atención rápida durante los campeonatos", o(EMPRESA.horarioWhatsapp), o(EMPRESA.respuestaWhatsapp)],
  ];
  return (
    <div className="space-y-6">
      <div className="grid gap-4 md:grid-cols-3">
        {NIVELES.map(([nivel, titulo, texto]) => (
          <Card key={nivel} className="p-5">
            <span className="text-xs font-semibold uppercase tracking-wider text-brand-700">{nivel}</span>
            <h3 className="mt-1 font-semibold text-ink-900">{titulo}</h3>
            <p className="mt-2 text-sm text-ink-600">{texto}</p>
          </Card>
        ))}
      </div>
      <Card className="overflow-x-auto">
        <table className="w-full min-w-[34rem] text-left text-sm">
          <caption className="sr-only">Canales de soporte, disponibilidad y tiempo de respuesta</caption>
          <thead className="bg-ink-50 text-xs uppercase tracking-wide text-ink-500">
            <tr>{["Canal", "Para qué sirve", "Disponibilidad", "Respuesta"].map((c) => <th key={c} scope="col" className="px-4 py-3 font-medium">{c}</th>)}</tr>
          </thead>
          <tbody>
            {canales.map((f) => (
              <tr key={f[0]} className="border-t border-ink-100">
                <th scope="row" className="px-4 py-3 font-medium text-ink-900">{f[0]}</th>
                <td className="px-4 py-3 text-ink-600">{f[1]}</td>
                <td className={`px-4 py-3 ${f[2] === POR_CONFIRMAR ? "text-ink-400" : "text-ink-700"}`}>{f[2]}</td>
                <td className={`px-4 py-3 ${f[3] === POR_CONFIRMAR ? "text-ink-400" : "text-ink-700"}`}>{f[3]}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </Card>
    </div>
  );
}
