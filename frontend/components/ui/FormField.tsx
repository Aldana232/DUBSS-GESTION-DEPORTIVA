import { cloneElement, isValidElement, useId, type ReactElement, type ReactNode } from "react";
import { cn } from "@/lib/utils";

interface FormFieldProps {
  label: string;
  error?: string;
  hint?: string;
  required?: boolean;
  className?: string;
  children: ReactNode;
}

/** Etiqueta + control + ayuda/error, con los atributos aria conectados. */
export function FormField({ label, error, hint, required, className, children }: FormFieldProps) {
  const id = useId();
  const descripcion = error ? `${id}-error` : hint ? `${id}-hint` : undefined;
  const control = isValidElement(children)
    ? cloneElement(children as ReactElement<Record<string, unknown>>, {
        id,
        "aria-invalid": error ? true : undefined,
        "aria-describedby": descripcion,
      })
    : children;
  return (
    <div className={cn("space-y-1.5", className)}>
      <label htmlFor={id} className="block text-sm font-medium text-ink-700">
        {label}
        {required && <span className="ml-0.5 text-brand-600" aria-hidden="true">*</span>}
      </label>
      {control}
      {error ? (
        <p id={`${id}-error`} role="alert" className="text-xs font-medium text-brand-700">{error}</p>
      ) : hint ? (
        <p id={`${id}-hint`} className="text-xs text-ink-500">{hint}</p>
      ) : null}
    </div>
  );
}
