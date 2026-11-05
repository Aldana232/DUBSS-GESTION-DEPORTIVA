"use client";
import { useState } from "react";
import { PageHeader, Tabs, type Columna } from "@/components/ui";
import { CatalogoCrud, SiNo, type CampoCatalogo } from "@/components/gestion/CatalogoCrud";
import { useApi } from "@/lib/hooks/queries";
import {
  bloqueoService, canchaService, categoriaService, deporteService, facultadService, horarioService,
  instalacionService, restriccionService,
} from "@/lib/api/services";
import { DIAS_SEMANA, etiqueta, fechaDia, hora } from "@/lib/utils";

type Fila = { id: number } & Record<string, unknown>;
const col = (clave: string, titulo: string, render?: (f: Fila) => React.ReactNode): Columna<Fila> => ({
  clave, titulo, render: render ?? ((f) => String(f[clave] ?? "—")),
});
const horaTexto = (v: unknown) => String(v ?? "").slice(0, 5);

export default function GestionCatalogos() {
  const [pestana, setPestana] = useState("deportes");
  const deportes = useApi(["deportes"], () => deporteService.listar());
  const instalaciones = useApi(["instalaciones"], () => instalacionService.listar());
  const canchas = useApi(["canchas"], () => canchaService.listar());
  const facultades = useApi(["facultades"], () => facultadService.listar());

  const opDeportes = (deportes.data?.results ?? []).map((d) => ({ valor: d.id, texto: d.nombre }));
  const opInstalaciones = (instalaciones.data?.results ?? []).map((i) => ({ valor: i.id, texto: i.nombre }));
  const opCanchas = (canchas.data?.results ?? []).map((c) => ({ valor: c.id, texto: `${c.instalacion_nombre} — ${c.nombre}` }));
  const opFacultades = (facultades.data?.results ?? []).map((f) => ({ valor: f.id, texto: `${f.sigla} — ${f.nombre}` }));
  const opDias = DIAS_SEMANA.map((d, i) => ({ valor: i, texto: d }));
  const nombreDe = (lista: { valor: number | string; texto: string }[], id: unknown) => lista.find((o) => o.valor === id)?.texto ?? "—";

  const hora_: CampoCatalogo[] = [
    { nombre: "hora_inicio", etiqueta: "Hora de inicio", tipo: "hora", requerido: true },
    { nombre: "hora_fin", etiqueta: "Hora de fin", tipo: "hora", requerido: true },
  ];

  return (
    <>
      <PageHeader title="Catálogos" description="Deportes, categorías, instalaciones, canchas, horarios y bloqueos de mantenimiento." />
      <Tabs activa={pestana} onCambiar={setPestana} pestanas={[
        {
          id: "deportes", label: "Deportes",
          contenido: <CatalogoCrud clave="deportes" titulo="Deportes" singular="Deporte" servicio={deporteService}
            campos={[
              { nombre: "nombre", etiqueta: "Nombre", tipo: "texto", requerido: true },
              { nombre: "cantidad_jugadores", etiqueta: "Jugadores por equipo en cancha", tipo: "numero", requerido: true, inicial: 11 },
              { nombre: "descripcion", etiqueta: "Descripción", tipo: "area" },
              { nombre: "activo", etiqueta: "Activo", tipo: "casilla", inicial: true },
            ]}
            columnas={[col("nombre", "Nombre"), col("cantidad_jugadores", "Jugadores"), col("activo", "Activo", (f) => <SiNo valor={f.activo} />)]} />,
        },
        {
          id: "categorias", label: "Categorías",
          contenido: <CatalogoCrud clave="categorias" titulo="Categorías" singular="Categoría" servicio={categoriaService}
            campos={[
              { nombre: "deporte", etiqueta: "Deporte", tipo: "select", requerido: true, opciones: opDeportes },
              { nombre: "nombre", etiqueta: "Nombre", tipo: "texto", requerido: true },
              { nombre: "genero", etiqueta: "Género", tipo: "select", requerido: true, inicial: "VARONES", opciones: [{ valor: "VARONES", texto: "Varones" }, { valor: "DAMAS", texto: "Damas" }, { valor: "MIXTO", texto: "Mixto" }] },
              { nombre: "rango_edad", etiqueta: "Rango de edad", tipo: "texto", inicial: "GENERAL" },
              { nombre: "descripcion", etiqueta: "Descripción", tipo: "area" },
              { nombre: "activa", etiqueta: "Activa", tipo: "casilla", inicial: true },
            ]}
            columnas={[col("deporte_nombre", "Deporte"), col("nombre", "Nombre"), col("genero", "Género", (f) => etiqueta(String(f.genero))), col("activa", "Activa", (f) => <SiNo valor={f.activa} />)]} />,
        },
        {
          id: "facultades", label: "Facultades",
          contenido: <CatalogoCrud clave="facultades" titulo="Facultades" singular="Facultad" servicio={facultadService}
            campos={[{ nombre: "nombre", etiqueta: "Nombre", tipo: "texto", requerido: true, ancho: true }, { nombre: "sigla", etiqueta: "Sigla", tipo: "texto", requerido: true }]}
            columnas={[col("sigla", "Sigla"), col("nombre", "Nombre")]} />,
        },
        {
          id: "instalaciones", label: "Instalaciones",
          contenido: <CatalogoCrud clave="instalaciones" titulo="Instalaciones" singular="Instalación" servicio={instalacionService}
            campos={[
              { nombre: "nombre", etiqueta: "Nombre", tipo: "texto", requerido: true },
              { nombre: "tipo", etiqueta: "Tipo", tipo: "texto", ayuda: "Ej.: Coliseo, Estadio, Gimnasio." },
              { nombre: "ubicacion", etiqueta: "Ubicación", tipo: "texto", requerido: true, ancho: true },
              { nombre: "capacidad", etiqueta: "Capacidad", tipo: "numero", inicial: 0 },
            ]}
            columnas={[col("nombre", "Nombre"), col("tipo", "Tipo"), col("ubicacion", "Ubicación"), col("capacidad", "Capacidad"), col("total_canchas", "Canchas")]} />,
        },
        {
          id: "canchas", label: "Canchas",
          contenido: <CatalogoCrud clave="canchas" titulo="Canchas" singular="Cancha" servicio={canchaService}
            campos={[
              { nombre: "instalacion", etiqueta: "Instalación", tipo: "select", requerido: true, opciones: opInstalaciones },
              { nombre: "nombre", etiqueta: "Nombre o número", tipo: "texto", requerido: true },
              { nombre: "deporte", etiqueta: "Deporte", tipo: "select", requerido: true, opciones: opDeportes },
              { nombre: "superficie", etiqueta: "Superficie", tipo: "select", opciones: [
                { valor: "CESPED_NATURAL", texto: "Césped natural" }, { valor: "CESPED_SINTETICO", texto: "Césped sintético" },
                { valor: "PARQUET", texto: "Parquet" }, { valor: "CEMENTO", texto: "Cemento" }, { valor: "TIERRA", texto: "Tierra" }] },
              { nombre: "capacidad", etiqueta: "Capacidad de espectadores", tipo: "numero", inicial: 0 },
              { nombre: "techada", etiqueta: "Techada", tipo: "casilla" },
              { nombre: "activa", etiqueta: "Activa", tipo: "casilla", inicial: true },
            ]}
            columnas={[col("instalacion_nombre", "Instalación"), col("nombre", "Cancha"), col("deporte_nombre", "Deporte"), col("techada", "Techada", (f) => <SiNo valor={f.techada} />), col("activa", "Activa", (f) => <SiNo valor={f.activa} />)]} />,
        },
        {
          id: "horarios", label: "Horarios",
          contenido: <CatalogoCrud clave="horarios" titulo="Horarios de canchas" singular="Horario" servicio={horarioService}
            campos={[{ nombre: "cancha", etiqueta: "Cancha", tipo: "select", requerido: true, opciones: opCanchas, ancho: true },
              { nombre: "dia_semana", etiqueta: "Día de la semana", tipo: "select", requerido: true, opciones: opDias }, ...hora_]}
            columnas={[col("cancha", "Cancha", (f) => nombreDe(opCanchas, f.cancha)), col("dia_semana", "Día", (f) => DIAS_SEMANA[Number(f.dia_semana)]), col("hora_inicio", "Desde", (f) => horaTexto(f.hora_inicio)), col("hora_fin", "Hasta", (f) => horaTexto(f.hora_fin))]} />,
        },
        {
          id: "bloqueos", label: "Bloqueos",
          contenido: <CatalogoCrud clave="bloqueos" titulo="Bloqueos de mantenimiento" singular="Bloqueo" servicio={bloqueoService}
            campos={[{ nombre: "cancha", etiqueta: "Cancha", tipo: "select", requerido: true, opciones: opCanchas, ancho: true },
              { nombre: "fecha_inicio", etiqueta: "Desde", tipo: "fechahora", requerido: true }, { nombre: "fecha_fin", etiqueta: "Hasta", tipo: "fechahora", requerido: true },
              { nombre: "tipo", etiqueta: "Tipo", tipo: "select", requerido: true, inicial: "MANTENIMIENTO", opciones: [{ valor: "MANTENIMIENTO", texto: "Mantenimiento" }, { valor: "EVENTO", texto: "Evento" }, { valor: "OTRO", texto: "Otro" }] },
              { nombre: "motivo", etiqueta: "Motivo", tipo: "texto", requerido: true }]}
            columnas={[col("cancha", "Cancha", (f) => nombreDe(opCanchas, f.cancha)), col("fecha_inicio", "Desde", (f) => `${fechaDia(String(f.fecha_inicio))} ${hora(String(f.fecha_inicio))}`), col("fecha_fin", "Hasta", (f) => `${fechaDia(String(f.fecha_fin))} ${hora(String(f.fecha_fin))}`), col("tipo", "Tipo", (f) => etiqueta(String(f.tipo))), col("motivo", "Motivo")]} />,
        },
        {
          id: "restricciones", label: "Restricciones de facultad",
          contenido: <CatalogoCrud clave="restricciones" titulo="Restricciones horarias de facultades" singular="Restricción" servicio={restriccionService}
            campos={[{ nombre: "facultad", etiqueta: "Facultad", tipo: "select", requerido: true, opciones: opFacultades, ancho: true },
              { nombre: "dia_semana", etiqueta: "Día de la semana", tipo: "select", requerido: true, opciones: opDias }, ...hora_,
              { nombre: "motivo", etiqueta: "Motivo", tipo: "texto", ayuda: "Ej.: Clases, exámenes." }]}
            columnas={[col("facultad", "Facultad", (f) => nombreDe(opFacultades, f.facultad)), col("dia_semana", "Día", (f) => DIAS_SEMANA[Number(f.dia_semana)]), col("hora_inicio", "Desde", (f) => horaTexto(f.hora_inicio)), col("hora_fin", "Hasta", (f) => horaTexto(f.hora_fin)), col("motivo", "Motivo")]} />,
        },
      ]} />
    </>
  );
}
