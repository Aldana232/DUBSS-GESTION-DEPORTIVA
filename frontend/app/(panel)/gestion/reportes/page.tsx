"use client";
import { useState } from "react";
import { Download, FileSpreadsheet } from "lucide-react";
import { Button, Card, CardBody, CardHeader, FormField, PageHeader, Select, useToast } from "@/components/ui";
import { SelectorCampeonato } from "@/components/SelectorCampeonato";
import { useApi } from "@/lib/hooks/queries";
import { equipoService, facultadService, jugadorService, reporteService, type TipoReporte } from "@/lib/api/services";
import { mensajeDeError } from "@/lib/api/errors";

function Descargas({ tipo, id }: { tipo: TipoReporte; id: string }) {
  const toast = useToast();
  const [cargando, setCargando] = useState<"pdf" | "excel" | null>(null);
  const bajar = async (formato: "pdf" | "excel") => {
    setCargando(formato);
    try { await reporteService.descargar(tipo, Number(id), formato); toast.success("Reporte descargado."); }
    catch (e) { toast.error(mensajeDeError(e, "No se pudo descargar el reporte.")); }
    finally { setCargando(null); }
  };
  return (
    <div className="flex flex-wrap gap-2">
      <Button disabled={!id} loading={cargando === "pdf"} icon={<Download className="h-4 w-4" />} onClick={() => bajar("pdf")}>Descargar PDF</Button>
      <Button variant="secondary" disabled={!id} loading={cargando === "excel"} icon={<FileSpreadsheet className="h-4 w-4" />} onClick={() => bajar("excel")}>Descargar Excel</Button>
    </div>
  );
}

export default function GestionReportes() {
  const [campeonato, setCampeonato] = useState("");
  const [equipo, setEquipo] = useState("");
  const [equipoJ, setEquipoJ] = useState("");
  const [jugador, setJugador] = useState("");
  const [facultad, setFacultad] = useState("");
  const facultades = useApi(["facultades"], () => facultadService.listar());
  const equipos = useApi(["equipos"], () => equipoService.listar());
  const plantel = useApi(["jugadores", equipoJ], () => jugadorService.listar({ equipo: equipoJ }), !!equipoJ);

  return (
    <>
      <PageHeader title="Reportes" description="Exporta información en PDF o Excel. La descarga requiere tu sesión." />
      <div className="grid gap-5 lg:grid-cols-2 xl:grid-cols-4">
        <Card>
          <CardHeader title="Por campeonato" />
          <CardBody className="space-y-4">
            <p className="text-sm text-ink-500">Tabla de posiciones y fixture completo.</p>
            <FormField label="Campeonato"><SelectorCampeonato valor={campeonato} onCambiar={setCampeonato} vacio="Selecciona..." /></FormField>
            <Descargas tipo="campeonato" id={campeonato} />
          </CardBody>
        </Card>
        <Card>
          <CardHeader title="Por equipo" />
          <CardBody className="space-y-4">
            <p className="text-sm text-ink-500">Plantel con goles y tarjetas, y todos sus partidos.</p>
            <FormField label="Equipo">
              <Select value={equipo} onChange={(e) => setEquipo(e.target.value)}>
                <option value="">Selecciona...</option>
                {equipos.data?.results.map((e) => <option key={e.id} value={e.id}>{e.nombre} — {e.facultad_nombre}</option>)}
              </Select>
            </FormField>
            <Descargas tipo="equipo" id={equipo} />
          </CardBody>
        </Card>
        <Card>
          <CardHeader title="Por jugador" />
          <CardBody className="space-y-4">
            <p className="text-sm text-ink-500">Ficha, goles, tarjetas y sanciones.</p>
            <FormField label="Equipo">
              <Select value={equipoJ} onChange={(e) => { setEquipoJ(e.target.value); setJugador(""); }}>
                <option value="">Selecciona...</option>
                {equipos.data?.results.map((e) => <option key={e.id} value={e.id}>{e.nombre}</option>)}
              </Select>
            </FormField>
            <FormField label="Jugador">
              <Select value={jugador} onChange={(e) => setJugador(e.target.value)} disabled={!equipoJ}>
                <option value="">Selecciona...</option>
                {plantel.data?.results.map((j) => <option key={j.id} value={j.id}>{j.numero_camiseta != null ? `#${j.numero_camiseta} ` : ""}{j.nombre} {j.apellido}</option>)}
              </Select>
            </FormField>
            <Descargas tipo="jugador" id={jugador} />
          </CardBody>
        </Card>
        <Card>
          <CardHeader title="Por facultad" />
          <CardBody className="space-y-4">
            <p className="text-sm text-ink-500">Rendimiento de todos sus equipos, goleadores y tarjetas.</p>
            <FormField label="Facultad">
              <Select value={facultad} onChange={(e) => setFacultad(e.target.value)}>
                <option value="">Selecciona...</option>
                {facultades.data?.results.map((f) => <option key={f.id} value={f.id}>{f.nombre}</option>)}
              </Select>
            </FormField>
            <Descargas tipo="facultad" id={facultad} />
          </CardBody>
        </Card>
      </div>
    </>
  );
}
