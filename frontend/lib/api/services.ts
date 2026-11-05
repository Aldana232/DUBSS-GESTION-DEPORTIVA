/**
 * Servicios por recurso (F4-03). Ninguna página importa axios ni el cliente: usa los servicios
 * a través de los hooks de lib/hooks/queries.ts (useApi / useAccion).
 */
import api from "./client";
import type {
  Bloqueo, Campeonato, Cancha, Categoria, DatosResultado, Deporte, Elegibilidad, Equipo, Estadisticas,
  Facultad, FilaPosicion, HistorialJornada, HorarioCancha, Incidencia, Inscripcion, Instalacion, Jugador,
  NuevoCampeonato, Paginado, InformePredictor, RiesgoClima, Asistencia, AccionSugerida, EstadoAsistente, Interpretacion, ResultadoAsistente, CanalesNotificacion, ResumenEnvio, EstadisticasFacultad, EstadoAgente, ConversacionAgente, MensajeAgente, AccionAgente, AnalisisNiveles, AlertaAtipica, FichaPropia, PaquetePlanilla, ResumenGeneracion, CalidadFixture, ModeloAsignacion, PartidoDetalle, PartidoResumen, Prediccion, Queja, RegistroBitacora,
  RestriccionFacultad, Resultado, Usuario,
} from "@/types";

type Params = Record<string, string | number | boolean | undefined>;

/** CRUD genérico de un recurso REST de Django (listado con page_size alto por defecto). */
function recurso<T, N = Partial<T>>(base: string) {
  return {
    listar: (params?: Params) =>
      api.get<Paginado<T>>(base, { params: { page_size: 200, ...params } }).then((r) => r.data),
    obtener: (id: number) => api.get<T>(`${base}${id}/`).then((r) => r.data),
    crear: (datos: N) => api.post<T>(base, datos).then((r) => r.data),
    editar: (id: number, datos: Partial<N>) => api.patch<T>(`${base}${id}/`, datos).then((r) => r.data),
    eliminar: (id: number) => api.delete(`${base}${id}/`).then((r) => r.data),
  };
}

/* ── Sesión (cookies httpOnly vía route handlers de Next) ─────────────────────────────────── */
export const authService = {
  login: (email: string, password: string) =>
    fetch("/api/auth/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password }),
    }),
  logout: () => fetch("/api/auth/logout", { method: "POST" }),
  sesion: async (): Promise<Usuario | null> => {
    const r = await fetch("/api/auth/session", { cache: "no-store" });
    if (!r.ok) return null;
    return ((await r.json()) as { usuario: Usuario | null }).usuario;
  },
  cambiarPassword: (datos: { password_actual: string; password_nuevo: string; password_nuevo2: string }) =>
    fetch("/api/auth/cambio-password", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(datos),
    }),
};

export const perfilService = {
  editar: (datos: Partial<Pick<Usuario, "nombre" | "apellido" | "telefono" | "ci">>) =>
    api.patch<Usuario>("/usuarios/perfil/", datos).then((r) => r.data),
  subirFoto: (archivo: File) => {
    const form = new FormData();
    form.append("foto_perfil", archivo);
    return api
      .patch<Usuario>("/usuarios/perfil/", form, { headers: { "Content-Type": "multipart/form-data" } })
      .then((r) => r.data);
  },
};

/* ── Catálogos ────────────────────────────────────────────────────────────────────────────── */
export const deporteService = recurso<Deporte>("/deportes/deportes/");
export const categoriaService = recurso<Categoria, Omit<Categoria, "id" | "deporte_nombre">>("/deportes/categorias/");
export const facultadService = recurso<Facultad>("/deportes/facultades/");
export const restriccionService = recurso<RestriccionFacultad>("/deportes/restricciones-horario/");
export const instalacionService = recurso<Instalacion>("/instalaciones/instalaciones/");
export const canchaService = recurso<Cancha>("/instalaciones/canchas/");
export const horarioService = recurso<HorarioCancha>("/instalaciones/horarios/");
export const bloqueoService = recurso<Bloqueo>("/instalaciones/bloqueos/");

/* ── Equipos, jugadores e inscripciones ───────────────────────────────────────────────────── */
export const equipoService = {
  ...recurso<Equipo, { nombre: string; color: string; facultad: number }>("/deportes/equipos/"),
  mios: () => api.get<Equipo[]>("/mi-equipo/").then((r) => r.data),
};
export const jugadorService = recurso<Jugador, Omit<Jugador, "id" | "estado" | "partidos_sancion_restantes">>("/deportes/jugadores/");

export const inscripcionService = {
  ...recurso<Inscripcion, { campeonato: number; equipo: number }>("/deportes/inscripciones/"),
  elegibilidad: (id: number) => api.get<Elegibilidad>(`/deportes/inscripciones/${id}/elegibilidad/`).then((r) => r.data),
  validar: (id: number, estado: "APROBADA" | "RECHAZADA", observaciones?: string) =>
    api.patch<Inscripcion>(`/deportes/inscripciones/${id}/validar/`, { estado, observaciones }).then((r) => r.data),
};

/* ── Campeonatos y fixture ────────────────────────────────────────────────────────────────── */
export const campeonatoService = {
  ...recurso<Campeonato, NuevoCampeonato>("/deportes/campeonatos/"),
  cambiarEstado: (id: number, estado: string) =>
    api.patch<{ estado: string }>(`/deportes/campeonatos/${id}/estado/`, { estado }).then((r) => r.data),
  historial: (id: number) => api.get<HistorialJornada[]>(`/deportes/campeonatos/${id}/historial/`).then((r) => r.data),
};

export const fixtureService = {
  generar: (
    campeonatoId: number,
    opciones: { hora_inicio?: string; doble_vuelta?: boolean; dias_entre_jornadas?: number; usar_ml?: boolean; sembrar_con_ml?: boolean } = {},
  ) =>
    api.post<ResumenGeneracion>("/fixture/generar/", { campeonato_id: campeonatoId, ...opciones })
      .then((r) => r.data),
  hoy: () => api.get<PaquetePlanilla>("/fixture/planilla/paquete/", { params: { dias: 1 } }).then((r) => r.data),
  calidad: (campeonatoId: number | string) =>
    api.get<CalidadFixture>("/fixture/calidad/", { params: { campeonato: campeonatoId } }).then((r) => r.data),
  partidos: (params: Params) =>
    api.get<Paginado<PartidoResumen>>("/fixture/partidos/", { params: { page_size: 200, ...params } }).then((r) => r.data),
  partido: (id: number) => api.get<PartidoDetalle>(`/fixture/partidos/${id}/`).then((r) => r.data),
  reprogramar: (id: number, datos: { fecha_hora: string; cancha: number | null }) =>
    api.patch<PartidoDetalle>(`/fixture/partidos/${id}/`, datos).then((r) => r.data),
  registrarResultado: (id: number, datos: DatosResultado) =>
    api.post<Resultado>(`/fixture/partidos/${id}/resultado/`, datos).then((r) => r.data),
  corregirResultado: (id: number, datos: DatosResultado) =>
    api.patch<Resultado>(`/fixture/partidos/${id}/resultado/`, datos).then((r) => r.data),
  eliminarResultado: (id: number, motivo: string) =>
    api.delete(`/fixture/partidos/${id}/resultado/`, { data: { motivo } }).then((r) => r.data),
  registrarIncidencia: (
    id: number,
    datos: { tipo: string; jugador?: number | null; minuto?: number | null; descripcion?: string },
  ) => api.post<Incidencia & { partidos_sancion: number }>(`/fixture/partidos/${id}/incidencia/`, datos).then((r) => r.data),
  tabla: (campeonatoId: number | string) =>
    api.get<FilaPosicion[]>("/fixture/tabla-posiciones/", { params: { campeonato: campeonatoId } }).then((r) => r.data),
  estadisticas: (campeonatoId: number | string) =>
    api.get<Estadisticas>("/fixture/estadisticas/", { params: { campeonato: campeonatoId } }).then((r) => r.data),
};

export const mlService = {
  modeloAsignacion: () => api.get<ModeloAsignacion>("/ml/asignacion/").then((r) => r.data),
  reentrenarAsignacion: () => api.post<ModeloAsignacion>("/ml/asignacion/").then((r) => r.data),
  cabezasDeSerie: (campeonatoId: number, grupos?: number) =>
    api.post<AnalisisNiveles>("/ml/cabezas-de-serie/", { campeonato_id: campeonatoId, grupos }).then((r) => r.data),
  atipicos: (revisado?: boolean) =>
    api.get<{ pendientes: number; resultados: AlertaAtipica[] }>("/ml/atipicos/", { params: revisado === undefined ? {} : { revisado } }).then((r) => r.data),
  buscarAtipicos: () => api.post<{ nuevos: number; resultados: AlertaAtipica[] }>("/ml/atipicos/").then((r) => r.data),
  revisarAtipico: (id: number) => api.post<AlertaAtipica>(`/ml/atipicos/${id}/revisar/`).then((r) => r.data),
  informePredictor: () => api.get<InformePredictor>("/ml/entrenar/").then((r) => r.data),
  entrenarPredictor: () => api.post<InformePredictor>("/ml/entrenar/").then((r) => r.data),
  riesgo: (partidoId: number) => api.get<RiesgoClima>(`/ml/riesgo-climatico/${partidoId}/`).then((r) => r.data),
  actualizarRiesgo: (partidoId: number) => api.post<RiesgoClima>(`/ml/riesgo-climatico/${partidoId}/`).then((r) => r.data),
  asistencia: (partidoId: number) => api.get<Asistencia>(`/ml/asistencia/${partidoId}/`).then((r) => r.data),
  acciones: () => api.get<{ acciones: AccionSugerida[] }>("/ml/recomendaciones/").then((r) => r.data.acciones),
  tablero: (campeonatoId: number | string) =>
    api.get<Prediccion[]>("/ml/tablero/", { params: { campeonato: campeonatoId } }).then((r) => r.data),
};

/* ── Quejas, usuarios, bitácora y reportes ────────────────────────────────────────────────── */
export const quejaService = {
  ...recurso<Queja, { tipo: string; descripcion: string; encuentro: number }>("/quejas/quejas/"),
  mias: () => api.get<Paginado<Queja>>("/mis-quejas/", { params: { page_size: 200 } }).then((r) => r.data),
  resolver: (id: number, estado: string, resolucion: string) =>
    api.post<Queja>(`/quejas/quejas/${id}/resolver/`, { estado, resolucion }).then((r) => r.data),
};

export interface NuevoUsuario {
  email: string; nombre: string; apellido: string; ci?: string; telefono?: string;
  rol: string; facultad: number | null; password: string; password2: string;
}
export const usuarioService = {
  listar: (params?: Params) => api.get<Paginado<Usuario>>("/usuarios/", { params }).then((r) => r.data),
  crear: (datos: NuevoUsuario) => api.post<Usuario>("/usuarios/", datos).then((r) => r.data),
  editar: (id: number, datos: Partial<Usuario>) => api.patch<Usuario>(`/usuarios/${id}/`, datos).then((r) => r.data),
  baja: (id: number) => api.delete(`/usuarios/${id}/`).then((r) => r.data),
  restablecer: (id: number, datos: { password_nuevo: string; password_nuevo2?: string }) =>
    api.post(`/usuarios/${id}/restablecer-password/`, datos).then((r) => r.data),
};

export const bitacoraService = {
  listar: (params?: Params) => api.get<Paginado<RegistroBitacora>>("/auditoria/bitacora/", { params }).then((r) => r.data),
};

export const notificacionService = {
  canales: () => api.get<CanalesNotificacion>("/notificaciones/canales/").then((r) => r.data),
  enviar: (datos: { titulo: string; mensaje: string; todos?: boolean; roles?: string[]; facultad?: number | null }) =>
    api.post<ResumenEnvio>("/notificaciones/enviar/", datos).then((r) => r.data),
};

export const asistenteService = {
  estado: () => api.get<EstadoAsistente>("/asistente/estado/").then((r) => r.data),
  transcribir: (audio: Blob) => {
    const form = new FormData();
    form.append("audio", audio, "orden.webm");
    return api.post<{ texto: string }>("/asistente/transcribir/", form, { headers: { "Content-Type": "multipart/form-data" } })
      .then((r) => r.data);
  },
  interpretar: (texto: string, previo?: { intencion: string; formato: string | null; proveedor: string }, seleccion?: Record<string, number>) =>
    api.post<Interpretacion>("/asistente/interpretar/", { texto, previo, seleccion }).then((r) => r.data),
  ejecutar: (orden: { intencion: string; formato?: string | null; campeonato?: number; equipo?: number; jugador?: number }) =>
    api.post<ResultadoAsistente>("/asistente/ejecutar/", orden).then((r) => r.data),
};

export const agenteService = {
  estado: () => api.get<EstadoAgente>("/agente/estado/").then((r) => r.data),
  conversaciones: () => api.get<ConversacionAgente[]>("/agente/conversaciones/").then((r) => r.data),
  conversacion: (id: number) => api.get<ConversacionAgente & { mensajes: MensajeAgente[] }>(`/agente/conversaciones/${id}/`).then((r) => r.data),
  eliminar: (id: number) => api.delete(`/agente/conversaciones/${id}/`).then(() => undefined),
  // El agente puede tardar (varias consultas al modelo): se amplía el tiempo de espera del cliente.
  enviar: (texto: string, conversacion?: number | null) =>
    api.post<{ conversacion: number; respuesta: MensajeAgente }>("/agente/mensajes/", { texto, conversacion: conversacion ?? undefined }, { timeout: 120_000 })
      .then((r) => r.data),
  confirmar: (id: number) => api.post<AccionAgente>(`/agente/acciones/${id}/confirmar/`).then((r) => r.data),
  cancelar: (id: number) => api.post<AccionAgente>(`/agente/acciones/${id}/cancelar/`).then((r) => r.data),
};

export const jugadorPanelService = {
  miFicha: () => api.get<{ fichas: FichaPropia[] }>("/deportes/mi-ficha/").then((r) => r.data.fichas),
};

export const facultadStatsService = {
  obtener: (id: number) => api.get<EstadisticasFacultad>(`/reportes/facultad/${id}/`).then((r) => r.data),
};

export type TipoReporte = "campeonato" | "equipo" | "jugador" | "facultad";
export const reporteService = {
  /** Descarga autenticada como blob (F4-08): sin enlaces directos a la API. */
  descargar: async (tipo: TipoReporte, id: number, formato: "pdf" | "excel") => {
    const r = await api.get<Blob>(`/reportes/${tipo}/${id}/${formato}/`, { responseType: "blob" });
    const cabecera = String(r.headers["content-disposition"] ?? "");
    const nombre = /filename="?([^";]+)"?/i.exec(cabecera)?.[1] ?? `${tipo}-${id}.${formato === "pdf" ? "pdf" : "xlsx"}`;
    const url = URL.createObjectURL(r.data);
    const enlace = document.createElement("a");
    enlace.href = url;
    enlace.download = nombre;
    document.body.appendChild(enlace);
    enlace.click();
    enlace.remove();
    URL.revokeObjectURL(url);
  },
};
