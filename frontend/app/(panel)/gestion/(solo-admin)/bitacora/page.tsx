"use client";
import { useState } from "react";
import { Eye, Search } from "lucide-react";
import { Badge, Button, Input, Modal, PageHeader, PageLoader, Select, Table, type BadgeTono, type Columna } from "@/components/ui";
import { useApi } from "@/lib/hooks/queries";
import { bitacoraService } from "@/lib/api/services";
import { etiqueta, fechaCorta, hora } from "@/lib/utils";
import type { RegistroBitacora } from "@/types";

const ACCIONES = [
  "LOGIN", "LOGIN_FALLIDO", "CUENTA_BLOQUEADA", "LOGOUT", "CAMBIO_PASSWORD", "CREAR", "EDITAR", "ELIMINAR", "CAMBIO_ROL",
  "CAMBIO_ESTADO", "GENERAR_FIXTURE", "REGISTRAR_RESULTADO", "CORREGIR_RESULTADO", "REGISTRAR_INCIDENCIA", "EXPORTAR", "ML_PRED", "ACCESO_DENEGADO",
];
const MODULOS = ["usuario", "campeonato", "equipo", "ficha_jugador", "inscripcion", "partido", "queja", "jugador", "api"];
const TONO: Record<string, BadgeTono> = { OK: "success", DENEGADO: "danger", ERROR: "warning" };

export default function GestionBitacora() {
  const [pagina, setPagina] = useState(1);
  const [filtro, setFiltro] = useState({ accion: "", modulo: "", resultado: "", desde: "", hasta: "", buscar: "" });
  const [detalle, setDetalle] = useState<RegistroBitacora | null>(null);
  const cambiar = (campo: keyof typeof filtro) => (valor: string) => { setFiltro((f) => ({ ...f, [campo]: valor })); setPagina(1); };

  const { data, isLoading } = useApi(["bitacora", pagina, filtro], () => bitacoraService.listar({
    page: pagina, accion: filtro.accion || undefined, modulo: filtro.modulo || undefined, resultado: filtro.resultado || undefined,
    search: filtro.buscar || undefined,
    fecha_hora__gte: filtro.desde ? new Date(`${filtro.desde}T00:00:00`).toISOString() : undefined,
    fecha_hora__lte: filtro.hasta ? new Date(`${filtro.hasta}T23:59:59`).toISOString() : undefined,
  }));

  const columnas: Columna<RegistroBitacora>[] = [
    { clave: "f", titulo: "Fecha", render: (r) => <span className="whitespace-nowrap">{fechaCorta(r.fecha_hora)} {hora(r.fecha_hora)}</span> },
    { clave: "u", titulo: "Usuario", render: (r) => r.usuario?.nombre_completo ?? (r.usuario_email || "—") },
    { clave: "a", titulo: "Acción", render: (r) => etiqueta(r.accion) },
    { clave: "m", titulo: "Módulo", render: (r) => (r.modulo ? `${etiqueta(r.modulo)}${r.objeto_id ? ` #${r.objeto_id}` : ""}` : "—") },
    { clave: "d", titulo: "Descripción", render: (r) => <span className="text-xs text-ink-600">{r.descripcion || "—"}</span> },
    { clave: "r", titulo: "Resultado", render: (r) => <Badge tono={TONO[r.resultado]}>{etiqueta(r.resultado)}</Badge> },
    { clave: "v", titulo: "", alinear: "right", render: (r) => <Button size="sm" variant="ghost" aria-label="Ver detalle" icon={<Eye className="h-4 w-4" />} onClick={() => setDetalle(r)} /> },
  ];

  return (
    <>
      <PageHeader title="Bitácora" description="Registro de las acciones críticas del sistema. Nunca incluye contraseñas ni tokens." />
      <div className="mb-5 grid gap-3 sm:grid-cols-2 lg:grid-cols-6">
        <div className="lg:col-span-2"><Input aria-label="Buscar" placeholder="Buscar por descripción o correo" leading={<Search className="h-4 w-4" />} value={filtro.buscar} onChange={(e) => cambiar("buscar")(e.target.value)} /></div>
        <Select aria-label="Acción" value={filtro.accion} onChange={(e) => cambiar("accion")(e.target.value)}><option value="">Todas las acciones</option>{ACCIONES.map((a) => <option key={a} value={a}>{etiqueta(a)}</option>)}</Select>
        <Select aria-label="Módulo" value={filtro.modulo} onChange={(e) => cambiar("modulo")(e.target.value)}><option value="">Todos los módulos</option>{MODULOS.map((m) => <option key={m} value={m}>{etiqueta(m)}</option>)}</Select>
        <Select aria-label="Resultado" value={filtro.resultado} onChange={(e) => cambiar("resultado")(e.target.value)}><option value="">Cualquier resultado</option><option value="OK">Correcto</option><option value="DENEGADO">Denegado</option><option value="ERROR">Error</option></Select>
        <div className="flex gap-2">
          <Input type="date" aria-label="Desde" value={filtro.desde} onChange={(e) => cambiar("desde")(e.target.value)} />
          <Input type="date" aria-label="Hasta" value={filtro.hasta} onChange={(e) => cambiar("hasta")(e.target.value)} />
        </div>
      </div>
      {isLoading ? <PageLoader /> : (
        <Table columnas={columnas} filas={data?.results ?? []} clave={(r) => r.id}
          pagina={{ actual: pagina, total: Math.ceil((data?.count ?? 0) / 20), onCambiar: setPagina }}
          vacio={{ titulo: "No hay registros con esos filtros" }} />
      )}
      <Modal open={!!detalle} onClose={() => setDetalle(null)} title="Detalle del registro" size="lg" footer={<Button variant="secondary" onClick={() => setDetalle(null)}>Cerrar</Button>}>
        {detalle && (
          <dl className="space-y-3 text-sm">
            <div><dt className="text-xs text-ink-500">Usuario</dt><dd>{detalle.usuario?.nombre_completo ?? detalle.usuario_email ?? "—"} ({detalle.ip_origen ?? "sin IP"})</dd></div>
            <div><dt className="text-xs text-ink-500">Descripción</dt><dd>{detalle.descripcion || "—"}</dd></div>
            <div><dt className="text-xs text-ink-500">Datos adicionales</dt><dd><pre className="overflow-x-auto rounded-lg bg-ink-50 p-3 text-xs">{JSON.stringify(detalle.detalle, null, 2)}</pre></dd></div>
          </dl>
        )}
      </Modal>
    </>
  );
}
