import axios from "axios";
import type { FieldValues, Path, UseFormSetError } from "react-hook-form";

const POR_ESTADO: Record<number, string> = {
  401: "Tu sesión expiró. Inicia sesión de nuevo.",
  403: "No tienes permisos para realizar esta acción.",
  404: "No se encontró lo que buscas.",
  409: "La acción entra en conflicto con otros datos del sistema.",
  429: "Demasiados intentos. Espera un momento e inténtalo de nuevo.",
  500: "Ocurrió un error en el servidor. Inténtalo de nuevo más tarde.",
  502: "No se pudo conectar con el servidor.",
};

type Cuerpo = Record<string, unknown> | string | unknown[] | undefined;

const aTexto = (valor: unknown): string[] => {
  if (typeof valor === "string") return [valor];
  if (Array.isArray(valor)) return valor.flatMap(aTexto);
  if (valor && typeof valor === "object") return Object.values(valor).flatMap(aTexto);
  return [];
};

/** Mensaje legible en español a partir de cualquier error de la API (RNF09). */
export function mensajeDeError(error: unknown, porDefecto = "No se pudo completar la acción."): string {
  if (!axios.isAxiosError(error)) return porDefecto;
  const status = error.response?.status;
  const cuerpo = error.response?.data as Cuerpo;
  if (cuerpo && typeof cuerpo === "object" && !Array.isArray(cuerpo)) {
    const directo = cuerpo.detail ?? cuerpo.error ?? cuerpo.mensaje;
    if (typeof directo === "string") return directo;
  }
  if (status === 400 || status === 409) {
    const textos = aTexto(cuerpo);
    if (textos.length) return textos.join(" ");
  }
  if (status && POR_ESTADO[status]) return POR_ESTADO[status];
  if (!error.response) return "No hay conexión con el servidor. Revisa tu red.";
  return porDefecto;
}

/**
 * Lleva los errores de campo de DRF (400) a react-hook-form.
 * Devuelve true si al menos un campo recibió su error; si no, conviene mostrar un toast.
 */
export function aplicarErroresDRF<T extends FieldValues>(
  error: unknown,
  setError: UseFormSetError<T>,
  campos: readonly string[],
): boolean {
  if (!axios.isAxiosError(error) || error.response?.status !== 400) return false;
  const cuerpo = error.response.data as Record<string, unknown> | undefined;
  if (!cuerpo || typeof cuerpo !== "object") return false;
  let alguno = false;
  for (const [campo, valor] of Object.entries(cuerpo)) {
    if (!campos.includes(campo)) continue;
    setError(campo as Path<T>, { type: "server", message: aTexto(valor).join(" ") });
    alguno = true;
  }
  return alguno;
}
