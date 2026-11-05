"use client";
import { useState } from "react";
import { Pencil, Plus, Trash2 } from "lucide-react";
import { useForm } from "react-hook-form";
import { Badge, Button, ConfirmDialog, FormField, Input, Modal, PageLoader, Select, Table, Textarea, useToast, type Columna } from "@/components/ui";
import { useAccion, useApi, useErrorFormulario } from "@/lib/hooks/queries";
import { mensajeDeError } from "@/lib/api/errors";
import { aInputFechaHora, deInputFechaHora } from "@/lib/utils";

type Valor = string | number | boolean | null | undefined;
type Fila = { id: number } & Record<string, unknown>;

export interface CampoCatalogo {
  nombre: string;
  etiqueta: string;
  tipo: "texto" | "numero" | "select" | "casilla" | "hora" | "fechahora" | "area";
  requerido?: boolean;
  opciones?: { valor: string | number; texto: string }[];
  ayuda?: string;
  /** Valor inicial al crear. */
  inicial?: Valor;
  ancho?: boolean;
}

export interface ServicioCrud {
  listar: (params?: Record<string, string | number | boolean | undefined>) => Promise<{ results: unknown[] }>;
  crear: (datos: never) => Promise<unknown>;
  editar: (id: number, datos: never) => Promise<unknown>;
  eliminar: (id: number) => Promise<unknown>;
}

interface Props {
  clave: string;
  titulo: string;
  singular: string;
  servicio: ServicioCrud;
  campos: CampoCatalogo[];
  columnas: Columna<Fila>[];
  filtros?: Record<string, string | number | boolean | undefined>;
}

function aFormulario(campos: CampoCatalogo[], fila?: Fila): Record<string, Valor> {
  const base: Record<string, Valor> = {};
  campos.forEach((c) => {
    const v = fila ? (fila[c.nombre] as Valor) : c.inicial;
    base[c.nombre] = c.tipo === "fechahora" ? aInputFechaHora(v as string) : c.tipo === "hora" ? ((v as string) ?? "").slice(0, 5) : (v ?? (c.tipo === "casilla" ? false : ""));
  });
  return base;
}

function aPayload(campos: CampoCatalogo[], datos: Record<string, Valor>) {
  const salida: Record<string, Valor> = {};
  campos.forEach((c) => {
    const v = datos[c.nombre];
    if (c.tipo === "numero" || c.tipo === "select") {
      const numerico = c.tipo === "numero" || typeof c.opciones?.[0]?.valor === "number";
      salida[c.nombre] = v === "" || v === undefined || v === null ? null : numerico ? Number(v) : v;
    }
    else if (c.tipo === "fechahora") salida[c.nombre] = deInputFechaHora(v as string);
    else salida[c.nombre] = v;
  });
  return salida;
}

function ModalFila({ props, fila, onCerrar }: { props: Props; fila?: Fila; onCerrar: () => void }) {
  const { campos, servicio, clave, singular } = props;
  const { register, handleSubmit, setError, formState: { errors } } = useForm<Record<string, Valor>>({ defaultValues: aFormulario(campos, fila) });
  const nombres = campos.map((c) => c.nombre);
  const alFallar = useErrorFormulario(setError, [...nombres, "detail", "non_field_errors"]);
  const guardar = useAccion(
    (d: Record<string, Valor>) => (fila ? servicio.editar(fila.id, aPayload(campos, d) as never) : servicio.crear(aPayload(campos, d) as never)),
    { invalidar: [clave], exito: fila ? `${singular} actualizado.` : `${singular} creado.` },
  );
  const enviar = (d: Record<string, Valor>) => {
    const faltan = campos.filter((c) => c.requerido && c.tipo !== "casilla" && (d[c.nombre] === "" || d[c.nombre] == null));
    if (faltan.length) { faltan.forEach((c) => setError(c.nombre, { message: "Este campo es obligatorio." })); return; }
    guardar.ejecutar(d, { onSuccess: onCerrar, onError: alFallar });
  };
  const mensaje = (n: string) => (errors[n]?.message as string | undefined);

  return (
    <Modal open onClose={onCerrar} title={fila ? `Editar ${singular.toLowerCase()}` : `Nuevo ${singular.toLowerCase()}`}
      footer={<><Button variant="secondary" onClick={onCerrar}>Cancelar</Button><Button type="submit" form="form-catalogo" loading={guardar.pendiente}>Guardar</Button></>}>
      <form id="form-catalogo" onSubmit={handleSubmit(enviar)} noValidate className="grid gap-4 sm:grid-cols-2">
        {(mensaje("detail") || mensaje("non_field_errors")) && <p role="alert" className="text-sm text-brand-700 sm:col-span-2">{mensaje("detail") ?? mensaje("non_field_errors")}</p>}
        {campos.map((c) => {
          const comun = { ...register(c.nombre) };
          return c.tipo === "casilla" ? (
            <label key={c.nombre} className="flex cursor-pointer items-center gap-2 text-sm text-ink-700 sm:col-span-2">
              <input type="checkbox" className="h-4 w-4 rounded border-ink-300 accent-brand-600" {...comun} />{c.etiqueta}
            </label>
          ) : (
            <FormField key={c.nombre} label={c.etiqueta} required={c.requerido} error={mensaje(c.nombre)} hint={c.ayuda} className={c.ancho || c.tipo === "area" ? "sm:col-span-2" : undefined}>
              {c.tipo === "select" ? (
                <Select {...comun}><option value="">Selecciona...</option>{c.opciones?.map((o) => <option key={o.valor} value={o.valor}>{o.texto}</option>)}</Select>
              ) : c.tipo === "area" ? <Textarea {...comun} />
              : <Input type={c.tipo === "numero" ? "number" : c.tipo === "hora" ? "time" : c.tipo === "fechahora" ? "datetime-local" : "text"} {...comun} />}
            </FormField>
          );
        })}
      </form>
    </Modal>
  );
}

/** CRUD genérico para los catálogos de administración (RF3–RF5). */
export function CatalogoCrud(props: Props) {
  const { clave, titulo, singular, servicio, columnas, filtros } = props;
  const [edicion, setEdicion] = useState<{ fila?: Fila } | null>(null);
  const [borrar, setBorrar] = useState<Fila | null>(null);
  const toast = useToast();
  const { data, isLoading } = useApi([clave, filtros ?? {}], () => servicio.listar(filtros));
  const eliminar = useAccion((id: number) => servicio.eliminar(id), { invalidar: [clave], exito: `${singular} eliminado.` });

  const todas: Columna<Fila>[] = [
    ...columnas,
    { clave: "_acc", titulo: "", alinear: "right", render: (f) => (
      <span className="inline-flex gap-1">
        <Button size="sm" variant="ghost" aria-label={`Editar ${singular.toLowerCase()}`} icon={<Pencil className="h-4 w-4" />} onClick={() => setEdicion({ fila: f })} />
        <Button size="sm" variant="ghost" aria-label={`Eliminar ${singular.toLowerCase()}`} icon={<Trash2 className="h-4 w-4 text-brand-600" />} onClick={() => setBorrar(f)} />
      </span>
    ) },
  ];

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between gap-3">
        <h2 className="text-base font-semibold text-ink-900">{titulo}</h2>
        <Button size="sm" icon={<Plus className="h-4 w-4" />} onClick={() => setEdicion({})}>Nuevo {singular.toLowerCase()}</Button>
      </div>
      {isLoading ? <PageLoader /> : <Table columnas={todas} filas={(data?.results ?? []) as Fila[]} clave={(f) => f.id} vacio={{ titulo: `No hay ${titulo.toLowerCase()}`, descripcion: "Crea el primero con el botón de arriba." }} />}
      {edicion && <ModalFila key={edicion.fila?.id ?? "nuevo"} props={props} fila={edicion.fila} onCerrar={() => setEdicion(null)} />}
      <ConfirmDialog open={!!borrar} onClose={() => setBorrar(null)} danger loading={eliminar.pendiente}
        title={`Eliminar ${singular.toLowerCase()}`} message="Esta acción no se puede deshacer. Si otros registros lo usan, el sistema no lo permitirá." confirmText="Eliminar"
        onConfirm={() => borrar && eliminar.ejecutar(borrar.id, { onSuccess: () => setBorrar(null), onError: (e) => { toast.error(mensajeDeError(e, "No se pudo eliminar.")); setBorrar(null); } })} />
    </div>
  );
}

export const SiNo = ({ valor }: { valor: unknown }) => <Badge tono={valor ? "success" : "neutral"}>{valor ? "Sí" : "No"}</Badge>;
