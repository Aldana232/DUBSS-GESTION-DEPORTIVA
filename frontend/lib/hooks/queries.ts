"use client";
/** Hooks de React Query: lecturas con useApi/hooks por recurso y escrituras con useAccion (F4-03/F5). */
import { useCallback } from "react";
import { useMutation, useQueries, useQuery, useQueryClient } from "@tanstack/react-query";
import type { FieldValues, UseFormSetError } from "react-hook-form";
import { useToast } from "@/components/ui/Toast";
import { aplicarErroresDRF, mensajeDeError } from "@/lib/api/errors";
import {
  campeonatoService, categoriaService, equipoService, fixtureService, mlService,
} from "@/lib/api/services";
import type { PartidoResumen } from "@/types";

/** Lectura genérica: la clave empieza por el nombre del recurso para poder invalidar por prefijo. */
export function useApi<T>(clave: unknown[], consulta: () => Promise<T>, activo = true) {
  return useQuery({ queryKey: clave, queryFn: consulta, enabled: activo });
}

interface OpcionesAccion<A, R> {
  /** Recursos (primer elemento de la clave) que se refrescan al terminar. */
  invalidar?: string[];
  exito?: string | ((resultado: R, argumento: A) => string);
  error?: string;
}

/**
 * Escritura con aviso de éxito/error y refresco de datos. `ejecutar` acepta callbacks por llamada
 * (por ejemplo para cerrar un modal o llevar errores de campo a un formulario).
 */
export function useAccion<A = void, R = unknown>(accion: (argumento: A) => Promise<R>, opciones: OpcionesAccion<A, R> = {}) {
  const qc = useQueryClient();
  const toast = useToast();
  const mutacion = useMutation({ mutationFn: accion });
  const ejecutar = (
    argumento: A,
    callbacks?: { onSuccess?: (resultado: R) => void; onError?: (error: unknown) => void },
  ) =>
    mutacion.mutate(argumento, {
      onSuccess: (resultado) => {
        opciones.invalidar?.forEach((k) => qc.invalidateQueries({ queryKey: [k] }));
        const mensaje = typeof opciones.exito === "function" ? opciones.exito(resultado, argumento) : opciones.exito;
        if (mensaje) toast.success(mensaje);
        callbacks?.onSuccess?.(resultado);
      },
      onError: (e) => {
        if (callbacks?.onError) callbacks.onError(e);
        else toast.error(mensajeDeError(e, opciones.error));
      },
    });
  return { ejecutar, pendiente: mutacion.isPending };
}

/** Callback de error para formularios: errores 400 de DRF a sus campos; el resto, a un aviso. */
export function useErrorFormulario<T extends FieldValues>(setError: UseFormSetError<T>, campos: readonly string[]) {
  const toast = useToast();
  return useCallback(
    (e: unknown) => { if (!aplicarErroresDRF(e, setError, campos)) toast.error(mensajeDeError(e)); },
    [setError, campos, toast],
  );
}

/* ── Lecturas frecuentes ───────────────────────────────────────────────────────────────────── */
export const useCategorias = () => useApi(["categorias"], () => categoriaService.listar({ activa: true }));
export const useEquipos = () => useApi(["equipos"], () => equipoService.listar());
export const useCampeonatos = () => useApi(["campeonatos"], () => campeonatoService.listar({ ordering: "-fecha_inicio" }));
export const useCampeonato = (id: number) =>
  useApi(["campeonato", id], () => campeonatoService.obtener(id), Number.isFinite(id) && id > 0);
export const usePartidos = (campeonato = "", jornada = "", extra: Record<string, string> = {}) =>
  useApi(["partidos", campeonato, jornada, extra], () =>
    fixtureService.partidos({ campeonato: campeonato || undefined, jornada: jornada || undefined, ...extra }));
export const usePartido = (id: number) =>
  useApi(["partido", id], () => fixtureService.partido(id), Number.isFinite(id) && id > 0);
export const useTabla = (campeonato: string) =>
  useApi(["tabla", campeonato], () => fixtureService.tabla(campeonato), !!campeonato);
export const useTablero = (campeonato: string) =>
  useApi(["tablero", campeonato], () => mlService.tablero(campeonato), !!campeonato);
export const useEstadisticas = (campeonato: string) =>
  useApi(["estadisticas", campeonato], () => fixtureService.estadisticas(campeonato), !!campeonato);
export const useHistorial = (campeonato: number) =>
  useApi(["historial", campeonato], () => campeonatoService.historial(campeonato), Number.isFinite(campeonato) && campeonato > 0);

/** Recursos que se refrescan tras cambiar un partido, un resultado o la tabla. */
export const RECURSOS_PARTIDO = ["partido", "partidos", "tabla", "historial", "estadisticas", "campeonato"];

/** Equipos que administra el delegado autenticado. */
export const useMisEquipos = () => useApi(["mis-equipos"], () => equipoService.mios());

/** Partidos de varios equipos (calendario del delegado), sin repetir y en orden cronológico. */
export function usePartidosDeEquipos(equipoIds: number[]) {
  const consultas = useQueries({
    queries: equipoIds.map((id) => ({
      queryKey: ["partidos", "equipo", id],
      queryFn: () => fixtureService.partidos({ equipo: id, ordering: "fecha_hora" }),
    })),
  });
  const cargando = consultas.some((c) => c.isLoading);
  const vistos = new Map<number, PartidoResumen>();
  consultas.forEach((c) => c.data?.results.forEach((p) => vistos.set(p.id, p)));
  const partidos = Array.from(vistos.values()).sort((a, b) => a.fecha_hora.localeCompare(b.fecha_hora));
  return { partidos, cargando };
}
