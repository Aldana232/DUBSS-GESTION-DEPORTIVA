"use client";
import { useState } from "react";
import { notFound } from "next/navigation";
import { Inbox, Plus, Trophy } from "lucide-react";
import {
  Badge, Button, Card, CardBody, CardHeader, Checkbox, ConfirmDialog, EmptyState, EstadoBadge, FormField,
  Input, Modal, PageHeader, Select, Spinner, Table, Tabs, Textarea, useToast, type Columna,
} from "@/components/ui";

interface Fila { id: number; equipo: string; puntos: number }
const FILAS: Fila[] = [
  { id: 1, equipo: "Ingeniería", puntos: 9 },
  { id: 2, equipo: "Medicina", puntos: 6 },
  { id: 3, equipo: "Derecho", puntos: 3 },
];
const COLUMNAS: Columna<Fila>[] = [
  { clave: "equipo", titulo: "Equipo", render: (f) => f.equipo },
  { clave: "puntos", titulo: "Pts", alinear: "center", render: (f) => f.puntos },
];

function Seccion({ titulo, children }: { titulo: string; children: React.ReactNode }) {
  return (
    <Card className="mb-5">
      <CardHeader title={titulo} />
      <CardBody className="flex flex-wrap items-start gap-3">{children}</CardBody>
    </Card>
  );
}

/** Catálogo de componentes (solo desarrollo): sirve para revisar el diseño en 360, 768 y 1280 px. */
export default function UiKitPage() {
  if (process.env.NODE_ENV === "production") notFound();
  const toast = useToast();
  const [modal, setModal] = useState(false);
  const [confirmar, setConfirmar] = useState(false);
  const [pestana, setPestana] = useState("a");

  return (
    <>
      <PageHeader title="Catálogo de componentes" description="Vista de desarrollo de la librería components/ui." />

      <Seccion titulo="Botones">
        <Button>Primario</Button>
        <Button variant="secondary">Secundario</Button>
        <Button variant="ghost">Fantasma</Button>
        <Button variant="danger">Peligro</Button>
        <Button icon={<Plus className="h-4 w-4" />}>Con ícono</Button>
        <Button loading>Cargando</Button>
        <Button disabled>Deshabilitado</Button>
        <Button size="sm">Pequeño</Button>
        <Button size="lg">Grande</Button>
      </Seccion>

      <Seccion titulo="Insignias">
        <Badge>Neutral</Badge><Badge tono="brand">Marca</Badge><Badge tono="success">Éxito</Badge>
        <Badge tono="info">Info</Badge><Badge tono="warning">Aviso</Badge><Badge tono="danger">Peligro</Badge>
        <EstadoBadge estado="EN_CURSO" /><EstadoBadge estado="INSCRIPCIONES" /><EstadoBadge estado="CANCELADO" />
      </Seccion>

      <Seccion titulo="Formulario">
        <div className="grid w-full gap-4 sm:grid-cols-2">
          <FormField label="Nombre" required hint="Texto de ayuda."><Input placeholder="Escribe aquí" /></FormField>
          <FormField label="Con error" error="Este campo es obligatorio."><Input /></FormField>
          <FormField label="Selección"><Select defaultValue="a"><option value="a">Opción A</option><option value="b">Opción B</option></Select></FormField>
          <FormField label="Texto largo"><Textarea /></FormField>
          <Checkbox label="Casilla de verificación" />
        </div>
      </Seccion>

      <Seccion titulo="Tabla y estado vacío">
        <div className="w-full space-y-4">
          <Table columnas={COLUMNAS} filas={FILAS} clave={(f) => f.id} resaltar={(_, i) => i === 0} />
          <Table columnas={COLUMNAS} filas={[]} clave={(f) => f.id} vacio={{ titulo: "Sin datos", descripcion: "Aquí aparecerán los registros." }} />
          <EmptyState icon={Trophy} title="Estado vacío" description="Con ícono, texto y acción." action={<Button size="sm" icon={<Inbox className="h-4 w-4" />}>Acción</Button>} />
        </div>
      </Seccion>

      <Seccion titulo="Pestañas">
        <div className="w-full">
          <Tabs activa={pestana} onCambiar={setPestana} pestanas={[
            { id: "a", label: "Primera", contenido: <p className="text-sm text-ink-600">Contenido de la primera pestaña.</p> },
            { id: "b", label: "Segunda", contenido: <p className="text-sm text-ink-600">Contenido de la segunda pestaña.</p> },
          ]} />
        </div>
      </Seccion>

      <Seccion titulo="Superposiciones y avisos">
        <Button variant="secondary" onClick={() => setModal(true)}>Abrir modal</Button>
        <Button variant="secondary" onClick={() => setConfirmar(true)}>Confirmar acción</Button>
        <Button variant="secondary" onClick={() => toast.success("Operación realizada.")}>Toast éxito</Button>
        <Button variant="secondary" onClick={() => toast.error("No se pudo completar la acción.")}>Toast error</Button>
        <Button variant="secondary" onClick={() => toast.info("Información para el usuario.")}>Toast info</Button>
        <Spinner />
      </Seccion>

      <Modal open={modal} onClose={() => setModal(false)} title="Ejemplo de modal" footer={<Button onClick={() => setModal(false)}>Entendido</Button>}>
        <p className="text-sm text-ink-600">Cierra con Escape, con el fondo o con el botón. El foco queda atrapado dentro.</p>
      </Modal>
      <ConfirmDialog open={confirmar} onClose={() => setConfirmar(false)} onConfirm={() => setConfirmar(false)} title="¿Eliminar registro?" message="Esta acción no se puede deshacer." confirmText="Eliminar" danger />
    </>
  );
}
