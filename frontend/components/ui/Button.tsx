import { forwardRef, type ButtonHTMLAttributes, type ReactNode } from "react";
import { cn } from "@/lib/utils";
import { Spinner } from "./Spinner";

type Variante = "primary" | "secondary" | "ghost" | "danger";
type Tamano = "sm" | "md" | "lg";

const VARIANTES: Record<Variante, string> = {
  primary:   "bg-brand-600 text-white hover:bg-brand-700 active:bg-brand-800 shadow-sm",
  secondary: "bg-white text-ink-800 border border-ink-200 hover:bg-ink-50 hover:border-ink-300",
  ghost:     "text-ink-700 hover:bg-ink-100",
  danger:    "bg-white text-brand-700 border border-brand-200 hover:bg-brand-50",
};
const TAMANOS: Record<Tamano, string> = {
  sm: "h-8 px-3 text-xs gap-1.5",
  md: "h-10 px-4 text-sm gap-2",
  lg: "h-12 px-6 text-base gap-2",
};

export interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variante;
  size?: Tamano;
  loading?: boolean;
  icon?: ReactNode;
}

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(function Button(
  { variant = "primary", size = "md", loading, icon, className, children, disabled, type = "button", ...props },
  ref,
) {
  return (
    <button
      ref={ref}
      type={type}
      disabled={disabled || loading}
      className={cn(
        "inline-flex items-center justify-center rounded-lg font-medium transition-colors",
        "disabled:cursor-not-allowed disabled:opacity-60",
        VARIANTES[variant], TAMANOS[size], className,
      )}
      {...props}
    >
      {loading ? <Spinner className="h-4 w-4 text-current" /> : icon}
      {children}
    </button>
  );
});
