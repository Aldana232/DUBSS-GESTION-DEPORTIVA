/** Tipos alineados con los serializers de Django (F4-03). */
import type { Rol } from "@/lib/auth/roles";

export type { Rol };

export interface Paginado<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}

export interface Usuario {
  id: number;
  email: string;
  nombre: string;
  apellido: string;
  nombre_completo: string;
  ci: string | null;
  telefono: string;
  foto_perfil: string | null;
  rol: Rol;
  facultad: number | null;
  is_active: boolean;
  ultimo_acceso: string | null;
}

export type EstadoCampeonato = "PLANIFICACION" | "INSCRIPCIONES" | "INSCRIPCION_CERRADA" | "EN_CURSO" | "FINALIZADO" | "CANCELADO";
export type EstadoPartido = "PROGRAMADO" | "EN_CURSO" | "FINALIZADO" | "SUSPENDIDO" | "POSTERGADO" | "WALKOVER";
export type FormatoCampeonato = "LIGA" | "ELIMINACION";

export interface Categoria {
  id: number;
  deporte: number;
  deporte_nombre: string;
  nombre: string;
  genero: string;
  activa: boolean;
}

export interface Campeonato {
  id: number;
  nombre: string;
  deporte: number;
  deporte_detalle?: { id: number; nombre: string };
  categoria: number;
  categoria_detalle?: Categoria;
  estado: EstadoCampeonato;
  transiciones_permitidas: EstadoCampeonato[];
  formato: FormatoCampeonato;
  fecha_inicio: string;
  fecha_fin: string;
  max_equipos: number;
  total_equipos: number;
  min_jugadores: number;
  max_jugadores: number;
  fecha_cierre_inscripcion: string | null;
  descripcion?: string;
  actualizado_en?: string;
}

export interface NuevoCampeonato {
  nombre: string;
  categoria: number;
  formato: FormatoCampeonato;
  fecha_inicio: string;
  fecha_fin: string;
  max_equipos: number;
  min_jugadores?: number;
  max_jugadores?: number;
  fecha_cierre_inscripcion?: string | null;
  descripcion?: string;
}

export interface EquipoResumen {
  id: number;
  nombre: string;
  facultad: string;
  color_principal: string;
}

export interface Jugador {
  id: number;
  equipo: number;
  nombre: string;
  apellido: string;
  carnet: string;
  registro: string;
  posicion: string;
  numero_camiseta: number | null;
  estado: string;
  partidos_sancion_restantes: number;
}

export interface Equipo {
  id: number;
  nombre: string;
  facultad: number;
  facultad_nombre: string;
  color: string;
  estado: string;
  cantidad_jugadores: number;
  jugadores?: Jugador[];
}

export interface Facultad { id: number; nombre: string; sigla: string }
export interface Deporte { id: number; nombre: string; descripcion: string; cantidad_jugadores: number; activo: boolean }
export interface Instalacion { id: number; nombre: string; tipo: string; ubicacion: string; capacidad: number; estado: string; total_canchas: number }
export interface Cancha {
  id: number; instalacion: number; instalacion_nombre: string; nombre: string; deporte: number;
  deporte_nombre: string; superficie: string; capacidad: number; techada: boolean; activa: boolean;
}
export interface HorarioCancha { id: number; cancha: number; dia_semana: number; hora_inicio: string; hora_fin: string }
export interface Bloqueo { id: number; cancha: number; fecha_inicio: string; fecha_fin: string; tipo: string; motivo: string }
export interface RestriccionFacultad { id: number; facultad: number; dia_semana: number; hora_inicio: string; hora_fin: string; motivo: string }

export type EstadoInscripcion = "PENDIENTE" | "APROBADA" | "RECHAZADA";
export interface Inscripcion {
  id: number;
  campeonato: number;
  campeonato_nombre: string;
  equipo: number;
  equipo_detalle: EquipoResumen;
  fecha_inscripcion: string;
  estado: EstadoInscripcion;
  observaciones: string;
  advertencias?: string[];
}
export interface Elegibilidad { bloqueantes: string[]; advertencias: string[]; aprobable: boolean }

export type EstadoQueja = "ABIERTA" | "EN_REVISION" | "RESUELTA" | "RECHAZADA";
export interface Queja {
  id: number;
  tipo: "QUEJA" | "APELACION";
  descripcion: string;
  estado: EstadoQueja;
  resolucion: string | null;
  fecha_hora: string;
  delegado_nombre: string | null;
  encuentro: number;
  encuentro_detalle: { id: number; local: string; visitante: string; fecha_hora: string; campeonato: string };
}

export interface RegistroBitacora {
  id: number;
  usuario: { id: number; nombre_completo: string; email: string } | null;
  usuario_email: string;
  accion: string;
  modulo: string;
  objeto_id: number | null;
  descripcion: string;
  detalle: Record<string, unknown>;
  resultado: "OK" | "DENEGADO" | "ERROR";
  ip_origen: string | null;
  fecha_hora: string;
}

export interface Estadisticas {
  resumen: {
    partidos_total: number; partidos_jugados: number; goles: number; promedio_goles: number;
    victorias_local: number; empates: number; victorias_visitante: number;
  };
  goleadores: { jugador_id: number; jugador: string; equipo: string; goles: number }[];
  tarjetas: { jugador_id: number; jugador: string; equipo: string; amarillas: number; rojas: number }[];
  mejor_ataque: { equipo: string; goles: number } | null;
  mejor_defensa: { equipo: string; goles: number } | null;
}

export interface HistorialJornada {
  jornada: number;
  posiciones: { equipo: number; equipo_nombre: string; posicion: number; puntos: number; pj: number; gf: number; gc: number }[];
}

/** Elemento del listado de partidos (PartidoResumenSerializer). */
export interface PartidoResumen {
  id: number;
  jornada: number;
  fase: string;
  ronda: number | null;
  local: string;
  visitante: string;
  cancha: string;
  fecha_hora: string;
  duracion_min: number;
  fecha_hora_fin: string;
  instalacion: number | null;
  estado: EstadoPartido;
  generado_por_ml: boolean;
  goles_local: number | null;
  goles_visitante: number | null;
}

export interface Resultado {
  id: number;
  goles_local: number;
  goles_visitante: number;
  penales_local: number | null;
  penales_visitante: number | null;
  walkover: boolean;
  ganador: { id: number; nombre: string } | null;
  es_empate: boolean;
  observaciones: string;
}

export interface Incidencia {
  id: number;
  tipo: string;
  minuto: number | null;
  descripcion: string;
  jugador: number | null;
  jugador_nombre: string | null;
  equipo_id: number | null;
}

export interface PartidoDetalle {
  id: number;
  campeonato: number;
  jornada: number;
  fase: string;
  fecha_hora: string;
  estado: EstadoPartido;
  equipo_local: number | null;
  equipo_visitante: number | null;
  equipo_local_detalle: EquipoResumen | null;
  equipo_visitante_detalle: EquipoResumen | null;
  cancha: number | null;
  duracion_min: number;
  cancha_detalle: { id: number; nombre: string } | null;
  resultado: Resultado | null;
  incidencias: Incidencia[];
}

export interface DatosResultado {
  goles_local?: number;
  goles_visitante?: number;
  walkover?: boolean;
  ganador_walkover?: "LOCAL" | "VISITANTE";
  penales_local?: number | null;
  penales_visitante?: number | null;
  observaciones?: string;
  motivo?: string;
}

export interface FilaPosicion {
  id: number;
  equipo: number;
  equipo_detalle: EquipoResumen;
  posicion: number;
  pj: number; pg: number; pe: number; pp: number;
  gf: number; gc: number;
  diferencia_goles: number;
  puntos: number;
}

export interface Prediccion {
  partido_id: number;
  local: string;
  visitante: string;
  fecha_hora: string;
  prob_local: number;
  prob_empate: number;
  prob_visitante: number;
  resultado_probable: "local" | "empate" | "visitante";
  confianza: number;
  datos_suficientes: boolean;
  modelo: string;
}

/** Métricas de calidad de un fixture (RF11). */
export interface CalidadFixture {
  partidos: number;
  conflictos: number;
  descanso_promedio_dias: number | null;
  descanso_minimo_dias: number | null;
  en_franja_ideal_pct: number | null;
  equidad_pct: number | null;
  generado_por_ml?: boolean;
}

export interface ResumenGeneracion {
  total_partidos: number;
  generado_por_ml: boolean;
  aviso: string;
  calidad: CalidadFixture | null;
  ml: { modelo_version: string; puntaje_medio: number; segundos: number; jornadas: number } | null;
  siembra?: Siembra | null;
}

export interface ModeloAsignacion {
  entrenado: boolean;
  version?: string;
  exactitud?: number;
  precision?: number;
  sensibilidad?: number;
  f1?: number;
  auc?: number;
  muestras?: number;
  muestras_reales?: number;
  etiquetado?: string;
  entrenado_en?: string;
  importancias?: Record<string, number>;
  muestras_totales?: number;
}

/** Informe del predictor de resultados (F6-01). */
export interface MetricasPrediccion { accuracy: number; log_loss: number; brier: number; ece: number }
export interface InformePredictor {
  entrenado: boolean;
  partidos_disponibles: number;
  minimo: number;
  metodo_actual: string;
  version?: string;
  fecha_entrenamiento?: string;
  es_activo?: boolean;
  supera_linea_base?: boolean;
  conclusion?: string;
  partidos_validacion?: number;
  cortes_walk_forward?: number;
  calibrado?: boolean;
  modelo?: MetricasPrediccion;
  linea_base_frecuencia?: MetricasPrediccion;
  linea_base_elo?: MetricasPrediccion;
  importancias?: Record<string, number>;
  motivo?: string;
}

export type NivelRiesgo = "BAJO" | "MEDIO" | "ALTO" | "CRITICO" | "SIN_DATOS";
export interface RiesgoClima {
  nivel_riesgo: NivelRiesgo;
  calculado: boolean;
  temperatura: number | null;
  precipitacion: number | null;
  viento: number | null;
  descripcion: string;
  recomendacion: string;
  fuente_api: string;
  consultado_en: string | null;
}
export interface Asistencia {
  asistencia_predicha: number;
  rango_min: number;
  rango_max: number;
  factores: Record<string, unknown> & { metodo?: string };
}
export interface AccionSugerida { prioridad: "ALTA" | "MEDIA" | "BAJA"; mensaje: string; enlace: string }

export interface EstadoAsistente { voz: boolean; llm: boolean; proveedor_llm: string }
export type IntencionAsistente =
  | "reporte_campeonato" | "tabla_posiciones" | "estadisticas_jugador" | "estadisticas_equipo" | "proximos_partidos" | "resumen_torneo";
export interface OpcionAsistente { id: number; nombre: string }
export interface Interpretacion {
  estado: "ok" | "aclaracion" | "no_entendido";
  texto: string;
  proveedor: string;
  intencion: IntencionAsistente | null;
  formato: "pdf" | "excel" | null;
  parametros: Partial<Record<"campeonato" | "equipo" | "jugador", OpcionAsistente>>;
  supuestos: string[];
  aclaracion: { campo: "campeonato" | "equipo" | "jugador"; pregunta: string; opciones: OpcionAsistente[] } | null;
  mensaje: string;
}
export type ResultadoAsistente =
  | { tipo: "descarga"; recurso: "campeonato" | "equipo" | "jugador"; id: number; formato: "pdf" | "excel"; nombre: string }
  | { tipo: "tabla"; campeonato: string; filas: { posicion: number; equipo: string; pj: number; pg: number; pe: number; pp: number; gf: number; gc: number; puntos: number }[] }
  | { tipo: "partidos"; partidos: { id: number; local: string; visitante: string; fecha_hora: string; cancha: string | null; jornada: number; campeonato: string }[] }
  | { tipo: "resumen"; campeonato: string; estado: string; equipos: number; partidos_jugados: number; partidos_total: number; goles: number; lider: string | null; goleador: { jugador: string; equipo: string; goles: number } | null; proximo_partido: string | null }
  | { tipo: "estadisticas_equipo"; datos: Record<string, unknown> & { equipo: string; facultad: string; pj: number; pg: number; pe: number; pp: number; gf: number; gc: number; puntos: number } }
  | { tipo: "estadisticas_jugador"; datos: { jugador: string; equipo: string; facultad: string; goles: number; amarillas: number; rojas: number; sancion_pendiente: number } };

export interface CanalesNotificacion { push: boolean; email: boolean }
export interface ResumenEnvio { mensaje: string; usuarios: number; email: number; push: number; push_configurado: boolean; email_configurado: boolean }
export interface EstadisticasFacultad {
  facultad: string; sigla: string; campeonatos: string[];
  totales: { pj: number; pg: number; pe: number; pp: number; gf: number; gc: number; dg: number; equipos: number; jugadores: number; amarillas: number; rojas: number };
  equipos: { equipo: string; pj: number; pg: number; pe: number; pp: number; gf: number; gc: number; dg: number; puntos: number }[];
  goleadores: { jugador: string; equipo: string; goles: number }[];
}

/* ── Agente del organizador (F7-A) ─────────────────────────────────────────────────────────── */
export type EstadoAccion = "PENDIENTE" | "CONFIRMADA" | "CANCELADA" | "EXPIRADA" | "FALLIDA";
export interface CambioPropuesto { partido: string; campeonato: string; jornada: number; antes: string; despues: string; clima: string | null }
export type DetalleAccion =
  | { tipo: "reprogramacion"; motivo: string; clima_verificado: boolean; cambios: CambioPropuesto[]; delegados: number; sin_solucion: { partido: string; motivo: string }[] }
  | { tipo: "notificacion"; titulo: string; mensaje: string; destinatarios: number; vista_previa: string[] };
export interface AccionAgente {
  id: number; herramienta: string; estado: EstadoAccion; resumen: string; detalle: DetalleAccion | Record<string, never>;
  resultado: Record<string, unknown>; creado_en: string; expira_en: string; resuelta_en: string | null;
}
export interface PasoAgente { herramienta: string; etiqueta: string; ok: boolean; detalle: string; argumentos?: Record<string, string> }
export interface MensajeAgente {
  id: number; rol: "USUARIO" | "AGENTE"; contenido: string; pasos: PasoAgente[];
  descargas: { recurso: "campeonato" | "equipo" | "facultad"; id: number; formato: "pdf" | "excel"; nombre: string }[];
  acciones: AccionAgente[]; creado_en: string;
}
export interface ConversacionAgente { id: number; titulo: string; creado_en: string; actualizado_en: string }
export interface EstadoAgente {
  disponible: boolean; modelo: string | null; limite_por_hora: number; vigencia_minutos: number;
  herramientas: { nombre: string; tipo: "LECTURA" | "CALCULO" | "ESCRITURA"; etiqueta: string }[];
}

/* ── Planilla móvil sin conexión (F7-B) ────────────────────────────────────────────────────── */
export type TipoIncidencia = "GOL" | "TARJETA_AMARILLA" | "TARJETA_ROJA" | "LESION" | "SUSTITUCION" | "OTRO";
export interface JugadorPlanilla { id: number; nombre: string; apellido: string; numero: number | null; posicion: string; sancionado: boolean; partidos_sancion: number }
export interface EquipoPlanilla { id: number; nombre: string; color: string; jugadores: JugadorPlanilla[] }
export interface IncidenciaPlanilla { id: number; tipo: TipoIncidencia; jugador: number | null; minuto: number | null; descripcion: string }
export interface ResultadoPlanilla { goles_local: number; goles_visitante: number; penales_local: number | null; penales_visitante: number | null }
export interface PartidoPlanilla {
  id: number; jornada: number; fase: string; estado: string; fecha_hora: string; duracion_min: number;
  campeonato: { id: number; nombre: string; formato: "LIGA" | "ELIMINACION" };
  cancha: string | null; local: EquipoPlanilla; visitante: EquipoPlanilla;
  incidencias: IncidenciaPlanilla[]; resultado: ResultadoPlanilla | null;
}
export interface PaquetePlanilla { generado_en: string; usuario: number; partidos: PartidoPlanilla[] }

/* ── Análisis avanzado (F7-C) ──────────────────────────────────────────────────────────────── */
export interface EquipoNivel {
  equipo_id: number; nombre: string; facultad: string; sigla: string; nivel: number | null; fuerza: number | null;
  partidos: number; ppp: number | null; dg_pp: number | null; forma: number | null; sin_historial: boolean; semilla: number;
}
export interface AnalisisNiveles {
  campeonato: { id: number; nombre: string; formato: "LIGA" | "ELIMINACION"; deporte: string };
  equipos_total: number; metodo: "kmeans" | "inscripcion"; datos_suficientes: boolean; k: number; silueta: number | null; motivo: string;
  niveles: { nivel: number; etiqueta: string; equipos: number[]; fuerza_media: number }[];
  equipos: EquipoNivel[]; orden_siembra: number[]; cabezas_de_serie: number[];
  grupos: { nombre: string; equipos: number[]; fuerza_media: number | null }[];
  balance: { diferencia_max: number } | null;
}
export interface AlertaAtipica {
  id: number; partido_id: number; partido: string; campeonato: string; marcador: string; fecha: string;
  puntaje: number; motivo: string; detectado_en: string; revisado: boolean; revisado_en: string | null;
}
export interface Siembra { aplicada: boolean; motivo: string; metodo?: string; niveles?: number; orden?: { semilla: number; equipo: string; nivel: number | null }[] }

/* ── Panel del jugador (F7-10) ─────────────────────────────────────────────────────────────── */
export interface FichaPropia {
  id: number; nombre: string; apellido: string; numero: number | null; posicion: string; estado: string;
  equipo: { id: number; nombre: string; color: string; facultad: string; sigla: string };
  estadisticas: { goles: number; amarillas: number; rojas: number; sancion_pendiente: number };
  sancion: { partidos_restantes: number; mensaje: string | null };
  proximos_partidos: { id: number; fecha_hora: string; rival: string; es_local: boolean; cancha: string | null; campeonato: string; jornada: number }[];
  ultimos_resultados: { id: number; fecha_hora: string; rival: string; marcador: string; resultado: "G" | "E" | "P"; campeonato: string }[];
}
