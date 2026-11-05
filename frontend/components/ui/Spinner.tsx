import { Loader2 } from "lucide-react";
import { cn } from "@/lib/utils";

export function Spinner({ className, label = "Cargando" }: { className?: string; label?: string }) {
  return <Loader2 role="status" aria-label={label} className={cn("h-5 w-5 animate-spin text-brand-600", className)} />;
}

export function PageLoader({ texto = "Cargando..." }: { texto?: string }) {
  return (
    <div className="flex flex-col items-center justify-center gap-3 py-16 text-sm text-ink-500">
      <Spinner className="h-7 w-7" />
      <span>{texto}</span>
    </div>
  );
}
