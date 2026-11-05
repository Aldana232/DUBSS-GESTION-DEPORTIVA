"use client";
import { useCampeonatos } from "@/lib/hooks/queries";
import { Select } from "@/components/ui";

/** Lista desplegable de campeonatos reutilizada por fixture, posiciones y predicciones. */
export function SelectorCampeonato({ valor, onCambiar, vacio, id }: {
  valor: string; onCambiar: (v: string) => void; vacio: string; id?: string;
}) {
  const { data } = useCampeonatos();
  return (
    <Select id={id} aria-label="Campeonato" value={valor} onChange={(e) => onCambiar(e.target.value)} className="min-w-[14rem]">
      <option value="">{vacio}</option>
      {data?.results.map((c) => <option key={c.id} value={c.id}>{c.nombre}</option>)}
    </Select>
  );
}
